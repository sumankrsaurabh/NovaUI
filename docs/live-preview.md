# Live preview

NovaUI provides a Python preview decorator and a local renderer runtime. It is
an early development feature: preview modules execute as trusted Python code in
the preview process and are **not sandboxed**.

## Declare previews

```python
import novaui as ui
from novaui import Button, Column, NovaPreview, Text

@NovaPreview
def CounterPreview():
    count = ui.state(0)
    Column(
        Text(lambda: f"Count: {count.value}"),
        Button("+", on_click=lambda: count.update(count.value + 1)),
        spacing=12,
        padding=24,
    )
```

Use `@NovaPreview(id="counter", name="Counter", theme="dark", width=800, height=600)` to set
metadata. The optional id is a stable identifier (defaults to the Python function
name); names remain unique display labels within the module. Theme accepts
`light` or `dark`; dimensions are integer CSS viewport dimensions from 100 through
4096 pixels. Decorated preview functions must be regular, synchronous,
zero-parameter functions. They may return a NovaUI `Component` or compose
components directly in the function body without `return`; multiple sibling
roots are grouped in a layout-neutral `Fragment`. Parameters, async functions,
and invalid results are rejected. Each call
creates a new component tree. Ordinary `ui.state()` values are recreated when
source is reloaded. To preserve a small piece of state across compatible source
edits, opt into `ui.preview_state("counter", 0)` inside the selected preview.
Keys must be stable, and values are retained only when their Python value type
still matches. The store is isolated by preview id; reset clears the selected
preview's values. State is in-memory only and is disposed when the runtime closes.
Preview functions should not perform durable side effects during construction.
Component disposal runs through the usual `App.dispose()` lifecycle.
Reusable parameterized component factories can be declared with
`from novaui import NovaComponent` and `@NovaComponent`, then called from a
preview. The preview function itself remains a zero-argument entry point
decorated with `@NovaPreview` (imported from `novaui`). The lowercase
`component` and `preview` decorator names remain available as aliases.

Several previews may be declared in one module; their display names must be
unique. Discovery imports the module (so module-level trusted Python executes)
but does not call the decorated functions. Only a selected preview is invoked.

## Start from a terminal

```bash
novaui preview path/to/your_preview.py
novaui preview path/to/your_preview.py --name Counter
novaui preview path/to/your_preview.py --theme dark --no-browser
```

Open [`examples/counter.py`](../examples/counter.py) and run the VS Code
command to try the preview workflow. It contains both a runnable browser app
and a top-level `@NovaPreview` declaration.

The process serves the same NovaUI HTML/CSS/JavaScript renderer on loopback,
selects a dynamic port by default, and watches the source plus imported local
Python modules. Polling uses the standard library; rapid editor saves are
debounced. A syntax or render error leaves the last successful component visible
and displays a separate error banner. Fixing the source triggers recovery.
Ctrl+C stops the watcher and server. `--no-watch` disables hot reload.

## VS Code

The source extension is in `editors/vscode`. Install NovaUI into the Python
interpreter you intend to use, open the project and a Python preview file, then
run **NovaUI: Open Live Preview**. The default interpreter is `python` on
Windows and `python3` on macOS/Linux. Set `novaui.pythonPath` to the interpreter
with NovaUI installed when the default is not the one used by your project. The
command lists previews without rendering them,
then prompts when multiple declarations exist. The panel is opened beside the
source editor. Saving the active file triggers a refresh; the runtime also
watches imported workspace modules. Its selector is refreshed from each runtime
discovery result, so added, renamed, and deleted previews appear without
restarting the extension. The toolbar provides refresh, selected-preview state
reset, light/dark theme, custom viewport dimensions, Mobile (390×844), Tablet
(768×1024), Desktop (1440×900), and Fit controls. Viewport dimensions describe
the iframe's CSS viewport, not a physical-device rendering profile.

For extension development, open `editors/vscode` in VS Code, press F5 to start
an Extension Development Host, and run `npm run check` for syntax validation.
The extension is not published to the Marketplace. It supports VS Code only;
PyCharm is not implemented. Run `npm --prefix editors/vscode run test:integration`
for the real Python child-process/renderer integration test and
`npm --prefix editors/vscode run test:vscode` for the installed VS Code Extension
Host smoke test (requires VS Code and a graphical session).

## Runtime API

`ui.discover_previews(path, workspace=...)` returns `PreviewDiscovery` with
`PreviewInfo` entries or a structured diagnostic. `ui.render_preview(path,
name, workspace=..., theme=...)` returns `PreviewResult`; use
`PreviewRuntime` when the caller needs reloads, event dispatch, server hosting,
watching, theme changes, and explicit cleanup. Errors expose type, concise
message, file, and line where available.

The renderer process accepts version 1 JSON control messages over its private
stdin pipe. The running HTTP renderer binds to `127.0.0.1`; a short-lived random
session token is required for component-tree and event requests. The browser
frontend obtains it from the URL fragment (not sent in the HTTP request URL).
The VS Code Webview uses a nonce Content Security Policy and forwards only
validated selection, theme, viewport, refresh, and shutdown controls. No code
typed or sent by the Webview is evaluated as Python. The workspace Python
process is trusted code and can access files and the network with the user's
permissions; do not preview untrusted repositories.

### Protocol v1 fields

Host-to-runtime JSON lines contain exactly these fields:

| Type | Fields |
| --- | --- |
| `refresh` | `version: 1`, `type` |
| `select` | `version: 1`, `type`, `name` |
| `theme` | `version: 1`, `type`, `theme: light|dark` |
| `viewport` | `version: 1`, `type`, integer `width`, integer `height` (100–4096) |
| `reset` | `version: 1`, `type` |
| `shutdown` | `version: 1`, `type` |

The runtime emits `ready` (URL, selected preview, theme, viewport, preview
metadata), `loading`, and `update` (selected preview, refreshed preview
metadata, and structured error, if any) as
`NOVAUI_PREVIEW {json}` stdout lines. Other Python stdout is ignored by the
VS Code extension. `novaui preview FILE --list` outputs a JSON discovery object
and exits without calling preview functions.

## Limitations and troubleshooting

- Only top-level decorated functions are registered. Decorators in imported
  modules are not enumerated as previews.
- Only `preview_state()` values with unchanged keys and exact value types survive
  source reloads. This is opt-in local in-memory state, not persistence.
- Watching uses periodic filesystem metadata checks, not OS-native notifications.
- In VS Code, viewport controls resize the iframe's CSS viewport; a narrow
panel may require horizontal scrolling. The Python
runtime watcher handles edits (including editor saves); the extension does not
issue a second save-triggered reload.
- Extension discovery and runtime each import the preview module in separate
  Python processes. Keep module-level code free of side effects; preview
  functions themselves run only when selected.
- Extension installation is a local source/development workflow; Marketplace
  packaging remains future work.
- If discovery reports no previews, save the file and verify `@NovaPreview` is
  imported from `novaui as ui` and placed directly on a module-level function.
- If Python cannot import NovaUI, select an interpreter with NovaUI installed
  in `novaui.pythonPath`.
