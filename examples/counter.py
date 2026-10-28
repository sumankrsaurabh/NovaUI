from novaui import (
    Button,
    Card,
    Center,
    Column,
    Component,
    Icon,
    IconButton,
    NovaPreview,
    Row,
    State,
    Text,
    Theme,
    app,
    preview_state,
    state,
)


def counter_panel(count: State[int], *, title: str, subtitle: str) -> Component:
    return Card(
        Column(
            Row(
                Card(
                    Center(Icon("cube", size=42), width=72, height=72),
                    padding=8,
                    variant="glass-strong",
                    style={
                        "background-color": "var(--primary-soft)",
                        "border-radius": "var(--radius-control)",
                    },
                ),
                Column(
                    Text(title, size=28, bold=True),
                    Text(subtitle, color="var(--muted)"),
                    spacing=4,
                ),
                spacing=18,
                align="center",
            ),
            Card(
                Column(
                    Text("COUNT", size=12, bold=True, color="var(--muted)"),
                    Text(
                        lambda: str(count.value),
                        size=56,
                        bold=True,
                        color="var(--primary)",
                    ),
                    spacing=2,
                    align="center",
                ),
                padding=20,
                style={
                    "background-color": "var(--primary-soft)",
                    "border-radius": "var(--radius)",
                },
            ),
            Row(
                IconButton(
                    "minus",
                    "Decrease count",
                    on_click=lambda: count.update(count.value - 1),
                    size="large",
                ),
                Button(
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


@NovaPreview(name="Reactive counter", id="counter")
def CounterPreview():
    return counter_panel(
        preview_state("count", 0),
        title="NovaUI Counter",
        subtitle="State updates are handled by Python.",
    )


def main():
    count = state(0)
    app(
        counter_panel(
            count,
            title="NovaUI Counter",
            subtitle="State updates are handled by Python.",
        ),
        title="NovaUI Counter",
        theme=Theme(mode="system", appearance="glass"),
    )


if __name__ == "__main__":
    main()
