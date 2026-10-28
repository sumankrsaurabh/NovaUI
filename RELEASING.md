# Release checklist

Do not publish artifacts or external releases without explicit authorization. Run this checklist from a clean checkout and record the Python version and OS.

1. Update `novaui/__init__.py` (the authoritative version source) and `CHANGELOG.md`. Hatchling reads the project version from this attribute.
2. Create a clean environment and install `.[dev]`; separately verify the optional desktop extra on a supported OS.
3. Run `ruff`, the full test suite, frontend syntax check, and `novaui check`.
4. Run `pip-audit` against the release environment and review every finding.
5. Build source and wheel distributions with `python -m build --sdist --wheel`; validate with `python -m twine check dist/*`.
6. Inspect the wheel and source archive for `novaui/frontend/index.html`, `app.js`, `styles.css`, metadata, and the project license.
7. Install the wheel into a fresh environment without the source checkout on `sys.path`; verify import, version, frontend resources, and the `novaui` entry point.
8. Run representative web examples from the installed package. Manually test desktop mode and native APIs on each OS being claimed.
9. Do not describe a platform or package as tested unless the corresponding command actually ran there.
10. Review `SECURITY.md`, known limitations, wheel contents, and generated artifacts before any release.

Version 0.1.0 is published on PyPI. The 0.1.1 release still requires its own CI, advisory, clean-environment, browser, desktop, and platform validation; passing local checks does not establish that the GitHub publishing workflow or every claimed platform works.

## Local install and build commands

From a source checkout:

```bash
python -m pip install .
python -m pip install -e '.[dev]'
python -m pip install -e '.[desktop]'
python -m build --sdist --wheel
python -m twine check dist/*
```

`desktop-qt` is an additional optional extra. The base runtime has no third-party dependencies. The Python distribution is `novaui`, imported with `import novaui`.

## GitHub and PyPI release setup

The public source repository is `https://github.com/sumankrsaurabh/NovaUI`. Package metadata and direct-from-GitHub installation instructions use this location.

The PyPI project `novaui` has a 0.1.0 release. The existing MIT license and its `NovaUI Contributors` copyright line are retained; no individual author identity is declared in package metadata.

The release workflow is `.github/workflows/release.yml`. Before it can publish:

1. Protect the repository's default branch and `v*` release tags; enable private vulnerability reporting.
2. Create a PyPI account. Then create a PyPI project (or pending publisher) for `novaui` and configure Trusted Publishing with owner `sumankrsaurabh`, repository `NovaUI`, workflow `release.yml`, and GitHub environment `pypi`.
3. Create a protected GitHub environment named `pypi`; require maintainer approval if desired.
4. Ensure the changelog and authoritative version are updated, then create a matching tag such as `v0.1.1` only after review.
5. The tag workflow runs tests/build/metadata validation first, publishes with GitHub OIDC, then creates a GitHub release containing the wheel and sdist. It does not run for ordinary branches or pull requests.

PyPI documents the required `id-token: write` permission and environment-based publisher setup in its [Trusted Publishing guide](https://docs.pypi.org/trusted-publishers/using-a-publisher/) and [publisher configuration guide](https://docs.pypi.org/trusted-publishers/adding-a-publisher/). The workflow uses Trusted Publishing; confirm the PyPI publisher and GitHub environment settings are active before relying on a tag to publish.

The separate `.github/workflows/testpypi.yml` is manually dispatched, requires typing `UPLOAD`, and requires dispatch from a tag matching the package version. Configure a separate TestPyPI Trusted Publisher for workflow `testpypi.yml` and environment `testpypi`. The workflow publishes once for that version and then installs the uploaded package to verify import, CLI, and packaged frontend resources. Do not reuse production settings or tokens. PyPA supports TestPyPI through the separate `repository-url` input; see the [PyPA publishing action documentation](https://github.com/pypa/gh-action-pypi-publish).
