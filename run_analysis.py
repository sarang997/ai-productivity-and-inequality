"""Regenerate the figures and underlying tables with python run_analysis.py."""

import csv
from dataclasses import asdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import PercentFormatter, StrMethodFormatter

from simulation import (
    BASELINE_CAPITAL_FRACTION,
    CONCENTRATED_OWNERSHIP,
    DIVIDEND_FRACTION,
    SCENARIOS,
    TOP_GROUP_FRACTION,
    YEARS,
    AnnualMetrics,
    Population,
    Scenario,
    make_population,
    simulate,
)

OUTPUT = Path(__file__).resolve().parent / "figures"
TOP_SHARES = (TOP_GROUP_FRACTION, 0.30, 0.50, 0.70, CONCENTRATED_OWNERSHIP, 1.00)
CAPITAL_FRACTIONS = (0.25, 0.50, BASELINE_CAPITAL_FRACTION, 1.00)
COLOURS = ("#14796f", "#ab4f2d", "#5757a0")
LINE_STYLES = ("-", "--", "-.")

plt.rcParams.update({
    "figure.facecolor": "#f8f7f4",
    "axes.facecolor": "#f8f7f4",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#9c9c9a",
    "axes.labelcolor": "#232c33",
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "text.color": "#232c33",
    "xtick.color": "#424e56",
    "ytick.color": "#424e56",
    "grid.color": "#dddcd7",
    "axes.axisbelow": True,
    "legend.frameon": False,
    "font.size": 11,
})


def heading(fig, title, subtitle):
    fig.text(0.08, 0.96, title, fontsize=23, weight="bold", va="top")
    fig.text(0.08, 0.90, subtitle, fontsize=11, va="top", color="#424e56")


def save_figure(fig, filename):
    fig.savefig(OUTPUT / filename, dpi=160)
    plt.close(fig)


def save_csv(filename, rows):
    with (OUTPUT / filename).open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def plot_over_time(baseline: dict[str, list[AnnualMetrics]]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.5))
    fig.subplots_adjust(left=0.08, right=0.96, top=0.78, bottom=0.12, wspace=0.24, hspace=0.42)
    heading(
        fig,
        "Who receives the gains from AI?",
        f"1,000 simulated households  •  {YEARS} annual periods  •  {BASELINE_CAPITAL_FRACTION:.0%} of AI gains go to capital",
    )
    gini_ax, top_ax, income_ax, shares_ax = axes.flat
    for (label, series), colour, style in zip(baseline.items(), COLOURS, LINE_STYLES):
        years = [row.year for row in series]
        gini_ax.plot(years, [row.wealth_gini for row in series], style, color=colour, lw=2.5, label=label)
        top_ax.plot(years, [row.top_10_wealth_share for row in series], style, color=colour, lw=2.5)

    shared_path = next(iter(baseline.values()))
    years = [row.year for row in shared_path]
    income_ax.plot(years, [row.mean_income / 1_000 for row in shared_path], color="#344a5e", lw=2.5)
    income_ax.text(0.04, 0.88, "All three scenarios", transform=income_ax.transAxes, color="#344a5e")
    shares_ax.plot(years, [row.labour_income_share for row in shared_path], color="#344a5e", lw=2.5, label="Labour")
    shares_ax.plot(years, [row.capital_income_share for row in shared_path], "--", color="#ab4f2d", lw=2.5, label="Capital")
    shares_ax.legend(loc="upper right", fontsize=10)

    income_ax.set(ylabel="Thousands of units per year", ylim=(0, None))
    shares_ax.set(ylim=(0, 1.05))
    for ax in (top_ax, shares_ax):
        ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    titles = (
        "Wealth Gini", "Top 10% share of wealth",
        "Average household income", "Labour and capital shares of income",
    )
    for ax, title in zip(axes.flat, titles):
        ax.set_title(title, loc="left", pad=10)
        ax.set(xlim=(0, YEARS), xticks=range(0, YEARS + 1, 5))
        ax.grid(axis="y")
    for ax in axes[1]:
        ax.set_xlabel("Simulation year")
    fig.legend(*gini_ax.get_legend_handles_labels(), ncol=3, loc="upper left", bbox_to_anchor=(0.07, 0.867))
    fig.text(0.08, 0.034, "Year 0 is the pre-AI starting point. Factor shares are measured before the dividend.")
    save_figure(fig, "01_trajectories.png")


