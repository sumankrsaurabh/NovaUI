# Your first application

Create `app.py` in a project directory:

```python
import novaui as ui

count = ui.state(0)

def MainPage() -> ui.Component:
    return ui.Column(
        ui.Text("Hello, NovaUI!", size=28, bold=True),
        ui.Text(lambda: f"Count: {count.value}"),
        ui.Button("Add", on_click=lambda: count.update(count.value + 1)),
        spacing=16,
        padding=24,
    )

if __name__ == "__main__":
    ui.app(MainPage(), title="First NovaUI app")
```

From the project directory, run:

```bash
python app.py
```

The direct app API opens the browser by default. With NovaUI installed, the CLI
can run the same entry point without changing its UI code:

```bash
novaui run app.py --mode web --open-browser
```

`Text` accepts `bold=True`; it does not currently accept a font `weight`
parameter. The button callback is Python code registered by NovaUI. The browser
sends a generated event ID, never source code. For live input examples, see
[state and events](../fundamentals/state-events.md).
