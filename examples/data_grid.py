"""Editable, keyboard-navigable data grid."""

import novaui as ui


def main() -> None:
    employees = ui.state([
        {"name": "Avery Chen", "team": "Design"},
        {"name": "Jordan Lee", "team": "Engineering"},
        {"name": "Morgan Patel", "team": "Operations"},
    ])
    ui.app(
        ui.Column(
            ui.Text("Editable Team Grid", size=28, bold=True),
            ui.Text("Focus a cell; press Enter or F2 to edit and use arrow keys to navigate."),
            ui.DataGrid(
                [ui.ColumnDef("name", title="Employee"), ui.ColumnDef("team", title="Team")],
                employees,
            ),
            spacing=16,
        ),
        title="Editable Team Grid",
    )


if __name__ == "__main__":
    main()
