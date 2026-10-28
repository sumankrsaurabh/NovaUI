"""Application lifecycle and convenience API."""

from __future__ import annotations

import argparse
import asyncio
import inspect
import logging
import os
import re
import secrets
import sys
import threading
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .components import Component
from .desktop import (
    DesktopWindow,
    Menu,
    WindowOptions,
    activate_window,
    build_native_menus,
)
from .extensions import CustomComponent, Extensions, check_compatibility
from .project import current_project_root
from .routing import Router, activate_app
from .server import make_server
from .shortcuts import ShortcutRegistry
from .theme import Theme

_NO_EVENT_VALUE = object()
_logger = logging.getLogger(__name__)
_STYLESHEET_PATH = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9._/-]*\.css$")


def _validate_stylesheets(stylesheets: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    if not isinstance(stylesheets, (tuple, list)):
        raise TypeError("stylesheets must be a list or tuple of CSS paths under the project's assets/ directory.")
    if len(stylesheets) > 8:
        raise ValueError("At most 8 application stylesheets may be configured.")
    validated: list[str] = []
    for path in stylesheets:
        if (not isinstance(path, str) or not _STYLESHEET_PATH.fullmatch(path)
                or any(part in {"", ".", ".."} for part in path.split("/"))):
            raise ValueError("Stylesheet paths must be relative .css paths under assets/ without traversal segments.")
        if path in validated:
            raise ValueError(f"Duplicate application stylesheet: {path!r}.")
        validated.append(path)
    return tuple(validated)


def _package_version() -> str:
    # Resolved at runtime to avoid a package-init import cycle.
    from . import __version__

    return __version__


class App:
    def __init__(self, root: Component, title: str = "NovaUI", theme: str | Theme = "light",
                 host: str = "127.0.0.1", port: int = 0, debug: bool = False,
                 extensions: Extensions | None = None,
                 stylesheets: tuple[str, ...] | list[str] = ()):
        if not isinstance(root, Component):
            raise TypeError("app() expects a NovaUI Component as its root.")
        if not isinstance(theme, (str, Theme)):
            raise TypeError("theme must be 'light', 'dark', 'system', a registered theme name, or a Theme instance.")
        if not isinstance(debug, bool):
            raise TypeError("debug must be a bool.")
        self.root = root
        self.title = title
        self.stylesheets = _validate_stylesheets(stylesheets)
        if extensions is not None and not isinstance(extensions, Extensions):
            raise TypeError("extensions must be a ui.Extensions instance or None.")
        self._extension_components = dict(extensions.components) if extensions else {}
        self._extension_themes = dict(extensions.themes) if extensions else {}
        self._plugins = list(extensions.plugins) if extensions else []
        self._started_plugins: list[Any] = []
        self._services: dict[str, Any] = {}
        if isinstance(theme, str) and theme not in {"light", "dark", "system"}:
            try:
                theme = self._extension_themes[theme]
            except KeyError as exc:
                raise ValueError(f"Unknown theme {theme!r}; register it in ui.Extensions first.") from exc
        self.theme = theme
        self.host = host
        self.port = port
        self.debug = debug
        project_root = current_project_root()
        if project_root is None:
            configured_root = os.environ.get("NOVAUI_PROJECT_ROOT")
            entrypoint = Path(sys.argv[0]).expanduser() if sys.argv and sys.argv[0] else None
            if configured_root:
                project_root = Path(configured_root)
            elif entrypoint is not None and entrypoint.is_file():
                project_root = entrypoint.resolve().parent
            else:
                project_root = Path.cwd()
        self.asset_root = project_root.resolve()
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._handler_lock = threading.RLock()
        self._preview_lock = threading.RLock()
        self._tree_generation = 0
        self._components: dict[int, Component] = {}
        self._disposed = False
        self.server = None
        self.window: DesktopWindow | None = None
        self.shortcuts = ShortcutRegistry()
        self._close_callback: Callable[[], bool | None] | None = None
        # Private hooks used only by the live-preview host. Ordinary apps do
        # not emit polling metadata or require a preview session token.
        self._preview_poll_ms: int | None = None
        self._preview_token: str | None = None
        self._preview_error: dict[str, Any] | None = None
        for plugin in self._plugins:
            check_compatibility(plugin, _package_version())
            setup = getattr(plugin, "setup", None)
            if setup is not None:
                before = set(self._services)
                try:
                    setup(self)
                except Exception:
                    for service_name in set(self._services) - before:
                        del self._services[service_name]
                    raise

    def register_component(self, name: str, component: type[CustomComponent]) -> None:
        """Register a custom compositional component for this app instance."""
        configuration = Extensions()
        for existing_name, existing_component in self._extension_components.items():
            configuration.register_component(existing_name, existing_component)
        configuration.register_component(name, component)
        self._extension_components = configuration.components

    def register_theme(self, theme: Theme) -> None:
        """Register a named theme for subsequent use by this app."""
        configuration = Extensions()
        configuration.themes.update(self._extension_themes)
        configuration.register_theme(theme)
        self._extension_themes = configuration.themes

    def set_theme(self, theme: str | Theme) -> None:
        """Set the theme used by the next rendered application tree.

        This is useful from an event callback: after the callback returns, the
        server serializes the tree again and the frontend applies the new tokens.
        """
        if not isinstance(theme, (str, Theme)):
            raise TypeError("theme must be 'light', 'dark', 'system', a registered theme name, or a Theme instance.")
        if isinstance(theme, str) and theme not in {"light", "dark", "system"}:
            try:
                theme = self._extension_themes[theme]
            except KeyError as exc:
                raise ValueError(f"Unknown theme {theme!r}; register it in ui.Extensions first.") from exc
        self.theme = theme

    def register_service(self, name: str, service: Any) -> None:
        """Register an app-scoped service from trusted Python application code."""
        if not isinstance(name, str) or not name or not name.replace("_", "a").isalnum() or not name[0].isalpha():
            raise ValueError("Service name must start with a letter and contain only letters, digits, or underscores.")
        if name in self._services:
            raise ValueError(f"Service {name!r} is already registered.")
        self._services[name] = service

    def get_service(self, name: str) -> Any:
        try:
            return self._services[name]
        except KeyError as exc:
            raise KeyError(f"No service named {name!r} is registered.") from exc

    def register_event(self, callback: Callable[..., Any]) -> str:
        with self._handler_lock:
            event_id = secrets.token_urlsafe(32)
            while event_id in self._handlers:
                event_id = secrets.token_urlsafe(32)
            self._handlers[event_id] = callback
        return event_id

    def serialize_tree(self, route_path: str | None = None) -> dict[str, Any]:
        with self._preview_lock:
            return self._serialize_tree_locked(route_path)

    def _serialize_tree_locked(self, route_path: str | None = None) -> dict[str, Any]:
        # Rebuild the registry for the current tree so stale event IDs stop working.
        with self._handler_lock:
            if self._disposed:
                raise RuntimeError("App has been disposed and cannot be rendered again.")
            if route_path is not None and isinstance(self.root, Router):
                self.navigate(route_path)
            self._tree_generation += 1
            self._handlers = {}
            pending = [self.root]
            visited: set[int] = set()
            while pending:
                component = pending.pop()
                if not isinstance(component, Component):
                    raise TypeError("Component children must be NovaUI components.")
                if isinstance(component, CustomComponent) and type(component) not in self._extension_components.values():
                    raise ValueError(
                        f"Custom component {type(component).__name__!r} is not registered for this App."
                    )
                identity = id(component)
                if identity in visited:
                    raise ValueError("A component instance can appear only once in a component tree.")
                visited.add(identity)
                self._components[identity] = component
                pending.extend(component.iter_children())
            tree = {
                "title": self.title,
                "theme": self.theme.to_dict() if isinstance(self.theme, Theme) else self.theme,
                "stylesheets": list(self.stylesheets),
                "root": self.root.to_dict(self.register_event),
                "shortcuts": self.shortcuts.to_dict(self.register_event),
            }
            if self._preview_poll_ms is not None:
                tree["preview_poll_ms"] = self._preview_poll_ms
                tree["preview_error"] = self._preview_error
            return tree

    def navigate(self, path: str) -> None:
        """Change the current route when this app is rooted at a Router."""
        if self._disposed:
            raise RuntimeError("App has been disposed and cannot be navigated.")
        if not isinstance(self.root, Router):
            raise TypeError("Navigation requires App.root to be a ui.Router.")
        self.root.navigate(path)

    def dispose(self) -> None:
        """Release component-owned resources and invalidate registered events."""
        with self._handler_lock:
            if self._disposed:
                return
            self._disposed = True
            self._handlers.clear()
            components = tuple(reversed(tuple(self._components.values())))
        self._stop_plugins()
        for component in components:
            component.dispose()

    def _start_plugins(self) -> None:
        for plugin in self._plugins:
            # Include the current plugin before calling it so shutdown can
            # release resources acquired before a failing start hook.
            self._started_plugins.append(plugin)
            callback = getattr(plugin, "on_app_start", None)
            if callback is not None:
                callback(self)

    def _stop_plugins(self) -> None:
        while self._started_plugins:
            plugin = self._started_plugins.pop()
            callback = getattr(plugin, "on_app_stop", None)
            if callback is None:
                continue
            try:
                callback(self)
            except Exception as exc:  # noqa: BLE001 - cleanup continues for other extensions
                _logger.error("NovaUI plugin %s shutdown failed with %s", plugin.name, type(exc).__name__)

    def on_close(self, callback: Callable[[], bool | None]) -> None:
        """Set a desktop close hook; returning False cancels the close request."""
        if not callable(callback):
            raise TypeError("Close callback must be callable.")
        self._close_callback = callback

    def dispatch_event(self, event_id: str, value: Any = _NO_EVENT_VALUE) -> None:
        with self._preview_lock:
            self._dispatch_event_locked(event_id, value)

    def _dispatch_event_locked(self, event_id: str, value: Any = _NO_EVENT_VALUE) -> None:
        with self._handler_lock:
            callback = self._handlers.pop(event_id, None)
            generation = self._tree_generation
        if callback is None:
            raise ValueError("Unknown, expired, or already handled event.")
        accepts_value = bool(getattr(callback, "accepts_value", False))
        try:
            if value is _NO_EVENT_VALUE:
                if accepts_value:
                    raise ValueError("Input event requires a value.")
                with activate_app(self), activate_window(self.window):
                    result = callback()
                    if inspect.isawaitable(result):
                        asyncio.run(result)
            else:
                if not accepts_value:
                    raise ValueError("This event does not accept a value.")
                with activate_app(self), activate_window(self.window):
                    result = callback(value)
                    if inspect.isawaitable(result):
                        asyncio.run(result)
        except Exception:
            # Keep the current event usable after a handler failure. The server
            # still reports the failure, and concurrent replays remain blocked.
            with self._handler_lock:
                if generation == self._tree_generation:
                    self._handlers.setdefault(event_id, callback)
            raise

    def run(
        self,
        desktop: bool = False,
        open_browser: bool = True,
        *,
        window_options: WindowOptions | None = None,
        menu: tuple[Menu, ...] | list[Menu] = (),
    ) -> None:
        backend = None
        thread: threading.Thread | None = None
        serving = False
        try:
            self._start_plugins()
            if desktop:
                if self.host not in {"127.0.0.1", "localhost"}:
                    raise ValueError("Desktop hosting must bind to the loopback host 127.0.0.1.")
                try:
                    import webview
                except ImportError as exc:
                    raise RuntimeError('Desktop mode requires: pip install "novaui[desktop]"') from exc
                backend = webview
                options = window_options or WindowOptions()
                native_menu = build_native_menus(
                    backend,
                    menu,
                    lambda callback: self._invoke_menu_callback(callback),
                )
            else:
                if window_options is not None or menu:
                    raise ValueError("Window options and native menus require desktop=True.")
            self.server = make_server(self)
            thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            thread.start()
            serving = True
            url = f"http://127.0.0.1:{self.server.server_port}/"
            if desktop:
                try:
                    raw_window = backend.create_window(
                        self.title,
                        url,
                        **options.to_backend_options(),
                        menu=native_menu,
                    )
                except Exception as exc:
                    raise RuntimeError(
                        f"Desktop window creation failed: {exc}. Check that a pywebview GUI backend is installed."
                    ) from exc
                if raw_window is None:
                    raise RuntimeError("The desktop backend did not create a window.")
                self.window = DesktopWindow(raw_window, backend)
                if self._close_callback is not None:
                    self.window.on_close(self._invoke_close_callback)
                try:
                    backend.start(debug=self.debug)
                except Exception as exc:
                    raise RuntimeError(
                        f"Desktop GUI startup failed: {exc}. On Linux, install a pywebview GTK or Qt backend."
                    ) from exc
            else:
                if open_browser:
                    webbrowser.open(url)
                print(f"{self.title} running at {url} (Ctrl+C to stop)")
                thread.join()
        except KeyboardInterrupt:
            pass
        finally:
            self._stop_plugins()
            self.window = None
            if self.server is not None:
                if serving:
                    self.server.shutdown()
                self.server.server_close()
                self.server = None
            if thread is not None:
                thread.join(timeout=5)
            self.dispose()

    def _invoke_menu_callback(self, callback: Callable[[], Any]) -> Any:
        with activate_app(self), activate_window(self.window):
            result = callback()
        if self.window is not None:
            self.window.refresh()
        return result

    def _invoke_close_callback(self) -> bool | None:
        if self._close_callback is None:
            return None
        try:
            with activate_app(self), activate_window(self.window):
                result = self._close_callback()
        except Exception as exc:  # noqa: BLE001 - keep the window open if its close hook fails.
            _logger.error("NovaUI desktop close callback failed with %s", type(exc).__name__)
            return False
        if result is not None and not isinstance(result, bool):
            raise TypeError("Close callback must return bool or None.")
        return result


def app(
    root: Component,
    *,
    title: str = "NovaUI",
    theme: str | Theme = "light",
    debug: bool = False,
    host: str = "127.0.0.1",
    port: int = 0,
    extensions: Extensions | None = None,
    stylesheets: tuple[str, ...] | list[str] = (),
) -> App:
    """Create and run an application. Pass --desktop in argv to select desktop hosting."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--desktop", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--host", default=host)
    parser.add_argument("--port", type=int, default=port)
    args, _ = parser.parse_known_args()
    application = App(root=root, title=title, theme=theme, debug=debug or args.debug, host=args.host, port=args.port,
                      extensions=extensions, stylesheets=stylesheets)
    application.run(desktop=args.desktop, open_browser=not args.no_browser)
    return application


def desktop(
    root: Component,
    *,
    title: str = "NovaUI",
    theme: str | Theme = "light",
    width: int = 1200,
    height: int = 800,
    min_width: int = 200,
    min_height: int = 100,
    resizable: bool = True,
    fullscreen: bool = False,
    frameless: bool = False,
    background_color: str = "#FFFFFF",
    debug: bool = False,
    menu: tuple[Menu, ...] | list[Menu] = (),
    on_close: Callable[[], bool | None] | None = None,
    extensions: Extensions | None = None,
    stylesheets: tuple[str, ...] | list[str] = (),
) -> App:
    """Create and run a desktop window using the existing NovaUI frontend."""
    options = WindowOptions(
        width=width,
        height=height,
        min_width=min_width,
        min_height=min_height,
        resizable=resizable,
        fullscreen=fullscreen,
        frameless=frameless,
        background_color=background_color,
    )
    application = App(root=root, title=title, theme=theme, debug=debug, extensions=extensions,
                      stylesheets=stylesheets)
    if on_close is not None:
        application.on_close(on_close)
    application.run(desktop=True, window_options=options, menu=menu)
    return application
