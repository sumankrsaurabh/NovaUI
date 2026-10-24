# Agent Instructions for NovaUI

You are implementing NovaUI, an original Python-first declarative UI framework inspired by Compose-style APIs.

## Non-negotiable goals
- Keep the public API concise and Pythonic.
- Support a shared component model with browser rendering and optional desktop hosting.
- Prefer small, testable increments over large rewrites.
- Preserve backward compatibility for documented public APIs unless a deliberate versioned change is made.
- Do not claim features are implemented unless code and tests demonstrate them.
- Keep application business logic separate from UI framework internals.
- Never expose arbitrary Python evaluation or execution through the browser bridge.

## Workflow
1. Read `README.md`, `ARCHITECTURE.md`, `ROADMAP.md`, and relevant tests before editing.
2. Inspect the current implementation; do not assume TODOs are unimplemented.
3. Write or update tests before or alongside behavior changes.
4. Implement the smallest coherent change.
5. Run `pytest` and any frontend checks available.
6. Report changed files, commands run, results, known limitations, and next steps.
7. Do not silently delete files or change dependencies without a reason.

## Design rules
- Python source should be typed where it improves clarity.
- Use standard-library facilities when practical.
- Keep frontend dependencies minimal until a measured need appears.
- Components must validate inputs and serialize to JSON-safe values.
- Event handlers are registered by generated opaque IDs; the browser sends IDs, never Python code.
- State changes must be reflected when the component tree is requested again.
- Avoid blocking the UI thread for long-running work.
- Keep rendering backends behind a small interface.
- Use CSS variables for theme tokens.
- Support keyboard interaction and accessible labels as components mature.

## Acceptance checklist
- Tests pass.
- Examples run from the repository root.
- Errors are actionable.
- Documentation reflects actual behavior.
- Security-sensitive changes include explicit validation and tests.
