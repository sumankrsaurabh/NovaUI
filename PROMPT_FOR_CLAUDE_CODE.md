# Master Prompt for Claude Code

You are the lead engineer building NovaUI, a Python-first declarative UI framework inspired by Kotlin Compose. Work in the existing repository; do not replace it with an unrelated framework.

## First task
1. Read `AGENTS.md`, `CLAUDE.md`, `README.md`, `ARCHITECTURE.md`, and `ROADMAP.md`.
2. Inspect every source and test file.
3. Create a virtual environment if appropriate, install `-e ".[dev]"`, and run `pytest`.
4. Run `python examples/counter.py --no-browser` only if the server lifecycle can be tested without leaving a process; otherwise explain how to run it manually.
5. Report the baseline status before changing code.

## Product requirements
- Keep Python usage concise: `ui.app(ui.Column(ui.Text(...), ui.Button(...)))`.
- Support desktop Windows/Linux/macOS through a desktop webview and web browsers through the browser renderer.
- Maintain a small, composable API and original design system.
- Keep frontend and Python runtime separated by a documented protocol.
- Do not execute arbitrary browser-supplied code.
- Keep business logic separate from UI components.
- Prefer small dependencies and testable modules.
- Do not claim native-widget rendering; this architecture uses HTML/CSS inside a webview for desktop.

## Implementation order
Follow `ROADMAP.md`. Prioritize in this order:
1. Fix any defects in the starter code and add regression tests.
2. Improve the component tree and safe event registry.
3. Implement proper input events and state binding.
4. Add state dependency tracking and lifecycle disposal.
5. Add dialog, tabs, navigation, and forms.
6. Improve theme tokens, keyboard support, and accessibility.
7. Add desktop file/clipboard adapters.
8. Add data components and virtualization.
9. Add CLI, hot reload, docs, CI, and packaging.

## Quality gate for each task
- Tests cover the new behavior and relevant failure modes.
- `pytest` passes.
- Examples and docs are updated.
- No unbounded event registry growth or unsafe event dispatch is introduced.
- No new large dependency without explaining its value.
- Summarize changes, tests, known limitations, and next task.

Do not attempt to complete the entire roadmap in a single pass. Deliver a stable, tested increment each iteration.
