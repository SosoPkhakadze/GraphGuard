#!/usr/bin/env python3
"""
Generate thesis charts for GraphGuard evaluation results.
Outputs PNG files to charts/ directory.

Usage: py -3.12 generate_charts.py
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Palette ───────────────────────────────────────────────────────────────────
C_BASE   = "#E05C2A"   # red-orange  — Baseline
C_GRAPH  = "#2E6FBF"   # blue        — Context+Graph
C_AGENT  = "#2BA84A"   # green       — Agent

FONT = "DejaVu Sans"
plt.rcParams.update({
    "font.family":      FONT,
    "axes.spines.top":  False,
    "axes.spines.right":False,
    "axes.grid":        True,
    "grid.alpha":       0.35,
    "grid.linestyle":   "--",
})


def save(fig, name):
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: charts/{name}")


# ─────────────────────────────────────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────────────────────────────────────

# Real-world cJSON (5 scenarios)
rw_scenarios    = ["ensure", "parse_number", "cJSON_strdup",
                   "cJSON_GetObjectItem", "print_value"]
rw_affected_gt  = [11, 7, 22, 3, 7]
rw_baseline     = [0.000, 0.364, 0.083, 0.286, 0.545]
rw_graph        = [0.667, 0.933, 0.467, 0.667, 0.545]
rw_agent        = [0.667, 0.933, 0.905, 0.750, 0.667]

# Synthetic benchmark (50 projects) — averages
syn_baseline = 0.531
syn_graph    = 0.981
syn_agent    = 0.980

# Per-scenario precision / recall for real-world
rw_prec_base  = [0.000, 0.667, 1.000, 0.333, 1.000]
rw_rec_base   = [0.000, 0.250, 0.043, 0.250, 0.375]
rw_prec_graph = [1.000, 1.000, 1.000, 0.600, 1.000]
rw_rec_graph  = [0.500, 0.875, 0.304, 0.750, 0.375]
rw_prec_agent = [1.000, 1.000, 1.000, 0.750, 1.000]
rw_rec_agent  = [0.500, 0.875, 0.826, 0.750, 0.500]


# ─────────────────────────────────────────────────────────────────────────────
# CHART 1 — Real-world F1 by scenario (grouped bar)
# ─────────────────────────────────────────────────────────────────────────────
def chart_rw_f1_by_scenario():
    x      = np.arange(len(rw_scenarios))
    width  = 0.25
    fig, ax = plt.subplots(figsize=(10, 5.5))

    b1 = ax.bar(x - width, rw_baseline, width, color=C_BASE,   label="Baseline (diff only)",  zorder=3)
    b2 = ax.bar(x,          rw_graph,   width, color=C_GRAPH,  label="Context+Graph",          zorder=3)
    b3 = ax.bar(x + width,  rw_agent,   width, color=C_AGENT,  label="Agent (iterative)",      zorder=3)

    # Avg lines
    avgs = [
        (np.mean(rw_baseline), C_BASE,  "--"),
        (np.mean(rw_graph),    C_GRAPH, "-."),
        (np.mean(rw_agent),    C_AGENT, ":"),
    ]
    labels_done = set()
    for val, col, ls in avgs:
        lbl = f"avg = {val:.3f}" if val not in labels_done else None
        ax.axhline(val, color=col, linestyle=ls, linewidth=1.3, alpha=0.7)
        labels_done.add(val)

    ax.set_xticks(x)
    ax.set_xticklabels(rw_scenarios, fontsize=10)
    ax.set_ylabel("F1 Score", fontsize=11)
    ax.set_ylim(0, 1.08)
    ax.set_title("Real-World F1 Scores by Scenario (cJSON, GPT-4o)", fontsize=13, fontweight="bold", pad=12)
    ax.legend(fontsize=10, loc="upper left")

    # Annotate bars with value
    for bars in [b1, b2, b3]:
        for bar in bars:
            h = bar.get_height()
            if h > 0.01:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.015,
                        f"{h:.3f}", ha="center", va="bottom", fontsize=7.5)

    # Annotate GT affected count above x-axis
    for i, (sc, n) in enumerate(zip(rw_scenarios, rw_affected_gt)):
        ax.text(i, -0.07, f"GT={n}", ha="center", va="top", fontsize=8,
                color="#555", transform=ax.get_xaxis_transform())

    fig.tight_layout()
    save(fig, "chart1_realworld_f1_by_scenario.png")


# ─────────────────────────────────────────────────────────────────────────────
# CHART 2 — Synthetic benchmark averages (simple bar)
# ─────────────────────────────────────────────────────────────────────────────
def chart_synthetic_averages():
    labels = ["Baseline\n(diff only)", "Context+Graph", "Agent\n(iterative)"]
    values = [syn_baseline, syn_graph, syn_agent]
    colors = [C_BASE, C_GRAPH, C_AGENT]

    fig, ax = plt.subplots(figsize=(6, 4.5))
    bars = ax.bar(labels, values, color=colors, width=0.5, zorder=3)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.012,
                f"{val:.3f}", ha="center", va="bottom", fontsize=12, fontweight="bold")

    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Average F1 Score (50 projects)", fontsize=11)
    ax.set_title("Synthetic Benchmark — Average F1 per Approach\n(GPT-4o, 50 projects)",
                 fontsize=12, fontweight="bold", pad=10)
    fig.tight_layout()
    save(fig, "chart2_synthetic_avg_f1.png")


# ─────────────────────────────────────────────────────────────────────────────
# CHART 3 — Side-by-side: synthetic avg vs real-world avg
# ─────────────────────────────────────────────────────────────────────────────
def chart_synthetic_vs_realworld():
    approaches = ["Baseline", "Context+Graph", "Agent"]
    syn   = [syn_baseline, syn_graph, syn_agent]
    real  = [np.mean(rw_baseline), np.mean(rw_graph), np.mean(rw_agent)]

    x     = np.arange(len(approaches))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 5))

    b1 = ax.bar(x - width/2, syn,  width, color=["#7BA7D6","#2E6FBF","#1A4D85"], label="Synthetic (50 projects)", zorder=3)
    b2 = ax.bar(x + width/2, real, width, color=["#F4A97A","#E05C2A","#A83210"], label="Real-world (cJSON)",       zorder=3)

    for bars in [b1, b2]:
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.012,
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
# CHART 4 — Precision vs Recall scatter (real-world, all scenarios)
# ─────────────────────────────────────────────────────────────────────────────
def chart_precision_recall_scatter():
    fig, ax = plt.subplots(figsize=(6, 6))

    scatter_data = [
        (rw_prec_base,  rw_rec_base,  C_BASE,  "Baseline",      "o"),
        (rw_prec_graph, rw_rec_graph, C_GRAPH, "Context+Graph", "s"),
        (rw_prec_agent, rw_rec_agent, C_AGENT, "Agent",         "^"),
    ]

    for precs, recs, col, label, marker in scatter_data:
        ax.scatter(precs, recs, c=col, marker=marker, s=90, label=label,
                   zorder=4, edgecolors="white", linewidths=0.5)
        # Annotate each point with scenario name
        for p, r, sc in zip(precs, recs, rw_scenarios):
            ax.annotate(sc, (p, r), textcoords="offset points",
                        xytext=(6, 4), fontsize=7, color=col, alpha=0.85)

    # Diagonal reference
    ax.plot([0, 1], [0, 1], "k--", linewidth=0.8, alpha=0.4, label="P = R")

    ax.set_xlim(-0.05, 1.10)
    ax.set_ylim(-0.05, 1.10)
    ax.set_xlabel("Precision", fontsize=11)
    ax.set_ylabel("Recall", fontsize=11)
    ax.set_title("Precision vs Recall — Real-World cJSON Scenarios\n(GPT-4o)",
                 fontsize=12, fontweight="bold", pad=10)
    ax.legend(fontsize=10)
    fig.tight_layout()
    save(fig, "chart4_precision_recall_scatter.png")


# ─────────────────────────────────────────────────────────────────────────────
# CHART 5 — Agent advantage vs affected count (scatter)
# Shows that agent advantage grows with blast radius
# ─────────────────────────────────────────────────────────────────────────────
def chart_agent_advantage_vs_blast_radius():
    delta_agent_vs_graph = [a - g for a, g in zip(rw_agent, rw_graph)]

    fig, ax = plt.subplots(figsize=(7, 5))
    sc = ax.scatter(rw_affected_gt, delta_agent_vs_graph,
                    c=rw_affected_gt, cmap="RdYlGn", s=120,
                    zorder=4, edgecolors="black", linewidths=0.5)

    for x, y, name in zip(rw_affected_gt, delta_agent_vs_graph, rw_scenarios):
        ax.annotate(name, (x, y), textcoords="offset points",
                    xytext=(8, 4), fontsize=9)

    ax.axhline(0, color="gray", linewidth=0.9, linestyle="--")
    ax.set_xlabel("Number of Transitively Affected Functions (ground truth)", fontsize=11)
    ax.set_ylabel("Agent F1 - Context+Graph F1", fontsize=11)
    ax.set_title("Agent Advantage vs Blast Radius\n(positive = Agent wins)",
                 fontsize=12, fontweight="bold", pad=10)

    cb = plt.colorbar(sc, ax=ax)
    cb.set_label("Affected functions (GT)", fontsize=9)
    fig.tight_layout()
    save(fig, "chart5_agent_advantage_vs_blast_radius.png")


# ─────────────────────────────────────────────────────────────────────────────
# CHART 6 — Stacked bar: TP / FP / FN breakdown per approach (real-world avg)
# ─────────────────────────────────────────────────────────────────────────────
def chart_tp_fp_fn_breakdown():
    # Real-world totals across 5 scenarios
    # From batch_results.txt
    data = {
        "Baseline":      {"TP": 0+2+1+1+3, "FP": 2+1+0+2+0, "FN": 12+6+22+3+5},
        "Context+Graph": {"TP": 6+7+7+3+3, "FP": 0+0+0+2+0, "FN": 6+1+16+1+5},
        "Agent":         {"TP": 6+7+19+3+4,"FP": 0+0+0+1+0, "FN": 6+1+4+1+4},
    }

    labels   = list(data.keys())
    tp_vals  = [data[l]["TP"] for l in labels]
    fp_vals  = [data[l]["FP"] for l in labels]
    fn_vals  = [data[l]["FN"] for l in labels]

    x     = np.arange(len(labels))
    width = 0.45
    fig, ax = plt.subplots(figsize=(7, 5))

    p1 = ax.bar(x, tp_vals, width, label="True Positives (correct)",  color="#2BA84A", zorder=3)
    p2 = ax.bar(x, fp_vals, width, bottom=tp_vals, label="False Positives (false alarms)", color="#E05C2A", zorder=3)
    fn_bottom = [t + f for t, f in zip(tp_vals, fp_vals)]
    p3 = ax.bar(x, fn_vals, width, bottom=fn_bottom, label="False Negatives (missed)",    color="#999", zorder=3)

    for i, (tp, fp, fn) in enumerate(zip(tp_vals, fp_vals, fn_vals)):
        total = tp + fp + fn
        ax.text(i, total + 0.5, f"Total={total}", ha="center", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel("Function Count (summed across 5 scenarios)", fontsize=10)
    ax.set_title("Classification Breakdown — Real-World cJSON\n(Summed across 5 scenarios, GPT-4o)",
                 fontsize=12, fontweight="bold", pad=10)
    ax.legend(fontsize=9)
    fig.tight_layout()
    save(fig, "chart6_tp_fp_fn_breakdown.png")


# ─────────────────────────────────────────────────────────────────────────────
# RUN ALL
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Generating thesis charts...")
    chart_rw_f1_by_scenario()
    chart_synthetic_averages()
    chart_synthetic_vs_realworld()
    chart_precision_recall_scatter()
    chart_agent_advantage_vs_blast_radius()
    chart_tp_fp_fn_breakdown()
    print(f"\nAll charts saved to: charts/")
    print("Files:")
    for f in sorted(os.listdir(OUT_DIR)):
        if f.endswith(".png"):
            print(f"  {f}")
