"""Employee directory demonstrating DataTable search, filtering, and selection."""

import novaui as ui

EMPLOYEES = [
    {"name": "Avery Chen", "team": "Design", "status": "Active"},
    {"name": "Jordan Lee", "team": "Engineering", "status": "Active"},
    {"name": "Morgan Patel", "team": "Operations", "status": "On leave"},
    {"name": "Riley Diaz", "team": "Engineering", "status": "Active"},
]


def main() -> None:
    ui.app(
        ui.Column(
            ui.Text("Employee Directory", size=28, bold=True),
            ui.Text("Search, sort, filter, and select employees."),
            ui.DataTable(
                columns=[
                    ui.ColumnDef("name", title="Employee"),
                    ui.ColumnDef("team", title="Team"),
                    ui.ColumnDef("status", title="Status"),
                ],
                data=EMPLOYEES,
                selectable=True,
                column_visibility=True,
                exportable=True,
                page_size=10,
            ),
            spacing=16,
        ),
        title="Employee Directory",
    )


if __name__ == "__main__":
    main()
