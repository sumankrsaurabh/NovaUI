import csv
import io
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


def test_column_visibility_retains_one_column_and_hides_cells():
    table = ui.DataTable(
        [ui.ColumnDef("name"), ui.ColumnDef("team")],
        [{"name": "Mina", "team": "Design"}],
        column_visibility=True,
    )
    tree, events = serialize(table)
    team_toggle = next(item for item in tree["column_controls"] if item["key"] == "team")
    events[team_toggle["event_id"]]()
    tree, events = serialize(table)
    assert [column["key"] for column in tree["columns"]] == ["name"]
    assert tree["rows"][0]["cells"] == ["Mina"]
    name_toggle = next(item for item in tree["column_controls"] if item["key"] == "name")
    assert name_toggle["event_id"] is None


def test_csv_export_escapes_cells_and_exports_filtered_rows_not_only_page():
    table = ui.DataTable(
        [ui.ColumnDef("name", title="=Name"), ui.ColumnDef("note")],
        [{"name": "=1+1", "note": 'comma, quote " and newline\n'},
         {"name": " \t=SUM(1,2)", "note": "Formula-like value"},
         {"name": "Ari", "note": "Second row"}],
        page_size=1,
        exportable=True,
    )
    tree, events = serialize(table)
    events[tree["export_event_id"]]()
    exported, _ = serialize(table)
    rows = list(csv.reader(io.StringIO(exported["export_csv"])))
    assert rows == [
        ["'=Name", "Note"],
        ["'=1+1", 'comma, quote " and newline\n'],
        ["' \t=SUM(1,2)", "Formula-like value"],
        ["Ari", "Second row"],
    ]


def test_bulk_action_receives_selected_rows_and_mobile_layout_is_configurable():
    selected = []
    table = ui.DataTable(
        [ui.ColumnDef("name")],
        [{"name": "Mina"}, {"name": "Noah"}],
        selectable=True,
        bulk_actions=[ui.BulkAction("Archive", selected.append)],
        mobile_layout="table",
    )
    tree, events = serialize(table)
    events[tree["rows"][1]["select_event_id"]]()
    tree, events = serialize(table)
    assert tree["mobile_layout"] == "table"
    events[tree["bulk_actions"][0]["event_id"]]()
    assert selected == [[{"name": "Noah"}]]


def test_data_grid_edits_state_and_supports_undo_redo():
    rows = ui.state([{"name": "Ari"}, {"name": "Bea"}])
    changes = []
    grid = ui.DataGrid([ui.ColumnDef("name")], rows, on_change=changes.append)
    tree, events = serialize(grid)
    events[tree["rows"][0]["cells"][0]["event_id"]]("Ari edited")
    assert rows.value == [{"name": "Ari edited"}, {"name": "Bea"}]
    assert changes[-1] == rows.value

    tree, events = serialize(grid)
    assert tree["rows"][0]["cells"][0]["value"] == "Ari edited"
    events[tree["undo_event_id"]]()
    assert rows.value[0]["name"] == "Ari"

    tree, events = serialize(grid)
    events[tree["redo_event_id"]]()
    assert rows.value[0]["name"] == "Ari edited"


def test_data_grid_clears_stale_history_after_external_data_change():
    rows = ui.state([{"name": "Ari"}])
    grid = ui.DataGrid([ui.ColumnDef("name")], rows)
    tree, events = serialize(grid)
    events[tree["rows"][0]["cells"][0]["event_id"]]("Ari edited")
    rows.value = [{"name": "Bea"}]

    tree, events = serialize(grid)
    with pytest.raises(ValueError, match="underlying data changed"):
        events[tree["undo_event_id"]]()
    assert serialize(grid)[0]["undo_event_id"] is None


def test_data_grid_keeps_undo_history_when_change_callback_fails():
    calls = 0

    def fail(_rows):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("application callback failed")

    grid = ui.DataGrid([ui.ColumnDef("name")], [{"name": "Ari"}], on_change=fail)
    tree, events = serialize(grid)
    with pytest.raises(RuntimeError, match="callback failed"):
        events[tree["rows"][0]["cells"][0]["event_id"]]("Ari edited")
    tree, events = serialize(grid)
    events[tree["undo_event_id"]]()
    assert serialize(grid)[0]["rows"][0]["cells"][0]["value"] == "Ari"


