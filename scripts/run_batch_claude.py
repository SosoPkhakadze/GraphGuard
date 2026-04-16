#!/usr/bin/env python3
"""
run_batch_claude.py  —  same evaluation pipeline as run_batch.py
but uses the Anthropic Claude API instead of OpenAI GPT.

Outputs per project : evaluation_claude.txt   (does NOT overwrite evaluation.txt)
Output per batch    : batch_results_claude.txt (does NOT overwrite batch_results.txt)

Usage (from project root):
    python scripts/run_batch_claude.py                      # runs BATCH_DIR
    python scripts/run_batch_claude.py batches/batch_02     # override via CLI
"""

# ── CONFIG — only section you need to change ────────────────────────────────
BATCH_DIR     = "test_projects"   # relative to project root
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")  # set via env or graphguard.py config
MODEL         = "claude-sonnet-4-6"
# ────────────────────────────────────────────────────────────────────────────

import os, sys, json, glob

ROOT_DIR     = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ANALYZER_DIR = os.path.join(ROOT_DIR, "analyzer")
sys.path.insert(0, ANALYZER_DIR)

from callgraph       import CallGraph
from diff_parser     import parse as parse_diff
from impact          import ImpactAnalyzer
from context_builder import build_diff_with_graph, build_diff_only

import anthropic as _anthropic
_client = _anthropic.Anthropic(api_key=ANTHROPIC_KEY)

PROMPT = """\
You are reviewing a C code change to identify impact.
Respond ONLY with valid JSON — no markdown fences, no explanation:
{{"changed_functions": ["directly modified functions"], "affected_functions": ["functions that call or depend on changed functions"], "concerns": "one sentence"}}

{content}"""


def query_claude(content: str) -> dict:
    msg = _client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": PROMPT.format(content=content)}],
    )
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    return json.loads(text)


# ── Metrics ──────────────────────────────────────────────────────────────────

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


# ── Per-project ───────────────────────────────────────────────────────────────

def process_project(project_dir: str) -> dict | None:
    name      = os.path.basename(project_dir)
    src_dir   = os.path.join(project_dir, "src")
    diff_file = os.path.join(project_dir, "diff.txt")
    gt_file   = os.path.join(project_dir, "ground_truth.json")
    cg_file   = os.path.join(project_dir, "diff_with_callgraph.txt")

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

    with open(diff_file) as f:
        diff_text = f.read()

    file_to_lines = parse_diff(diff_text, repo_root=os.path.abspath(project_dir))
    changed_fns   = ImpactAnalyzer(cg).find_changed_functions(file_to_lines)

    cg_content = build_diff_with_graph(diff_text, cg, changed_fns)
    with open(cg_file, "w") as f:
        f.write(cg_content)

    with open(gt_file) as f:
        gt = json.load(f)
    all_fns = set(gt["all_functions"])
    gt_pos  = set(gt["changed_functions"]) | set(gt["affected_functions"])

    def predicted_set(resp):
        return (set(resp.get("changed_functions", [])) |
                set(resp.get("affected_functions", []))) & all_fns

    print(f"  [{name}] Querying Claude (Friend 1 — diff only)...")
    r1 = query_claude(build_diff_only(diff_text))

    print(f"  [{name}] Querying Claude (Friend 2 — diff + call graph)...")
    r2 = query_claude(cg_content)

    m1 = compute_metrics(predicted_set(r1), gt_pos, all_fns)
    m2 = compute_metrics(predicted_set(r2), gt_pos, all_fns)

    winner = ("Friend 2 (diff+graph)" if m2["F1"] > m1["F1"]
              else "Friend 1 (diff only)" if m1["F1"] > m2["F1"]
              else "Tie")

    eval_path = os.path.join(project_dir, "evaluation_claude.txt")
    with open(eval_path, "w", encoding="utf-8") as f:
        f.write(_fmt(name, gt, r1, m1, r2, m2, winner))

    print(f"  [{name}] evaluation_claude.txt written "
          f"(F1: Friend1={m1['F1']:.3f} Friend2={m2['F1']:.3f}  Winner: {winner})")
    return {"project": name, "friend1": m1, "friend2": m2}


