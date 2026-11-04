"""Run the US debt simulation and write its reproducible outputs."""
import csv
import json
from pathlib import Path
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

import config as c
from usasim.model import YEARS, load_cbo, simulate


def write_csv(path, fields, rows):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def first_crossing(condition):
    return np.where(condition.any(axis=1), YEARS[condition.argmax(axis=1)], 0)


def distribution(first):
    return {str(y): int(np.count_nonzero(first == y)) for y in YEARS if np.any(first == y)} | {'never': int(np.count_nonzero(first == 0))}


def summary(data, cbo):
    debt, interest = data['debt'], data['interest']
    ss, medicare, defense = (cbo[k][None, :] for k in ('social_security_pct', 'medicare_net_pct', 'defense_pct'))
    conditions = {
        'debt_above_1946_record': debt > c.RECORD_1946,
        'debt_above_125': debt > 125,
        'debt_above_150': debt > 150,
        'debt_above_200': debt > 200,
        'y10_above_6': data['y10'] > 6,
        'interest_above_social_security': interest > ss,
        'interest_above_medicare': interest > medicare,
        'interest_above_twice_defense': interest > 2 * defense,
        'interest_above_20_percent_revenue': data['interest_rev'] > 20,
        'interest_above_25_percent_revenue': data['interest_rev'] > 25,
    }
    # Events concern the simulated years, not the initial observation.
    probabilities = {f'{key}_any_year': float(np.mean(value[:, 1:].any(axis=1))) for key, value in conditions.items()}
    probabilities.update(debt_2041_above_initial=float(np.mean(debt[:, -1] > c.B0)),
                         debt_above_1946_record_by_2028=float(np.mean(conditions['debt_above_1946_record'][:, 1:3].any(axis=1))),
                         interest_above_medicare_2027=float(np.mean(conditions['interest_above_medicare'][:, 1])))
    crossings = {}
    for key in ('debt_above_1946_record', 'debt_above_150', 'interest_above_social_security', 'interest_above_25_percent_revenue'):
        condition = conditions[key].copy(); condition[:, 0] = False
        first = first_crossing(condition); crossed = first[first != 0]
        crossings[key] = {'median_year_conditional_on_crossing': float(np.median(crossed)) if crossed.size else None, 'counts': distribution(first)}
    last = lambda key: float(np.median(data[key][:, -1]))
    cumulative = last('cumulative_interest')
    i, g = last('rate') / 100, last('growth') / 100
    return {
        'debt_percent_gdp': {str(year): dict(zip(('p10', 'median', 'p90'), map(float, np.percentile(debt[:, year - YEARS[0]], [10, 50, 90])))) for year in (2028, 2031, 2036, 2041)},
        'probabilities': probabilities,
        'first_crossing': crossings,
        'medians_2041': {'interest_percent_gdp': last('interest'), 'interest_percent_revenue': last('interest_rev'),
                         'interest_billion_2026_dollars': last('real_interest'),
                         'interest_over_defense': float(np.median(interest[:, -1] / defense[0, -1])),
                         'interest_over_social_security': float(np.median(interest[:, -1] / ss[0, -1])),
                         'y10': last('y10'), 'effective_rate': last('rate'), 'deficit_percent_gdp': last('deficit')},
        'median_paths': {key: np.median(data[key], axis=0).tolist() for key in ('debt', 'deficit', 'interest', 'interest_rev', 'rate', 'y10')},
        'cumulative_interest_median': {'billion_2026_dollars': cumulative, 'dollars_per_household': cumulative * 1000 / c.HOUSEHOLDS_MILLIONS, 'dollars_per_person': cumulative * 1000 / c.POPULATION_MILLIONS},
        'stabilising_primary_balance_2041_percent_gdp': float((i - g) / (1 + g) * np.median(debt[:, -2])),
    }


