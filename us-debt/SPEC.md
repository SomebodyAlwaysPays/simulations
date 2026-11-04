# US federal debt Monte Carlo: model spec (v1)

Purpose: a transparent, reproducible simulation of US federal debt held by the public for fiscal years 2027–2041 (15 years), run 100,000 times per fiscal scenario. It is the first model published in the Somebody Always Pays simulation series; France comes next.

## Deliverables (all inside this `model/` folder)

- `usasim/` Python package (numpy only; matplotlib only for previews). Python 3.11+. No pandas, no other dependencies.
- `run.py`: runs everything with a fixed seed (default 20261103) and writes `out/`.
- `config.py`: every parameter from the inputs table, with a source comment. No magic numbers in the code.
- `tests/` (pytest): see "Tests".
- `out/` (generated, re-creatable): `summary.json`, `fan_<S>.csv`, `paths_<S>.csv`, `break_year_<S>.csv`, `central_<S>.csv`, `validation.json`, `sensitivity.csv`, `preview/` (one fan chart PNG per scenario, one chart comparing the four medians, one chart of the CBO replication vs CBO). Details below.
- `README.md` for a curious viewer: what the model does, the equations, each assumption and its source, how to run it, limitations, implementation choices. MIT licence.

## Data files (read-only, in `data/`)

- `cbo_paths.csv`: CBO projections by fiscal year 2026–2041 (columns documented in `cbo_paths_SOURCES.md`): `debt_pct`, `primary_balance_pct`, `real_growth`, `deflator`, `y10`, `bill3m`, `avg_rate`, `net_interest_pct`, `revenue_pct`, `customs_pct`, `social_security_pct`, `medicare_net_pct`, `defense_pct`, `gdp_bn`.
- `fred_GDPC1.csv` (real GDP, quarterly, columns observation_date,GDPC1), `fred_GDPDEF.csv` (GDP deflator, quarterly), `fred_GS10.csv` (10-year Treasury constant maturity, monthly). Annual values are calendar-year averages of the quarterly or monthly observations; growth and inflation are percent changes of those annual averages; the 10-year change is the difference of annual averages.

## State at the start (end of fiscal year 2026, 30 Sep 2026)

