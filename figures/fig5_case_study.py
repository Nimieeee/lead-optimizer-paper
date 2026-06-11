#!/usr/bin/env python3
"""
Figure 4, End-to-end case study (Experiment 4).

Two panels:
  (a) Stage-by-stage attrition funnel for each case (DYRK1A + Linezolid).
  (b) Top-10 analog scatter: pareto_score vs SA score, color-coded by case.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _style import PAPER_COLORS, apply_paper_style, save

RESULTS = HERE.parent / "experiments/exp4_case_study/results/summary.json"
OUT_DIR = HERE / "out"


def load():
    with open(RESULTS) as f:
        return json.load(f)


def panel_a_attrition(ax, data):
    """Horizontal funnel: 5 stage labels, bar lengths = count per case."""
    stages = [
        ("Strategies\nproposed", "total_strategies_proposed"),
        ("Analogs\ngenerated", "total_analogs_generated"),
        ("After\npre-filter", "total_passed_prefilter"),
        ("After\nADMET screen", "total_passed_admet"),
        ("Diversity\nclusters", "diversity_clusters_after_ranking"),
    ]
    case_color = {"CASE_001": PAPER_COLORS["accent"], "CASE_002": PAPER_COLORS["substrate"]}
    case_label = {
        "CASE_001": "DYRK1A series\n(Compound 25014)",
        "CASE_002": "Linezolid\n(oxazolidinone)",
    }

    n_stages = len(stages)
    n_cases = len(data["cases"])
    bar_h = 0.36

    y_centers = np.arange(n_stages)
    for i, c in enumerate(data["cases"]):
        if "pipeline_attrition" not in c:
            continue
        values = [c["pipeline_attrition"].get(k, 0) for _, k in stages]
        offset = (i - (n_cases - 1) / 2) * (bar_h + 0.04)
        bars = ax.barh(
            y_centers + offset, values, bar_h,
            color=case_color.get(c["case_id"], PAPER_COLORS["ink"]),
            edgecolor=PAPER_COLORS["ink"], lw=0.4, label=case_label.get(c["case_id"], c["case_id"]),
        )
        for y, v in zip(y_centers + offset, values):
            ax.text(v + max(values) * 0.015, y, str(v), va="center", fontsize=8.5, color=PAPER_COLORS["ink"])

    ax.set_yticks(y_centers)
    ax.set_yticklabels([s[0] for s in stages], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Count")
    ax.set_title("(a)  Stage-by-stage attrition through the 12-stage pipeline", loc="left")
    ax.legend(loc="lower right", frameon=False)
    ax.grid(True, axis="x", alpha=0.25)


def panel_b_top10(ax, data):
    """pareto_score vs SA score for the top-10 per case, colour by case."""
    case_color = {"CASE_001": PAPER_COLORS["accent"], "CASE_002": PAPER_COLORS["substrate"]}
    case_marker = {"CASE_001": "o", "CASE_002": "s"}
    case_label = {
        "CASE_001": "DYRK1A series\n(Compound 25014)",
        "CASE_002": "Linezolid\n(oxazolidinone)",
    }
    for c in data["cases"]:
        if "top_analogs_top10" not in c:
            continue
        xs = [a["sa_score"] for a in c["top_analogs_top10"]]
        ys = [a["pareto_score"] for a in c["top_analogs_top10"]]
        ranks = [a["pareto_rank"] for a in c["top_analogs_top10"]]
        ax.scatter(
            xs, ys, s=70, alpha=0.85,
            marker=case_marker[c["case_id"]],
            edgecolor=PAPER_COLORS["ink"], lw=0.6,
            facecolor=case_color[c["case_id"]],
            label=case_label[c["case_id"]],
        )
        # rank-1 callout per case
        if xs and ys:
            ax.annotate(
                f"  rank 1", (xs[0], ys[0]),
                fontsize=8, color=PAPER_COLORS["ink_soft"],
                xytext=(6, -3), textcoords="offset points",
            )

    ax.set_xlabel("SA score (Ertl, lower = easier)")
    ax.set_ylabel("Total-score (sorted weighted scalar; higher = better rank)")
    ax.set_title("(b)  Top-10 per case, total-score vs synthetic accessibility", loc="left")
    ax.legend(loc="lower left", frameon=False)
    ax.grid(True, alpha=0.25)


def main():
    apply_paper_style()
    data = load()

    fig = plt.figure(figsize=(13, 5.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.0], wspace=0.30)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    panel_a_attrition(ax_a, data)
    panel_b_top10(ax_b, data)

    fig.suptitle(
        "Figure 4, End-to-end case study: pipeline attrition + top-K analog metrics",
        x=0.06, y=0.985, ha="left", fontsize=12.5, weight="bold",
    )
    runtimes = "; ".join(f"{c['case_id']}: {c.get('runtime_s', ',')}s" for c in data["cases"])
    fig.text(
        0.06, 0.94,
        f"Two leads, no-LID path (every functional group classified as TARGET). Wall-clock per case: {runtimes}.",
        ha="left", fontsize=9, style="italic", color=PAPER_COLORS["ink_soft"],
    )

    paths = save(fig, OUT_DIR, "fig5_case_study")
    for p in paths:
        print(f"wrote {p}")
    plt.close(fig)


if __name__ == "__main__":
    main()
