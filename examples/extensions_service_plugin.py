"""Runnable app-scoped plugin and service example."""

import novaui as ui


class AuditPlugin:
    name = "audit"
    min_novaui_version = "0.1.0"
    max_novaui_version_exclusive = "1.0.0"

    def setup(self, app: ui.App) -> None:
        app.register_service("audit", AuditService())

    def on_app_start(self, app: ui.App) -> None:
        print("Audit service ready")

    def on_app_stop(self, app: ui.App) -> None:
        print("Audit service stopped")


class AuditService:
    def record(self, action: str) -> None:
        print(f"Audit action: {action}")


extensions = ui.Extensions()
extensions.use(AuditPlugin())

if __name__ == "__main__":
    ui.app(
        ui.Column(ui.Text("App with an app-scoped audit service"), padding=24),
        title="NovaUI Plugin Example",
        extensions=extensions,
    )
