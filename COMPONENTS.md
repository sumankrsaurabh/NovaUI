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

### Reusable function components

Import `NovaComponent` from NovaUI, then use the one-word `@NovaComponent`
decorator on a synchronous Python function to define a reusable component
factory. It may accept ordinary Python arguments. The function can either
return a component explicitly or call component constructors directly in its
body without `return`. NovaUI infers the constructed roots; multiple sibling
roots are grouped in a layout-neutral `Fragment`. Explicit `Fragment(...)` is
also available. The resulting tree uses the normal rendering and disposal
lifecycle. The decorator preserves the function name, docstring, and signature
for editor tools.

```python
from novaui import Card, Column, NovaComponent, Text

@NovaComponent
def InfoCard(title: str, description: str) -> None:
    Card(Text(title, bold=True), Text(description), padding=16)

Column(InfoCard("Reusable", "Build screens from small functions."))
```

Import `NovaPreview` and use the one-word `@NovaPreview` decorator separately on a
zero-argument function to register an IDE
preview entry point. A preview can call any reusable component factory; it is
not itself a different component type:

```python
from novaui import NovaPreview

@NovaPreview(name="Info card")
def InfoCardPreview():
    InfoCard("Reusable", "Previewed with NovaUI's regular renderer.")
```

See [live preview](docs/live-preview.md) for discovery and runtime behavior.

`Fragment(*children)` is a layout-neutral group for explicit sibling
composition. `@NovaComponent` and `@NovaPreview` use the same grouping when a
function body creates more than one top-level component and has no explicit
return value.

### `Text(text, size=None, bold=False, color=None)`

Renders text with `textContent` (never as HTML). `text` may be a string or zero-argument callable. Callables track reads from `State` instances and recalculate when those states change. `size` is a non-negative pixel integer; `bold` is a bool; `color` is a CSS color string.

### `Image(src, alt, width=None, height=None)`

Displays a local file from the app's `assets/` directory, for example `ui.Image("assets/logo.png", alt="NovaUI logo")`. `alt` is required. Absolute paths, parent-directory traversal, and paths outside `assets/` are rejected. The CLI resolves assets relative to the entry-point directory; direct Python launches use the working directory. Other static files can be requested at `/assets/<path>` without a bundler.

### `Button(label, on_click=None, disabled=False, variant="primary", icon=None)`

Renders a keyboard-operable button. `on_click` is registered with an opaque one-shot event ID. `variant` is `primary` or `secondary`. Optional `icon` places a built-in icon before the label.

### `Icon(name, size=18, label=None)`

Renders a dependency-free stroke icon using safe DOM SVG elements. Names are
`home`, `grid`, `search`, `settings`, `plus`, `minus`, `arrow_right`,
`chevron_right`, `chart`, `users`, `file`, `check`, `close`, `menu`, `sun`,
`moon`, `sparkles`, `download`, `folder`, `heart`, `clock`, and `cube`. `size` is 12–48
pixels. Without `label` the icon is hidden from assistive technology; provide a
label when it conveys information by itself.

### `IconButton(icon, label, on_click=None, disabled=False, variant="secondary", size="medium")`

Renders a compact icon-only action. `icon` accepts a built-in icon name or a short plain-text symbol, never HTML; `label` is required and supplies both the accessible name and hover title. `size` accepts `small`, `medium`, or `large`; `variant` follows `Button`. The click callback uses the same opaque event bridge as `Button`.

```python
ui.IconButton("+", "Add item", on_click=add_item, size="small")
```

### `Input(placeholder="", value="", password=False, label=None, on_change=None, disabled=False, read_only=False, input_type="text", ...)`

Renders a text or password field. `value` may be a string or `State[str]`. When bound or when `on_change` is supplied, the browser sends the changed string through the validated event bridge. `on_change(value)` may return an error string or `None`, synchronously or asynchronously; errors are rendered as text and associated with the field.

`input_type` supports `text`, `email`, `password`, `number`, and `date`; `password=True` remains a shorthand for password type. Optional `name`, `required`, `min_length`, `max_length`, `min_value`, and `max_value` set the corresponding field semantics and are validated in Python. See [Forms](FORMS.md) for Python-side `Field`/`Form` validation.

`input_type` also supports `search`; number fields accept `step` in addition to
the range attributes. `NumberField(value="", label=None, min_value=None,
max_value=None, step=1, **props)` is a convenience constructor for numeric
inputs. `SearchField(on_submit=..., value="", label="Search",
placeholder="Search", on_change=None, disabled=False)` provides clear and
submit actions; submitted callbacks receive the current string value.

### `TextArea(value="", label=..., placeholder="", rows=4, max_length=None, ...)`

Renders an accessible multiline field. Values may be a string or `State[str]`;
changes are sent as strings over the opaque event bridge. `rows` is 1–40 and
`max_length` is an optional non-negative integer. Disabled and read-only
controls do not register change handlers.

