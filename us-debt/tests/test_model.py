"""Checks for reproducibility and US debt model arithmetic."""

import csv
import json

import numpy as np
import pytest

from usasim.model import bootstrap_years, debt_next, simulate
from run import main


@pytest.fixture(scope="module")
def outputs(tmp_path_factory):
    first = tmp_path_factory.mktemp("first")
    second = tmp_path_factory.mktemp("second")
    main(n=256, sensitivity_n=64, seed=20261103, out_dir=first)
    main(n=256, sensitivity_n=64, seed=20261103, out_dir=second)
    return first, second


@pytest.mark.parametrize("scenario", ["A", "B", "C", "D"])
def test_zero_shock_is_central_path(outputs, scenario):
    with (outputs[0] / f"central_{scenario}.csv").open() as f:
        central = list(csv.DictReader(f))
    path = simulate(scenario, 1, zero_shocks=True)
    for key, values in path.items():
        np.testing.assert_array_equal([float(row[key]) for row in central], values[0])


def test_same_seed_produces_identical_summary(outputs):
    assert (outputs[0] / "summary.json").read_bytes() == (outputs[1] / "summary.json").read_bytes()


@pytest.mark.parametrize("start", [1985, 1960])
def test_bootstrap_draws_historical_years_in_wrapped_pairs(start):
    years = bootstrap_years(1000, seed=42, history_start=start)
    assert years.shape == (1000, 15)
    assert np.all((start <= years) & (years <= 2025))
    expected_second = start + (years[:, 0:14:2] - start + 1) % (2026 - start)
    np.testing.assert_array_equal(years[:, 1:15:2], expected_second)


def test_scenario_ordering_with_common_draws():
    b = simulate("B", 1000, seed=42)["debt"]
    c = simulate("C", 1000, seed=42)["debt"]
    d = simulate("D", 1000, seed=42)["debt"]
    assert np.all(c >= b)
    assert np.median(d[:, -1]) < np.median(b[:, -1])


def test_zero_shock_deficit_in_d_meets_target():
    deficit = simulate("D", 1, zero_shocks=True)["deficit"][0, 1:]
    years = np.arange(2027, 2042)
    target = np.maximum(3.0, 5.756 - 0.75 * (years - 2026))
    np.testing.assert_allclose(deficit, target, rtol=0, atol=1e-9)


def test_equal_interest_and_growth_with_balanced_primary_keeps_debt_constant():
    debt = np.array([100.588, 100.588, 100.588])
    rates = np.array([-1.0, 0.0, 4.5])
    for _ in range(15):
        debt = debt_next(debt, rates, rates, 0.0)
    np.testing.assert_allclose(debt, 100.588, rtol=0, atol=1e-12)


def test_cbo_replication_reports_each_annual_gap(outputs):
    validation = json.loads((outputs[0] / "validation.json").read_text())
    replication = validation["cbo_replication"]
    assert set(replication) == {str(year) for year in range(2027, 2042)}
    for row in replication.values():
        for measure in ("debt", "interest", "rate"):
            assert np.isfinite(row[measure]["gap"])
