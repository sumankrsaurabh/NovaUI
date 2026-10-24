# Component reference

The canonical reference is [`COMPONENTS.md`](../../COMPONENTS.md). It documents
the implemented text, image, button, input, layout, data-table, form, routing,
feedback, shell, and theme APIs. The signatures below come from the current
public API; shared style properties are described in that reference.

```python
import novaui as ui

ui.Column(
    ui.Text("Dashboard", size=24, bold=True),
    ui.Button("Refresh", on_click=refresh),
    spacing=12,
    padding=20,
)
```

Not every roadmap component exists. Editable data grids, charts, rich text,
file explorers, uploads, and command palettes are planned, not part of the
current component API.
