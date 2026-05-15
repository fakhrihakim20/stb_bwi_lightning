"""Render the 4 paper figures as PNG via matplotlib.

No new computation. Every figure reads from an existing parquet/JSON.

Outputs (paper/figures/):
    fig1_history.png         — Annual line totals + Niño 3.4 / IOD JJA overlay
    fig2_scenario.png        — 2026 line-mean GFD per scenario (Model D, with 80% PI)
    fig3_top20_paired.png    — Top-20 paired bars C vs D + Jaccard pill
    fig4_delta_vs_elev.png   — Per-tower Δ (D − C) density vs elevation
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = REPO / "outputs"
FIGJSON = REPO / "docs" / "figures"
CACHE = REPO / "cache"

# IEEE two-column paper figure target: ~3.5 inch wide single-column figures
# at 300 dpi → 1050 px wide PNG. Use a consistent style.
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 8,
    "axes.titlesize": 9,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

ACCENT_C = "#B8854F"   # Model C — warm bronze
ACCENT_D = "#4A7A8C"   # Model D — ocean blue
INK = "#2E261F"
MUTED = "#6B6157"
SAGE = "#8FA38E"
RUST = "#A85638"
BOLT = "#C9A24A"


def jja_mean(df: pd.DataFrame, year: int) -> float:
    s = df[(df["year"] == year) & df["month"].between(6, 8)]["value"].dropna()
    if len(s):
        return float(s.mean())
    s = df[df["year"] == year]["value"].dropna()
    return float(s.mean()) if len(s) else 0.0


def fig1_history() -> None:
    """Annual unique strikes (bars) + Niño 3.4 JJA and DMI JJA (lines, right axis)."""
    panel = pd.read_csv(REPO / "data_tidy" / "exposure_tower_year.csv")
    line = pd.read_csv(REPO / "data_tidy" / "exposure_line_year.csv")
    nino = pd.read_parquet(CACHE / "nino34.parquet")
    dmi = pd.read_parquet(CACHE / "dmi.parquet")

    years = sorted(line["year"].unique().tolist())
    unique_strikes = [int(line.loc[line["year"] == y, "count"].iloc[0]) for y in years]
    nino_jja = [jja_mean(nino, y) for y in years]
    dmi_jja = [jja_mean(dmi, y) for y in years]

    fig, ax1 = plt.subplots(figsize=(3.4, 2.4))
    bars = ax1.bar(years, unique_strikes, color=ACCENT_C, alpha=0.85,
                    width=0.7, label="Unique strikes")
    ax1.set_ylabel("Annual unique strikes", color=INK)
    ax1.set_xlabel("Year")
    ax1.set_xticks(years)
    ax1.tick_params(axis="y", colors=INK)
    ax1.spines["top"].set_visible(False)
    ax1.set_ylim(0, max(unique_strikes) * 1.15)

    # Annotate the 2022 peak
    peak = max(unique_strikes)
    peak_year = years[unique_strikes.index(peak)]
    ax1.annotate(f"{peak:,} ({peak_year})", xy=(peak_year, peak),
                  xytext=(0, 4), textcoords="offset points",
                  ha="center", fontsize=7, color=INK)

    ax2 = ax1.twinx()
    ax2.plot(years, nino_jja, "o-", color=RUST, linewidth=1.6, markersize=4,
              label="Niño 3.4 (JJA)")
    ax2.plot(years, dmi_jja, "s--", color=ACCENT_D, linewidth=1.4, markersize=3.5,
              label="IOD DMI (JJA)")
    ax2.axhline(0, color=MUTED, linewidth=0.5, linestyle=":")
    ax2.set_ylabel("Climate anomaly (°C)", color=MUTED)
    ax2.tick_params(axis="y", colors=MUTED)
    ax2.spines["top"].set_visible(False)

    # Combined legend below the plot
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    fig.legend(h1 + h2, l1 + l2, loc="lower center", ncol=3,
                bbox_to_anchor=(0.5, -0.05), frameon=False, fontsize=7)

    plt.tight_layout()
    plt.savefig(HERE / "fig1_history.png", bbox_inches="tight")
    plt.close()
    print("  wrote fig1_history.png")


def fig2_scenario() -> None:
    """2026 line-mean GFD per scenario with 80 % PI under Model D."""
    fc = pd.read_parquet(OUT / "forecast_2026_2030.parquet")
    sub = fc[(fc["model"] == "D") & (fc["year"] == 2026)]

    scenarios = ["LaNina", "Neutral", "ElNino"]
    labels = ["La Niña", "Neutral", "El Niño"]
    p50 = [sub[sub["scenario"] == s]["density_p50"].mean() for s in scenarios]
    lo80 = [sub[sub["scenario"] == s]["density_lo80"].mean() for s in scenarios]
    hi80 = [sub[sub["scenario"] == s]["density_hi80"].mean() for s in scenarios]
    err_low = [p - lo for p, lo in zip(p50, lo80)]
    err_high = [hi - p for hi, p in zip(hi80, p50)]

    fig, ax = plt.subplots(figsize=(3.4, 2.4))
    x = np.arange(len(scenarios))
    bars = ax.bar(x, p50, color=[SAGE, BOLT, RUST], alpha=0.85, width=0.55,
                   edgecolor="none")
    ax.errorbar(x, p50, yerr=[err_low, err_high], fmt="none",
                 ecolor=INK, capsize=4, capthick=1, elinewidth=1)
    for i, v in enumerate(p50):
        ax.text(i, v + 0.15, f"{v:.2f}", ha="center", va="bottom",
                 fontsize=8, color=INK)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("2026 line-mean GFD\n(flashes/km²/yr)")
    ax.set_ylim(0, max(hi80) * 1.15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(HERE / "fig2_scenario.png", bbox_inches="tight")
    plt.close()
    print("  wrote fig2_scenario.png")


def fig3_top20_paired() -> None:
    """Top-20 paired bars C vs D (union of both top-20 lists)."""
    d = json.load(open(FIGJSON / "comparison_top20.json"))
    union = sorted(d["union_ids"])
    cVals = [d["C_values"].get(str(t), 0) for t in union]
    dVals = [d["D_values"].get(str(t), 0) for t in union]
    c_only = set(d.get("C_only", []))
    d_only = set(d.get("D_only", []))
    labels = [f"$\\it{{Tower\\ {t}}}$*" if (t in c_only or t in d_only)
              else f"Tower {t}" for t in union]
    jaccard = d["jaccard"]

    fig, ax = plt.subplots(figsize=(3.4, 5.2))
    y = np.arange(len(union))
    h = 0.4
    ax.barh(y - h/2, cVals, height=h, color=ACCENT_C, label="Model C", alpha=0.9)
    ax.barh(y + h/2, dVals, height=h, color=ACCENT_D, label="Model D", alpha=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("5-yr mean GFD (Neutral, flashes/km²/yr)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="lower right", frameon=False)

    # Jaccard annotation
    ax.text(0.98, 0.01, f"Jaccard = {jaccard:.2f}",
             transform=ax.transAxes, ha="right", va="bottom",
             fontsize=7, color=MUTED,
             bbox=dict(boxstyle="round,pad=0.3", fc="white",
                       ec=MUTED, lw=0.5, alpha=0.9))

    plt.tight_layout()
    plt.savefig(HERE / "fig3_top20_paired.png", bbox_inches="tight")
    plt.close()
    print("  wrote fig3_top20_paired.png")


def fig4_delta_vs_elev() -> None:
    """Per-tower Δ (D − C) density_p50 vs elevation, 5-yr mean Neutral."""
    d = json.load(open(FIGJSON / "comparison_delta.json"))
    rows = d["rows"]
    elev = np.array([r["elev"] for r in rows])
    delta = np.array([r["delta"] for r in rows])

    fig, ax = plt.subplots(figsize=(3.4, 2.4))
    colors = [ACCENT_D if x >= 0 else RUST for x in delta]
    ax.scatter(elev, delta, c=colors, s=10, alpha=0.7, edgecolor="none")
    ax.axhline(0, color=MUTED, linestyle=":", linewidth=0.6)
    ax.set_xlabel("Tower elevation (m)")
    ax.set_ylabel("Δ GFD : Model D − Model C\n(flashes/km²/yr, 5-yr Neutral)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    mean_d = float(np.mean(delta))
    ax.text(0.98, 0.95, f"mean Δ = {mean_d:+.2f}",
             transform=ax.transAxes, ha="right", va="top",
             fontsize=7, color=MUTED,
             bbox=dict(boxstyle="round,pad=0.3", fc="white",
                       ec=MUTED, lw=0.5, alpha=0.9))

    plt.tight_layout()
    plt.savefig(HERE / "fig4_delta_vs_elev.png", bbox_inches="tight")
    plt.close()
    print("  wrote fig4_delta_vs_elev.png")


if __name__ == "__main__":
    fig1_history()
    fig2_scenario()
    fig3_top20_paired()
    fig4_delta_vs_elev()
    print("\nAll 4 figures rendered.")
