"""Composable preview declarations and an isolated preview runtime.

Loading a preview module executes trusted Python at module scope. Preview
functions themselves are not called until selected for rendering.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import logging
import secrets
import sys
import threading
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar

from .app import App
from .components import Component
from .extensions import CustomComponent, Extensions
from .server import make_server
from .state import State, preview_state_scope

_PREVIEW_ATTRIBUTE = "__novaui_preview__"
_NAME_LIMIT = 120
_ALLOWED_THEMES = {"light", "dark"}
_T = TypeVar("_T", bound=Callable[..., Any])
_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreviewOptions:
    identifier: str
    name: str
    theme: str
    width: int
    height: int


@dataclass(frozen=True)
class PreviewInfo:
    identifier: str
    name: str
    function_name: str
    theme: str
    width: int
    height: int

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.identifier,
            "name": self.name,
            "function": self.function_name,
            "theme": self.theme,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True)
class PreviewDiagnostic:
    error_type: str
    message: str
    file: str
    line: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.error_type,
            "message": self.message,
            "file": self.file,
            "line": self.line,
        }


@dataclass(frozen=True)
class PreviewDiscovery:
    previews: tuple[PreviewInfo, ...]
    error: PreviewDiagnostic | None = None


@dataclass(frozen=True)
class PreviewResult:
    selected: str | None
    tree: dict[str, Any] | None
    error: PreviewDiagnostic | None = None
    previews: tuple[PreviewInfo, ...] = ()

    @property
    def ok(self) -> bool:
        return self.error is None and self.tree is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "selected": self.selected,
            "tree": self.tree,
            "error": self.error.to_dict() if self.error else None,
            "previews": [item.to_dict() for item in self.previews],
        }


@dataclass
class _Candidate:
    module: ModuleType
    module_name: str
    definitions: dict[str, tuple[Callable[..., Component], PreviewOptions]]
    local_module_names: set[str]
    replaced_modules: dict[str, ModuleType]


@dataclass(kw_only=True, eq=False)
class _PreviewRoot(Component):
    child: Component
    lock: threading.RLock

    def to_dict(self, register_event):
        with self.lock:
            return self.child.to_dict(register_event)

    def iter_children(self) -> tuple[Component, ...]:
        with self.lock:
            return (self.child,)

    def replace(self, child: Component) -> Component:
        with self.lock:
            old = self.child
            self.child = child
            return old


def _validate_dimension(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"Preview {label} must be an integer between 100 and 4096.")
    if not 100 <= value <= 4096:
        raise ValueError(f"Preview {label} must be between 100 and 4096.")


def _make_options(function: Callable[..., Any], name: str | None, theme: str, width: int, height: int,
                  identifier: str | None) -> PreviewOptions:
    if not inspect.isfunction(function):
        raise TypeError("@preview can decorate only a Python function.")
    if inspect.iscoroutinefunction(function):
        raise TypeError("Preview functions must be synchronous.")
    try:
        signature = inspect.signature(function)
    except (TypeError, ValueError) as exc:
        raise TypeError("Could not inspect the preview function signature.") from exc
    if signature.parameters:
        raise TypeError("Preview functions must take no parameters.")
    resolved_id = function.__name__ if identifier is None else identifier
    if (not isinstance(resolved_id, str) or not resolved_id.strip() or len(resolved_id) > _NAME_LIMIT
            or any(char.isspace() for char in resolved_id)):
        raise ValueError(f"Preview id must be a non-empty string of at most {_NAME_LIMIT} characters without spaces.")
    resolved_name = function.__name__ if name is None else name
    if not isinstance(resolved_name, str) or not resolved_name.strip() or len(resolved_name) > _NAME_LIMIT:
        raise ValueError(f"Preview name must be a non-empty string of at most {_NAME_LIMIT} characters.")
    if not isinstance(theme, str) or theme not in _ALLOWED_THEMES:
        raise ValueError("Preview theme must be 'light' or 'dark'.")
    _validate_dimension(width, "width")
    _validate_dimension(height, "height")
    return PreviewOptions(resolved_id.strip(), resolved_name.strip(), theme, width, height)


def preview(
    function: _T | None = None,
    *,
    name: str | None = None,
    id: str | None = None,
    theme: str = "light",
    width: int = 1024,
    height: int = 768,
) -> _T | Callable[[_T], _T]:
    """Mark a zero-argument component function for IDE live preview.

    The decorator attaches metadata only. The function runs only after the
    selected preview is explicitly rendered by :class:`PreviewRuntime`.
    """

    def decorate(target: _T) -> _T:
        options = _make_options(target, name, theme, width, height, id)
        if hasattr(target, _PREVIEW_ATTRIBUTE):
            raise ValueError(f"Function {target.__name__!r} is already a NovaUI preview.")
        # Preview functions share the function-component composition behavior,
        # including implicit single-root composition without a return statement.
        from .components import component

        wrapped = component(target)
        setattr(wrapped, _PREVIEW_ATTRIBUTE, options)
        return wrapped  # type: ignore[return-value]

    if function is None:
        return decorate
    return decorate(function)


class PreviewRuntime:
    """Loads, discovers, renders, serves, and watches workspace previews."""

    def __init__(self, workspace: str | Path | None = None) -> None:
        root = Path.cwd() if workspace is None else Path(workspace).expanduser()
        self.workspace = root.resolve()
        if not self.workspace.is_dir():
            raise NotADirectoryError(f"Preview workspace is not a directory: {self.workspace}")
        self._source: Path | None = None
        self._module: ModuleType | None = None
        self._module_name: str | None = None
        self._local_module_names: set[str] = set()
        self._definitions: dict[str, tuple[Callable[..., Component], PreviewOptions]] = {}
        self._root: _PreviewRoot | None = None
        self.app: App | None = None
        self.selected: str | None = None
        self.selected_id: str | None = None
        self.theme: str | None = None
        self.viewport = (1024, 768)
        self.last_tree: dict[str, Any] | None = None
        self.last_error: PreviewDiagnostic | None = None
        self.available_previews: tuple[PreviewInfo, ...] = ()
        self._preview_states: dict[str, dict[str, State[Any]]] = {}
        self.on_change: Callable[[PreviewResult], None] | None = None
        self.on_loading: Callable[[], None] | None = None
        self._active_candidate: _Candidate | None = None
        self._watch_stop = threading.Event()
        self._watch_thread: threading.Thread | None = None
        self.server: ThreadingHTTPServer | None = None
        self._server_thread: threading.Thread | None = None
        self._session_token: str | None = None
        self._closed = False

    def _resolve_source(self, file_path: str | Path) -> Path:
        requested = Path(file_path).expanduser()
        source = (self.workspace / requested).resolve() if not requested.is_absolute() else requested.resolve()
        try:
            source.relative_to(self.workspace)
        except ValueError as exc:
            raise ValueError("Preview source must be inside the selected workspace.") from exc
        if source.suffix != ".py":
            raise ValueError("Preview source must be a Python .py file.")
        if not source.is_file():
            raise FileNotFoundError(f"Preview source file not found: {source}")
        return source

    def _local_module(self, module: ModuleType) -> bool:
        filename = getattr(module, "__file__", None)
        if not filename:
            return False
        try:
            Path(filename).resolve().relative_to(self.workspace)
            return True
        except (ValueError, OSError):
            return False

    def _load_candidate(self, source: Path) -> _Candidate:
        replaced: dict[str, ModuleType] = {}
        # Python's timestamp-based bytecode cache can treat rapid same-size
        # editor saves within one second as unchanged. Remove caches for the
        # active module and previously tracked local modules before import.
        cache_sources = {source}
        for previous_name in self._local_module_names:
            previous_module = sys.modules.get(previous_name)
            previous_file = getattr(previous_module, "__file__", None) if previous_module else None
            if previous_file and str(previous_file).endswith(".py"):
                cache_sources.add(Path(previous_file))
        for cache_source in cache_sources:
            try:
                Path(importlib.util.cache_from_source(str(cache_source))).unlink(missing_ok=True)
            except (NotImplementedError, OSError):
                pass
        for name in self._local_module_names:
            module = sys.modules.pop(name, None)
            if module is not None:
                replaced[name] = module
        module_name = f"_novaui_preview_{secrets.token_hex(12)}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, source)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load Python source module: {source}")
            module = importlib.util.module_from_spec(spec)
            before = set(sys.modules)
            sys.modules[module_name] = module
            search_paths = [str(source.parent), str(self.workspace)]
            added = [item for item in search_paths if item not in sys.path]
            sys.path[:0] = added
            try:
                spec.loader.exec_module(module)
            finally:
                for item in added:
                    try:
                        sys.path.remove(item)
                    except ValueError:
                        pass
            local_names = {
                name for name in set(sys.modules) - before
                if self._local_module(sys.modules[name])
            }
            local_names.add(module_name)
            definitions = self._collect_previews(module)
            return _Candidate(module, module_name, definitions, local_names, replaced)
        except Exception:
            for name in set(sys.modules) - set(replaced):
                module = sys.modules.get(name)
                if name == module_name or (module is not None and self._local_module(module) and name not in replaced):
                    sys.modules.pop(name, None)
            sys.modules.update(replaced)
            raise

    @staticmethod
    def _collect_previews(module: ModuleType) -> dict[str, tuple[Callable[..., Component], PreviewOptions]]:
        found: dict[str, tuple[Callable[..., Component], PreviewOptions]] = {}
        identifiers: set[str] = set()
        seen_functions: set[int] = set()
        for value in vars(module).values():
            metadata = getattr(value, _PREVIEW_ATTRIBUTE, None)
            if metadata is None or id(value) in seen_functions:
                continue
            seen_functions.add(id(value))
            if not inspect.isfunction(value) or not isinstance(metadata, PreviewOptions):
                continue
            if metadata.name in found:
                raise ValueError(f"Duplicate preview name {metadata.name!r} in {module.__file__}.")
            if metadata.identifier in identifiers:
                raise ValueError(f"Duplicate preview id {metadata.identifier!r} in {module.__file__}.")
            identifiers.add(metadata.identifier)
            found[metadata.name] = (value, metadata)
        return found

    def _commit_candidate(self, source: Path, candidate: _Candidate) -> None:
        previous_names = self._local_module_names
        for name in previous_names:
            if name not in candidate.local_module_names:
                sys.modules.pop(name, None)
        self._source = source
        self._module = candidate.module
        self._module_name = candidate.module_name
        self._local_module_names = candidate.local_module_names
        self._definitions = candidate.definitions
        self._active_candidate = candidate

    def _rollback_candidate(self, candidate: _Candidate) -> None:
        for name in candidate.local_module_names:
            sys.modules.pop(name, None)
        sys.modules.update(candidate.replaced_modules)

    @staticmethod
    def _preview_infos(
        definitions: dict[str, tuple[Callable[..., Component], PreviewOptions]],
    ) -> tuple[PreviewInfo, ...]:
        return tuple(
            PreviewInfo(options.identifier, options.name, function.__name__, options.theme, options.width, options.height)
            for function, options in definitions.values()
        )

    def discover_previews(self, file_path: str | Path) -> PreviewDiscovery:
        """Import a workspace module and inspect its decorators without rendering."""
        try:
            source = self._resolve_source(file_path)
            candidate = self._load_candidate(source)
            if not candidate.definitions:
                self.available_previews = ()
                self._rollback_candidate(candidate)
                diagnostic = PreviewDiagnostic("NoPreviews", "No top-level @ui.preview functions were found.", str(source))
                self.last_error = diagnostic
                return PreviewDiscovery((), diagnostic)
            self._commit_candidate(source, candidate)
            self.available_previews = self._preview_infos(candidate.definitions)
            self.last_error = None
            return PreviewDiscovery(self._preview_infos(candidate.definitions))
        except Exception as exc:  # noqa: BLE001 - convert trusted module load failures to diagnostics.
            diagnostic = self._diagnostic(exc, Path(file_path))
            self.last_error = diagnostic
            return PreviewDiscovery((), diagnostic)

    def render_preview(
        self,
        file_path: str | Path,
        preview_name: str | None = None,
        *,
        theme: str | None = None,
    ) -> PreviewResult:
        """Execute one selected function and serialize it through NovaUI's App."""
        return self._render(file_path, preview_name, theme=theme, force=False)

    def reload_preview(self, file_path: str | Path | None = None, preview_name: str | None = None) -> PreviewResult:
        """Reload the active source; keep the last successful tree on failure."""
        source = file_path or self._source
        if source is None:
            diagnostic = PreviewDiagnostic("NoSource", "No preview source is active.", "")
            self.last_error = diagnostic
            return PreviewResult(self.selected, self.last_tree, diagnostic)
        return self._render(source, preview_name if preview_name is not None else self.selected,
                            theme=None, force=True, allow_fallback=preview_name is None)

    def _render(
        self,
        file_path: str | Path,
        preview_name: str | None,
        *,
        theme: str | None,
        force: bool,
        allow_fallback: bool = False,
    ) -> PreviewResult:
        source: Path | None = None
        candidate: _Candidate | None = None
        staged_states: dict[str, State[Any]] | None = None
        old_states: dict[str, State[Any]] = {}
        try:
            if self._closed:
                raise RuntimeError("Preview runtime is closed.")
            source = self._resolve_source(file_path)
            candidate = self._load_candidate(source) if force or self._source != source else self._active_candidate
            if candidate is None:
                raise RuntimeError("Preview module was not loaded.")
            if not candidate.definitions:
                raise ValueError("No top-level @ui.preview functions were found.")
            self.available_previews = self._preview_infos(candidate.definitions)
            if force and allow_fallback and preview_name not in candidate.definitions:
                matching = next((options.name for _, options in candidate.definitions.values()
                                 if options.identifier == self.selected_id), None)
                preview_name = matching or next(iter(candidate.definitions))
            if preview_name is None:
                if len(candidate.definitions) != 1:
                    options = ", ".join(candidate.definitions)
                    raise ValueError(f"Select a preview by name; available previews: {options}.")
                preview_name = next(iter(candidate.definitions))
            try:
                function, options = candidate.definitions[preview_name]
            except KeyError as exc:
                options = ", ".join(candidate.definitions)
                raise ValueError(f"Unknown preview {preview_name!r}; available previews: {options}.") from exc
            selected_theme = options.theme if theme is None else theme
            if not isinstance(selected_theme, str) or selected_theme not in _ALLOWED_THEMES:
                raise ValueError("Preview theme must be 'light' or 'dark'.")
            old_states = self._preview_states.get(options.identifier, {})
            staged_states = dict(old_states)
            used_states: set[str] = set()
            try:
                with preview_state_scope(staged_states, used_states):
                    component = function()
            except Exception:
                for key, value in staged_states.items():
                    if key not in old_states:
                        value.dispose()
                raise
            if not isinstance(component, Component):
                raise TypeError(f"Preview {preview_name!r} must return a NovaUI Component.")
            extensions = self._component_extensions(candidate.module)
            if self.app is None:
                root = _PreviewRoot(child=component, lock=threading.RLock())
                application = App(root, title=f"NovaUI Preview — {preview_name}", theme=selected_theme,
                                  host="127.0.0.1", port=0, extensions=extensions)
                self._configure_preview_app(application)
                try:
                    tree = application.serialize_tree()
                except Exception:
                    application.dispose()
                    raise
                self.app = application
                self._root = root
            else:
                assert self._root is not None
                tree = self._replace_component(component, selected_theme, extensions)
            if candidate is not self._active_candidate:
                self._commit_candidate(source, candidate)
            for key, old_state in old_states.items():
                if key not in used_states or staged_states.get(key) is not old_state:
                    old_state.dispose()
            self._preview_states[options.identifier] = staged_states
            self.selected = preview_name
            self.selected_id = options.identifier
            self.theme = selected_theme
            self.viewport = (options.width, options.height)
            self.last_tree = tree
            self.last_error = None
            self.app._preview_error = None
            return PreviewResult(self.selected, tree, previews=self.available_previews)
        except Exception as exc:  # noqa: BLE001 - preview failures must not terminate the host.
            if candidate is not None and candidate is not self._active_candidate:
                self._rollback_candidate(candidate)
            if staged_states is not None:
                for key, value in staged_states.items():
                    if key not in old_states:
                        value.dispose()
            diagnostic = self._diagnostic(exc, source or Path(file_path))
            self.last_error = diagnostic
            if self.app is not None:
                self.app._preview_error = diagnostic.to_dict()
            return PreviewResult(self.selected, self.last_tree, diagnostic, self.available_previews)

    @staticmethod
    def _component_extensions(module: ModuleType) -> Extensions:
        extensions = Extensions()
        seen: set[type[CustomComponent]] = set()
        for value in vars(module).values():
            if isinstance(value, type) and value not in seen and issubclass(value, CustomComponent) and value is not CustomComponent:
                seen.add(value)
                extensions.register_component(value.__name__, value)
        return extensions

    @staticmethod
    def _configure_preview_app(application: App) -> None:
        application._preview_poll_ms = 650
        application._preview_token = getattr(application, "_preview_token", None)

    def _replace_component(self, component: Component, theme: str, extensions: Extensions) -> dict[str, Any]:
        assert self.app is not None and self._root is not None
        with self.app._preview_lock:
            old_components = self.app._extension_components
            self.app._extension_components = dict(extensions.components)
            old_child = self._root.replace(component)
            old_theme = self.app.theme
            self.app.set_theme(theme)
            try:
                tree = self.app.serialize_tree()
            except Exception:
                rejected = self._root.replace(old_child)
                self.app._extension_components = old_components
                self.app.set_theme(old_theme)
                self._dispose_component_tree(rejected, self.app)
                self.app.serialize_tree()  # regenerate the prior tree's one-shot event IDs.
                raise
            self._dispose_component_tree(old_child, self.app)
            self._configure_preview_app(self.app)
            return tree

    @staticmethod
    def _dispose_component_tree(component: Component, application: App) -> None:
        pending = [component]
        visited: set[int] = set()
        while pending:
            current = pending.pop()
            if id(current) in visited:
                continue
            visited.add(id(current))
            pending.extend(current.iter_children())
            application._components.pop(id(current), None)
            try:
                current.dispose()
            except Exception as exc:  # noqa: BLE001 - finish disposing siblings after a faulty extension hook.
                _logger.error("Preview component %s cleanup failed with %s", type(current).__name__, type(exc).__name__)

    @staticmethod
    def _diagnostic(exc: Exception, source: Path) -> PreviewDiagnostic:
        line: int | None = getattr(exc, "lineno", None)
        frames = traceback.extract_tb(exc.__traceback__) if exc.__traceback__ else []
        resolved = str(source.resolve()) if str(source) else ""
        for frame in reversed(frames):
            try:
                if Path(frame.filename).resolve() == Path(resolved):
                    line = frame.lineno
                    break
            except (OSError, ValueError):
                continue
        return PreviewDiagnostic(type(exc).__name__, str(exc), resolved, line)

    def dispatch_event(self, event_id: str, value: Any = None) -> dict[str, Any]:
        """Dispatch a test or trusted host event through the normal App bridge."""
        if self.app is None:
            raise RuntimeError("Render a preview before dispatching events.")
        if value is None:
            self.app.dispatch_event(event_id)
        else:
            self.app.dispatch_event(event_id, value)
        self.last_tree = self.app.serialize_tree()
        return self.last_tree

    def set_theme(self, theme: str) -> dict[str, Any]:
        if not isinstance(theme, str) or theme not in _ALLOWED_THEMES:
            raise ValueError("Preview theme must be 'light' or 'dark'.")
        if self.app is None:
            raise RuntimeError("Render a preview before changing its theme.")
        with self.app._preview_lock:
            self.app.set_theme(theme)
            self.theme = theme
            self.last_tree = self.app.serialize_tree()
        return self.last_tree

    def set_viewport(self, width: int, height: int) -> None:
        _validate_dimension(width, "width")
        _validate_dimension(height, "height")
        self.viewport = width, height

    def reset_preview_state(self) -> PreviewResult:
        """Clear only the selected preview's explicitly preserved state and rerender."""
        if self._source is None or self.selected is None or self.selected_id is None:
            diagnostic = PreviewDiagnostic("NoPreview", "Render a preview before resetting its state.", "")
            return PreviewResult(self.selected, self.last_tree, diagnostic, self.available_previews)
        states = self._preview_states.pop(self.selected_id, {})
        for value in states.values():
            value.dispose()
        return self._render(self._source, self.selected, theme=None, force=False)

    def start_server(self, *, port: int = 0) -> str:
        """Start the existing renderer server with a per-session preview token."""
        if self.app is None:
            raise RuntimeError("Render a preview before starting its server.")
        if self.server is not None:
            raise RuntimeError("Preview server is already running.")
        if not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535:
            raise ValueError("Preview port must be an integer between 0 and 65535.")
        self._session_token = secrets.token_urlsafe(32)
        self.app._preview_token = self._session_token
        self.app.port = port
        self.server = make_server(self.app)
        _ = self.server.server_port  # Force server bind before starting its thread.
        self._server_thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="novaui-preview-server")
        self._server_thread.start()
        return f"http://127.0.0.1:{self.server.server_port}/#novaui-preview-token={self._session_token}"

    def start_watching(self, *, interval: float = 0.2, debounce: float = 0.25) -> None:
        if self._source is None:
            raise RuntimeError("Render a preview before starting the file watcher.")
        if interval < 0.05 or debounce < 0:
            raise ValueError("Watcher interval must be at least 0.05 seconds and debounce cannot be negative.")
        if self._watch_thread is not None and self._watch_thread.is_alive():
            return
        self._watch_stop.clear()
        initial_snapshot = self._watch_snapshot()
        self._watch_thread = threading.Thread(
            target=self._watch_loop, args=(interval, debounce, initial_snapshot), daemon=True,
            name="novaui-preview-watcher"
        )
        self._watch_thread.start()

    def _watch_snapshot(self) -> dict[Path, tuple[int, int]]:
        candidates = set()
        if self._source is not None:
            candidates.add(self._source)
        for name in self._local_module_names:
            module = sys.modules.get(name)
            filename = getattr(module, "__file__", None) if module is not None else None
            if filename:
                candidates.add(Path(filename).resolve())
        snapshot: dict[Path, tuple[int, int]] = {}
        for path in candidates:
            try:
                stat = path.stat()
                snapshot[path] = (stat.st_mtime_ns, stat.st_size)
            except OSError:
                snapshot[path] = (-1, -1)
        return snapshot

    def _watch_loop(self, interval: float, debounce: float, previous: dict[Path, tuple[int, int]]) -> None:
        while not self._watch_stop.wait(interval):
            current = self._watch_snapshot()
            if current == previous:
                continue
            if self._watch_stop.wait(debounce):
                break
            stable = self._watch_snapshot()
            if stable != current:
                previous = stable
                continue
            previous = stable
            if self.on_loading is not None:
                try:
                    self.on_loading()
                except Exception as exc:  # noqa: BLE001 - observer failures must not stop source watching.
                    _logger.warning("Preview loading observer failed with %s", type(exc).__name__)
            result = self.reload_preview()
            if self.app is not None:
                self.app._preview_error = result.error.to_dict() if result.error else None
            if self.on_change is not None:
                try:
                    self.on_change(result)
                except Exception as exc:  # noqa: BLE001 - observer failures must not stop source watching.
                    _logger.warning("Preview update observer failed with %s", type(exc).__name__)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._watch_stop.set()
        if self._watch_thread is not None:
            self._watch_thread.join(timeout=2)
            self._watch_thread = None
        if self.server is not None:
            if self._server_thread is not None and self._server_thread.is_alive():
                self.server.shutdown()
            self.server.server_close()
            self.server = None
        if self._server_thread is not None:
            self._server_thread.join(timeout=2)
            self._server_thread = None
        if self.app is not None:
            self.app.dispose()
            self.app = None
        for name in self._local_module_names:
            sys.modules.pop(name, None)
        self._local_module_names.clear()
        for states in self._preview_states.values():
            for value in states.values():
                value.dispose()
        self._preview_states.clear()
        self._module = None
        self._active_candidate = None


