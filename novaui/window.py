"""Window operations available from a desktop application event callback."""

from __future__ import annotations

from collections.abc import Callable

from .desktop import active_window


def set_title(title: str) -> None:
    active_window().set_title(title)


def resize(width: int, height: int) -> None:
    active_window().resize(width, height)


def minimize() -> None:
    active_window().minimize()


def maximize() -> None:
    active_window().maximize()


def restore() -> None:
    active_window().restore()


def toggle_fullscreen() -> None:
    active_window().toggle_fullscreen()


def close() -> None:
    active_window().close()


def on_close(callback: Callable[[], bool | None]) -> None:
    active_window().on_close(callback)
