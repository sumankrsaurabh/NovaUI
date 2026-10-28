# NovaUI Roadmap

## 0.1 — Working foundation
- [x] Python package skeleton
- [x] Component tree and JSON serialization
- [x] Text, Button, Input, Row, Column, Card, Spacer
- [x] Minimal browser renderer
- [x] Local HTTP runtime and event bridge
- [x] Optional pywebview host
- [x] Basic theme variables
- [x] Counter example and tests

## 0.2 — Core correctness
- [x] Stable component IDs and validated pixel dimensions
- [x] Formal component lifecycle and disposal for app-owned component resources
  - [x] Explicit `State.dispose()` releases subscriptions and rejects later updates/subscriptions
  - [x] `App.dispose()` releases component-owned subscriptions and invalidates the tree
- [x] Safe string input binding, request validation, and inline field errors
- [x] State subscriptions and dependency tracking for computed `Text`
- [x] Batched state notifications with nested `ui.batch()` scopes
- [x] Async event handlers awaited in bounded request workers
- [x] Observable async state with loading, success, error, and superseded-run cancellation
- [x] Browser diagnostics for failed event requests
- [ ] Better error pages and structured logging
- [x] Event registry cleanup, one-shot dispatch, and request size limits
- [ ] Accessibility review for every core control

## Phase 3 — Component system and layouts (in progress)
- [x] Shared validated visual properties: margins, min/max sizes, background, border, shadow, visibility, class names, and constrained styles
- [x] Configurable `Theme` tokens for mode, primary color, radius, and font family
- [x] Flexbox `Row`/`Column` alignment and justification
- [x] `Container`, responsive `Grid`, `ScrollView`, `Stack`, and `Wrap`
- [x] Component reference and layout examples
- [x] Additional visual components: `Icon`, `Divider`, `Badge`
- [x] Tooltip
- [x] `Image` component for confined project assets
- [x] Additional inputs: `TextArea`, `Checkbox`, `Select`
- [x] Additional inputs: `Switch`, `Slider`, `DatePicker`
- [x] Additional input controls: `Icon`, `ProgressBar`, `RadioGroup`
- [x] `NumberField`, `SearchField`, and accessible `RadioGroup`/`MultiSelect`
- [x] Size-limited small-file upload with validation and progress feedback
- [ ] Full keyboard and screen-reader accessibility review
- [x] Interactive theme updates through `App.set_theme()` and optional semantic color tokens

## 0.3 — Developer experience
- [x] `novaui create` starter project scaffolding
- [x] CLI web/desktop run with loopback host, port, and optional browser launch
- [x] Project `[tool.novaui]` entry/mode/host/port configuration
- [x] `novaui check` syntax/import/metadata/test checks and `novaui build` source/wheel command
- [x] Confined project asset endpoint and `Image` component
- [x] Hot reload for the VS Code live-preview extension
- [ ] Better browser exception overlays
- [x] Generated public constructor signatures in the component reference
- [ ] Component gallery
- [x] Ruff linting in CI
- [ ] Static type checking in CI

## 0.4 — Design system
- [x] Optional semantic color tokens for application background, surfaces, text, muted text, borders, and primary hover
- [x] Theme-level glass appearance and per-card solid/glass/glass-strong variants
- [x] Shared typography, spacing, radius, focus, shadow, and motion tokens
- [x] App-scoped stylesheets confined to project assets
- [x] System theme detection
- [x] Optional browser persistence for dynamic theme changes
- [x] Responsive grid breakpoint columns
- [x] Collapsible responsive Scaffold sidebar
- [x] Resizable split panels with accessible keyboard divider
- [x] Sticky headers
- [x] Reduced-motion support for framework animations, transitions, and spinner
- [x] Validated entrance animation wrapper (`Animated`); exit transitions remain planned
- [x] Optional high-contrast theme mode
- [ ] Full keyboard focus review

## Phase 4 — Application logic and navigation (in progress)
- [x] `Field` and `Form` with required, length, email/date/number range/custom validation
- [x] Form errors and accessible error summary, cross-field validation, dirty tracking, reset, synchronous/asynchronous submission, disabled/loading states
- [x] Router with static and parameter routes, query access, not-found pages, direct path loads, and browser history
- [x] App shell compositions, tabs, alerts, spinners, and separate dialog confirm/cancel events
- [x] Registration, routed dashboard, tabbed settings, and data-entry examples
- [x] Standalone checkbox, select, and textarea controls; `Form` fields remain string-valued
- [x] Async validation with cancellation
- [x] File upload validation with a bounded payload and progress feedback
- [x] Accessible toast notifications with auto-dismiss and a stacking host
- [x] Bounded ToastQueue state manager
- [ ] Imperative confirmation API
- [x] Collapsible responsive sidebar state
- [ ] Full keyboard/screen-reader review and production security review