def write_scenario(out, name, data, central, seed):
    keys = ('debt', 'interest', 'rate', 'y10', 'bill', 'primary', 'deficit', 'interest_rev')
    qs = {k: np.percentile(data[k], c.PERCENTILES, axis=0) for k in keys}
    rows = [{'year': int(y), **{f'{k}_p{p}': float(qs[k][j, t]) for k in keys for j, p in enumerate(c.PERCENTILES)}} for t, y in enumerate(YEARS)]
    write_csv(out / f'fan_{name}.csv', rows[0].keys(), rows)
    ids = np.random.default_rng(seed + 2).choice(len(data['debt']), size=min(c.PATH_COUNT, len(data['debt'])), replace=False)
    keys = ('debt', 'y10', 'interest', 'interest_rev')
    rows = ({'run_id': int(i), 'year': int(y), **{k: float(data[k][i, t]) for k in keys}} for i in ids for t, y in enumerate(YEARS))
    write_csv(out / f'paths_{name}.csv', ('run_id', 'year', *keys), rows)
    rows = []
    for threshold in (c.RECORD_1946, 125, 150, 200):
        condition = data['debt'] > threshold; condition[:, 0] = False
        rows.extend({'threshold': '200%+' if threshold == 200 else str(threshold), 'year': year, 'count': count} for year, count in distribution(first_crossing(condition)).items())
    write_csv(out / f'break_year_{name}.csv', ('threshold', 'year', 'count'), rows)
    rows = [{'year': int(y), **{k: float(v[0, t]) for k, v in central.items()}} for t, y in enumerate(YEARS)]
    write_csv(out / f'central_{name}.csv', rows[0].keys(), rows)
    q = qs['debt']; fig, ax = plt.subplots(figsize=(9, 5))
    for low, high, color, label in ((0, 6, '#b9cde0', 'P5–P95'), (1, 5, '#7fa9ce', 'P10–P90'), (2, 4, '#4883b5', 'P25–P75')):
        ax.fill_between(YEARS, q[low], q[high], color=color, label=label)
    ax.plot(YEARS, q[3], color='#103b61', label='Median'); ax.plot(YEARS, central['debt'][0], '--', color='#c0392b', label='Zero shocks')
    ax.set(title=f'Scenario {name}: federal debt held by the public', ylabel='% of GDP', xlabel='Fiscal year'); ax.legend(); ax.grid(alpha=.2); fig.tight_layout()
    fig.savefig(out / 'preview' / f'fan_{name}.png', dpi=120); plt.close(fig)
    return q[3]


def validation(data, central, cbo, seed, out):
    replication = simulate('B', 1, seed, zero_shocks=True, overrides={'replication': True})
    rows = {}
    for t, y in enumerate(YEARS[1:], 1):
        row = {}
        for key, reference in (('debt', 'debt_pct'), ('interest', 'net_interest_pct'), ('rate', 'avg_rate')):
            model, baseline = float(replication[key][0, t]), float(cbo[reference][t])
            row[key] = {'model': model, 'cbo': baseline, 'gap': model - baseline}
        rows[str(y)] = row
    fig, ax = plt.subplots(figsize=(9, 5)); ax.plot(YEARS, replication['debt'][0], label='Model replication'); ax.plot(YEARS, cbo['debt_pct'], label='CBO'); ax.set(title='CBO replication', xlabel='Fiscal year', ylabel='Debt, % of GDP'); ax.legend(); ax.grid(alpha=.2); fig.tight_layout(); fig.savefig(out / 'preview' / 'cbo_replication.png', dpi=120); plt.close(fig)
    debt = central['debt'][0]; g = central['growth'][0, 1:] / 100; i = central['rate'][0, 1:] / 100
    lhs = float(np.diff(debt).sum()); rhs = float(np.sum(debt[:-1] * ((1 + i) / (1 + g) - 1) - central['primary'][0, 1:]))
    growth = (data['gdp'][:, 2036 - YEARS[0]] / c.GDP_2024 - 1) * 100
    return {'cbo_replication': rows,
            'today_vs_cbo': {str(y): {'model_debt': float(debt[y-YEARS[0]]), 'cbo_debt': float(cbo['debt_pct'][y-YEARS[0]]), 'gap': float(debt[y-YEARS[0]] - cbo['debt_pct'][y-YEARS[0]])} for y in (2036, 2041)},
            'nominal_gdp_growth_2024_to_2036_percent': {'model_p5': float(np.percentile(growth, 5)), 'model_p95': float(np.percentile(growth, 95)), 'cbo_p5_approx': 25, 'cbo_p95_approx': 100},
            'debt_cone': {'2036': {'model_p10_p50_p90': np.percentile(data['debt'][:, 2036-YEARS[0]], [10, 50, 90]).tolist(), 'cbo_baseline': 120.2, 'cbo_higher_rate': 124.3, 'cbo_high_growth': 109}, '2041': {'cbo_baseline': 131.7, 'cbo_higher_rate': 141.2}},
            'accounting_identity': {'debt_change_sum': lhs, 'snowball_minus_primary_sum': rhs, 'difference': lhs-rhs, 'tolerance': 1e-9, 'passes': abs(lhs-rhs) <= 1e-9}}


