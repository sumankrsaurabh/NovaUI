from novaui import state


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
