"""Small mutable state primitive for the NovaUI MVP."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Generic, TypeVar

T = TypeVar("T")
_active_dependencies: ContextVar[set[Any] | None] = ContextVar("novaui_dependencies", default=None)
_preview_states: ContextVar[tuple[dict[str, State[Any]], set[str]] | None] = ContextVar(
    "novaui_preview_states", default=None
)


class State(Generic[T]):
    """Mutable value with subscriptions and an explicit disposal boundary.

    Disposing a state releases its listeners. Reads remain available, while
    updates and new subscriptions fail so stale references are easy to spot.
    """

    def __init__(self, value: T):
        self._value = value
        self._listeners: list[Callable[[T], Any]] = []
        self._disposed = False

    @property
    def value(self) -> T:
        dependencies = _active_dependencies.get()
        if dependencies is not None:
            dependencies.add(self)
        return self._value

    @value.setter
    def value(self, value: T) -> None:
        self.update(value)

    def update(self, value: T) -> None:
        self._ensure_active()
        if value == self._value:
            return
        self._value = value
        failure: Exception | None = None
        for listener in tuple(self._listeners):
            try:
                listener(value)
            except Exception as exc:  # noqa: BLE001 - notify all listeners before reporting failure.
                if failure is None:
                    failure = exc
        if failure is not None:
            raise RuntimeError("A State subscriber failed after the value was updated.") from failure

    def subscribe(self, listener: Callable[[T], Any]) -> Callable[[], None]:
        self._ensure_active()
        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    @property
    def is_disposed(self) -> bool:
        return self._disposed

    def dispose(self) -> None:
        """Release all subscriptions; safe to call more than once."""
        if self._disposed:
            return
        self._disposed = True
        self._listeners.clear()

    def _ensure_active(self) -> None:
        if self._disposed:
            raise RuntimeError("State has been disposed and can no longer be used.")


@contextmanager
def track_dependencies() -> Iterator[set[State[Any]]]:
    """Collect State values read while computing a component property."""
    dependencies: set[State[Any]] = set()
    token = _active_dependencies.set(dependencies)
    try:
        yield dependencies
    finally:
        _active_dependencies.reset(token)


def state(value: T) -> State[T]:
    return State(value)


@contextmanager
def preview_state_scope(states: dict[str, State[Any]], used: set[str]) -> Iterator[None]:
    """Select the explicit state store used by one preview render."""
    token = _preview_states.set((states, used))
    try:
        yield
    finally:
        _preview_states.reset(token)


def preview_state(key: str, initial: T) -> State[T]:
    """Return a preview-local state value preserved across compatible reloads.

    This is available only while NovaUI is invoking a selected preview. Ordinary
    ``state()`` values retain their normal construction and reset semantics.
    """
    if not isinstance(key, str) or not key.strip() or len(key) > 120:
        raise ValueError("Preview state key must be a non-empty string of at most 120 characters.")
    active = _preview_states.get()
    if active is None:
        raise RuntimeError("preview_state() can only be used inside a rendered @ui.preview function.")
    states, used = active
    key = key.strip()
    used.add(key)
    existing = states.get(key)
    if existing is not None and type(existing.value) is type(initial) and not existing.is_disposed:
        return existing  # type: ignore[return-value]
    replacement = State(initial)
    states[key] = replacement
    return replacement
