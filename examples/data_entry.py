"""Validated data-entry form displaying submitted records in memory."""
import novaui as ui

records: list[str] = []
record_field = ui.Field(label="Record title", required=True, min_length=2, max_length=100)
status = ui.state("No records submitted yet.")


def save(values: dict[str, str]) -> None:
    records.append(values["title"])
    status.value = "Saved: " + ", ".join(records)


ui.app(ui.Column(
    ui.Text("New record", size=26, bold=True),
    ui.Form(fields={"title": record_field}, on_submit=save, submit_label="Save record"),
    ui.Text(lambda: status.value),
    spacing=16, padding=24,
), title="NovaUI Data Entry")
