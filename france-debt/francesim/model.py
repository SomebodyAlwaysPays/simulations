"""Vectorised debt dynamics and historical macro bootstrap."""
import csv
import json
from pathlib import Path

import numpy as np
import config as c

DATA = Path(__file__).resolve().parents[1] / 'research' / 'data'
YEARS = np.arange(c.START_YEAR, c.END_YEAR + 1)


def historical_deviations():
    """Load the joint 1991–2025 observations from the supplied files."""
    def world_bank(indicator):
        records = json.loads((DATA / f'wb_{indicator}.json').read_text())[1]
        return {int(r['date']): float(r['value']) for r in records if r['value'] is not None}

    growth = world_bank('NY.GDP.MKTP.KD.ZG')
    inflation = world_bank('NY.GDP.DEFL.KD.ZG')
    monthly = {}
    with (DATA / 'fred_de.csv').open() as f:
        for row in csv.DictReader(f):
            try:
                monthly.setdefault(int(row['observation_date'][:4]), []).append(float(row['IRLTLT01DEM156N']))
            except ValueError:
                continue
    annual = {year: np.mean(values) for year, values in monthly.items()}
    years = range(c.HISTORY_START, c.HISTORY_END + 1)
    values = np.array([[growth[y], inflation[y], annual[y] - annual[y-1]] for y in years])
    return values - values.mean(axis=0)


def bootstrap_years(n, seed=c.SEED):
    """Sample consecutive two-year blocks, wrapping around historical years."""
    rng = np.random.default_rng(seed)
    horizon = c.END_YEAR - c.START_YEAR
    count = c.HISTORY_END - c.HISTORY_START + 1
    starts = rng.integers(0, count, size=(n, (horizon + c.BLOCK_LENGTH - 1) // c.BLOCK_LENGTH))
    return ((starts[:, :, None] + np.arange(c.BLOCK_LENGTH)) % count).reshape(n, -1)[:, :horizon] + c.HISTORY_START


def debt_next(debt, rate, growth, primary):
    """Apply the step 7 debt accumulation identity."""
    return debt * (1 + rate / 100) / (1 + growth / 100) - primary


def simulate(scenario, n, seed=c.SEED, zero_shocks=False, overrides=None):
    """Simulate one scenario; repeated seeds share all random draws."""
    p = {'real_growth': c.REAL_GROWTH, 'bund_long_run': c.BUND_LONG_RUN,
         'spread_low': c.SPREAD_LOW, 'spread_high': c.SPREAD_HIGH,
         'spread_intercept': c.SPREAD_INTERCEPT, 'refinance': c.REFINANCE,
         'slippage_sd': c.SLIPPAGE_SD}
    p.update(overrides or {})
    history = historical_deviations()
    years = bootstrap_years(n, seed)
    rng = np.random.default_rng(seed + 1)
    spread_noise = rng.normal(0, c.SPREAD_SD, (n, len(YEARS)-1))
    fiscal_noise = rng.normal(0, p['slippage_sd'], (n, len(YEARS)-1))
    if zero_shocks:
        spread_noise.fill(0)
        fiscal_noise.fill(0)
    keys = ('debt', 'rate', 'cash_rate', 'oat', 'spread', 'primary', 'interest', 'growth', 'gdp', 'real_interest', 'cumulative_interest')
    result = {k: np.zeros((n, len(YEARS))) for k in keys}
    b, rate, cash_rate, oat, spread, primary, interest, growth, gdp, real_interest, cumulative = (result[k] for k in keys)
    b[:, 0], rate[:, 0], spread[:, 0], primary[:, 0], gdp[:, 0] = c.B0, c.RATE0, c.SPREAD0, c.PB0, c.GDP0
    cash_rate[:, 0] = c.RATE0
    oat[:, 0] = c.BUND0 + c.SPREAD0
    interest[:, 0] = c.DEFICIT0 + c.PB0
    real_interest[:, 0] = interest[:, 0] * c.GDP0 / 100
    bund = np.full(n, c.BUND0)
    deficit = np.full(n, c.DEFICIT0)
    fiscal = np.zeros(n)
    price = np.ones(n)

    def equilibrium(debt):
        return (p['spread_intercept'] + p['spread_low'] * (np.minimum(debt, c.SPREAD_KINK) - c.B0)
                + p['spread_high'] * np.maximum(debt - c.SPREAD_KINK, 0))

    for t in range(1, len(YEARS)):
        # Step 1: the same sampled historical year supplies all three macro deviations.
        macro = np.zeros((n, 3)) if zero_shocks else history[years[:, t-1] - c.HISTORY_START]
        real = p['real_growth'] + macro[:, 0]
        inflation = c.DEFLATOR + macro[:, 1]
        growth[:, t] = ((1 + real / 100) * (1 + inflation / 100) - 1) * 100
        # Step 2: mean-reverting German yield.
        bund = bund + c.BUND_SPEED * (p['bund_long_run'] - bund) + macro[:, 2]
        # Step 3: spread adjusts to debt with persistence and a floor.
        spread[:, t] = np.maximum(c.SPREAD_FLOOR, equilibrium(b[:, t-1]) + c.SPREAD_PERSISTENCE * (spread[:, t-1] - equilibrium(b[:, max(0, t-2)])) + spread_noise[:, t-1])
        # Step 4: OAT yield combines Bund and spread.
        oat[:, t] = bund + spread[:, t]
        # Step 5: refinance maturing debt and the previous year's deficit.
        share = p['refinance'] + np.maximum(0, deficit) / b[:, t-1]
        rate[:, t] = (1 - share) * rate[:, t-1] + share * oat[:, t]
        # Mid-year convention: debt refinanced during the year pays the new yield for half of it.
        cash_rate[:, t] = rate[:, t-1] + c.MIDYEAR * share * (oat[:, t] - rate[:, t-1])
        # Step 6: fiscal plans plus cycle and persistent slippage.
        fiscal = c.SLIPPAGE_PERSISTENCE * fiscal + fiscal_noise[:, t-1]
        plan = {'A': c.PB0, 'B': min(c.PB0 + c.PLAN_B_STEP * t, c.PLAN_B_CAP),
                'C': c.PLAN_C[min(t-1, len(c.PLAN_C)-1)], 'D': min(c.PB0 + c.PLAN_D_STEP * t, c.PLAN_D_CAP)}[scenario]
        primary[:, t] = plan + c.BUDGET_CYCLE * (real - c.REAL_GROWTH) + fiscal
        # Step 7: debt accumulation.
        b[:, t] = debt_next(b[:, t-1], cash_rate[:, t], growth[:, t], primary[:, t])
        # Step 8: interest, deficit, GDP and interest in 2026 euros.
        interest[:, t] = (cash_rate[:, t] / 100) * b[:, t-1] / (1 + growth[:, t] / 100)
        deficit = interest[:, t] - primary[:, t]
        gdp[:, t] = gdp[:, t-1] * (1 + growth[:, t] / 100)
        price *= 1 + inflation / 100
        real_interest[:, t] = interest[:, t] * gdp[:, t] / 100 / price
        cumulative[:, t] = cumulative[:, t-1] + real_interest[:, t]
    return result
