"""A compact gallery of currently implemented everyday components."""

import novaui as ui


def build_root() -> ui.Component:
    return ui.Column(
        ui.Text("Everyday components", size=28, bold=True),
        ui.Text("A small tour of controls available in the current release."),
        ui.Row(
            ui.Button("Primary action", variant="primary", icon="sparkles"),
            ui.Button("Secondary action", variant="secondary", icon="file"),
            ui.IconButton("plus", label="Add item"),
            spacing=12,
        ),
        ui.Row(
            ui.Badge("Active", tone="success"),
            ui.Badge("Review", tone="warning"),
            ui.Badge("Offline", tone="danger"),
            spacing=10,
        ),
        ui.Card(
            ui.Column(
                ui.Text("Progress", size=18, bold=True),
                ui.ProgressBar(68, label="Import progress", show_value=True),
                ui.Divider(),
                ui.Text("Reserved loading space"),
                ui.Skeleton(variant="text", lines=2),
                spacing=12,
                padding=20,
            )
        ),
        spacing=18,
        padding=24,
        max_width=860,
    )


def main():
    ui.app(
        build_root(),
        title="NovaUI Components",
        theme=ui.Theme(appearance="glass"),
    )


if __name__ == "__main__":
    main()
