"""Small multi-page dashboard demonstrating route history and shell helpers."""
import novaui as ui


def shell(title: str, content: ui.Component) -> ui.Component:
    return ui.AppShell(
        ui.Sidebar(
            ui.Text("NovaUI", size=20, bold=True),
            ui.NavigationItem("Dashboard", "/", active=title == "Dashboard"),
            ui.NavigationItem("Settings", "/settings", active=title == "Settings"),
            spacing=12,
        ),
        ui.Column(
            ui.Header(ui.Text(title, size=24, bold=True)),
            ui.MainContent(content),
            ui.Footer(ui.Text("NovaUI sample")),
        ),
    )


def dashboard() -> ui.Component:
    return shell("Dashboard", ui.Column(
        ui.Text("Overview", size=20),
        ui.Row(ui.Card(ui.Text("Active users: 128")), ui.Card(ui.Text("Tasks: 7")), spacing=16),
        spacing=16,
    ))


def settings() -> ui.Component:
    return shell("Settings", ui.Column(
        ui.Text("Settings page", size=20),
        ui.Text("Use your browser back and forward buttons to navigate."),
        spacing=12,
    ))


ui.app(ui.Router(routes={"/": dashboard, "/settings": settings}), title="NovaUI Dashboard")
