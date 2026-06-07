#!/usr/bin/env python3
"""
Generate thesis charts for GraphGuard evaluation results.
Reads real data from batches/real_world/ automatically.
Outputs PNG files to charts/ directory.

Usage: py -3.12 generate_charts.py
"""

import os, re, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

ROOT    = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "charts")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Palette ───────────────────────────────────────────────────────────────────
C_BASE  = "#E05C2A"
C_GRAPH = "#2E6FBF"
C_AGENT = "#2BA84A"

plt.rcParams.update({
    "font.family":      "DejaVu Sans",
    "axes.spines.top":  False,
    "axes.spines.right":False,
    "axes.grid":        True,
    "grid.alpha":       0.3,
    "grid.linestyle":   "--",
})


def save(fig, name):
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: charts/{name}")


# ── Load real-world results from batch directory ──────────────────────────────

METRICS_RE = re.compile(
    r"TP=(\d+)\s+TN=(\d+)\s+FP=(\d+)\s+FN=(\d+)\s+"
    r"Prec=([0-9.]+)\s+Rec=([0-9.]+)\s+F1=([0-9.]+)\s+Acc=([0-9.]+)"
)

def parse_evaluation(eval_path):
    """Return (f1_base, f1_graph, f1_agent, prec_base, rec_base,
               prec_graph, rec_graph, prec_agent, rec_agent,
               tp_base, fp_base, fn_base, tp_graph, fp_graph, fn_graph,
               tp_agent, fp_agent, fn_agent)
    or None if file is incomplete."""
    if not os.path.isfile(eval_path):
        return None
    text = open(eval_path, encoding="utf-8").read()
    matches = METRICS_RE.findall(text)
    if len(matches) < 2:
        return None
    rows = []
    for m in matches:
        tp, tn, fp, fn, prec, rec, f1, acc = m
        rows.append({
            "TP": int(tp), "TN": int(tn), "FP": int(fp), "FN": int(fn),
            "Prec": float(prec), "Rec": float(rec), "F1": float(f1),
        })
    # rows[0]=base, rows[1]=graph, rows[2]=agent (if present)
    return rows


def load_batch(batch_dir):
    """Load all scenario results from a batch directory.
    Returns list of dicts with keys: name, affected_gt, rows (list per approach)."""
    results = []
    for d in sorted(os.listdir(batch_dir)):
        sd = os.path.join(batch_dir, d)
        if not os.path.isdir(sd):
            continue
        gt_path   = os.path.join(sd, "ground_truth.json")
        eval_path = os.path.join(sd, "evaluation.txt")
        if not os.path.isfile(gt_path) or not os.path.isfile(eval_path):
            continue
        gt   = json.load(open(gt_path, encoding="utf-8"))
        rows = parse_evaluation(eval_path)
        if rows is None:
            continue
        results.append({
            "name":        d,
            "fn":          gt.get("changed_functions", ["?"])[0] if gt.get("changed_functions") else "?",
            "affected_gt": len(gt.get("affected_functions", [])),
            "rows":        rows,   # [base_metrics, graph_metrics, agent_metrics?]
        })
    return results


# ── Synthetic benchmark hardcoded averages (50 projects, GPT-4o) ──────────────
SYN = {"base": 0.531, "graph": 0.981, "agent": 0.980}


