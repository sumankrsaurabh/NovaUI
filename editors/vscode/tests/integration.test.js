const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn: realSpawn } = require('node:child_process');
const Module = require('node:module');
const { test } = require('node:test');

const repository = path.resolve(__dirname, '../../..');

class FakeWebview {
  constructor() {
    this.messages = [];
    this.listeners = [];
    this.html = '';
  }
  postMessage(message) {
    this.messages.push(message);
    return Promise.resolve(true);
  }
  onDidReceiveMessage(listener) {
    this.listeners.push(listener);
    return { dispose: () => { this.listeners = this.listeners.filter((item) => item !== listener); } };
  }
  fire(message) {
    for (const listener of this.listeners) listener(message);
  }
}

class FakePanel extends EventEmitter {
  constructor() {
    super();
    this.webview = new FakeWebview();
    this.disposables = [];
  }
  onDidDispose(listener) {
    this.on('dispose', listener);
    return { dispose: () => this.off('dispose', listener) };
  }
  dispose() { this.emit('dispose'); }
}

function makeVscode(workspace, source) {
  const commands = new Map();
  const errors = [];
  const panel = new FakePanel();
  const editor = {
    document: {
      languageId: 'python',
      uri: { fsPath: source },
    },
  };
  const vscode = {
    commands: {
      registerCommand(name, callback) {
        commands.set(name, callback);
        return { dispose: () => commands.delete(name) };
      },
      executeCommand: async () => undefined,
    },
    ViewColumn: { Beside: 2 },
    window: {
      activeTextEditor: editor,
      showErrorMessage: (message) => errors.push(String(message)),
      showWarningMessage: (message) => errors.push(String(message)),
      showInformationMessage: (message) => errors.push(String(message)),
      showQuickPick: async (items) => items[0],
      createWebviewPanel: () => panel,
    },
    workspace: {
      isTrusted: true,
      getWorkspaceFolder: () => ({ uri: { fsPath: workspace } }),
      getConfiguration: () => ({ get: (_key, fallback) => fallback }),
    },
  };
  return { vscode, commands, errors, panel };
}

function waitFor(predicate, timeout = 8000, context = () => '') {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    const poll = () => {
      const value = predicate();
      if (value) return resolve(value);
      if (Date.now() - started > timeout) return reject(new Error(`Timed out waiting for VS Code preview integration event. ${context()}`));
      setTimeout(poll, 25);
    };
    poll();
  });
}

function writeApp(source, { value = 'First version', extra = false } = {}) {
  const additional = extra ? `\n@ui.preview(id="settings", name="Settings")\ndef Settings(): return ui.Text("Settings preview")\n` : '';
  fs.writeFileSync(source, `import novaui as ui\n@ui.preview(id="counter", name="Counter")\ndef Counter():\n    count = ui.preview_state("count", 0)\n    return ui.Column(ui.Text(${JSON.stringify(value)}), ui.Text(lambda: f"Count: {count.value}"), ui.Button("+", on_click=lambda: count.update(count.value + 1)))\n${additional}`);
}

function loadExtensionWithVscode(vscode) {
  const originalLoad = Module._load;
  Module._load = function(request, parent, isMain) {
    if (request === 'vscode') return vscode;
    return originalLoad.call(this, request, parent, isMain);
  };
  const extensionPath = require.resolve('../extension');
  delete require.cache[extensionPath];
  const extension = require(extensionPath);
  Module._load = originalLoad;
  return extension;
}

