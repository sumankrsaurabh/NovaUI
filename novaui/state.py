"""Small mutable state primitive for the NovaUI MVP."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Generic, TypeVar

T = TypeVar("T")
_active_dependencies: ContextVar[set[Any] | None] = ContextVar("novaui_dependencies", default=None)


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
