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
    const provider = new GraphGuardViewProvider(context.extensionUri);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider('graphguard.sidebar', provider));
}
function deactivate() { }
// ── Paths ─────────────────────────────────────────────────────────────────────
function resolvePython() {
    const cfg = vscode.workspace.getConfiguration('graphguard');
    const custom = cfg.get('pythonPath');
    if (custom)
        return custom;
    // On Windows 'python' is often absent; 'py' (launcher) is the reliable default
    return process.platform === 'win32' ? 'py' : 'python3';
}
function resolveScript(extensionUri) {
    const cfg = vscode.workspace.getConfiguration('graphguard');
    const custom = cfg.get('scriptPath');
    if (custom) {
        if (fs.existsSync(custom))
            return custom;
        return null; // explicitly set but wrong — report the bad path
    }
    // When running from the repo (F5 dev mode), extensionUri is vscode-extension/
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
    // ── File watcher ─────────────────────────────────────────────────────────
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
    // ── Git diff check ────────────────────────────────────────────────────────
    _checkDiff() {
        const root = workspaceRoot();
        if (!root)
            return;
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
                message: `${detail}\n\nFix: open VS Code Settings (Ctrl+,), search "graphguard",\nand set graphguard.scriptPath to the full path of graphguard.py.\n\nExample: C:\\Users\\you\\Desktop\\GraphGuard\\graphguard.py`,
            });
            return;
        }
        this._running = true;
        const python = resolvePython();
        const proc = cp.spawn(python, [script, 'analyze', '--model', model, '--approach', approach], {
            cwd: root,
        });
        proc.stdout.on('data', (data) => {
            for (const line of data.toString().split('\n')) {
                if (line.trim()) {
                    this._view?.webview.postMessage({ type: 'output', line });
                }
            }
        });
        proc.stderr.on('data', (data) => {
            const text = data.toString().trim();
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
        proc.on('error', (err) => {
            this._running = false;
            this._view?.webview.postMessage({
                type: 'error',
                message: `Failed to start Python ("${python}"): ${err.message}\n\nFix: open VS Code Settings (Ctrl+,), search "graphguard",\nand set graphguard.pythonPath to your Python executable.\n\nExample: C:\\Users\\ASUS_ZEPHYRUS\\AppData\\Local\\Programs\\Python\\Python312\\python.exe`,
            });
        });
    }
}
// ── Helpers ───────────────────────────────────────────────────────────────────
function workspaceRoot() {
    return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}
// ── Webview HTML ──────────────────────────────────────────────────────────────
function getWebviewHtml() {
    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
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
    color: var(--vscode-sideBarSectionHeader-foreground);
    margin-bottom: 10px;
    opacity: 0.8;
  }

  .status {
    font-size: 12px;
    padding: 6px 8px;
    border-radius: 3px;
    margin-bottom: 12px;
    border-left: 3px solid transparent;
  }

  .status.idle {
    background: var(--vscode-inputValidation-infoBackground, #1a3a4a);
    border-color: var(--vscode-inputValidation-infoBorder, #007acc);
    color: var(--vscode-inputValidation-infoForeground, #cce7ff);
  }

  .status.ready {
    background: var(--vscode-inputValidation-warningBackground, #352a05);
    border-color: var(--vscode-inputValidation-warningBorder, #b89500);
    color: var(--vscode-foreground);
  }

  label {
    display: block;
    font-size: 11px;
    opacity: 0.75;
    margin-bottom: 3px;
    margin-top: 8px;
  }

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

  #analyzeBtn:hover:not(:disabled) {
    background: var(--vscode-button-hoverBackground);
  }

  #analyzeBtn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  #spinner {
    font-size: 11px;
    opacity: 0.65;
    margin-top: 8px;
    display: none;
    text-align: center;
  }

  #output {
    margin-top: 12px;
    font-family: var(--vscode-editor-font-family, monospace);
    font-size: 11px;
    white-space: pre-wrap;
    word-break: break-word;
    background: var(--vscode-editor-background);
    border: 1px solid var(--vscode-panel-border, #3c3c3c);
    padding: 8px;
    border-radius: 2px;
    max-height: 450px;
    overflow-y: auto;
    display: none;
  }

  .clear-btn {
    font-size: 10px;
    opacity: 0.6;
    cursor: pointer;
    float: right;
    margin-top: 12px;
    background: none;
    border: none;
    color: inherit;
    text-decoration: underline;
    display: none;
  }

  .clear-btn:hover { opacity: 1; }
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

<button class="clear-btn" id="clearBtn">clear output</button>
<div id="output"></div>

<script>
  const vscode = acquireVsCodeApi();
  const btn     = document.getElementById('analyzeBtn');
  const output  = document.getElementById('output');
  const status  = document.getElementById('status');
  const spinner = document.getElementById('spinner');
  const clearBtn = document.getElementById('clearBtn');
  let hasChanges = false;

  btn.addEventListener('click', () => {
    const model    = document.getElementById('model').value;
    const approach = document.getElementById('approach').value;
    output.style.display = 'block';
    output.textContent   = '';
    clearBtn.style.display = 'none';
    spinner.style.display  = 'block';
    btn.disabled = true;
    vscode.postMessage({ type: 'analyze', model, approach });
  });

  clearBtn.addEventListener('click', () => {
    output.textContent = '';
    output.style.display = 'none';
    clearBtn.style.display = 'none';
  });

  window.addEventListener('message', event => {
    const msg = event.data;

    if (msg.type === 'status') {
      hasChanges = msg.hasChanges;
      if (msg.hasChanges) {
        const fileList = msg.files.slice(0, 3).join(', ') +
                         (msg.files.length > 3 ? \` +\${msg.files.length - 3} more\` : '');
        status.textContent  = 'Changes detected: ' + fileList;
        status.className    = 'status ready';
        btn.disabled        = false;
      } else {
        status.textContent = 'No uncommitted changes in .c/.h files';
        status.className   = 'status idle';
        btn.disabled       = true;
      }
    }

    else if (msg.type === 'output') {
      output.textContent += msg.line + '\\n';
      output.scrollTop    = output.scrollHeight;
    }

    else if (msg.type === 'done') {
      spinner.style.display  = 'none';
      btn.disabled           = !hasChanges;
      clearBtn.style.display = 'inline';
    }

    else if (msg.type === 'error') {
      spinner.style.display = 'none';
      output.style.display  = 'block';
      output.textContent   += '\\nERROR: ' + msg.message;
      btn.disabled          = !hasChanges;
      clearBtn.style.display = 'inline';
    }
  });
</script>

</body>
</html>`;
}
//# sourceMappingURL=extension.js.map