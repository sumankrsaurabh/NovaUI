"""A deliberately bounded plain-text desktop document workflow.

The framework has no multiline input or rich-text editor yet, so this prototype
uses twelve labeled single-line fields and ordinary UTF-8 text files.
"""

from __future__ import annotations

from pathlib import Path

import novaui as ui
from examples.phase11_design import LIGHT, MUTED

MAX_LINES = 12
MAX_LINE_LENGTH = 2000
MAX_FILE_BYTES = 1_000_000


def parse_document(text: str) -> list[str]:
    if not isinstance(text, str):
        raise TypeError("Document contents must be text.")
    if len(text.encode("utf-8")) > MAX_FILE_BYTES:
        raise ValueError("Document exceeds the 1 MB prototype limit.")
    lines = text.splitlines()
    if len(lines) > MAX_LINES:
        raise ValueError(f"This prototype supports at most {MAX_LINES} lines.")
    if any(len(line) > MAX_LINE_LENGTH for line in lines):
        raise ValueError(f"Each line must be at most {MAX_LINE_LENGTH} characters.")
    return [*lines, *("" for _ in range(MAX_LINES - len(lines)))]


def serialize_document(lines: list[str]) -> str:
    if not isinstance(lines, list) or len(lines) != MAX_LINES or any(not isinstance(line, str) for line in lines):
        raise ValueError(f"Document must contain exactly {MAX_LINES} text lines.")
    if any(len(line) > MAX_LINE_LENGTH for line in lines):
        raise ValueError(f"Each line must be at most {MAX_LINE_LENGTH} characters.")
    last_content = max((index for index, line in enumerate(lines) if line), default=-1)
    return "\n".join(lines[: last_content + 1])


def read_document(path: str | Path) -> list[str]:
    selected = Path(path)
    if selected.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Document exceeds the 1 MB prototype limit.")
    return parse_document(selected.read_text(encoding="utf-8"))


def write_document(path: str | Path, lines: list[str]) -> None:
    Path(path).write_text(serialize_document(lines), encoding="utf-8", newline="\n")


def build_app() -> ui.App:
    title = ui.state("Untitled document")
    lines = [ui.state("") for _ in range(MAX_LINES)]
    dirty = ui.state(True)
    status = ui.state("New document · unsaved · UTF-8 plain text · 12 single-line rows")

    def changed(_value: str) -> None:
        dirty.value = True
        status.value = "Unsaved changes"

    def open_document() -> None:
        try:
            selected = ui.dialogs.open_file(title="Open text document", file_types=["Text files (*.txt)"])
            if not selected:
                status.value = "Open cancelled"
                return
            loaded = read_document(selected)
            for target, value in zip(lines, loaded):
                target.value = value
            title.value = Path(selected).stem[:80] or "Untitled document"
            dirty.value = False
            status.value = f"Opened {Path(selected).name}"
        except (OSError, UnicodeError, ValueError, RuntimeError):
            status.value = "Could not open this file. Choose a UTF-8 text file with at most 12 lines and 1 MB."

    def save_document() -> None:
        try:
            selected = ui.dialogs.save_file(
                title="Save text document",
                suggested_name=f"{title.value or 'document'}.txt",
                file_types=["Text files (*.txt)"],
            )
            if not selected:
                status.value = "Save cancelled"
                return
            write_document(selected, [line.value for line in lines])
            dirty.value = False
            status.value = f"Saved {Path(selected).name}"
        except (OSError, UnicodeError, ValueError, RuntimeError):
            status.value = "Could not save this file. Check the destination and document limits."

    editor_rows = [
        ui.Row(
            ui.Text(f"{index + 1:02}", color=MUTED, width=36),
            ui.Input(value=line, placeholder="Write a line…", on_change=changed, max_length=MAX_LINE_LENGTH),
            spacing=12,
            align="center",
        )
        for index, line in enumerate(lines)
    ]
    application = ui.App(
        ui.Column(
            ui.Header(
                ui.Text("PyOffice · Notes", size=24, bold=True),
                ui.Spacer(),
                ui.Button("Open", on_click=open_document, variant="secondary"),
                ui.Button("Save as…", on_click=save_document),
                padding=16,
            ),
            ui.MainContent(
                ui.Row(ui.Input(label="Document name", value=title, max_length=80, on_change=changed), ui.Text(lambda: "● Unsaved" if dirty.value else "Saved", color=MUTED), align="center"),
                ui.Card(ui.ScrollView(ui.Column(*editor_rows, spacing=4), height=560), padding=20),
                ui.Footer(
                    ui.Text(lambda: f"{sum(len(line.value) for line in lines)} characters · {MAX_LINES} line slots", color=MUTED),
                    ui.Spacer(),
                    ui.Text(lambda: status.value, color=MUTED),
                ),
                spacing=16,
            ),
            spacing=0,
            class_name="pyoffice-root",
        ),
        title="PyOffice Notes",
        theme=LIGHT,
    )
    application.shortcuts.register("Mod+O", open_document, allow_in_inputs=True)
    application.shortcuts.register("Mod+S", save_document, allow_in_inputs=True)
    return application


if __name__ == "__main__":
    build_app().run(desktop=True)
