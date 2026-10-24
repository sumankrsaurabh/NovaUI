"""Small route matcher and event-scoped navigation API."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

from .components import Component, Text

_ACTIVE_APP: ContextVar[Any | None] = ContextVar("novaui_active_app", default=None)
_PARAMETER = re.compile(r"\{([A-Za-z][A-Za-z0-9_]*)\}")


@contextmanager
def activate_app(application: Any) -> Iterator[None]:
    token = _ACTIVE_APP.set(application)
    try:
        yield
    finally:
        _ACTIVE_APP.reset(token)


def navigate(path: str) -> None:
    """Navigate the Router belonging to the currently executing UI event."""
    application = _ACTIVE_APP.get()
    if application is None:
        raise RuntimeError("navigate() can only be called from a NovaUI event callback.")
    application.navigate(path)


class Router(Component):
    """Resolve static or ``{parameter}`` routes to component trees."""

    def __init__(
        self,
        *,
        routes: Mapping[str, Component | Callable[..., Component]],
        not_found: Component | Callable[[], Component] | None = None,
        **props: Any,
    ):
        super().__init__(**props)
        if not isinstance(routes, Mapping) or not routes:
            raise ValueError("Router routes must be a non-empty mapping.")
        self._routes: list[tuple[str, re.Pattern[str], tuple[str, ...], Any]] = []
        signatures: set[str] = set()
        for pattern, page in routes.items():
            compiled, parameters, signature = self._compile(pattern)
            if signature in signatures:
                raise ValueError(f"Router contains a duplicate route pattern: {pattern!r}.")
            if not isinstance(page, Component) and not callable(page):
                raise TypeError(f"Route {pattern!r} must map to a Component or page factory.")
            signatures.add(signature)
            self._routes.append((pattern, compiled, parameters, page))
        self._routes.sort(key=lambda route: len(route[2]))
        if not_found is not None and not isinstance(not_found, Component) and not callable(not_found):
            raise TypeError("Router not_found must be a Component, page factory, or None.")
        self._not_found = not_found or Text("404 — Page not found")
        self._page_cache: dict[tuple[str, tuple[tuple[str, str], ...]], Component] = {}
        self.current_path = "/"
        self.path = "/"
        self.params: dict[str, str] = {}
        self.query_params: dict[str, list[str]] = {}
        self._page: Component
        self.navigate("/")

    @staticmethod
    def _compile(pattern: str) -> tuple[re.Pattern[str], tuple[str, ...], str]:
        if not isinstance(pattern, str) or not pattern.startswith("/") or "?" in pattern or "#" in pattern:
            raise ValueError(f"Invalid route path: {pattern!r}.")
        normalized = pattern.rstrip("/") or "/"
        names: list[str] = []
        signature_parts: list[str] = []
        regex_parts: list[str] = []
        segments = [] if normalized == "/" else normalized[1:].split("/")
        for segment in segments:
            match = _PARAMETER.fullmatch(segment)
            if match:
                name = match.group(1)
                if name in names:
                    raise ValueError(f"Route path {pattern!r} repeats parameter {name!r}.")
                names.append(name)
                signature_parts.append("{}")
                regex_parts.append(f"(?P<{name}>[^/]+)")
            else:
                if "{" in segment or "}" in segment or "\\" in segment:
                    raise ValueError(f"Invalid route path: {pattern!r}.")
                signature_parts.append(segment)
                regex_parts.append(re.escape(segment))
        route_regex = "^/" + "/".join(regex_parts) + "$"
        signature = "/" + "/".join(signature_parts)
        return re.compile(route_regex), tuple(names), signature

    @staticmethod
    def _normalize(path: str) -> tuple[str, str, dict[str, list[str]]]:
        if not isinstance(path, str) or not 1 <= len(path) <= 2048:
            raise ValueError("Invalid navigation path: expected a path up to 2048 characters.")
        try:
            parsed = urlsplit(path)
            decoded_path = unquote(parsed.path, errors="strict")
            query = parse_qs(parsed.query, keep_blank_values=True, max_num_fields=100)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("Invalid navigation path.") from exc
        if (
            not parsed.path.startswith("/") or parsed.scheme or parsed.netloc or "\\" in decoded_path
            or any(part == ".." for part in decoded_path.split("/")) or "\x00" in decoded_path
        ):
            raise ValueError("Invalid navigation path: use an application route beginning with '/'.")
        route_path = decoded_path.rstrip("/") or "/"
        query_string = f"?{parsed.query}" if parsed.query else ""
        return route_path + query_string, route_path, query

    def navigate(self, path: str) -> None:
        current_path, route_path, query = self._normalize(path)
        matched: tuple[str, tuple[str, ...], Any, dict[str, str]] | None = None
        for pattern, regex, parameters, page in self._routes:
            match = regex.fullmatch(route_path)
            if match:
                params = {name: unquote(match.group(name)) for name in parameters}
                matched = (pattern, parameters, page, params)
                break
        if matched is None:
            cache_key = ("__not_found__", ())
            page_factory = self._not_found
            params: dict[str, str] = {}
        else:
            pattern, _, page_factory, params = matched
            cache_key = (pattern, tuple(params.items()))
        self.query_params = query
        self.params = params
        if cache_key not in self._page_cache:
            page = page_factory(**params) if callable(page_factory) and not isinstance(page_factory, Component) else page_factory
            if not isinstance(page, Component):
                raise TypeError("A route page factory must return a NovaUI Component.")
            self._page_cache[cache_key] = page
        self._page = self._page_cache[cache_key]
        self.path = route_path
        self.current_path = current_path

    def iter_children(self) -> tuple[Component, ...]:
        pages = [page for _, _, _, page in self._routes if isinstance(page, Component)]
        pages.extend(self._page_cache.values())
        if isinstance(self._not_found, Component):
            pages.append(self._not_found)
        unique: dict[int, Component] = {id(page): page for page in pages}
        return tuple(unique.values())

    def to_dict(self, register_event):
        return {
            "id": self._node_id(),
            "type": "router",
            "path": self.current_path,
            "params": dict(self.params),
            "query": dict(self.query_params),
            "children": [self._page.to_dict(register_event)],
            **self._common_props(),
        }
