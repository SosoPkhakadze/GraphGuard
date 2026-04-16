#!/usr/bin/env python3
"""
GraphGuard CLI — AI-powered C code impact analyzer

Usage examples:
  python graphguard.py analyze                        # auto-detect git changes here
  python graphguard.py analyze --model claude         # use Claude instead of GPT
  python graphguard.py analyze --staged               # only staged changes
  python graphguard.py analyze --unpushed             # committed but not yet pushed
  python graphguard.py batch ./batches/batch_01 --model gpt
  python graphguard.py batch ./batches/batch_02 --model claude
  python graphguard.py summary
  python graphguard.py compare
  python graphguard.py config --gpt-key sk-proj-... --claude-key sk-ant-...
"""

import os
import sys
import json
import glob
import subprocess
import argparse

# ── Package path so IDE resolves imports ─────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from analyzer.callgraph       import CallGraph
from analyzer.diff_parser     import parse as parse_diff
from analyzer.impact          import ImpactAnalyzer
from analyzer.context_builder import build_diff_with_graph, build_diff_only

# ── Constants ─────────────────────────────────────────────────────────────────
CONFIG_FILE = os.path.join(ROOT, "graphguard_config.json")

BATCHES = [
    ("batch_01", os.path.join(ROOT, "batches", "batch_01")),
    ("batch_02", os.path.join(ROOT, "batches", "batch_02")),
    ("batch_03", os.path.join(ROOT, "batches", "batch_03")),
    ("batch_04", os.path.join(ROOT, "batches", "batch_04")),
    ("batch_05", os.path.join(ROOT, "batches", "batch_05")),
]

MODEL_ALIASES = {
    "gpt":                       "gpt-4o",
    "gpt4":                      "gpt-4o",
    "gpt-4o":                    "gpt-4o",
    "gpt-mini":                  "gpt-4o-mini",
    "gpt-4o-mini":               "gpt-4o-mini",
    "claude":                    "claude-sonnet-4-6",
    "claude-sonnet":             "claude-sonnet-4-6",
    "claude-sonnet-4-6":         "claude-sonnet-4-6",
    "claude-opus":               "claude-opus-4-7",
    "claude-opus-4-7":           "claude-opus-4-7",
    "claude-haiku":              "claude-haiku-4-5-20251001",
    "claude-haiku-4-5":          "claude-haiku-4-5-20251001",
    "claude-haiku-4-5-20251001": "claude-haiku-4-5-20251001",
}

OPENAI_MODELS    = {"gpt-4o", "gpt-4o-mini"}
ANTHROPIC_MODELS = {"claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5-20251001"}

PROMPT = """\
You are reviewing a C code change to identify impact.
Respond ONLY with valid JSON — no markdown fences, no explanation:
{{"changed_functions": ["directly modified functions"], "affected_functions": ["functions that call or depend on changed functions"], "concerns": "one sentence"}}

{content}"""


# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    print(f"Config saved to {os.path.relpath(CONFIG_FILE)}")


def resolve_model(alias: str) -> str:
    m = MODEL_ALIASES.get(alias.lower())
    if m is None:
        choices = ", ".join(sorted(set(MODEL_ALIASES.values())))
        sys.exit(f"ERROR: Unknown model '{alias}'.\nSupported: {choices}")
    return m


def get_api_client(model: str, cfg: dict, args):
    if model in OPENAI_MODELS:
        key = (getattr(args, "api_key", None)
               or os.environ.get("OPENAI_API_KEY")
               or cfg.get("openai_key"))
        if not key:
            sys.exit("ERROR: OpenAI API key required.\n"
                     "  Set via: python graphguard.py config --gpt-key sk-proj-...\n"
                     "  Or env:  OPENAI_API_KEY=...")
        from openai import OpenAI
        return OpenAI(api_key=key), "openai"

    if model in ANTHROPIC_MODELS:
        key = (getattr(args, "api_key", None)
               or os.environ.get("ANTHROPIC_API_KEY")
               or cfg.get("anthropic_key"))
        if not key:
            sys.exit("ERROR: Anthropic API key required.\n"
                     "  Set via: python graphguard.py config --claude-key sk-ant-...\n"
                     "  Or env:  ANTHROPIC_API_KEY=...")
        import anthropic
        return anthropic.Anthropic(api_key=key), "anthropic"

    sys.exit(f"ERROR: Unrecognized model '{model}'")


# ── AI query ──────────────────────────────────────────────────────────────────

