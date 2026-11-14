"""Household income and wealth accounting for a fixed AI productivity path."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]

HOUSEHOLDS = 1_000
YEARS = 30
SEED = 42
WEALTH_MEDIAN = 80_000
WEALTH_LOG_SD = 1.0
WAGE_MEDIAN = 45_000
WAGE_LOG_SD = 0.45
SAVING_RATE = 0.20
AI_PRODUCTIVITY_GROWTH = 0.04
TOP_GROUP_FRACTION = 0.10
TOP_GROUP_SIZE = round(HOUSEHOLDS * TOP_GROUP_FRACTION)
BASELINE_CAPITAL_FRACTION = 0.75
CONCENTRATED_OWNERSHIP = 0.90
DIVIDEND_FRACTION = 0.50


@dataclass(frozen=True)
class Scenario:
    label: str
    top_ownership_share: float
    dividend_fraction: float = 0.0


SCENARIOS = (
    Scenario("Broad ownership", TOP_GROUP_FRACTION),
    Scenario("Concentrated ownership", CONCENTRATED_OWNERSHIP),
    Scenario("Concentrated + dividend", CONCENTRATED_OWNERSHIP, DIVIDEND_FRACTION),
)


@dataclass(frozen=True)
class Population:
    starting_wealth: FloatArray
    base_wages: FloatArray
    initially_wealthiest: NDArray[np.intp]


@dataclass(frozen=True)
class AnnualMetrics:
    year: int
    wealth_gini: float
    top_10_wealth_share: float
    mean_income: float
    median_income: float
    income_gini: float
    labour_income_share: float
    capital_income_share: float


def make_population() -> Population:
    """Draw two independent log-normal samples and fix the initial owner group."""
    rng = np.random.default_rng(SEED)
    wealth = rng.lognormal(np.log(WEALTH_MEDIAN), WEALTH_LOG_SD, HOUSEHOLDS)
    wages = rng.lognormal(np.log(WAGE_MEDIAN), WAGE_LOG_SD, HOUSEHOLDS)
    initially_wealthiest = np.argsort(wealth)[-TOP_GROUP_SIZE:]
    return Population(wealth, wages, initially_wealthiest)


def ownership_weights(top_ownership_share: float, population: Population) -> FloatArray:
    """Allocate the top group's share equally within it, and the rest outside it."""
    other_share = (1 - top_ownership_share) / (HOUSEHOLDS - TOP_GROUP_SIZE)
    weights = np.full(HOUSEHOLDS, other_share)
    weights[population.initially_wealthiest] = top_ownership_share / TOP_GROUP_SIZE
    return weights


def gini(sorted_values: FloatArray) -> float:
    """Compute the Gini of sorted, non-negative values with a positive total."""
    count = sorted_values.size
    ranks = np.arange(1, count + 1)
    return float(np.dot(2 * ranks - count - 1, sorted_values) / (count * sorted_values.sum()))


def measure(year: int, wealth: FloatArray, income: FloatArray, capital_pool: float) -> AnnualMetrics:
    sorted_wealth = np.sort(wealth)
    capital_share = capital_pool / income.sum()
    return AnnualMetrics(
        year=year,
        wealth_gini=gini(sorted_wealth),
        top_10_wealth_share=float(sorted_wealth[-TOP_GROUP_SIZE:].sum() / sorted_wealth.sum()),
        mean_income=float(income.mean()),
        median_income=float(np.median(income)),
        income_gini=gini(np.sort(income)),
        labour_income_share=float(1 - capital_share),
        capital_income_share=float(capital_share),
    )


def simulate(
    population: Population,
    scenario: Scenario,
    capital_fraction: float = BASELINE_CAPITAL_FRACTION,
    *,
    productivity_growth: float = AI_PRODUCTIVITY_GROWTH,
) -> list[AnnualMetrics]:
    """Record the pre-AI baseline, then earn income and save in years 1–30."""
    wealth = population.starting_wealth.copy()
    base_wages = population.base_wages
    base_output = base_wages.sum()
    gross_ownership = ownership_weights(scenario.top_ownership_share, population)
    metrics = [measure(0, wealth, base_wages, 0.0)]

    for year in range(1, YEARS + 1):
        ai_gain = base_output * ((1 + productivity_growth) ** year - 1)
        capital_pool = capital_fraction * ai_gain
        wage_gain = ai_gain - capital_pool
        wages = base_wages + wage_gain * (base_wages / base_output)
        dividend = scenario.dividend_fraction * capital_pool / HOUSEHOLDS
        retained_capital = (1 - scenario.dividend_fraction) * capital_pool * gross_ownership
        disposable_income = wages + retained_capital + dividend
        wealth += SAVING_RATE * disposable_income
        metrics.append(measure(year, wealth, disposable_income, capital_pool))

    return metrics
