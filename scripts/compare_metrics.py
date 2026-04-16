#!/usr/bin/env python3
"""
compare_metrics.py

For each project in test_projects/, loads:
  - ground_truth.json
  - friend1_response.json  (diff only)
  - friend2_response.json  (diff + call graph)

Computes TP, TN, FP, FN, Precision, Recall, F1, Accuracy per project
for both approaches, then prints a summary table and saves metrics_results.json.

The positive class = changed_functions ∪ affected_functions from ground truth.
The negative class = all remaining functions in all_functions.

Usage (from project root):
    python scripts/compare_metrics.py
"""

import os
import json

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.normpath(os.path.join(SCRIPTS_DIR, "..", "test_projects"))


def compute_metrics(predicted: set, ground_pos: set, all_fns: set) -> dict:
    """
    predicted   — functions the AI said are changed or affected
    ground_pos  — functions actually changed or affected (ground truth positives)
    all_fns     — full universe of functions in the project
    """
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
        "Precision": round(prec, 3),
        "Recall":    round(rec,  3),
        "F1":        round(f1,   3),
        "Accuracy":  round(acc,  3),
        "TP_functions": sorted(tp),
        "FP_functions": sorted(fp),
        "FN_functions": sorted(fn),
    }


def evaluate_project(project_dir) -> dict | None:
    name    = os.path.basename(project_dir)
    gt_path = os.path.join(project_dir, "ground_truth.json")
    f1_path = os.path.join(project_dir, "friend1_response.json")
    f2_path = os.path.join(project_dir, "friend2_response.json")

    missing = [p for p in [gt_path, f1_path, f2_path] if not os.path.isfile(p)]
    if missing:
        rel = [os.path.basename(p) for p in missing]
        print(f"  [{name}] Missing: {rel} — skipping.")
        return None

    with open(gt_path) as f: gt = json.load(f)
    with open(f1_path) as f: r1 = json.load(f)
    with open(f2_path) as f: r2 = json.load(f)

    all_fns    = set(gt["all_functions"])
    gt_pos     = set(gt["changed_functions"]) | set(gt["affected_functions"])

    # Filter AI predictions to the known function universe (removes hallucinations)
    def predicted_set(resp):
        p = set(resp.get("changed_functions", [])) | set(resp.get("affected_functions", []))
        return p & all_fns

    m1 = compute_metrics(predicted_set(r1), gt_pos, all_fns)
    m2 = compute_metrics(predicted_set(r2), gt_pos, all_fns)

    return {"project": name, "friend1": m1, "friend2": m2}


def print_table(results: list):
    COL = 22
    header = (
        f"{'Project':<{COL}} | {'Approach':<20} | "
        f"{'TP':>4} {'TN':>4} {'FP':>4} {'FN':>4} | "
        f"{'Prec':>6} {'Rec':>6} {'F1':>6} {'Acc':>6}"
    )
    sep = "─" * len(header)

    print(f"\n{header}")
    print(sep)

    f1_scores, f2_scores = [], []

    for r in results:
        if r is None:
            continue
        for label, m, score_list in [
            ("Friend 1 (diff only)",    r["friend1"], f1_scores),
            ("Friend 2 (diff+graph)",   r["friend2"], f2_scores),
        ]:
            score_list.append(m["F1"])
            print(
                f"{r['project']:<{COL}} | {label:<20} | "
                f"{m['TP']:>4} {m['TN']:>4} {m['FP']:>4} {m['FN']:>4} | "
                f"{m['Precision']:>6.3f} {m['Recall']:>6.3f} "
                f"{m['F1']:>6.3f} {m['Accuracy']:>6.3f}"
            )

            if m["FP_functions"]:
                print(f"{'':>{COL}}   FP (false alarms): {m['FP_functions']}")
            if m["FN_functions"]:
                print(f"{'':>{COL}}   FN (missed):       {m['FN_functions']}")
        print(sep)

    def avg(lst): return sum(lst) / len(lst) if lst else 0.0

    print(f"\n{'Avg F1  Friend 1 (diff only)   :':<40} {avg(f1_scores):.3f}")
    print(f"{'Avg F1  Friend 2 (diff+graph)  :':<40} {avg(f2_scores):.3f}")
    delta = avg(f2_scores) - avg(f1_scores)
    sign  = "+" if delta >= 0 else ""
    print(f"{'Delta (Friend 2 − Friend 1)    :':<40} {sign}{delta:.3f}")


def main():
    projects = sorted([
        os.path.join(PROJECTS_DIR, d)
        for d in os.listdir(PROJECTS_DIR)
        if os.path.isdir(os.path.join(PROJECTS_DIR, d))
    ])

    results = [evaluate_project(p) for p in projects]
    print_table(results)

    out_path = os.path.normpath(os.path.join(SCRIPTS_DIR, "..", "metrics_results.json"))
    with open(out_path, "w") as f:
        json.dump([r for r in results if r], f, indent=2)
    print(f"\nFull results saved → {os.path.relpath(out_path)}")


if __name__ == "__main__":
    main()
