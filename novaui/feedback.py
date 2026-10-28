"""Accessible alert, spinner, and confirmation-dialog components."""

from __future__ import annotations

import itertools
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .components import Component
from .state import State, state

_logger = logging.getLogger(__name__)


@dataclass
class Alert(Component):
    message: str
    kind: str = "info"

    def to_dict(self, register_event):
        if not isinstance(self.message, str):
            raise TypeError("Alert message must be a string.")
        if not isinstance(self.kind, str) or self.kind not in ("info", "success", "warning", "error"):
            raise ValueError("Alert kind must be info, success, warning, or error.")
        return {"id": self._node_id(), "type": "alert", "message": self.message,
                "kind": self.kind, **self._common_props()}


@dataclass
class Spinner(Component):
    label: str = "Loading"

    def to_dict(self, register_event):
        if not isinstance(self.label, str) or not self.label:
            raise ValueError("Spinner label must be a non-empty string.")
        return {"id": self._node_id(), "type": "spinner", "label": self.label,
                **self._common_props()}


class Toast(Component):
    """A dismissible notification that optionally disappears after a duration."""

    def __init__(
        self,
        message: str,
        *,
        kind: str = "info",
        duration: int = 5000,
        on_dismiss: Callable[[], Any] | None = None,
        **props: Any,
    ):
        super().__init__(**props)
        self.message = message
        self.kind = kind
        self.duration = duration
        self.on_dismiss = on_dismiss
        self._dismissed = False

    def _dismiss(self) -> None:
        if self._dismissed:
            return
        self._dismissed = True
        if self.on_dismiss is not None:
            self.on_dismiss()

    def to_dict(self, register_event):
        if not isinstance(self.message, str) or not self.message:
            raise ValueError("Toast message must be a non-empty string.")
        if self.kind not in {"info", "success", "warning", "error"}:
            raise ValueError("Toast kind must be info, success, warning, or error.")
        if (isinstance(self.duration, bool) or not isinstance(self.duration, int)
                or not 0 <= self.duration <= 60000):
            raise ValueError("Toast duration must be an integer from 0 to 60000 milliseconds.")
        if self.on_dismiss is not None and not callable(self.on_dismiss):
            raise TypeError("Toast on_dismiss must be callable or None.")
        return {
            "id": self._node_id(),
            "type": "toast",
            "message": self.message,
            "kind": self.kind,
            "duration": self.duration,
            "dismissed": self._dismissed,
            "dismiss_event_id": (
                register_event(self._dismiss) if not self._dismissed else None
            ),
            **self._common_props(),
            "visible": self.visible and not self._dismissed,
        }


class ToastHost(Component):
    """A live notification region that lays out multiple toast components."""

    def __init__(self, *toasts: Toast, label: str = "Notifications", **props: Any):
        super().__init__(**props)
        self.toasts = toasts
        self.label = label

    def iter_children(self) -> tuple[Component, ...]:
        return self.toasts

    def to_dict(self, register_event):
        if any(not isinstance(toast, Toast) for toast in self.toasts):
            raise TypeError("ToastHost children must be Toast instances.")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("ToastHost label must be a non-empty string.")
        return {
            "id": self._node_id(),
            "type": "toast_host",
            "label": self.label,
            "children": [toast.to_dict(register_event) for toast in self.toasts],
            **self._common_props(),
        }


