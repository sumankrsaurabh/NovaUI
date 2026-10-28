# Live Preview Architecture

## Current NovaUI rendering path

NovaUI components are ordinary Python objects derived from `Component`. Their
`to_dict()` methods validate properties and serialize a JSON-safe tree.
`App.serialize_tree()` owns that operation, registers opaque event identifiers,
and tracks component resources for disposal. The existing local HTTP server
serves the packaged `novaui/frontend/` renderer and delegates event requests to
the owning `App`. Browser and optional desktop hosting both use this pipeline.

The preview feature will reuse those APIs. It will not implement a second
component model, renderer, or event protocol. A selected preview function will
produce a normal component tree, which is wrapped in a short-lived `App` for
serialization or served through the existing local runtime when interactive
hosting is requested.

## Preview declarations and discovery

`@NovaPreview` (also available as `@preview` and `@ui.preview`) attaches immutable preview metadata to a Python function. It does
not invoke the function or register a process-global callable. Discovery loads
the requested source file as a trusted Python module, scans its namespace for
decorated functions, and returns their names and display configuration. This
necessarily executes module-level Python code, as normal Python imports do.
Only files within the explicitly selected workspace may be loaded. Preview
functions must take no parameters and either return a NovaUI `Component` or
compose components directly in the function body. Multiple roots are grouped
in a layout-neutral `Fragment`. `@NovaComponent` functions follow the same rule
and may accept regular Python parameters. A preview can create its own state
each time it is invoked.

Display names and stable identifiers are unique within a loaded module. If
`name=` is omitted, the function's Python name is used; `id=` defaults to the
function name and can remain fixed when a display label changes. Discovery
reports malformed declarations and duplicate names or identifiers as
diagnostics instead of invoking previews to infer metadata.

Normal `state()` values are initialized each time the preview function runs.
An explicit `preview_state(key, initial)` scope lets a preview retain values
between source reloads. The runtime stages this map during rendering and commits
it only after successful serialization. A changed value type replaces that key;
removed keys are disposed after a successful update. State maps are keyed by
preview id, so switching previews does not share state. Reset clears only the
selected preview's map. No arbitrary object serialization or memory inspection
is used.

## Runtime and lifecycle

`PreviewRuntime` owns the resolved workspace boundary, active module instance,
selected preview, and last successful serialized result. Each source reload
uses a fresh module identity. Replaced modules and previous component trees are
disposed after a new render succeeds; a syntax or render error is returned as
structured diagnostic data and does not replace the last good preview. A
manual refresh and file watcher use the same reload path. The watcher is
optional and must ignore caches, build output, virtual environments, and files
outside the workspace.

The preview CLI starts the selected preview without calling `ui.app()` or
starting the application's normal entry-point lifecycle. Interactive preview
hosting reuses NovaUI's loopback HTTP server and opaque event bridge. Preview
shutdown disposes the active app and closes its server/thread.

## IDE boundary and security

The VS Code extension is a separate package and uses VS Code's official
extension APIs. The Webview communicates with its extension host using version
1 validated JSON messages over VS Code's private Webview bridge. The extension
launches the Python runtime and exchanges JSON lines over private child-process
stdin/stdout pipes. The embedded renderer runs on a loopback-only NovaUI server
and API requests carry a short-lived per-session random token. Workspace paths
are resolved and checked by the Python host.
The webview never submits Python source for evaluation; source files are loaded
by the local Python process as trusted workspace code. Opening an untrusted
workspace can execute its module-level Python code, so the extension must make
that trust boundary clear and follow VS Code's workspace trust behavior.

The webview uses a restrictive Content Security Policy, minimal capabilities,
and message allowlists. Tokens are session-scoped and must not be included in
logs. The preview server binds to `127.0.0.1` on an available port. A random
port is not treated as authentication by itself.

## Protocol evolution

The implemented JSON-lines protocol uses a top-level version field and message
type. It covers discovery, selection, render status, errors, theme/viewport
changes, refresh, and shutdown. The Python runtime validates commands and the
extension validates messages before forwarding them. Unsupported protocol
versions and unknown fields/types are rejected. The HTTP tree and event
endpoints require the separate session token.

## Incremental implementation

The current vertical slice includes the decorator, module discovery without
calling preview functions, selected-preview rendering through
`App.serialize_tree()`, hot reload, authenticated local HTTP rendering, a CLI,
and a source VS Code extension. The extension is not Marketplace packaged and
has no automated VS Code integration-test harness yet.

## Known constraints

- Discovery imports the selected workspace file and therefore executes its
  module-level Python code; NovaUI does not sandbox Python.
- Preview functions are synchronous and accept no arguments.
- Component/state updates use the current request-and-serialize behavior; this
  is not push-based background synchronization.
- A browser renderer or VS Code Webview is required for visual preview. The
  Python runtime alone can validate and serialize a preview but cannot display
  pixels.
