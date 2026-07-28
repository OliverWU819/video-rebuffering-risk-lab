"""Regenerate the aggregate figures embedded in the project README."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import PercentFormatter


ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = ROOT / "reports" / "tables"
FIGURE_DIR = ROOT / "reports" / "figures"

NAVY = "#17324D"
BLUE = "#2F6BFF"
TEAL = "#22A699"
RED = "#D95D5D"
GREY = "#AAB4BE"
GRID = "#DDE3E8"


def finish_figure(fig: plt.Figure, output_name: str) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        FIGURE_DIR / output_name,
        dpi=180,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)


def plot_average_precision() -> None:
    results = pd.read_csv(TABLE_DIR / "model_results.csv")

    fig, ax = plt.subplots(figsize=(10, 5.8))
    colors = [GREY, TEAL, BLUE]
    bars = ax.bar(
        results["risk_ranking"],
        results["average_precision"],
        color=colors,
        width=0.62,
    )

    ax.set_title(
        "Risk ranking improves beyond buffer alone",
        color=NAVY,
        fontsize=18,
        fontweight="bold",
        pad=34,
    )
    ax.set_ylabel("Test Average Precision", color=NAVY, fontsize=12)
    ax.set_ylim(0, 0.62)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.grid(axis="y", color=GRID, linewidth=0.9)
    ax.set_axisbelow(True)

    for bar, value in zip(bars, results["average_precision"], strict=True):
        label = f"{value:.4f}"
        y = max(value + 0.018, 0.025)
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            y,
            label,
            ha="center",
            va="bottom",
            color=NAVY,
            fontsize=12,
            fontweight="bold",
        )

    ax.text(
        0.5,
        1.015,
        "692 unseen sessions · 2.23M eligible rows · 661 positives",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        color="#596773",
        fontsize=10,
    )

    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(axis="x", colors=NAVY, labelsize=11)
    ax.tick_params(axis="y", colors="#596773")

    fig.tight_layout()
    finish_figure(fig, "ap_comparison.png")


def plot_coefficients() -> None:
    coefficients = pd.read_csv(TABLE_DIR / "logistic_coefficients.csv")
    coefficients = coefficients.sort_values("standardized_coefficient")
    colors = [
        RED if value > 0 else BLUE
        for value in coefficients["standardized_coefficient"]
    ]

    fig, ax = plt.subplots(figsize=(10, 6.4))
    bars = ax.barh(
        coefficients["feature"],
        coefficients["standardized_coefficient"],
        color=colors,
        height=0.64,
    )

    ax.axvline(0, color=NAVY, linewidth=1)
    ax.set_xlim(-0.55, 0.55)
    ax.set_title(
        "Logistic V1 standardized coefficients",
        color=NAVY,
        fontsize=18,
        fontweight="bold",
        pad=18,
    )
    ax.set_xlabel(
        "Change in model log-odds per one feature standard deviation",
        color=NAVY,
        fontsize=11,
    )
    ax.grid(axis="x", color=GRID, linewidth=0.9)
    ax.set_axisbelow(True)

    for bar, value in zip(
        bars,
        coefficients["standardized_coefficient"],
        strict=True,
    ):
        offset = 0.012 if value >= 0 else -0.012
        ax.text(
            value + offset,
            bar.get_y() + bar.get_height() / 2,
            f"{value:+.3f}",
            ha="left" if value >= 0 else "right",
            va="center",
            color=NAVY,
            fontsize=10,
        )

    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(axis="x", colors="#596773")
    ax.tick_params(axis="y", colors=NAVY, labelsize=11)

    fig.text(
        0.5,
        0.018,
        "Associations are conditional and non-causal.",
        ha="center",
        va="bottom",
        color="#596773",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0.055, 1, 1))
    finish_figure(fig, "standardized_coefficients.png")


def main() -> None:
    plot_average_precision()
    plot_coefficients()
    print(f"Saved README figures to {FIGURE_DIR}")


if __name__ == "__main__":
    main()