# ─────────────────────────────────────────────────────────────────────────────
# CHART 1 — Real-world F1 by scenario (grouped bar, sorted by blast radius)
# ─────────────────────────────────────────────────────────────────────────────
def chart_rw_f1_by_scenario(data):
    # Sort by affected_gt ascending
    data = sorted(data, key=lambda x: x["affected_gt"])

    fn_labels  = [f"{d['fn']}\n(GT={d['affected_gt']})" for d in data]
    f1_base    = [d["rows"][0]["F1"] for d in data]
    f1_graph   = [d["rows"][1]["F1"] for d in data]
    f1_agent   = [d["rows"][2]["F1"] if len(d["rows"]) > 2 else None for d in data]

    n     = len(data)
    x     = np.arange(n)
    has_a = all(v is not None for v in f1_agent)
    width = 0.27 if has_a else 0.38

    fig, ax = plt.subplots(figsize=(max(12, n * 0.85), 5.5))

    b1 = ax.bar(x - width, f1_base,  width, color=C_BASE,  label="Baseline",       zorder=3)
    b2 = ax.bar(x,          f1_graph, width, color=C_GRAPH, label="Context+Graph",  zorder=3)
    if has_a:
        b3 = ax.bar(x + width, f1_agent, width, color=C_AGENT, label="Agent", zorder=3)

    # Avg dashed lines
    ax.axhline(np.mean(f1_base),  color=C_BASE,  linestyle="--", linewidth=1.2, alpha=0.7,
               label=f"Baseline avg {np.mean(f1_base):.3f}")
    ax.axhline(np.mean(f1_graph), color=C_GRAPH, linestyle="-.", linewidth=1.2, alpha=0.7,
               label=f"Context+Graph avg {np.mean(f1_graph):.3f}")
    if has_a:
        ax.axhline(np.mean([v for v in f1_agent if v is not None]),
                   color=C_AGENT, linestyle=":", linewidth=1.2, alpha=0.7,
                   label=f"Agent avg {np.mean([v for v in f1_agent if v is not None]):.3f}")

    ax.set_xticks(x)
    ax.set_xticklabels(fn_labels, fontsize=8)
    ax.set_ylabel("F1 Score", fontsize=11)
    ax.set_ylim(0, 1.18)
    ax.set_title(f"Real-World F1 Scores by Scenario — cJSON ({n} tests, GPT-4o)",
                 fontsize=13, fontweight="bold", pad=12)
    ax.legend(fontsize=8, loc="upper left", ncol=2)
    fig.tight_layout()
    save(fig, "chart1_realworld_f1_by_scenario.png")


# ─────────────────────────────────────────────────────────────────────────────
# CHART 2 — Synthetic benchmark averages
# ─────────────────────────────────────────────────────────────────────────────
def chart_synthetic_averages():
    labels = ["Baseline\n(diff only)", "Context+Graph", "Agent\n(iterative)"]
    values = [SYN["base"], SYN["graph"], SYN["agent"]]
    colors = [C_BASE, C_GRAPH, C_AGENT]

    fig, ax = plt.subplots(figsize=(6, 4.5))
    bars = ax.bar(labels, values, color=colors, width=0.5, zorder=3)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.012,
                f"{val:.3f}", ha="center", va="bottom", fontsize=12, fontweight="bold")

    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Average F1 Score", fontsize=11)
    ax.set_title("Synthetic Benchmark — Average F1\n(GPT-4o, 50 projects)",
                 fontsize=12, fontweight="bold", pad=10)
    fig.tight_layout()
    save(fig, "chart2_synthetic_avg_f1.png")


# ─────────────────────────────────────────────────────────────────────────────
# CHART 3 — Synthetic vs real-world averages side-by-side
# ─────────────────────────────────────────────────────────────────────────────
def chart_synthetic_vs_realworld(data):
    f1b = [d["rows"][0]["F1"] for d in data]
    f1g = [d["rows"][1]["F1"] for d in data]
    f1a = [d["rows"][2]["F1"] for d in data if len(d["rows"]) > 2]

    approaches = ["Baseline", "Context+Graph", "Agent"]
    syn  = [SYN["base"], SYN["graph"], SYN["agent"]]
    real = [np.mean(f1b), np.mean(f1g), np.mean(f1a) if f1a else 0]

    x     = np.arange(len(approaches))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 5))

    b1 = ax.bar(x - width/2, syn,  width, color=["#7BA7D6","#2E6FBF","#1A4D85"],
                label="Synthetic (50 projects)", zorder=3)
    b2 = ax.bar(x + width/2, real, width, color=["#F4A97A","#E05C2A","#A83210"],
                label=f"Real-world cJSON ({len(data)} scenarios)", zorder=3)

    for bars in [b1, b2]:
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.012,
                    f"{h:.3f}", ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(approaches, fontsize=11)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Average F1 Score", fontsize=11)
    ax.set_title("Synthetic vs Real-World Performance per Approach\n(GPT-4o)",
                 fontsize=12, fontweight="bold", pad=10)
    ax.legend(fontsize=10)
    fig.tight_layout()
    save(fig, "chart3_synthetic_vs_realworld.png")


