# NovaUI Architecture

## Direction

NovaUI uses a Python declarative API and a browser renderer. The same HTML/CSS/JavaScript frontend can run in a browser or inside a desktop webview. This is not a native-widget renderer.

## Layers

1. **Public API** (`novaui/__init__.py`): ergonomic exports.
2. **Components** (`novaui/components.py`): component definitions, validated layout/style properties, and JSON-safe serialization.
3. **State** (`novaui/state.py`): mutable state objects with subscriptions and dependency collection for computed `Text` values.
4. **Runtime** (`novaui/app.py`, `novaui/server.py`): lifecycle, HTTP endpoints, event registry.
5. **Frontend** (`novaui/frontend/`): DOM renderer, CSS tokens, event bridge.
6. **Desktop host** (`novaui/app.py`, `novaui/desktop.py`): optional `pywebview` adapter over the same local HTTP frontend, with validated window options and a per-window facade.
7. **Application logic** (`novaui/forms.py`, `novaui/routing.py`, `novaui/shell.py`, `novaui/feedback.py`): Python-side form state/validation, route matching, layout compositions, and event-backed feedback controls.
8. **Native adapters** (`novaui/dialogs.py`, `novaui/clipboard.py`, `novaui/window.py`, `novaui/shortcuts.py`): explicit desktop-only OS access and per-application shortcut registrations.
9. **Developer tooling** (`novaui/cli.py`, `novaui/project.py`): argparse commands, starter templates, project options, and a context-local project root for runtime asset resolution.
10. **Data components** (`novaui/data_table.py`): validated column definitions and server-owned table interaction state.

## Component and layout pipeline

Component instances serialize to a small JSON tree. The browser renderer (`novaui/frontend/app.js`) maps the known component types to DOM elements and updates existing elements by stable ID. `Row` and `Column` use Flexbox, `Grid` uses CSS Grid with responsive integer-column presets, `Wrap` uses wrapping Flexbox, `ScrollView` uses overflow scrolling, and `Stack` overlays children in one grid cell. `Container`, `Card`, and `Center` provide box, surface, and centering behavior.

Shared visual properties serialize as style tokens and are applied with DOM `style` APIs. The Python layer validates class names, common CSS lengths, and a constrained style-property allowlist; it rejects CSS URL and expression values. `Theme` serializes its validated mode, primary color, radius, font family, and optional semantic palette overrides into an allowlist of CSS variables. Omitted palette values preserve the built-in light/dark defaults. The server never evaluates browser-supplied code.

## Event flow

1. Python builds a component tree and registers handlers with random 256-bit event IDs.
2. The browser requests `/api/tree` with the private `X-NovaUI-Request: tree` fetch header; this blocks simple cross-site requests from embedding the endpoint as an image or form target.
3. The frontend renders safe, known component types using DOM APIs.
4. A user event posts an event ID and, for a bound input, a validated string value to `/api/event`.
5. Python invokes only the handler registered for that ID; each ID is single-use.
6. The server returns the serialized tree. Stable component IDs let the frontend reuse unchanged DOM nodes and update changed properties in place.

The browser never sends source code or callable names.

## Desktop lifecycle and native features

`App.run(desktop=True)` lazily imports optional pywebview, binds the existing server to `127.0.0.1` on port `0` by default, starts the server thread, then creates a webview window pointed at the selected port. The GUI loop runs on the main thread. On close or startup failure, the HTTP server is shut down, its socket is closed, its thread is joined, and the component tree is disposed. Desktop mode rejects non-loopback hosts.

`WindowOptions` validates sizes, minimum sizes, booleans, and a `#RRGGBB` background. `DesktopWindow` wraps a specific pywebview window instance; it does not rely on a process-global active window. The active desktop window is carried through a `ContextVar` only while registered application events execute. Native file dialogs use pywebview. The text clipboard uses Python's optional-at-build-time Tkinter module and reports unavailable Tk/clipboard environments. Menu items are converted to pywebview native menu objects; GTK does not support those menu objects. Shortcut definitions are application-owned and serialized to the existing frontend as opaque event IDs; they do not expose Python names or source code.

