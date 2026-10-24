"""Native open/save dialogs; selecting a path never opens or writes it."""
import novaui as ui

result = ui.state("No file selected.")


def open_document() -> None:
    path = ui.dialogs.open_file(title="Open document", file_types=["Text files (*.txt)", "PDF files (*.pdf)"])
    result.value = f"Selected: {path}" if path else "Open cancelled."


def save_document() -> None:
    path = ui.dialogs.save_file(
        title="Save document", suggested_name="report.txt", file_types=["Text files (*.txt)"]
    )
    result.value = f"Save location: {path}" if path else "Save cancelled."


ui.desktop(ui.Column(
    ui.Text("Native file dialogs", size=26, bold=True),
    ui.Button("Open file…", on_click=open_document),
    ui.Button("Choose save location…", on_click=save_document),
    ui.Text(lambda: result.value), spacing=12, padding=24,
), title="NovaUI File Dialogs")
