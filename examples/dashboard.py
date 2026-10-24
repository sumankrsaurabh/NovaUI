"""Compact dashboard layout built from reusable cards and a grid."""

import novaui as ui


def metric(title: str, value: str) -> ui.Card:
    return ui.Card(
        ui.Column(ui.Text(title, color="#6b7280"), ui.Text(value, size=28, bold=True), spacing=8),
        padding=20,
    )


ui.app(
    ui.Row(
        ui.Column(
            ui.Text("Workspace", size=20, bold=True),
            ui.Button("Overview", variant="secondary"),
            ui.Button("Projects", variant="secondary"),
            ui.Button("Settings", variant="secondary"),
            spacing=12,
            padding=16,
            min_width=190,
            background="#ffffff",
        ),
        ui.Column(
            ui.Text("Overview", size=30, bold=True),
            ui.Text("A responsive dashboard assembled from reusable components."),
            ui.Grid(
                metric("Active projects", "12"),
                metric("Tasks completed", "84"),
                metric("Team members", "6"),
                columns=3,
                spacing=16,
            ),
            ui.ScrollView(
                ui.Column(ui.Text("Recent activity", size=20, bold=True), ui.Text("No recent activity."), spacing=8),
                max_height=240,
                padding=20,
                background="#ffffff",
                border="1px solid #e4e7ef",
            ),
            spacing=20,
            padding=24,
            min_width=0,
            max_width=1100,
        ),
        spacing=20,
        align="start",
        padding=20,
        max_width=1200,
        margin="0 auto",
    ),
    title="NovaUI Dashboard",
    theme="light",
)
