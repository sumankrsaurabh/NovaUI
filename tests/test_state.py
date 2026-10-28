import asyncio

import pytest

from novaui import AsyncState, batch, state


def test_state_update_and_subscription():
    value = state(1)
    observed = []
    unsubscribe = value.subscribe(observed.append)
    value.update(2)
    assert value.value == 2
    assert observed == [2]
    unsubscribe()
    value.update(3)
    assert observed == [2]


def test_dispose_releases_subscribers_and_is_idempotent():
    value = state(1)
    observed = []
    unsubscribe = value.subscribe(observed.append)

    value.dispose()
    value.dispose()
    unsubscribe()

    assert value.value == 1
    assert observed == []


def test_disposed_state_rejects_updates_and_new_subscriptions():
    value = state(1)
    value.dispose()

    import pytest

    with pytest.raises(RuntimeError, match="disposed"):
        value.update(2)
    with pytest.raises(RuntimeError, match="disposed"):
        value.subscribe(lambda _: None)


def test_state_update_notifies_all_subscribers_then_reports_failure():
    value = state(1)
    observed = []

    def fail(_new_value):
        raise ValueError("listener failed")

    value.subscribe(fail)
    value.subscribe(observed.append)

    import pytest

    with pytest.raises(RuntimeError, match="subscriber failed"):
        value.update(2)

    assert value.value == 2
    assert observed == [2]


def test_batch_defers_and_coalesces_nested_state_updates():
    first = state(1)
    second = state("before")
    observed = []
    first.subscribe(lambda value: observed.append(("first", value)))
    second.subscribe(lambda value: observed.append(("second", value)))

    with batch():
        first.update(2)
        with batch():
            first.update(3)
            second.value = "after"
        assert observed == []
        assert first.value == 3

    assert observed == [("first", 3), ("second", "after")]


def test_batch_notifies_remaining_states_before_reporting_subscriber_failure():
    def fail(_value):
        raise ValueError("listener failed")

    first = state(1)
    second = state(1)
    observed = []
    first.subscribe(fail)
    second.subscribe(observed.append)

    import pytest

    with pytest.raises(RuntimeError, match="subscriber failed"), batch():
        first.update(2)
        second.update(2)

    assert second.value == 2
    assert observed == [2]


def test_batch_flushes_state_notifications_when_body_raises():
    value = state(1)
    observed = []
    value.subscribe(observed.append)

    with pytest.raises(ValueError, match="operation failed"), batch():
        value.update(2)
        raise ValueError("operation failed")

    assert observed == [2]


def test_async_state_tracks_success_and_sanitized_failure():
    async def scenario():
        value = AsyncState()
        assert value.status == "idle"
        assert await value.run(asyncio.sleep(0, result="ready")) == "ready"
        assert value.value == "ready"
        assert value.status == "success"

        async def fail():
            raise RuntimeError("private details")

        assert await value.run(fail()) is None
        assert value.status == "error"
        assert value.error == "Operation failed. Please try again."

    asyncio.run(scenario())


def test_async_state_cancels_superseded_work_without_stale_results():
    async def scenario():
        value = AsyncState()
        started = asyncio.Event()

        async def slow():
            started.set()
            await asyncio.Event().wait()

        previous = asyncio.create_task(value.run(slow()))
        await started.wait()
        assert await value.run(asyncio.sleep(0, result=2)) == 2
        with pytest.raises(asyncio.CancelledError):
            await previous
        assert value.value == 2
        assert value.status == "success"

    asyncio.run(scenario())


def test_async_state_explicit_cancel_updates_status():
    async def scenario():
        value = AsyncState()
        started = asyncio.Event()

        async def slow():
            started.set()
            await asyncio.Event().wait()

        operation = asyncio.create_task(value.run(slow()))
        await started.wait()
        value.cancel()
        with pytest.raises(asyncio.CancelledError):
            await operation
        assert value.status == "error"
        assert value.error == "Operation was cancelled."

    asyncio.run(scenario())


def test_async_state_dispose_cancels_without_updating_disposed_state():
    async def scenario():
        value = AsyncState()
        started = asyncio.Event()

        async def slow():
            started.set()
            await asyncio.Event().wait()

        operation = asyncio.create_task(value.run(slow()))
        await started.wait()
        value.dispose()
        with pytest.raises(asyncio.CancelledError):
            await operation
        assert value.status == "loading"
        with pytest.raises(RuntimeError, match="disposed"):
            await value.run(asyncio.sleep(0))

    asyncio.run(scenario())