# ─────────────────────────────────────────────────────────────────────────────
# CHART 4 — Agent advantage vs blast radius (scatter)
# ─────────────────────────────────────────────────────────────────────────────
def chart_agent_advantage_vs_blast_radius(data):
    data_a = [d for d in data if len(d["rows"]) > 2]
    gt     = [d["affected_gt"] for d in data_a]
    delta  = [d["rows"][2]["F1"] - d["rows"][1]["F1"] for d in data_a]
    labels = [d["fn"] for d in data_a]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    sc = ax.scatter(gt, delta, c=gt, cmap="RdYlGn", s=110,
                    zorder=4, edgecolors="black", linewidths=0.5)
    for x_, y_, lbl in zip(gt, delta, labels):
        ax.annotate(lbl, (x_, y_), textcoords="offset points", xytext=(7, 4), fontsize=8)

    ax.axhline(0, color="gray", linewidth=0.9, linestyle="--")
    ax.set_xlabel("Number of Transitively Affected Functions (ground truth)", fontsize=11)
    ax.set_ylabel("Agent F1 - Context+Graph F1", fontsize=11)
    ax.set_title("Agent Advantage vs Blast Radius\n(positive = Agent wins, cJSON, GPT-4o)",
                 fontsize=12, fontweight="bold", pad=10)
    cb = plt.colorbar(sc, ax=ax)
    cb.set_label("Affected functions (GT)", fontsize=9)
    fig.tight_layout()
    save(fig, "chart4_agent_advantage_vs_blast_radius.png")


# ─────────────────────────────────────────────────────────────────────────────
# CHART 5 — F1 vs blast radius: all three approaches as lines
# ─────────────────────────────────────────────────────────────────────────────
def chart_f1_vs_blast_radius_lines(data):
    data_s = sorted(data, key=lambda d: d["affected_gt"])
    gt     = [d["affected_gt"] for d in data_s]
    f1b    = [d["rows"][0]["F1"] for d in data_s]
    f1g    = [d["rows"][1]["F1"] for d in data_s]
    f1a    = [d["rows"][2]["F1"] for d in data_s if len(d["rows"]) > 2]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(gt, f1b, "o-", color=C_BASE,  linewidth=1.8, markersize=6, label="Baseline")
    ax.plot(gt, f1g, "s-", color=C_GRAPH, linewidth=1.8, markersize=6, label="Context+Graph")
    if len(f1a) == len(gt):
        ax.plot(gt, f1a, "^-", color=C_AGENT, linewidth=1.8, markersize=6, label="Agent")

    ax.set_xlabel("Transitively Affected Functions (ground truth)", fontsize=11)
    ax.set_ylabel("F1 Score", fontsize=11)
    ax.set_ylim(-0.05, 1.10)
    ax.set_title("F1 Score vs Blast Radius — All Three Approaches\n(cJSON, GPT-4o, sorted by affected count)",
                 fontsize=12, fontweight="bold", pad=10)
    ax.legend(fontsize=10)
    fig.tight_layout()
    save(fig, "chart5_f1_vs_blast_radius_lines.png")