def query_model(content: str, client, provider: str, model: str) -> dict:
    if provider == "openai":
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": PROMPT.format(content=content)}],
            temperature=0,
        )
        text = resp.choices[0].message.content.strip()
    else:
        msg = client.messages.create(
            model=model,
            max_tokens=512,
            messages=[{"role": "user", "content": PROMPT.format(content=content)}],
        )
        text = msg.content[0].text.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    return json.loads(text)


# ── Metrics ───────────────────────────────────────────────────────────────────

def compute_metrics(predicted: set, ground_pos: set, all_fns: set) -> dict:
    tp = predicted & ground_pos
    fp = predicted - ground_pos
    fn = ground_pos - predicted
    tn = (all_fns - ground_pos) - predicted
    n_tp, n_fp, n_fn, n_tn = len(tp), len(fp), len(fn), len(tn)
    prec = n_tp / (n_tp + n_fp) if (n_tp + n_fp) > 0 else 0.0
    rec  = n_tp / (n_tp + n_fn) if (n_tp + n_fn) > 0 else 0.0
    f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    acc  = (n_tp + n_tn) / len(all_fns) if all_fns else 0.0
    return {
        "TP": n_tp, "TN": n_tn, "FP": n_fp, "FN": n_fn,
        "Precision": round(prec, 3), "Recall": round(rec, 3),
        "F1": round(f1, 3), "Accuracy": round(acc, 3),
        "TP_fns": sorted(tp), "FP_fns": sorted(fp), "FN_fns": sorted(fn),
    }


def metrics_line(m: dict) -> str:
    return (f"  TP={m['TP']}  TN={m['TN']}  FP={m['FP']}  FN={m['FN']}  "
            f"Prec={m['Precision']:.3f}  Rec={m['Recall']:.3f}  "
            f"F1={m['F1']:.3f}  Acc={m['Accuracy']:.3f}")


# ── Git helpers ───────────────────────────────────────────────────────────────

def git_run(*args, cwd=None) -> str:
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True,
        cwd=cwd or os.getcwd(),
    )
    return result.stdout


def get_git_root(cwd=None) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
        cwd=cwd or os.getcwd(),
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def get_diff_text(mode: str, cwd=None) -> str:
    """
    mode:
      'all'      — all uncommitted changes (staged + unstaged)  [default]
      'staged'   — only staged changes
      'unstaged' — only unstaged changes
      'unpushed' — committed but not yet pushed to upstream
    """
    if mode == "staged":
        return git_run("diff", "--cached", cwd=cwd)
    if mode == "unstaged":
        return git_run("diff", cwd=cwd)
    if mode == "unpushed":
        # Check if upstream exists
        upstream = git_run("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", cwd=cwd).strip()
        if not upstream or upstream.startswith("fatal"):
            print("No upstream branch configured — checking last commit instead.")
            return git_run("diff", "HEAD~1..HEAD", cwd=cwd)
        return git_run("diff", f"{upstream}..HEAD", cwd=cwd)
    # default: all uncommitted
    return git_run("diff", "HEAD", cwd=cwd)


def extract_changed_c_files(diff_text: str, git_root: str) -> list[str]:
    """Return absolute paths of .c files mentioned in the diff."""
    files = []
    for line in diff_text.splitlines():
        if line.startswith("+++ b/") and line.endswith(".c"):
            rel = line[len("+++ b/"):]
            files.append(os.path.normpath(os.path.join(git_root, rel)))
    return files


def find_project_c_files(changed_files: list[str]) -> list[str]:
    """
    Given a list of changed .c files, locate the "project root" for each
    (go up one level if the file lives in src/, source/, or lib/) then
    collect all .c files in that subtree.
    """
    search_roots: set[str] = set()
    for f in changed_files:
        d = os.path.dirname(os.path.abspath(f))
        if os.path.basename(d).lower() in ("src", "source", "lib", "libs"):
            d = os.path.dirname(d)
        search_roots.add(d)

    all_c: list[str] = []
    for root in search_roots:
        all_c.extend(glob.glob(os.path.join(root, "**", "*.c"), recursive=True))
    return list(set(all_c))


# ── Subcommand: analyze (git-aware) ──────────────────────────────────────────

