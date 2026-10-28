"""Local development HTTP server and safe event bridge."""

from __future__ import annotations

import hmac
import json
import logging
import mimetypes
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files as package_files
from urllib.parse import parse_qs, unquote, urlparse

_MAX_EVENT_BODY = 16_384
_MAX_INPUT_VALUE = 8_000
_MAX_FORM_FIELDS = 100
_MAX_ASSET_SIZE = 32 * 1024 * 1024
_MAX_REQUEST_WORKERS = 32
_REQUEST_TIMEOUT_SECONDS = 10
_FORM_FIELD_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")
_logger = logging.getLogger(__name__)
_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; font-src 'self' data:; connect-src 'self'; "
    "object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
)


class _BoundedThreadingHTTPServer(ThreadingHTTPServer):
    """Threaded local server with bounded concurrent requests and socket reads."""

    daemon_threads = True
    request_queue_size = 64

    def __init__(self, *args, max_workers: int = _MAX_REQUEST_WORKERS, **kwargs):
        if not isinstance(max_workers, int) or isinstance(max_workers, bool) or max_workers < 1:
            raise ValueError("max_workers must be a positive integer.")
        self._worker_slots = threading.BoundedSemaphore(max_workers)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        if not self._worker_slots.acquire(blocking=False):
            try:
                request.sendall(
                    b"HTTP/1.1 503 Service Unavailable\r\n"
                    b"Connection: close\r\nContent-Length: 0\r\n\r\n"
                )
            except OSError:
                pass
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._worker_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._worker_slots.release()

    def get_request(self):
        request, client_address = super().get_request()
        request.settimeout(_REQUEST_TIMEOUT_SECONDS)
        return request, client_address


def _parse_event_payload(body: bytes) -> tuple[str, str | dict[str, str] | None]:
    """Validate a browser event body before it reaches the event registry."""
    if not 1 <= len(body) <= _MAX_EVENT_BODY:
        raise ValueError("Invalid request size.")
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("Event payload must be valid JSON.") from exc
    if not isinstance(payload, dict):
        raise TypeError("Event payload must be a JSON object.")
    if set(payload) - {"event_id", "value"}:
        raise ValueError("Event payload contains unsupported fields.")
    event_id = payload.get("event_id")
    if not isinstance(event_id, str) or not 1 <= len(event_id) <= 100:
        raise ValueError("Invalid event ID.")
    if "value" not in payload:
        return event_id, None
    value = payload["value"]
    if isinstance(value, str):
        if len(value) > _MAX_INPUT_VALUE:
            raise ValueError("Input value must be a string of at most 8000 characters.")
        return event_id, value
    if isinstance(value, dict):
        if not 1 <= len(value) <= _MAX_FORM_FIELDS:
            raise ValueError("Form submissions must contain between 1 and 100 fields.")
        for name, field_value in value.items():
            if (
                not isinstance(name, str) or not _FORM_FIELD_NAME.fullmatch(name) or not isinstance(field_value, str)
                or len(field_value) > _MAX_INPUT_VALUE
            ):
                raise ValueError("Form field names and values are invalid or too large.")
        return event_id, value
    raise ValueError("Event value must be text or a form field mapping.")