class ToastQueue(Component):
    """A bounded toast host for application code that adds notifications over time."""

    def __init__(
        self,
        *,
        max_toasts: int = 5,
        label: str = "Notifications",
        **props: Any,
    ):
        super().__init__(**props)
        if isinstance(max_toasts, bool) or not isinstance(max_toasts, int) or not 1 <= max_toasts <= 20:
            raise ValueError("ToastQueue max_toasts must be an integer from 1 to 20.")
        if not isinstance(label, str) or not label.strip():
            raise ValueError("ToastQueue label must be a non-empty string.")
        self.max_toasts = max_toasts
        self.label = label.strip()
        self._counter = itertools.count(1)
        self._items: list[tuple[str, Toast]] = []
        self._lock = threading.RLock()

    def push(
        self,
        message: str,
        *,
        kind: str = "info",
        duration: int = 5000,
    ) -> str:
        toast_id = f"toast-{next(self._counter)}"
        toast = Toast(message, kind=kind, duration=duration, on_dismiss=lambda: self._remove(toast_id))
        toast.to_dict(lambda _callback: "unused")
        with self._lock:
            if len(self._items) == self.max_toasts:
                self._items.pop(0)
            self._items.append((toast_id, toast))
        return toast_id

    def _remove(self, toast_id: str) -> None:
        with self._lock:
            self._items = [(item_id, toast) for item_id, toast in self._items if item_id != toast_id]

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def dispose(self) -> None:
        self.clear()

    def iter_children(self) -> tuple[Component, ...]:
        return ()

    def to_dict(self, register_event):
        with self._lock:
            toasts = tuple(toast for _, toast in self._items)
        return {
            "id": self._node_id(),
            "type": "toast_host",
            "label": self.label,
            "children": [toast.to_dict(register_event) for toast in toasts],
            **self._common_props(),
        }


class _DialogAction:
    def __init__(self, dialog: Dialog, confirm: bool):
        self.dialog = dialog
        self.confirm = confirm

    def __call__(self) -> None:
        if not self.dialog.is_open:
            return
        self.dialog._open.value = False
        callback = self.dialog.on_confirm if self.confirm else self.dialog.on_cancel
        if callback is not None:
            try:
                callback()
            except Exception as exc:  # noqa: BLE001 - provide a safe UI failure for application callbacks.
                _logger.error("NovaUI dialog callback failed with %s", type(exc).__name__)
                self.dialog.status = "Action failed. Please try again."
                self.dialog._open.value = True


class Dialog(Component):
    """A native HTML dialog with separate confirm and cancel event handlers."""

    def __init__(
        self,
        title: str,
        child: Component,
        *,
        open: bool | State[bool] = False,
        on_confirm: Callable[[], Any] | None = None,
        on_cancel: Callable[[], Any] | None = None,
        confirm_label: str = "Confirm",
        cancel_label: str = "Cancel",
        **props: Any,
    ):
        super().__init__(**props)
        if not isinstance(title, str) or not title:
            raise ValueError("Dialog title must be a non-empty string.")
        if not isinstance(child, Component):
            raise TypeError("Dialog child must be a NovaUI Component.")
        if not isinstance(open, (bool, State)):
            raise TypeError("Dialog open must be a bool or State[bool].")
        if isinstance(open, State) and not isinstance(open.value, bool):
            raise TypeError("Dialog open state must contain a bool.")
        if on_confirm is not None and not callable(on_confirm):
            raise TypeError("Dialog on_confirm must be callable or None.")
        if on_cancel is not None and not callable(on_cancel):
            raise TypeError("Dialog on_cancel must be callable or None.")
        if not isinstance(confirm_label, str) or not confirm_label:
            raise ValueError("Dialog confirm_label must be a non-empty string.")
        if not isinstance(cancel_label, str) or not cancel_label:
            raise ValueError("Dialog cancel_label must be a non-empty string.")
        self.title = title
        self.child = child
        self._owns_state = not isinstance(open, State)
        self._open = open if isinstance(open, State) else state(open)
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.confirm_label = confirm_label
        self.cancel_label = cancel_label
        self.status = ""
        self._confirm_action = _DialogAction(self, True)
        self._cancel_action = _DialogAction(self, False)

    @property
    def is_open(self) -> bool:
        return self._open.value

    def iter_children(self) -> tuple[Component, ...]:
        return (self.child,)

    def dispose(self) -> None:
        if self._owns_state:
            self._open.dispose()

    def to_dict(self, register_event):
        if not isinstance(self._open.value, bool):
            raise TypeError("Dialog open state must contain a bool.")
        return {
            "id": self._node_id(),
            "type": "dialog",
            "title": self.title,
            "open": self.is_open,
            "confirm_label": self.confirm_label,
            "cancel_label": self.cancel_label,
            "status": self.status,
            "confirm_event_id": register_event(self._confirm_action),
            "cancel_event_id": register_event(self._cancel_action),
            "children": [self.child.to_dict(register_event)],
            **self._common_props(),
        }
