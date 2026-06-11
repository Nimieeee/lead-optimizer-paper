#!/usr/bin/env python3
"""
Figure 2, MMP recovery on the curated pilot and the unbiased ChEMBL scale-up.

Three panels:
  (a) Per-pair recovery on the curated pilot (30 pairs), best-Tanimoto bars,
      colour-coded by hit / miss-with-analogs / zero-analog gap.
  (b) Pilot vs ChEMBL exact-recovery comparison, bar chart with rate + Tanimoto.
  (c) ChEMBL best-Tanimoto histogram across 2000 unbiased pairs, surfaces that
      the engine produces close alternatives in most misses (median Tanimoto 0.75).
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _style import PAPER_COLORS, apply_paper_style, save

PILOT_DIR = HERE.parent / "experiments/exp1_mmp_recovery/results/pilot"
CHEMBL_DIR = HERE.parent / "experiments/exp1_mmp_recovery/results/chembl_2k"
OUT_DIR = HERE / "out"


def load():
    pilot_rows = []
    with open(PILOT_DIR / "per_pair.csv") as f:
        for r in csv.DictReader(f):
            r["B_recovered_exact"] = r["B_recovered_exact"] == "True"
            r["best_tanimoto"] = float(r["best_tanimoto"])
            r["unique_analogs"] = int(r["unique_analogs"])
            pilot_rows.append(r)
    pilot_summary = json.loads((PILOT_DIR / "summary.json").read_text())

    chembl_rows = []
    chembl_csv = CHEMBL_DIR / "per_pair.csv"
    if chembl_csv.exists():
        with open(chembl_csv) as f:
            for r in csv.DictReader(f):
                chembl_rows.append({
                    "B_recovered_exact": r["B_recovered_exact"] == "True",
                    "best_tanimoto": float(r["best_tanimoto"]),
                })
    chembl_summary = json.loads((CHEMBL_DIR / "summary.json").read_text()) if (CHEMBL_DIR / "summary.json").exists() else None

    return pilot_rows, pilot_summary, chembl_rows, chembl_summary


def panel_a(ax, pilot_summary, chembl_summary):
    """Recall@K curves, pilot and ChEMBL on the same axes."""
    ks = sorted(int(k) for k in pilot_summary["recall_at_k"])
    p_rec = [pilot_summary["recall_at_k"][str(k)] * 100 for k in ks]
    ax.plot(ks, p_rec, "-o", color=PAPER_COLORS["accent"], lw=1.5, ms=5,
            label=f"Pilot (curated, $n={pilot_summary['n_pairs']}$): {pilot_summary['any_recovery_rate']*100:.1f}%")
    if chembl_summary:
        c_rec = [chembl_summary["recall_at_k"][str(k)] * 100 for k in ks]
        ax.plot(ks, c_rec, "-s", color=PAPER_COLORS["substrate"], lw=1.5, ms=5,
                label=f"ChEMBL-37 (unbiased, $n={chembl_summary['n_pairs']:,}$): {chembl_summary['any_recovery_rate']*100:.1f}%")
    ax.set_xscale("log")
    ax.set_xticks(ks)
    ax.set_xticklabels([str(k) for k in ks])
    ax.set_ylim(0, 70)
    ax.set_xlim(ks[0] * 0.7, ks[-1] * 1.4)
    ax.set_xlabel("Rank cutoff $K$ (Tanimoto-to-$B$ rank)")
    ax.set_ylabel("Recall@$K$ (%)")
    ax.set_title("(a)  Recall@$K$ on the two evaluation sets", loc="left")
    ax.text(
        ks[1], 56,
        "Curves are flat: exact recoveries canonicalise to Tanimoto $=1.0$, always at rank 1",
        fontsize=8, color=PAPER_COLORS["ink_faint"], style="italic",
    )
    ax.legend(loc="upper right", fontsize=8.5, frameon=False)
    ax.grid(True, axis="y", alpha=0.3)


def panel_c_chembl_tanimoto(ax, chembl_rows, chembl_summary):
    """Histogram of best-Tanimoto across all 2000 ChEMBL pairs."""
    if not chembl_rows:
        ax.text(0.5, 0.5, "ChEMBL results not yet available", ha="center", va="center",
                transform=ax.transAxes, fontsize=10, color=PAPER_COLORS["ink_faint"])
        ax.set_axis_off()
        return
    tans = np.array([r["best_tanimoto"] for r in chembl_rows])
    recovered = np.array([r["B_recovered_exact"] for r in chembl_rows])

    bins = np.linspace(0, 1.0, 41)
    ax.hist(tans[~recovered], bins=bins, color=PAPER_COLORS["substrate_soft"],
            edgecolor=PAPER_COLORS["substrate"], lw=0.5, label=f"Miss ($n={(~recovered).sum():,}$)")
    ax.hist(tans[recovered], bins=bins, color=PAPER_COLORS["accent_soft"],
            edgecolor=PAPER_COLORS["accent"], lw=0.5,
            bottom=np.histogram(tans[~recovered], bins=bins)[0],
            label=f"Exact recovery ($n={recovered.sum():,}$)")

    ax.axvline(float(chembl_summary["mean_best_tanimoto"]), color=PAPER_COLORS["ink"], lw=0.8, ls="--")
    ax.text(float(chembl_summary["mean_best_tanimoto"]) - 0.02,
            ax.get_ylim()[1] * 0.92 if ax.get_ylim()[1] > 0 else 100,
            f"mean = {chembl_summary['mean_best_tanimoto']:.2f}",
            ha="right", fontsize=9, color=PAPER_COLORS["ink"], rotation=0)

    ax.set_xlabel("Best Tanimoto to target $B$")
    ax.set_ylabel("Count of ChEMBL pairs")
    ax.set_title("(c)  ChEMBL pairs, best-Tanimoto distribution", loc="left")
    ax.set_xlim(0, 1.02)
    ax.legend(loc="upper left", fontsize=8.5, frameon=False)
    ax.grid(True, axis="y", alpha=0.25)


def panel_b(ax, rows):
    """Per-pair best-Tanimoto bar, hits in accent, misses in critical, zero-analog in faint."""
    rows_sorted = sorted(rows, key=lambda r: (not r["B_recovered_exact"], -r["best_tanimoto"]))
    labels = [r["transformation"] for r in rows_sorted]
    tans = [r["best_tanimoto"] for r in rows_sorted]
    colors = []
    for r in rows_sorted:
        if r["B_recovered_exact"]:
            colors.append(PAPER_COLORS["accent"])
        elif r["unique_analogs"] == 0:
            colors.append(PAPER_COLORS["critical"])
        else:
            colors.append(PAPER_COLORS["substrate"])

    y = np.arange(len(rows_sorted))
    ax.barh(y, tans, color=colors, edgecolor=PAPER_COLORS["ink_soft"], lw=0.3, height=0.7)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7.5)
    ax.set_xlabel("Best Tanimoto to target $B$ in generated analog set")
    ax.set_xlim(0, 1.05)
    ax.set_title("(b)  Per-pair recovery, pilot MMP set", loc="left")
    ax.invert_yaxis()
    ax.axvline(1.0, color=PAPER_COLORS["ink_faint"], lw=0.5, ls=":")
    ax.grid(True, axis="x", alpha=0.3)

    # legend
    from matplotlib.patches import Patch

    handles = [
        Patch(facecolor=PAPER_COLORS["accent"], label="$B$ recovered exactly (Tanimoto = 1)"),
        Patch(facecolor=PAPER_COLORS["substrate"], label="Analogs produced, $B$ not in set"),
        Patch(facecolor=PAPER_COLORS["critical"], label="Zero analogs (library coverage gap)"),
    ]
    ax.legend(handles=handles, loc="lower right", framealpha=0.9, edgecolor="none")


def main():
    apply_paper_style()
    pilot_rows, pilot_summary, chembl_rows, chembl_summary = load()

    fig = plt.figure(figsize=(15.5, 7.0))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.45, 1.10], wspace=0.34)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])
    panel_a(ax_a, pilot_summary, chembl_summary)
    panel_b(ax_b, pilot_rows)
    panel_c_chembl_tanimoto(ax_c, chembl_rows, chembl_summary)

    fig.suptitle(
        "Figure 2, MMP recovery on curated and unbiased evaluation sets",
        x=0.06, y=0.985, ha="left", fontsize=12.5, weight="bold",
    )
    chembl_n = chembl_summary["n_pairs"] if chembl_summary else ","
    fig.text(
        0.06, 0.945,
        f"Pilot: 30 literature-documented single-edit pairs (upper bound on the library's native domain). "
        f"ChEMBL-37 scale-up: {chembl_n:,} unbiased single-edit pairs from a 2000-compound drug-like subset, "
        f"built via mmpdb fragment + index. Library = 479 SMIRKS / 22 categories.",
        ha="left", fontsize=9, style="italic", color=PAPER_COLORS["ink_soft"],
    )

    paths = save(fig, OUT_DIR, "fig2_mmp_recovery")
    for p in paths:
        print(f"wrote {p}")
    plt.close(fig)


if __name__ == "__main__":
    main()
