# Project structure

`novaui create hello_app` creates this small starter:

```text
hello_app/
├── app.py
├── assets/.gitkeep
├── hello_app/__init__.py
├── pyproject.toml
├── README.md
└── tests/test_app.py
```

`app.py` is the entry point. Place local images, CSS, JavaScript, fonts, or
other static files under `assets/`; NovaUI serves files from that directory
only. The `hello_app/` Python package is a place for reusable app modules.
`tests/test_app.py` shows a basic serialization test.

The generated project declares NovaUI as a package dependency. While NovaUI is
being developed from this repository, install the framework editable in the
environment used to run the project, then install the generated app:

```bash
python -m pip install -e /path/to/NovaUI-Starter
cd hello_app
python -m pip install -e '.[dev]'
novaui run --open-browser
```

See the [CLI reference](../reference/cli.md) for configuration and exit codes.