def cmd_analyze(args, cfg):
    cwd = os.getcwd()

    # Resolve diff source
    if hasattr(args, "diff_file") and args.diff_file:
        with open(args.diff_file, encoding="utf-8") as f:
            diff_text = f.read()
        git_root = cwd
        changed_c = extract_changed_c_files(diff_text, git_root)
        if not changed_c and hasattr(args, "src_dir") and args.src_dir:
            changed_c = glob.glob(os.path.join(args.src_dir, "*.c"))
    else:
        git_root = get_git_root(cwd)
        if not git_root:
            sys.exit("ERROR: Not inside a git repository.\n"
                     "  Run this from inside a git project, or use --diff <file>.")

        mode = "all"
        if getattr(args, "staged", False):   mode = "staged"
        if getattr(args, "unpushed", False): mode = "unpushed"

        diff_text = get_diff_text(mode, cwd=cwd)
        if not diff_text.strip():
            mode_label = {"all": "uncommitted", "staged": "staged",
                          "unpushed": "unpushed"}[mode]
            print(f"No {mode_label} changes detected in this git repository.")
            print("Tip: make a change to a .c file, or use --staged / --unpushed.")
            return

        changed_c = extract_changed_c_files(diff_text, git_root)

    if not changed_c:
        print("No .c files found in the diff.")
        print("  - If your project files are not yet committed, stage them first:")
        print("      git add <files>  then  python graphguard.py analyze --staged")
        print("  - Or point at an existing diff.txt:")
        print("      python graphguard.py analyze --diff ./diff.txt")
        print("  - GraphGuard currently analyzes C (.c) projects only.")
        return

    # Find all .c files in the same project subtree
    all_c_files = find_project_c_files(changed_c)
    if not all_c_files:
        print("Could not locate .c source files near the changed files.")
        return

    print(f"\nChanged file(s) : {[os.path.relpath(f, cwd) for f in changed_c]}")
    print(f"Call graph scope: {len(all_c_files)} .c file(s) in project subtree")

    # Build call graph
    print("Building call graph...")
    cg = CallGraph()
    cg.build(all_c_files)

    file_to_lines = parse_diff(diff_text, repo_root=git_root)
    changed_fns   = ImpactAnalyzer(cg).find_changed_functions(file_to_lines)

    print(f"Changed function(s): {sorted(changed_fns) if changed_fns else '(none detected)'}")

    cg_content = build_diff_with_graph(diff_text, cg, changed_fns)

    # Query AI
    model = resolve_model(args.model)
    client, provider = get_api_client(model, cfg, args)
    model_label = model

    print(f"Querying {model_label} (Friend 1 — diff only)...")
    r1 = query_model(build_diff_only(diff_text), client, provider, model)

    print(f"Querying {model_label} (Friend 2 — diff + call graph)...")
    r2 = query_model(cg_content, client, provider, model)

    # Pretty output
    div  = "=" * 72
    div2 = "-" * 72
    f1_affected = set(r1.get("affected_functions", []))
    f2_affected = set(r2.get("affected_functions", []))
    graph_added = sorted(f2_affected - f1_affected)

    print(f"\n{div}")
    print("  GraphGuard Impact Analysis")
    print(f"  Model: {model_label}")
    print(div)

    print("\n  FRIEND 1  (diff only — no call graph context)")
    print(div2)
    print(f"  Changed  : {sorted(r1.get('changed_functions', []))}")
    print(f"  Affected : {sorted(r1.get('affected_functions', []))}")
    print(f"  Concerns : {r1.get('concerns', '')}")

    print("\n  FRIEND 2  (diff + call graph context)")
    print(div2)
    print(f"  Changed  : {sorted(r2.get('changed_functions', []))}")
    print(f"  Affected : {sorted(r2.get('affected_functions', []))}")
    print(f"  Concerns : {r2.get('concerns', '')}")

    print(f"\n  Call graph revealed {len(graph_added)} additional function(s): "
          f"{graph_added if graph_added else '(none — same result)'}")
    print(div)

    # Optionally save
    if getattr(args, "save", False):
        out = os.path.join(cwd, "graphguard_analysis.txt")
        lines = [
            div, "GraphGuard Impact Analysis", f"Model: {model_label}", div,
            "", "FRIEND 1  (diff only)", div2,
            f"Changed  : {sorted(r1.get('changed_functions', []))}",
            f"Affected : {sorted(r1.get('affected_functions', []))}",
            f"Concerns : {r1.get('concerns', '')}",
            "", "FRIEND 2  (diff + call graph)", div2,
            f"Changed  : {sorted(r2.get('changed_functions', []))}",
            f"Affected : {sorted(r2.get('affected_functions', []))}",
            f"Concerns : {r2.get('concerns', '')}",
            "",
            f"Call graph revealed {len(graph_added)} additional function(s): {graph_added}",
            div, "",
        ]
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"Analysis saved -> {os.path.relpath(out)}")