The desktop runtime does not expose a general JavaScript-to-Python bridge. The renderer posts registered opaque event IDs through the local HTTP endpoint. The server requires loopback Host values and same-origin `application/json` event requests, bounds concurrent workers and request reads, and limits served project assets to 32 MiB. Responses include a restrictive Content Security Policy, frame denial, and no-referrer policy. Loopback and origin checks reduce browser-based request risk, but do not authenticate local processes or make this a production server.

## CLI and project assets

The CLI runs the same Python entry point through `runpy`; it does not implement a second app runtime. `novaui run` applies project settings from `[tool.novaui]` (CLI flags override config, which overrides defaults) and enforces loopback binding. The CLI carries the entry point's parent as a `ContextVar` while the app is constructed. `App` captures this asset root; direct script launches infer it from `sys.argv[0]`, while interactive launches use the current working directory.

`Image` serializes a relative asset URL under `/assets/`. The HTTP handler decodes the request path, resolves it under `<asset_root>/assets`, checks the resolved target remains inside that directory (including symlinks), and serves a guessed MIME type or 404. Files above 32 MiB are rejected. No arbitrary filesystem path is accepted, and NovaUI does not bundle or transform static files.

`novaui check` compiles project Python sources, verifies NovaUI imports and basic `[project]` name/version metadata, then runs pytest if a tests directory exists. `novaui build` delegates source/wheel creation to the standard `build` frontend; it is an optional development tool, not a runtime dependency. Hot reload and standalone executable packaging are not part of the CLI.

## Data table

`DataTable` validates its `ColumnDef` objects and row mappings during serialization. It applies sort, search, per-column filters, selection, and pagination in Python, then sends only the visible page's formatted cell strings and registered opaque event IDs to the renderer. A `State[list[Mapping]]` is re-read whenever a tree is requested. Formatting returns plain scalar text and the frontend sets it with `textContent`; cell formatters cannot inject HTML. Row click and row-action handlers are registered for that tree and are subject to the existing one-shot event lifecycle. Sorting and filtering currently scan the full in-memory dataset; the table has no virtualization and the local Python timings below do not characterize large-dataset browser responsiveness.

## Local Python performance baseline

Run `env PYTHONPATH=. .venv/bin/python benchmarks/runtime.py` to reproduce the framework-only baseline. On Linux 7.0.0-31-generic x86_64 with CPython 3.14.4, median times across 7 runs were: construct an App with 100 `Text` children, 0.203 ms; serialize that tree, 0.306 ms; notify one state subscriber, 0.000418 ms; dispatch a button event plus serialize the next tree, 0.010 ms; bind and close the HTTP listening socket without serving requests, 0.103 ms. The 3-column DataTable serialization medians were 0.195 ms for 100 rows, 1.163 ms for 1,000 rows, and 6.557 ms for 5,000 rows, with traced peaks of 16.5, 70.0, and 884.5 KiB respectively. General operations use 100 iterations/run; event and socket operations use 20, and DataTable operations use 10. DataTable memory excludes source data; no browser engine, frontend layout/paint, network round trip, full threaded-server shutdown, or desktop startup is included. These are local baselines, not cross-framework claims.

## Forms and navigation

`Field` owns a string `State`; `Form` binds fields to existing `Input` components and validates submitted values before calling application code. Form event bodies are bounded mappings of safe field names to strings. Validation callback errors and submission errors are returned as generic messages; logs include only the exception type. Form callbacks are synchronous. This is local application logic, not a replacement for validation in trusted services.

`Router` resolves exact static paths and single-segment `{parameter}` patterns in Python. The frontend requests `/api/tree?path=...`; `server.py` serves a fixed `index.html` for non-API paths, so route paths cannot expose files. Browser navigation updates the URL with History API and reloads the Python component tree on `popstate`. The current page factory cache is in-memory. `ui.navigate()` is scoped to the callback currently being dispatched.

`AppShell`, `Tabs`, `Alert`, `Spinner`, and `Dialog` are composed or rendered through the same known-component renderer. Dialog confirm and cancel have separate registered event IDs.

## Extension boundary

`novaui/extensions.py` provides explicit extension configuration. Each `App` copies component, theme, and plugin registrations so services and extension names remain app-scoped. `CustomComponent` composes one cached NovaUI component subtree and delegates serialization to the existing known-component renderer; it cannot emit raw markup or script. Named `Theme` instances use the same token serialization as inline themes. Plugins are application-supplied trusted Python objects: setup is run at app construction, runtime hooks run in deterministic order, and start hooks are unwound in reverse order on shutdown or startup failure. Optional version and module checks use the standard library. Entry-point discovery, sandboxing, renderer plugins, and a stable binary/plugin ABI are intentionally absent.

