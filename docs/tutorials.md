# Tutorials and runnable examples

All scripts below run from the repository root after installing NovaUI with
`python -m pip install -e .`. Browser scripts open a local browser by default.
Desktop examples require the optional desktop setup and a graphical session.

## A. Your first application

Start with [first-app.md](getting-started/first-app.md), then run
`python examples/landing.py` to see nested layouts and a theme.

## B. Reactive state

Run `python examples/counter.py`. It creates state with `ui.state(0)`, reads it
from a computed `Text`, and updates it from button callbacks. Input-bound state
is shown in `python examples/reactive_input.py`.

## C. Forms and validation

Run `python examples/registration.py` for required, length, and email validation
with submission feedback. `python examples/form_validation.py` shows the
`Input.on_change(value)` error-message callback. Form values are strings and
validation does not replace trusted server-side checks; see [Forms](../FORMS.md).

## D. Multi-page application

Run `python examples/routed_dashboard.py` and use Dashboard/Settings navigation
and browser back/forward. The example combines `Router`, `AppShell`, `Sidebar`,
`NavigationItem`, `Header`, `MainContent`, and `Footer`. Routes are Python
component factories, not filesystem paths; see [Routing](../ROUTING.md).

## E. Dashboard and data table

Run `python examples/dashboard.py` for a responsive dashboard layout or
`python examples/employee_table.py` for search, sort, filtering, row selection,
pagination, and row actions. Charts are not implemented yet.

## F. Desktop application

Install `.[desktop]`, then run `python examples/desktop_window.py`. Try
`desktop_native.py` for file dialogs and `desktop_clipboard.py` for text
clipboard access. These examples need a working platform GUI backend; they
cannot be verified by the headless serialization smoke check.

## G. Custom components

Run `python examples/extensions_component_pack.py`. `StatusBadge` returns a
built-in `Text` component and is registered in an app-scoped `Extensions`
configuration. Use `ui.CustomComponent` and the public registration methods;
do not bypass the renderer with raw markup.

## H. Plugin and extension lifecycle

Run `python examples/extensions_service_plugin.py` to see plugin setup, service
registration, and app start/stop hooks. Run `python examples/extensions_theme_pack.py`
for named light/dark themes. Python plugins
are trusted in-process code, not sandboxed. See [EXTENSIONS.md](../EXTENSIONS.md).

Additional scripts are catalogued in the root [README](../README.md). Examples
are demonstrations, not a substitute for platform-specific GUI testing.

## Example gallery

| Example | Command | Coverage |
| --- | --- | --- |
| Counter | `python examples/counter.py` | State and button events |
| Login | `python examples/login.py` | Controlled text and password inputs |
| Registration | `python examples/registration.py` | Validated form |
| Data entry | `python examples/data_entry.py` | Form submission and in-memory records |
| Settings | `python examples/settings_app.py` | Tabs and reactive state |
| Routed dashboard | `python examples/routed_dashboard.py` | Routes, browser history, app shell |
| Employee directory | `python examples/employee_table.py` | `DataTable` interactions |
| Dashboard | `python examples/dashboard.py` | Layouts and cards |
| Landing page | `python examples/landing.py` | Responsive layouts and theme tokens |
| Component pack | `python examples/extensions_component_pack.py` | Custom component registration |
| Theme pack | `python examples/extensions_theme_pack.py` | Named light/dark themes |
| Service plugin | `python examples/extensions_service_plugin.py` | Plugin hooks and service registry |
| Desktop window | `python examples/desktop_window.py` | Window options and controls |
| Native dialogs | `python examples/desktop_native.py` | Open/save path selection |
| Clipboard | `python examples/desktop_clipboard.py` | Text clipboard |
| Shortcuts | `python examples/desktop_shortcuts.py` | `Mod+S` shortcut |
| Native menu | `python examples/desktop_menu.py` | pywebview menu |
| Shared application | `python examples/shared_app.py --desktop` | Browser/webview shared app |
| NovaUI Studio | `python -m examples.phase11_studio.app` | Curated component playground and inspector |
| NovaUI Admin | `python -m examples.phase11_admin.app` | Routed admin flows, forms, data table, confirmations |
| PyOffice Notes | `python -m examples.phase11_pyoffice.app` | Bounded plain-text desktop open/save workflow |

See the [Phase 11 validation guide](phase11-applications.md) for app-specific
limitations, persistence behavior, tests, and the framework gap register.
