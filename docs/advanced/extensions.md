# Extensions

NovaUI's extension API is explicit and app-scoped. Register compositional
components, named themes, or trusted plugin instances using `ui.Extensions`,
then pass it to `ui.App`, `ui.app`, or `ui.desktop`.

```python
extensions = ui.Extensions()
extensions.register_theme(ui.Theme(name="brand", primary="#3157D5"))
ui.app(ui.Text("Themed"), theme="brand", extensions=extensions)
```

Custom components subclass `ui.CustomComponent` and return one built-in
component from `render()`. Plugins can implement `setup(app)`,
`on_app_start(app)`, and `on_app_stop(app)` and register services on that app.
See the full [extension guide](../../EXTENSIONS.md) and the three runnable
`examples/extensions_*.py` files.

Plugins execute trusted Python in-process; they are not sandboxed. NovaUI does
not auto-discover installed plugins, load arbitrary paths, or provide a stable
plugin ABI.
