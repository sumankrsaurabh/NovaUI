"""Interactive, safe component catalogue for the NovaUI public API."""

from __future__ import annotations

import argparse
from inspect import signature

import novaui as ui
from examples.phase11_design import DARK, LIGHT, MUTED


def _entry(component, category, code, preview):
    # Keep property details tied to the real constructor instead of hand-written
    # signatures that can silently drift from the component API.
    return {
        "category": category,
        "properties": f"{component.__name__}{signature(component)}",
        "code": code,
        "preview": preview,
    }


CATALOGUE = {
    "Text": _entry(ui.Text, "Basic", 'ui.Text("Hello", size=24, bold=True)',
                   lambda: ui.Text("Preview text", size=24, bold=True)),
    "Button": _entry(ui.Button, "Basic", 'ui.Button("Continue", on_click=continue_action)',
                     lambda: ui.Button("Continue", on_click=lambda: None)),
    "Input": _entry(ui.Input, "Inputs", 'ui.Input(label="Name", placeholder="Your name")',
                    lambda: ui.Input(label="Name", placeholder="Your name")),
    "Row": _entry(ui.Row, "Layouts", 'ui.Row(ui.Text("Left"), ui.Spacer(), ui.Text("Right"))',
                  lambda: ui.Row(ui.Text("Left"), ui.Spacer(), ui.Text("Right"), padding=12,
                                 class_name="studio-preview-row")),
    "Column": _entry(ui.Column, "Layouts", 'ui.Column(ui.Text("First"), ui.Text("Second"), spacing=8)',
                      lambda: ui.Column(ui.Text("First item"), ui.Text("Second item"), spacing=8)),
    "Card": _entry(ui.Card, "Layouts", 'ui.Card(ui.Text("Summary"), padding=20)',
                   lambda: ui.Card(ui.Text("Summary card"), padding=20)),
    "Grid": _entry(ui.Grid, "Layouts", 'ui.Grid(ui.Card(...), ui.Card(...), columns=2)',
                   lambda: ui.Grid(ui.Card(ui.Text("One")), ui.Card(ui.Text("Two")), columns=2,
                                   spacing=12)),
    "Form": _entry(ui.Form, "Forms", 'ui.Form(fields={"name": ui.Field(required=True)}, on_submit=save)',
                   lambda: ui.Form(fields={"name": ui.Field(label="Name", value="Ada")},
                                   on_submit=lambda values: "Preview only", reset_label=None)),
    "DataTable": _entry(ui.DataTable, "Data", 'ui.DataTable([ui.ColumnDef("name")], [{"name": "Ada"}])',
                        lambda: ui.DataTable(
                            [ui.ColumnDef("name", title="Name"), ui.ColumnDef("role", title="Role")],
                            [{"name": "Ada", "role": "Engineer"}], page_size=5,
                        )),
    "Alert": _entry(ui.Alert, "Feedback", 'ui.Alert("Saved", kind="success")',
                    lambda: ui.Alert("Settings saved", kind="success")),
    "Spinner": _entry(ui.Spinner, "Feedback", 'ui.Spinner(label="Loading")',
                       lambda: ui.Spinner(label="Loading preview")),
    "Animated": _entry(ui.Animated, "Motion", 'ui.Animated(ui.Card(ui.Text("Hello")), enter="fade_up")',
                        lambda: ui.Animated(ui.Card(ui.Text("Entrance preview"), padding=18), enter="fade_up")),
}


