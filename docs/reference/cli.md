# CLI reference

Install NovaUI to use `novaui`; `python -m novaui` is equivalent.

- `novaui --help`, `novaui --version`
- `novaui create NAME` — create a starter directory; refuses existing paths.
- `novaui run [ENTRY] [--mode web|desktop] [--host LOOPBACK] [--port PORT]`
  with optional `--open-browser`, `--no-browser`, and `--debug`.
- `novaui check` — syntax, import, metadata, and available pytest checks.
- `novaui build [--outdir PATH]` — create Python source and wheel distributions.

CLI options override `[tool.novaui]` configuration; defaults are `app.py`, web
mode, `127.0.0.1`, and port `0`. Only loopback host values are allowed. See the
[complete CLI guide](../../CLI.md) for exit codes and details.