# ─────────────────────────────────────────────────────────────────────────────
# CHART 6 — Precision vs Recall scatter (real-world)
# ─────────────────────────────────────────────────────────────────────────────
def chart_precision_recall(data):
    fig, ax = plt.subplots(figsize=(6.5, 6.5))

    configs = [
        (0, C_BASE,  "o", "Baseline"),
        (1, C_GRAPH, "s", "Context+Graph"),
        (2, C_AGENT, "^", "Agent"),
    ]
    for idx, col, marker, label in configs:
        pts = [(d["rows"][idx]["Prec"], d["rows"][idx]["Rec"])
               for d in data if len(d["rows"]) > idx]
        if pts:
            px, py = zip(*pts)
            ax.scatter(px, py, c=col, marker=marker, s=80, label=label,
                       zorder=4, edgecolors="white", linewidths=0.5)

    ax.plot([0, 1], [0, 1], "k--", linewidth=0.8, alpha=0.4)
    ax.set_xlim(-0.05, 1.10)
    ax.set_ylim(-0.05, 1.10)
    ax.set_xlabel("Precision", fontsize=11)
    ax.set_ylabel("Recall", fontsize=11)
    ax.set_title("Precision vs Recall — Real-World cJSON Scenarios\n(GPT-4o, all scenarios)",
                 fontsize=12, fontweight="bold", pad=10)
    ax.legend(fontsize=10)
    fig.tight_layout()
    save(fig, "chart6_precision_recall_scatter.png")


# ─────────────────────────────────────────────────────────────────────────────
# CHART 7 — Cumulative TP/FP/FN bar (stacked, summed across all scenarios)
# ─────────────────────────────────────────────────────────────────────────────
def chart_tp_fp_fn(data):
    totals = {"Baseline": {"TP":0,"FP":0,"FN":0},
              "Context+Graph": {"TP":0,"FP":0,"FN":0},
              "Agent": {"TP":0,"FP":0,"FN":0}}
    keys = list(totals.keys())
    for d in data:
        for i, k in enumerate(keys):
            if i < len(d["rows"]):
                totals[k]["TP"] += d["rows"][i]["TP"]
                totals[k]["FP"] += d["rows"][i]["FP"]
                totals[k]["FN"] += d["rows"][i]["FN"]

    labels  = keys
    tp_vals = [totals[k]["TP"] for k in labels]
    fp_vals = [totals[k]["FP"] for k in labels]
    fn_vals = [totals[k]["FN"] for k in labels]

    x     = np.arange(len(labels))
    width = 0.45
    fig, ax = plt.subplots(figsize=(7, 5))

    ax.bar(x, tp_vals, width, label="True Positives",   color="#2BA84A", zorder=3)
    ax.bar(x, fp_vals, width, bottom=tp_vals, label="False Positives", color="#E05C2A", zorder=3)
    fn_bot = [t+f for t,f in zip(tp_vals, fp_vals)]
    ax.bar(x, fn_vals, width, bottom=fn_bot, label="False Negatives",  color="#AAA", zorder=3)

    for i, (tp, fp, fn) in enumerate(zip(tp_vals, fp_vals, fn_vals)):
        ax.text(i, tp+fp+fn+0.5, f"Total={tp+fp+fn}", ha="center", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel(f"Function count (summed, {len(data)} scenarios)", fontsize=10)
    ax.set_title("Classification Breakdown — Real-World cJSON\n(Summed across all scenarios, GPT-4o)",
                 fontsize=12, fontweight="bold", pad=10)
    ax.legend(fontsize=9)
    fig.tight_layout()
    save(fig, "chart7_tp_fp_fn_breakdown.png")


# ─────────────────────────────────────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    batch_dir = os.path.join(ROOT, "batches", "real_world")
    data = load_batch(batch_dir)
    print(f"Loaded {len(data)} scenarios from {os.path.relpath(batch_dir)}")
    for d in data:
        n_rows = len(d["rows"])
        f1s = [f"{r['F1']:.3f}" for r in d["rows"]]
        print(f"  {d['name']:<42} GT={d['affected_gt']:>2}  F1={f1s}")

    print("\nGenerating charts...")
    chart_rw_f1_by_scenario(data)
    chart_synthetic_averages()
    chart_synthetic_vs_realworld(data)
    chart_agent_advantage_vs_blast_radius(data)
    chart_f1_vs_blast_radius_lines(data)
    chart_precision_recall(data)
    chart_tp_fp_fn(data)
    print(f"\nAll charts saved to: charts/")
