"""Minimal interactive NovaUI counter."""

import novaui as ui

count = ui.state(0)

ui.app(
    ui.Card(
        ui.Column(
            ui.Text("NovaUI", size=14, color="#6558d3", bold=True),
            ui.Text("Hello, declarative UI.", size=28, bold=True),
            ui.Text(lambda: f"Counter value: {count.value}", size=18),
            ui.Row(
                ui.Button("−", on_click=lambda: count.update(count.value - 1), variant="secondary"),
                ui.Button("+", on_click=lambda: count.update(count.value + 1)),
                spacing=8,
            ),
            spacing=14,
            padding=8,
        ),
        padding=24,
        radius=18,
    ),
    title="NovaUI Counter",
    theme="light",
)
