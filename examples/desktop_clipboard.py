"""Explicit text clipboard read/write actions for desktop mode."""
import novaui as ui

text = ui.state("NovaUI clipboard demo")
status = ui.state("Use Copy or Paste to access the system text clipboard.")


def copy_text() -> None:
    ui.clipboard.write_text(text.value)
    status.value = "Copied text to clipboard."


def paste_text() -> None:
    text.value = ui.clipboard.read_text()
    status.value = "Pasted text from clipboard."


ui.desktop(ui.Column(
    ui.Text("Clipboard", size=26, bold=True),
    ui.Input(label="Text", value=text),
    ui.Row(ui.Button("Copy", on_click=copy_text), ui.Button("Paste", on_click=paste_text), spacing=8),
    ui.Text(lambda: status.value), spacing=12, padding=24,
), title="NovaUI Clipboard")
