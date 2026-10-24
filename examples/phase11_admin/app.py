"""A small routed administration app backed by in-memory sample records."""

from __future__ import annotations

from typing import Any

import novaui as ui
from examples.phase11_design import DARK, LIGHT, MUTED


class AdminModel:
    """App-local sample data. Records intentionally reset when the process exits."""

    def __init__(self, records: list[dict[str, Any]] | None = None):
        initial = records if records is not None else [
            {"id": 1, "name": "Mira Patel", "team": "Platform", "status": "Active"},
            {"id": 2, "name": "Jon Bell", "team": "Design", "status": "Active"},
            {"id": 3, "name": "Sam Lee", "team": "Operations", "status": "Review"},
            {"id": 4, "name": "Noah Chen", "team": "Platform", "status": "Active"},
            {"id": 5, "name": "Amara Okafor", "team": "Research", "status": "Active"},
            {"id": 6, "name": "Elena Rossi", "team": "Design", "status": "Review"},
            {"id": 7, "name": "Theo Martin", "team": "Operations", "status": "Active"},
        ]
        self.records: ui.State[list[dict[str, Any]]] = ui.state(initial)
        self._next_id = max((row["id"] for row in initial), default=0) + 1

    def add(self, values: dict[str, str]) -> str:
        name, team = values.get("name", "").strip(), values.get("team", "").strip()
        if len(name) < 2 or not team:
            raise ValueError("A name and team are required.")
        self.records.value = [
            *self.records.value,
            {"id": self._next_id, "name": name, "team": team, "status": "Active"},
        ]
        self._next_id += 1
        return f"Added {name}."

    def delete(self, record_id: int) -> None:
        self.records.value = [row for row in self.records.value if row["id"] != record_id]


def _page_shell(title: str, active_path: str, content: ui.Component, app_ref: dict[str, ui.App]) -> ui.Component:
    def toggle_theme():
        current = app_ref["app"].theme
        app_ref["app"].set_theme(DARK if getattr(current, "mode", current) == "light" else LIGHT)

    return ui.AppShell(
        ui.Sidebar(
            ui.Text("NOVAUI ADMIN", size=12, bold=True, color=MUTED),
            ui.Text("Workspace", size=22, bold=True),
            *(
                ui.NavigationItem(label, path, active=active_path == path)
                for label, path in (
                    ("Overview", "/"), ("Data table", "/records"), ("Data entry", "/entry"),
                    ("Reports", "/reports"), ("Settings", "/settings"),
                )
            ),
            width=220,
            class_name="admin-sidebar",
        ),
        ui.Column(
            ui.Header(
                ui.Text(title, size=24, bold=True),
                ui.Spacer(),
                ui.Button("Toggle theme", on_click=toggle_theme, variant="secondary"),
                class_name="admin-header",
            ),
            ui.MainContent(content, class_name="admin-main"),
            ui.Footer(ui.Text("NovaUI Admin · Local sample data", color=MUTED)),
            spacing=0,
            class_name="admin-body",
        ),
        class_name="admin-shell",
    )


def create_application() -> tuple[ui.App, AdminModel]:
    model = AdminModel()
    app_ref: dict[str, ui.App] = {}
    delete_target = ui.state(0)
    dialog_open = ui.state(False)
    entry_status = ui.state("Values are held in memory and reset on restart.")

    def overview():
        return _page_shell(
            "Overview", "/",
            ui.Column(
                ui.Text("Good morning", size=30, bold=True),
                ui.Text("A working sample admin workspace. Changes stay in this process.", color=MUTED),
                ui.Row(
                    ui.Card(ui.Text("People", color=MUTED), ui.Text(lambda: str(len(model.records.value)), size=28, bold=True)),
                    ui.Card(ui.Text("Active", color=MUTED), ui.Text(lambda: str(sum(r["status"] == "Active" for r in model.records.value)), size=28, bold=True)),
                    ui.Card(ui.Text("Needs review", color=MUTED), ui.Text(lambda: str(sum(r["status"] == "Review" for r in model.records.value)), size=28, bold=True)),
                    spacing=16,
                ),
                ui.Card(ui.Text("Recent activity", size=18, bold=True), ui.Text("Use the data table to search, sort, page, and remove a record.")),
                spacing=18,
            ),
            app_ref,
        )

    def request_delete(record):
        delete_target.value = record["id"]
        dialog_open.value = True

    def confirm_delete():
        model.delete(delete_target.value)

    def records_page():
        return _page_shell(
            "People", "/records",
            ui.Column(
                ui.Text("People directory", size=28, bold=True),
                ui.Text("Search, sort columns, and use the page controls. Remove asks for confirmation.", color=MUTED),
                ui.DataTable(
                    [ui.ColumnDef("name", title="Name"), ui.ColumnDef("team", title="Team"), ui.ColumnDef("status", title="Status")],
                    model.records,
                    row_key="id",
                    searchable=True,
                    sortable=True,
                    filterable=True,
                    selectable=True,
                    page_size=5,
                    row_actions=[ui.RowAction("Remove", request_delete)],
                ),
                ui.Dialog(
                    "Remove record?",
                    ui.Text("This removes the sample record from the current in-memory session."),
                    open=dialog_open,
                    on_confirm=confirm_delete,
                    on_cancel=lambda: None,
                    confirm_label="Remove",
                ),
                spacing=16,
            ),
            app_ref,
        )

    form: ui.Form

    def on_submit(values: dict[str, str]) -> str:
        result = model.add(values)
        entry_status.value = result
        return result

    def entry_page():
        nonlocal form
        form = ui.Form(
            fields={
                "name": ui.Field(label="Full name", required=True, min_length=2, max_length=80),
                "team": ui.Field(label="Team", required=True, min_length=2, max_length=60),
            },
            on_submit=on_submit,
            submit_label="Add person",
        )
        return _page_shell(
            "Data entry", "/entry",
            ui.Column(
                ui.Text("Add a person", size=28, bold=True),
                ui.Text(lambda: entry_status.value, color=MUTED),
                ui.Card(form, padding=24),
                spacing=16,
            ),
            app_ref,
        )

    def reports_page():
        return _page_shell(
            "Reports", "/reports",
            ui.Column(
                ui.Text("Team report", size=28, bold=True),
                ui.Text("Counts are computed from the current in-memory records; chart components are not implemented yet.", color=MUTED),
                ui.Card(ui.Text(lambda: " · ".join(
                    f"{team}: {sum(row['team'] == team for row in model.records.value)}"
                    for team in sorted({row['team'] for row in model.records.value})
                ))),
                spacing=16,
            ),
            app_ref,
        )

    settings_theme = ui.state("System preview: light/dark is controlled by the app theme button.")

    def settings_page():
        return _page_shell(
            "Settings", "/settings",
            ui.Column(
                ui.Text("Workspace settings", size=28, bold=True),
                ui.Input(label="Workspace name", value=ui.state("NovaUI workspace")),
                ui.Text(lambda: settings_theme.value, color=MUTED),
                ui.Text("Theme selection applies to the next complete tree render. No settings are persisted."),
                spacing=16,
            ),
            app_ref,
        )

    router = ui.Router(
        routes={"/": overview, "/records": records_page, "/entry": entry_page, "/reports": reports_page, "/settings": settings_page},
        not_found=lambda: _page_shell("Not found", "", ui.Text("404 — Page not found", size=28), app_ref),
    )
    application = ui.App(router, title="NovaUI Admin", theme=LIGHT)
    app_ref["app"] = application
    return application, model


def build_app() -> ui.App:
    return create_application()[0]


if __name__ == "__main__":
    build_app().run()
