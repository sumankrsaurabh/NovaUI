"""Run with --dark to switch the same component tree to the dark theme."""

import sys

import novaui as ui

theme = "dark" if "--dark" in sys.argv else "light"

ui.app(
    ui.Card(
        ui.Column(
            ui.Text(f"{theme.title()} theme", size=24, bold=True),
            ui.Text("Theme colors are supplied by CSS variables."),
            ui.Button("Continue"),
            spacing=12,
        ),
        padding=24,
    ),
    title="NovaUI Themes",
    theme=theme,
)
