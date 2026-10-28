"""Small routed dashboard with a searchable, sortable data table."""

import novaui as ui

EMPLOYEES = [
    {"name": "Avery Chen", "team": "Design", "status": "Active"},
    {"name": "Jordan Lee", "team": "Engineering", "status": "Active"},
    {"name": "Morgan Patel", "team": "Operations", "status": "On leave"},
]


def page(title: str, content: ui.Component) -> ui.Component:
    return ui.Scaffold(
        ui.Column(content, spacing=20, padding=24),
        destinations=[
            ui.NavDestination("Overview", "/", icon="home"),
            ui.NavDestination("Team", "/team", icon="users"),
        ],
        brand=ui.Text("NovaUI", size=20, bold=True),
        top_bar=ui.Row(
            ui.Text(title, size=24, bold=True),
            ui.Badge("Workspace"),
            spacing=12,
            justify="between",
        ),
        label="Dashboard navigation",
    )


def overview() -> ui.Component:
    return page(
        "Overview",
        ui.Column(
            ui.Text("A compact application shell with working client navigation."),
            ui.Grid(
                ui.Card(ui.Column(ui.Text("Team members", color="#697086"), ui.Text("3", size=28, bold=True), spacing=6), padding=18),
                ui.Card(ui.Column(ui.Text("Monthly revenue", color="#697086"), ui.Text("$24.8k", size=28, bold=True), spacing=6), padding=18),
                ui.Card(ui.Column(ui.Text("Open tasks", color="#697086"), ui.Text("12", size=28, bold=True), spacing=6), padding=18),
                columns=3,
                spacing=14,
            ),
            ui.Chart(
                ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                {"Revenue": [12, 18, 16, 24, 21, 29], "Costs": [8, 11, 10, 15, 13, 17]},
                kind="area",
                title="Revenue and costs · this year",
                height=260,
            ),
            ui.Grid(
                ui.Chart(
                    ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                    {"Orders": [18, 25, 21, 32, 28, 39]},
                    kind="bar",
                    title="Monthly orders",
                    height=220,
                ),
                ui.Chart(
                    ["Design", "Engineering", "Operations"],
                    {"People": [8, 12, 5]},
                    kind="doughnut",
                    title="Team distribution",
                    height=220,
                ),
                columns=2,
                spacing=14,
            ),
            spacing=16,
        ),
    )


def team() -> ui.Component:
    return page(
        "Team",
        ui.Column(
            ui.Text("Search, sort, and page through the supplied in-memory rows."),
            ui.DataTable(
                columns=[
                    ui.ColumnDef("name", title="Name"),
                    ui.ColumnDef("team", title="Team"),
                    ui.ColumnDef("status", title="Status"),
                ],
                data=EMPLOYEES,
                selectable=True,
                page_size=5,
            ),
            spacing=16,
        ),
    )


def main():
    ui.app(
        ui.Router(
            routes={"/": overview, "/team": team},
            not_found=lambda: page("Not found", ui.Text("This dashboard page does not exist.")),
        ),
        title="NovaUI Dashboard",
        theme=ui.Theme(appearance="glass"),
    )


if __name__ == "__main__":
    main()
