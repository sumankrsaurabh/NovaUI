"""Sortable, searchable employee table with selection and row actions."""

import novaui as ui

employees = [
    {"id": 1, "name": "Alice Chen", "department": "Engineering", "salary": 65000},
    {"id": 2, "name": "Bob Rivera", "department": "Design", "salary": 58000},
    {"id": 3, "name": "Mina Patel", "department": "Engineering", "salary": 72000},
    {"id": 4, "name": "Noah Williams", "department": "Operations", "salary": 61000},
]


def show_employee(row):
    print(f"Selected employee: {row['name']}")


def show_selection(rows):
    print(f"Selected {len(rows)} employees")


ui.app(
    ui.Column(
        ui.Text("Employee directory", size=28, bold=True),
        ui.Text("Sort columns, filter by department, or search the directory."),
        ui.DataTable(
            columns=[
                ui.ColumnDef("name", title="Employee", width="15rem"),
                ui.ColumnDef("department", title="Department"),
                ui.ColumnDef("salary", title="Salary", formatter=lambda value, row: f"${value:,.0f}"),
            ],
            data=employees,
            row_key="id",
            selectable=True,
            page_size=3,
            on_row_click=show_employee,
            on_selection_change=show_selection,
            row_actions=[ui.RowAction("View", show_employee)],
        ),
        spacing=12,
        padding=24,
    ),
    title="Employee Directory",
)
