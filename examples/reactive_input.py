"""A text input that updates Python state and computed text."""

import novaui as ui

name = ui.state("")

ui.app(
    ui.Card(
        ui.Column(
            ui.Text("Reactive input", size=24, bold=True),
            ui.Input(label="Your name", placeholder="Enter your name", value=name),
            ui.Text(lambda: f"Hello, {name.value}!" if name.value else "Type your name above."),
            spacing=12,
        ),
        padding=24,
    ),
    title="NovaUI Reactive Input",
)