def make_server(application):
    if not isinstance(application.host, str) or application.host not in {"127.0.0.1", "localhost"}:
        raise ValueError("NovaUI's local server must bind to the loopback host 127.0.0.1 or localhost.")
    if (
        not isinstance(application.port, int)
        or isinstance(application.port, bool)
        or not 0 <= application.port <= 65535
    ):
        raise ValueError("NovaUI server port must be an integer between 0 and 65535.")

    class Handler(BaseHTTPRequestHandler):
        server_version = "NovaUI/0.1"

        def log_message(self, format, *args):
            # Keep normal console output concise; override for structured logging later.
            return

        def _send(self, status: int, body: bytes, content_type: str):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", _CONTENT_SECURITY_POLICY)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _valid_host(self) -> bool:
            host = self.headers.get("Host", "")
            parsed = urlparse(f"//{host}")
            try:
                port = parsed.port
            except ValueError:
                return False
            return (
                parsed.hostname in {"127.0.0.1", "localhost"}
                and parsed.username is None
                and parsed.password is None
                and not parsed.path
                and not parsed.query
                and not parsed.fragment
                and port == self.server.server_port
            )

        def _valid_same_origin_post(self) -> bool:
            if self.headers.get_content_type().lower() != "application/json":
                return False
            origin = self.headers.get("Origin")
            if not origin:
                return False
            parsed_origin = urlparse(origin)
            try:
                port = parsed_origin.port
            except ValueError:
                return False
            parsed_host = urlparse(f"//{self.headers.get('Host', '')}")
            return (
                parsed_origin.scheme == "http"
                and parsed_origin.hostname in {"127.0.0.1", "localhost"}
                and parsed_origin.hostname == parsed_host.hostname
                and port == self.server.server_port
                and parsed_origin.path == ""
                and not parsed_origin.query
                and not parsed_origin.fragment
                and parsed_origin.username is None
                and parsed_origin.password is None
            )

        def _valid_preview_token(self) -> bool:
            expected = getattr(application, "_preview_token", None)
            if expected is None:
                return True
            supplied = self.headers.get("X-NovaUI-Preview-Token", "")
            return bool(supplied) and hmac.compare_digest(expected, supplied)

        def do_GET(self):
            if not self._valid_host():
                self._send(421, b"Misdirected request", "text/plain; charset=utf-8")
                return
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/api/tree":
                if self.headers.get("X-NovaUI-Request") != "tree":
                    self._send(403, b"Invalid tree request", "text/plain; charset=utf-8")
                    return
                if not self._valid_preview_token():
                    self._send(403, b"Invalid or missing preview session token", "text/plain; charset=utf-8")
                    return
                route_path = parse_qs(parsed.query).get("path", ["/"])[0]
                try:
                    payload = json.dumps(application.serialize_tree(route_path=route_path)).encode("utf-8")
                    self._send(200, payload, "application/json; charset=utf-8")
                except Exception as exc:  # noqa: BLE001 - return a bounded error for unexpected route failures.
                    _logger.error("NovaUI route rendering failed with %s", type(exc).__name__)
                    message = f"Route rendering failed ({type(exc).__name__})." if application.debug else "Could not render this page."
                    body = json.dumps({"error": message}).encode("utf-8")
                    self._send(500, body, "application/json; charset=utf-8")
                return
            if path in {"/", "/index.html"}:
                self._serve_file("index.html", "text/html; charset=utf-8")
                return
            if path == "/app.js":
                self._serve_file("app.js", "text/javascript; charset=utf-8")
                return
            if path == "/styles.css":
                self._serve_file("styles.css", "text/css; charset=utf-8")
                return
            if path.startswith("/assets/"):
                self._serve_project_asset(path.removeprefix("/assets/"))
                return
            if path.startswith("/api/"):
                self._send(404, b"Not found", "text/plain; charset=utf-8")
                return
            # Serve only the fixed application shell for client-side route paths.
            self._serve_file("index.html", "text/html; charset=utf-8")

        def _serve_file(self, name, content_type):
            try:
                body = package_files("novaui").joinpath("frontend", name).read_bytes()
            except OSError:
                self._send(500, b"NovaUI frontend asset missing", "text/plain; charset=utf-8")
                return
            self._send(200, body, content_type)

        def _serve_project_asset(self, relative_path: str) -> None:
            try:
                decoded = unquote(relative_path, errors="strict")
                if not decoded or "\\" in decoded or "\x00" in decoded:
                    raise ValueError("invalid asset path")
                root = (application.asset_root / "assets").resolve()
                target = (root / decoded).resolve()
                if not target.is_relative_to(root) or not target.is_file():
                    raise ValueError("asset is outside the assets directory or missing")
                if target.stat().st_size > _MAX_ASSET_SIZE:
                    self._send(413, b"Asset is too large", "text/plain; charset=utf-8")
                    return
                content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
                self._send(200, target.read_bytes(), content_type)
            except (OSError, UnicodeError, ValueError):
                self._send(404, b"Asset not found", "text/plain; charset=utf-8")

        def do_POST(self):
            if not self._valid_host():
                self._send(421, b"Misdirected request", "text/plain; charset=utf-8")
                return
            path = urlparse(self.path).path
            if path != "/api/event":
                self._send(404, b"Not found", "text/plain; charset=utf-8")
                return
            if not self._valid_same_origin_post():
                self._send(403, b"Cross-origin event request rejected", "text/plain; charset=utf-8")
                return
            if not self._valid_preview_token():
                self._send(403, b"Invalid or missing preview session token", "text/plain; charset=utf-8")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > _MAX_EVENT_BODY:
                    raise ValueError("Invalid request size.")
                event_id, value = _parse_event_payload(self.rfile.read(length))
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                body = json.dumps({"error": str(exc)}).encode("utf-8")
                self._send(400, body, "application/json; charset=utf-8")
                return
            try:
                if value is not None:
                    application.dispatch_event(event_id, value)
                else:
                    application.dispatch_event(event_id)
                response = json.dumps(application.serialize_tree()).encode("utf-8")
                self._send(200, response, "application/json; charset=utf-8")
            except Exception as exc:  # noqa: BLE001 - contain application callback failures at HTTP boundary.
                _logger.error("NovaUI event handler failed with %s", type(exc).__name__)
                message = f"Event handler failed ({type(exc).__name__})." if application.debug else "Event handler failed."
                body = json.dumps({"error": message}).encode("utf-8")
                self._send(500, body, "application/json; charset=utf-8")

    return _BoundedThreadingHTTPServer((application.host, application.port), Handler)
