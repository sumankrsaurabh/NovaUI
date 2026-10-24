import runpy
from pathlib import Path

import pytest

import novaui as ui
from novaui.state import state


def serialize(component):
    callbacks = {}

    def register(callback):
        event_id = f"event-{len(callbacks) + 1}"
        callbacks[event_id] = callback
        return event_id

    return component.to_dict(register), callbacks


def test_table_sorts_filters_searches_and_paginates():
    table = ui.DataTable(
        [ui.ColumnDef("name", title="Name"), ui.ColumnDef("age", title="Age")],
        [{"name": "Ari", "age": 30}, {"name": "Bea", "age": 20}, {"name": "Cal", "age": 40}],
        page_size=2,
    )
    tree, events = serialize(table)
    assert [row["cells"] for row in tree["rows"]] == [["Ari", "30"], ["Bea", "20"]]

    events[tree["columns"][1]["sort_event_id"]]()
    tree, events = serialize(table)
    assert [row["cells"][1] for row in tree["rows"]] == ["20", "30"]
    assert tree["columns"][1]["sort_direction"] == "asc"

    events[tree["columns"][1]["sort_event_id"]]()
    tree, events = serialize(table)
    assert [row["cells"][1] for row in tree["rows"]] == ["40", "30"]
    assert tree["columns"][1]["sort_direction"] == "desc"

    events[tree["next_event_id"]]()
    tree, events = serialize(table)
    assert tree["page"] == 2
    assert [row["cells"][0] for row in tree["rows"]] == ["Bea"]

    search = tree["search_event_id"]
    events[search]("bea")
    tree, _ = serialize(table)
    assert tree["total_rows"] == 1
    assert tree["rows"][0]["cells"][0] == "Bea"
    assert tree["page"] == 1


def test_table_selection_select_all_and_row_callback():
    selected_changes = []
    clicked = []
    table = ui.DataTable(
        [ui.ColumnDef("name")],
        [{"name": "Ada"}, {"name": "Lin"}],
        selectable=True,
        on_selection_change=selected_changes.append,
        on_row_click=clicked.append,
    )
    tree, events = serialize(table)
    events[tree["select_all_event_id"]]()
    tree, events = serialize(table)
    assert tree["selected_count"] == 2
    assert [row["name"] for row in selected_changes[-1]] == ["Ada", "Lin"]
    events[tree["rows"][0]["row_click_event_id"]]()
    assert clicked[-1] == {"name": "Ada"}
    events[tree["select_all_event_id"]]()
    assert serialize(table)[0]["selected_count"] == 0


def test_table_state_backing_refreshes_and_formatter_is_text():
    data = state([{"name": "<b>Ada</b>"}])
    table = ui.DataTable(
        [ui.ColumnDef("name", formatter=lambda value, row: value.upper())], data
    )
    assert serialize(table)[0]["rows"][0]["cells"][0] == "<B>ADA</B>"
    data.value = [{"name": "Grace"}]
    assert serialize(table)[0]["rows"][0]["cells"][0] == "GRACE"


def test_column_filter_and_row_action_callbacks():
    acted = []
    table = ui.DataTable(
        [ui.ColumnDef("name"), ui.ColumnDef("team")],
        [{"name": "Mina", "team": "Design"}, {"name": "Noah", "team": "Engineering"}],
        row_actions=[ui.RowAction("Open", lambda row: acted.append(row["name"]))],
    )
    tree, events = serialize(table)
    events[tree["columns"][1]["filter_event_id"]]("design")
    tree, events = serialize(table)
    assert [row["cells"][0] for row in tree["rows"]] == ["Mina"]
    events[tree["rows"][0]["actions"][0]["event_id"]]()
    assert acted == ["Mina"]


def test_table_filter_event_dispatch_uses_registered_value_handler():
    table = ui.DataTable([ui.ColumnDef("name")], [{"name": "Nora"}, {"name": "Omar"}])
    application = ui.App(table)
    tree = application.serialize_tree()["root"]
    application.dispatch_event(tree["search_event_id"], "omar")
    assert application.serialize_tree()["root"]["rows"][0]["cells"][0] == "Omar"
    application.dispose()


def test_table_empty_and_loading_states():
    tree, _ = serialize(ui.DataTable([ui.ColumnDef("name")], [], loading=True))
    assert tree["loading"] is True
    assert tree["rows"] == []
    assert tree["empty_message"] == "No data available."


@pytest.mark.parametrize(
    "columns,data,options",
    [
        ([], [], {}),
        ([ui.ColumnDef("name"), ui.ColumnDef("name")], [], {}),
        ([ui.ColumnDef("missing")], [{"name": "Ada"}], {}),
        ([ui.ColumnDef("id"), ui.ColumnDef("name")], [{"id": 1, "name": "A"}, {"id": 1, "name": "B"}], {"row_key": "id"}),
        ([ui.ColumnDef("name", width="wide")], [{"name": "Ada"}], {}),
        ([ui.ColumnDef("name")], [{"name": "Ada"}], {"page_size": 0}),
        ([ui.ColumnDef("name")], [{"name": "Ada"}], {"selectable": 1}),
    ],
)
def test_table_rejects_invalid_definitions(columns, data, options):
    with pytest.raises((TypeError, ValueError)):
        serialize(ui.DataTable(columns, data, **options))


def test_employee_table_example_uses_working_component_api(monkeypatch):
    root = {}

    def capture(component, **kwargs):
        root["tree"] = component.to_dict(lambda callback: "event")
        root["title"] = kwargs["title"]

    monkeypatch.setattr(ui, "app", capture)
    example = Path(__file__).parents[1] / "examples" / "employee_table.py"
    runpy.run_path(str(example), run_name="__main__")
    table = root["tree"]["children"][2]
    assert table["type"] == "data_table"
    assert table["total_rows"] == 4
    assert root["title"] == "Employee Directory"
