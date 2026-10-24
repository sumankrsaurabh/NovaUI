"""Desktop window with validated dimensions and window controls."""
import novaui as ui

ui.desktop(
    ui.Column(
        ui.Text("NovaUI desktop window", size=28, bold=True),
        ui.Text("This is the same HTML renderer hosted in a webview."),
        ui.Button("Resize window", on_click=lambda: ui.window.resize(900, 650)),
        ui.Button("Toggle fullscreen", on_click=ui.window.toggle_fullscreen),
        spacing=16,
        padding=24,
    ),
    title="NovaUI Desktop",
    width=1000,
    height=720,
    min_width=600,
    min_height=400,
)
