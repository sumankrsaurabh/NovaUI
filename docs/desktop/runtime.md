# Desktop runtime

NovaUI desktop mode hosts the same HTML/CSS/JavaScript frontend in `pywebview`.
Install the optional extra:

```bash
python -m pip install -e '.[desktop]'
python examples/desktop_window.py
```

`ui.desktop(root, title=..., width=..., height=..., min_width=..., min_height=...,
resizable=..., fullscreen=..., frameless=..., background_color=..., debug=...)`
validates common window settings. `WindowOptions` has the same defaults. Backend
support varies; no native-widget rendering is provided.

On Linux, GTK requires system PyGObject and WebKitGTK packages. Alternatively,
install `python -m pip install -e '.[desktop-qt]'` and select Qt with
`PYWEBVIEW_GUI=qt`; Qt dependencies have separate license obligations. Windows
and macOS require their platform webview runtime. GUI tests are manual and
should be performed on each target OS before distribution.

The server binds loopback and uses an ephemeral port by default. The desktop
window does not expose unrestricted Python methods through a JavaScript bridge.
Loopback is not process isolation; see [SECURITY.md](../../SECURITY.md).