### `Checkbox(label, value=False, disabled=False, on_change=None)`

Renders a labeled boolean control. `value` may be a bool or `State[bool]`.
Events are validated as boolean strings before state changes.

### `Switch(label, value=False, disabled=False, on_change=None)`

Boolean switch appearance with a native keyboard-operable checkbox and
`role="switch"` semantics. It shares the state and callback contract of
`Checkbox`.

### `Slider(value=0, label=..., min_value=0, max_value=100, step=1, ...)`

An accessible numeric range control. Values must be finite and within bounds;
incoming values are checked against the configured step before updating state.

### `Select(options, label=..., value=None, disabled=False, on_change=None)`

Renders a labeled native single-choice select. `options` maps visible labels to
unique string values. If `value` is omitted, the first declared option is
selected; submitted values must match a declared option.

### `DatePicker(value="", label=None, **props)`

Creates an `Input` with native date semantics. Values are ISO dates
(`YYYY-MM-DD`) and use the standard bound-state and change callback behavior.

### `Dropdown(label, child, open=False)`

Native disclosure with keyboard-operable summary and one component subtree.
User-expanded state is retained in the browser DOM while that component remains
mounted.

### `Tooltip(child, text)`

Associates non-interactive descriptive text with a child control. Focusable
children receive `aria-describedby`; non-focusable children are placed in a
keyboard-focusable wrapper. The tooltip appears on hover or focus.

### `ContextMenu(child, actions, label="Actions")`

Adds a custom right-click menu to a child, with keyboard invocation through the
Context Menu key or Shift+F10. Menu actions are ordinary trusted Python
callbacks registered as opaque event IDs. Arrow keys, Home/End, and Escape
operate the rendered menu.

### `RadioGroup(options, label, value="", on_change=None, disabled=False)`

Accessible single-choice options, passed as a mapping from display labels to stable string values. `value` may be a string or `State[str]`.

### `MultiSelect(options, label, value=None, on_change=None, disabled=False)`

Accessible checkbox group for selecting multiple values. Options are a mapping from labels to string values; `value` may be a list of strings or `State[list[str]]`. Browser selections are validated against the declared values before state is updated.

## Layouts

### `Animated(child, enter="fade", duration=240, easing="ease-out")`

Wraps one component and applies a CSS entrance animation the first time that component node is mounted. Presets are `fade`, `fade_up`, `fade_down`, `slide_in`, `scale_in`, and `pop`; easing is one of `linear`, `ease`, `ease-in`, `ease-out`, or `ease-in-out`; duration is an integer from 0 to 2000 milliseconds. Nested child behavior and events use the normal component renderer. The wrapper remains mounted during state updates, so the entrance effect does not replay on each update. Exit animation is not supported because the current reconciliation lifecycle removes obsolete nodes immediately. The frontend honors `prefers-reduced-motion` for animations, transitions, and the spinner.

All layout constructors accept child components as positional arguments. Empty layouts render as empty elements.

### `Row(*children, spacing=8, padding=0, align="center", justify="start")`

Flexbox horizontal layout. `align` accepts `start`, `center`, `end`, `stretch`, or `baseline`; `justify` accepts `start`, `center`, `end`, `between`, `around`, or `evenly`. Rows wrap on narrow screens.

### `Column(*children, spacing=8, padding=0, align="stretch", justify="start")`

Flexbox vertical layout, with the same alignment options as `Row`.

### `Card(*children, padding=16, radius=None, variant="auto")`

Surface section with theme background, border, and shadow defaults. By default it follows the theme's `radius` token; an explicit `radius` is a non-negative pixel integer. `variant` accepts `auto`, `solid`, `glass`, or `glass-strong`; glass variants use translucent color mixing and backdrop blur where supported.

### `Center(child)`

Centers one child using Flexbox.

### `Container(*children, padding=0)`

Generic box for sizing and shared visual properties.

### `Grid(*children, columns=2, tablet_columns=None, mobile_columns=None, spacing=8, padding=0)`

CSS Grid layout. `columns` is an integer from 1 to 12 or a CSS grid-template string. Integer templates use equal-width columns. Use `tablet_columns` and `mobile_columns` to set explicit 641–1024px and up-to-640px column counts; custom CSS templates cannot be combined with these breakpoint properties.

### `SplitPane(first, second, orientation="horizontal", initial_percent=50, min_percent=15, max_percent=85)`

Two-pane layout with a pointer-resizable divider and keyboard arrow support. `orientation` is `horizontal` (left/right panels) or `vertical` (top/bottom panels). The divider is an accessible separator; its initial and permitted positions are percentages.

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

