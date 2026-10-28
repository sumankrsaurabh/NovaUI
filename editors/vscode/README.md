# NovaUI Live Preview for VS Code

This source extension starts the trusted Python NovaUI preview runtime as a child process and embeds its loopback-rendered page in a VS Code Webview. The Webview sends only validated JSON controls; it never evaluates workspace Python.

## Requirements

- VS Code 1.85 or later.
- A selected Python interpreter with NovaUI installed (`python -m pip install -e .` from the repository, or install the published package).
- Open the preview source inside a workspace folder.
- Trust the workspace in VS Code before opening a preview; its Python module is executed locally.

By default the extension uses `python` on Windows and `python3` on macOS/Linux. Set `novaui.pythonPath` to the interpreter that has NovaUI installed when needed (for example `.venv/bin/python` on Linux/macOS or `.venv\\Scripts\\python.exe` on Windows). Run **NovaUI: Open Live Preview** from the Command Palette. The selected file and imported local Python modules are watched by NovaUI's polling watcher.

Commands: **NovaUI: Open Live Preview**, **NovaUI: Refresh Preview**, **NovaUI: Select Preview**, and **NovaUI: Reset Preview State**. The panel selector tracks additions, renames, and removals after source reloads. It also provides light/dark themes, custom viewport dimensions, Mobile (390×844), Tablet (768×1024), Desktop (1440×900), and Fit controls.

## Development

From this directory, run `npm run check` for JavaScript syntax and manifest checks. Run `npm run test:integration` for the Node integration test: it mocks the VS Code API surface but starts the real Python NovaUI preview child process and exercises the authenticated renderer, event dispatch, preview selection, state reset, source hot reload, syntax-error recovery, and shutdown.

For an actual VS Code Extension Host smoke test, install VS Code and run `npm run test:vscode` from this directory. The test uses the installed `code` CLI and opens a temporary isolated profile/workspace; set `CODE_CLI` if the executable is not named `code`, or `NOVAUI_TEST_PYTHON` to select a Python interpreter with NovaUI installed. It checks extension activation, command registration, opening the Webview beside a Python source file, refresh/reset commands, and panel closure. This requires a working graphical session. The tests do not install Marketplace packages. The included launch configuration remains available for interactive extension development. Package the extension with `vsce package` only after installing the VS Code packaging tool separately.

## Security and limits

Workspace Python executes in the configured Python process and is trusted code, not sandboxed. The runtime binds to `127.0.0.1`, uses a random session token for renderer API calls, and is stopped when the panel closes. Source paths must remain under the opened workspace. Webview scripts use a nonce CSP and a narrow message schema. The preview iframe intentionally runs the NovaUI frontend; this is not a security boundary against malicious workspace code. This extension targets VS Code only; PyCharm support is not implemented.