| Symbol | Value | Source |
|---|---|---|
| B0, debt held by the public % GDP | 100.588 | Treasury Debt to the Penny, 30 Sep 2026: $32,425.0bn / FY2026 nominal GDP |
| Y0, FY2026 nominal GDP | $32,235.5bn | BEA via FRED `GDP`: average of SAAR quarters 2025Q4–2026Q3 |
| I0, effective rate on the stock | 3.355% | Monthly Treasury Statement (MTS) Sep 2026: FY2026 net interest $1,051.8bn / average debt held by the public (end-FY2025 $30,277.8bn, end-FY2026 $32,425.0bn) |
| BILL0, FY2026 average 3-month bill | 3.686% | FRED `TB3MS`, Oct 2025–Sep 2026 average |
| Y10_NOW, 10-year yield today | 5.13% | FRED `GS10`, October 2026 average |
| D0, FY2026 deficit | 6.181% | MTS: $1,992.5bn |
| PB0_UNDERLYING | −2.493% | MTS: primary deficit $940.7bn (−2.918%) excluding one-off tariff refunds of $137.1bn (FY2026 customs refunds $144.6bn minus FY2025's $7.5bn) |
| D0_UNDERLYING | 5.756% | same adjustment |
| SHORT_SHARE β | 0.2446 | Monthly Statement of the Public Debt (MSPD), 30 Sep 2026: bills $7.118tn + floating-rate notes $0.708tn of $32.0tn marketable |
| ROLLOVER m | 0.132 | MSPD: notes, bonds and TIPS maturing by 30 Sep 2027 = $3.19tn of $24.17tn coupon debt (weighted average maturity of all marketable debt 5.8 years) |
| POPULATION | 343.1 million | BEA via FRED `POPTHM`, Sep 2026 |
| HOUSEHOLDS | 134.79 million | Census CPS ASEC 2025 via FRED `TTLHH` |
| RECORD_1946 | 106.1% | OMB Historical Table 7.1 (FY2027 budget): debt held by the public, end of FY1946 |

## Each simulated year t = 2027..2041

All rates in percent per year, ratios in % of GDP. `cbo.X[t]` means the column X of `cbo_paths.csv` for year t.

1. Macro draw. Joint block bootstrap (block length 2, wrap-around, independent block starts per run) of historical calendar years 1985–2025. For each year, deviations from the 1985–2025 window means of: real GDP growth, GDP-deflator inflation, and the annual change in the 10-year yield (1985's change uses the 1984 average). The same sampled year supplies all three. Then real_t = cbo.real_growth[t] + dev_r, infl_t = cbo.deflator[t] + dev_p, g_t = (1 + real_t)(1 + infl_t) − 1 (fractions inside the formula). Window 1985–2025 = the post-Volcker monetary regime (independent Fed, inflation near 2% targets), the same regime CBO uses to estimate debt effects on rates; it still contains 1990–91, 2001, 2008–09, 2020 and the 2021–22 inflation and rate shock. Sensitivity: 1960–2025.
2. 10-year yield. Deviation from CBO's path: x_t = (1 − κ) x_{t−1} + dev_y, with x_2026 = Y10_NOW − cbo.y10[2027] and κ = 0.25 (ASSUMPTION, same speed as France's Bund). Debt premium from CBO's own estimate: y_t = max(0.5, cbo.y10[t] + x_t + DSIR × (b_{t−1} − cbo.debt_pct[t−1])), DSIR = 0.02 (2 basis points per point of debt above CBO's projected path; CBO Working Paper 2024-05, Neveu & Schafer, Dec 2024). Using the gap from CBO's own debt path avoids double counting: CBO's rate forecast already includes the debt CBO projects. For t = 2027, b_{t−1} = B0 and the CBO reference is cbo.debt_pct[2026].
3. Bill rate: s_t = max(0, cbo.bill3m[t] + x_t) (same market shock, no debt premium).
4. Refinancing. A share β of the debt (bills and floating notes) reprices every year at s_t. The rest is coupon debt with stock rate c: share_t = m + max(0, d_{t−1}) / b_{t−1} of it is new each year (maturing notes and bonds plus the previous year's deficit) and pays y_t. c_t = (1 − share_t) c_{t−1} + share_t × y_t. Mid-year convention (as France): the cash coupon rate in year t is cc_t = c_{t−1} + 0.5 × share_t × (y_t − c_{t−1}). Effective cash rate i_t = β s_t + (1 − β) cc_t. Start: c_2026 = (I0 − β × BILL0) / (1 − β); d_2026 = D0.
5. Interest: int_t = i_t / 100 × b_{t−1} / (1 + g_t/100) (% of GDP).
6. Primary balance: pb_t = plan_t(scenario) + θ × (real_t − cbo.real_growth[t]) + u_t, with θ = 0.4 (CBO automatic-stabilizer data, Aug 2026: the stabilizers' effect on the deficit has been 0.32–0.51 of the GDP gap in recessions; ASSUMPTION that a one-year growth shortfall maps one-for-one into the gap), u_t = 0.5 u_{t−1} + ε_t, ε_t ~ N(0, 0.5) (persistent fiscal slippage; ASSUMPTION, as France).
7. Debt: b_t = b_{t−1} × (1 + i_t/100) / (1 + g_t/100) − pb_t.
8. Bookkeeping: deficit d_t = int_t − pb_t. GDP Y_t = Y_{t−1}(1 + g_t). Interest in 2026 dollars = int_t × Y_t / 100 / P_t, P_t = cumulative product of (1 + infl). Revenue share rev_t = cbo.revenue_pct[t] − REV_ADJ(scenario); interest share of revenue = int_t / rev_t. Comparisons with programs use CBO's paths (same in every scenario): Social Security, Medicare net of premiums, defense.

No default, no Fed rescue, no market panic jump, no feedback from deficits to growth, no TIPS indexation, no stock-flow adjustments (CBO's "other means of financing"). Cap nothing; report runs above 200% as "200%+".

## Scenarios (plan_t, primary balance in % of GDP; negative = deficit)

| Id | Name | One line for the screen | plan_t | REV_ADJ |
|---|---|---|---|---|
| A | Frozen | This year's budget before interest, every year | −2.493 every year (FY2026 underlying primary deficit) | 0.176 |
| B | Current law | CBO's official path, updated for this summer's tariffs | cbo.primary_balance_pct[t] − 0.176 (CBO blog, 20 Aug 2026: tariff changes through 31 Jul 2026 add $0.7tn to primary deficits over 2027–2036 = 0.176% of that period's GDP; held after 2036) | 0.176 |
| C | No tariffs | The new tariffs go, as the emergency ones already did | B − 0.373 (CBO blog, 5 Mar 2026: removing 8 points of effective tariff rate = $1.6tn of primary deficits over 2026–2036 = 0.373% of GDP; CBO's effective rate is 10% now vs 2% in 2024, also 8 points) | 0.549 |
| D | 3% deficit | Cut the deficit to 3% of GDP by 2030 and hold it there | int_t − target_t, target_t = max(3.0, 5.756 − 0.75 × (t − 2026)) → 5.0, 4.25, 3.5, then 3.0 from 2030 (Bessent, Jan 2026: "shave 50–100 bp off the deficit-to-GDP ratio every year", aiming for 3%; midpoint used) | 0.176 |

In D the plan reacts to that year's interest bill; cycle and slippage still apply, so the realised deficit fluctuates around the target. 100,000 runs per scenario with common random numbers (same seed, same draws in all scenarios).

## Outputs: `summary.json` (per scenario)

- Debt % GDP: median, P10, P90 in 2028, 2031, 2036, 2041.
- Probabilities: debt_2041 > B0; debt > 106.1 (1946 record) in any year; debt > 106.1 by FY2028 (before the November 2028 election); debt > 125, 150, 200 in any year; y10 > 6% in any year; interest > Social Security in any year; interest > Medicare (net) in 2027 and in any year; interest > 2 × defense in any year; interest > 20% and > 25% of revenue in any year.
- First-crossing medians (conditional on crossing) and count distributions for: debt > 106.1, debt > 150, interest > Social Security, interest > 25% of revenue.
- Medians for 2041: interest % GDP, % of revenue, $bn of 2026 dollars, interest / defense, interest / Social Security; y10; effective rate; deficit % GDP.
- Median paths 2026–2041 for debt, deficit, interest % GDP, interest % revenue, effective rate, y10 (lists of 16 numbers; the median of each year separately).
- Cumulative interest 2027–2041 in 2026 dollars, median: total $bn, per household, per person.
- Debt-stabilising primary balance in 2041 at the median: (i − g)/(1 + g) × b, using median 2041 rate and growth and median 2040 debt.

## Other outputs

- `fan_<S>.csv`: per year 2026–2041, P5, P10, P25, P50, P75, P90, P95 of debt, interest (% GDP), effective rate, y10, bill rate, primary balance, deficit, interest share of revenue.
- `paths_<S>.csv`: 300 random full paths (run_id, year, debt, y10, interest, interest_rev).
- `break_year_<S>.csv`: first year above 106.1, 125, 150, 200 (label 200 as "200%+"), or "never".
- `central_<S>.csv`: all shocks zero (bootstrap deviations, ε, and x shocks; x still decays from x_2026).

## Validation (`validation.json`)

1. CBO replication, deterministic: start from CBO's own FY2026 values (b = 100.605, I0 = 3.404, BILL0 = 3.432, d_2026 = 5.807, x_2026 = 0), plan = cbo.primary_balance_pct (no tariff adjustment), growth, inflation, y10 and bills exactly CBO's. Report model vs CBO for every year 2027–2041: debt, net interest % GDP (vs cbo.net_interest_pct), effective rate (vs cbo.avg_rate), and the gaps (model − CBO). Do not tune any parameter to close a gap.
2. Today vs CBO: the zero-shock scenario-B path from today's actual start (higher rates than CBO assumed) next to CBO's debt path; report the 2036 and 2041 gaps.
3. Cone checks (report only):
   a. Cumulative nominal GDP growth from FY2024 (CBO: $28,947.9bn) to FY2036 in scenario B: model P5 and P95, next to CBO's simulations (blog 27 Feb 2026: about 5% of simulations above +100% and about 5% below +25% since end-2024).
   b. Scenario B debt in 2036 (P10, P50, P90) next to CBO baseline 120.2, CBO higher-rate scenario 124.3 (rates rising to +1 pp, letter of 24 Sep 2026) and CBO's 95th-percentile-growth case 109 (blog 27 Feb 2026). For 2041: CBO baseline 131.7, higher-rate 141.2.
4. Accounting identity on the B central path: sum of debt changes = sum of (snowball − primary balance), tolerance 1e-9.

## Sensitivity (`sensitivity.csv`)

Scenario B, 20,000 runs each, one change at a time; columns: parameter, value, median debt 2041, P(debt > 150 any year), P(interest > Social Security any year), P(y10 > 6 any year):
- DSIR 0.01 and 0.035 (Laubach 2009, 3–4 bp) and 0.05;
- κ 0.10 and 0.50;
- central real growth −0.5 and +0.5 pp every year (cycle term keeps measuring against the shifted path);
- short share β 0.15 and 0.35; rollover m 0.10 and 0.17;
- slippage sd 0.25 and 1.0; θ 0.25 and 0.55;
- bootstrap window 1960–2025;
- start the 10-year on CBO's path (x_2026 = 0).

## Tests

- Zero-shock run equals `central_<S>.csv` exactly.
- Same seed → byte-identical `summary.json`.
- With i = g and pb = 0 every year, debt stays at B0.
- Common random numbers: scenario C debt ≥ scenario B debt in every run and year; D's 2041 median < B's.
- In D with zero shocks, the deficit equals target_t every year to 1e-9.
- Bootstrap draws only years 1985–2025 (and 1960–2025 under the window override).
- The CBO replication runs and reports a gap for every year 2027–2041 (no tolerance asserted).

## Style

Readable code with short docstrings; each equation carries a one-line comment with its step number in this spec. Vectorise over runs with numpy; the full run should take under a minute.
