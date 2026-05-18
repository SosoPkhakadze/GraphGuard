import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

export function activate(context: vscode.ExtensionContext) {
    autoConfigureSettings(context.extensionUri);
    const provider = new GraphGuardViewProvider(context.extensionUri);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('graphguard.sidebar', provider, {
            webviewOptions: { retainContextWhenHidden: true },
        })
    );
}

function autoConfigureSettings(extensionUri: vscode.Uri) {
    const cfg = vscode.workspace.getConfiguration('graphguard');

    // Auto-detect libclang.dll on Windows if not set
    if (!cfg.get<string>('libclangPath')) {
        const candidates = [
            String.raw`C:\msys64\ucrt64\bin\libclang.dll`,
            String.raw`C:\msys64\mingw64\bin\libclang.dll`,
            String.raw`C:\Program Files\LLVM\bin\libclang.dll`,
            String.raw`C:\Program Files (x86)\LLVM\bin\libclang.dll`,
        ];
        const found = candidates.find(p => fs.existsSync(p));
        if (found) {
            cfg.update('libclangPath', found, vscode.ConfigurationTarget.Global);
        }
    }

    // Auto-detect Python if not set
    if (!cfg.get<string>('pythonPath')) {
        const pythonCandidates = ['python', 'python3', 'py'];
        for (const cmd of pythonCandidates) {
            try {
                const result = cp.spawnSync(cmd, ['--version'], { encoding: 'utf-8' });
                if (result.status === 0) {
                    cfg.update('pythonPath', cmd, vscode.ConfigurationTarget.Global);
                    break;
                }
            } catch { /* try next */ }
        }
    }

    // Auto-detect script path if not set
    if (!cfg.get<string>('scriptPath')) {
        const sibling = path.join(extensionUri.fsPath, '..', 'graphguard.py');
        if (fs.existsSync(sibling)) {
            cfg.update('scriptPath', sibling, vscode.ConfigurationTarget.Global);
        }
    }
}

export function deactivate() {}

// ── Paths ─────────────────────────────────────────────────────────────────────

function resolvePython(): string {
    const cfg = vscode.workspace.getConfiguration('graphguard');
    const custom = cfg.get<string>('pythonPath');
    if (custom) return custom;
    // On Windows 'python' is often absent; 'py' (launcher) is the reliable default
    return process.platform === 'win32' ? 'py' : 'python3';
}

function resolveScript(extensionUri: vscode.Uri): string | null {
    const cfg = vscode.workspace.getConfiguration('graphguard');
    const custom = cfg.get<string>('scriptPath');
    if (custom) {
        if (fs.existsSync(custom)) return custom;
        return null; // explicitly set but wrong — report the bad path
    }
    // When running from the repo (F5 dev mode), extensionUri is vscode-extension/
    const sibling = path.join(extensionUri.fsPath, '..', 'graphguard.py');
    if (fs.existsSync(sibling)) return sibling;

    return null;
}

// ── Provider ──────────────────────────────────────────────────────────────────

class GraphGuardViewProvider implements vscode.WebviewViewProvider {
    private _view?: vscode.WebviewView;
    private _watcher?: vscode.FileSystemWatcher;
    private _debounce?: ReturnType<typeof setTimeout>;
    private _running = false;

    constructor(private readonly _extensionUri: vscode.Uri) {}

    resolveWebviewView(
        webviewView: vscode.WebviewView,
        _context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ) {
        this._view = webviewView;
        webviewView.webview.options = { enableScripts: true };
        webviewView.webview.html = getWebviewHtml();

        webviewView.webview.onDidReceiveMessage(msg => {
            if (msg.type === 'analyze') {
                this._runAnalysis(msg.model, msg.approach);
            }
        });

        this._startWatcher();
        this._checkDiff();
    }

    // ── File watcher ─────────────────────────────────────────────────────────

    private _startWatcher() {
        this._watcher = vscode.workspace.createFileSystemWatcher('**/*.{c,h}');
        const debounce = () => {
            if (this._debounce) clearTimeout(this._debounce);
            this._debounce = setTimeout(() => this._checkDiff(), 600);
        };
        this._watcher.onDidChange(debounce);
        this._watcher.onDidCreate(debounce);
        this._watcher.onDidDelete(debounce);
    }

    // ── Git diff check ────────────────────────────────────────────────────────

    private _checkDiff() {
        const root = workspaceRoot();
        if (!root) return;

        cp.exec('git diff HEAD --name-only', { cwd: root }, (_err, stdout) => {
            const files = stdout.trim()
                .split('\n')
                .filter(f => f.endsWith('.c') || f.endsWith('.h'))
                .map(f => path.basename(f));

            this._view?.webview.postMessage({
                type: 'status',
                hasChanges: files.length > 0,
                files,
            });
        });
    }

