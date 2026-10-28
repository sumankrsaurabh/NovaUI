"""Native desktop open/save dialogs backed by pywebview."""

from __future__ import annotations

from collections.abc import Sequence

from .desktop import active_window


def open_file(*, title: str | None = None, file_types: Sequence[str] = ()) -> str | None:
    """Open a native single-file picker; return the chosen path or None if cancelled."""
    return active_window().open_file(title=title, file_types=file_types)


def save_file(
    *,
    title: str | None = None,
    suggested_name: str = "",
    file_types: Sequence[str] = (),
) -> str | None:
    """Open a native save picker; do not create or write the selected file."""
    return active_window().save_file(title=title, suggested_name=suggested_name, file_types=file_types)


def select_folder(*, title: str | None = None) -> str | None:
    """Open a native folder picker; return the selected directory or None if cancelled."""
    return active_window().select_folder(title=title)