def test_data_grid_rejects_irreversible_formatter_on_editable_column():
    grid = ui.DataGrid(
        [ui.ColumnDef("amount", formatter=lambda value, row: f"${value}")],
        [{"amount": 10}],
    )
    with pytest.raises(ValueError, match="cannot use formatters"):
        serialize(grid)


def test_data_grid_pastes_rectangular_text_and_undoes_each_cell():
    rows = ui.state([{"name": "Ari", "team": "Design"}, {"name": "Bea", "team": "Data"}])
    changes = []
    grid = ui.DataGrid(
        [ui.ColumnDef("name"), ui.ColumnDef("team")],
        rows,
        on_change=changes.append,
    )
    tree, events = serialize(grid)

    events[tree["rows"][0]["cells"][0]["paste_event_id"]]("Ari A\tEngineering\nBea B\tResearch")

    assert rows.value == [
        {"name": "Ari A", "team": "Engineering"},
        {"name": "Bea B", "team": "Research"},
    ]
    assert changes == [rows.value]
    for _ in range(4):
        tree, events = serialize(grid)
        events[tree["undo_event_id"]]()
    assert rows.value == [{"name": "Ari", "team": "Design"}, {"name": "Bea", "team": "Data"}]
    for _ in range(4):
        tree, events = serialize(grid)
        events[tree["redo_event_id"]]()
    assert rows.value == [
        {"name": "Ari A", "team": "Engineering"},
        {"name": "Bea B", "team": "Research"},
    ]


@pytest.mark.parametrize(
    "paste, column_index, message",
    [
        ("one\ttwo\nthree", 0, "rectangular"),
        ("one\ttwo", 1, "beyond"),
    ],
)
def test_data_grid_rejects_invalid_paste_without_partial_changes(paste, column_index, message):
    rows = ui.state([{"name": "Ari", "team": "Design"}])
    grid = ui.DataGrid([ui.ColumnDef("name"), ui.ColumnDef("team")], rows)
    tree, events = serialize(grid)
    with pytest.raises(ValueError, match=message):
        events[tree["rows"][0]["cells"][column_index]["paste_event_id"]](paste)
    assert rows.value == [{"name": "Ari", "team": "Design"}]


def test_data_grid_paste_checks_json_encoded_transport_size():
    grid = ui.DataGrid([ui.ColumnDef("name")], [{"name": "Ari"}])
    tree, events = serialize(grid)
    with pytest.raises(ValueError, match="16 KiB"):
        events[tree["rows"][0]["cells"][0]["paste_event_id"]]("\x00" * 3000)


def test_data_grid_static_data_edits_and_restricts_editable_columns():
    grid = ui.DataGrid(
        [ui.ColumnDef("name"), ui.ColumnDef("team")],
        [{"name": "Mina", "team": "Design"}],
        editable_columns=["team"],
    )
    tree, events = serialize(grid)
    assert tree["rows"][0]["cells"][0]["editable"] is False
    assert tree["rows"][0]["cells"][1]["editable"] is True
    events[tree["rows"][0]["cells"][1]["event_id"]]("Product")
    tree, _ = serialize(grid)
    assert tree["rows"][0]["cells"][1]["value"] == "Product"


@pytest.mark.parametrize(
    "columns,data,options",
    [
        ([], [], {}),
        ([ui.ColumnDef("missing")], [{"name": "Ari"}], {}),
        ([ui.ColumnDef("name")], [{"name": "Ari"}], {"editable": 1}),
        ([ui.ColumnDef("name")], [{"name": "Ari"}], {"editable_columns": ["team"]}),
    ],
)
def test_data_grid_rejects_invalid_definitions(columns, data, options):
    with pytest.raises((TypeError, ValueError)):
        serialize(ui.DataGrid(columns, data, **options))


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