Renders a semantic table. On phones, `mobile_layout="cards"` (the default) presents rows as labeled cards; `"table"` keeps a horizontally scrollable table. `data` is a sequence of mappings or a `State` containing one. Header buttons sort ascending/descending; a global search box and per-column filter fields update server-owned filters. Pagination is one-based. Select-all applies to the visible page; `on_selection_change(rows)` receives all currently selected records. Use `row_key` for a unique stable field; without it, selection keys use the source row positions.

`on_row_click(row)` handles accessible mouse and Enter/Space activation of a row. `row_actions` accepts `RowAction(label, on_click)` items and calls each callback with the row. `loading=True` disables actions and shows a loading status. `empty_message` controls the empty-state copy.

Set `column_visibility=True` to display per-column visibility toggles; the last visible column cannot be hidden. Set `exportable=True` to download all currently filtered rows and visible columns as CSV. CSV cells are quoted by Python's CSV writer, and spreadsheet formula prefixes are neutralized. `bulk_actions` accepts `BulkAction(label, on_click)` items whose callback receives the selected row mappings.

```python
ui.DataTable(
    columns=[ui.ColumnDef("name", title="Employee"), ui.ColumnDef("salary")],
    data=[{"id": 1, "name": "Alice", "salary": 65000}],
    row_key="id",
    selectable=True,
    page_size=20,
)
```

### `DataGrid(columns, data, editable=True, editable_columns=None, on_change=None)`

Renders an editable semantic grid. Keyboard arrows move between cells, Enter or
F2 starts editing, and Enter/blur commits a cell. `editable_columns` limits
editing to the named column keys. `data` may be a list of row mappings or a
`State` containing them; `on_change(rows)` receives a copy after each edit.
Undo/redo controls and Ctrl/Cmd+Z, Ctrl/Cmd+Y shortcuts retain up to 100 edits.
Cells and callback values are text; other columns can be formatted with
`ColumnDef.formatter`. Copy copies a cell value and paste accepts a bounded
rectangular tab-separated range, validates it before applying, and records
each changed cell in undo history.

### `VirtualList(items, item_height=40, height=320, overscan=3, label="List")`

Renders a bounded text-only window from a sequence of strings; only visible
items plus the overscan buffer are serialized and placed in the DOM. Scroll
position changes are sent through a bounded event and windowed in Python.
`item_height` and `height` are positive pixel integers; `overscan` is 0–40.

### `CommandPalette(commands, placeholder="Search commands", empty_message=...)`

`Command` entries have a label, callback, optional search keywords, description,
and shortcut hint. The palette filters in the browser and dispatches callbacks
only through generated event IDs. Arrow Down and Enter operate on the first
match; Escape clears the query.

### `TreeView(nodes, label="Tree")`

`TreeNode(label, children=(), key=None, expanded=False, on_select=None)` defines
the tree. Keys are unique when supplied; otherwise path-derived keys are used.
Branches expand/collapse from the disclosure control or keyboard, and arrow
keys move through visible nodes. The selection callback receives the selected
`TreeNode`.

### `Toolbar(*children, label="Toolbar", orientation="horizontal")` and `StatusBar(*children, label="Status")`

Semantic `role="toolbar"` and `role="status"` wrappers for ordinary components.
Toolbar orientation is `horizontal` or `vertical`.

### `Toast(message, kind="info", duration=5000, on_dismiss=None)`, `ToastHost(*toasts)`, and `ToastQueue(max_toasts=5, label="Notifications")`

Accessible dismissible notifications. `kind` is `info`, `success`, `warning`,
or `error`; a duration of zero disables automatic dismissal. Place notifications
in a `ToastHost` to stack them in the notification region. Dismiss callbacks run
through the normal generated event bridge. `ToastQueue.push(message, kind=,
duration=)` adds notifications dynamically; when the queue is full, the oldest
item is evicted. `Dialog` remains the reusable declarative confirm/cancel flow.

### `FileUpload(on_upload, label="Choose a file", accept="", max_size=5000, disabled=False)`

