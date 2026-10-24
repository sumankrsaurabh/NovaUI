# Release workflow

NovaUI has not completed a public release validation. Do not upload packages
without explicit authorization.

Build local distributions with:

```bash
python -m pip install -e '.[build]'
python -m build --sdist --wheel
```

The CI build job installs the wheel into a clean target directory, checks its
frontend resource and CLI entry point, smoke-serializes a minimal app, then
stores the source and wheel distributions as a workflow artifact for 14 days.
This is an internal CI artifact, not a public release.

Then follow [RELEASING.md](../../RELEASING.md): verify version consistency,
run tests and lint, inspect the wheel and source archive, install the wheel in a
clean environment, test resources and CLI, review optional dependencies, and
record target-platform manual tests. CI has not yet been observed on the remote
service for every matrix entry. No publish job or registry credentials are
configured.
