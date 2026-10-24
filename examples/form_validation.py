"""Input validation with a Python callback and safely rendered error text."""

import novaui as ui

email = ui.state("")


def validate_email(value: str) -> str | None:
    if not value:
        return "Email is required."
    if "@" not in value:
        return "Enter an email address containing @."
    return None


ui.app(
    ui.Card(
        ui.Column(
            ui.Text("Create your account", size=24, bold=True),
            ui.Input(label="Email", placeholder="you@example.com", value=email, on_change=validate_email),
            ui.Button("Continue"),
            spacing=14,
        ),
        padding=24,
        max_width=480,
    ),
    title="NovaUI Form Validation",
)
