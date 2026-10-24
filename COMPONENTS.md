# NovaUI Component Reference

This reference documents components currently implemented by NovaUI. Components are Python objects that serialize to a validated tree and render through the shared HTML/CSS/JavaScript frontend.

## Shared properties

All current components accept these keyword-only properties:

| Property | Accepted values | Default | Behavior |
| --- | --- | --- | --- |
| `margin` | pixel integer or CSS length; margin also accepts 1–4 CSS length tokens | `None` | Outer spacing |
| `min_width`, `max_width`, `min_height`, `max_height` | pixel integer or CSS length | `None` | CSS min/max size |
| `background`, `border`, `shadow` | safe CSS value string | `None` | Inline visual token |
| `visible` | `bool` | `True` | Hides the rendered element when false |
| `class_name` | CSS class names separated by spaces | `None` | Adds classes to the rendered element |
| `style` | Mapping of allowed CSS property names to strings or numbers | `None` | Applied with DOM style properties; numbers use pixels except unitless CSS properties |

Style values reject declaration delimiters, markup delimiters, `url()`, and `expression()`. Supported custom style properties include color, background color, borders, typography, spacing, overflow, and grid columns. Component-specific properties take precedence where they set the same CSS property.

The visual components `Text`, `Button`, `Image`, `Input`, `Card`, `Center`, `Container`, `Grid`, `ScrollView`, `Stack`, `Wrap`, and `Spacer` also accept `width` and `height` as non-negative integer pixels.

## Content and controls

### `Text(text, size=None, bold=False, color=None)`

Renders text with `textContent` (never as HTML). `text` may be a string or zero-argument callable. Callables track reads from `State` instances and recalculate when those states change. `size` is a non-negative pixel integer; `bold` is a bool; `color` is a CSS color string.

### `Image(src, alt, width=None, height=None)`

Displays a local file from the app's `assets/` directory, for example `ui.Image("assets/logo.png", alt="NovaUI logo")`. `alt` is required. Absolute paths, parent-directory traversal, and paths outside `assets/` are rejected. The CLI resolves assets relative to the entry-point directory; direct Python launches use the working directory. Other static files can be requested at `/assets/<path>` without a bundler.

### `Button(label, on_click=None, disabled=False, variant="primary")`

Renders a keyboard-operable button. `on_click` is registered with an opaque one-shot event ID. `variant` is `primary` or `secondary`.

### `Input(placeholder="", value="", password=False, label=None, on_change=None, disabled=False, read_only=False, input_type="text", ...)`

Renders a text or password field. `value` may be a string or `State[str]`. When bound or when `on_change` is supplied, the browser sends the changed string through the validated event bridge. `on_change(value)` may return an error string or `None`; errors are rendered as text and associated with the field.

`input_type` supports `text`, `email`, `password`, `number`, and `date`; `password=True` remains a shorthand for password type. Optional `name`, `required`, `min_length`, `max_length`, `min_value`, and `max_value` set the corresponding field semantics and are validated in Python. See [Forms](FORMS.md) for Python-side `Field`/`Form` validation.

## Layouts

### `Animated(child, enter="fade", duration=240, easing="ease-out")`

Wraps one component and applies a CSS entrance animation the first time that component node is mounted. Presets are `fade`, `fade_up`, `fade_down`, `slide_in`, `scale_in`, and `pop`; easing is one of `linear`, `ease`, `ease-in`, `ease-out`, or `ease-in-out`; duration is an integer from 0 to 2000 milliseconds. Nested child behavior and events use the normal component renderer. The wrapper remains mounted during state updates, so the entrance effect does not replay on each update. Exit animation is not supported because the current reconciliation lifecycle removes obsolete nodes immediately. The frontend honors `prefers-reduced-motion` for animations, transitions, and the spinner.

All layout constructors accept child components as positional arguments. Empty layouts render as empty elements.

### `Row(*children, spacing=8, padding=0, align="center", justify="start")`

Flexbox horizontal layout. `align` accepts `start`, `center`, `end`, `stretch`, or `baseline`; `justify` accepts `start`, `center`, `end`, `between`, `around`, or `evenly`. Rows wrap on narrow screens.

### `Column(*children, spacing=8, padding=0, align="stretch", justify="start")`

Flexbox vertical layout, with the same alignment options as `Row`.

### `Card(*children, padding=16, radius=12)`

Surface section with theme background, border, and shadow defaults. `radius` is a non-negative pixel integer.

### `Center(child)`

Centers one child using Flexbox.

### `Container(*children, padding=0)`

Generic box for sizing and shared visual properties.

### `Grid(*children, columns=2, spacing=8, padding=0)`

