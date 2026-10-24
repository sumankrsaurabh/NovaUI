"""Registration form with Python-side validation and feedback."""
import novaui as ui

name = ui.Field(label="Name", required=True, min_length=2, max_length=80)
email = ui.Field(label="Email", input_type="email", required=True)
password = ui.Field(label="Password", input_type="password", required=True, min_length=8)
message = ui.state("")


def register(values: dict[str, str]) -> None:
    # A real application must repeat sensitive validation on its trusted server.
    message.value = f"Registration ready for {values['name']} ({values['email']})."


ui.app(
    ui.Center(ui.Card(ui.Column(
        ui.Text("Create your account", size=28, bold=True),
        ui.Form(fields={"name": name, "email": email, "password": password}, on_submit=register),
        ui.Text(lambda: message.value),
        spacing=16,
    ), padding=24)),
    title="NovaUI Registration",
)
