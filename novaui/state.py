"""Small mutable state primitive for the NovaUI MVP."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Generic, Literal, TypeVar

T = TypeVar("T")
AsyncStatus = Literal["idle", "loading", "success", "error"]
_logger = logging.getLogger(__name__)
_active_dependencies: ContextVar[set[Any] | None] = ContextVar("novaui_dependencies", default=None)
_pending_updates: ContextVar[dict[State[Any], Any] | None] = ContextVar(
    "novaui_pending_updates", default=None
)
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
        pending = _pending_updates.get()
        if pending is not None:
            pending[self] = value
            return
        self._notify(value)

    def _notify(self, value: T) -> None:
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


class AsyncState(Generic[T]):
    """Observable loading/value/error state for a replaceable async operation."""

    def __init__(self):
        self._status: State[AsyncStatus] = State("idle")
        self._value: State[T | None] = State(None)
        self._error: State[str | None] = State(None)
        self._generation = 0
        self._task: asyncio.Future[T] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._disposed = False

    @property
    def status(self) -> AsyncStatus:
        return self._status.value

    @property
    def value(self) -> T | None:
        return self._value.value

    @property
    def error(self) -> str | None:
        return self._error.value

    async def run(self, operation: Awaitable[T]) -> T | None:
        """Run an awaitable, cancelling the previous run and exposing its status."""
        if self._disposed:
            if asyncio.iscoroutine(operation):
                operation.close()
            raise RuntimeError("AsyncState has been disposed and cannot run new operations.")
        if not hasattr(operation, "__await__"):
            raise TypeError("AsyncState.run expects an awaitable operation.")
        previous = self._task
        if previous is not None and not previous.done():
            previous.cancel()
        self._generation += 1
        generation = self._generation
        self._status.value = "loading"
        self._error.value = None
        self._loop = asyncio.get_running_loop()
        task = asyncio.ensure_future(operation)
        self._task = task
        try:
            result = await task
        except asyncio.CancelledError:
            if generation == self._generation and not self._disposed:
                self._status.value = "error"
                self._error.value = "Operation was cancelled."
            raise
        except Exception as exc:  # noqa: BLE001 - expose a safe error state for arbitrary awaitables.
            if generation == self._generation and not self._disposed:
                _logger.error("NovaUI async state operation failed with %s", type(exc).__name__)
                self._status.value = "error"
                self._error.value = "Operation failed. Please try again."
            return None
        else:
            if generation == self._generation and not self._disposed:
                self._value.value = result
                self._status.value = "success"
                return result
            return None
        finally:
            if self._task is task:
                self._task = None

    def cancel(self) -> None:
        """Cancel the active operation and prevent it from publishing a result."""
        task, loop = self._task, self._loop
        if task is None or task.done() or loop is None:
            return
        self._generation += 1
        loop.call_soon_threadsafe(task.cancel)
        if not self._disposed:
            self._status.value = "error"
            self._error.value = "Operation was cancelled."

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        self.cancel()
        self._status.dispose()
        self._value.dispose()
        self._error.dispose()


@contextmanager
def batch() -> Iterator[None]:
    """Defer State notifications and emit each changed State's latest value once."""
    pending = _pending_updates.get()
    if pending is not None:
        yield
        return

    pending = {}
    token = _pending_updates.set(pending)
    try:
        yield
    finally:
        _pending_updates.reset(token)
        failure: RuntimeError | None = None
        for value_state, value in pending.items():
            try:
                value_state._notify(value)
            except RuntimeError as exc:
                if failure is None:
                    failure = exc
        if failure is not None:
            raise failure


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
