const vscode = require('vscode');
const cp = require('child_process');
const path = require('path');

let active;

function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand('novaui.openLivePreview', () => openPreview(context)),
    vscode.commands.registerCommand('novaui.refreshPreview', () => send({ version: 1, type: 'refresh' })),
    vscode.commands.registerCommand('novaui.selectPreview', () => choosePreview()),
    vscode.commands.registerCommand('novaui.resetPreviewState', () => send({ version: 1, type: 'reset' }))
  );
}

async function openPreview(context) {
  const editor = vscode.window.activeTextEditor;
  const folder = vscode.workspace.getWorkspaceFolder(editor?.document.uri);
  if (!editor || editor.document.languageId !== 'python' || !folder) {
    vscode.window.showErrorMessage('Open a Python file inside a NovaUI workspace first.');
    return;
  }
  if (!vscode.workspace.isTrusted) {
    vscode.window.showWarningMessage('NovaUI previews execute trusted Python from the workspace. Trust this workspace before opening a live preview.');
    return;
  }
  const workspace = folder.uri.fsPath;
  const source = editor.document.uri.fsPath;
  if (!isWithin(workspace, source)) {
    vscode.window.showErrorMessage('The preview source must be inside the selected workspace.');
    return;
  }
  await stopRuntime();
  const configuredPython = vscode.workspace.getConfiguration('novaui').get('pythonPath', '');
  const python = typeof configuredPython === 'string' && configuredPython.trim()
    ? configuredPython.trim()
    : (global.process.platform === 'win32' ? 'python' : 'python3');
  const listed = await runList(python, workspace, source);
  if (!listed) return;
  if (listed.length === 0) {
    vscode.window.showInformationMessage('No @ui.preview functions were found in this file.');
    return;
  }
  let selected = listed.length === 1 ? listed[0].name : undefined;
  if (listed.length > 1) {
    const choice = await vscode.window.showQuickPick(listed.map((item) => ({ label: item.name, description: item.function })), { placeHolder: 'Select a NovaUI preview' });
    if (!choice) return;
    selected = choice.label;
  }
  const panel = vscode.window.createWebviewPanel('novauiPreview', 'NovaUI Preview', vscode.ViewColumn.Beside, {
    enableScripts: true,
    retainContextWhenHidden: true,
    localResourceRoots: []
  });
  const process = cp.spawn(python, ['-m', 'novaui', 'preview', source, '--name', selected, '--no-browser', '--json-protocol'], {
    cwd: workspace, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe']
  });
  const session = { panel, process, previews: listed, source, workspace, pending: '', disposables: [] };
  active = session;
  panel.webview.html = renderWebview(panel.webview, null, listed, selected);
  process.stdout.setEncoding('utf8');
  process.stdout.on('data', (chunk) => receiveStdout(session, chunk));
  process.stderr.setEncoding('utf8');
  process.stderr.on('data', (text) => {
    const clean = String(text).slice(0, 2000);
    panel.webview.postMessage({ version: 1, type: 'diagnostic', message: clean });
  });
  process.on('error', (error) => panel.webview.postMessage({ version: 1, type: 'diagnostic', message: `Could not start Python: ${error.message}. Set novaui.pythonPath to an interpreter with NovaUI installed.` }));
  process.on('exit', (code) => {
    if (active === session && code !== 0) panel.webview.postMessage({ version: 1, type: 'diagnostic', message: `Preview runtime exited (${code}). Check Python and NovaUI installation.` });
  });
  session.disposables.push(panel.webview.onDidReceiveMessage((message) => handleWebviewMessage(session, message)));
  session.disposables.push(panel.onDidDispose(() => stopRuntime(session)));
  context.subscriptions.push({ dispose: () => stopRuntime(session) });
}

async function runList(python, workspace, source) {
  return new Promise((resolve) => {
    const child = cp.spawn(python, ['-m', 'novaui', 'preview', source, '--list'], { cwd: workspace, windowsHide: true });
    let stdout = '', stderr = '';
    child.stdout.setEncoding('utf8').on('data', (part) => { stdout += part; });
    child.stderr.setEncoding('utf8').on('data', (part) => { stderr += part; });
    child.on('error', (error) => { vscode.window.showErrorMessage(`Could not run NovaUI Python runtime: ${error.message}. Configure novaui.pythonPath.`); resolve(null); });
    child.on('exit', (code) => {
      if (code !== 0) { vscode.window.showErrorMessage(stderr.trim() || 'Preview discovery failed. Install NovaUI into the selected Python environment.'); resolve(null); return; }
      try { resolve(JSON.parse(stdout).previews); } catch (_) { vscode.window.showErrorMessage('NovaUI returned an invalid preview list.'); resolve(null); }
    });
  });
}