    // ── Analysis runner ───────────────────────────────────────────────────────

    private _runAnalysis(model: string, approach: string) {
        if (this._running) return;
        const root = workspaceRoot();
        if (!root) return;

        const script = resolveScript(this._extensionUri);
        if (!script) {
            const configured = vscode.workspace.getConfiguration('graphguard').get<string>('scriptPath');
            const detail = configured
                ? `scriptPath is set to "${configured}" but that file does not exist.`
                : 'graphguard.py could not be found automatically.';
            this._view?.webview.postMessage({
                type: 'error',
                message: `${detail}\n\nFix: open VS Code Settings (Ctrl+,), search "graphguard",\nand set graphguard.scriptPath to the full path of graphguard.py.\n\nExample: C:\\Users\\you\\Desktop\\GraphGuard\\graphguard.py`,
            });
            return;
        }

        this._running = true;
        const python = resolvePython();
        const libclangPath =
            vscode.workspace.getConfiguration('graphguard').get<string>('libclangPath') ||
            process.env['LIBCLANG_PATH'] || '';

        const proc = cp.spawn(python, [script, 'analyze', '--model', model, '--approach', approach], {
            cwd: root,
            env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1', ...(libclangPath ? { LIBCLANG_PATH: libclangPath } : {}) },
        });

        proc.stdout.on('data', (data: Buffer) => {
            for (const raw of data.toString().split('\n')) {
                const line = raw.replace(/\r$/, '');
                if (line.trim()) {
                    this._view?.webview.postMessage({ type: 'output', line });
                }
            }
        });

        proc.stderr.on('data', (data: Buffer) => {
            const text = data.toString().replace(/\r\n/g, '\n').trim();
            if (text) {
                this._view?.webview.postMessage({ type: 'output', line: text });
            }
        });

        proc.on('close', (code) => {
            this._running = false;
            if (code !== 0) {
                this._view?.webview.postMessage({
                    type: 'output',
                    line: `\n[Process exited with code ${code}]`,
                });
            }
            // Re-check diff so button state reflects current state
            this._checkDiff();
            this._view?.webview.postMessage({ type: 'done' });
        });

        proc.on('error', (err: Error) => {
            this._running = false;
            this._view?.webview.postMessage({
                type: 'error',
                message: `Failed to start Python ("${python}"): ${err.message}\n\nFix: open VS Code Settings (Ctrl+,), search "graphguard",\nand set graphguard.pythonPath to your Python executable.\n\nExample: C:\\Users\\ASUS_ZEPHYRUS\\AppData\\Local\\Programs\\Python\\Python312\\python.exe`,
            });
        });
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function workspaceRoot(): string | undefined {
    return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}

// ── Webview HTML ──────────────────────────────────────────────────────────────

function getWebviewHtml(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  padding: 12px;
  font-family: var(--vscode-font-family);
  font-size: var(--vscode-font-size);
  color: var(--vscode-foreground);
  background: var(--vscode-sideBar-background);
}

h3 {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  opacity: 0.7;
  margin-bottom: 10px;
}

.status {
  font-size: 12px;
  padding: 6px 8px;
  border-radius: 3px;
  margin-bottom: 12px;
  border-left: 3px solid transparent;
}
.status.idle    { background: var(--vscode-inputValidation-infoBackground, #1a3a4a); border-color: #007acc; }
.status.ready   { background: var(--vscode-inputValidation-warningBackground, #352a05); border-color: #b89500; }

label { display: block; font-size: 11px; opacity: 0.7; margin: 8px 0 3px; }

select {
  width: 100%;
  padding: 4px 6px;
  background: var(--vscode-input-background);
  color: var(--vscode-input-foreground);
  border: 1px solid var(--vscode-input-border, #3c3c3c);
  border-radius: 2px;
  font-size: 12px;
  font-family: inherit;
}

#analyzeBtn {
  width: 100%;
  margin-top: 12px;
  padding: 7px;
  background: var(--vscode-button-background);
  color: var(--vscode-button-foreground);
  border: none;
  border-radius: 2px;
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  font-weight: 500;
}
#analyzeBtn:hover:not(:disabled) { background: var(--vscode-button-hoverBackground); }
#analyzeBtn:disabled { opacity: 0.4; cursor: not-allowed; }

#spinner { font-size: 11px; opacity: 0.6; margin-top: 8px; display: none; text-align: center; }

.clear-btn {
  font-size: 10px; opacity: 0.5; cursor: pointer; float: right;
  margin-top: 12px; background: none; border: none; color: inherit;
  text-decoration: underline; display: none;
}
.clear-btn:hover { opacity: 1; }

/* ── Result card ── */
#result {
  margin-top: 14px;
  display: none;
  font-size: 12px;
}

.section {
  margin-bottom: 10px;
}

.section-title {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  opacity: 0.55;
  margin-bottom: 5px;
  padding-bottom: 3px;
  border-bottom: 1px solid var(--vscode-panel-border, #3c3c3c);
}

.fn-item {
  padding: 2px 0 2px 10px;
  font-family: var(--vscode-editor-font-family, monospace);
  font-size: 11px;
  color: var(--vscode-symbolIcon-functionForeground, #dcdcaa);
}

.bug-item {
  padding: 3px 0 3px 10px;
  font-size: 11px;
  color: var(--vscode-errorForeground, #f48771);
  border-left: 2px solid var(--vscode-errorForeground, #f48771);
  margin: 2px 0;
}

.concerns {
  font-size: 12px;
  line-height: 1.5;
  opacity: 0.9;
  padding: 6px 8px;
  background: var(--vscode-editor-background);
  border-radius: 3px;
  border-left: 3px solid var(--vscode-panel-border, #3c3c3c);
}

.severity {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 10px;
  margin-bottom: 10px;
}
.sev-low      { background: #1e3a1e; color: #89d185; }
.sev-medium   { background: #3a2e05; color: #cca700; }
.sev-high     { background: #3a1a05; color: #f48771; }
.sev-critical { background: #3a0505; color: #ff6b6b; }
.sev-unknown  { background: #2a2a2a; color: #aaa; }

.tool-call {
  font-family: var(--vscode-editor-font-family, monospace);
  font-size: 10px;
  opacity: 0.5;
  padding: 1px 0 1px 10px;
}

/* ── Raw log (during streaming) ── */
#log {
  margin-top: 12px;
  font-family: var(--vscode-editor-font-family, monospace);
  font-size: 10px;
  opacity: 0.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 120px;
  overflow-y: auto;
  display: none;
  padding: 4px;
  border-left: 2px solid var(--vscode-panel-border, #3c3c3c);
}

.error-box {
  margin-top: 10px;
  padding: 8px;
  font-size: 11px;
  font-family: var(--vscode-editor-font-family, monospace);
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--vscode-inputValidation-errorBackground, #3a0505);
  border-left: 3px solid var(--vscode-errorForeground, #f48771);
  border-radius: 2px;
  display: none;
}
</style>
</head>
<body>

<h3>GraphGuard</h3>

<div id="status" class="status idle">Scanning for changes...</div>

<label for="model">Model</label>
<select id="model">
  <option value="claude-sonnet-4-6">Claude Sonnet 4.6</option>
  <option value="claude-opus-4-7">Claude Opus 4.7</option>
  <option value="claude-haiku-4-5-20251001">Claude Haiku 4.5</option>
  <option value="gpt-4o">GPT-4o</option>
  <option value="gpt-4o-mini">GPT-4o mini</option>
</select>

<label for="approach">Approach</label>
<select id="approach">
  <option value="agent">Agent — iterative tool calls</option>
  <option value="graph">Diff + Call Graph</option>
  <option value="diff">Diff only</option>
</select>

<button id="analyzeBtn" disabled>Analyze Impact</button>
<div id="spinner">Running analysis...</div>

<div id="log"></div>
<div id="result"></div>
<div id="errorBox" class="error-box"></div>

<button class="clear-btn" id="clearBtn">clear</button>

<script>
const vscode   = acquireVsCodeApi();
const btn      = document.getElementById('analyzeBtn');
const status   = document.getElementById('status');
const spinner  = document.getElementById('spinner');
const log      = document.getElementById('log');
const result   = document.getElementById('result');
const errorBox = document.getElementById('errorBox');
const clearBtn = document.getElementById('clearBtn');
let hasChanges = false;
let rawLines   = [];

btn.addEventListener('click', () => {
  const model    = document.getElementById('model').value;
  const approach = document.getElementById('approach').value;
  rawLines = [];
  log.textContent = '';
  log.style.display = 'block';
  result.style.display = 'none';
  result.innerHTML = '';
  errorBox.style.display = 'none';
  clearBtn.style.display = 'none';
  spinner.style.display = 'block';
  btn.disabled = true;
  vscode.postMessage({ type: 'analyze', model, approach });
});

clearBtn.addEventListener('click', () => {
  log.style.display = 'none';
  result.style.display = 'none';
  errorBox.style.display = 'none';
  clearBtn.style.display = 'none';
  rawLines = [];
});

window.addEventListener('message', event => {
  const msg = event.data;

  if (msg.type === 'status') {
    hasChanges = msg.hasChanges;
    if (msg.hasChanges) {
      const names = msg.files.slice(0, 3).join(', ') +
                    (msg.files.length > 3 ? \` +\${msg.files.length - 3} more\` : '');
      status.textContent = 'Changes: ' + names;
      status.className   = 'status ready';
      if (!spinner.style.display || spinner.style.display === 'none') btn.disabled = false;
    } else {
      status.textContent = 'No uncommitted changes in .c/.h files';
      status.className   = 'status idle';
      btn.disabled = true;
    }
  }

  else if (msg.type === 'output') {
    rawLines.push(msg.line);
    // Show agent tool calls in the small log during streaming
    if (msg.line.includes('[agent]')) {
      log.textContent += msg.line.trim() + '\\n';
      log.scrollTop = log.scrollHeight;
    }
  }

  else if (msg.type === 'done') {
    spinner.style.display = 'none';
    btn.disabled = !hasChanges;
    clearBtn.style.display = 'inline';
    log.style.display = 'none';
    renderResult(rawLines);
  }

  else if (msg.type === 'error') {
    spinner.style.display = 'none';
    btn.disabled = !hasChanges;
    clearBtn.style.display = 'inline';
    errorBox.textContent = msg.message;
    errorBox.style.display = 'block';
  }
});

// ── Parser: turn raw graphguard output lines into structured cards ──────────

function renderResult(lines) {
  const text = lines.join('\\n');

  // Pull out fields using the known output format
  const severity   = extract(text, /Severity\\s*:\\s*(\\S+)/i);
  const model      = extract(text, /Model\\s*:\\s*(.+)/i);
  const approach   = extract(text, /Approach\\s*:\\s*(.+)/i);
  const concerns   = extractBlock(lines, 'SUMMARY');
  const changed    = extractList(lines, 'FUNCTIONS DIRECTLY MODIFIED');
  const affected   = extractList(lines, 'WHAT WILL BE AFFECTED');
  const bugs       = extractList(lines, 'BUGS / RISKS INTRODUCED');
  const tools      = extractList(lines, 'TOOLS CALLED BY AGENT');

  if (!severity && !concerns && changed.length === 0) {
    // Couldn't parse — show raw
    result.innerHTML = '<div class="section"><div class="section-title">Output</div><pre style="font-size:11px;white-space:pre-wrap;word-break:break-word;opacity:.8">' + esc(text) + '</pre></div>';
    result.style.display = 'block';
    return;
  }

  let html = '';

  if (severity) {
    const cls = 'sev-' + severity.toLowerCase().replace(/[\\[\\]]/g, '');
    html += \`<span class="severity \${cls}">\${severity.replace(/[\\[\\]]/g, '')}</span>\`;
  }
  if (model && approach) {
    html += \`<div style="font-size:10px;opacity:.5;margin-bottom:10px">\${esc(model.trim())} — \${esc(approach.trim())}</div>\`;
  }

  if (changed.length) {
    html += section('Functions Modified', changed.map(f => \`<div class="fn-item">\${esc(f)}</div>\`).join(''));
  }
  if (affected.length) {
    html += section('What Will Be Affected', affected.map(f => \`<div class="fn-item">\${esc(f)}</div>\`).join(''));
  }
  if (bugs.length) {
    html += section('Bugs / Risks', bugs.map(b => \`<div class="bug-item">\${esc(b)}</div>\`).join(''));
  }
  if (concerns) {
    html += section('Summary', \`<div class="concerns">\${esc(concerns)}</div>\`);
  }
  if (tools.length) {
    html += section('Agent Tools Called', tools.map((t,i) => \`<div class="tool-call">\${i+1}. \${esc(t)}</div>\`).join(''));
  }

  result.innerHTML = html;
  result.style.display = 'block';
}

function section(title, body) {
  return \`<div class="section"><div class="section-title">\${title}</div>\${body}</div>\`;
}

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function extract(text, re) {
  const m = text.match(re);
  return m ? m[1].trim() : null;
}

function extractBlock(lines, header) {
  let capture = false;
  const out = [];
  for (const line of lines) {
    if (line.includes(header)) { capture = true; continue; }
    if (capture) {
      if (line.match(/^[\\s]*[-=]{4,}/) || line.match(/^\\s{2,}[A-Z /]{4,}$/)) break;
      const t = line.trim();
      if (t) out.push(t);
    }
  }
  return out.join(' ').trim() || null;
}

function extractList(lines, header) {
  let capture = false;
  const items = [];
  for (const line of lines) {
    if (line.includes(header)) { capture = true; continue; }
    if (capture) {
      if (line.match(/^\\s*[=]{4,}/) || (line.match(/^\\s{2,}[A-Z /]{4,}$/) && !line.includes('-'))) break;
      const t = line.replace(/^\\s*[-!\\d.]+\\s*/, '').trim();
      if (t && !t.match(/^[-=]{3,}/)) items.push(t);
    }
  }
  return items;
}
</script>

</body>
</html>`;
}