# ── Per-project processing (for batch/thesis mode) ────────────────────────────

def process_project(project_dir: str, client, provider: str, model: str,
                    out_suffix: str = "") -> dict | None:
    name      = os.path.basename(project_dir)
    src_dir   = os.path.join(project_dir, "src")
    diff_file = os.path.join(project_dir, "diff.txt")
    gt_file   = os.path.join(project_dir, "ground_truth.json")
    cg_file   = os.path.join(project_dir, "diff_with_callgraph.txt")
    eval_file = os.path.join(project_dir, f"evaluation{out_suffix}.txt")

    for path in [diff_file, gt_file]:
        if not os.path.isfile(path):
            print(f"  [{name}] Missing {os.path.basename(path)} — skipping.")
            return None

    c_files = sorted(glob.glob(os.path.join(src_dir, "*.c")))
    if not c_files:
        print(f"  [{name}] No .c files in src/ — skipping.")
        return None

    print(f"  [{name}] Building call graph ({len(c_files)} file(s))...")
    cg = CallGraph()
    cg.build(c_files)

    with open(diff_file, encoding="utf-8") as f:
        diff_text = f.read()

    file_to_lines = parse_diff(diff_text, repo_root=os.path.abspath(project_dir))
    changed_fns   = ImpactAnalyzer(cg).find_changed_functions(file_to_lines)
    cg_content    = build_diff_with_graph(diff_text, cg, changed_fns)

    with open(cg_file, "w", encoding="utf-8") as f:
        f.write(cg_content)

    with open(gt_file, encoding="utf-8") as f:
        gt = json.load(f)
    all_fns = set(gt["all_functions"])
    gt_pos  = set(gt["changed_functions"]) | set(gt["affected_functions"])

    def predicted_set(resp):
        return (set(resp.get("changed_functions", [])) |
                set(resp.get("affected_functions", []))) & all_fns

    model_label = f"{provider.upper()} / {model}"
    print(f"  [{name}] Querying {model_label} (Friend 1)...")
    r1 = query_model(build_diff_only(diff_text), client, provider, model)

    print(f"  [{name}] Querying {model_label} (Friend 2)...")
    r2 = query_model(cg_content, client, provider, model)

    m1 = compute_metrics(predicted_set(r1), gt_pos, all_fns)
    m2 = compute_metrics(predicted_set(r2), gt_pos, all_fns)

    winner = ("Friend 2 (diff+graph)" if m2["F1"] > m1["F1"]
              else "Friend 1 (diff only)" if m1["F1"] > m2["F1"]
              else "Tie")

    div  = "=" * 72
    div2 = "-" * 72
    lines = [
        div, f"Project : {name}  [{model_label}]", div, "",
        "GROUND TRUTH",
        f"  Changed  : {sorted(gt['changed_functions'])}",
        f"  Affected : {sorted(gt['affected_functions'])}",
        f"  All fns  : {sorted(gt['all_functions'])}",
        "", div2, "FRIEND 1  (diff only)", div2,
        f"  Predicted changed  : {sorted(r1.get('changed_functions', []))}",
        f"  Predicted affected : {sorted(r1.get('affected_functions', []))}",
        f"  Concerns : {r1.get('concerns', '')}",
        metrics_line(m1),
    ]
    if m1["FP_fns"]: lines.append(f"  False alarms : {m1['FP_fns']}")
    if m1["FN_fns"]: lines.append(f"  Missed       : {m1['FN_fns']}")
    lines += [
        "", div2, "FRIEND 2  (diff + call graph)", div2,
        f"  Predicted changed  : {sorted(r2.get('changed_functions', []))}",
        f"  Predicted affected : {sorted(r2.get('affected_functions', []))}",
        f"  Concerns : {r2.get('concerns', '')}",
        metrics_line(m2),
    ]
    if m2["FP_fns"]: lines.append(f"  False alarms : {m2['FP_fns']}")
    if m2["FN_fns"]: lines.append(f"  Missed       : {m2['FN_fns']}")
    lines += [
        "", div, f"WINNER : {winner}",
        f"  Friend 1 F1 = {m1['F1']:.3f}    Friend 2 F1 = {m2['F1']:.3f}",
        div, "",
    ]

    with open(eval_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  [{name}] {os.path.basename(eval_file)} written "
          f"(F1: F1={m1['F1']:.3f}  F2={m2['F1']:.3f}  Winner: {winner})")
    return {"project": name, "friend1": m1, "friend2": m2}


