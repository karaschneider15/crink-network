"""Static figures for the README. Single-hue (blue) sequential encoding throughout."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from .build import DYAD_LABELS, graph_for  # noqa: E402
from .schema import ACTORS  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#1f1f1d"
MUTED = "#6b6a66"
GRID = "#e4e3df"
# Sequential blue ramp, surface -> dark (palette steps 100..700)
BLUES = LinearSegmentedColormap.from_list(
    "crink_blues", [SURFACE, "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
)
EDGE = "#2a78d6"
NAMES = {"CHN": "China", "RUS": "Russia", "IRN": "Iran", "PRK": "North Korea"}

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "text.color": INK,
        "axes.labelcolor": MUTED,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
    }
)


def _pretty(dyad: str) -> str:
    a, b = dyad.split("-")
    return f"{NAMES[a]} – {NAMES[b]}"


def heatmap(panel: pd.DataFrame, path: Path) -> None:
    mat = panel.pivot(index="dyad", columns="year", values="weighted_intensity")
    mat = mat.reindex(DYAD_LABELS)
    fig, ax = plt.subplots(figsize=(9, 3.6))
    vmax = float(np.nanmax(mat.values)) or 1.0
    ax.imshow(mat.values, cmap=BLUES, vmin=0, vmax=vmax, aspect="auto")
    ax.set_xticks(range(mat.shape[1]), [str(y) for y in mat.columns])
    ax.set_yticks(range(mat.shape[0]), [_pretty(d) for d in mat.index])
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    # white 2px gaps between cells
    ax.set_xticks(np.arange(-0.5, mat.shape[1]), minor=True)
    ax.set_yticks(np.arange(-0.5, mat.shape[0]), minor=True)
    ax.grid(which="minor", color=SURFACE, linewidth=2)
    ax.tick_params(which="minor", length=0)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat.values[i, j]
            if v > 0:
                ax.text(j, i, f"{v:g}", ha="center", va="center", fontsize=8.5,
                        color="white" if v > 0.55 * vmax else INK)
    ax.set_title("Coded tie intensity by dyad and year (verification-weighted)",
                 loc="left", fontsize=11, color=INK, pad=10)
    fig.text(0.01, 0.01, "Seed dataset: high-salience events only. Blank = nothing coded, "
             "not evidence of no tie.", fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=200)
    plt.close(fig)


def network(panel: pd.DataFrame, path: Path) -> None:
    g = graph_for(panel, None)
    pos = {"CHN": (0, 1), "RUS": (1, 1), "IRN": (0, 0), "PRK": (1, 0)}
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.set_axis_off()
    wmax = max((d["weight"] for _, _, d in g.edges(data=True)), default=1.0)
    for a, b, d in g.edges(data=True):
        (x1, y1), (x2, y2) = pos[a], pos[b]
        ax.plot([x1, x2], [y1, y2], color=EDGE, linewidth=1 + 11 * d["weight"] / wmax,
                solid_capstyle="round", alpha=0.85, zorder=1)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if {a, b} == {"CHN", "PRK"}:
            mx, my = mx - 0.13, my + 0.1
        if {a, b} == {"RUS", "IRN"}:
            mx, my = mx + 0.13, my + 0.1
        ax.text(mx, my, f"{d['weight']:g}\n({d['n_events']} ev.)", ha="center", va="center",
                fontsize=8.5, color=INK,
                bbox={"boxstyle": "round,pad=0.25", "fc": SURFACE, "ec": GRID})
    strength = dict(g.degree(weight="weight"))
    smax = max(strength.values()) or 1
    for n in ACTORS:
        x, y = pos[n]
        ax.scatter([x], [y], s=900 + 2200 * strength[n] / smax, color=SURFACE,
                   edgecolors=INK, linewidths=1.5, zorder=2)
        ax.text(x, y, NAMES[n].replace(" ", "\n"), ha="center", va="center",
                fontsize=9.5, color=INK, zorder=3)
    ax.set_xlim(-0.35, 1.35)
    ax.set_ylim(-0.3, 1.3)
    ax.set_title("CRINK network, all coded years\nEdge width = weighted intensity; "
                 "node size = strength", loc="left", fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def make_all(panel: pd.DataFrame, fig_dir: str | Path) -> list[Path]:
    fig_dir = Path(fig_dir)
    fig_dir.mkdir(parents=True, exist_ok=True)
    out = [fig_dir / "dyad_year_heatmap.png", fig_dir / "network_all_years.png"]
    heatmap(panel, out[0])
    network(panel, out[1])
    return out