def build_app(*, host: str = "127.0.0.1", port: int = 0, debug: bool = False) -> ui.App:
    selected = ui.state("Text")
    category = ui.state("All")
    query = ui.state("")
    visible_rows = ui.state([])
    notice = ui.state("Select a component to inspect its API and preview.")
    app_ref: dict[str, ui.App] = {}
    categories = ["All", *dict.fromkeys(item["category"] for item in CATALOGUE.values())]

    def refresh_catalogue() -> None:
        term = query.value.casefold().strip()
        visible_rows.value = [
            {"name": name, "category": spec["category"]}
            for name, spec in CATALOGUE.items()
            if (category.value == "All" or spec["category"] == category.value)
            and (not term or term in name.casefold() or term in spec["category"].casefold())
        ]
        if selected.value not in {row["name"] for row in visible_rows.value} and visible_rows.value:
            selected.value = visible_rows.value[0]["name"]

    refresh_catalogue()

    def choose_category(value: str):
        def choose() -> None:
            category.value = value
            refresh_catalogue()
        return choose

    def search(value: str) -> None:
        query.value = value
        refresh_catalogue()

    def choose(row):
        selected.value = row["name"]
        notice.value = f"Selected {row['name']} · {row['category']}"

    def copy_example():
        try:
            ui.clipboard.write_text(CATALOGUE[selected.value]["code"])
            notice.value = "Example copied to the desktop clipboard."
        except RuntimeError:
            notice.value = "Clipboard is available in desktop mode; select the sample below to copy in a browser."

    def toggle_theme():
        current = app_ref["app"].theme
        app_ref["app"].set_theme(DARK if getattr(current, "mode", current) == "light" else LIGHT)

    table = ui.DataTable(
        [ui.ColumnDef("name", title="Component"), ui.ColumnDef("category", title="Category")],
        visible_rows,
        searchable=False,
        filterable=False,
        sortable=True,
        page_size=20,
        on_row_click=choose,
        class_name="studio-catalogue",
    )
    tabs = ui.Tabs(
        {name: ui.Card(spec["preview"](), padding=24, class_name="studio-preview-card")
         for name, spec in CATALOGUE.items()},
        selected=selected,
        class_name="studio-preview-tabs",
    )
    category_buttons = [
        ui.Button(label, on_click=choose_category(label), variant="secondary",
                  class_name="studio-category")
        for label in categories
    ]
    hero = ui.Card(
        ui.Text("NovaUI Component Showcase", size=32, bold=True),
        ui.Text("A practical playground for components that are implemented today.", color=MUTED),
        ui.Row(
            ui.Text("Python-first", class_name="studio-pill"),
            ui.Text("HTML · CSS · JavaScript renderer", class_name="studio-pill"),
            ui.Text(f"{len(CATALOGUE)} working previews", class_name="studio-pill"),
            spacing=8,
        ),
        padding=24,
        class_name="studio-hero",
    )
    sidebar = ui.Sidebar(
        ui.Text("NOVAUI", size=13, bold=True, color=MUTED),
        ui.Text("Component library", size=20, bold=True),
        ui.Input(label="Search components", placeholder="Search by name or category", on_change=search),
        *category_buttons,
        ui.Text("CATALOGUE", size=12, bold=True, color=MUTED),
        table,
        width=310,
        padding=16,
        class_name="studio-sidebar",
    )
    main = ui.MainContent(
        ui.Header(
            ui.Text("Developer preview", size=20, bold=True),
            ui.Spacer(),
            ui.Button("Copy Python example", on_click=copy_example, variant="secondary"),
            ui.Button("Toggle theme", on_click=toggle_theme, variant="primary"),
            class_name="studio-topbar",
        ),
        hero,
        ui.Grid(
            ui.Card(ui.Text("Stateful previews", bold=True), ui.Text("Controls use NovaUI's regular event bridge."), padding=16),
            ui.Card(ui.Text("Constructor details", bold=True), ui.Text("Signatures are read from public component constructors."), padding=16),
            ui.Card(ui.Text("Safe examples", bold=True), ui.Text("Code samples are displayed as text and never executed."), padding=16),
            columns=3,
            spacing=12,
            class_name="studio-feature-grid",
        ),
        ui.Row(
            ui.Column(
                ui.Text("Live component preview", size=20, bold=True),
                tabs,
                spacing=12,
                class_name="studio-panel",
            ),
            ui.Column(
                ui.Card(
                    ui.Text("Properties", size=18, bold=True),
                    ui.Text(lambda: CATALOGUE[selected.value]["properties"],
                            style={"font-family": "monospace", "white-space": "pre-wrap"}),
                    ui.Text(lambda: f"Reference: COMPONENTS.md · {selected.value}", color=MUTED),
                    padding=20,
                ),
                ui.Card(
                    ui.Text("Python example", size=18, bold=True),
                    ui.Text(lambda: CATALOGUE[selected.value]["code"],
                            style={"font-family": "monospace", "white-space": "pre-wrap"}),
                    ui.Text(lambda: notice.value, color=MUTED),
                    padding=20,
                ),
                spacing=12,
                class_name="studio-inspector",
            ),
            align="stretch",
            spacing=16,
            class_name="studio-workspace",
        ),
        ui.Footer(ui.Text("NovaUI · early-stage framework · APIs remain experimental", color=MUTED),
                  class_name="studio-footer"),
        spacing=16,
        class_name="studio-main",
    )
    shell = ui.Row(sidebar, main, spacing=0, align="stretch", class_name="studio-root")
    application = ui.App(shell, title="NovaUI Studio", theme=LIGHT, host=host, port=port, debug=debug)
    app_ref["app"] = application
    return application


def run_app(argv: list[str] | None = None) -> None:
    """Run Studio with the standard NovaUI CLI-injected hosting options."""
    parser = argparse.ArgumentParser(description="Run the NovaUI component showcase.")
    parser.add_argument("--desktop", action="store_true", help="open in the optional desktop webview")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser in web mode")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--debug", action="store_true")
    options, _ = parser.parse_known_args(argv)
    application = build_app(host=options.host, port=options.port, debug=options.debug)
    application.run(desktop=options.desktop, open_browser=not options.no_browser)


if __name__ == "__main__":
    run_app()
