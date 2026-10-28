# Changelog

## 0.1.1 - 2026-10-29

- Added standalone text area, checkbox, switch, select, slider, date picker, radio group, and multi-select controls, plus dropdown, tooltip, and context-menu components.
- Added cancellable asynchronous form-field validation, bounded toast queues, a windowed text-only `VirtualList`, and bounded file-upload drag-and-drop.
- Added DataGrid clipboard copy/paste with validation and undo history, a native folder-picker adapter, and large-tree serialization benchmarks.
- Expanded runnable examples, component documentation, regression coverage, and browser validation for virtual scrolling and file uploads.
- Fixed `novaui check` to accept valid PEP 621 dynamic package versions and reject conflicting static/dynamic declarations.
- Clarified current release limitations and pinned the PyPI publishing action to its verified immutable commit.

## 0.1.0 - 2026-10-24

- Made `novaui/__init__.py` the authoritative package version source, declared the existing MIT license for distribution, removed the unverified placeholder author from package metadata, and explicitly included frontend resources in wheels.
- Switched the HTTP server to `importlib.resources` for frontend asset access and added package-resource smoke tests.
- Added version-tagged PyPI Trusted Publishing and manually confirmed TestPyPI verification workflows, plus GitHub issue and pull-request templates.
- Configured package metadata, public GitHub project links, and PyPI Trusted Publishing workflows; version 0.1.0 was published to PyPI.
- Added validated optional semantic theme colors for page backgrounds, surfaces, foreground and muted text, borders, and primary hover states; existing themes retain their defaults when these values are omitted.
- Reworked the README and added a navigable Markdown documentation set, runnable tutorial gallery, public API reference additions, and automatic documentation/example smoke checks.
- Documented pre-1.0 API stability and semantic versioning, and clarified private security reporting setup and maintainer response expectations.
- Added an explicit app-scoped extension configuration for compositional custom components, named themes, trusted plugins, and plugin-owned services. Plugins are never discovered or executed automatically.
- Hardened the loopback HTTP server with Host and same-origin checks for event requests, a bounded request-worker pool, socket timeouts, response security headers, and a project-asset size limit.
- Added security regression tests, CI checks, security policy, contribution guide, and release checklist.
- Recorded the current local DataTable Python serialization baseline and remaining MVP limitations.
