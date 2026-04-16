#!/usr/bin/env python3
"""
summarize_all.py  —  reads batch_results.txt from every batch folder
and writes a combined cross-batch summary.

Usage (from project root):
    python scripts/summarize_all.py

Output: all_batches_summary.txt  (project root)
"""

import os, json, glob

ROOT    = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BATCHES = [
    os.path.join(ROOT, "test_projects"),               # batch 01
    os.path.join(ROOT, "batches", "batch_02"),
    os.path.join(ROOT, "batches", "batch_03"),
    os.path.join(ROOT, "batches", "batch_04"),
    os.path.join(ROOT, "batches", "batch_05"),
]

def load_evaluations(batch_dir: str) -> list[dict]:
    """Read every project/evaluation.txt in a batch and parse the metrics."""
    results = []
    for proj_dir in sorted(glob.glob(os.path.join(batch_dir, "*"))):
        if not os.path.isdir(proj_dir):
            continue
        ev = os.path.join(proj_dir, "evaluation.txt")
        if not os.path.isfile(ev):
            continue
        with open(ev, encoding="utf-8") as f:
            text = f.read()
        rec = _parse_evaluation(text, os.path.basename(proj_dir), os.path.basename(batch_dir))
        if rec:
            results.append(rec)
    return results

def _parse_evaluation(text: str, proj: str, batch: str) -> dict | None:
    """Pull F1 scores out of an evaluation.txt."""
    f1_1 = f1_2 = None
    for line in text.splitlines():
        line = line.strip()
        # metrics line looks like: TP=X  TN=X  FP=X  FN=X  Prec=X  Rec=X  F1=X  Acc=X
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
    return {"batch": batch, "project": proj, "f1_f1": f1_1, "f2_f1": f1_2}

def main():
    all_rows = []
    batch_summaries = []

    for bd in BATCHES:
        bname = os.path.basename(bd)
        if not os.path.isdir(bd):
            print(f"  Skipping {bname} (not found)")
            continue
        rows = load_evaluations(bd)
        if not rows:
            print(f"  Skipping {bname} (no evaluation.txt files)")
            continue
        all_rows.extend(rows)
        avg1 = sum(r["f1_f1"] for r in rows) / len(rows)
        avg2 = sum(r["f2_f1"] for r in rows) / len(rows)
        batch_summaries.append({"batch": bname, "n": len(rows), "avg_f1": avg1, "avg_f2": avg2})

    if not all_rows:
        print("No evaluation data found. Run run_batch.py on each batch first.")
        return

    COL = 24
    header = (f"{'Batch':<14} {'Project':<{COL}} | {'F1 Friend1':>10} {'F1 Friend2':>10} | {'Winner':<22}")
    sep    = "-" * len(header)

    lines = [
        "=" * len(header),
        "CROSS-BATCH SUMMARY",
        "=" * len(header),
        "",
        header,
        sep,
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
            f"{r['batch']:<14} {r['project']:<{COL}} | {r['f1_f1']:>10.3f} {r['f2_f1']:>10.3f} | {winner:<22}"
        )
    lines.append(sep)

    # Per-batch averages
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

    # Overall
    total = len(all_rows)
    ov1 = sum(r["f1_f1"] for r in all_rows) / total
    ov2 = sum(r["f2_f1"] for r in all_rows) / total
    delta = ov2 - ov1

    lines += [
        "",
        "OVERALL  (" + str(total) + " projects across " + str(len(batch_summaries)) + " batches)",
        sep,
        f"  Avg F1  Friend 1 (diff only)   : {ov1:.3f}",
        f"  Avg F1  Friend 2 (diff+graph)  : {ov2:.3f}",
        f"  Delta  (Friend2 - Friend1)     : {'+' if delta>=0 else ''}{delta:.3f}",
        "",
        f"  Friend2 wins : {win2}/{total}  ({100*win2/total:.1f}%)",
        f"  Friend1 wins : {win1}/{total}  ({100*win1/total:.1f}%)",
        f"  Ties         : {ties}/{total}  ({100*ties/total:.1f}%)",
        sep,
        "",
    ]

    out_path = os.path.join(ROOT, "all_batches_summary.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n".join(lines))
    print(f"\nSummary saved -> {os.path.relpath(out_path)}")

if __name__ == "__main__":
    main()