def main(n=c.RUNS, sensitivity_n=c.SENSITIVITY_RUNS, seed=c.SEED, out_dir='out'):
    start = time.perf_counter(); out = Path(out_dir); (out / 'preview').mkdir(parents=True, exist_ok=True)
    cbo = load_cbo(); summaries, medians = {}, {}
    for name in 'ABCD':
        data = simulate(name, n, seed); central = simulate(name, 1, seed, zero_shocks=True)
        summaries[name] = summary(data, cbo); medians[name] = write_scenario(out, name, data, central, seed)
        if name == 'B': (out / 'validation.json').write_text(json.dumps(validation(data, central, cbo, seed, out), indent=2, allow_nan=False) + '\n')
    (out / 'summary.json').write_text(json.dumps(summaries, indent=2, allow_nan=False) + '\n')
    fig, ax = plt.subplots(figsize=(9, 5))
    for name, median in medians.items(): ax.plot(YEARS, median, label=f'Scenario {name}')
    ax.set(title='Median federal debt by scenario', ylabel='% of GDP', xlabel='Fiscal year'); ax.legend(); ax.grid(alpha=.2); fig.tight_layout(); fig.savefig(out / 'preview' / 'median_comparison.png', dpi=120); plt.close(fig)
    variants = [('dsir', x) for x in (.01, .035, .05)] + [('kappa', x) for x in (.10, .50)] + [('real_growth_shift', x) for x in (-.5, .5)] + [('short_share', x) for x in (.15, .35)] + [('rollover', x) for x in (.10, .17)] + [('slippage_sd', x) for x in (.25, 1.0)] + [('theta', x) for x in (.25, .55)] + [('history_start', 1960), ('x0', 0)]
    rows = []
    for key, value in variants:
        data = simulate('B', sensitivity_n, seed, overrides={key: value})
        rows.append({'parameter': key, 'value': value, 'median_debt_2041': float(np.median(data['debt'][:, -1])), 'probability_debt_above_150_any_year': float(np.mean((data['debt'][:, 1:] > 150).any(axis=1))), 'probability_interest_above_social_security_any_year': float(np.mean((data['interest'][:, 1:] > cbo['social_security_pct'][None, 1:]).any(axis=1))), 'probability_y10_above_6_any_year': float(np.mean((data['y10'][:, 1:] > 6).any(axis=1)))})
    write_csv(out / 'sensitivity.csv', rows[0].keys(), rows)
    print(f'Completed in {time.perf_counter()-start:.2f} seconds ({n:,} runs per scenario; {sensitivity_n:,} per sensitivity).')


if __name__ == '__main__':
    main()
