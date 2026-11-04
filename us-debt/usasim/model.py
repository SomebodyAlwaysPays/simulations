"""Vectorised US debt dynamics and historical macro bootstrap."""
import csv
from functools import lru_cache
from pathlib import Path

import numpy as np
import config as c

DATA = Path(__file__).resolve().parents[1] / 'data'
YEARS = np.arange(c.START_YEAR, c.END_YEAR + 1)


@lru_cache(maxsize=1)
def load_cbo():
    """Read CBO paths aligned to the simulation years."""
    with (DATA / 'cbo_paths.csv').open(newline='') as f:
        rows = [row for row in csv.DictReader(f) if c.START_YEAR <= int(row['year']) <= c.END_YEAR]
    if [int(row['year']) for row in rows] != list(YEARS):
        raise ValueError('CBO paths must contain each simulation year in order')
    return {key: np.array([float(row[key]) for row in rows]) for key in rows[0]}


@lru_cache(maxsize=None)
def historical_deviations(history_start=c.HISTORY_START):
    """Return centered growth, inflation and yield changes for historical years."""
    def annual(filename, column):
        values = {}
        with (DATA / filename).open(newline='') as f:
            for row in csv.DictReader(f):
                try:
                    values.setdefault(int(row['observation_date'][:4]), []).append(float(row[column]))
                except ValueError:
                    continue
        return {year: np.mean(data) for year, data in values.items()}

    gdp = annual('fred_GDPC1.csv', 'GDPC1')
    prices = annual('fred_GDPDEF.csv', 'GDPDEF')
    yields = annual('fred_GS10.csv', 'GS10')
    values = np.array([[100 * (gdp[y] / gdp[y - 1] - 1),
                        100 * (prices[y] / prices[y - 1] - 1),
                        yields[y] - yields[y - 1]]
                       for y in range(history_start, c.HISTORY_END + 1)])
    return values - values.mean(axis=0)


