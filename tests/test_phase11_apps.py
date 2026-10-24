from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.phase11_admin.app import AdminModel, create_application
from examples.phase11_pyoffice.app import (
    MAX_LINES,
    parse_document,
    read_document,
    serialize_document,
    write_document,
)
from examples.phase11_pyoffice.app import (
    build_app as build_pyoffice,
)
from examples.phase11_studio.app import CATALOGUE
from examples.phase11_studio.app import build_app as build_studio
from examples.phase11_studio.app import run_app as run_studio


def find_node(node: dict[str, Any], node_type: str) -> dict[str, Any] | None:
    if node.get("type") == node_type:
        return node
    for child in node.get("children", []):
        found = find_node(child, node_type)
        if found:
            return found
    for tab in node.get("tabs", []):
        if tab.get("type") == node_type:
            return tab
    return None


def test_studio_catalogue_is_bounded_and_previews_registered_components():
    app = build_studio()
    try:
        tree = app.serialize_tree()
        table = find_node(tree["root"], "data_table")
        assert table is not None
        assert {row["cells"][0] for row in table["rows"]} == set(CATALOGUE)
        tabs = find_node(tree["root"], "tabs")
        assert tabs is not None and tabs["selected"] == "Text"
        assert all(isinstance(entry["code"], str) for entry in CATALOGUE.values())
        assert CATALOGUE["Text"]["properties"].startswith("Text(")
        for entry in CATALOGUE.values():
            preview = entry["preview"]()
            assert preview.to_dict(lambda callback: "preview-event")["type"]
    finally:
        app.dispose()


def test_studio_row_selection_updates_preview_and_theme_toggle():
    app = build_studio()
    try:
        tree = app.serialize_tree()
        table = find_node(tree["root"], "data_table")
        assert table
        row_event = table["rows"][1]["row_click_event_id"]
        app.dispatch_event(row_event)
        tree = app.serialize_tree()
        tabs = find_node(tree["root"], "tabs")
        assert tabs and tabs["selected"] == "Button"

        toggle = next(
            node["event_id"]
            for node in walk(tree["root"])
            if node.get("type") == "button" and node.get("label") == "Toggle theme"
        )
        app.dispatch_event(toggle)
        assert app.serialize_tree()["theme"]["mode"] == "dark"
    finally:
        app.dispose()


def test_studio_search_and_category_controls_filter_catalogue():
    app = build_studio()
    try:
        tree = app.serialize_tree()
        input_node = next(node for node in walk(tree["root"]) if node.get("type") == "input")
        app.dispatch_event(input_node["event_id"], "data")
        table = find_node(app.serialize_tree()["root"], "data_table")
        assert table and [row["cells"][0] for row in table["rows"]] == ["DataTable"]

        tree = app.serialize_tree()
        input_node = next(node for node in walk(tree["root"]) if node.get("type") == "input")
        app.dispatch_event(input_node["event_id"], "")
        tree = app.serialize_tree()
        layouts_button = next(
            node for node in walk(tree["root"])
            if node.get("type") == "button" and node.get("label") == "Layouts"
        )
        app.dispatch_event(layouts_button["event_id"])
        table = find_node(app.serialize_tree()["root"], "data_table")
        assert table
        assert {row["cells"][0] for row in table["rows"]} == {"Row", "Column", "Card", "Grid"}
    finally:
        app.dispose()


def test_studio_entrypoint_passes_desktop_and_server_options(monkeypatch):
    calls = {}

    class FakeApp:
        def run(self, *, desktop, open_browser):
            calls["run"] = (desktop, open_browser)

    def fake_build_app(**options):
        calls["build"] = options
        return FakeApp()

    monkeypatch.setattr("examples.phase11_studio.app.build_app", fake_build_app)
    run_studio(["--desktop", "--host", "127.0.0.1", "--port", "8123", "--no-browser", "--debug"])
    assert calls == {
        "build": {"host": "127.0.0.1", "port": 8123, "debug": True},
        "run": (True, False),
    }


def walk(node: dict[str, Any]):
    yield node
    for child in node.get("children", []):
        yield from walk(child)


def test_admin_routes_entry_validation_table_update_and_delete_confirmation():
    app, model = create_application()
    try:
        assert app.serialize_tree()["root"]["path"] == "/"
        app.navigate("/entry")
        form_node = find_node(app.serialize_tree()["root"], "form")
        assert form_node
        app.dispatch_event(form_node["submit_event_id"], {"name": "", "team": ""})
        invalid = find_node(app.serialize_tree()["root"], "form")
        assert invalid and invalid["status"] == "Please fix the highlighted fields."
        assert len(model.records.value) == 7

        app.dispatch_event(invalid["submit_event_id"], {"name": "Avery Stone", "team": "Research"})
        assert len(model.records.value) == 8
        assert model.records.value[-1]["name"] == "Avery Stone"

        app.navigate("/records")
        table = find_node(app.serialize_tree()["root"], "data_table")
        assert table and table["total_rows"] == 8 and table["page_count"] == 2
        remove_event = table["rows"][0]["actions"][0]["event_id"]
        app.dispatch_event(remove_event)
        dialog = find_node(app.serialize_tree()["root"], "dialog")
        assert dialog and dialog["open"] is True
        app.dispatch_event(dialog["confirm_event_id"])
        assert len(model.records.value) == 7
        assert find_node(app.serialize_tree()["root"], "dialog")["open"] is False

        app.navigate("/reports")
        assert app.serialize_tree()["root"]["path"] == "/reports"
        app.navigate("/missing")
        texts = [node["text"] for node in walk(app.serialize_tree()["root"]) if node.get("type") == "text"]
        assert "404 — Page not found" in texts
    finally:
        app.dispose()


def test_admin_model_rejects_invalid_records():
    model = AdminModel([])
    with pytest.raises(ValueError, match="required"):
        model.add({"name": "", "team": ""})
    assert model.records.value == []


def test_pyoffice_round_trips_local_utf8_document(tmp_path: Path):
    destination = tmp_path / "notes.txt"
    lines = parse_document("First line\nदूसरी पंक्ति\n\n")
    assert len(lines) == MAX_LINES
    write_document(destination, lines)
    assert read_document(destination) == lines
    assert serialize_document(lines) == "First line\nदूसरी पंक्ति"


def test_pyoffice_rejects_over_limit_and_invalid_documents():
    with pytest.raises(ValueError, match="at most 12 lines"):
        parse_document("\n".join(str(number) for number in range(MAX_LINES + 1)))
    with pytest.raises(ValueError, match="exactly 12"):
        serialize_document(["only one"])


def test_pyoffice_tree_exposes_shortcuts_without_starting_gui():
    app = build_pyoffice()
    try:
        tree = app.serialize_tree()
        assert {shortcut["key"] for shortcut in tree["shortcuts"]} == {"Mod+O", "Mod+S"}
        assert find_node(tree["root"], "input") is not None
    finally:
        app.dispose()
