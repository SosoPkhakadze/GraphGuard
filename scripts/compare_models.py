#!/usr/bin/env python3
"""
compare_models.py  —  reads evaluation.txt (GPT) and evaluation_claude.txt (Claude)
from every project across all 5 batches and writes gpt_vs_claude.txt.

Usage (from project root):
    python scripts/compare_models.py
"""

import os, glob

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BATCHES = [
    ("test_projects",    os.path.join(ROOT, "test_projects")),
    ("batch_02",         os.path.join(ROOT, "batches", "batch_02")),
    ("batch_03",         os.path.join(ROOT, "batches", "batch_03")),
    ("batch_04",         os.path.join(ROOT, "batches", "batch_04")),
    ("batch_05",         os.path.join(ROOT, "batches", "batch_05")),
]


def parse_eval(path: str) -> dict | None:
    """Extract F1 scores for Friend1 and Friend2 from an evaluation txt."""
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


def main():
    rows = []

    for batch_label, batch_dir in BATCHES:
        if not os.path.isdir(batch_dir):
            print(f"  Skipping {batch_label} (not found)")
            continue
        for proj_dir in sorted(glob.glob(os.path.join(batch_dir, "*"))):
            if not os.path.isdir(proj_dir):
                continue
            proj = os.path.basename(proj_dir)
            gpt    = parse_eval(os.path.join(proj_dir, "evaluation.txt"))
            claude = parse_eval(os.path.join(proj_dir, "evaluation_claude.txt"))
            if gpt is None or claude is None:
                print(f"  [{batch_label}/{proj}] Missing evaluation file(s) — skipping.")
                continue
            rows.append({
                "batch": batch_label, "project": proj,
                "gpt_f1":    gpt["f1"],    "gpt_f2":    gpt["f2"],
                "claude_f1": claude["f1"], "claude_f2": claude["f2"],
            })

    if not rows:
        print("No data found. Run run_batch.py and run_batch_claude.py on all batches first.")
        return

    # ── build report ────────────────────────────────────────────────────────
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
        "GPT-4o  vs  Claude (claude-sonnet-4-6)  —  50 Projects / 5 Batches",
        "F1-1 = Friend 1 (diff only)   F1-2 = Friend 2 (diff + call graph)",
        div, "", header, div2,
    ]

    prev_batch = None
    gpt_f1_all, gpt_f2_all, cld_f1_all, cld_f2_all = [], [], [], []
    batch_agg = {}   # batch_label -> {gf1,gf2,cf1,cf2 lists}

    for r in rows:
        if r["batch"] != prev_batch:
            if prev_batch is not None:
                lines.append(div2)
            prev_batch = r["batch"]
            batch_agg.setdefault(r["batch"], {"gf1":[],"gf2":[],"cf1":[],"cf2":[]})

        ba = batch_agg[r["batch"]]
        ba["gf1"].append(r["gpt_f1"]);    ba["gf2"].append(r["gpt_f2"])
        ba["cf1"].append(r["claude_f1"]); ba["cf2"].append(r["claude_f2"])
        gpt_f1_all.append(r["gpt_f1"]);   gpt_f2_all.append(r["gpt_f2"])
        cld_f1_all.append(r["claude_f1"]); cld_f2_all.append(r["claude_f2"])

        # who won on Friend-2 comparison (the augmented approach)?
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

    # ── per-batch averages ───────────────────────────────────────────────────
    def avg(lst): return sum(lst) / len(lst) if lst else 0.0

    lines += ["", "PER-BATCH AVERAGES (Friend 2 — diff + call graph)", div2]
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

    # ── overall ──────────────────────────────────────────────────────────────
    n = len(rows)
    og_f1 = avg(gpt_f1_all);   og_f2 = avg(gpt_f2_all)
    oc_f1 = avg(cld_f1_all);   oc_f2 = avg(cld_f2_all)

    gpt_wins   = sum(1 for r in rows if r["gpt_f2"] > r["claude_f2"])
    cld_wins   = sum(1 for r in rows if r["claude_f2"] > r["gpt_f2"])
    ties_f2    = sum(1 for r in rows if r["gpt_f2"] == r["claude_f2"])

    # delta improvements: how much does graph context help each model?
    gpt_delta   = og_f2 - og_f1
    cld_delta   = oc_f2 - oc_f1

    lines += [
        "",
        "OVERALL  (" + str(n) + " projects across 5 batches)",
        div,
        "",
        f"  {'Metric':<42} {'GPT-4o':>10} {'Claude':>10}",
        f"  {'-'*62}",
        f"  {'Avg F1 — Friend 1  (diff only)':<42} {og_f1:>10.3f} {oc_f1:>10.3f}",
        f"  {'Avg F1 — Friend 2  (diff + call graph)':<42} {og_f2:>10.3f} {oc_f2:>10.3f}",
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
        "",
        div,
        "",
    ]

    out_path = os.path.join(ROOT, "gpt_vs_claude.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n".join(lines))
    print(f"Comparison saved -> {os.path.relpath(out_path)}")


if __name__ == "__main__":
    main()
