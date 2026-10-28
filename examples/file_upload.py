"""A polished, cross-platform small-file upload screen."""

import novaui as ui


def main() -> None:
    status = ui.state("Your next file is ready to upload.")

    def handle_upload(upload: ui.UploadedFile) -> None:
        status.value = f"Received {upload.name} ({len(upload.data)} bytes)."

    ui.app(
        ui.Column(
            ui.Row(
                ui.Icon("sparkles", size=20),
                ui.Text("NOVA UI", size=14, bold=True),
                justify="center",
                spacing=8,
            ),
            ui.Column(
                ui.Badge("SMALL FILES / PRIVATE BY DESIGN", tone="info"),
                ui.Text("A calmer way to share files.", size=34, bold=True),
                ui.Text(
                    "Choose a text or CSV file and NovaUI will validate it before "
                    "your Python callback receives its contents."
                ),
                align="center",
                spacing=12,
            ),
            ui.Card(
                ui.Column(
                    ui.Row(
                        ui.Icon("folder", size=28),
                        ui.Column(
                            ui.Text("Choose a file", size=19, bold=True),
                            ui.Text("TXT and CSV / up to 5 KB"),
                            spacing=4,
                        ),
                        justify="center",
                        spacing=12,
                    ),
                    ui.Divider(),
                    ui.Text("Your file stays in this app session and is passed directly to its upload handler."),
                    ui.FileUpload(
                        handle_upload,
                        label="Browse files",
                        accept=".txt,.csv",
                        max_size=5000,
                    ),
                    ui.Text(lambda: status.value, color="var(--muted)"),
                    spacing=16,
                    padding=4,
                ),
                variant="glass-strong",
                padding=28,
                max_width=640,
            ),
            ui.Grid(
                ui.Card(
                    ui.Row(
                        ui.Icon("check", size=18),
                        ui.Column(
                            ui.Text("Validated locally", bold=True),
                            ui.Text("File type and size are checked before handling."),
                            spacing=4,
                        ),
                        spacing=10,
                    ),
                    padding=16,
                    variant="glass",
                ),
                ui.Card(
                    ui.Row(
                        ui.Icon("file", size=18),
                        ui.Column(
                            ui.Text("One clear limit", bold=True),
                            ui.Text("Small uploads fit NovaUI's bounded event bridge."),
                            spacing=4,
                        ),
                        spacing=10,
                    ),
                    padding=16,
                    variant="glass",
                ),
                columns=2,
                tablet_columns=2,
                mobile_columns=1,
                spacing=12,
                max_width=720,
            ),
            spacing=28,
            padding=32,
            max_width=880,
            margin="0 auto",
            align="center",
        ),
        title="NovaUI · File upload",
        theme=ui.Theme(
            mode="system",
            appearance="glass",
            glass_blur=24,
            glass_opacity=0.72,
        ),
    )


if __name__ == "__main__":
    main()