def discover_previews(file_path: str | Path, *, workspace: str | Path | None = None) -> PreviewDiscovery:
    """Discover previews from one trusted Python file without calling them."""
    runtime = PreviewRuntime(workspace)
    try:
        return runtime.discover_previews(file_path)
    finally:
        runtime.close()


def render_preview(
    file_path: str | Path,
    preview_name: str | None = None,
    *,
    workspace: str | Path | None = None,
    theme: str | None = None,
) -> PreviewResult:
    """Render one preview to a normal NovaUI JSON component tree."""
    runtime = PreviewRuntime(workspace)
    try:
        return runtime.render_preview(file_path, preview_name, theme=theme)
    finally:
        runtime.close()


_PROTOCOL_TYPES = {"refresh", "select", "theme", "viewport", "reset", "shutdown"}


def parse_preview_command(raw: str) -> dict[str, Any]:
    """Validate one host-to-runtime protocol message read from a private pipe."""
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > 16_384:
        raise ValueError("Preview protocol message is too large.")
    try:
        message = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Preview protocol message must be valid JSON.") from exc
    if (not isinstance(message, dict) or isinstance(message.get("version"), bool)
            or message.get("version") != 1):
        raise ValueError("Unsupported preview protocol version.")
    kind = message.get("type")
    if not isinstance(kind, str):
        raise TypeError("Preview protocol message type must be a string.")
    if kind not in _PROTOCOL_TYPES:
        raise ValueError("Unknown preview protocol message type.")
    fields_by_type = {
        "refresh": {"version", "type"},
        "select": {"version", "type", "name"},
        "theme": {"version", "type", "theme"},
        "viewport": {"version", "type", "width", "height"},
        "reset": {"version", "type"},
        "shutdown": {"version", "type"},
    }
    if set(message) != fields_by_type[kind]:
        raise ValueError(f"Preview {kind} message has missing or unsupported fields.")
    if kind == "select" and (not isinstance(message.get("name"), str) or not message["name"]):
        raise ValueError("Preview selection requires a non-empty name.")
    if kind == "theme" and (
        not isinstance(message.get("theme"), str) or message["theme"] not in _ALLOWED_THEMES
    ):
        raise ValueError("Preview theme must be 'light' or 'dark'.")
    if kind == "viewport":
        _validate_dimension(message.get("width"), "width")
        _validate_dimension(message.get("height"), "height")
    return message