## 0.5 — Navigation and overlays
- [x] Router and browser history (initial implementation)
- [x] Toast notification host
- [x] Dropdown, tooltip
- [x] Per-app keyboard shortcuts and searchable command palette
- [x] Form composition and validation (initial string-field implementation)

## Phase 5 — Desktop runtime and native integration (in progress)
- [x] Optional pywebview runtime with same frontend, loopback/ephemeral server, and cleanup
- [x] Validated desktop window options and title/resize/minimize/maximize/restore/fullscreen/close controls
- [x] Native open/save dialogs with cancellation and file filters
- [x] Explicit text clipboard API through Tkinter where available
- [x] Per-App keyboard shortcuts with Mod mapping, input focus protection, replacement, disabling, and unregister
- [x] Native menu definitions for pywebview backends that support menus
- [x] `novaui`/`python -m novaui` CLI and desktop/web mode
- [x] Desktop and shared-mode examples plus a PyInstaller sample configuration
- [x] Shared-renderer context menu component
- [ ] Native context menu, application icon, and notifications
- [ ] GUI manual testing across Windows, macOS, Linux GTK, and Linux Qt; frozen build verification

## 0.6 — Data UI
- [x] Sortable/filterable/searchable `DataTable` with paging and selection
- [x] `DataTable` column visibility, mobile row cards, safe CSV export, and bulk actions
- [x] Responsive SVG line, bar, area, and doughnut charts
- [x] Semantic horizontal and side navigation landmarks
- [x] Responsive `Scaffold` with route-aware sidebar, compact rail, and mobile bottom navigation
- [x] Editable data grid with keyboard navigation, cell editing, and undo/redo
- [x] Tree view with keyboard navigation
- [x] Virtualized text list with bounded visible-window serialization

## Phase 7 — Advanced components (in progress)
- [x] Semantic, searchable, sortable `DataTable` with per-column filtering, selection, pagination, formatters, and row callbacks
- [x] `DataTable` column visibility controls, configurable mobile cards, safe CSV export, and selected-row bulk actions
- [x] Dependency-free SVG `Chart` for line, bar, area, and doughnut datasets
- [x] `NavigationBar`/`Navbar` and `SideNavigation` semantic components
- [x] Route-aware `Scaffold` with responsive desktop, tablet, and mobile navigation
- [x] Editable `DataGrid` with keyboard navigation, cell editing, and undo/redo
- [x] DataGrid clipboard integration
- [x] Toolbar and status bar
- [x] Searchable command palette with registered commands
- [x] Context menu
- [ ] Rich-text editor integration after dependency/license/security review
- [x] Bounded upload with drag-and-drop support
- [ ] File explorer and download components
- [ ] Accessibility and performance review for advanced widgets

## 0.7 — Desktop integrations
- [x] Basic open/save file dialogs
- [x] Folder picker
- [x] Text clipboard adapter where Tk is available
- [ ] Print support investigation
- [ ] System tray investigation
- [x] Cross-platform CI matrix configured; completed platform runs remain pending

## 0.8 — Performance and stability
- [ ] Keyed incremental updates
  - [x] Stable component IDs and in-place DOM reuse; server still returns the full tree
- [x] Local benchmarks for construction, events, memory, and large trees
- [x] Loopback Host validation, same-origin JSON event checks, bounded request workers, socket timeouts, asset-size limits, and security response headers
- [ ] Packaging and signed-app documentation

## 1.0 — Stable API
- [x] Public API compatibility policy
- [x] Public docs, tutorials, and references for implemented APIs
- [ ] Windows/Linux/macOS test matrix
- [ ] Web deployment guide
- [ ] License and dependency review
- [x] Release checklist documented

