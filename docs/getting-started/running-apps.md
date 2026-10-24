# Running applications

## Browser

Run an entry point directly with `python app.py`, or use the installed CLI:

```bash
novaui run app.py --mode web --host 127.0.0.1 --port 0 --open-browser
```

The CLI defaults to `app.py`, loopback host, and no automatic browser opening.
Port `0` asks the OS to select an available port. It rejects non-loopback hosts.
See the [CLI reference](../reference/cli.md).

## Desktop

Install the optional dependency and use `ui.desktop(...)`, or use CLI mode for
an entry point that calls `ui.app(...)`:

```bash
python -m pip install -e '.[desktop]'
python app.py --desktop
novaui run app.py --mode desktop
```

`pywebview` embeds the same frontend in a platform webview; this is not native
widget rendering. Native dialogs, menus, and clipboard support depend on
platform libraries. See [desktop runtime](../desktop/runtime.md).