`App.set_theme()` changes the theme used by the next serialized tree, allowing callbacks to switch themes through the existing full-tree event response. The Phase 11 Studio and Admin apps exercise this path. Component metadata is not currently machine-readable, so Studio maintains a curated app-level catalogue. The PyOffice validation app demonstrates native file dialogs and bounded plain-text persistence; NovaUI does not yet provide multiline text editing, charts, or editable grids.

## Security boundary and limitations

The development server accepts only loopback bind hosts (`127.0.0.1` or `localhost`), validates the Host authority, requires the private fetch header for tree requests, and requires a matching loopback Origin plus JSON content type for event POSTs. Requests without Origin are rejected. The server caps event bodies at 16 KiB, bounds active request workers to 32, sets a 10 second socket timeout, and refuses project assets larger than 32 MiB. The frontend uses known component types and DOM text APIs; the server does not evaluate browser-provided code. See [SECURITY.md](SECURITY.md) for the threat model and reporting policy.

These checks do not provide authentication, per-user sessions, isolation from other processes running as the same user, or hardened public hosting. Callback and route code is application code and runs synchronously in a request thread. Desktop applications still expose their local endpoint to processes able to reach loopback. The current browser frontend requires inline style attributes through DOM style properties, so the CSP allows inline styles while restricting scripts to same-origin files.

## Important MVP limitations

- The handler registry is in-memory and intended for one local application session.
- The development server binds to loopback.
- The renderer is intentionally small; components are not yet fully accessible or production hardened.
- Visual components support validated integer pixel `width` and `height`; shared min/max constraints and margins accept CSS lengths. Width and height themselves remain integer pixels in this release.
- Form fields are strings and currently render text, email, password, number, and date inputs. Checkbox, radio, select, textarea, native date object conversion, async callbacks, and persistent settings are not implemented.
- Router route factories and event handlers run synchronously in bounded server request threads. There is no authentication, production session isolation, or hardened public hosting mode.
- Dialogs are basic native HTML dialogs; focus restoration and complete assistive-technology behavior need further review. `Toast` and global imperative `ui.confirm()` do not exist.
- The server still serializes the full tree after each event. The frontend reuses existing DOM nodes, but the protocol does not yet send narrow property patches.
- `Text` tracks `State.value` reads, caches computed text until a dependency changes, and releases its subscriptions when its owning `App` is disposed. Updates from background Python code are not pushed to browsers without a subsequent tree request.
- Inputs support `State[str]`, optional `on_change`, text/email/password/number/date types, disabled, and read-only modes. They commit on browser `change`; values are limited to 8,000 characters. `on_change` can return a text error message, which is safely displayed and associated with the field. `Form` validates on change and submit.
- Event request bodies are limited to 16 KiB. Event IDs are single-use and expire when the tree is serialized again. The registry contains handlers for the current tree only.
- Desktop mode requires a platform webview backend in addition to pywebview. Linux users can install the optional Qt extra; host display and system-library issues remain outside NovaUI's runtime.
- The tested backend API targets pywebview 6.2; legacy dialog constants are used as a fallback for older supported pywebview releases. Windows WebView2/.NET, macOS Cocoa/WebKit, and Linux GTK/WebKit or Qt/WebEngine dependencies remain OS-managed. No Windows or macOS GUI run has been performed from this environment.
- Native open/save dialogs return a selected path or `None`; NovaUI never opens or writes the selected path automatically. The current pywebview API has no file-dialog title option. Clipboard support is text-only through Tk and depends on a working desktop clipboard service. Native menus are not supported by GTK; context menus, app icons, and notifications are not included.
- `Mod` shortcuts map to Ctrl on Windows/Linux and Meta/Command on macOS. They are ignored in text-entry elements unless explicitly allowed. Browser/OS shortcut conflicts are possible.
- PyInstaller configuration is a sample and has not been run. A frozen app still relies on platform webview/system libraries and should be built and tested on its target OS.

## Planned evolution

Next: broader form controls, robust route lifecycle and async callbacks, narrower property-patch delivery, push updates for background state changes, accessibility standards, hot reload, and verified distribution packaging. See `ROADMAP.md`.