# ── Batch results writer ───────────────────────────────────────────────────────

def write_batch_results(results: list, batch_dir: str, model: str,
                        batch_label: str = "", out_suffix: str = ""):
    valid  = [r for r in results if r]
    COL    = 24
    header = (f"{'Project':<{COL}} | {'Approach':<22} | "
              f"{'TP':>4} {'TN':>4} {'FP':>4} {'FN':>4} | "
              f"{'Prec':>6} {'Rec':>6} {'F1':>6} {'Acc':>6}")
    sep    = "-" * len(header)
    lines  = [
        f"Batch : {batch_label or os.path.basename(batch_dir)}",
        f"Model : {model}",
        f"Projects evaluated : {len(valid)}/{len(results)}",
        "", header, sep,
    ]
    f1_list, f2_list = [], []
    for r in valid:
        for label, m, lst in [
            ("Friend 1 (diff only)",  r["friend1"], f1_list),
            ("Friend 2 (diff+graph)", r["friend2"], f2_list),
        ]:
            lst.append(m["F1"])
            lines.append(
                f"{r['project']:<{COL}} | {label:<22} | "
                f"{m['TP']:>4} {m['TN']:>4} {m['FP']:>4} {m['FN']:>4} | "
                f"{m['Precision']:>6.3f} {m['Recall']:>6.3f} "
                f"{m['F1']:>6.3f} {m['Accuracy']:>6.3f}"
            )
        lines.append(sep)

    def avg(lst): return sum(lst) / len(lst) if lst else 0.0
    delta = avg(f2_list) - avg(f1_list)
    sign  = "+" if delta >= 0 else ""
    lines += [
        "",
        f"{'Avg F1  Friend 1 (diff only)   :':<42} {avg(f1_list):.3f}",
        f"{'Avg F1  Friend 2 (diff+graph)  :':<42} {avg(f2_list):.3f}",
        f"{'Delta (Friend 2 - Friend 1)    :':<42} {sign}{delta:.3f}",
        "",
    ]
    out_path = os.path.join(batch_dir, f"batch_results{out_suffix}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nBatch results saved -> {os.path.relpath(out_path)}")
    for line in lines:
        print(line)


# ── Subcommand: batch ──────────────────────────────────────────────────────────

def cmd_batch(args, cfg):
    model    = resolve_model(args.model)
    client, provider = get_api_client(model, cfg, args)
    out_suffix = "" if provider == "openai" else f"_{provider}"

    batch_dir = os.path.abspath(args.batch_dir)
    if not os.path.isdir(batch_dir):
        sys.exit(f"ERROR: Batch directory not found: {batch_dir}")

    projects = sorted([
        os.path.join(batch_dir, d)
        for d in os.listdir(batch_dir)
        if os.path.isdir(os.path.join(batch_dir, d))
    ])

    batch_label = os.path.relpath(batch_dir, ROOT)
    print(f"Batch : {batch_label}")
    print(f"Model : {model}")
    print(f"Projects found : {len(projects)}\n")

    results = []
    for pdir in projects:
        try:
            results.append(process_project(pdir, client, provider, model, out_suffix))
        except Exception as e:
            print(f"  [{os.path.basename(pdir)}] ERROR: {e}")
            results.append(None)

    write_batch_results(results, batch_dir, model, batch_label, out_suffix)


# ── Subcommand: summary ────────────────────────────────────────────────────────

def _parse_eval_file(path: str) -> dict | None:
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        text = f.read()
    f1_1 = f1_2 = None
    for line in text.splitlines():
        line = line.strip()
        if "F1=" in line and "TP=" in line:
            parts = {p.split("=")[0].strip(): p.split("=")[1].strip()
                     for p in line.split() if "=" in p}
            val = float(parts.get("F1", 0))
            if f1_1 is None:
                f1_1 = val
            else:
                f1_2 = val
        if "WINNER" in line:
            break
    if f1_1 is None or f1_2 is None:
        return None
    return {"f1": f1_1, "f2": f1_2}


