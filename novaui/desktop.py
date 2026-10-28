"""Optional pywebview integration and window configuration."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

_ACTIVE_WINDOW: ContextVar[DesktopWindow | None] = ContextVar("novaui_desktop_window", default=None)
_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
_FILE_FILTER = re.compile(r"^[^()\r\n]+ \(\*\.[A-Za-z0-9*?.; -]+\)$")


@dataclass(frozen=True)
class WindowOptions:
    width: int = 1200
    height: int = 800
    min_width: int = 200
    min_height: int = 100
    resizable: bool = True
    fullscreen: bool = False
    frameless: bool = False
    background_color: str = "#FFFFFF"

    def __post_init__(self) -> None:
        for name in ("width", "height", "min_width", "min_height"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"Desktop {name} must be a positive integer.")
        if self.min_width > self.width or self.min_height > self.height:
            raise ValueError("Desktop minimum dimensions cannot exceed the initial dimensions.")
        for name in ("resizable", "fullscreen", "frameless"):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"Desktop {name} must be a bool.")
        if not isinstance(self.background_color, str) or not _HEX_COLOR.fullmatch(self.background_color):
            raise ValueError("Desktop background_color must be a #RRGGBB color.")

    def to_backend_options(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "min_size": (self.min_width, self.min_height),
            "resizable": self.resizable,
            "fullscreen": self.fullscreen,
            "frameless": self.frameless,
            "background_color": self.background_color,
        }


@contextmanager
def activate_window(window: DesktopWindow | None) -> Iterator[None]:
    token = _ACTIVE_WINDOW.set(window)
    try:
        yield
    finally:
        _ACTIVE_WINDOW.reset(token)


def active_window() -> DesktopWindow:
    window = _ACTIVE_WINDOW.get()
    if window is None:
        raise RuntimeError("This native API is available only inside a desktop event callback.")
    return window


class DesktopWindow:
    """Small stable wrapper around a single pywebview window instance."""

    def __init__(self, backend_window: Any, backend: Any):
        self._window = backend_window
        self._backend = backend
        self._closed = False

    def set_title(self, title: str) -> None:
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Window title must be a non-empty string.")
        self._window.title = title

    def resize(self, width: int, height: int) -> None:
        _dimensions(width, height)
        self._window.resize(width, height)

    def minimize(self) -> None:
        self._window.minimize()

    def maximize(self) -> None:
        self._window.maximize()

    def restore(self) -> None:
        self._window.restore()

    def toggle_fullscreen(self) -> None:
        self._window.toggle_fullscreen()

    def close(self) -> None:
        self._window.destroy()
        self._closed = True

    def refresh(self) -> None:
        if not self._closed:
            self._window.evaluate_js("window.location.reload()")

    def on_close(self, callback: Callable[[], bool | None]) -> None:
        if not callable(callback):
            raise TypeError("Window close callback must be callable.")
        self._window.events.closing += callback

    def open_file(
        self, *, title: str | None = None, file_types: Sequence[str] = ()
    ) -> str | None:
        _validate_dialog_options(title, file_types)
        # pywebview currently does not expose a native file-dialog title option.
        file_dialog = getattr(self._backend, "FileDialog", None)
        open_type = file_dialog.OPEN if file_dialog is not None else self._backend.OPEN_DIALOG
        selected = self._window.create_file_dialog(open_type, allow_multiple=False, file_types=tuple(file_types))
        return str(selected[0]) if selected else None

    def save_file(
        self,
        *,
        title: str | None = None,
        suggested_name: str = "",
        file_types: Sequence[str] = (),
    ) -> str | None:
        _validate_dialog_options(title, file_types)
        if not isinstance(suggested_name, str) or "\x00" in suggested_name:
            raise ValueError("suggested_name must be a string without null characters.")
        file_dialog = getattr(self._backend, "FileDialog", None)
        save_type = file_dialog.SAVE if file_dialog is not None else self._backend.SAVE_DIALOG
        selected = self._window.create_file_dialog(
            save_type,
            save_filename=suggested_name,
            file_types=tuple(file_types),
        )
        return str(selected[0]) if selected else None

    def select_folder(self, *, title: str | None = None) -> str | None:
        _validate_dialog_options(title, ())
        file_dialog = getattr(self._backend, "FileDialog", None)
        folder_type = getattr(file_dialog, "FOLDER", None) if file_dialog is not None else None
        if folder_type is None:
            folder_type = getattr(self._backend, "FOLDER_DIALOG", None)
        if folder_type is None:
            raise RuntimeError("The active pywebview backend does not support folder selection.")
        selected = self._window.create_file_dialog(folder_type, allow_multiple=False)
        return str(selected[0]) if selected else None


@dataclass(frozen=True)
class MenuItem:
    title: str
    callback: Callable[[], Any]

    def __post_init__(self) -> None:
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("Menu item title must be a non-empty string.")
        if not callable(self.callback):
            raise TypeError("Menu item callback must be callable.")


@dataclass(frozen=True)
class MenuSeparator:
    """Visual separator between native menu items."""


@dataclass(frozen=True)
class Menu:
    title: str
    items: Sequence[MenuItem | Menu | MenuSeparator]

    def __post_init__(self) -> None:
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("Menu title must be a non-empty string.")
        if not isinstance(self.items, Sequence) or isinstance(self.items, (str, bytes)):
            raise TypeError("Menu items must be a sequence.")
        if any(not isinstance(item, (MenuItem, Menu, MenuSeparator)) for item in self.items):
            raise TypeError("Menus may contain only MenuItem, Menu, or MenuSeparator values.")


def build_native_menus(backend: Any, menus: Sequence[Menu], invoke: Callable[[Callable[[], Any]], Any]):
    if not isinstance(menus, Sequence) or isinstance(menus, (str, bytes)):
        raise TypeError("menu must be a sequence of Menu values.")
    if any(not isinstance(menu, Menu) for menu in menus):
        raise TypeError("menu must contain only Menu values.")

    def build(menu: Menu):
        items = []
        for item in menu.items:
            if isinstance(item, Menu):
                items.append(build(item))
            elif isinstance(item, MenuSeparator):
                items.append(backend.menu.MenuSeparator())
            else:
                items.append(backend.menu.MenuAction(item.title, lambda callback=item.callback: invoke(callback)))
        return backend.menu.Menu(menu.title, items)

    return [build(menu) for menu in menus]


def _dimensions(width: int, height: int) -> None:
    for name, value in (("width", width), ("height", height)):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"Window {name} must be a positive integer.")


def _validate_dialog_options(title: str | None, file_types: Sequence[str]) -> None:
    if title is not None and (not isinstance(title, str) or not title.strip()):
        raise ValueError("Dialog title must be a non-empty string or None.")
    if not isinstance(file_types, Sequence) or isinstance(file_types, (str, bytes)):
        raise TypeError("file_types must be a sequence of filter strings.")
    if any(not isinstance(item, str) or not _FILE_FILTER.fullmatch(item) for item in file_types):
        raise ValueError('File filters must use pywebview format, for example "Text files (*.txt)".')