def plot_final(baseline: dict[str, list[AnnualMetrics]], no_ai: AnnualMetrics) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.8))
    fig.subplots_adjust(left=0.20, right=0.95, top=0.80, bottom=0.13, wspace=0.26, hspace=0.53)
    final = [series[-1] for series in baseline.values()]
    shared = final[0]
    heading(
        fig,
        f"Household outcomes in year {YEARS}",
        f"All three scenarios average {shared.mean_income:,.0f} units per year"
        f"  •  {shared.labour_income_share:.1%} labour income  •  {shared.capital_income_share:.1%} capital income",
    )
    labels = ("Broad ownership", "Concentrated", "Concentrated + dividend")
    positions = range(len(final))
    panels = (
        ("Wealth Gini", "wealth_gini", ".3f", 1),
        ("Top 10% share of wealth", "top_10_wealth_share", ".1%", 1),
        ("Median household income", "median_income", ",.0f", 1_000),
        ("Disposable income Gini", "income_gini", ".3f", 1),
    )
    for ax, (title, metric, display_format, unit) in zip(axes.flat, panels):
        values = [getattr(row, metric) for row in final]
        reference = getattr(no_ai, metric)
        ax.axvline(reference / unit, color="#535d66", lw=1.5, ls=":", zorder=4)
        bars = ax.barh(list(positions), np.array(values) / unit, color=COLOURS, height=0.52, zorder=3)
        ax.bar_label(
            bars, labels=[format(value, display_format) for value in values], padding=5,
            bbox={"facecolor": fig.get_facecolor(), "edgecolor": "none", "pad": 1},
            zorder=5,
        )
        ax.set(yticks=list(positions), xlim=(0, 1.27 * max(reference, *values) / unit))
        ax.invert_yaxis()
        ax.grid(axis="x")
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.set_title(title, loc="left", pad=10)

    for ax in axes[:, 0]:
        ax.set_yticklabels(labels)
    for ax in axes[:, 1]:
        ax.set_yticklabels([])
    axes[0, 1].xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    axes[1, 0].xaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))
    axes[1, 0].set_xlabel("Thousands of units per year")
    fig.text(0.08, 0.033, f"Dotted lines mark year {YEARS} outcomes with zero AI productivity growth.")
    save_figure(fig, "02_year_30_comparison.png")


def run_sensitivity(population: Population) -> list[dict]:
    rows = []
    for capital_fraction in CAPITAL_FRACTIONS:
        broad = simulate(population, SCENARIOS[0], capital_fraction)[-1]
        for top_share in TOP_SHARES:
            gross = simulate(population, Scenario("No dividend", top_share), capital_fraction)[-1]
            net = simulate(
                population, Scenario("With dividend", top_share, DIVIDEND_FRACTION), capital_fraction
            )[-1]
            rows.append({
                "top_ownership_share": top_share,
                "capital_fraction_of_ai_gains": capital_fraction,
                "dividend_fraction": DIVIDEND_FRACTION,
                "broad_wealth_gini": broad.wealth_gini,
                "no_dividend_wealth_gini": gross.wealth_gini,
                "with_dividend_wealth_gini": net.wealth_gini,
                "no_dividend_gini_gap": gross.wealth_gini - broad.wealth_gini,
                "with_dividend_gini_gap": net.wealth_gini - broad.wealth_gini,
                "broad_top_10_wealth_share": broad.top_10_wealth_share,
                "no_dividend_top_10_wealth_share": gross.top_10_wealth_share,
                "with_dividend_top_10_wealth_share": net.top_10_wealth_share,
            })
    return rows


def plot_sensitivity(rows: list[dict]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4))
    fig.subplots_adjust(left=0.08, right=0.91, top=0.72, bottom=0.23, wspace=0.22)
    heading(
        fig,
        "When does ownership concentration matter most?",
        "Year-30 wealth Gini gap versus equal ownership at the same capital share of AI gains",
    )
    panels = (
        ("No dividend", "no_dividend_gini_gap"),
        (f"{DIVIDEND_FRACTION:.0%} AI dividend", "with_dividend_gini_gap"),
    )
    maximum = max(row["no_dividend_gini_gap"] for row in rows)
    for ax, (title, key) in zip(axes, panels):
        gaps = np.array([row[key] for row in rows]).reshape(len(CAPITAL_FRACTIONS), len(TOP_SHARES))
        image = ax.imshow(gaps, cmap="YlGnBu", aspect="auto", origin="lower", vmin=0, vmax=maximum)
        for (i, j), gap in np.ndenumerate(gaps):
            ax.text(j, i, f"{gap:.3f}", ha="center", va="center", fontsize=10, color="white" if gap > 0.62 * maximum else "#172832")
        ax.set_title(title, loc="left", pad=10)
        ax.set_xticks(range(len(TOP_SHARES)), [f"{share:.0%}" for share in TOP_SHARES])
        ax.set_yticks(range(len(CAPITAL_FRACTIONS)), [f"{fraction:.0%}" for fraction in CAPITAL_FRACTIONS])
        ax.set_xlabel("AI capital owned by the initial top 10%")
    axes[0].set_ylabel("AI gains going to capital")
    axes[1].set_yticklabels([])
    colourbar = fig.colorbar(image, cax=fig.add_axes([0.926, 0.23, 0.012, 0.49]))
    colourbar.set_label("Wealth Gini gap")
    fig.text(0.08, 0.053, "At 10% ownership by the initial top 10%, every household owns the same share.")
    save_figure(fig, "03_sensitivity.png")


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    population = make_population()
    baseline = {scenario.label: simulate(population, scenario) for scenario in SCENARIOS}
    no_ai = simulate(population, SCENARIOS[0], productivity_growth=0)
    sensitivity = run_sensitivity(population)
    annual_paths = {**baseline, "No AI reference": no_ai}
    save_csv("annual_metrics.csv", [
        {"scenario": label, **asdict(row)}
        for label, path in annual_paths.items()
        for row in path
    ])
    save_csv("sensitivity.csv", sensitivity)
    plot_over_time(baseline)
    plot_final(baseline, no_ai[-1])
    plot_sensitivity(sensitivity)

    for label, series in annual_paths.items():
        final = series[-1]
        print(
            f"{label:24s}  wealth Gini {final.wealth_gini:.3f}  "
            f"top 10% {final.top_10_wealth_share:5.1%}  "
            f"mean {final.mean_income:>8,.0f}  median {final.median_income:>8,.0f}"
        )
    print(f"Saved three figures and two CSV tables to {OUTPUT}")


if __name__ == "__main__":
    main()