CSS Grid layout. `columns` is an integer from 1 to 12 or a CSS grid-template string. Integer templates use equal-width columns and collapse to two columns on tablet widths and one on narrow screens when the configured count is greater than one.

### `ScrollView(*children, direction="vertical", padding=0)`

Scrollable container. `direction` is `vertical`, `horizontal`, or `both`. Use `height`, `width`, `max_height`, or `max_width` to constrain its viewport.

### `Stack(*children)`

Overlays children in a shared CSS Grid cell. Give the stack dimensions or constrain it through shared min/max properties when needed.

### `Wrap(*children, spacing=8, run_spacing=8, align="start")`

Wrapping Flexbox layout. `spacing` sets horizontal gaps; `run_spacing` sets gaps between wrapped lines. `align` is `start`, `center`, `end`, or `stretch`.

### `Spacer(size=8)`

Flexible empty space in a row or column. `size` is a non-negative pixel minimum.

## Data components

### `ColumnDef(key, title=None, width=None, sortable=True, formatter=None)`

Defines one table column. Keys must be unique valid field names and must exist in every row. `width` accepts non-negative pixel integers or supported CSS lengths. `formatter(value, row)` may return text or a scalar; results are always rendered as text, never HTML.

### `DataTable(columns, data, selectable=False, sortable=True, searchable=True, filterable=True, page_size=20, ...)`

Renders a semantic, horizontally scrollable table. `data` is a sequence of mappings or a `State` containing one. Header buttons sort ascending/descending; a global search box and per-column filter fields update server-owned filters. Pagination is one-based. Select-all applies to the visible page; `on_selection_change(rows)` receives all currently selected records. Use `row_key` for a unique stable field; without it, selection keys use the source row positions.

`on_row_click(row)` handles accessible mouse and Enter/Space activation of a row. `row_actions` accepts `RowAction(label, on_click)` items and calls each callback with the row. `loading=True` disables actions and shows a loading status. `empty_message` controls the empty-state copy.

```python
ui.DataTable(
    columns=[ui.ColumnDef("name", title="Employee"), ui.ColumnDef("salary")],
    data=[{"id": 1, "name": "Alice", "salary": 65000}],
    row_key="id",
    selectable=True,
    page_size=20,
)
```

The table scans/sorts the in-memory dataset on each tree request but sends only the current page's formatted rows to the browser. It is intended for small and medium datasets; it has no virtualization. Search/filter callbacks update the table after the browser `change` event, and NovaUI currently returns the full application tree after each interaction.

Local baseline (Linux 7.0.0-31-generic x86_64, CPython 3.14.4; median across 7 runs, 10 serializations per run, 3 columns sorted descending, page size 20; one additional `tracemalloc` serialization): 100 rows — 0.195 ms / 16.5 KiB; 1,000 rows — 1.163 ms / 70.0 KiB; 5,000 rows — 6.557 ms / 884.5 KiB. Source data is allocated before tracing. Timing excludes browser rendering and HTTP dispatch; memory excludes source data. The reproducible Python-only baseline, including tree construction, state notification, event dispatch, and server socket bind/close, is `env PYTHONPATH=. .venv/bin/python benchmarks/runtime.py`. Figures are environment-specific, not a performance guarantee; full sorting/filtering scans all rows.

## Forms, navigation, and feedback

- `Field(value="", label=None, input_type="text", required=False, min_length=None, max_length=None, min_value=None, max_value=None, validator=None, disabled=False)` tracks a string value, dirty state, and validation result.
- `Form(fields=..., on_submit=..., submit_label="Submit", reset_label="Reset", disabled=False, loading=False)` validates submitted string values in Python. It exposes `values`, `errors`, `dirty_fields`, `revalidate()`, `reset()`, and `submit(values)`.
- `Router(routes=..., not_found=None)` maps paths to components or factories. Route factories accept `{parameter}` path values; `params`, `query_params`, and `current_path` describe the resolved URL. Call `ui.navigate(path)` from a component event callback.
- `AppShell`, `Header`, `Sidebar`, `MainContent`, `Footer`, `NavigationItem`, and `Breadcrumbs` compose the standard layout components. `Sidebar(collapsed=True)` selects a narrow width; it does not provide interactive collapse state.
- `Tabs({label: component}, selected=None)` serializes the selected panel and supports a `State[str]` selection.
- `Alert(message, kind="info")` accepts `info`, `success`, `warning`, or `error`; `Spinner(label="Loading")` displays a status indicator.
- `Dialog(title, child, open=False, on_confirm=None, on_cancel=None, confirm_label="Confirm", cancel_label="Cancel")` provides separate confirm and cancel events. Pass `State[bool]` for controlled visibility.

