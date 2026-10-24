# NovaUI Extensions

NovaUI 0.1 exposes a small, explicit extension API for Python code trusted by
the application owner. Extensions run in the application process with the same
permissions as the application. They are **not sandboxed**. NovaUI does not
automatically discover or execute installed plugins.

## Per-application registration

Create an `Extensions` configuration, register additions, then pass it to
`ui.App`, `ui.app`, or `ui.desktop`. An `App` copies the registrations so
separate applications do not share service/component/theme registries.
Plugin objects themselves are the instances supplied by the caller; create a
fresh `Extensions` object and plugin instance for each independently configured
application if the plugin stores mutable per-app state.

```python
import novaui as ui

class StatusBadge(ui.CustomComponent):
    def __init__(self, text: str, status: str = "ok"):
        super().__init__()
        if status not in {"ok", "error"}:
            raise ValueError("status must be 'ok' or 'error'")
        self.text, self.status = text, status

    def render(self) -> ui.Component:
        color = "#087443" if self.status == "ok" else "#b42318"
        return ui.Text(self.text, color=color, bold=True)

extensions = ui.Extensions()
extensions.register_component("StatusBadge", StatusBadge)
ui.app(ui.Column(StatusBadge("Connected")), extensions=extensions)
```

Custom components subclass `CustomComponent` and implement `render()` to
return one NovaUI `Component`. NovaUI caches that returned subtree per instance
and sends it through the ordinary renderer and event registry. Common styling
on a custom instance uses the existing `Container` renderer, which adds a
wrapper only when styling is set. Custom components cannot return raw HTML,
JavaScript, renderer instructions, or arbitrary JSON. Names must start with a
letter and contain up to 64 ASCII letters, digits, or underscores. Duplicate
names in one registry are rejected. A custom component must be registered in
each `Extensions` configuration used by an app.

## Themes

`Theme` supports validated `mode`, `primary`, `radius`, and `font_family`
tokens. A named theme can be registered and selected by name:

```python
extensions = ui.Extensions()
extensions.register_theme(ui.Theme(
    name="corporate", mode="light", primary="#3157D5", radius="10px",
))
ui.app(ui.Text("Hello"), theme="corporate", extensions=extensions)
```

Theme registration rejects unnamed themes and duplicate names. The selected
theme is serialized using the same renderer tokens as an inline `Theme`; it
does not merge with another theme. Application selection wins because exactly
one theme is sent to the frontend.

## Plugins and services

Plugins are explicit trusted Python instances. Their unique `name` is required.
The optional `setup(app)` runs once while the `App` is constructed. Plugins may
register app-scoped services through `app.register_service(name, service)`;
application callbacks can retrieve them using `app.get_service(name)`. Duplicate
service names are errors.

```python
class MetricsPlugin:
    name = "metrics"
    min_novaui_version = "0.1.0"  # inclusive
    max_novaui_version_exclusive = "1.0.0"
    optional_dependencies = ("my_metrics_package",)

    def setup(self, app: ui.App) -> None:
        app.register_service("metrics", MetricsService())

    def on_app_start(self, app: ui.App) -> None:
        app.get_service("metrics").start()

    def on_app_stop(self, app: ui.App) -> None:
        app.get_service("metrics").stop()

extensions = ui.Extensions()
extensions.use(MetricsPlugin())
application = ui.App(ui.Text("Metrics enabled"), extensions=extensions)
application.run()
```

Setup runs in registration order. Version checks use `major.minor.patch`, with
an inclusive minimum and exclusive maximum. Missing optional modules and
incompatible NovaUI versions fail app construction with an actionable error.
`on_app_start(app)` runs in registration order immediately before runtime
startup; `on_app_stop(app)` runs in reverse order for every plugin whose start
hook began, including when a later startup hook fails. A startup failure stops
the application instead of continuing with partial functionality. Shutdown
hook failures are logged by exception type and do not prevent other plugins or
app resources from being cleaned up. Hooks are synchronous.

Plugins should keep `setup` limited to registration/configuration and allocate
runtime resources in `on_app_start`, releasing them in `on_app_stop`. NovaUI
does not provide process isolation, permission prompts, dependency solving, or
automatic package entry-point discovery. Importing a plugin module executes
Python code; only import plugins that you trust.

## Public API and limitations

The supported extension surface is `Extensions`, `CustomComponent`, named
`Theme`, `App.register_component`, `App.register_theme`,
`App.register_service`, `App.get_service`, and the three plugin hooks above.
The component registry, renderer serialization format, and frontend protocol
remain internal and may change. There is no extension marketplace, hot reload,
remote plugin support, sandbox, or stable plugin ABI guarantee in NovaUI 0.1.
For a sample of each extension type, run `examples/extensions_component_pack.py`,
`examples/extensions_theme_pack.py`, or `examples/extensions_service_plugin.py`.
