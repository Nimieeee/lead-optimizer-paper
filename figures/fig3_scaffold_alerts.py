#!/usr/bin/env python3
"""
Figure 3 — Scaffold preservation + structural-alert audit (Exp 2).

Three panels:
  (a) Stacked bar comparing seed baseline, ablation (gate off), and default (gate on)
      across PAINS / Brenk / clean.
  (b) Scaffold preservation rate: default vs ablation.
  (c) Property-shift distributions (HA delta, LogP delta) under default condition.
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
from _style import PAPER_COLORS, PAPER_PALETTE, apply_paper_style, save

RESULTS_DIR = HERE.parent / "experiments/exp2_scaffold_alerts/results/drugpool_129"
OUT_DIR = HERE / "out"

# Seed baseline numbers — recomputed by run_seed_baseline.py
# (or hard-coded here as constants matching the verified compute)
SEED_BASELINE = {"pains_pct": 5.0, "brenk_pct": 26.1, "clean_pct": 70.6}


def load():
    with open(RESULTS_DIR / "summary.json") as f:
        summ = json.load(f)
    per_analog = []
    with open(RESULTS_DIR / "per_analog.csv") as f:
        for r in csv.DictReader(f):
            r["has_pains"] = r["has_pains"] == "True"
            r["has_brenk"] = r["has_brenk"] == "True"
            r["scaffold_preserved"] = r["scaffold_preserved"] == "True"
            r["heavy_atom_delta"] = int(r["heavy_atom_delta"])
            r["logp_delta"] = float(r["logp_delta"])
            per_analog.append(r)
    return summ, per_analog


def panel_a_structural_alerts(ax, summ):
    """Stacked bar: PAINS-flagged, Brenk-only, clean. Conditions on x-axis."""
    cond_keys = [
        ("Seed compounds\n($n=119$)", SEED_BASELINE),
        (
            "Ablation\n(Murcko gate OFF)",
            summ["conditions"]["ablation_murcko_gate_off"],
        ),
        (
            "Default\n(Murcko gate ON)",
            summ["conditions"]["default_murcko_gate_on"],
        ),
    ]

    def fractions(c):
        if "pains_pct" in c:  # seed baseline
            p = c["pains_pct"]
            b = c["brenk_pct"]
            # PAINS and Brenk can overlap; for stacking we approximate:
            # bottom = clean, middle = Brenk-only (no PAINS), top = any PAINS.
            clean = c["clean_pct"]
            return clean, max(0, b), p
        else:
            p = c["pct_pains_alert"]
            b = c["pct_brenk_alert"]
            clean = c["pct_clean"]
            return clean, max(0, b - 0), p  # we don't have overlap data; show as columns

    labels = [k for k, _ in cond_keys]
    cleans = []
    brenks = []
    painss = []
    for _, c in cond_keys:
        cl, br, pa = fractions(c)
        cleans.append(cl)
        brenks.append(br)
        painss.append(pa)

    x = np.arange(len(labels))
    width = 0.55
    ax.bar(x, cleans, width, label="Clean (no PAINS, no Brenk)", color=PAPER_COLORS["accent_soft"], edgecolor=PAPER_COLORS["accent"], lw=0.8)
    ax.bar(x, brenks, width, bottom=cleans, label="Brenk-flagged", color=PAPER_COLORS["substrate_soft"], edgecolor=PAPER_COLORS["substrate"], lw=0.8)
    bottoms_for_pains = [c + b for c, b in zip(cleans, brenks)]
    ax.bar(x, painss, width, bottom=bottoms_for_pains, label="PAINS-flagged", color=PAPER_COLORS["critical_soft"], edgecolor=PAPER_COLORS["critical"], lw=0.8)
    for i, (cl, br, pa) in enumerate(zip(cleans, brenks, painss)):
        ax.text(i, cl / 2, f"{cl:.1f}%", ha="center", va="center", fontsize=8, color=PAPER_COLORS["ink"])
        ax.text(i, cl + br / 2, f"{br:.1f}%", ha="center", va="center", fontsize=8, color=PAPER_COLORS["ink"])
        if pa > 4:
            ax.text(i, cl + br + pa / 2, f"{pa:.1f}%", ha="center", va="center", fontsize=8, color=PAPER_COLORS["ink"])
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(0, 115)
    ax.set_ylabel("Fraction of compounds (%)")
    ax.set_title("(a)  Structural-alert composition", loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3, frameon=False, fontsize=8.5)


def panel_b_scaffold(ax, summ):
    cond_keys = [
        ("Ablation\n(gate OFF)", summ["conditions"]["ablation_murcko_gate_off"]),
        ("Default\n(gate ON)", summ["conditions"]["default_murcko_gate_on"]),
    ]
    labels = [k for k, _ in cond_keys]
    preserved = [c["pct_scaffold_preserved"] for _, c in cond_keys]
    counts = [c["n_analogs"] for _, c in cond_keys]

    x = np.arange(len(labels))
    bars = ax.bar(x, preserved, 0.55, color=[PAPER_COLORS["substrate"], PAPER_COLORS["accent"]], edgecolor=PAPER_COLORS["ink"], lw=0.5)
    for i, (p, n) in enumerate(zip(preserved, counts)):
        ax.text(i, p + 2, f"{p:.1f}%", ha="center", fontsize=10, color=PAPER_COLORS["ink"])
        ax.text(i, p - 8, f"$n={n:,}$ analogs", ha="center", fontsize=8.5, color=PAPER_COLORS["ink_faint"], style="italic")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 115)
    ax.set_ylabel("Bemis–Murcko scaffold preserved (%)")
    ax.set_title("(b)  Soft Murcko gate impact", loc="left")


def panel_c_property_shifts(ax, per_analog):
    default = [r for r in per_analog if r["scaffold_preserved"]]
    ha = np.array([r["heavy_atom_delta"] for r in default])
    lp = np.array([r["logp_delta"] for r in default])

    # Twin histograms, horizontal layout
    ax.hist(ha, bins=np.arange(ha.min() - 0.5, ha.max() + 1.5, 1), color=PAPER_COLORS["accent_soft"],
            edgecolor=PAPER_COLORS["accent"], lw=0.8, label="$\\Delta$ heavy atoms (count)")
    ax.set_xlabel("$\\Delta$ heavy atoms (analog − lead)")
    ax.set_ylabel("Analog count")
    ax.set_title(f"(c)  $\\Delta$HA distribution ($n={len(default):,}$ default-condition analogs)", loc="left")
    ax.axvline(0, color=PAPER_COLORS["ink_faint"], lw=0.5, ls=":")
    # Annotation
    mean_ha = ha.mean()
    mean_lp = lp.mean()
    ax.text(0.97, 0.93, f"mean $\\Delta$HA = {mean_ha:+.2f}\nmean $\\Delta$cLogP = {mean_lp:+.2f}",
            transform=ax.transAxes, fontsize=9, ha="right", va="top",
            bbox=dict(boxstyle="round,pad=0.5", facecolor=PAPER_COLORS["paper_bg"], edgecolor=PAPER_COLORS["ink_soft"], lw=0.5))


def main():
    apply_paper_style()
    summ, per_analog = load()

    fig = plt.figure(figsize=(13, 5.6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.4, 1.0, 1.5], wspace=0.34)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])

    panel_a_structural_alerts(ax_a, summ)
    panel_b_scaffold(ax_b, summ)
    panel_c_property_shifts(ax_c, per_analog)

    fig.suptitle(
        "Figure 3 — Scaffold preservation and structural-alert audit, $n=129$ marketed-drug seeds",
        x=0.06, y=0.985, ha="left", fontsize=12.5, weight="bold",
    )
    fig.text(
        0.06, 0.94,
        "Each seed processed by the full 479-entry SMIRKS library; per-analog metrics computed by RDKit. "
        "Default condition retains only analogs whose Bemis–Murcko scaffold matches the lead.",
        ha="left", fontsize=9, style="italic", color=PAPER_COLORS["ink_soft"],
    )

    paths = save(fig, OUT_DIR, "fig3_scaffold_alerts")
    for p in paths:
        print(f"wrote {p}")
    plt.close(fig)


if __name__ == "__main__":
    main()
