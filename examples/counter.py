"""Reactive counter and IDE live preview example."""

import novaui as ui


def counter_panel(count: ui.State[int], *, title: str, subtitle: str) -> ui.Component:
    return ui.Card(
        ui.Column(
            ui.Row(
                ui.Card(
                    ui.Center(ui.Icon("cube", size=42), width=72, height=72),
                    padding=8,
                    variant="glass-strong",
                    style={"background-color": "#eeeaff", "border-radius": "24px", "box-shadow": "none"},
                ),
                ui.Column(
                    ui.Text(title, size=28, bold=True),
                    ui.Text(subtitle, color="#626a85"),
                    spacing=4,
                ),
                spacing=18,
                align="center",
            ),
            ui.Card(
                ui.Column(
                    ui.Text("COUNT", size=12, bold=True, color="#626a85"),
                    ui.Text(lambda: str(count.value), size=56, bold=True, color="#5144e8"),
                    spacing=2,
                    align="center",
                ),
                padding=20,
                style={"background-color": "#f1efff", "border-radius": "24px", "box-shadow": "none"},
            ),
            ui.Row(
                ui.IconButton(
                    "minus",
                    "Decrease count",
                    on_click=lambda: count.update(count.value - 1),
                    size="large",
                ),
                ui.Button(
                    "Add one",
                    icon="plus",
                    on_click=lambda: count.update(count.value + 1),
                    height=56,
                ),
                spacing=14,
                align="center",
            ),
            spacing=22,
            padding=28,
        ),
        max_width=760,
        padding=8,
    )


@ui.NovaPreview(name="Reactive counter", id="counter")
def CounterPreview():
    return counter_panel(
        ui.preview_state("count", 0),
        title="NovaUI Counter",
        subtitle="State updates are handled by Python.",
    )


def main():
    count = ui.state(0)
    ui.app(
        counter_panel(count, title="NovaUI Counter", subtitle="State updates are handled by Python."),
        title="NovaUI Counter",
        theme=ui.Theme(appearance="glass"),
    )


if __name__ == "__main__":
    main()