def bootstrap_years(n, seed=c.SEED, history_start=c.HISTORY_START):
    """Sample consecutive two-year blocks, wrapping around the window."""
    rng = np.random.default_rng(seed)
    horizon = c.END_YEAR - c.START_YEAR
    count = c.HISTORY_END - history_start + 1
    starts = rng.integers(0, count, size=(n, (horizon + c.BLOCK_LENGTH - 1) // c.BLOCK_LENGTH))
    return ((starts[:, :, None] + np.arange(c.BLOCK_LENGTH)) % count).reshape(n, -1)[:, :horizon] + history_start


def debt_next(debt, rate, growth, primary):
    """Apply the step 7 debt accumulation identity."""
    return debt * (1 + rate / 100) / (1 + growth / 100) - primary


def simulate(scenario, n, seed=c.SEED, zero_shocks=False, overrides=None):
    """Simulate one fiscal scenario; equal seeds share all random draws."""
    if scenario not in 'ABCD' or len(scenario) != 1:
        raise ValueError('Unknown scenario')
    p = {'dsir': c.DSIR, 'kappa': c.KAPPA, 'real_growth_shift': 0,
         'short_share': c.SHORT_SHARE, 'rollover': c.ROLLOVER,
         'slippage_sd': c.SLIPPAGE_SD, 'theta': c.THETA,
         'history_start': c.HISTORY_START, 'replication': False}
    p.update(overrides or {})
    cbo = load_cbo()
    sampled = bootstrap_years(n, seed, p['history_start'])
    history = historical_deviations(p['history_start'])
    fiscal_noise = np.random.default_rng(seed + 1).normal(0, p['slippage_sd'], (n, len(YEARS) - 1))
    keys = ('debt', 'rate', 'coupon_rate', 'y10', 'bill', 'primary', 'interest', 'deficit',
            'growth', 'real_growth', 'inflation', 'gdp', 'real_interest', 'cumulative_interest', 'interest_rev')
    result = {key: np.zeros((n, len(YEARS))) for key in keys}
    b, rate, coupon, y10, bill, primary, interest, deficit, growth, real_growth, inflation, gdp, real_interest, cumulative, interest_rev = (result[k] for k in keys)
    replication = p['replication']
    b[:, 0] = c.CBO_B0 if replication else c.B0
    rate[:, 0] = c.CBO_RATE0 if replication else c.RATE0
    bill[:, 0] = c.CBO_BILL0 if replication else c.BILL0
    deficit[:, 0] = c.CBO_DEFICIT0 if replication else c.DEFICIT0
    primary[:, 0] = cbo['primary_balance_pct'][0] if replication else c.PB0_ACTUAL
    interest[:, 0] = deficit[:, 0] + primary[:, 0]
    gdp[:, 0] = cbo['gdp_bn'][0] if replication else c.GDP0
    y10[:, 0] = cbo['y10'][0] if replication else c.Y10_NOW
    coupon[:, 0] = (rate[:, 0] - p['short_share'] * bill[:, 0]) / (1 - p['short_share'])
    real_interest[:, 0] = interest[:, 0] * gdp[:, 0] / 100
    rev_adj = 0 if replication else c.TARIFF_ADJ + (c.NO_TARIFF_ADJ if scenario == 'C' else 0)
    interest_rev[:, 0] = interest[:, 0] / (cbo['revenue_pct'][0] - rev_adj) * 100
    x = np.full(n, p.get('x0', 0 if replication else c.Y10_NOW - cbo['y10'][1]), dtype=float)
    fiscal = np.zeros(n)
    price = np.ones(n)
    for t in range(1, len(YEARS)):
        # Step 1: joint block bootstrap and nominal growth.
        macro = np.zeros((n, 3)) if zero_shocks or replication else history[sampled[:, t - 1] - p['history_start']]
        baseline_real = cbo['real_growth'][t] + p['real_growth_shift']
        real_growth[:, t] = baseline_real + macro[:, 0]
        inflation[:, t] = cbo['deflator'][t] + macro[:, 1]
        growth[:, t] = ((1 + real_growth[:, t] / 100) * (1 + inflation[:, t] / 100) - 1) * 100
        # Step 2: yield shock reverts and debt premium tracks the CBO debt gap.
        x = (1 - p['kappa']) * x + macro[:, 2]
        y10[:, t] = cbo['y10'][t] if replication else np.maximum(c.YIELD_FLOOR, cbo['y10'][t] + x + p['dsir'] * (b[:, t - 1] - cbo['debt_pct'][t - 1]))
        # Step 3: bills share the market shock, without the debt premium.
        bill[:, t] = cbo['bill3m'][t] if replication else np.maximum(c.BILL_FLOOR, cbo['bill3m'][t] + x)
        # Step 4: coupon stock reprices, with a mid-year cash convention.
        share = p['rollover'] + np.maximum(0, deficit[:, t - 1]) / b[:, t - 1]
        coupon[:, t] = (1 - share) * coupon[:, t - 1] + share * y10[:, t]
        cash_coupon = coupon[:, t - 1] + c.MIDYEAR * share * (y10[:, t] - coupon[:, t - 1])
        rate[:, t] = p['short_share'] * bill[:, t] + (1 - p['short_share']) * cash_coupon
        # Step 5: interest is measured against current-year GDP.
        interest[:, t] = rate[:, t] / 100 * b[:, t - 1] / (1 + growth[:, t] / 100)
        # Step 6: plans, automatic stabilizers and persistent fiscal slippage.
        fiscal = c.SLIPPAGE_PERSISTENCE * fiscal + (0 if zero_shocks or replication else fiscal_noise[:, t - 1])
        if replication:
            plan = cbo['primary_balance_pct'][t]
        elif scenario == 'A':
            plan = c.PB0
        elif scenario in ('B', 'C'):
            plan = cbo['primary_balance_pct'][t] - c.TARIFF_ADJ - (c.NO_TARIFF_ADJ if scenario == 'C' else 0)
        else:
            target = max(c.TARGET_DEFICIT, c.D0_UNDERLYING - c.TARGET_STEP * t)
            plan = interest[:, t] - target
        primary[:, t] = plan + p['theta'] * (real_growth[:, t] - baseline_real) + fiscal
        # Step 7: debt accumulation.
        b[:, t] = debt_next(b[:, t - 1], rate[:, t], growth[:, t], primary[:, t])
        # Step 8: deficit, GDP, real interest and revenue share.
        deficit[:, t] = interest[:, t] - primary[:, t]
        gdp[:, t] = gdp[:, t - 1] * (1 + growth[:, t] / 100)
        price *= 1 + inflation[:, t] / 100
        real_interest[:, t] = interest[:, t] * gdp[:, t] / 100 / price
        cumulative[:, t] = cumulative[:, t - 1] + real_interest[:, t]
        interest_rev[:, t] = 100 * interest[:, t] / (cbo['revenue_pct'][t] - rev_adj)
    return result
