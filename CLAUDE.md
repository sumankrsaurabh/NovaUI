# Claude Code instructions

Read `AGENTS.md`, `README.md`, `ARCHITECTURE.md`, and `ROADMAP.md` first.

Work in small, tested increments. Do not attempt to implement the entire roadmap in one pass. Begin by running the existing tests and the counter example, then identify the highest-priority gap.

When making changes:
- Preserve the simple API: `ui.app(ui.Column(...))`.
- Keep Python and browser renderer responsibilities separate.
- Do not execute code received from the browser.
- Add tests for new behavior.
- Update docs and roadmap checkboxes.
- Run `pytest` and report the exact result.
- Ask before introducing a large dependency or making a breaking API change.
