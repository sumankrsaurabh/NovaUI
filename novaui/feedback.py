"""Accessible alert, spinner, and confirmation-dialog components."""

from __future__ import annotations

import logging
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
        if self.kind not in {"info", "success", "warning", "error"}:
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
