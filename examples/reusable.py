"""A small example of composing reusable Python component functions."""

import novaui as ui


def info_card(title: str, description: str) -> ui.Card:
    return ui.Card(
        ui.Column(
            ui.Text(title, size=20, bold=True),
            ui.Text(description, color="#6b7280"),
            spacing=8,
        ),
        padding=20,
    )


ui.app(
    ui.Column(
        info_card("Reusable components", "Compose screens from ordinary Python functions."),
        info_card("Shared renderer", "The browser and desktop host use the same frontend."),
        spacing=16,
        padding=16,
    ),
    title="NovaUI Reusable Components",
)
