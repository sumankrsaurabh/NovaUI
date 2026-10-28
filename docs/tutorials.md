# Tutorials and runnable code

The repository includes a small set of runnable applications in
[`../examples/`](../examples/README.md). The guides below explain the same
features step by step so you can adapt them in your own project.

## Build your first app

Follow the [getting started guide](getting-started/first-app.md). It creates an
`app.py`, builds a small reactive counter, and runs it with either direct Python
execution or the NovaUI CLI.

## Continue learning

- [Installation](getting-started/installation.md)
- [Components](../COMPONENTS.md)
- [State and events](fundamentals/state-events.md)
- [Forms and validation](../FORMS.md)
- [Routing](../ROUTING.md)
- [Design tokens and themes](design-system.md)
- [Desktop runtime](desktop/runtime.md)
- [Live preview](live-preview.md)
- [Extension development](advanced/extensions.md)

## Small applications

From the repository root, run `novaui run examples/counter.py` for reactive
state, `novaui run examples/forms.py` for validation, and
`novaui run examples/dashboard.py` for routing and tables. The complete list,
including themes and desktop mode, is in the [examples guide](../examples/README.md).

The code snippets in the reference docs use the public API. Save them in your
own application module to run and adapt them.
