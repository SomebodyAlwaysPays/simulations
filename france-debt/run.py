"""Generate simulation outputs from the local historical data."""
import csv
import json
from pathlib import Path
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

import config as c
from francesim.model import YEARS, debt_next, simulate


def write_csv(path, fieldnames, rows):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def first_crossing(data, threshold):
    crossed = data > threshold
    return np.where(crossed.any(axis=1), YEARS[np.argmax(crossed, axis=1)], 0)


def distribution(first):
    return {str(year): int(np.count_nonzero(first == year)) for year in YEARS if np.any(first == year)} | {'never': int(np.count_nonzero(first == 0))}


def summary(data):
    debt = data['debt']
    result = {'debt_percent_gdp': {str(year): dict(zip(('p10', 'median', 'p90'), map(float, np.percentile(debt[:, year-c.START_YEAR], [10, 50, 90])))) for year in (2031, 2036, 2041)}}
    result['probabilities'] = {'debt_2041_above_initial': float(np.mean(debt[:, -1] > c.B0)),
        **{f'debt_above_{x}_any_year': float(np.mean(np.any(debt > x, axis=1))) for x in c.DEBT_THRESHOLDS},
        'spread_above_2_25_any_year': float(np.mean(np.any(data['spread'] > c.SPREAD_THRESHOLD, axis=1))),
        'oat_above_6_any_year': float(np.mean(np.any(data['oat'] > c.OAT_THRESHOLD, axis=1)))}
    med_interest = float(np.median(data['interest'][:, -1]))
    cum = float(np.median(data['cumulative_interest'][:, -1]))
    result['interest_2041_median'] = {'percent_gdp': med_interest, 'percent_revenue': med_interest / c.REVENUE_SHARE * 100,
        'billion_2026_euros': float(np.median(data['real_interest'][:, -1]))}
    result['cumulative_interest_median'] = {'billion_2026_euros': cum, 'euros_per_resident': cum * 1000 / c.POPULATION_MILLIONS}
    result['first_crossing'] = {}
    for threshold in (130, 140):
        first = first_crossing(debt, threshold)
        crossing = first[first > 0]
        result['first_crossing'][str(threshold)] = {'median_year_conditional_on_crossing': float(np.median(crossing)) if len(crossing) else None,
                                                      'counts': distribution(first), 'runs': len(first)}
    # The 2041 stabilising balance uses median 2041 rates/growth and 2040 debt.
    i = np.median(data['rate'][:, -1]) / 100
    g = np.median(data['growth'][:, -1]) / 100
    result['stabilising_primary_balance_2041_percent_gdp'] = float((i-g) / (1+g) * np.median(debt[:, -2]))
    return result


def write_scenario(out, name, data, central, seed):
    fan_keys = ('debt', 'interest', 'rate', 'oat', 'spread', 'primary')
    quantiles = {k: np.percentile(data[k], c.PERCENTILES, axis=0) for k in fan_keys}
    rows = [{'year': int(year), **{f'{k}_p{p}': float(quantiles[k][j, t]) for k in fan_keys for j, p in enumerate(c.PERCENTILES)}} for t, year in enumerate(YEARS)]
    write_csv(out / f'fan_{name}.csv', rows[0].keys(), rows)
    ids = np.random.default_rng(seed + 2).choice(len(data['debt']), size=min(c.PATH_COUNT, len(data['debt'])), replace=False)
    rows = ({'run_id': int(i), 'year': int(year), **{k: float(data[k][i, t]) for k in ('debt', 'oat', 'interest')}} for i in ids for t, year in enumerate(YEARS))
    write_csv(out / f'paths_{name}.csv', ('run_id', 'year', 'debt', 'oat', 'interest'), rows)
    rows = [{'threshold': f'{threshold}%+' if threshold == 200 else str(threshold), 'year': year, 'count': count} for threshold in c.DEBT_THRESHOLDS for year, count in distribution(first_crossing(data['debt'], threshold)).items()]
    write_csv(out / f'break_year_{name}.csv', ('threshold', 'year', 'count'), rows)
    rows = [{'year': int(year), **{k: float(v[0, t]) for k, v in central.items()}} for t, year in enumerate(YEARS)]
    write_csv(out / f'central_{name}.csv', rows[0].keys(), rows)
    fig, ax = plt.subplots(figsize=(9, 5))
    q = quantiles['debt']
    ax.fill_between(YEARS, q[0], q[6], color='#b9cde0', label='P5–P95')
    ax.fill_between(YEARS, q[1], q[5], color='#7fa9ce', label='P10–P90')
    ax.fill_between(YEARS, q[2], q[4], color='#4883b5', label='P25–P75')
    ax.plot(YEARS, q[3], color='#103b61', linewidth=2, label='Median')
    ax.plot(YEARS, central['debt'][0], color='#c0392b', linestyle='--', label='Zero shocks')
    ax.set(title=f'Scenario {name}: government debt', ylabel='% of GDP', xlabel='Year')
    ax.legend(loc='upper left'); ax.grid(alpha=.2); fig.tight_layout()
    fig.savefig(out / 'preview' / f'fan_{name}.png', dpi=120); plt.close(fig)
    return q[3]


