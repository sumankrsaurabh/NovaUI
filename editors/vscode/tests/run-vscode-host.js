const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const extensionPath = path.resolve(__dirname, '..');
const repository = path.resolve(extensionPath, '../..');
const code = process.env.CODE_CLI || 'code';
const python = process.env.NOVAUI_TEST_PYTHON || path.join(repository, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const tempRoot = fs.mkdtempSync(path.join(repository, '.vscode-host-test-'));
const workspace = path.join(tempRoot, 'workspace');
const userData = path.join(tempRoot, 'user-data');
const resultFile = path.join(tempRoot, 'host-result.json');
fs.mkdirSync(workspace);
fs.mkdirSync(path.join(userData, 'User'), { recursive: true });
fs.writeFileSync(path.join(userData, 'User', 'settings.json'), JSON.stringify({
  'security.workspace.trust.enabled': false,
  'novaui.pythonPath': python,
}));
fs.writeFileSync(path.join(workspace, 'preview.py'), [
  'import novaui as ui',
  '@ui.preview',
  'def Counter():',
  '    count = ui.preview_state("count", 0)',
  '    return ui.Column(ui.Text(lambda: f"Count: {count.value}"), ui.Button("+", on_click=lambda: count.update(count.value + 1)))',
  '',
].join('\n'));

const env = {
  ...process.env,
  PYTHONPATH: [repository, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
  NOVAUI_TEST_PYTHON: python,
  NOVAUI_VSCODE_TEST_RESULT: resultFile,
};
const args = [
  '--new-window',
  '--wait',
  `--user-data-dir=${userData}`,
  '--disable-extensions',
  '--skip-welcome',
  `--extensionDevelopmentPath=${extensionPath}`,
  `--extensionTestsPath=${path.join(__dirname, 'vscode-host.test.js')}`,
  workspace,
];

const child = spawn(code, args, { env, stdio: 'inherit', windowsHide: true });
let finished = false;
const timer = setTimeout(() => {
  if (finished) return;
  console.error('VS Code extension-host test timed out after 90 seconds.');
  child.kill();
}, 90_000);
child.on('error', (error) => {
  console.error(`Could not launch VS Code (${error.message}). Install VS Code or set CODE_CLI to its executable.`);
  process.exitCode = 1;
});
child.on('exit', (code, signal) => {
  finished = true;
  clearTimeout(timer);
  let testResult;
  try { testResult = JSON.parse(fs.readFileSync(resultFile, 'utf8')); } catch (_) { /* host test did not complete */ }
  process.exitCode = code === 0 && testResult?.ok === true ? 0 : 1;
  if (!testResult) console.error('VS Code exited without reporting Extension Host test results.');
  else console.log(`VS Code Extension Host checks passed: ${testResult.checks.join(', ')}`);
  if (signal) console.error(`VS Code exited from signal ${signal}.`);
  if (testResult?.ok === true) fs.rmSync(tempRoot, { recursive: true, force: true });
  else console.error(`Preserved VS Code test profile for diagnosis: ${tempRoot}`);
});
