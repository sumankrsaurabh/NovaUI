# NovaUI

NovaUI is an early-stage Python-first UI framework. Describe interfaces with Python components; a lightweight HTML, CSS, and JavaScript renderer displays the same UI in a browser or an optional desktop webview.

The project favors a small declarative API, ordinary Python for application logic, and explicit boundaries between Python events and browser rendering. **NovaUI is an MVP, not a production-ready or fully accessible framework.**

## What works today

- Browser UI with text, buttons, inputs, layout components, forms, routing, dialogs, and themes.
- Built-in solid and opt-in glass appearances, quieter border-led surfaces, icon-first buttons/navigation, semantic design tokens, and project-scoped CSS.
- Reactive `State` values and computed `Text` content refreshed after UI events.
- Searchable, sortable, filterable, selectable, paginated in-memory `DataTable`.
- Semantic top and side navigation plus responsive SVG line, bar, area, and doughnut charts with no charting dependency.
- `Scaffold` layouts with route-aware desktop sidebars, compact tablet rails, and mobile bottom navigation.
- Optional desktop hosting via `pywebview`, with window controls, file dialogs, text clipboard, shortcuts, and menus where the platform backend supports them.
- CLI for project creation, running apps, basic checks, and Python package builds.
- Explicit, trusted Python extensions for compositional components, named themes, and app-scoped services.
- Experimental `@NovaComponent` reusable function components and `@NovaPreview` previews, with hot reload in the VS Code source extension. Lowercase `@component` and `@preview` aliases remain supported.

Python 3.10 or newer is required. Browser mode is the default. Desktop mode needs `pywebview` plus a platform webview. NovaUI has been tested locally on Linux; CI is configured for additional OS and Python versions, but that is not the same as a completed release compatibility review.

## Install and run

NovaUI requires Python 3.10 or newer. The public source repository is
[sumankrsaurabh/NovaUI](https://github.com/sumankrsaurabh/NovaUI). NovaUI has
not yet been published to PyPI, so `pip install novaui` is not available yet.

Install this source checkout:

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
```

To install the current source without development tools, use
`python -m pip install .`. To build a wheel and source archive, use
`python -m pip install '.[build]'` followed by `python -m novaui build`.

Install directly from GitHub:

```bash
python -m pip install "git+https://github.com/sumankrsaurabh/NovaUI.git"
```

For a local clone and editable development install:

```bash
git clone https://github.com/sumankrsaurabh/NovaUI.git
cd NovaUI
python -m pip install -e '.[dev]'
```

The default branch may change without notice. A version-tag install becomes
available after the corresponding tag is published, for example
`python -m pip install "git+https://github.com/sumankrsaurabh/NovaUI.git@v0.1.0"`.
The PyPI command `python -m pip install novaui` will work after the first
package release.

Scaffold a project with the CLI:

```bash
novaui create hello_app
cd hello_app
novaui run --open-browser
```

For a desktop window, install the optional dependency and run your app in desktop mode:

```bash
python -m pip install -e '.[desktop]'
novaui run app.py --mode desktop
```

For the optional Qt webview backend:

```bash
python -m pip install -e '.[desktop-qt]'
```

Qt's license and platform requirements should be reviewed before redistributing
desktop applications. The base package has no runtime dependencies; `dev` and
`build` extras are only for maintainers.

Linux also needs a supported GTK/WebKitGTK or Qt/WebEngine backend and a graphical session. The `desktop-qt` extra installs Qt Python packages with their own license terms; see [desktop setup](docs/desktop/runtime.md) before distributing an application.

## Minimal app

```python
import novaui as ui

count = ui.state(0)

ui.app(
    ui.Column(
        ui.Text("Hello, NovaUI!", size=28, bold=True),
        ui.Text(lambda: f"Count: {count.value}"),
        ui.Button("Add", on_click=lambda: count.update(count.value + 1)),
        spacing=16,
        padding=24,
    ),
    title="Counter",
)
```

`Text` supports `bold=True`; there is no `weight` argument. Inputs can bind to `ui.state(...)`, and callback events are registered by opaque IDs. See the [first app tutorial](docs/getting-started/first-app.md) for a complete walkthrough.

## Documentation

- [Documentation index](docs/index.md)
- [Installation and first app](docs/getting-started/installation.md)
- [Component reference](COMPONENTS.md)
- [Design system: themes, glass surfaces, and tokens](docs/design-system.md)
- [Forms](FORMS.md) and [routing](ROUTING.md)
- [CLI reference](CLI.md)
- [Extension guide](EXTENSIONS.md)
- [Live preview guide](docs/live-preview.md) and [VS Code extension source](editors/vscode/README.md)
- [Security policy and limitations](SECURITY.md)
- [Tutorials](docs/tutorials.md)

The [`examples/`](examples/README.md) directory contains small runnable apps for reactive state, forms, routing and tables, themes, implemented components, and optional desktop dialogs. Run them from the repository root, for example `novaui run examples/dashboard.py`. The examples use only currently implemented APIs; they are not a promise that planned widgets such as charts or editable grids are available.

## Development and releases

```bash
python -m pip install -e '.[dev]'
PYTHONPATH=. python -m pytest -q
python -m ruff check novaui tests packaging
node --check novaui/frontend/app.js
python -m build --sdist --wheel
python -m twine check dist/*
```

HTTP tests need permission to bind loopback sockets. `novaui check` runs syntax/import/metadata checks and project tests; it is not a security audit. The repeatable release checklist is in [RELEASING.md](RELEASING.md). Do not publish artifacts without maintainer authorization.

## Current limitations

- The local server is for development and desktop use, not hardened public hosting. It has no user authentication or process isolation.
- Updates are requested after UI events; background state changes are not pushed live. The server returns the full component tree after interactions.
- Tables are in-memory and not virtualized. Editable grids, charts, rich-text editors, upload/download widgets, and command palettes are not implemented.
- Forms validate supported string fields synchronously. Repeat security-sensitive validation in trusted application services.
- Accessibility and cross-platform desktop behavior still need broader manual review. Desktop dialogs, menus, and clipboard support depend on the OS backend.
- Extensions execute trusted Python in-process; they are not sandboxed and are not automatically discovered.
- The public API is experimental before 1.0; see [contribution and compatibility guidance](CONTRIBUTING.md).

NovaUI is distributed under the MIT License. Contributions and security reports are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

To uninstall a source or PyPI installation, run `python -m pip uninstall novaui` in the same environment. Release builds and publication setup are documented in [RELEASING.md](RELEASING.md); publishing is intentionally a separate, maintainer-authorized step.
