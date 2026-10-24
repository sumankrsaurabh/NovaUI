"""Tabbed settings screen with controlled fields and a stateful toggle button."""
import novaui as ui

display_name = ui.state("Nova User")
notifications = ui.state(True)

ui.app(
    ui.Column(
        ui.Text("Settings", size=28, bold=True),
        ui.Tabs({
            "Profile": ui.Column(
                ui.Input(label="Display name", value=display_name),
                ui.Text(lambda: f"Preview: {display_name.value}"), spacing=12,
            ),
            "Notifications": ui.Column(
                ui.Text(lambda: "Notifications are enabled" if notifications.value else "Notifications are disabled"),
                ui.Button("Toggle notifications", on_click=lambda: notifications.update(not notifications.value)),
                spacing=12,
            ),
        }),
        spacing=16, padding=24,
    ),
    title="NovaUI Settings",
    theme=ui.Theme(mode="light"),
)
