import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

import novaui as ui
from novaui.server import _MAX_REQUEST_WORKERS, _parse_event_payload, make_server


def test_parse_event_payload_accepts_registered_event_shape():
    assert _parse_event_payload(b'{"event_id":"event-1"}') == ("event-1", None)
    assert _parse_event_payload(b'{"event_id":"event-2","value":"hello"}') == (
        "event-2",
        "hello",
    )
    assert _parse_event_payload(b'{"event_id":"event-3","value":{"name":"Nova"}}') == (
        "event-3",
        {"name": "Nova"},
    )


@pytest.mark.parametrize(
    "body",
    [
        b"",
        b"not json",
        b"[]",
        b'{"event_id":""}',
        b'{"event_id":42}',
        b'{"event_id":"event-1","value":42}',
        b'{"event_id":"event-1","value":{"name":42}}',
        b'{"event_id":"event-1","value":{"bad/name":"x"}}',
        b'{"event_id":"event-1","source":"python"}',
        json.dumps({"event_id": "event-1", "value": "x" * 8_001}).encode(),
    ],
)
def test_parse_event_payload_rejects_invalid_bodies(body):
    with pytest.raises((ValueError, TypeError)):
        _parse_event_payload(body)


def test_parse_event_payload_rejects_oversized_request():
    with pytest.raises(ValueError, match="request size"):
        _parse_event_payload(b" " * 16_385)


def test_application_event_ids_are_unpredictable_and_replaced_per_tree():
    application = ui.App(ui.Button("Run", on_click=lambda: None))
    first = application.serialize_tree()["root"]["event_id"]
    second = application.serialize_tree()["root"]["event_id"]
    assert first != second
    assert len(first) >= 40
    with pytest.raises(ValueError, match="Unknown, expired"):
        application.dispatch_event(first)
    application.dispose()


def test_direct_route_load_serves_fixed_shell_and_resolves_component_tree():
    application = ui.App(ui.Router(routes={"/": ui.Text("Home"), "/users/{user_id}": lambda user_id: ui.Text(user_id)}))
    server = make_server(application)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://127.0.0.1:{server.server_port}/users/42?view=full") as response:
            assert response.status == 200
            assert b"/app.js" in response.read()
        tree_request = Request(
            f"http://127.0.0.1:{server.server_port}/api/tree?path=%2Fusers%2F42%3Fview%3Dfull",
            headers={"X-NovaUI-Request": "tree"},
        )
        with urlopen(tree_request) as response:
            tree = json.loads(response.read())
        assert tree["root"]["path"] == "/users/42?view=full"
        assert tree["root"]["children"][0]["text"] == "42"
        assert tree["root"]["query"] == {"view": ["full"]}
        with urlopen(f"http://127.0.0.1:{server.server_port}/missing/path") as response:
            assert response.status == 200
            assert b"/app.js" in response.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        application.dispose()


def test_plain_component_app_loads_through_tree_endpoint_with_root_path():
    application = ui.App(ui.Text("Single page"))
    server = make_server(application)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        tree_request = Request(
            f"http://127.0.0.1:{server.server_port}/api/tree?path=%2F",
            headers={"X-NovaUI-Request": "tree"},
        )
        with urlopen(tree_request) as response:
            tree = json.loads(response.read())
        assert tree["root"]["text"] == "Single page"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        application.dispose()


