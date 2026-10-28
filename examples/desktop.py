"""Optional desktop window with an explicit native open-file action."""

import novaui as ui


def build_root() -> ui.Component:
    selected = ui.state("No file selected.")

    def choose_file():
        path = ui.dialogs.open_file(
            title="Choose a document",
            file_types=["Text files (*.txt)", "All files (*.*)"],
        )
        if path:
            selected.value = f"Selected: {path}"

    return ui.Column(
        ui.Text("NovaUI Desktop", size=28, bold=True),
        ui.Text("This is the same NovaUI web renderer inside an optional webview."),
        ui.Text(lambda: selected.value),
        ui.Button("Open file…", icon="folder", on_click=choose_file),
        spacing=16,
        padding=24,
        max_width=720,
    )


def main():
    ui.desktop(
        build_root(),
        title="NovaUI Desktop Example",
        width=1000,
        height=700,
        theme=ui.Theme(appearance="glass"),
    )


if __name__ == "__main__":
    main()