def validation(data, central):
    # IMF exercise: fixed Bund and spread, and the same refinance and deficit rules.
    b, rate, deficit = c.IMF_B0, c.RATE0, c.DEFICIT0
    g = ((1+c.IMF_GROWTH/100)*(1+c.IMF_DEFLATOR/100)-1)*100
    replication = {}
    for year, pb, target in zip((2027, 2028), c.PLAN_C[:2], c.IMF_DEBT):
        share = c.REFINANCE + max(0, deficit)/b
        cash = rate + c.MIDYEAR*share*(c.BUND0+c.SPREAD0-rate)
        rate = (1-share)*rate + share*(c.BUND0+c.SPREAD0)
        new_b = debt_next(b, cash, g, pb)
        interest = cash/100*b/(1+g/100)
        deficit = interest-pb
        replication[str(year)] = {'model_debt': float(new_b), 'imf_debt': target, 'gap_model_minus_imf': float(new_b-target)}
        b = new_b
    debt = central['debt'][0]
    snowball = debt[:-1] * ((1+central['cash_rate'][0, 1:]/100)/(1+central['growth'][0, 1:]/100)-1)
    lhs = float(np.diff(debt).sum())
    rhs = float(np.sum(snowball-central['primary'][0, 1:]))
    return {'imf_replication': replication,
            'cone_width_2031': {'model_p90_minus_p10': float(np.diff(np.percentile(data['debt'][:, 2031-c.START_YEAR], [10, 90]))[0]), 'references': c.CONE_REFERENCES},
            'accounting_identity': {'debt_change_sum': lhs, 'snowball_minus_primary_sum': rhs, 'difference': lhs-rhs, 'tolerance': 1e-9, 'passes': abs(lhs-rhs) <= 1e-9}}


def main(n=c.RUNS, sensitivity_n=c.SENSITIVITY_RUNS, seed=c.SEED, out_dir='out'):
    start = time.perf_counter()
    out = Path(out_dir); (out / 'preview').mkdir(parents=True, exist_ok=True)
    summaries, medians = {}, {}
    for name in 'ABCD':
        data = simulate(name, n, seed)
        central = simulate(name, 1, seed, zero_shocks=True)
        summaries[name] = summary(data)
        medians[name] = write_scenario(out, name, data, central, seed)
        if name == 'C':
            (out / 'validation.json').write_text(json.dumps(validation(data, central), indent=2, allow_nan=False) + '\n')
    (out / 'summary.json').write_text(json.dumps(summaries, indent=2, allow_nan=False) + '\n')
    fig, ax = plt.subplots(figsize=(9, 5))
    for name, median in medians.items(): ax.plot(YEARS, median, label=f'Scenario {name}')
    ax.set(title='Median government debt by scenario', ylabel='% of GDP', xlabel='Year')
    ax.legend(); ax.grid(alpha=.2); fig.tight_layout()
    fig.savefig(out / 'preview' / 'median_comparison.png', dpi=120); plt.close(fig)
    variants = [('central_real_growth', {'real_growth': x}) for x in (0.5, 1.5)] + [('bund_long_run', {'bund_long_run': x}) for x in (2.5, 3.5)] + [('spread_slopes', {'spread_low': x, 'spread_high': y}) for x, y in ((0.029, 0.029), (0.086, 0.086))] + [('spread_intercept', {'spread_intercept': x}) for x in (0.9, 1.5)] + [('refinance', {'refinance': x}) for x in (0.10, 0.16)] + [('slippage_sd', {'slippage_sd': x}) for x in (0.25, 1.0)]
    rows = []
    for name, change in variants:
        debt = simulate('C', sensitivity_n, seed, overrides=change)['debt']
        rows.append({'parameter': name, 'value': '/'.join(str(x) for x in change.values()), 'median_debt_2041': float(np.median(debt[:, -1])), 'probability_debt_above_140': float(np.mean(np.any(debt > 140, axis=1)))})
    write_csv(out / 'sensitivity.csv', rows[0].keys(), rows)
    print(f'Completed in {time.perf_counter()-start:.2f} seconds ({n:,} runs per scenario; {sensitivity_n:,} per sensitivity).')


if __name__ == '__main__':
    main()