def cmd_summary(args, cfg):
    all_rows = []
    batch_summaries = []

    for label, bd in BATCHES:
        if not os.path.isdir(bd):
            print(f"  Skipping {label} (not found)")
            continue
        rows = []
        for proj_dir in sorted(glob.glob(os.path.join(bd, "*"))):
            if not os.path.isdir(proj_dir):
                continue
            data = _parse_eval_file(os.path.join(proj_dir, "evaluation.txt"))
            if data:
                rows.append({"batch": label, "project": os.path.basename(proj_dir),
                             "f1_f1": data["f1"], "f2_f1": data["f2"]})
        if not rows:
            print(f"  Skipping {label} (no evaluation.txt files)")
            continue
        all_rows.extend(rows)
        avg1 = sum(r["f1_f1"] for r in rows) / len(rows)
        avg2 = sum(r["f2_f1"] for r in rows) / len(rows)
        batch_summaries.append({"batch": label, "n": len(rows),
                                 "avg_f1": avg1, "avg_f2": avg2})

    if not all_rows:
        print("No evaluation data found. Run 'batch' on each batch first.")
        return

    COL = 24
    header = (f"{'Batch':<14} {'Project':<{COL}} | "
              f"{'F1 Friend1':>10} {'F1 Friend2':>10} | {'Winner':<22}")
    sep = "-" * len(header)
    lines = [
        "=" * len(header), "CROSS-BATCH SUMMARY (GPT-4o)", "=" * len(header),
        "", header, sep,
    ]

    prev_batch = None
    win1 = win2 = ties = 0
    for r in all_rows:
        if r["batch"] != prev_batch:
            if prev_batch is not None:
                lines.append(sep)
            prev_batch = r["batch"]
        winner = ("Friend2" if r["f2_f1"] > r["f1_f1"]
                  else "Friend1" if r["f1_f1"] > r["f2_f1"]
                  else "Tie")
        if winner == "Friend2":   win2 += 1
        elif winner == "Friend1": win1 += 1
        else:                     ties += 1
        lines.append(
            f"{r['batch']:<14} {r['project']:<{COL}} | "
            f"{r['f1_f1']:>10.3f} {r['f2_f1']:>10.3f} | {winner:<22}"
        )
    lines.append(sep)

    lines += ["", "PER-BATCH AVERAGES", sep]
    for bs in batch_summaries:
        delta = bs["avg_f2"] - bs["avg_f1"]
        sign  = "+" if delta >= 0 else ""
        lines.append(
            f"{bs['batch']:<14} n={bs['n']:<4} "
            f"Avg F1 Friend1={bs['avg_f1']:.3f}  "
            f"Friend2={bs['avg_f2']:.3f}  "
            f"Delta={sign}{delta:.3f}"
        )
    lines.append(sep)

    total = len(all_rows)
    ov1 = sum(r["f1_f1"] for r in all_rows) / total
    ov2 = sum(r["f2_f1"] for r in all_rows) / total
    delta = ov2 - ov1
    lines += [
        "", f"OVERALL  ({total} projects across {len(batch_summaries)} batches)", sep,
        f"  Avg F1  Friend 1 (diff only)   : {ov1:.3f}",
        f"  Avg F1  Friend 2 (diff+graph)  : {ov2:.3f}",
        f"  Delta  (Friend2 - Friend1)     : {'+' if delta>=0 else ''}{delta:.3f}",
        "",
        f"  Friend2 wins : {win2}/{total}  ({100*win2/total:.1f}%)",
        f"  Friend1 wins : {win1}/{total}  ({100*win1/total:.1f}%)",
        f"  Ties         : {ties}/{total}  ({100*ties/total:.1f}%)",
        sep, "",
    ]

    out_path = os.path.join(ROOT, "reports", "all_batches_summary.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    print(f"Summary saved -> {os.path.relpath(out_path)}")


# ── Subcommand: compare ────────────────────────────────────────────────────────

def cmd_compare(args, cfg):
    rows = []
    for label, bd in BATCHES:
        if not os.path.isdir(bd):
            continue
        for proj_dir in sorted(glob.glob(os.path.join(bd, "*"))):
            if not os.path.isdir(proj_dir):
                continue
            proj   = os.path.basename(proj_dir)
            gpt    = _parse_eval_file(os.path.join(proj_dir, "evaluation.txt"))
            claude = _parse_eval_file(os.path.join(proj_dir, "evaluation_claude.txt"))
            if gpt is None or claude is None:
                print(f"  [{label}/{proj}] Missing evaluation file(s) — skipping.")
                continue
            rows.append({
                "batch": label, "project": proj,
                "gpt_f1": gpt["f1"], "gpt_f2": gpt["f2"],
                "claude_f1": claude["f1"], "claude_f2": claude["f2"],
            })

    if not rows:
        print("No data. Run 'batch --model gpt' and 'batch --model claude' first.")
        return

    C1, C2, C3 = 14, 24, 10
    W = C1 + C2 + C3 * 4 + 20
    div  = "=" * W
    div2 = "-" * W
    header = (f"{'Batch':<{C1}} {'Project':<{C2}} | "
              f"{'GPT F1-1':>{C3}} {'GPT F1-2':>{C3}} | "
              f"{'CLD F1-1':>{C3}} {'CLD F1-2':>{C3}} | "
              f"{'Better (F2)':>14}")
    lines = [
        div,
        "GPT-4o  vs  Claude (claude-sonnet-4-6)  --  50 Projects / 5 Batches",
        "F1-1 = Friend 1 (diff only)   F1-2 = Friend 2 (diff + call graph)",
        div, "", header, div2,
    ]

    prev_batch = None
    gpt_f1_all, gpt_f2_all, cld_f1_all, cld_f2_all = [], [], [], []
    batch_agg: dict = {}

    for r in rows:
        if r["batch"] != prev_batch:
            if prev_batch is not None:
                lines.append(div2)
            prev_batch = r["batch"]
            batch_agg.setdefault(r["batch"], {"gf1": [], "gf2": [], "cf1": [], "cf2": []})

        ba = batch_agg[r["batch"]]
        ba["gf1"].append(r["gpt_f1"]);    ba["gf2"].append(r["gpt_f2"])
        ba["cf1"].append(r["claude_f1"]); ba["cf2"].append(r["claude_f2"])
        gpt_f1_all.append(r["gpt_f1"]);   gpt_f2_all.append(r["gpt_f2"])
        cld_f1_all.append(r["claude_f1"]); cld_f2_all.append(r["claude_f2"])

        better = ("GPT" if r["gpt_f2"] > r["claude_f2"]
                  else "Claude" if r["claude_f2"] > r["gpt_f2"]
                  else "Tie")
        lines.append(
            f"{r['batch']:<{C1}} {r['project']:<{C2}} | "
            f"{r['gpt_f1']:>{C3}.3f} {r['gpt_f2']:>{C3}.3f} | "
            f"{r['claude_f1']:>{C3}.3f} {r['claude_f2']:>{C3}.3f} | "
            f"{better:>14}"
        )
    lines.append(div2)

    def avg(lst): return sum(lst) / len(lst) if lst else 0.0

    lines += ["", "PER-BATCH AVERAGES (Friend 2 -- diff + call graph)", div2]
    for label, _ in BATCHES:
        if label not in batch_agg:
            continue
        ba = batch_agg[label]
        gf2 = avg(ba["gf2"]); cf2 = avg(ba["cf2"])
        gf1 = avg(ba["gf1"]); cf1 = avg(ba["cf1"])
        winner = "GPT" if gf2 > cf2 else "Claude" if cf2 > gf2 else "Tie"
        lines.append(
            f"{label:<14} n={len(ba['gf2'])}  "
            f"GPT  F1(diff-only)={gf1:.3f}  F1(+graph)={gf2:.3f}   "
            f"Claude F1(diff-only)={cf1:.3f}  F1(+graph)={cf2:.3f}   "
            f"Better(F2): {winner}"
        )
    lines.append(div2)

    n = len(rows)
    og_f1 = avg(gpt_f1_all); og_f2 = avg(gpt_f2_all)
    oc_f1 = avg(cld_f1_all); oc_f2 = avg(cld_f2_all)
    gpt_wins  = sum(1 for r in rows if r["gpt_f2"] > r["claude_f2"])
    cld_wins  = sum(1 for r in rows if r["claude_f2"] > r["gpt_f2"])
    ties_f2   = sum(1 for r in rows if r["gpt_f2"] == r["claude_f2"])
    gpt_delta = og_f2 - og_f1
    cld_delta = oc_f2 - oc_f1

    lines += [
        "", f"OVERALL  ({n} projects across 5 batches)", div, "",
        f"  {'Metric':<42} {'GPT-4o':>10} {'Claude':>10}",
        f"  {'-'*62}",
        f"  {'Avg F1 -- Friend 1  (diff only)':<42} {og_f1:>10.3f} {oc_f1:>10.3f}",
        f"  {'Avg F1 -- Friend 2  (diff + call graph)':<42} {og_f2:>10.3f} {oc_f2:>10.3f}",
        f"  {'Graph context improvement (F2-F1)':<42} {gpt_delta:>+10.3f} {cld_delta:>+10.3f}",
        "",
        f"  Friend-2 head-to-head (which model scored higher per project):",
        f"    GPT-4o wins  : {gpt_wins}/{n}  ({100*gpt_wins/n:.1f}%)",
        f"    Claude wins  : {cld_wins}/{n}  ({100*cld_wins/n:.1f}%)",
        f"    Ties         : {ties_f2}/{n}  ({100*ties_f2/n:.1f}%)",
        "",
        f"  Overall winner (Friend-2 Avg F1): "
        f"{'GPT-4o' if og_f2 > oc_f2 else 'Claude' if oc_f2 > og_f2 else 'Tie'}"
        f"  (GPT={og_f2:.3f}  Claude={oc_f2:.3f}  delta={oc_f2-og_f2:+.3f})",
        "", div, "",
    ]

    out_path = os.path.join(ROOT, "reports", "gpt_vs_claude.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    print(f"Comparison saved -> {os.path.relpath(out_path)}")


# ── Subcommand: config ─────────────────────────────────────────────────────────

def cmd_config(args, cfg):
    if args.gpt_key:
        cfg["openai_key"] = args.gpt_key
    if args.claude_key:
        cfg["anthropic_key"] = args.claude_key
    if args.gpt_key or args.claude_key:
        save_config(cfg)
    else:
        print("Current config:")
        gpt = cfg.get("openai_key", "(not set)")
        ant = cfg.get("anthropic_key", "(not set)")
        if gpt != "(not set)":
            gpt = gpt[:12] + "..." + gpt[-4:]
        if ant != "(not set)":
            ant = ant[:16] + "..." + ant[-4:]
        print(f"  OpenAI key   : {gpt}")
        print(f"  Anthropic key: {ant}")
        print(f"\nConfig file: {os.path.relpath(CONFIG_FILE)}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="graphguard",
        description="GraphGuard -- AI-powered C code impact analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
commands:
  analyze   Detect git changes and analyze impact (run from your C project)
  batch     Run evaluation on a thesis batch directory (with ground truth)
  summary   Regenerate cross-batch GPT summary -> reports/all_batches_summary.txt
  compare   Regenerate GPT vs Claude comparison -> reports/gpt_vs_claude.txt
  config    View or set API keys

model aliases (--model):
  gpt / gpt-4o / gpt-4o-mini
  claude / claude-sonnet / claude-sonnet-4-6
  claude-opus / claude-opus-4-7
  claude-haiku / claude-haiku-4-5

analyze examples:
  python graphguard.py analyze                     # auto-detect all uncommitted changes
  python graphguard.py analyze --staged            # only staged changes
  python graphguard.py analyze --unpushed          # committed but not yet pushed
  python graphguard.py analyze --model claude      # use Claude instead of GPT
  python graphguard.py analyze --save              # also save result to graphguard_analysis.txt

batch examples:
  python graphguard.py batch ./batches/batch_01 --model gpt
  python graphguard.py batch ./batches/batch_02 --model claude
""")

    sub = parser.add_subparsers(dest="command")

    # analyze
    p_analyze = sub.add_parser("analyze", help="Analyze git changes in current directory")
    p_analyze.add_argument("--model", "-m", default="gpt",
                           help="Model to use (default: gpt)")
    p_analyze.add_argument("--staged", action="store_true",
                           help="Only analyze staged changes")
    p_analyze.add_argument("--unpushed", action="store_true",
                           help="Analyze committed but not yet pushed changes")
    p_analyze.add_argument("--save", action="store_true",
                           help="Save analysis to graphguard_analysis.txt")
    p_analyze.add_argument("--api-key", help="Override API key for this run")
    p_analyze.add_argument("--diff", dest="diff_file",
                           help="Use a specific diff file instead of git diff")

    # batch
    p_batch = sub.add_parser("batch", help="Evaluate a batch directory (thesis mode)")
    p_batch.add_argument("batch_dir", help="Path to batch directory")
    p_batch.add_argument("--model", "-m", default="gpt", help="Model (default: gpt)")
    p_batch.add_argument("--api-key", help="Override API key for this run")

    # summary
    sub.add_parser("summary", help="Regenerate cross-batch GPT summary")

    # compare
    sub.add_parser("compare", help="Regenerate GPT vs Claude comparison")

    # config
    p_config = sub.add_parser("config", help="View or set API keys")
    p_config.add_argument("--gpt-key", help="Set OpenAI API key")
    p_config.add_argument("--claude-key", help="Set Anthropic API key")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    cfg = load_config()
    dispatch = {
        "analyze": cmd_analyze,
        "batch":   cmd_batch,
        "summary": cmd_summary,
        "compare": cmd_compare,
        "config":  cmd_config,
    }
    dispatch[args.command](args, cfg)


if __name__ == "__main__":
    main()
