================================================================================
  GraphGuard -- Thesis Results & Reports Index
================================================================================

WHAT IS GraphGuard?
-------------------
GraphGuard evaluates whether adding call-graph context to an AI code review
prompt improves impact analysis accuracy for C code changes.

Two "friends" review each diff:
  Friend 1  -- sees only the unified diff (diff.txt)
  Friend 2  -- sees the diff + full call graph (diff_with_callgraph.txt)

Two AI models were tested across 50 projects (5 batches x 10 projects):
  - GPT-4o              (OpenAI)
  - Claude Sonnet 4.6   (Anthropic)

Metrics per project: TP / TN / FP / FN / Precision / Recall / F1 / Accuracy


================================================================================
  QUICK RESULTS SUMMARY
================================================================================

  GPT-4o:
    Friend 1  (diff only)      avg F1 = 0.518
    Friend 2  (diff + graph)   avg F1 = 0.982   (+0.464 improvement)

  Claude Sonnet 4.6:
    Friend 1  (diff only)      avg F1 = 0.567
    Friend 2  (diff + graph)   avg F1 = 0.993   (+0.426 improvement)

  Head-to-head on Friend 2 (per project, 50 total):
    GPT wins   :  0 / 50  (0.0%)
    Claude wins:  2 / 50  (4.0%)
    Ties       : 48 / 50  (96.0%)
    Overall winner: Claude  (0.993 vs 0.982, delta = +0.011)

  KEY FINDING: Both models reach ~F1=0.98-0.99 with call-graph context
  versus ~F1=0.52-0.57 without. The call graph explains nearly all of the
  ~0.45 improvement regardless of which model is used.


================================================================================
  REPORT FILES
================================================================================

  reports/gpt_vs_claude.txt          Full GPT vs Claude comparison
                                     (50 projects, per-batch averages, overall)

  reports/all_batches_summary.txt    Cross-batch GPT-4o summary
                                     (per-project F1 table + overall totals)

  batches/batch_01/                  10 hand-crafted C projects (batch 1)
    batch_results.txt                GPT-4o batch summary
    batch_results_claude.txt         Claude batch summary
    <project>/evaluation.txt         GPT-4o per-project result
    <project>/evaluation_claude.txt  Claude per-project result
    <project>/diff.txt               The code change (unified diff)
    <project>/diff_with_callgraph.txt  Diff + call graph (Friend 2 input)
    <project>/ground_truth.json      Hand-labeled correct answer
    <project>/src/*.c                C source files

  batches/batch_02/ ... batch_05/    40 auto-generated projects (10 each)
    (same structure as batch_01)


================================================================================
  HOW TO USE THE CLI
================================================================================

  REAL-WORLD MODE (analyze your own C project changes)
  ─────────────────────────────────────────────────────
  Run from inside any git-tracked C project. GraphGuard reads git diff
  automatically -- no arguments needed.

    cd /your/c/project
    python /path/to/graphguard.py analyze             # all uncommitted changes
    python /path/to/graphguard.py analyze --staged    # only staged changes
    python /path/to/graphguard.py analyze --unpushed  # committed, not yet pushed
    python /path/to/graphguard.py analyze --model claude

  NOTE: The project files must be tracked by git for auto-detection to work.
  If analyzing a new project before the first commit, stage the files first:
    git add src/*.c
    python graphguard.py analyze --staged

  THESIS DEMO MODE (use existing diff files)
  ──────────────────────────────────────────
  Use the --diff flag to point at one of the pre-built diff files:

    cd batches/batch_01/07_stack
    python graphguard.py analyze --diff diff.txt --model gpt
    python graphguard.py analyze --diff diff.txt --model claude

  BATCH MODE (re-run the full evaluation)
  ─────────────────────────────────────────
    python graphguard.py batch ./batches/batch_01 --model gpt
    python graphguard.py batch ./batches/batch_02 --model claude

  REGENERATE REPORTS
  ──────────────────
    python graphguard.py summary    # -> reports/all_batches_summary.txt
    python graphguard.py compare    # -> reports/gpt_vs_claude.txt

  API KEY MANAGEMENT
  ──────────────────
    python graphguard.py config                         # show current keys
    python graphguard.py config --gpt-key sk-proj-...
    python graphguard.py config --claude-key sk-ant-...


================================================================================
  PROJECT STRUCTURE
================================================================================

  GraphGuard/
  ├── graphguard.py             Main CLI tool (single entry point)
  ├── graphguard_config.json    API keys (gitignored)
  ├── analyzer/                 Core analysis engine
  │   ├── callgraph.py          libclang-based call graph builder
  │   ├── context_builder.py    Builds Friend 1 / Friend 2 prompts
  │   ├── diff_parser.py        Parses unified diffs to file->line maps
  │   └── impact.py             Maps changed lines to changed functions
  ├── batches/
  │   ├── batch_01/             10 hand-crafted projects
  │   ├── batch_02/             10 auto-generated projects
  │   ├── batch_03/             10 auto-generated projects
  │   ├── batch_04/             10 auto-generated projects
  │   └── batch_05/             10 auto-generated projects
  ├── reports/
  │   ├── README.txt            This file
  │   ├── all_batches_summary.txt
  │   └── gpt_vs_claude.txt
  └── scripts/                  Original scripts (kept for reference)
      ├── run_batch.py          Original GPT-4o batch runner
      ├── run_batch_claude.py   Original Claude batch runner
      ├── gen_batches.py        Generated all 40 projects in batches 02-05
      ├── summarize_all.py      Original cross-batch summary
      └── compare_models.py     Original GPT vs Claude comparison
