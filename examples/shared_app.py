"""Shared page and controls for browser and optional desktop hosting."""
import novaui as ui

saved = ui.state(False)

ui.app(ui.Column(
    ui.Text("Shared web and desktop application", size=26, bold=True),
    ui.Button("Save", on_click=lambda: saved.update(True)),
    ui.Text(lambda: "Saved" if saved.value else "Not saved yet"),
    padding=24, spacing=12,
), title="NovaUI Shared App")