function receiveStdout(session, chunk) {
  session.pending += chunk;
  const lines = session.pending.split(/\r?\n/);
  session.pending = lines.pop() || '';
  for (const line of lines) {
    if (!line.startsWith('NOVAUI_PREVIEW ')) continue;
    try {
      const message = JSON.parse(line.slice('NOVAUI_PREVIEW '.length));
      if (message.version !== 1 || typeof message.type !== 'string') continue;
      if (message.type === 'ready' && (!validPreviewUrl(message.url) ||
          !session.previews.some((item) => item.name === message.selected))) continue;
      if (!['ready', 'loading', 'update', 'refresh', 'select', 'reset'].includes(message.type)) continue;
      if (Array.isArray(message.previews)) session.previews = message.previews.filter((item) =>
        item && typeof item.name === 'string' && typeof item.function === 'string' && typeof item.id === 'string');
      session.panel.webview.postMessage(message);
    } catch (_) { /* malformed child output is ignored; it never becomes executable webview content */ }
  }
}

function handleWebviewMessage(session, message) {
  if (active !== session || !message || message.version !== 1 || typeof message.type !== 'string') return;
  if (message.type === 'refresh') send({ version: 1, type: 'refresh' }, session);
  else if (message.type === 'reset') send({ version: 1, type: 'reset' }, session);
  else if (message.type === 'select' && session.previews.some((item) => item.name === message.name)) send({ version: 1, type: 'select', name: message.name }, session);
  else if (message.type === 'theme' && ['light', 'dark'].includes(message.theme)) send({ version: 1, type: 'theme', theme: message.theme }, session);
  else if (message.type === 'viewport' && Number.isInteger(message.width) && Number.isInteger(message.height) && message.width >= 100 && message.width <= 4096 && message.height >= 100 && message.height <= 4096)
    send({ version: 1, type: 'viewport', width: message.width, height: message.height }, session);
}

function send(message, session = active) {
  if (session?.process?.stdin?.writable) session.process.stdin.write(`${JSON.stringify(message)}\n`);
}

async function choosePreview() {
  if (!active) return vscode.commands.executeCommand('novaui.openLivePreview');
  const choice = await vscode.window.showQuickPick(active.previews.map((item) => ({ label: item.name, description: item.function })));
  if (choice) send({ version: 1, type: 'select', name: choice.label });
}

async function stopRuntime(session = active) {
  if (!session) return;
  if (session.stopping) return session.stopping;
  session.stopping = (async () => {
    if (active === session) active = undefined;
    for (const disposable of session.disposables || []) disposable.dispose();
    if (session.process && session.process.exitCode === null) {
      send({ version: 1, type: 'shutdown' }, session);
      const child = session.process;
      await new Promise((resolve) => {
        const timer = setTimeout(() => { child.kill(); resolve(); }, 2000);
        child.once('exit', () => { clearTimeout(timer); resolve(); });
      });
    }
  })();
  return session.stopping;
}

function validPreviewUrl(value) {
  try {
    const url = new URL(value);
    const token = new URLSearchParams(url.hash.slice(1)).get('novaui-preview-token');
    return url.protocol === 'http:' && url.hostname === '127.0.0.1' &&
      Number(url.port) > 0 && url.port <= 65535 && url.pathname === '/' &&
      !url.username && !url.password && /^[A-Za-z0-9_-]{43}$/.test(token || '');
  } catch (_) { return false; }
}

function isWithin(root, target) {
  const relative = path.relative(root, target);
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative));
}

