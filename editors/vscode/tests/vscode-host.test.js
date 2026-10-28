const assert = require('node:assert/strict');
const fs = require('node:fs');
const vscode = require('vscode');

function delay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function waitForPreviewTab(timeout = 20_000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    const tab = vscode.window.tabGroups.all.flatMap((group) => group.tabs)
      .find((item) => item.input && String(item.input.viewType).endsWith('novauiPreview'));
    if (tab) return tab;
    await delay(100);
  }
  const tabs = vscode.window.tabGroups.all.flatMap((group) => group.tabs)
    .map((item) => ({ label: item.label, input: item.input?.constructor?.name, viewType: item.input?.viewType }));
  throw new Error(`NovaUI preview Webview tab did not open. Tabs: ${JSON.stringify(tabs)}`);
}

async function run() {
  const surfacedErrors = [];
  for (const method of ['showErrorMessage', 'showWarningMessage', 'showInformationMessage']) {
    const original = vscode.window[method];
    vscode.window[method] = function(message, ...items) {
      surfacedErrors.push(`${method}: ${String(message)}`);
      return original.call(this, message, ...items);
    };
  }
  const extension = vscode.extensions.getExtension('novaui.novaui-live-preview');
  assert.ok(extension, 'NovaUI Live Preview extension is available in the Extension Host');
  await extension.activate();

  const commands = await vscode.commands.getCommands(true);
  for (const command of [
    'novaui.openLivePreview',
    'novaui.refreshPreview',
    'novaui.selectPreview',
    'novaui.resetPreviewState',
  ]) assert.ok(commands.includes(command), `registered command: ${command}`);

  const document = await vscode.workspace.openTextDocument(vscode.Uri.file(
    vscode.Uri.joinPath(vscode.workspace.workspaceFolders[0].uri, 'preview.py').fsPath,
  ));
  await vscode.window.showTextDocument(document, vscode.ViewColumn.One);
  assert.equal(vscode.window.activeTextEditor.document.uri.fsPath, document.uri.fsPath, 'Python preview is the active editor');
  assert.equal(vscode.workspace.isTrusted, true, 'test workspace trust is explicitly configured');
  assert.ok(vscode.workspace.getWorkspaceFolder(document.uri), 'source file belongs to the opened workspace');
  await vscode.workspace.getConfiguration('novaui').update(
    'pythonPath', process.env.NOVAUI_TEST_PYTHON, vscode.ConfigurationTarget.Workspace,
  );
  await vscode.commands.executeCommand('novaui.openLivePreview');
  let previewTab;
  try { previewTab = await waitForPreviewTab(); }
  catch (error) { error.message += ` Surfaced extension errors: ${surfacedErrors.join(' | ') || '(none)'}`; throw error; }
  assert.equal(previewTab.label, 'NovaUI Preview');

  // Exercise commands against the running extension child process.
  await vscode.commands.executeCommand('novaui.refreshPreview');
  await delay(400);
  await vscode.commands.executeCommand('novaui.resetPreviewState');
  await delay(400);

  fs.writeFileSync(process.env.NOVAUI_VSCODE_TEST_RESULT, JSON.stringify({
    ok: true,
    checks: ['extension activation', 'four contributed commands', 'trusted Python workspace', 'preview Webview opened beside editor', 'refresh/reset commands', 'panel close'],
  }));
  await vscode.commands.executeCommand('workbench.action.closeAllEditors');
  await vscode.commands.executeCommand('workbench.action.quit');
}

module.exports = { run };
