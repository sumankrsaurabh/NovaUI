import novaui as ui


def test_field_validates_required_lengths_and_custom_validator():
    field = ui.Field(value="", required=True, min_length=3, validator=lambda value: "Invalid" if "!" in value else None)

    assert field.validate() == "This field is required."
    field.value = "ab"
    assert field.validate() == "Use at least 3 characters."
    field.value = "valid!"
    assert field.validate() == "Invalid"
    field.value = "valid"
    assert field.validate() is None


def test_form_blocks_invalid_submission_then_calls_callback_with_values():
    saved = []
    email = ui.Field(label="Email", input_type="email", required=True)
    password = ui.Field(label="Password", input_type="password", required=True, min_length=8)
    form = ui.Form(fields={"email": email, "password": password}, on_submit=saved.append)
    application = ui.App(form)

    tree = application.serialize_tree()["root"]
    application.dispatch_event(tree["submit_event_id"], {"email": "bad", "password": "short"})
    assert saved == []
    assert form.errors == {"email": "Enter a valid email address.", "password": "Use at least 8 characters."}
    assert form.status == "Please fix the highlighted fields."

    tree = application.serialize_tree()["root"]
    application.dispatch_event(tree["submit_event_id"], {"email": "user@example.com", "password": "long-enough"})
    assert saved == [{"email": "user@example.com", "password": "long-enough"}]
    assert form.status == "Submitted successfully."
    assert form.dirty_fields == {"email", "password"}
    assert form.to_dict(lambda _callback: "event")["error_summary"] == []


def test_form_supports_cross_field_validation_and_error_summary():
    form = ui.Form(
        fields={"password": ui.Field(), "confirm": ui.Field(label="Confirm password")},
        on_submit=lambda _values: None,
        validators={
            "confirm": lambda values: "Passwords do not match."
            if values["password"] != values["confirm"] else None,
        },
    )
    app = ui.App(form)
    tree = app.serialize_tree()["root"]
    app.dispatch_event(tree["submit_event_id"], {"password": "first", "confirm": "second"})
    assert form.errors == {"confirm": "Passwords do not match."}
    assert form.to_dict(lambda _callback: "event")["error_summary"] == [
        {"name": "confirm", "label": "Confirm password", "message": "Passwords do not match."}
    ]


def test_form_reset_restores_initial_values_and_clears_errors():
    field = ui.Field(value="initial", required=True)
    form = ui.Form(fields={"name": field}, on_submit=lambda _values: None)
    app = ui.App(form)
    tree = app.serialize_tree()["root"]
    app.dispatch_event(tree["submit_event_id"], {"name": ""})
    tree = app.serialize_tree()["root"]
    app.dispatch_event(tree["reset_event_id"])

    assert field.value == "initial"
    assert field.dirty is False
    assert form.errors == {}
    assert form.status == ""


def test_form_checks_numeric_ranges_and_reports_submit_errors_safely(caplog):
    amount = ui.Field(value="3", input_type="number", min_value=1, max_value=5)
    form = ui.Form(fields={"amount": amount}, on_submit=lambda _values: (_ for _ in ()).throw(RuntimeError("secret")))
    app = ui.App(form)
    event_id = app.serialize_tree()["root"]["submit_event_id"]
    app.dispatch_event(event_id, {"amount": "8"})
    assert form.errors["amount"] == "Enter a value no greater than 5."

    event_id = app.serialize_tree()["root"]["submit_event_id"]
    app.dispatch_event(event_id, {"amount": "4"})
    assert form.status == "Submission failed. Please try again."
    assert "secret" not in form.status
    assert "RuntimeError" in caplog.text
    assert "secret" not in caplog.text


def test_form_field_configuration_is_validated():
    import pytest

    with pytest.raises(ValueError, match="field name"):
        ui.Form(fields={"bad/name": ui.Field()}, on_submit=lambda _values: None)
    with pytest.raises(ValueError, match="min_length"):
        ui.Field(min_length=-1)
    with pytest.raises(ValueError, match="max_value"):
        ui.Field(input_type="number", min_value=5, max_value=2)


def test_form_awaits_async_submit_and_sets_safe_status():
    import asyncio

    calls = []

    async def save(values):
        await asyncio.sleep(0)
        calls.append(values)
        return "Saved asynchronously."

    form = ui.Form(fields={"name": ui.Field()}, on_submit=save)
    app = ui.App(form)
    event_id = app.serialize_tree()["root"]["submit_event_id"]
    app.dispatch_event(event_id, {"name": "Nova"})
    assert calls == [{"name": "Nova"}]
    assert form.status == "Saved asynchronously."


def test_form_reports_async_submit_errors_without_leaking_details(caplog):
    import asyncio

    async def save(_values):
        await asyncio.sleep(0)
        raise RuntimeError("private submission details")

    form = ui.Form(fields={"name": ui.Field()}, on_submit=save)
    app = ui.App(form)
    app.dispatch_event(app.serialize_tree()["root"]["submit_event_id"], {"name": "Nova"})
    assert form.status == "Submission failed. Please try again."
    assert "RuntimeError" in caplog.text
    assert "private submission details" not in caplog.text


def test_async_field_validation_cancels_superseded_work_and_keeps_latest_error():
    import asyncio

    async def scenario():
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def validate(value):
            if value == "slow":
                started.set()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    cancelled.set()
                    raise
            return "This name is taken." if value == "taken" else None

        field = ui.Field(async_validator=validate)
        previous = asyncio.create_task(field._on_change("slow"))
        await started.wait()
        field.value = "taken"
        latest = asyncio.create_task(field._on_change("taken"))

        await latest
        await previous
        assert cancelled.is_set()
        assert field.error == "This name is taken."

    asyncio.run(scenario())


def test_form_awaits_async_field_validation_before_submission():
    import asyncio

    submitted = []

    async def validate_username(value):
        await asyncio.sleep(0)
        return "Username is unavailable." if value == "taken" else None

    form = ui.Form(
        fields={"username": ui.Field(async_validator=validate_username)},
        on_submit=submitted.append,
    )
    app = ui.App(form)
    tree = app.serialize_tree()["root"]
    app.dispatch_event(tree["submit_event_id"], {"username": "taken"})
    assert submitted == []
    assert form.errors == {"username": "Username is unavailable."}
    assert form.status == "Please fix the highlighted fields."

    tree = app.serialize_tree()["root"]
    app.dispatch_event(tree["submit_event_id"], {"username": "available"})
    assert submitted == [{"username": "available"}]
    assert form.status == "Submitted successfully."
    app.dispose()
