# Desktop native APIs

Native APIs are explicit and only work inside a supported desktop runtime.

- `ui.window`: title, resize, minimize/maximize/restore, fullscreen, and close
  operations on the active desktop window.
- `ui.dialogs.open_file(...)` and `save_file(...)`: return a selected path or
  `None` on cancellation. NovaUI does not open or write the selected path.
- `ui.clipboard.read_text()` and `write_text(text)`: plain text only, through
  Tk where available.
- `App.shortcuts`: registers browser-rendered shortcuts using `Mod` for
  platform-aware Ctrl/Command mapping. Shortcuts avoid text inputs by default.
- `Menu`, `MenuItem`, and `MenuSeparator`: native menu definitions where the
  pywebview backend supports them. GTK does not support the native menu API.

Run `novaui run examples/desktop.py --mode desktop` to see a native open-file
dialog attached to an explicit button action. Use these APIs from an explicit
user action in your own app. Dialog titles are currently not forwarded by
the pywebview adapter. Clipboard availability depends on Tk and the desktop
session.
