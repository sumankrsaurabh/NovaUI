import pytest

import novaui as ui


def serialize(component):
    events = {}

    def register(callback):
        event_id = f"event-{len(events) + 1}"
        events[event_id] = callback
        return event_id

    return component.to_dict(register), events


def test_command_palette_serializes_registered_commands_and_dispatches():
    executed = []
    palette = ui.CommandPalette([
        ui.Command("Save file", lambda: executed.append("save"), keywords=("write",), shortcut="Ctrl+S"),
        ui.Command("Open file", lambda: executed.append("open")),
    ])
    tree, events = serialize(palette)
    assert tree["type"] == "command_palette"
    assert tree["commands"][0]["keywords"] == ["write"]
    events[tree["commands"][1]["event_id"]]()
    assert executed == ["open"]


def test_tree_view_expands_branches_and_selects_nodes():
    selected = []
    view = ui.TreeView([
        ui.TreeNode(
            "src",
            children=[ui.TreeNode("app.py", key="app", on_select=selected.append)],
            key="src",
        )
    ])
    tree, events = serialize(view)
    source = tree["nodes"][0]
    assert source["expanded"] is False
    events[source["toggle_event_id"]]()
    tree, events = serialize(view)
    source = tree["nodes"][0]
    assert source["expanded"] is True
    events[source["children"][0]["select_event_id"]]()
    assert selected[0].label == "app.py"


def test_toolbar_and_status_bar_are_semantic_child_components():
    toolbar = ui.Toolbar(ui.Button("Save"), label="File actions")
    status = ui.StatusBar(ui.Text("Ready"), label="Application status")
    toolbar_tree, _ = serialize(toolbar)
    status_tree, _ = serialize(status)
    assert toolbar_tree["type"] == "toolbar"
    assert toolbar_tree["children"][0]["type"] == "button"
    assert status_tree["type"] == "status_bar"
    assert status_tree["children"][0]["text"] == "Ready"


def test_toast_can_be_dismissed_and_calls_cleanup_callback():
    dismissed = []
    toast = ui.Toast("Saved", kind="success", duration=0, on_dismiss=lambda: dismissed.append(True))
    tree, events = serialize(toast)
    assert tree["duration"] == 0
    events[tree["dismiss_event_id"]]()
    tree, _ = serialize(toast)
    assert tree["visible"] is False
    assert dismissed == [True]


def test_toast_host_requires_toast_children_and_validates_duration():
    with pytest.raises(TypeError, match="Toast"):
        serialize(ui.ToastHost(ui.Text("Not a toast")))
    with pytest.raises(ValueError, match="duration"):
        serialize(ui.Toast("Saved", duration=-1))


@pytest.mark.parametrize(
    "component",
    [
        ui.CommandPalette([ui.Command("", lambda: None)]),
        ui.TreeView([ui.TreeNode("Duplicate", key="same"), ui.TreeNode("Duplicate", key="same")]),
        ui.Toolbar(ui.Text("Invalid"), orientation="diagonal"),
    ],
)
def test_productivity_components_validate_definitions(component):
    with pytest.raises((TypeError, ValueError)):
        serialize(component)
