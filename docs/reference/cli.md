# CLI reference

Install NovaUI to use `novaui`; `python -m novaui` is equivalent.

- `novaui --help`, `novaui --version`
- `novaui create NAME` — create a starter directory; refuses existing paths.
- `novaui run [ENTRY] [--mode web|desktop] [--host LOOPBACK] [--port PORT]`
  with optional `--open-browser`, `--no-browser`, and `--debug`.
- `novaui check` — syntax, import, metadata, and available pytest checks.
- `novaui build [--outdir PATH]` — create Python source and wheel distributions.
- `novaui preview FILE [--name NAME] [--theme light|dark] [--port PORT] [--no-browser] [--no-watch]` — render a decorated component and watch local source changes. `novaui preview FILE --list` discovers names without invoking preview functions.

CLI options override `[tool.novaui]` configuration; defaults are `app.py`, web
mode, `127.0.0.1`, and port `0`. Only loopback host values are allowed. See the
[complete CLI guide](../../CLI.md) for exit codes and details.

See the [live-preview guide](../live-preview.md) for the Python API, VS Code
extension development, protocol, and security boundaries.
