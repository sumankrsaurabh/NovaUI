"""Switch between the built-in light/dark glass palettes and custom tokens."""

import sys

import novaui as ui


def build_app() -> ui.App:
    application = None
    dark = False

    def toggle_theme():
        nonlocal dark
        dark = not dark
        application.set_theme("dark" if dark else "light")

    custom = ui.Theme(
        name="ocean_glass",
        mode="light",
        appearance="glass",
        primary="#1677B8",
        primary_hover="#105F98",
        radius="24px",
        glass_blur=26,
        glass_opacity=0.58,
        success="#16845B",
    )
    root = ui.Column(
        ui.Text("Theme tokens", size=28, bold=True),
        ui.Text("Switch the palette or run this app with a custom glass theme."),
        ui.Card(
            ui.Column(
                ui.Text("Surface example", size=18, bold=True),
                ui.Badge("Ready", tone="success"),
                ui.Button("Toggle light / dark", on_click=toggle_theme),
                spacing=14,
                padding=24,
            )
        ),
        spacing=18,
        padding=24,
        max_width=700,
    )
    application = ui.App(root, title="NovaUI Themes", theme=custom)
    return application


def main():
    application = build_app()
    application.run(
        desktop="--desktop" in sys.argv,
        open_browser="--no-browser" not in sys.argv,
    )


if __name__ == "__main__":
    main()
