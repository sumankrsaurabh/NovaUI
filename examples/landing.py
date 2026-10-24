"""Responsive landing page using NovaUI layout primitives."""

import novaui as ui

ui.app(
    ui.Container(
        ui.Column(
            ui.Row(
                ui.Text("NovaUI", size=22, bold=True),
                ui.Spacer(),
                ui.Button("Documentation", variant="secondary"),
                spacing=12,
            ),
            ui.Column(
                ui.Text("Build interfaces with Python", size=36, bold=True),
                ui.Text("Compose reusable layouts and render them in a browser or desktop webview."),
                ui.Wrap(
                    ui.Button("Get started"),
                    ui.Button("View examples", variant="secondary"),
                    spacing=12,
                    run_spacing=12,
                ),
                spacing=16,
                padding=32,
                background="#ffffff",
                border="1px solid #e4e7ef",
                shadow="0 12px 34px rgba(30, 35, 90, .08)",
                max_width=780,
            ),
            spacing=28,
            max_width=1100,
            margin="0 auto",
        ),
        padding=24,
    ),
    title="NovaUI Landing Page",
    theme=ui.Theme(primary="#635BFF", radius=12),
)
