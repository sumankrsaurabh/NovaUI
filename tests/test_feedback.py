import novaui as ui


def test_alert_spinner_and_dialog_serialize_for_frontend():
    app = ui.App(ui.Column(
        ui.Alert("Saved", kind="success"),
        ui.Spinner("Loading records"),
        ui.Dialog("Confirm", ui.Text("Continue?")),
    ))
    children = app.serialize_tree()["root"]["children"]
    assert children[0]["type"] == "alert"
    assert children[0]["kind"] == "success"
    assert children[1]["type"] == "spinner"
    assert children[2]["type"] == "dialog"
    assert children[2]["open"] is False


def test_dialog_cancel_and_confirm_use_separate_callbacks():
    calls = []
    dialog = ui.Dialog(
        "Delete item?", ui.Text("This cannot be undone."), open=True,
        on_confirm=lambda: calls.append("confirm"),
        on_cancel=lambda: calls.append("cancel"),
    )
    app = ui.App(dialog)
    tree = app.serialize_tree()["root"]
    app.dispatch_event(tree["cancel_event_id"])
    assert calls == ["cancel"]
    assert dialog.is_open is False

    dialog._open.value = True
    tree = app.serialize_tree()["root"]
    app.dispatch_event(tree["confirm_event_id"])
    assert calls == ["cancel", "confirm"]
    assert dialog.is_open is False


def test_closed_dialog_ignores_stale_action_and_callback_failure_is_safe(caplog):
    calls = []
    dialog = ui.Dialog("Confirm", ui.Text("Proceed?"), on_confirm=lambda: calls.append("confirm"))
    app = ui.App(dialog)
    event_id = app.serialize_tree()["root"]["confirm_event_id"]
    app.dispatch_event(event_id)
    assert calls == []

    dialog._open.value = True
    dialog.on_confirm = lambda: (_ for _ in ()).throw(RuntimeError("private detail"))
    event_id = app.serialize_tree()["root"]["confirm_event_id"]
    app.dispatch_event(event_id)
    assert dialog.status == "Action failed. Please try again."
    assert dialog.is_open
    assert "private detail" not in caplog.text


def test_tabs_selects_panel_and_releases_owned_state():
    tabs = ui.Tabs({"General": ui.Text("General panel"), "Privacy": ui.Text("Privacy panel")})
    app = ui.App(tabs)
    tree = app.serialize_tree()["root"]
    privacy_event = tree["tabs"][1]["event_id"]
    app.dispatch_event(privacy_event)
    updated = app.serialize_tree()["root"]
    assert tabs.selected == "Privacy"
    assert updated["children"][0]["text"] == "Privacy panel"
    selected_state = tabs._selected
    app.dispose()
    assert selected_state.is_disposed