function renderWebview(webview, url, previews, selected) {
  const nonce = require('crypto').randomBytes(16).toString('base64');
  const options = previews.map((item) => `<option value="${escapeHtml(item.name)}"${item.name === selected ? ' selected' : ''}>${escapeHtml(item.name)}</option>`).join('');
  const frame = url ? `<iframe title="NovaUI component preview" sandbox="allow-scripts allow-same-origin" src="${escapeHtml(url)}"></iframe>` : '<div class="empty">Starting NovaUI preview runtime…</div>';
  return `<!doctype html><html><head><meta charset="UTF-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'nonce-${nonce}'; script-src 'nonce-${nonce}'; frame-src http://127.0.0.1:*; img-src data: https:"><meta name="viewport" content="width=device-width, initial-scale=1"><style nonce="${nonce}">
  :root{color-scheme:light dark;font:13px var(--vscode-font-family);color:var(--vscode-foreground);background:var(--vscode-editor-background)}body{margin:0;display:flex;height:100vh;flex-direction:column}.bar{display:flex;gap:6px;align-items:center;padding:7px;border-bottom:1px solid var(--vscode-panel-border);flex-wrap:wrap}button,select,input{color:inherit;background:var(--vscode-input-background);border:1px solid var(--vscode-input-border);border-radius:4px;padding:5px}button{cursor:pointer}.spacer{flex:1}.frame{flex:1;display:grid;place-items:center;overflow:auto;background:var(--vscode-editor-background)}iframe{border:0;width:100%;height:100%;background:white}.error{display:none;white-space:pre-wrap;padding:12px;margin:0;color:var(--vscode-errorForeground)}.empty{opacity:.8;padding:18px}</style></head><body><div class="bar"><select id="preview" aria-label="Select preview">${options}</select><button id="refresh">Refresh</button><button id="reset">Reset state</button><select id="theme" aria-label="Preview theme"><option value="light">Light</option><option value="dark">Dark</option></select><select id="profile" aria-label="Viewport preset"><option value="custom">Custom</option><option value="390x844">Mobile · 390 × 844</option><option value="768x1024">Tablet · 768 × 1024</option><option value="1440x900">Desktop · 1440 × 900</option></select><label>W <input id="width" type="number" min="100" max="4096" value="1024" aria-label="Viewport width"></label><label>H <input id="height" type="number" min="100" max="4096" value="768" aria-label="Viewport height"></label><button id="fit">Fit</button><span class="spacer"></span><span id="status" role="status">Starting</span></div><pre id="error" class="error" role="alert"></pre><main class="frame">${frame}</main><script nonce="${nonce}">
  const vscode=acquireVsCodeApi();const post=(type,extra={})=>vscode.postMessage({version:1,type,...extra});const byId=id=>document.getElementById(id);const setOptions=(items,selected)=>{const select=byId('preview');select.replaceChildren();for(const item of items){const option=document.createElement('option');option.value=item.name;option.textContent=item.name;select.append(option)}if(selected&&items.some(item=>item.name===selected))select.value=selected;select.disabled=items.length===0};byId('preview').onchange=e=>{byId('status').textContent='Loading…';post('select',{name:e.target.value})};byId('refresh').onclick=()=>{byId('status').textContent='Refreshing…';post('refresh')};byId('reset').onclick=()=>{byId('status').textContent='Resetting state…';post('reset')};byId('theme').onchange=e=>post('theme',{theme:e.target.value});const resize=()=>{const w=Number(byId('width').value),h=Number(byId('height').value),frame=document.querySelector('iframe');if(!Number.isInteger(w)||!Number.isInteger(h)||w<100||w>4096||h<100||h>4096)return;if(frame){frame.style.width=w+'px';frame.style.height=h+'px';frame.style.maxWidth='100%';frame.style.maxHeight='none'}post('viewport',{width:w,height:h})};byId('width').onchange=()=>{byId('profile').value='custom';resize()};byId('height').onchange=()=>{byId('profile').value='custom';resize()};byId('profile').onchange=e=>{if(e.target.value==='custom')return;const [w,h]=e.target.value.split('x');byId('width').value=w;byId('height').value=h;resize()};byId('fit').onclick=()=>{byId('width').value=Math.max(100,window.innerWidth-24);byId('height').value=Math.max(100,window.innerHeight-100);byId('profile').value='custom';resize()};window.addEventListener('message',e=>{const m=e.data;if(!m||m.version!==1)return;if(m.type==='ready'){const frame=document.createElement('iframe');frame.title='NovaUI component preview';frame.setAttribute('sandbox','allow-scripts allow-same-origin');frame.src=m.url;document.querySelector('main').replaceChildren(frame);byId('width').value=m.viewport?.width||1024;byId('height').value=m.viewport?.height||768;byId('theme').value=m.theme||'light';setOptions(m.previews||[],m.selected);byId('status').textContent='Ready';resize()}else if(m.type==='loading'){byId('status').textContent='Reloading…'}else if(['update','refresh','select','reset'].includes(m.type)){if(Array.isArray(m.previews))setOptions(m.previews,m.selected);else if(m.selected)byId('preview').value=m.selected;byId('status').textContent=m.ok===false?'Error':(m.type==='reset'?'State reset':'Updated');if(m.error){const el=byId('error');el.style.display='block';el.textContent=m.error.type+': '+m.error.message+(m.error.file?('\n'+m.error.file+(m.error.line?':'+m.error.line:'')):'')}else{byId('error').style.display='none'}}else if(m.type==='diagnostic'||m.type==='error'){byId('status').textContent='Runtime error';const el=byId('error');el.style.display='block';el.textContent=String(m.message||m.error?.message||'Unknown preview error').slice(0,2000)}});</script></body></html>`;
}

function escapeHtml(value) { return String(value).replace(/[&<>"']/g, (char) => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[char])); }
function deactivate() { return stopRuntime(); }
module.exports = { activate, deactivate };
