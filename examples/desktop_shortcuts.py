"""Desktop keyboard shortcuts; Mod maps to Ctrl on Windows/Linux and Command on macOS."""
import novaui as ui

status = ui.state("Press Mod+S to save; focus a text field to see the default input protection.")


def save() -> None:
    status.value = "Save shortcut activated."


application = ui.App(ui.Column(
    ui.Text("Keyboard shortcuts", size=26, bold=True),
    ui.Input(label="Editable text", value=ui.state("Shortcut is ignored here by default")),
    ui.Text(lambda: status.value), spacing=12, padding=24,
))
application.shortcuts.register("Mod+S", save)
application.run(desktop=True)
