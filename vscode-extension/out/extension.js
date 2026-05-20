"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const cp = __importStar(require("child_process"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
function activate(context) {
    autoConfigureSettings(context.extensionUri);
    const provider = new GraphGuardViewProvider(context.extensionUri);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider('graphguard.sidebar', provider, {
        webviewOptions: { retainContextWhenHidden: true },
    }));
}
// ── Auto-configure on first install ──────────────────────────────────────────
function autoConfigureSettings(extensionUri) {
    const cfg = vscode.workspace.getConfiguration('graphguard');
    if (!cfg.get('pythonPath')) {
        const detected = detectPython();
        if (detected) {
            cfg.update('pythonPath', detected, vscode.ConfigurationTarget.Global);
        }
    }
    if (!cfg.get('scriptPath')) {
        const detected = detectScript(extensionUri);
        if (detected) {
            cfg.update('scriptPath', detected, vscode.ConfigurationTarget.Global);
        }
    }
    if (!cfg.get('libclangPath')) {
        const candidates = [
            String.raw `C:\msys64\ucrt64\bin\libclang.dll`,
            String.raw `C:\msys64\mingw64\bin\libclang.dll`,
            String.raw `C:\Program Files\LLVM\bin\libclang.dll`,
            String.raw `C:\Program Files (x86)\LLVM\bin\libclang.dll`,
        ];
        const found = candidates.find(p => fs.existsSync(p));
        if (found) {
            cfg.update('libclangPath', found, vscode.ConfigurationTarget.Global);
        }
    }
}
function detectPython() {
    if (process.platform === 'win32') {
        // Ask the py launcher for the actual interpreter path
        try {
            const r = cp.spawnSync('py', ['-c', 'import sys; print(sys.executable)'], { encoding: 'utf-8', timeout: 5000 });
            const p = r.stdout?.trim();
            if (r.status === 0 && p && fs.existsSync(p))
                return p;
        }
        catch { /* no py launcher */ }
        // Scan AppData\Local\Programs\Python for installed versions
        const username = process.env['USERNAME'] || '';
        const base = path.join('C:', 'Users', username, 'AppData', 'Local', 'Programs', 'Python');
        if (fs.existsSync(base)) {
            const versions = fs.readdirSync(base)
                .filter(d => d.startsWith('Python'))
                .sort()
                .reverse(); // newest first
            for (const ver of versions) {
                const exe = path.join(base, ver, 'python.exe');
                if (fs.existsSync(exe))
                    return exe;
            }
        }
        return null;
    }
    // macOS / Linux
    for (const cmd of ['python3', 'python']) {
        try {
            const r = cp.spawnSync(cmd, ['--version'], { encoding: 'utf-8', timeout: 3000 });
            if (r.status === 0) {
                const which = cp.spawnSync('which', [cmd], { encoding: 'utf-8' });
                const p = which.stdout?.trim();
                if (p && fs.existsSync(p))
                    return p;
                return cmd;
            }
        }
        catch { /* try next */ }
    }
    return null;
}
function detectScript(extensionUri) {
    // 1. Workspace root — works for any user who opens the GraphGuard project folder
    const wsRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (wsRoot) {
        const p = path.join(wsRoot, 'graphguard.py');
        if (fs.existsSync(p))
            return p;
    }
    // 2. Sibling of extension folder — works in dev / F5 mode
    const sibling = path.join(extensionUri.fsPath, '..', 'graphguard.py');
    if (fs.existsSync(sibling))
        return sibling;
    return null;
}
function deactivate() { }
// ── Path resolvers (runtime) ──────────────────────────────────────────────────
function resolvePython() {
    const custom = vscode.workspace.getConfiguration('graphguard').get('pythonPath');
    if (custom)
        return custom;
    return process.platform === 'win32' ? 'py' : 'python3';
}
function resolveScript(extensionUri) {
    const custom = vscode.workspace.getConfiguration('graphguard').get('scriptPath');
    if (custom)
        return fs.existsSync(custom) ? custom : null;
    // Workspace root (primary fallback — installed VSIX scenario)
    const wsRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (wsRoot) {
        const p = path.join(wsRoot, 'graphguard.py');
        if (fs.existsSync(p))
            return p;
    }
    // Sibling (dev mode)
    const sibling = path.join(extensionUri.fsPath, '..', 'graphguard.py');
    if (fs.existsSync(sibling))
        return sibling;
    return null;
}
// ── Provider ──────────────────────────────────────────────────────────────────
class GraphGuardViewProvider {
    constructor(_extensionUri) {
        this._extensionUri = _extensionUri;
        this._running = false;
    }
    resolveWebviewView(webviewView, _context, _token) {
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
    _startWatcher() {
        this._watcher = vscode.workspace.createFileSystemWatcher('**/*.{c,h}');
        const debounce = () => {
            if (this._debounce)
                clearTimeout(this._debounce);
            this._debounce = setTimeout(() => this._checkDiff(), 600);
        };
        this._watcher.onDidChange(debounce);
        this._watcher.onDidCreate(debounce);
        this._watcher.onDidDelete(debounce);
    }
    _checkDiff() {
        const root = workspaceRoot();
        if (!root)
            return;
        cp.exec('git diff HEAD --name-only', { cwd: root }, (_err, stdout) => {
            const files = stdout.trim()
                .split('\n')
                .filter(f => f.endsWith('.c') || f.endsWith('.h'))
                .map(f => path.basename(f));
            this._view?.webview.postMessage({ type: 'status', hasChanges: files.length > 0, files });
        });
    }
    _runAnalysis(model, approach) {
        if (this._running)
            return;
        const root = workspaceRoot();
        if (!root)
            return;
        const script = resolveScript(this._extensionUri);
        if (!script) {
            const configured = vscode.workspace.getConfiguration('graphguard').get('scriptPath');
            const detail = configured
                ? `scriptPath is set to "${configured}" but that file does not exist.`
                : 'graphguard.py could not be found automatically.';
            this._view?.webview.postMessage({
                type: 'error',
                message: `${detail}\n\nFix: open Settings (Ctrl+,), search "graphguard",\nset graphguard.scriptPath to the full path of graphguard.py.\n\nExample: C:\\Users\\you\\Desktop\\GraphGuard\\graphguard.py`,
            });
            return;
        }
        this._running = true;
        const python = resolvePython();
        const libclangPath = vscode.workspace.getConfiguration('graphguard').get('libclangPath') ||
            process.env['LIBCLANG_PATH'] || '';
        const proc = cp.spawn(python, [script, 'analyze', '--model', model, '--approach', approach], {
            cwd: root,
            env: {
                ...process.env,
                PYTHONIOENCODING: 'utf-8',
                PYTHONUTF8: '1',
                ...(libclangPath ? { LIBCLANG_PATH: libclangPath } : {}),
            },
        });
        proc.stdout.on('data', (data) => {
            for (const raw of data.toString().split('\n')) {
                const line = raw.replace(/\r$/, '');
                if (line.trim()) {
                    this._view?.webview.postMessage({ type: 'output', line });
                }
            }
        });
        proc.stderr.on('data', (data) => {
            const text = data.toString().replace(/\r\n/g, '\n').trim();
            if (text) {
                this._view?.webview.postMessage({ type: 'output', line: text });
            }
        });
        proc.on('close', (code) => {
            this._running = false;
            if (code !== 0) {
                this._view?.webview.postMessage({ type: 'output', line: `\n[Process exited with code ${code}]` });
            }
            this._checkDiff();
            this._view?.webview.postMessage({ type: 'done' });
        });
        proc.on('error', (err) => {
            this._running = false;
            this._view?.webview.postMessage({
                type: 'error',
                message: `Failed to start Python ("${python}"): ${err.message}\n\nFix: open Settings (Ctrl+,), search "graphguard",\nset graphguard.pythonPath to your Python executable.\n\nExample: C:\\Users\\ASUS_ZEPHYRUS\\AppData\\Local\\Programs\\Python\\Python312\\python.exe`,
            });
        });
    }
}
function workspaceRoot() {
    return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}
// ── Webview HTML ──────────────────────────────────────────────────────────────
function getWebviewHtml() {
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
  font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.08em;
  opacity: 0.7; margin-bottom: 10px;
}

.status {
  font-size: 12px; padding: 6px 8px; border-radius: 3px;
  margin-bottom: 12px; border-left: 3px solid transparent;
}
.status.idle  { background: var(--vscode-inputValidation-infoBackground,#1a3a4a); border-color:#007acc; }
.status.ready { background: var(--vscode-inputValidation-warningBackground,#352a05); border-color:#b89500; }

label { display:block; font-size:11px; opacity:0.7; margin:8px 0 3px; }

select {
  width:100%; padding:4px 6px;
  background:var(--vscode-input-background);
  color:var(--vscode-input-foreground);
  border:1px solid var(--vscode-input-border,#3c3c3c);
  border-radius:2px; font-size:12px; font-family:inherit;
}

.hint {
  font-size:10px; opacity:0.45; margin-top:3px; line-height:1.4;
}

#analyzeBtn {
  width:100%; margin-top:12px; padding:7px;
  background:var(--vscode-button-background);
  color:var(--vscode-button-foreground);
  border:none; border-radius:2px; font-size:12px;
  font-family:inherit; cursor:pointer; font-weight:500;
}
#analyzeBtn:hover:not(:disabled) { background:var(--vscode-button-hoverBackground); }
#analyzeBtn:disabled { opacity:0.4; cursor:not-allowed; }

#spinner {
  font-size:11px; opacity:0.6; margin-top:8px;
  display:none; text-align:center; line-height:1.6;
}

.toolbar {
  display:none; justify-content:flex-end; margin-top:10px;
}
.clear-btn {
  font-size:10px; opacity:0.45; cursor:pointer;
  background:none; border:none; color:inherit;
  text-decoration:underline;
}
.clear-btn:hover { opacity:1; }

/* ── Result card ── */
#result { margin-top:14px; display:none; font-size:12px; }

.section { margin-bottom:10px; }
.section-title {
  font-size:10px; font-weight:700; text-transform:uppercase;
  letter-spacing:0.07em; opacity:0.55; margin-bottom:5px;
  padding-bottom:3px; border-bottom:1px solid var(--vscode-panel-border,#3c3c3c);
}

.fn-item {
  padding:2px 0 2px 10px;
  font-family:var(--vscode-editor-font-family,monospace);
  font-size:11px; color:var(--vscode-symbolIcon-functionForeground,#dcdcaa);
}

.concerns {
  font-size:12px; line-height:1.5; opacity:0.9;
  padding:6px 8px; background:var(--vscode-editor-background);
  border-radius:3px; border-left:3px solid var(--vscode-panel-border,#3c3c3c);
}

.severity {
  display:inline-block; font-size:11px; font-weight:700;
  padding:1px 7px; border-radius:10px; margin-bottom:10px;
}
.sev-low      { background:#1e3a1e; color:#89d185; }
.sev-medium   { background:#3a2e05; color:#cca700; }
.sev-high     { background:#3a1a05; color:#f48771; }
.sev-critical { background:#3a0505; color:#ff6b6b; }
.sev-unknown  { background:#2a2a2a; color:#aaa; }

.show-more {
  font-size:10px; opacity:0.5; cursor:pointer;
  padding:2px 0 2px 10px; text-decoration:underline;
}
.show-more:hover { opacity:1; }
.hidden-items { display:none; }

.tool-summary {
  font-size:10px; opacity:0.4; padding:2px 0;
  font-family:var(--vscode-editor-font-family,monospace);
}

/* ── Streaming log ── */
#log {
  margin-top:12px;
  font-family:var(--vscode-editor-font-family,monospace);
  font-size:10px; opacity:0.6; white-space:pre-wrap;
  word-break:break-word; max-height:160px; overflow-y:auto;
  display:none; padding:6px;
  border-left:2px solid var(--vscode-panel-border,#3c3c3c);
  background:var(--vscode-editor-background);
  border-radius:0 3px 3px 0;
}

.error-box {
  margin-top:10px; padding:8px; font-size:11px;
  font-family:var(--vscode-editor-font-family,monospace);
  white-space:pre-wrap; word-break:break-word;
  background:var(--vscode-inputValidation-errorBackground,#3a0505);
  border-left:3px solid var(--vscode-errorForeground,#f48771);
  border-radius:2px; display:none;
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
<select id="approach" onchange="updateHint()">
  <option value="graph">Diff + Call Graph</option>
  <option value="agent" id="agentOption">Agent (iterative)</option>
  <option value="diff">Diff only</option>
</select>
<div class="hint" id="approachHint">One API call — fast results with full call graph context.</div>

<button id="analyzeBtn" disabled>Analyze Impact</button>
<div id="spinner">Running analysis...<br><span id="elapsed" style="font-size:10px;opacity:0.7"></span></div>

<div id="log"></div>
<div id="result"></div>
<div id="errorBox" class="error-box"></div>

<div class="toolbar" id="toolbar">
  <button class="clear-btn" id="clearBtn">Clear</button>
</div>

<script>
const vscode    = acquireVsCodeApi();
const btn       = document.getElementById('analyzeBtn');
const statusEl  = document.getElementById('status');
const spinner   = document.getElementById('spinner');
const elapsedEl = document.getElementById('elapsed');
const log       = document.getElementById('log');
const result    = document.getElementById('result');
const errorBox  = document.getElementById('errorBox');
const toolbar   = document.getElementById('toolbar');
const clearBtn  = document.getElementById('clearBtn');
let hasChanges  = false;
let rawLines    = [];
let timerInterval = null;
let startTime   = 0;

// ── Restore saved state when panel is re-shown ──────────────────────────────
(function restoreState() {
  const s = vscode.getState();
  if (s && s.html) {
    result.innerHTML = s.html;
    result.style.display = 'block';
    toolbar.style.display = 'flex';
    // Re-attach expand/collapse listeners
    attachExpandListeners();
  }
})();

// ── Approach hint ─────────────────────────────────────────────────────────────
const hints = {
  graph: 'One API call — fast results with full call graph context.',
  agent: 'Multiple tool calls — thorough but slower.',
  diff:  'Fastest — no call graph, LLM sees only the diff.',
};
function updateHint() {
  const approach = document.getElementById('approach');
  document.getElementById('approachHint').textContent = hints[approach.value] || '';
}

document.getElementById('model').addEventListener('change', updateHint);

// ── Analyze button ───────────────────────────────────────────────────────────
btn.addEventListener('click', () => {
  const model    = document.getElementById('model').value;
  const approach = document.getElementById('approach').value;
  rawLines = [];
  log.textContent = '';
  log.style.display = 'block';
  result.style.display = 'none';
  result.innerHTML = '';
  errorBox.style.display = 'none';
  toolbar.style.display = 'none';
  spinner.style.display = 'block';
  btn.disabled = true;
  vscode.setState(null);

  // Start elapsed timer
  startTime = Date.now();
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    const secs = Math.floor((Date.now() - startTime) / 1000);
    elapsedEl.textContent = secs + 's elapsed';
  }, 1000);

  vscode.postMessage({ type: 'analyze', model, approach });
});

clearBtn.addEventListener('click', () => {
  log.style.display = 'none';
  result.style.display = 'none';
  errorBox.style.display = 'none';
  toolbar.style.display = 'none';
  rawLines = [];
  vscode.setState(null);
});

// ── Message handler ───────────────────────────────────────────────────────────
window.addEventListener('message', event => {
  const msg = event.data;

  if (msg.type === 'status') {
    hasChanges = msg.hasChanges;
    if (msg.hasChanges) {
      const names = msg.files.slice(0, 3).join(', ') +
                    (msg.files.length > 3 ? \` +\${msg.files.length - 3} more\` : '');
      statusEl.textContent = 'Changes: ' + names;
      statusEl.className   = 'status ready';
      if (spinner.style.display === 'none' || !spinner.style.display) btn.disabled = false;
    } else {
      statusEl.textContent = 'No uncommitted changes in .c/.h files';
      statusEl.className   = 'status idle';
      btn.disabled = true;
    }
  }

  else if (msg.type === 'output') {
    rawLines.push(msg.line);
    // Show all output lines while running so user can see progress
    log.textContent += msg.line.trim() + '\\n';
    log.scrollTop = log.scrollHeight;
  }

  else if (msg.type === 'done') {
    if (timerInterval) { clearInterval(timerInterval); timerInterval = null; }
    spinner.style.display = 'none';
    log.style.display = 'none';
    btn.disabled = !hasChanges;
    renderResult(rawLines);
    toolbar.style.display = 'flex';
  }

  else if (msg.type === 'error') {
    if (timerInterval) { clearInterval(timerInterval); timerInterval = null; }
    spinner.style.display = 'none';
    log.style.display = 'none';
    btn.disabled = !hasChanges;
    errorBox.textContent = msg.message;
    errorBox.style.display = 'block';
    toolbar.style.display = 'flex';
  }
});

// ── Render result ─────────────────────────────────────────────────────────────

const SECTION_HEADERS = [
  'FUNCTIONS DIRECTLY MODIFIED',
  'WHAT WILL BE AFFECTED',
  'BUGS / RISKS INTRODUCED',
  'SUMMARY',
  'TOOLS CALLED BY AGENT',
];

function renderResult(lines) {
  const text = lines.join('\\n');

  const severityRaw = extract(text, /Severity\\s*:\\s*(\\S+)/i);
  const severity = severityRaw ? severityRaw.replace(/[\\[\\]]/g, '') : null;
  const modelVal = extract(text, /Model\\s*:\\s*(.+)/i);
  const appVal   = extract(text, /Approach\\s*:\\s*(.+)/i);
  const summary  = extractBlock(lines, 'SUMMARY');
  const changed  = extractList(lines, 'FUNCTIONS DIRECTLY MODIFIED');
  const affected = extractList(lines, 'WHAT WILL BE AFFECTED');
  const bugs     = extractBlock(lines, 'BUGS / RISKS INTRODUCED');
  const toolsCnt = countTools(lines);

  if (!severity && !summary && changed.length === 0) {
    result.innerHTML =
      '<div class="section"><div class="section-title">Output</div>' +
      '<pre style="font-size:11px;white-space:pre-wrap;word-break:break-word;opacity:.8">' +
      esc(text) + '</pre></div>';
    result.style.display = 'block';
    vscode.setState({ html: result.innerHTML });
    return;
  }

  let html = '';

  if (severity) {
    const cls = 'sev-' + severity.toLowerCase();
    html += \`<span class="severity \${cls}">\${esc(severity.toUpperCase())}</span>\`;
  }
  if (modelVal || appVal) {
    html += \`<div style="font-size:10px;opacity:.45;margin-bottom:10px">\${esc((modelVal||'').trim())}\${appVal ? ' — ' + esc(appVal.trim()) : ''}</div>\`;
  }

  if (changed.length) {
    html += section('Functions Modified', fnList(changed));
  }

  if (affected.length) {
    html += section('What Will Be Affected', fnListCollapsible(affected));
  }

  if (bugs) {
    html += section('Bugs / Risks', \`<div class="concerns">\${esc(bugs)}</div>\`);
  }

  if (summary) {
    html += section('Summary', \`<div class="concerns">\${esc(summary)}</div>\`);
  }

  if (toolsCnt > 0) {
    html += \`<div class="tool-summary">\${toolsCnt} agent tool call\${toolsCnt !== 1 ? 's' : ''} made</div>\`;
  }

  result.innerHTML = html;
  result.style.display = 'block';
  vscode.setState({ html: result.innerHTML });
  attachExpandListeners();
}

function fnList(items) {
  return items.map(f => \`<div class="fn-item">\${esc(f)}</div>\`).join('');
}

function fnListCollapsible(items) {
  const LIMIT = 5;
  if (items.length <= LIMIT) return fnList(items);
  const visible = items.slice(0, LIMIT);
  const hidden  = items.slice(LIMIT);
  return fnList(visible) +
    \`<div class="hidden-items" id="hiddenFns">\${fnList(hidden)}</div>\` +
    \`<div class="show-more" id="showMoreBtn">+ \${hidden.length} more</div>\`;
}

function attachExpandListeners() {
  const btn = document.getElementById('showMoreBtn');
  const box = document.getElementById('hiddenFns');
  if (btn && box) {
    btn.addEventListener('click', () => {
      box.style.display = 'block';
      btn.style.display = 'none';
    });
  }
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

// Extracts list items under the FIRST occurrence of a section header.
// The line immediately after the header is often a decorator (----), so we
// skip the first separator and only stop on a second one or another header.
function extractList(lines, header) {
  let capture = false;
  let skippedSep = false;
  const items = [];
  for (const line of lines) {
    if (!capture && line.includes(header)) { capture = true; continue; }
    if (!capture) continue;
    if (line.match(/^\\s*[=\\-]{4,}/)) {
      if (!skippedSep) { skippedSep = true; continue; }  // skip decorative separator
      break;
    }
    if (SECTION_HEADERS.some(h => h !== header && line.includes(h))) break;
    const t = line.replace(/^\\s*[-!\\d.]+\\s*/, '').trim();
    if (t) items.push(t);
  }
  return [...new Set(items)];
}

function extractBlock(lines, header) {
  let capture = false;
  let skippedSep = false;
  const out = [];
  for (const line of lines) {
    if (!capture && line.includes(header)) { capture = true; continue; }
    if (!capture) continue;
    if (line.match(/^\\s*[=\\-]{4,}/)) {
      if (!skippedSep) { skippedSep = true; continue; }
      break;
    }
    if (SECTION_HEADERS.some(h => h !== header && line.includes(h))) break;
    const t = line.trim();
    if (t) out.push(t);
  }
  return out.join(' ').trim() || null;
}

function countTools(lines) {
  let capture = false;
  let skippedSep = false;
  let count = 0;
  for (const line of lines) {
    if (!capture && line.includes('TOOLS CALLED BY AGENT')) { capture = true; continue; }
    if (!capture) continue;
    if (line.match(/^\\s*[=\\-]{4,}/)) {
      if (!skippedSep) { skippedSep = true; continue; }
      break;
    }
    if (SECTION_HEADERS.some(h => h !== 'TOOLS CALLED BY AGENT' && line.includes(h))) break;
    const t = line.replace(/^\\s*[-!\\d.]+\\s*/, '').trim();
    if (t) count++;
  }
  return count;
}
</script>
</body>
</html>`;
}
//# sourceMappingURL=extension.js.map