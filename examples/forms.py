"""Registration form with server-side Python validation."""

import novaui as ui


def save_registration(values: dict[str, str]) -> str:
    # Replace this local demonstration callback with trusted application logic.
    return f"Thanks, {values['name']} — the form passed validation."


def build_root() -> ui.Component:
    form = ui.Form(
        fields={
            "name": ui.Field(label="Name", required=True, min_length=2),
            "email": ui.Field(label="Email", input_type="email", required=True),
            "password": ui.Field(label="Password", input_type="password", required=True, min_length=8),
        },
        on_submit=save_registration,
        submit_label="Create account",
    )
    return ui.Column(
        ui.Text("Create your account", size=28, bold=True),
        ui.Text("Validation runs in the Python form handler."),
        form,
        spacing=16,
        padding=24,
        max_width=620,
    )


def main():
    ui.app(
        build_root(),
        title="NovaUI Forms",
        theme=ui.Theme(appearance="glass"),
    )


if __name__ == "__main__":
    main()
