# Master Prompt for Codex

Act as the lead engineer for NovaUI, a new Python-first declarative UI framework inspired by Kotlin Compose. Continue from this repository rather than generating a separate project.

Start by reading `AGENTS.md`, `CODEX.md`, `README.md`, `ARCHITECTURE.md`, and `ROADMAP.md`. Inspect the code, install development dependencies, and run the tests before editing.

Keep the API simple:
```python
import novaui as ui

count = ui.state(0)
ui.app(
    ui.Column(
        ui.Text(lambda: f"Count: {count.value}"),
        ui.Button("+", on_click=lambda: count.update(count.value + 1)),
        spacing=12,
        padding=24,
    )
)
```

This is the intended developer experience. The project uses Python for the API/runtime and HTML/CSS/JavaScript for rendering. Desktop mode embeds the same frontend in a webview. Do not describe this as native-widget rendering.

Implement the roadmap incrementally. First fix defects and establish reliable tests. Then improve state management, event lifecycle, input binding, accessibility, routing, desktop integrations, data components, performance, and documentation.

Never evaluate browser-provided Python or JavaScript as Python code. Use validated opaque event IDs. Keep the local development server bound to loopback unless a secure deployment mode is deliberately implemented.

After each milestone, run `pytest`, update documentation and roadmap, and report exactly what passed and what remains incomplete. Do not attempt a huge untested rewrite.
