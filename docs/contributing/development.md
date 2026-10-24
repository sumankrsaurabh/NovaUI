# Development

From the repository root:

```bash
python -m pip install -e '.[dev]'
PYTHONPATH=. python -m pytest -q
python -m ruff check novaui tests examples packaging
node --check novaui/frontend/app.js
```

HTTP integration tests need permission to bind loopback sockets. A new feature
should include tests, accurate docs, and a runnable example when practical.
Preserve documented APIs or include a migration path for an intentional
breaking change. See [CONTRIBUTING.md](../../CONTRIBUTING.md).
