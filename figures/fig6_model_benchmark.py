#!/usr/bin/env python3
"""
Figure 6, Cross-provider model benchmark across stages 2, 5, 6.

Three-panel bar chart, one panel per stage:
  (a) Stage 2 vision, JSON validity × self-consistency Jaccard, ranked
  (b) Stage 5 context, rubric score, ranked
  (c) Stage 6 optimization, total rubric score, ranked

Each bar coloured by provider. Models with JSON-validity < 0.5 are dimmed
(unreliable on this task) to surface the result without hiding it.
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

RES = HERE.parent / "experiments/exp5_model_benchmark/results"
OUT_DIR = HERE / "out"

PROVIDER_COLOR = {
    "openai":   PAPER_COLORS["accent"],
    "gemini":   PAPER_COLORS["substrate"],
    "opencode": PAPER_COLORS["defence"],
    "mistral":  PAPER_COLORS["critical"],
    "groq":     PAPER_COLORS["ink_soft"],
}


def short_model_label(provider: str, model: str) -> str:
    # Trim verbose model IDs for chart axis
    m = model.replace("meta-llama/", "").replace("openai/", "")
    m = m.replace("-17b-16e-instruct", " 17B-16e")
    m = m.replace("-17b-128e-instruct", " 17B-128e")
    m = m.replace("-latest", "")
    m = m.replace("-preview", "")
    return f"{m}  ·  {provider}"


def panel_stage(ax, rows, score_key: str, title: str, dim_below: float = 0.5):
    """Render one stage's models as horizontal bars sorted by score_key."""
    rows = sorted(rows, key=lambda r: -float(r.get(score_key) or 0))
    labels = [short_model_label(r["provider"], r["model"]) for r in rows]
    scores = [float(r.get(score_key) or 0) for r in rows]
    validity = [float(r.get("json_validity_rate", 0)) for r in rows]
    colors = []
    for r, v in zip(rows, validity):
        c = PROVIDER_COLOR.get(r["provider"], "#808080")
        if v < dim_below:
            # Dim by mixing with paper background
            from matplotlib.colors import to_rgb
            r_, g_, b_ = to_rgb(c)
            colors.append((0.6 * r_ + 0.4, 0.6 * g_ + 0.4, 0.6 * b_ + 0.4))
        else:
            colors.append(c)

    y = np.arange(len(rows))
    ax.barh(y, scores, color=colors, edgecolor=PAPER_COLORS["ink"], lw=0.4, height=0.7)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(0, max(scores + [0.001]) * 1.12)
    ax.set_xlabel(f"{score_key}")
    ax.set_title(title, loc="left")
    ax.grid(True, axis="x", alpha=0.25)
    # Annotate JSON validity rate at end of each bar
    for yi, (s, v) in enumerate(zip(scores, validity)):
        ax.text(s + 0.01, yi, f"  JSON-ok {v*100:.0f}%", va="center", fontsize=7,
                color=PAPER_COLORS["ink_faint"])


def load_summary(stage_name: str):
    p = RES / f"{stage_name}_summary.json"
    if not p.exists():
        # Try aggregating per-model jsons if summary not yet written
        rows = []
        for f in sorted(RES.glob(f"{stage_name}_*.json")):
            if "summary" in f.name: continue
            try:
                rows.append(json.loads(f.read_text()))
            except Exception:
                pass
        return rows
    return json.loads(p.read_text())


def main():
    apply_paper_style()

    stage2 = load_summary("stage2")
    stage5 = load_summary("stage5")
    stage6 = load_summary("stage6")

    fig = plt.figure(figsize=(15.5, 7.0))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.0, 1.0], wspace=0.55)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])

    panel_stage(ax_a, stage2, "mean_jaccard_self",
                "(a)  Stage 2, Vision Agent  ·  self-consistency Jaccard")
    panel_stage(ax_b, stage5, "mean_rubric_score",
                "(b)  Stage 5, Project context  ·  endpoint-priority rubric")
    panel_stage(ax_c, stage6, "mean_total_score",
                "(c)  Stage 6, Optimization agent  ·  SAR-strategy rubric")

    fig.suptitle(
        "Figure 6, Cross-provider model evaluation across three Lead-Optimizer agent stages",
        x=0.06, y=0.985, ha="left", fontsize=12.5, weight="bold",
    )
    fig.text(
        0.06, 0.945,
        "Stage 2: 14 vision models × 8 reps on a fixed LID. "
        "Stage 5: 11 text models × 4 project contexts × 3 reps. "
        "Stage 6: 11 text models × 4 leads × 3 reps. "
        "Bars dimmed when JSON validity < 50 % (model unreliable on this task).",
        ha="left", fontsize=8.5, style="italic", color=PAPER_COLORS["ink_soft"],
    )

    # Provider colour legend
    from matplotlib.patches import Patch
    handles = [Patch(facecolor=c, edgecolor=PAPER_COLORS["ink"], label=p) for p, c in PROVIDER_COLOR.items()]
    fig.legend(handles=handles, loc="upper right", bbox_to_anchor=(0.99, 0.99),
               frameon=False, ncol=5, fontsize=9)

    paths = save(fig, OUT_DIR, "fig6_model_benchmark")
    for p in paths:
        print(f"wrote {p}")
    plt.close(fig)


if __name__ == "__main__":
    main()
