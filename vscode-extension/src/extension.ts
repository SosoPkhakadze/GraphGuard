import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

export function activate(context: vscode.ExtensionContext) {
    const provider = new GraphGuardViewProvider(context.extensionUri);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('graphguard.sidebar', provider)
    );
}

export function deactivate() {}

// ── Paths ─────────────────────────────────────────────────────────────────────

function resolvePython(): string {
    const cfg = vscode.workspace.getConfiguration('graphguard');
    return cfg.get<string>('pythonPath') || 'python';
}

function resolveScript(extensionUri: vscode.Uri): string {
    const cfg = vscode.workspace.getConfiguration('graphguard');
    const custom = cfg.get<string>('scriptPath');
    if (custom && fs.existsSync(custom)) return custom;

    // Extension lives inside the repo at vscode-extension/, so graphguard.py is one level up
    const sibling = path.join(extensionUri.fsPath, '..', 'graphguard.py');
    if (fs.existsSync(sibling)) return sibling;

    return 'graphguard.py';
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

        this._running = true;
        const python = resolvePython();
        const script = resolveScript(this._extensionUri);

        const proc = cp.spawn(python, [script, 'analyze', '--model', model, '--approach', approach], {
            cwd: root,
        });

        proc.stdout.on('data', (data: Buffer) => {
            for (const line of data.toString().split('\n')) {
                if (line.trim()) {
                    this._view?.webview.postMessage({ type: 'output', line });
                }
            }
        });

        proc.stderr.on('data', (data: Buffer) => {
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

        proc.on('error', (err: Error) => {
            this._running = false;
            this._view?.webview.postMessage({
                type: 'error',
                message: `Failed to start process: ${err.message}\n\nCheck graphguard.pythonPath in settings.`,
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
