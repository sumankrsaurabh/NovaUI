"""Interactive login form with bound values and a submit status."""
import novaui as ui

email = ui.state("")
password = ui.state("")
submitted = ui.state(False)

ui.app(
    ui.Center(
        ui.Card(
            ui.Column(
                ui.Text("Welcome back", size=28, bold=True),
                ui.Text("Sign in to continue", color="#6b7280"),
                ui.Input(label="Email", placeholder="you@example.com", value=email),
                ui.Input(label="Password", placeholder="Enter password", password=True, value=password),
                ui.Button("Sign in", on_click=lambda: submitted.update(True), variant="primary"),
                ui.Text(lambda: f"Ready to sign in as {email.value}" if submitted.value else ""),
                spacing=14,
            ),
            padding=28,
            radius=18,
        )
    ),
    title="NovaUI Login",
    theme="dark",
)
