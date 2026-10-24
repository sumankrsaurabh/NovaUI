"""Explicit text clipboard operations for desktop event callbacks."""

from __future__ import annotations

from .desktop import active_window


def write_text(text: str) -> None:
    """Copy text using the system Tk clipboard; raises when Tk/clipboard is unavailable."""
    active_window()
    if not isinstance(text, str):
        raise TypeError("Clipboard text must be a string.")
    try:
        import tkinter

        root = tkinter.Tk()
        try:
            root.withdraw()
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
        finally:
            root.destroy()
    except Exception as exc:
        raise RuntimeError("Text clipboard access is unavailable in this desktop environment.") from exc


def read_text() -> str:
    """Read text from the system clipboard; raises when Tk/clipboard is unavailable."""
    active_window()
    try:
        import tkinter

        root = tkinter.Tk()
        try:
            root.withdraw()
            return str(root.clipboard_get())
        finally:
            root.destroy()
    except Exception as exc:
        raise RuntimeError("Text clipboard access is unavailable in this desktop environment.") from exc
