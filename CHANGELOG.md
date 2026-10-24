# Changelog

## Unreleased

- Made `novaui/__init__.py` the authoritative package version source, declared the existing MIT license for distribution, removed the unverified placeholder author from package metadata, and explicitly included frontend resources in wheels.
- Switched the HTTP server to `importlib.resources` for frontend asset access and added package-resource smoke tests.
- Added version-tagged PyPI Trusted Publishing and manually confirmed TestPyPI verification workflows, plus GitHub issue and pull-request templates.
- Configured package metadata, public GitHub project links, and PyPI Trusted Publishing workflows; PyPI publication remains pending.
- Added validated optional semantic theme colors for page backgrounds, surfaces, foreground and muted text, borders, and primary hover states; existing themes retain their defaults when these values are omitted.
- Reworked the README and added a navigable Markdown documentation set, runnable tutorial gallery, public API reference additions, and automatic documentation/example smoke checks.
- Documented pre-1.0 API stability and semantic versioning, and clarified private security reporting setup and maintainer response expectations.
- Added an explicit app-scoped extension configuration for compositional custom components, named themes, trusted plugins, and plugin-owned services. Plugins are never discovered or executed automatically.
- Hardened the loopback HTTP server with Host and same-origin checks for event requests, a bounded request-worker pool, socket timeouts, response security headers, and a project-asset size limit.
- Added security regression tests, CI checks, security policy, contribution guide, and release checklist.
- Recorded the current local DataTable Python serialization baseline and remaining MVP limitations.
