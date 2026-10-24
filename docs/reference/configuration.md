# Project configuration

The optional `[tool.novaui]` section in `pyproject.toml` supports `entry`,
`mode`, `host`, and `port`:

```toml
[tool.novaui]
entry = "app.py"
mode = "web"
host = "127.0.0.1"
port = 8000
```

Command-line options take precedence, then this section, then defaults. Host
must be `127.0.0.1` or `localhost`; port is an integer from 0 to 65535. Assets
are served from the project `assets/` directory and cannot escape that root.
See the [CLI guide](../../CLI.md).