test('extension launches real preview runtime, routes controls, hot reloads, and cleans up', async (t) => {
  const workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'novaui-vscode-preview-'));
  const source = path.join(workspace, 'preview.py');
  writeApp(source);
  const { vscode, commands, panel, errors } = makeVscode(workspace, source);
  const extension = loadExtensionWithVscode(vscode);
  const context = { subscriptions: [] };
  const children = [];
  const originalSpawn = require('node:child_process').spawn;
  const childProcess = require('node:child_process');
  childProcess.spawn = (command, args, options) => {
    const python = process.env.NOVAUI_TEST_PYTHON || path.join(repository, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
    const environment = { ...process.env, ...(options.env || {}) };
    environment.PYTHONPATH = [repository, environment.PYTHONPATH].filter(Boolean).join(path.delimiter);
    const child = realSpawn(python, args, { ...options, env: environment });
    children.push(child);
    return child;
  };
  t.after(async () => {
    childProcess.spawn = originalSpawn;
    await extension.deactivate();
    for (const child of children) {
      if (child.exitCode === null) child.kill();
    }
    fs.rmSync(workspace, { recursive: true, force: true });
  });

  extension.activate(context);
  await commands.get('novaui.openLivePreview')();
  const ready = await waitFor(() => panel.webview.messages.find((item) => item.type === 'ready'));
  assert.match(panel.webview.html, /frame\.title='NovaUI component preview'/);
  assert.equal(ready.selected, 'Counter');
  assert.equal(ready.previews.length, 1);

  const token = new URLSearchParams(new URL(ready.url).hash.slice(1)).get('novaui-preview-token');
  const headers = { 'X-NovaUI-Preview-Token': token, 'X-NovaUI-Request': 'tree' };
  const treeResponse = await fetch(new URL('api/tree', ready.url), { headers });
  assert.equal(treeResponse.status, 200);
  let tree = await treeResponse.json();
  assert.equal(tree.root.children[0].text, 'First version');
  const clickResponse = await fetch(new URL('api/event', ready.url), {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json', Origin: new URL(ready.url).origin },
    body: JSON.stringify({ event_id: tree.root.children[2].event_id }),
  });
  assert.equal(clickResponse.status, 200);
  tree = await clickResponse.json();
  assert.equal(tree.root.children[1].text, 'Count: 1');

  panel.webview.fire({ version: 1, type: 'reset' });
  const reset = await waitFor(() => panel.webview.messages.find((item) => item.type === 'reset'));
  assert.equal(reset.ok, true);
  assert.match((await (await fetch(new URL('api/tree', ready.url), { headers })).text()), /Count: 0/);

  writeApp(source, { value: 'Updated version', extra: true });
  const updated = await waitFor(() => panel.webview.messages.find((item) => item.type === 'update' && item.previews?.length === 2), 8000,
    () => JSON.stringify(panel.webview.messages.map(({ type, ok, error, previews }) => ({ type, ok, error: error?.type, count: previews?.length }))));
  assert.equal(updated.ok, true);
  assert.match(JSON.stringify(updated.tree), /Updated version/);
  assert.deepEqual(updated.previews.map((item) => item.name), ['Counter', 'Settings']);

  panel.webview.fire({ version: 1, type: 'select', name: 'Settings' });
  const selected = await waitFor(() => panel.webview.messages.find((item) => item.type === 'select' && item.selected === 'Settings'));
  assert.equal(selected.ok, true);
  tree = await (await fetch(new URL('api/tree', ready.url), { headers })).json();
  assert.match(JSON.stringify(tree), /Settings preview/);

  fs.writeFileSync(source, 'import novaui as ui\n@ui.preview\ndef Broken(:\n');
  const syntaxError = await waitFor(() => panel.webview.messages.find((item) => item.type === 'update' && item.error?.type === 'SyntaxError'));
  assert.equal(syntaxError.ok, false);
  assert.match(JSON.stringify(syntaxError.tree), /Settings preview/);
  const updatesBeforeRecovery = panel.webview.messages.filter((item) => item.type === 'update').length;
  writeApp(source, { value: 'Recovered', extra: true });
  const recovered = await waitFor(() => {
    const updates = panel.webview.messages.filter((item) => item.type === 'update');
    return updates.length > updatesBeforeRecovery && updates[updates.length - 1].ok === true ? updates[updates.length - 1] : false;
  }, 8000,
    () => JSON.stringify(panel.webview.messages.map(({ type, ok, error, selected }) => ({ type, ok, error: error?.type, selected }))));
  assert.equal(recovered.selected, 'Settings');
  assert.equal(errors.length, 0);

  const child = children[children.length - 1];
  panel.dispose();
  await waitFor(() => child.exitCode !== null);
  assert.equal(child.exitCode, 0);
});
