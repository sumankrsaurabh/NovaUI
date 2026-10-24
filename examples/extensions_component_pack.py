"""Runnable compositional custom component example."""

import novaui as ui


class StatusBadge(ui.CustomComponent):
    def __init__(self, text: str, status: str = "success"):
        super().__init__()
        colors = {"success": "#087443", "warning": "#9a6700", "error": "#b42318"}
        if status not in colors:
            raise ValueError(f"Unsupported status: {status}")
        self.text = text
        self.color = colors[status]

    def render(self):
        return ui.Text(self.text, color=self.color, bold=True)


extensions = ui.Extensions()
extensions.register_component("StatusBadge", StatusBadge)

if __name__ == "__main__":
    ui.app(
        ui.Column(
            StatusBadge("Connected"),
            StatusBadge("Pending", "warning"),
            StatusBadge("Unavailable", "error"),
            spacing=12,
            padding=24,
        ),
        title="NovaUI Component Extension",
        extensions=extensions,
    )