## Phase 8 — Security and production readiness (in progress)
- [x] Audit HTTP event, route, host, and asset boundaries; add regression coverage
- [x] Reject cross-origin or origin-less browser event posts and untrusted Host headers
- [x] Replace sequential event IDs with cryptographically random one-shot IDs
- [x] Bound concurrent HTTP requests and slow socket reads; cap served project assets
- [x] Add basic response security headers and document the CSP's inline-style exception
- [x] Add security policy, contribution guide, changelog, and release checklist
- [x] Configure Linux CI for Python 3.10–3.14, lint, tests, frontend syntax, distribution build, and dependency audit
- [ ] Run CI on all configured Python versions and resolve any platform-specific failures
- [ ] Complete advisory scan and review dependency licenses for a release
- [ ] Broader security review, including browser testing, native desktop bridge audit, and local-process threat review
- [ ] Accessibility review and manual keyboard/screen-reader testing
- [x] Record a local Python DataTable serialization baseline; startup, state, and event microbenchmarks remain outstanding
- [ ] Verify clean wheel installation and web/desktop behavior on each claimed platform

## Phase 9 — Plugin architecture and extension ecosystem (initial API)
- [x] Explicit per-app `Extensions` configuration; no automatic plugin imports
- [x] Safe compositional custom components through the existing renderer
- [x] Validated named themes applied by the existing theme serializer
- [x] App-scoped services and deterministic setup/start/stop plugin lifecycle
- [x] Basic inclusive/exclusive NovaUI compatibility and optional module checks
- [x] Extension guide and runnable component, theme, and service examples
- [x] Public compatibility policy
- [ ] Expanded third-party extension integration tests
- [ ] Optional, explicit package entry-point listing/loading after metadata-only discovery design
- [ ] Extension lifecycle coverage for async services and desktop-specific capabilities

## Phase 10 — Documentation and controlled releases
- [x] Concise README with verified installation, web, and desktop commands
- [x] Navigable Markdown documentation index, getting-started guides, tutorials, and references
- [x] Component/runtime reference aligned with inspected public signatures
- [x] Contribution, security reporting, semantic versioning, and release-process guidance
- [x] Automated relative Markdown-link and example tree-serialization checks
- [x] Smoke-check all runnable example scripts without opening a browser or GUI
- [x] Build source/wheel artifacts; install the wheel in a clean environment and verify CLI, frontend resources, and app serialization
- [x] Retain CI build artifacts for 14 days and exclude agent-specific prompts from the source archive
- [ ] Observe configured CI jobs on every listed OS/Python target and complete manual desktop/accessibility checks
- [ ] Configure private vulnerability reporting before the first public release

## Phase 11 — Real-world application validation

The original larger validation applications and showcase were removed. A
curated set of small runnable examples is now maintained under `examples/`;
the Admin and PyOffice prototypes remain out of the shipped source tree.

- [x] NovaUI Studio component catalogue, selection, property notes, previews, and theme toggle
- [x] NovaUI Admin routes, form validation, table search/sort/filter/pagination, and confirmed deletion
- [x] PyOffice Notes prototype with explicit UTF-8 open/save and keyboard shortcuts
- [x] Add app workflows and local file persistence tests without requiring a GUI
- [x] Record framework gaps exposed by integration work
- [x] Restore focused examples for state, forms, routes/tables, themes, components, and desktop APIs
- [x] Add an accessible textarea before expanding document editing
- [x] Provide charts through the framework's dependency-free SVG renderer; no external chart adapter is required
- [ ] Add machine-readable component metadata if more developer tooling needs it
- [ ] Manually validate desktop dialogs and shortcuts on supported graphical platforms

## Phase 12 — Live preview (experimental)
- [x] `@ui.preview` metadata API, multiple named previews, and zero-argument validation
- [x] Discovery without invoking preview functions, renderer output, event handling, structured errors, reload cleanup
- [x] Debounced polling watcher with last-successful-render preservation and syntax-error recovery
- [x] Loopback renderer with dynamic port and random token required for tree/event API requests
- [x] Versioned JSON-lines control protocol and `novaui preview` CLI
- [x] VS Code extension source with preview selection, refresh, theme, viewport, error/loading status, CSP, and child cleanup
- [x] Examples and live-preview guide
- [x] VS Code Extension Host integration tests
- [ ] Marketplace packaging/review
- [ ] Browser automated test for button interaction and preview refresh
- [ ] Preserve in-memory state across hot reloads and support broader dependency tracking
- [ ] Validate current Webview sandbox/CSP behavior on Linux, Windows, and macOS
