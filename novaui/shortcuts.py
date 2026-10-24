"""Per-application keyboard shortcut registrations."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

_KEY_PATTERN = re.compile(r"^[A-Za-z0-9]$|^(?:F(?:[1-9]|1[0-2])|Enter|Escape|Tab|Backspace|Delete|Arrow(?:Up|Down|Left|Right)|Space)$", re.IGNORECASE)
_MODIFIERS = {"ctrl": "Ctrl", "control": "Ctrl", "meta": "Meta", "cmd": "Meta",
              "command": "Meta", "alt": "Alt", "shift": "Shift", "mod": "Mod"}
_ORDER = {"Ctrl": 0, "Meta": 1, "Alt": 2, "Shift": 3, "Mod": 4}
_NAMED_KEYS = {
    "enter": "Enter", "escape": "Escape", "tab": "Tab", "backspace": "Backspace",
    "delete": "Delete", "arrowup": "ArrowUp", "arrowdown": "ArrowDown",
    "arrowleft": "ArrowLeft", "arrowright": "ArrowRight", "space": "Space",
}


def normalize_shortcut(shortcut: str) -> str:
    if not isinstance(shortcut, str) or not shortcut.strip():
        raise ValueError("Shortcut must be a non-empty string such as 'Mod+S'.")
    parts = [part.strip() for part in shortcut.split("+")]
    if len(parts) < 2 or any(not part for part in parts):
        raise ValueError("Shortcut must include a modifier and key, for example 'Ctrl+S'.")
    modifiers: list[str] = []
    key: str | None = None
    for part in parts:
        modifier = _MODIFIERS.get(part.lower())
        if modifier is not None:
            if modifier in modifiers:
                raise ValueError("Shortcut modifiers cannot be repeated.")
            modifiers.append(modifier)
        elif key is None and _KEY_PATTERN.fullmatch(part):
            key = part.upper() if len(part) == 1 else _NAMED_KEYS.get(part.lower(), part.upper())
        else:
            raise ValueError(f"Invalid shortcut key or modifier: {part!r}.")
    if key is None:
        raise ValueError("Shortcut must end with one key.")
    return "+".join([*sorted(modifiers, key=_ORDER.__getitem__), key])


@dataclass
class _Shortcut:
    callback: Callable[[], Any]
    prevent_default: bool
    allow_in_inputs: bool
    enabled: bool = True


class ShortcutRegistry:
    """Application-owned registry serialized as event IDs into the frontend."""

    def __init__(self):
        self._items: dict[str, _Shortcut] = {}

    def register(
        self,
        shortcut: str,
        callback: Callable[[], Any],
        *,
        prevent_default: bool = True,
        allow_in_inputs: bool = False,
        replace: bool = False,
    ) -> None:
        key = normalize_shortcut(shortcut)
        if not callable(callback):
            raise TypeError("Shortcut callback must be callable.")
        if not all(isinstance(value, bool) for value in (prevent_default, allow_in_inputs, replace)):
            raise TypeError("Shortcut options must be bools.")
        if key in self._items and not replace:
            raise ValueError(f"Shortcut {key!r} is already registered.")
        self._items[key] = _Shortcut(callback, prevent_default, allow_in_inputs)

    def unregister(self, shortcut: str) -> bool:
        key = normalize_shortcut(shortcut)
        return self._items.pop(key, None) is not None

    def set_enabled(self, shortcut: str, enabled: bool) -> None:
        key = normalize_shortcut(shortcut)
        if not isinstance(enabled, bool):
            raise TypeError("Shortcut enabled must be a bool.")
        if key not in self._items:
            raise KeyError(f"Shortcut {key!r} is not registered.")
        self._items[key].enabled = enabled

    def clear(self) -> None:
        self._items.clear()

    def to_dict(self, register_event: Callable[[Callable[[], Any]], str]) -> list[dict[str, Any]]:
        return [
            {
                "key": key,
                "event_id": register_event(item.callback),
                "prevent_default": item.prevent_default,
                "allow_in_inputs": item.allow_in_inputs,
            }
            for key, item in self._items.items()
            if item.enabled
        ]