See [Forms](FORMS.md) and [Routing](ROUTING.md) for runnable examples and security limits. Checkboxes, radio groups, select, textarea, toast queues, and asynchronous form handlers are not implemented.

## Shell, theme, and application APIs

- `AppShell(*children, **shared_props)` composes its children in the standard shell layout. `Header`, `MainContent`, and `Footer` are layout helpers with the same child-first convention.
- `Sidebar(*children, collapsed=False, **shared_props)` renders a sidebar; `collapsed` chooses a narrow width and is not an interactive toggle. `NavigationItem(label, href, active=False)` renders a navigation link. `Breadcrumbs(items)` accepts labels or `(label, href)` pairs.
- `Theme(mode="light", primary="#6558d3", radius="10px", font_family="Inter, ui-sans-serif, system-ui, sans-serif", name=None, background=None, surface=None, foreground=None, muted=None, border=None, primary_hover=None)` validates theme tokens. Optional colors override `--bg`, `--surface`, `--text`, `--muted`, `--border`, and `--primary-hover`; omitted values retain the built-in light/dark palette. `name` is used for explicit extension registration; it is omitted from renderer output. See [extensions](EXTENSIONS.md).
- `State(value)` and `ui.state(value)` provide mutable Python state. Read and assign `.value`, call `.update(value)`, subscribe with `.subscribe(callback)`, and release listeners with `.dispose()`.
- `App(root, title="NovaUI", theme="light", host="127.0.0.1", port=0, debug=False, extensions=None)` creates a runtime object. `App.set_theme(theme)` accepts `"light"`, `"dark"`, an app-registered theme name, or a `Theme` instance; call it in an event callback to change tokens on the next tree render. `ui.app(root, title=..., theme=..., debug=False, host="127.0.0.1", port=0, extensions=None)` creates and immediately runs it. `ui.desktop(root, title=..., theme=..., width=1200, height=800, min_width=200, min_height=100, resizable=True, fullscreen=False, frameless=False, background_color="#FFFFFF", debug=False, menu=(), on_close=None, extensions=None)` runs it in the optional webview host.
- `WindowOptions(width=1200, height=800, min_width=200, min_height=100, resizable=True, fullscreen=False, frameless=False, background_color="#FFFFFF")` carries validated desktop settings. `Menu(title, items)`, `MenuItem(title, callback)`, and `MenuSeparator()` describe supported native menu entries.
- `ShortcutRegistry.register(shortcut, callback, prevent_default=True, allow_in_inputs=False, replace=False)` accepts combinations such as `Mod+S`; `unregister(shortcut)`, `set_enabled(shortcut, enabled)`, and `clear()` manage registrations. Callbacks take no arguments. `Mod` resolves to Ctrl on Windows/Linux and Meta on macOS; shortcuts are ignored in input controls unless opted in.
- Extension APIs are `Extensions.register_component(name, CustomComponentSubclass)`, `register_theme(named_theme)`, and `use(plugin_instance)`. `CustomComponent.render()` returns a built-in component. See [the extension guide](EXTENSIONS.md) for plugin hooks, compatibility attributes, and trust limitations.

Window controls, file dialogs, clipboard, and shortcuts are runtime integrations rather than visual components. Their support depends on the desktop backend; see [native desktop APIs](docs/desktop/native-apis.md). The root-level `ui.window`, `ui.dialogs`, and `ui.clipboard` modules are only usable from an active desktop event callback.

## Themes

Pass a `Theme` to `ui.app` to set CSS variables:

```python
theme = ui.Theme(
    mode="light",
    primary="#635BFF",
    radius="12px",
    font_family="Inter, sans-serif",
    background="#f7f8fc",
    surface="#ffffff",
    foreground="#202333",
)
ui.app(ui.Text("Hello"), theme=theme)
```

`mode` is `light` or `dark`; color fields must be CSS color names, hex, RGB, or HSL values; `radius` is a non-negative pixel integer or CSS length; and `font_family` accepts a restricted family-list string. Existing `theme="light"` and `theme="dark"` calls remain supported.

## Examples

- `python examples/landing.py` — responsive page layout and custom theme.
- `python examples/dashboard.py` — sidebar-style layout, cards, grid, and scrolling.
- `python examples/form_validation.py` — input callback validation.
- `python examples/login.py` — controlled login fields.
- `python -m examples.phase11_studio.app` — predefined component playground.
- `python -m examples.phase11_admin.app` — routed administration dashboard.
- `python -m examples.phase11_pyoffice.app` — desktop plain-text notes prototype (desktop extra required).

Icons, dividers, badges, tooltips, checkbox/radio/select/textarea controls, toast notifications, and machine-readable component metadata remain planned.
