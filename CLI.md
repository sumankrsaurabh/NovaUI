# NovaUI CLI

Install NovaUI (editable from this source checkout with `python -m pip install -e '.[dev]'`) to register the `novaui` command. `python -m novaui` is equivalent.

## Commands

- `novaui --help`, `novaui --version` — show command help or installed package version.
- `novaui create my_app` — create a starter project. Names must start with a letter and contain letters, digits, `_`, or `-`. Existing paths are never overwritten.
- `novaui run` — run `app.py` in the current project, or use `[tool.novaui].entry` from `pyproject.toml`.
- `novaui run path/to/app.py --mode web|desktop` — select hosting explicitly. `web` is the default. Desktop requires `python -m pip install 'novaui[desktop]'` and a working platform webview.
- `novaui run --host 127.0.0.1 --port 8000 --open-browser` — choose a loopback address and port and open the browser. Port `0` asks the OS for an available port. `--no-browser` is the default.
- `novaui run --debug` or `novaui --debug run` — include detailed Python diagnostics. Without debug, ordinary configuration/runtime errors are concise.
- `novaui check` — compile Python files outside virtualenv/cache/build directories, import NovaUI, validate basic project name/version metadata when `pyproject.toml` exists, and run `pytest -q` in-process if a `tests/` directory exists. If pytest is missing, the test check is clearly marked skipped.
- `novaui build` — run `python -m build --sdist --wheel` into `dist/`. Install the optional build frontend first with `python -m pip install 'novaui[build]'` (or use the `dev` extra).

CLI values override `[tool.novaui]`, which overrides defaults:

```toml
[tool.novaui]
entry = "app.py"
mode = "web"
host = "127.0.0.1"
port = 8000
```

Only these four scalar keys are supported. The development CLI rejects non-loopback hosts. Use `novaui create` for a complete starter layout; install NovaUI into that project's environment before installing its `novaui` dependency when working from an unpublished source checkout.

## Assets

Put files under the project `assets/` directory. `ui.Image("assets/logo.png", alt="Logo")` renders through the local asset endpoint. The endpoint confines requests to that directory, including symlink resolution, and returns 404 for missing or escaping paths. Other files such as CSS, JavaScript, fonts, and icons can be loaded by the application using `/assets/<relative-path>` URLs. NovaUI does not bundle or transform assets. The CLI and direct script launches resolve the asset root from the entry point's directory; interactive launches use the current working directory.

## Exit status and limitations

Argument/configuration errors return `2`; application/runtime/check failures return a nonzero status; successful commands return `0`. `check` is a deterministic source syntax/import/test check, not a type checker or security audit. Hot reload is not implemented. `build` creates Python distributions; it does not create a desktop executable. For that, see the PyInstaller sample in `packaging/` and build on the target OS.
