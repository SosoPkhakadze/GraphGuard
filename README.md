# GraphGuard

AI-powered C code impact analyzer. Given uncommitted git changes, GraphGuard identifies which functions were modified and traces the full upstream impact through the call graph.

Three analysis modes:

| Mode | What the AI sees | Best for |
|------|-----------------|----------|
| **Friend 1 — Diff only** | The changed code | Quick check |
| **Friend 2 — Diff + Call Graph** | Changed code + full caller tree | Cross-file impact |
| **Friend 3 — Agent** | Retrieves context iteratively via tool calls | Contract violations, function pointers, #ifdefs |

---

## Requirements

- Python 3.11+
- LLVM/Clang (for call graph analysis)
- An OpenAI or Anthropic API key

---

## Installation

```bash
pip install -r requirements.txt
```

### Install LLVM

**Windows** — download from https://releases.llvm.org/ and install to `C:\Program Files\LLVM`

**Ubuntu/Debian**
```bash
sudo apt install libclang-dev
```

**macOS**
```bash
brew install llvm
```

---

## Setup

Set your API keys (stored locally in `graphguard_config.json`):

```bash
graphguard config --gpt-key sk-proj-...
graphguard config --claude-key sk-ant-...
```

Or use environment variables:

```bash
set OPENAI_API_KEY=sk-proj-...        # Windows
set ANTHROPIC_API_KEY=sk-ant-...

export OPENAI_API_KEY=sk-proj-...     # Linux/macOS
export ANTHROPIC_API_KEY=sk-ant-...
```

---

## Usage

### Analyze uncommitted changes

Run from inside any C project directory:

```bash
graphguard analyze
```

GraphGuard detects all uncommitted changes via `git diff HEAD`, builds the call graph for the affected project, then asks which model and approach to use.

Options:

```
--staged      Only analyze staged changes (git add)
--unpushed    Analyze committed but not yet pushed changes
--save        Save result to graphguard_analysis.txt
--model       Skip model menu (gpt, claude, claude-opus, claude-haiku)
--approach    Skip approach menu (diff, graph, agent)
```

Non-interactive example (useful for scripts):

```bash
graphguard analyze --model claude --approach agent
```

### Batch evaluation (thesis mode)

Evaluates Friend 1 vs Friend 2 across a directory of projects with ground truth JSON:

```bash
graphguard batch ./batches/batch_01 --model gpt
graphguard batch ./batches/batch_02 --model claude
```

### View results

```bash
graphguard summary    # cross-batch F1 score table
graphguard compare    # GPT-4o vs Claude comparison
```

---

## Windows PATH setup

To use `graphguard` from any directory, add the `GraphGuard/` folder to your PATH:

```powershell
setx PATH "$env:PATH;C:\path\to\GraphGuard"
```

Then open a new terminal — `graphguard analyze` will work from any C project.

---

## Demo

A ready-made banking system demo is in `demo/`. Follow `demo/DEMO_SCRIPT.txt` for step-by-step instructions that show the concrete difference between all three analysis modes.

---

## Project structure

```
graphguard.py          CLI entry point
graphguard.bat         Windows PATH launcher

analyzer/
  callgraph.py         libclang call graph builder (with caching)
  diff_parser.py       Git diff parser
  impact.py            Maps changed lines to function names
  context_builder.py   Builds prompts from diff + call graph
  agent_tools.py       Tool executor functions (find_callers, search_code, ...)
  agent.py             Anthropic tool-use agent loop

batches/               Thesis evaluation projects (batch_01 through batch_05)
demo/                  Standalone demo project for presentations
reports/               Generated evaluation output
```

---

## How the call graph cache works

On the first run inside a project, GraphGuard parses all `.c` files with libclang and saves the result to `.graphguard_cache.json` in the project root. On subsequent runs, it checks whether any source file has changed (by comparing modification times). If nothing changed, the cached graph is loaded instantly. If any file changed, the graph is rebuilt and the cache is updated.

The cache file is project-local and gitignored.