def test_project_assets_are_served_from_assets_only(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "logo.svg").write_text("<svg></svg>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("private", encoding="utf-8")
    application = ui.App(ui.Image("assets/logo.svg", "logo"))
    application.asset_root = tmp_path
    server = make_server(application)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://127.0.0.1:{server.server_port}/assets/logo.svg") as response:
            assert response.headers.get_content_type() == "image/svg+xml"
            assert response.read() == b"<svg></svg>"
        for escaped in ("%2e%2e%2fsecret.txt", "missing.png"):
            try:
                urlopen(f"http://127.0.0.1:{server.server_port}/assets/{escaped}")
            except HTTPError as error:
                assert error.code == 404
            else:
                raise AssertionError("asset traversal request should be rejected")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        application.dispose()


def test_event_endpoint_rejects_missing_or_cross_origin_browser_metadata():
    called = []
    application = ui.App(ui.Button("Run", on_click=lambda: called.append(True)))
    tree = application.serialize_tree()["root"]
    server = make_server(application)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/api/event"
    body = json.dumps({"event_id": tree["event_id"]}).encode()
    try:
        for headers in (
            {"Content-Type": "application/json"},
            {"Content-Type": "application/json", "Origin": "https://attacker.example"},
            {"Content-Type": "text/plain", "Origin": f"http://127.0.0.1:{server.server_port}"},
        ):
            request = Request(url, data=body, headers=headers, method="POST")
            with pytest.raises(HTTPError) as error:
                urlopen(request)
            assert error.value.code == 403
        assert called == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        application.dispose()


def test_event_endpoint_accepts_same_origin_json_once():
    called = []
    application = ui.App(ui.Button("Run", on_click=lambda: called.append(True)))
    tree = application.serialize_tree()["root"]
    server = make_server(application)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    request = Request(
        origin + "/api/event",
        data=json.dumps({"event_id": tree["event_id"]}).encode(),
        headers={"Content-Type": "application/json", "Origin": origin},
        method="POST",
    )
    try:
        with urlopen(request) as response:
            assert response.status == 200
            assert response.headers["Content-Security-Policy"]
        assert called == [True]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        application.dispose()


def test_event_endpoint_awaits_async_callback_before_returning_tree():
    import asyncio

    value = ui.state("before")

    async def update():
        await asyncio.sleep(0)
        value.update("after")

    application = ui.App(ui.Column(ui.Text(lambda: value.value), ui.Button("Update", on_click=update)))
    tree = application.serialize_tree()["root"]["children"][1]
    server = make_server(application)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    request = Request(
        origin + "/api/event",
        data=json.dumps({"event_id": tree["event_id"]}).encode(),
        headers={"Content-Type": "application/json", "Origin": origin},
        method="POST",
    )
    try:
        with urlopen(request) as response:
            result = json.loads(response.read())
        assert result["root"]["children"][0]["text"] == "after"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        application.dispose()


def test_callback_failure_does_not_log_or_return_sensitive_message(caplog):
    def fail():
        raise RuntimeError("password=example-secret")

    application = ui.App(ui.Button("Run", on_click=fail))
    tree = application.serialize_tree()["root"]
    server = make_server(application)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    request = Request(
        origin + "/api/event",
        data=json.dumps({"event_id": tree["event_id"]}).encode(),
        headers={"Content-Type": "application/json", "Origin": origin},
        method="POST",
    )
    try:
        with pytest.raises(HTTPError) as error:
            urlopen(request)
        assert error.value.code == 500
        body = error.value.read()
        assert b"Event handler failed." in body
        assert b"example-secret" not in body
        assert "example-secret" not in caplog.text
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        application.dispose()


def test_async_callback_failure_returns_safe_error_and_logs_type(caplog):
    async def fail():
        raise RuntimeError("sensitive async detail")

    application = ui.App(ui.Button("Run", on_click=fail))
    tree = application.serialize_tree()["root"]
    server = make_server(application)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    request = Request(
        origin + "/api/event",
        data=json.dumps({"event_id": tree["event_id"]}).encode(),
        headers={"Content-Type": "application/json", "Origin": origin},
        method="POST",
    )
    try:
        with pytest.raises(HTTPError) as error:
            urlopen(request)
        assert error.value.code == 500
        body = error.value.read()
        assert b"Event handler failed." in body
        assert b"sensitive async detail" not in body
        assert "RuntimeError" in caplog.text
        assert "sensitive async detail" not in caplog.text
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        application.dispose()


def test_host_header_is_restricted_to_loopback_authority():
    application = ui.App(ui.Text("Local"))
    server = make_server(application)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    request = Request(
        f"http://127.0.0.1:{server.server_port}/",
        headers={"Host": "attacker.example"},
    )
    try:
        with pytest.raises(HTTPError) as error:
            urlopen(request)
        assert error.value.code == 421
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        application.dispose()


def test_tree_endpoint_rejects_cross_site_style_get_without_custom_header():
    application = ui.App(ui.Text("Local"))
    server = make_server(application)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(HTTPError) as error:
            urlopen(f"http://127.0.0.1:{server.server_port}/api/tree?path=%2F")
        assert error.value.code == 403
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        application.dispose()


def test_assets_larger_than_limit_are_rejected(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    huge = assets / "large.bin"
    with huge.open("wb") as stream:
        stream.truncate(32 * 1024 * 1024 + 1)
    application = ui.App(ui.Text("Assets"))
    application.asset_root = tmp_path
    server = make_server(application)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(HTTPError) as error:
            urlopen(f"http://127.0.0.1:{server.server_port}/assets/large.bin")
        assert error.value.code == 413
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        application.dispose()


def test_server_returns_503_when_worker_limit_is_reached():
    application = ui.App(ui.Text("Busy"))
    server = make_server(application)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    acquired = [server._worker_slots.acquire(blocking=False) for _ in range(_MAX_REQUEST_WORKERS)]
    try:
        assert all(acquired)
        with pytest.raises(HTTPError) as error:
            urlopen(f"http://127.0.0.1:{server.server_port}/")
        assert error.value.code == 503
    finally:
        for _ in range(sum(acquired)):
            server._worker_slots.release()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        application.dispose()


@pytest.mark.parametrize("host", ["0.0.0.0", "::"])
def test_server_rejects_non_loopback_bind_hosts(host):
    application = ui.App(ui.Text("Unsafe bind"), host=host)
    with pytest.raises(ValueError, match="loopback"):
        make_server(application)
    application.dispose()


@pytest.mark.parametrize("port", [-1, 65536, True, "8000"])
def test_server_rejects_invalid_ports(port):
    application = ui.App(ui.Text("Bad port"), port=port)
    with pytest.raises(ValueError, match="port"):
        make_server(application)
    application.dispose()
