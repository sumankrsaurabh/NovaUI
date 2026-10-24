# Troubleshooting

- **`novaui: command not found`:** activate the virtual environment and install
  NovaUI with `python -m pip install -e .`.
- **Desktop dependency missing:** install `python -m pip install -e '.[desktop]'`
  and ensure a platform webview backend and GUI session are present.
- **Linux webview cannot start:** install GTK/WebKitGTK system packages, or use
  the Qt extra and set `PYWEBVIEW_GUI=qt`. These backends have OS-level
  dependencies.
- **Port in use:** use `--port 0` to let the OS choose a free port.
- **Browser not opened by CLI:** supply `--open-browser`; direct `ui.app()` opens
  a browser by default.
- **Assets return 404:** place files under `assets/`; CLI asset paths resolve
  relative to the entry script.
- **Server tests fail with `PermissionError`:** integration tests bind loopback;
  run them in an environment that permits local sockets.

For a failing callback, use `--debug` with the CLI or `debug=True` during local
development. Do not include secrets or user-submitted passwords in diagnostic
reports. See [security guidance](../../SECURITY.md).
