#!/usr/bin/env python3
"""
Figure 5 — Vision Agent self-consistency (Experiment 3).

Two panels:
  (a) Pairwise Jaccard heatmap across N runs (8×8 matrix on the fixed LID).
  (b) Per-run timeline: runtime + chemistry-validator drops.
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

RES = HERE.parent / "experiments/exp3_vision_consistency/results"
OUT_DIR = HERE / "out"


def load_runs():
    runs = []
    for p in sorted(RES.glob("run_*.json")):
        with open(p) as f:
            runs.append(json.load(f))
    with open(RES / "summary.json") as f:
        summ = json.load(f)
    return runs, summ


def keys_for(run):
    s = set()
    if not run.get("ok"):
        return s
    for g in run["output"]["restricted_groups"]:
        if g.get("atom_indices"):
            for a in g["atom_indices"]:
                s.add(("atom", a))
        else:
            residues = g.get("residues") or ([g["residue"]] if g.get("residue") else [])
            s.add(("name", g["group_name"], tuple(sorted(residues))))
    return s


def panel_a_jaccard_heatmap(ax, runs, summ):
    ok_runs = [r for r in runs if r.get("ok")]
    n = len(ok_runs)
    sets = [keys_for(r) for r in ok_runs]
    matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            inter = len(sets[i] & sets[j])
            union = len(sets[i] | sets[j])
            matrix[i, j] = inter / union if union else 1.0

    im = ax.imshow(matrix, vmin=0, vmax=1, cmap="Blues")
    for i in range(n):
        for j in range(n):
            ax.text(j, i, f"{matrix[i,j]:.2f}", ha="center", va="center", fontsize=8,
                    color="white" if matrix[i,j] > 0.5 else PAPER_COLORS["ink"])
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels([f"r{i+1}" for i in range(n)])
    ax.set_yticklabels([f"r{i+1}" for i in range(n)])
    ax.set_title(f"(a)  Pairwise Jaccard, restricted atom-set ({n}×{n}; mean={summ['mean_jaccard_pairwise']:.2f})", loc="left")
    cbar = plt.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cbar.set_label("Jaccard similarity", fontsize=9)
    cbar.ax.tick_params(labelsize=8)


def panel_b_per_run(ax, runs):
    ok_runs = [r for r in runs if r.get("ok")]
    n = len(ok_runs)
    idx = np.arange(n)
    runtimes = [r["runtime_s"] for r in ok_runs]
    drops = [r["drops_hallucinated"] + r["drops_chem_invalid"] for r in ok_runs]

    ax.bar(idx - 0.18, runtimes, width=0.36, color=PAPER_COLORS["accent_soft"],
           edgecolor=PAPER_COLORS["accent"], lw=0.6, label="Runtime (s)")
    ax2 = ax.twinx()
    ax2.bar(idx + 0.18, drops, width=0.36, color=PAPER_COLORS["defence_soft"],
            edgecolor=PAPER_COLORS["defence"], lw=0.6, label="Chemistry-validator drops")

    ax.set_xticks(idx)
    ax.set_xticklabels([f"r{i+1}" for i in range(n)])
    ax.set_ylabel("Runtime (s)", color=PAPER_COLORS["accent"])
    ax.tick_params(axis="y", colors=PAPER_COLORS["accent"])
    ax.set_ylim(0, max(runtimes) * 1.4)
    ax2.set_ylabel("Validator drops", color=PAPER_COLORS["defence"])
    ax2.tick_params(axis="y", colors=PAPER_COLORS["defence"])
    ax2.set_ylim(0, max(max(drops), 1) * 4 + 1)
    ax2.spines["top"].set_visible(False)
    ax.set_title("(b)  Per-run: runtime + chemistry-validator drop count", loc="left")
    ax.grid(False)

    # Combined legend
    from matplotlib.patches import Patch
    handles = [
        Patch(facecolor=PAPER_COLORS["accent_soft"], edgecolor=PAPER_COLORS["accent"], label="Runtime (s, left axis)"),
        Patch(facecolor=PAPER_COLORS["defence_soft"], edgecolor=PAPER_COLORS["defence"], label="Validator drops (right axis)"),
    ]
    ax.legend(handles=handles, loc="upper right", frameon=False)


def main():
    apply_paper_style()
    runs, summ = load_runs()

    fig = plt.figure(figsize=(12.5, 5.4))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.0], wspace=0.30)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    panel_a_jaccard_heatmap(ax_a, runs, summ)
    panel_b_per_run(ax_b, runs)

    fig.suptitle(
        "Figure 5 — Vision Agent self-consistency on a fixed LID, N=8 runs",
        x=0.06, y=0.985, ha="left", fontsize=12.5, weight="bold",
    )
    fig.text(
        0.06, 0.94,
        f"DYRK1A Compound 25014 LID image (348 KB). Mean runtime "
        f"{summ['runtime_stat']['mean']:.1f} ± {summ['runtime_stat']['std']:.2f} s per run; "
        f"consensus restricted-atom set size = {summ['consensus_keys_present_in_all']}.",
        ha="left", fontsize=9, style="italic", color=PAPER_COLORS["ink_soft"],
    )

    paths = save(fig, OUT_DIR, "fig4_vision_consistency")
    for p in paths:
        print(f"wrote {p}")
    plt.close(fig)


if __name__ == "__main__":
    main()
