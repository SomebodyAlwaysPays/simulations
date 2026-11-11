"""Checks for reproducibility and the model's core debt arithmetic."""

import csv

import numpy as np
import pytest

from francesim.model import bootstrap_years, debt_next, simulate
from run import main


@pytest.fixture(scope="module")
def outputs(tmp_path_factory):
    first = tmp_path_factory.mktemp("first")
    second = tmp_path_factory.mktemp("second")
    main(n=256, sensitivity_n=64, seed=20261030, out_dir=first)
    main(n=256, sensitivity_n=64, seed=20261030, out_dir=second)
    return first, second


@pytest.mark.parametrize("scenario", ["A", "B", "C", "D"])
def test_zero_shock_is_central_path(outputs, scenario):
    with (outputs[0] / f"central_{scenario}.csv").open() as f:
        central = list(csv.DictReader(f))
    path = simulate(scenario, 1, zero_shocks=True)
    for key in ("debt", "interest", "rate", "oat", "spread", "primary", "growth",
                "gdp", "real_interest", "cumulative_interest"):
        np.testing.assert_array_equal(np.array([float(row[key]) for row in central]), path[key][0])


def test_same_seed_produces_identical_summary(outputs):
    assert (outputs[0] / "summary.json").read_bytes() == (outputs[1] / "summary.json").read_bytes()


def test_bootstrap_draws_only_historical_years_in_wrapped_pairs():
    years = bootstrap_years(1000, seed=42)
    assert years.shape == (1000, 15)
    assert np.all((1991 <= years) & (years <= 2025))
    expected_second = 1991 + (years[:, 0:14:2] - 1991 + 1) % 35
    np.testing.assert_array_equal(years[:, 1:15:2], expected_second)


def test_scenario_d_has_lower_median_debt_than_a():
    a = simulate("A", 1000, seed=42)["debt"][:, -1]
    d = simulate("D", 1000, seed=42)["debt"][:, -1]
    assert np.median(d) < np.median(a)


def test_equal_interest_and_growth_with_balanced_primary_keeps_debt_constant():
    debt = np.array([119.3, 119.3, 119.3])
    rates = np.array([-1.0, 0.0, 4.5])
    for _ in range(15):
        debt = debt_next(debt, rates, rates, 0.0)
    np.testing.assert_allclose(debt, 119.3, rtol=0, atol=1e-12)