Reads a selected or dropped file in the browser and passes `UploadedFile(name,
content_type, data)` to the Python callback. MIME types and extensions in
`accept` are checked again by Python; filenames are validated and file size is
limited to 6000 bytes (the current event bridge's bounded payload). The
accessible progress indicator reports local file reading; the transfer itself
is a single bounded event request. This is intended for small files, not bulk
uploads.

The table scans/sorts the in-memory dataset on each tree request but sends only the current page's formatted rows to the browser. It is intended for small and medium datasets; it has no virtualization. Search/filter callbacks update the table after the browser `change` event, and NovaUI currently returns the full application tree after each interaction.

Local baseline (Linux 7.0.0-31-generic x86_64, CPython 3.14.4; median across 7 runs, 10 serializations per run, 3 columns sorted descending, page size 20; one additional `tracemalloc` serialization): 100 rows — 0.195 ms / 16.5 KiB; 1,000 rows — 1.163 ms / 70.0 KiB; 5,000 rows — 6.557 ms / 884.5 KiB. Source data is allocated before tracing. Timing excludes browser rendering and HTTP dispatch; memory excludes source data. The reproducible Python-only baseline, including tree construction, state notification, event dispatch, and server socket bind/close, is `env PYTHONPATH=. .venv/bin/python benchmarks/runtime.py`. Figures are environment-specific, not a performance guarantee; full sorting/filtering scans all rows.

## Forms, navigation, and feedback

- `Field(value="", label=None, input_type="text", required=False, min_length=None, max_length=None, min_value=None, max_value=None, validator=None, disabled=False)` tracks a string value, dirty state, and validation result.
- `Form(fields=..., on_submit=..., submit_label="Submit", reset_label="Reset", disabled=False, loading=False)` validates submitted string values in Python. It exposes `values`, `errors`, `dirty_fields`, `revalidate()`, `reset()`, and `submit(values)`.
- `Router(routes=..., not_found=None)` maps paths to components or factories. Route factories accept `{parameter}` path values; `params`, `query_params`, and `current_path` describe the resolved URL. Call `ui.navigate(path)` from a component event callback.
- `AppShell`, `Header`, `Sidebar`, `MainContent`, `Footer`, `NavigationItem`, and `Breadcrumbs` compose the standard layout components. `Sidebar(collapsed=True)` selects a narrow width; it does not provide interactive collapse state.
- `Tabs({label: component}, selected=None)` serializes the selected panel and supports a `State[str]` selection.
- `Alert(message, kind="info")` accepts `info`, `success`, `warning`, or `error`; `Spinner(label="Loading")` displays a status indicator.
- `Badge(label, tone="neutral")` accepts `neutral`, `info`, `success`, `warning`, or `danger` and renders a compact status label.
- `ProgressBar(value, max_value=100, label="Progress", show_value=False)` validates a determinate range and exposes its value through native progress-bar ARIA attributes.
- `Skeleton(variant="text", width=None, height=None, lines=1)` reserves space during loading. `variant` is `text`, `rect`, or `circle`; text skeletons support 1–12 lines and are hidden from assistive technology.
- `Divider(orientation="horizontal")` renders a semantic separator; `orientation` may be `horizontal` or `vertical`.
- `Dialog(title, child, open=False, on_confirm=None, on_cancel=None, confirm_label="Confirm", cancel_label="Cancel")` provides separate confirm and cancel events. Pass `State[bool]` for controlled visibility.

See [Forms](FORMS.md) and [Routing](ROUTING.md) for runnable examples and
security limits. Form fields remain strings; standalone boolean, selection,
date, and numeric controls are available. Small-file upload is supported
through `FileUpload`; generic large-file transfer is intentionally not
supported by the bounded event bridge.

## Shell, theme, and application APIs

- `AppShell(*children, **shared_props)` composes its children in a full-bleed, viewport-height shell. At the application root, NovaUI removes the outer app padding; apply padding to `MainContent` or page content instead. `Header`, `MainContent`, and `Footer` are layout helpers with the same child-first convention.
- `Scaffold(body, destinations=..., top_bar=None, brand=None, floating_action=None, current_path=None, label="Primary navigation", sidebar_width=256, collapsible=True)` provides a full-screen responsive application shell. Destinations are `NavDestination(label, href, icon=None, badge=None)` values. With a root `Router`, the current route is highlighted and destination clicks navigate through NovaUI. Screens wider than 1024px use a labeled sidebar; 641–1024px use a compact icon rail; screens up to 640px use a fixed bottom bar with safe-area spacing. The desktop sidebar can be collapsed using its accessible toggle; set `collapsible=False` to hide it. It supports 1–8 local route destinations; place body padding inside the `body` component.
- `StickyHeader(*children, **props)` creates a sticky top header row.
- `Sidebar(*children, collapsed=False, **shared_props)` renders a sidebar; `collapsed` chooses a narrow width and is not an interactive toggle. `NavigationItem(label, href, active=False, icon=None)` renders an icon-first navigation button when a built-in icon name is supplied. `NavigationBar(*items, label="Primary navigation")` (also `Navbar`) and `SideNavigation(*items, label="Side navigation")` render semantic, accessible navigation landmarks; pass `NavigationItem` children for route changes. `Breadcrumbs(items)` accepts labels or `(label, href)` pairs.
- `Chart(labels, datasets, kind="line", title="", width=None, height=280)` draws responsive SVG line, bar, area, and doughnut charts with a legend and accessible name. `datasets` may be a mapping of series names to numeric values or a sequence of `ChartDataset(label, values, color=None)`. Every series must match the labels. Up to 500 labels and 8 series are accepted; doughnut values must be non-negative and use one series, with slice colors from NovaUI's palette. Other series colors, when supplied, must be six-digit hex values. No charting dependency is required.
- `Theme(mode="light", appearance="solid", persist=False, primary="#4f46e5", radius="22px", font_family="Inter, ui-sans-serif, system-ui, sans-serif", name=None, ...)` validates theme tokens. `mode` accepts `light`, `dark`, or `system`; system mode follows the browser OS color preference and updates when it changes. Set `persist=True` to keep browser-side theme choices made by `App.set_theme()` across reloads. Set `appearance="glass"` to apply translucent surfaces app-wide. Optional glass controls are `glass_blur` (0–64 pixels) and `glass_opacity` (0.35–0.95). Optional colors include `background`, `surface`, `surface_raised`, `foreground`, `muted`, `border`, `primary_hover`, `on_primary`, `primary_soft`, `success`, `warning`, `danger`, and `info`. `name` is used for explicit extension registration; it is omitted from renderer output. See the [design system guide](docs/design-system.md) and [extensions](EXTENSIONS.md).
- `App(..., stylesheets=())`, `ui.app(..., stylesheets=())`, and `ui.desktop(..., stylesheets=())` accept up to eight CSS paths relative to the project `assets/` directory, such as `stylesheets=("admin.css",)`. Paths must end in `.css` and cannot traverse outside `assets/`. These styles load after NovaUI's base stylesheet.
- `State(value)` and `ui.state(value)` provide mutable Python state. Read and assign `.value`, call `.update(value)`, subscribe with `.subscribe(callback)`, and release listeners with `.dispose()`. Use `ui.batch()` to defer notifications across several state updates; each changed state notifies once with its final value when the outer batch exits.
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
    primary="#4f46e5",
    radius="12px",
    font_family="Inter, ui-sans-serif, system-ui, sans-serif",
    background="#f5f6fa",
    surface="#ffffff",
    foreground="#171a2b",
    success="#16845b",
)
ui.app(ui.Text("Hello"), theme=theme)
```

`mode` is `light`, `dark`, or `system`; color fields must be CSS color names, hex, RGB, or HSL values; `radius` is a non-negative pixel integer or CSS length; and `font_family` accepts a restricted family-list string. Optional `surface_raised`, `primary_soft`, `on_primary`, `primary_hover`, `success`, `warning`, `danger`, and `info` colors customize their matching CSS tokens. Existing `theme="light"` and `theme="dark"` calls remain supported. See the [design system guide](docs/design-system.md) for the complete built-in palette and token scales.

## Examples

Runnable applications are in [`examples/`](examples/README.md): a reactive
counter, registration form, routed dashboard with a data table, theme switcher,
small component gallery, employee table, editable grid, small-file upload, and
optional desktop file-picker app. These examples use the current runtime.

Tooltip, checkbox/select/textarea controls, and machine-readable component
metadata remain planned. The built-in stroke icon set is limited to the names
listed under `Icon`; it is not a general-purpose icon pack.

<!-- BEGIN GENERATED COMPONENT CONSTRUCTORS -->
## Constructor signatures

Generated from the exported component constructors. Refresh with `python scripts/generate_component_reference.py`.

- `Alert(message: 'str', kind: 'str' = 'info', *, margin: 'int | str | None' = None, min_width: 'int | str | None' = None, max_width: 'int | str | None' = None, min_height: 'int | str | None' = None, max_height: 'int | str | None' = None, background: 'str | None' = None, border: 'str | None' = None, shadow: 'str | None' = None, visible: 'bool' = True, class_name: 'str | None' = None, style: 'dict[str, str | int | float] | None' = None) -> None`
- `Animated(child: 'Component', *, enter: 'str' = 'fade', duration: 'int' = 240, easing: 'str' = 'ease-out', **props: 'Any')`
- `Badge(label: 'str', tone: 'str' = 'neutral', *, margin: 'int | str | None' = None, min_width: 'int | str | None' = None, max_width: 'int | str | None' = None, min_height: 'int | str | None' = None, max_height: 'int | str | None' = None, background: 'str | None' = None, border: 'str | None' = None, shadow: 'str | None' = None, visible: 'bool' = True, class_name: 'str | None' = None, style: 'dict[str, str | int | float] | None' = None) -> None`
- `Button(label: 'str', on_click: 'Callable[..., Any] | None' = None, disabled: 'bool' = False, variant: 'str' = 'primary', width: 'int | None' = None, height: 'int | None' = None, icon: 'str | None' = None, *, margin: 'int | str | None' = None, min_width: 'int | str | None' = None, max_width: 'int | str | None' = None, min_height: 'int | str | None' = None, max_height: 'int | str | None' = None, background: 'str | None' = None, border: 'str | None' = None, shadow: 'str | None' = None, visible: 'bool' = True, class_name: 'str | None' = None, style: 'dict[str, str | int | float] | None' = None) -> None`
- `Card(*children: 'Component', padding: 'int' = 16, radius: 'int | None' = None, variant: 'str' = 'auto', width: 'int | None' = None, height: 'int | None' = None, **props: 'Any')`
- `Center(child: 'Component', *, width: 'int | None' = None, height: 'int | None' = None, **props: 'Any')`
- `Chart(labels: 'Sequence[str]', datasets: 'Sequence[ChartDataset] | Mapping[str, Sequence[int | float]]', *, kind: 'str' = 'line', title: 'str' = '', width: 'int | None' = None, height: 'int' = 280, **props: 'Any') -> 'None'`
- `Checkbox(label: 'str', value: 'bool | State[bool]' = False, *, disabled: 'bool' = False, on_change: 'Callable[[bool], Any] | None' = None, **props: 'Any')`
- `Column(*children: 'Component', spacing: 'int' = 8, padding: 'int' = 0, align: 'str' = 'stretch', justify: 'str' = 'start', width: 'int | None' = None, height: 'int | None' = None, **props: 'Any')`
- `CommandPalette(commands: 'Sequence[Command]', *, placeholder: 'str' = 'Search commands', empty_message: 'str' = 'No matching commands.', **props: 'Any')`
- `Container(*children: 'Component', padding: 'int' = 0, width: 'int | None' = None, height: 'int | None' = None, **props: 'Any')`
- `ContextMenu(child: 'Component', actions: 'Mapping[str, Callable[[], Any]]', *, label: 'str' = 'Actions', **props: 'Any')`
- `CustomComponent(**props: 'Any') -> 'None'`
- `DataGrid(columns: 'Sequence[ColumnDef]', data: 'Sequence[Mapping[str, Any]] | State[list[Mapping[str, Any]]]', *, editable: 'bool' = True, editable_columns: 'Sequence[str] | None' = None, on_change: 'Callable[[list[dict[str, Any]]], Any] | None' = None, **props: 'Any')`
- `DataTable(columns: 'Sequence[ColumnDef]', data: 'Sequence[Mapping[str, Any]] | State[list[Mapping[str, Any]]]', *, selectable: 'bool' = False, sortable: 'bool' = True, searchable: 'bool' = True, filterable: 'bool' = True, page_size: 'int' = 20, row_key: 'str | None' = None, loading: 'bool' = False, empty_message: 'str' = 'No data available.', on_row_click: 'Callable[[Mapping[str, Any]], Any] | None' = None, on_selection_change: 'Callable[[list[Mapping[str, Any]]], Any] | None' = None, row_actions: 'Sequence[RowAction]' = (), bulk_actions: 'Sequence[BulkAction]' = (), column_visibility: 'bool' = False, exportable: 'bool' = False, mobile_layout: 'str' = 'cards', **props: 'Any')`
- `Dialog(title: 'str', child: 'Component', *, open: 'bool | State[bool]' = False, on_confirm: 'Callable[[], Any] | None' = None, on_cancel: 'Callable[[], Any] | None' = None, confirm_label: 'str' = 'Confirm', cancel_label: 'str' = 'Cancel', **props: 'Any')`
- `Divider(orientation: 'str' = 'horizontal', *, margin: 'int | str | None' = None, min_width: 'int | str | None' = None, max_width: 'int | str | None' = None, min_height: 'int | str | None' = None, max_height: 'int | str | None' = None, background: 'str | None' = None, border: 'str | None' = None, shadow: 'str | None' = None, visible: 'bool' = True, class_name: 'str | None' = None, style: 'dict[str, str | int | float] | None' = None) -> None`
- `Dropdown(label: 'str', child: 'Component', *, open: 'bool' = False, **props: 'Any')`
- `FileUpload(on_upload: 'Callable[[UploadedFile], Any]', *, label: 'str' = 'Choose a file', accept: 'str' = '', max_size: 'int' = 5000, disabled: 'bool' = False, **props: 'Any')`
- `Form(*, fields: 'Mapping[str, Field]', on_submit: 'Callable[[dict[str, str]], Any]', submit_label: 'str' = 'Submit', reset_label: 'str | None' = 'Reset', disabled: 'bool' = False, loading: 'bool' = False, validators: 'Mapping[str, Callable[[Mapping[str, str]], str | None]] | None' = None, **props: 'Any')`
- `Fragment(*children: 'Component')`
- `Grid(*children: 'Component', columns: 'int | str' = 2, spacing: 'int' = 8, padding: 'int' = 0, width: 'int | None' = None, height: 'int | None' = None, tablet_columns: 'int | None' = None, mobile_columns: 'int | None' = None, **props: 'Any')`
- `Icon(name: 'str', size: 'int' = 18, label: 'str | None' = None, *, margin: 'int | str | None' = None, min_width: 'int | str | None' = None, max_width: 'int | str | None' = None, min_height: 'int | str | None' = None, max_height: 'int | str | None' = None, background: 'str | None' = None, border: 'str | None' = None, shadow: 'str | None' = None, visible: 'bool' = True, class_name: 'str | None' = None, style: 'dict[str, str | int | float] | None' = None) -> None`
- `IconButton(icon: 'str', label: 'str', on_click: 'Callable[..., Any] | None' = None, disabled: 'bool' = False, variant: 'str' = 'secondary', size: 'str' = 'medium', width: 'int | None' = None, height: 'int | None' = None, *, margin: 'int | str | None' = None, min_width: 'int | str | None' = None, max_width: 'int | str | None' = None, min_height: 'int | str | None' = None, max_height: 'int | str | None' = None, background: 'str | None' = None, border: 'str | None' = None, shadow: 'str | None' = None, visible: 'bool' = True, class_name: 'str | None' = None, style: 'dict[str, str | int | float] | None' = None) -> None`
- `Image(src: 'str', alt: 'str', *, width: 'int | None' = None, height: 'int | None' = None, **props: 'Any')`
- `Input(placeholder: 'str' = '', value: 'str | State[str]' = '', password: 'bool' = False, label: 'str | None' = None, on_change: 'Callable[[str], str | None | Awaitable[str | None]] | None' = None, disabled: 'bool' = False, read_only: 'bool' = False, error: 'str | None' = None, width: 'int | None' = None, height: 'int | None' = None, input_type: 'str | None' = None, name: 'str | None' = None, required: 'bool' = False, min_length: 'int | None' = None, max_length: 'int | None' = None, min_value: 'str | int | float | None' = None, max_value: 'str | int | float | None' = None, step: 'int | float | str | None' = None, *, margin: 'int | str | None' = None, min_width: 'int | str | None' = None, max_width: 'int | str | None' = None, min_height: 'int | str | None' = None, max_height: 'int | str | None' = None, background: 'str | None' = None, border: 'str | None' = None, shadow: 'str | None' = None, visible: 'bool' = True, class_name: 'str | None' = None, style: 'dict[str, str | int | float] | None' = None) -> None`
- `MultiSelect(options: 'Mapping[str, str]', *, value: 'list[str] | State[list[str]] | None' = None, label: 'str', on_change: 'Callable[[list[str]], Any] | None' = None, disabled: 'bool' = False, **props: 'Any')`
- `Navbar(*items: 'Component', label: 'str' = 'Primary navigation', **props: 'Any')`
- `NavigationBar(*items: 'Component', label: 'str' = 'Primary navigation', **props: 'Any')`
- `ProgressBar(value: 'int | float', max_value: 'int | float' = 100, label: 'str' = 'Progress', show_value: 'bool' = False, *, margin: 'int | str | None' = None, min_width: 'int | str | None' = None, max_width: 'int | str | None' = None, min_height: 'int | str | None' = None, max_height: 'int | str | None' = None, background: 'str | None' = None, border: 'str | None' = None, shadow: 'str | None' = None, visible: 'bool' = True, class_name: 'str | None' = None, style: 'dict[str, str | int | float] | None' = None) -> None`
- `RadioGroup(options: 'Mapping[str, str]', *, value: 'str | State[str]' = '', label: 'str', on_change: 'Callable[[str], Any] | None' = None, disabled: 'bool' = False, **props: 'Any')`
- `Router(*, routes: 'Mapping[str, Component | Callable[..., Component]]', not_found: 'Component | Callable[[], Component] | None' = None, **props: 'Any')`
- `Row(*children: 'Component', spacing: 'int' = 8, padding: 'int' = 0, align: 'str' = 'center', justify: 'str' = 'start', width: 'int | None' = None, height: 'int | None' = None, **props: 'Any')`
- `Scaffold(body: 'Component', *, destinations: 'Sequence[NavDestination]', top_bar: 'Component | None' = None, brand: 'Component | None' = None, floating_action: 'Component | None' = None, current_path: 'str | None' = None, label: 'str' = 'Primary navigation', sidebar_width: 'int' = 256, collapsible: 'bool' = True, **props: 'Any') -> 'None'`
- `ScrollView(*children: 'Component', direction: 'str' = 'vertical', padding: 'int' = 0, width: 'int | None' = None, height: 'int | None' = None, **props: 'Any')`
- `SearchField(*, on_submit: 'Callable[[str], Any]', value: 'str | State[str]' = '', label: 'str' = 'Search', placeholder: 'str' = 'Search', on_change: 'Callable[[str], str | None | Awaitable[str | None]] | None' = None, disabled: 'bool' = False, **props: 'Any')`
- `Select(options: 'Mapping[str, str]', *, label: 'str', value: 'str | State[str] | None' = None, disabled: 'bool' = False, on_change: 'Callable[[str], Any] | None' = None, **props: 'Any')`
- `SideNavigation(*items: 'Component', label: 'str' = 'Side navigation', **props: 'Any')`
- `Skeleton(variant: 'str' = 'text', width: 'int | None' = None, height: 'int | None' = None, lines: 'int' = 1, *, margin: 'int | str | None' = None, min_width: 'int | str | None' = None, max_width: 'int | str | None' = None, min_height: 'int | str | None' = None, max_height: 'int | str | None' = None, background: 'str | None' = None, border: 'str | None' = None, shadow: 'str | None' = None, visible: 'bool' = True, class_name: 'str | None' = None, style: 'dict[str, str | int | float] | None' = None) -> None`
- `Slider(value: 'float | State[int | float]' = 0, *, label: 'str', min_value: 'float' = 0, max_value: 'float' = 100, step: 'float | str' = 1, disabled: 'bool' = False, on_change: 'Callable[[float], Any] | None' = None, **props: 'Any')`
- `Spacer(size: 'int' = 8, width: 'int | None' = None, height: 'int | None' = None, *, margin: 'int | str | None' = None, min_width: 'int | str | None' = None, max_width: 'int | str | None' = None, min_height: 'int | str | None' = None, max_height: 'int | str | None' = None, background: 'str | None' = None, border: 'str | None' = None, shadow: 'str | None' = None, visible: 'bool' = True, class_name: 'str | None' = None, style: 'dict[str, str | int | float] | None' = None) -> None`
- `Spinner(label: 'str' = 'Loading', *, margin: 'int | str | None' = None, min_width: 'int | str | None' = None, max_width: 'int | str | None' = None, min_height: 'int | str | None' = None, max_height: 'int | str | None' = None, background: 'str | None' = None, border: 'str | None' = None, shadow: 'str | None' = None, visible: 'bool' = True, class_name: 'str | None' = None, style: 'dict[str, str | int | float] | None' = None) -> None`
- `SplitPane(first: 'Component', second: 'Component', *, orientation: 'str' = 'horizontal', initial_percent: 'int' = 50, min_percent: 'int' = 15, max_percent: 'int' = 85, **props: 'Any')`
- `Stack(*children: 'Component', width: 'int | None' = None, height: 'int | None' = None, **props: 'Any')`
- `StatusBar(*children: 'Component', label: 'str' = 'Status', **props: 'Any')`
- `Switch(label: 'str', value: 'bool | State[bool]' = False, *, disabled: 'bool' = False, on_change: 'Callable[[bool], Any] | None' = None, **props: 'Any')`
- `Tabs(tabs: 'Mapping[str, Component]', *, selected: 'str | State[str] | None' = None, **props: 'Any')`
- `Text(text: 'str | Callable[[], Any]', size: 'int | None' = None, bold: 'bool' = False, color: 'str | None' = None, width: 'int | None' = None, height: 'int | None' = None, *, margin: 'int | str | None' = None, min_width: 'int | str | None' = None, max_width: 'int | str | None' = None, min_height: 'int | str | None' = None, max_height: 'int | str | None' = None, background: 'str | None' = None, border: 'str | None' = None, shadow: 'str | None' = None, visible: 'bool' = True, class_name: 'str | None' = None, style: 'dict[str, str | int | float] | None' = None) -> None`
- `TextArea(value: 'str | State[str]' = '', *, label: 'str', placeholder: 'str' = '', rows: 'int' = 4, max_length: 'int | None' = None, required: 'bool' = False, disabled: 'bool' = False, read_only: 'bool' = False, on_change: 'Callable[[str], Any] | None' = None, **props: 'Any')`
- `Toast(message: 'str', *, kind: 'str' = 'info', duration: 'int' = 5000, on_dismiss: 'Callable[[], Any] | None' = None, **props: 'Any')`
- `ToastHost(*toasts: 'Toast', label: 'str' = 'Notifications', **props: 'Any')`
- `ToastQueue(*, max_toasts: 'int' = 5, label: 'str' = 'Notifications', **props: 'Any')`
- `Toolbar(*children: 'Component', label: 'str' = 'Toolbar', orientation: 'str' = 'horizontal', **props: 'Any')`
- `Tooltip(child: 'Component', text: 'str', **props: 'Any')`
- `TreeView(nodes: 'Sequence[TreeNode]', *, label: 'str' = 'Tree', **props: 'Any')`
- `VirtualList(items: 'Sequence[str]', *, item_height: 'int' = 40, height: 'int' = 320, overscan: 'int' = 3, label: 'str' = 'List', **props: 'Any')`
- `Wrap(*children: 'Component', spacing: 'int' = 8, run_spacing: 'int' = 8, align: 'str' = 'start', width: 'int | None' = None, height: 'int | None' = None, **props: 'Any')`

<!-- END GENERATED COMPONENT CONSTRUCTORS -->