def _fmt(name, gt, r1, m1, r2, m2, winner) -> str:
    div  = "=" * 72
    div2 = "-" * 72
    def mline(m):
        return (f"  TP={m['TP']}  TN={m['TN']}  FP={m['FP']}  FN={m['FN']}  "
                f"Prec={m['Precision']:.3f}  Rec={m['Recall']:.3f}  "
                f"F1={m['F1']:.3f}  Acc={m['Accuracy']:.3f}")
    lines = [
        div, f"Project : {name}  [Claude / {MODEL}]", div, "",
        "GROUND TRUTH",
        f"  Changed  : {sorted(gt['changed_functions'])}",
        f"  Affected : {sorted(gt['affected_functions'])}",
        f"  All fns  : {sorted(gt['all_functions'])}",
        "", div2, "FRIEND 1  (diff only)", div2,
        f"  Predicted changed  : {sorted(r1.get('changed_functions',[]))}",
        f"  Predicted affected : {sorted(r1.get('affected_functions',[]))}",
        f"  Concerns : {r1.get('concerns','')}",
        mline(m1),
    ]
    if m1["FP_fns"]: lines.append(f"  False alarms : {m1['FP_fns']}")
    if m1["FN_fns"]: lines.append(f"  Missed       : {m1['FN_fns']}")
    lines += [
        "", div2, "FRIEND 2  (diff + call graph)", div2,
        f"  Predicted changed  : {sorted(r2.get('changed_functions',[]))}",
        f"  Predicted affected : {sorted(r2.get('affected_functions',[]))}",
        f"  Concerns : {r2.get('concerns','')}",
        mline(m2),
    ]
    if m2["FP_fns"]: lines.append(f"  False alarms : {m2['FP_fns']}")
    if m2["FN_fns"]: lines.append(f"  Missed       : {m2['FN_fns']}")
    lines += [
        "", div, f"WINNER : {winner}",
        f"  Friend 1 F1 = {m1['F1']:.3f}    Friend 2 F1 = {m2['F1']:.3f}",
        div, "",
    ]
    return "\n".join(lines)


# ── Batch summary ─────────────────────────────────────────────────────────────

def write_batch_results(results: list, batch_dir: str, batch_label: str = ""):
    valid  = [r for r in results if r]
    COL    = 24
    header = (f"{'Project':<{COL}} | {'Approach':<22} | "
              f"{'TP':>4} {'TN':>4} {'FP':>4} {'FN':>4} | "
              f"{'Prec':>6} {'Rec':>6} {'F1':>6} {'Acc':>6}")
    sep    = "-" * len(header)
    lines  = [
        f"Batch : {batch_label or os.path.basename(batch_dir)}",
        f"Model : {MODEL}  (Claude)",
        f"Projects evaluated : {len(valid)}/{len(results)}",
        "", header, sep,
    ]
    f1_f1, f2_f1 = [], []
    for r in valid:
        for label, m, lst in [
            ("Friend 1 (diff only)",  r["friend1"], f1_f1),
            ("Friend 2 (diff+graph)", r["friend2"], f2_f1),
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
    delta = avg(f2_f1) - avg(f1_f1)
    sign  = "+" if delta >= 0 else ""
    lines += [
        "",
        f"{'Avg F1  Friend 1 (diff only)   :':<42} {avg(f1_f1):.3f}",
        f"{'Avg F1  Friend 2 (diff+graph)  :':<42} {avg(f2_f1):.3f}",
        f"{'Delta (Friend 2 - Friend 1)    :':<42} {sign}{delta:.3f}",
        "",
    ]
    out_path = os.path.join(batch_dir, "batch_results_claude.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nBatch results saved -> {os.path.relpath(out_path)}")
    print()
    for line in lines:
        print(line)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    batch_dir = sys.argv[1] if len(sys.argv) > 1 else BATCH_DIR
    batch_abs = os.path.normpath(os.path.join(ROOT_DIR, batch_dir))
    if not os.path.isdir(batch_abs):
        sys.exit(f"ERROR: BATCH_DIR not found: {batch_abs}")

    projects = sorted([
        os.path.join(batch_abs, d)
        for d in os.listdir(batch_abs)
        if os.path.isdir(os.path.join(batch_abs, d))
    ])

    print(f"Batch : {batch_dir}")
    print(f"Model : {MODEL}  (Claude)")
    print(f"Projects found : {len(projects)}\n")

    results = []
    for pdir in projects:
        try:
            results.append(process_project(pdir))
        except Exception as e:
            print(f"  [{os.path.basename(pdir)}] ERROR: {e}")
            results.append(None)

    write_batch_results(results, batch_abs, batch_dir)


if __name__ == "__main__":
    main()
