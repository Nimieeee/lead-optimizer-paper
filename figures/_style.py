"""Shared matplotlib style for paper figures.

Goal: ChemRxiv-credible. Serif typography, muted palette, thin strokes,
no chartjunk. All figures saved as both PDF (vector for LaTeX/Word) and
PNG @ 300 dpi (preview / sanity check).
"""

import matplotlib as mpl
import matplotlib.pyplot as plt
from pathlib import Path

PAPER_COLORS = {
    "ink": "#1a1d24",
    "ink_soft": "#4a525e",
    "ink_faint": "#8a93a3",
    "accent": "#2e5266",
    "accent_soft": "#c9d6dd",
    "substrate": "#8a6b3f",
    "substrate_soft": "#ead9bf",
    "defence": "#6b4c8a",
    "defence_soft": "#d9cee5",
    "critical": "#a13f2f",
    "critical_soft": "#e6d0cc",
    "neutral_warm": "#b39074",
    "neutral_cool": "#7d8a99",
    "paper_bg": "#fdfcf9",
}

# Sequence used when many colors are needed
PAPER_PALETTE = [
    PAPER_COLORS["accent"],
    PAPER_COLORS["substrate"],
    PAPER_COLORS["defence"],
    PAPER_COLORS["critical"],
    PAPER_COLORS["neutral_cool"],
    PAPER_COLORS["neutral_warm"],
]


def apply_paper_style():
    mpl.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": [
                "Charter",
                "Iowan Old Style",
                "Cambria",
                "Georgia",
                "DejaVu Serif",
                "serif",
            ],
            "font.size": 10,
            "axes.labelsize": 10,
            "axes.titlesize": 11,
            "axes.titleweight": "regular",
            "axes.titlepad": 12,
            "axes.labelpad": 6,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "legend.frameon": False,
            "axes.edgecolor": PAPER_COLORS["ink_soft"],
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.color": PAPER_COLORS["ink_soft"],
            "ytick.color": PAPER_COLORS["ink_soft"],
            "xtick.major.size": 4,
            "ytick.major.size": 4,
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "grid.color": PAPER_COLORS["ink_faint"],
            "grid.alpha": 0.2,
            "grid.linewidth": 0.5,
            "figure.facecolor": PAPER_COLORS["paper_bg"],
            "axes.facecolor": PAPER_COLORS["paper_bg"],
            "savefig.facecolor": PAPER_COLORS["paper_bg"],
            "savefig.bbox": "tight",
            "savefig.dpi": 300,
        }
    )


def save(fig, out_dir: str | Path, name: str, *, pdf: bool = True, png: bool = True):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    if pdf:
        p = out_dir / f"{name}.pdf"
        fig.savefig(p, bbox_inches="tight")
        paths.append(p)
    if png:
        p = out_dir / f"{name}.png"
        fig.savefig(p, bbox_inches="tight", dpi=300)
        paths.append(p)
    return paths
