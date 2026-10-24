"""Runnable named theme extension example."""

import novaui as ui

extensions = ui.Extensions()
extensions.register_theme(
    ui.Theme(name="corporate", mode="light", primary="#3157D5", radius="10px")
)
extensions.register_theme(
    ui.Theme(name="corporate_dark", mode="dark", primary="#9AAEFF", radius="10px")
)

if __name__ == "__main__":
    ui.app(
        ui.Column(ui.Text("Corporate design system", size=28, bold=True), padding=24),
        theme="corporate",
        extensions=extensions,
    )
