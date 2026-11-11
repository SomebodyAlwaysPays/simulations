# France debt Monte Carlo: model spec (v1.2)

Purpose: a transparent, reproducible simulation of France's general-government debt for 2027–2041 (15 years), run 100,000 times per fiscal scenario. It will be published on GitHub and shown in a YouTube video, so every rule must be simple enough to explain in one sentence on screen, and every number must trace to the inputs table below.

## Deliverables (all inside this folder)

- `francesim/` Python package (numpy, pandas; matplotlib only for previews). Python 3.11+. No other dependencies.
- `run.py`: runs everything with a fixed seed (default 20261030) and writes `out/`.
- `config.yaml` or `config.py`: every parameter from the inputs table, with its source comment. No magic numbers in the code.
- `tests/` (pytest): see "Tests".
- `out/` (generated, re-creatable):
  - `summary.json`: per scenario, the headline probabilities and medians listed under "Outputs".
  - `fan_<scenario>.csv`: per year 2026–2041, percentiles P5, P10, P25, P50, P75, P90, P95 of debt (% GDP), interest (% GDP), effective rate, 10y OAT yield, spread, primary balance.
  - `paths_<scenario>.csv`: 300 randomly chosen full paths (debt, OAT, interest) for animation, with a run id.
  - `break_year_<scenario>.csv`: histogram of first year each threshold is crossed (or "never").
  - `central_<scenario>.csv`: the deterministic path with all shocks set to zero.
  - `validation.json` and `sensitivity.csv` (see below).
  - `preview/`: one PNG fan chart per scenario plus one chart comparing the four medians. For review only.
- `README.md`: written for a curious viewer. What the model does, the equations, each assumption and its source, how to run it, known limitations (it has no market panic, no default, no ECB rescue, no inflation-linked debt, no stock-flow adjustments). MIT `LICENSE`.

## State at the start (end-2026)

| Symbol | Value | Source |
|---|---|---|
| b0, debt % GDP end-2026 | 119.3 | Government forecast, 2027 budget bill (Oct 2026); INSEE Q2 2026 actual 119.0% |
| Y0, nominal GDP 2026 | €3,045bn | Derived: INSEE Q2 2026 debt €3,595.5bn = 119.0% of GDP → €3,021bn rolling four quarters, grown half a year |
| i_eff0, effective interest rate on the stock | 2.2% | Derived: 2026 general-government interest €77bn (Cour des comptes, Jun 2026) / average 2026 debt ≈ €3.53tn |
| pb0, primary balance 2026 % GDP | −2.9 | Government 2026 deficit forecast 5.4% (Oct 2026) minus interest ≈ 2.5% of GDP (Cour des comptes) |
| Bund0, German 10y | 3.35% | Bundesbank via ideal-investisseur.fr, 27 Oct 2026 close |
| s0, OAT–Bund spread | 1.59 pp | same source, 27 Oct 2026 (OAT 4.94%) |
| revenue share | 52.2% of GDP, held constant | INSEE Première no. 2106, May 2026 (2025 revenue) |

## Each simulated year t = 2027..2041

All rates in percent per year; all ratios in % of GDP.

1. Macro draw. Joint block bootstrap (block length 2 years, wrap-around) of historical annual deviations for the same calendar years, so correlations between growth, inflation and German rates are preserved:
   - real GDP growth deviation from its 1991–2025 mean (World Bank NY.GDP.MKTP.KD.ZG, file `research/data/wb_NY.GDP.MKTP.KD.ZG.json`);
   - GDP deflator deviation from its 1991–2025 mean (World Bank NY.GDP.DEFL.KD.ZG);
   - annual change in the German 10y yield, annual average of monthly data, demeaned over 1991–2025 (FRED IRLTLT01DEM156N, file `research/data/fred_de.csv`).
   - real growth g_r = 1.0 + deviation (central 1.0%: between the government's 1.0% and the 0.7–0.9% consensus for 2027; HCFP, Banque de France, OFCE, Oct 2026).
   - deflator π = 1.8 + deviation (anchored near the ECB's 2% target).
   - nominal growth g = (1 + g_r)(1 + π) − 1.
2. German yield: Bund_t = Bund_{t−1} + 0.25 × (3.0 − Bund_{t−1}) + ΔBund deviation. Long-run 3.0% and speed 0.25 are assumptions; they go into the sensitivity table.
3. Spread: s_eq(b) = 1.20 + 0.0573 × (b − 119.3) (European Commission, Pamies, Carnot & Patarau, Jun 2021, Table 1 regression (4): 0.0014 + 0.0559 pp per point of debt above 90% of GDP; the paper's benchmark without the high-debt term is ~3 bp). v1.0 used 0.03 below 130 and 0.06 above, which the paper does not state; changed in v1.2 after checking the PDF. Then s_t = s_eq(b_{t−1}) + 0.5 × (s_{t−1} − s_eq(b_{t−2})) + ε_s, ε_s ~ N(0, 0.30). Floor the spread at 0.20 pp. For t = 2027 use b_{t−2} = b0.
4. 10y OAT yield y_t = Bund_t + s_t. New borrowing and refinancing pay y_t (conservative: ignores cheaper short-term bills).
5. Effective rate: share refinanced this year m' = 0.13 + max(0, d_{t−1}) / b_{t−1}, where 0.13 ≈ 14% of debt maturing in 2027 (Candriam, AFP, 9 Oct 2026) and average maturity ~8.5 years (AFT). i_eff_t = (1 − m') × i_eff_{t−1} + m' × y_t. Use d_2026 = 5.4.
6. Primary balance: pb_t = plan_t(scenario) + 0.5 × (g_r − 1.0) + u_t, where 0.5 is the cyclical sensitivity of the budget (assumption, typical EU semi-elasticity; flag it in README as an assumption) and u_t = 0.5 × u_{t−1} + ε_pb, ε_pb ~ N(0, 0.5) (fiscal slippage, persistent).
7. Debt: b_t = b_{t−1} × (1 + i_eff_t/100) / (1 + g/100) − pb_t.
8. Interest bill: int_t = i_eff_t/100 × b_{t−1} / (1 + g/100) × 100 (% of GDP). Deficit d_t = int_t − pb_t. Nominal GDP Y_t = Y_{t−1} × (1 + g/100). Interest in euros = int_t × Y_t / 100. Deflate to 2026 euros with the cumulative deflator.

No defaults, no ECB intervention, no panic jumps. Debt can grow without limit; cap nothing, but report runs above 200% as "200%+".

## Scenarios (plan_t, primary balance in % of GDP)

| Id | Name | Path |
|---|---|---|
| A | Nothing changes | −2.9 every year (the 2026 position frozen) |
| B | Half the effort | +0.3 pp per year from −2.9 until 0.0, then hold 0.0 |
| C | The official plan | 2027 −2.3, 2028 −1.7 (IMF Article IV baseline, Jul 2026), 2029 −0.9, 2030 −0.2, 2031 onward +0.5 (consistent with the deficit below 3% target the IMF and government cite for 2029–2030) |
| D | Cour des comptes path | +0.6 pp per year from −2.9 until +1.8, then hold +1.8 (the Cour's reference primary surplus, Jun 2026) |

100,000 runs per scenario. Use the same random draws (common random numbers) across scenarios so differences come only from the plan.

## Outputs for `summary.json` (per scenario)

- Median and P10/P90 debt in 2031, 2036, 2041.
- P(debt_2041 > b0). P(debt > 130 at any point). P(debt > 140 at any point) (Italy is ~140% today). P(debt > 150 at any point).
- P(spread > 2.25 pp at any point): above the 2011 record of 225 bp (17 Nov 2011).
- P(10y OAT > 6% at any point).
- Median interest bill in 2041: % of GDP, % of revenue, and billions of 2026 euros.
- Median cumulative interest 2027–2041 in 2026 euros, total and per resident (population 69.1 million, INSEE Première no. 2087, Jan 2026).
- Median and distribution of the first year debt exceeds 130 and 140.
- The debt-stabilising primary balance in 2041 at the median path: (i_eff − g)/(1 + g) × b.

## Validation (`validation.json`)

1. IMF replication: deterministic run from b = 118.5 (IMF end-2026), pb 2027 −2.3, 2028 −1.7, real growth 1.2% (IMF 2027) both years, deflator 1.5%, Bund fixed 3.35, spread fixed 1.59, effective-rate rule as above. Report model debt 2027 and 2028 next to IMF 120.3 and 121.1, and the gap.
2. Cone width check: P90 − P10 of debt five years out (2031) in scenario C, next to Banque de France WP 1019 (Nov 2025): 25.2 pp (VAR) and 28.5 pp (BVAR) at a five-year horizon; European Commission 19.5 pp; ECB 37.8 pp. Report only; do not tune the model to hit them.
3. Accounting identity: on the central path, sum of debt changes equals the sum of the snowball term minus primary balances, to 1e-9.

## Sensitivity (`sensitivity.csv`)

For scenario C, re-run with 20,000 runs each, changing one parameter at a time, and report median debt 2041 and P(debt > 140 at any point):
- central real growth 0.5 and 1.5;
- Bund long-run 2.5 and 3.5;
- spread slope 0.029 (the paper's benchmark regression) and 0.086 (1.5 times the base);
- s_eq intercept 0.9 and 1.5;
- refinancing base share 0.10 and 0.16;
- slippage sd 0.25 and 1.0.

## Tests

- Zero-shock run equals `central_<scenario>.csv` exactly.
- Same seed → identical `summary.json` (byte for byte).
- With r = g and pb = 0 every year, debt stays at b0.
- Scenario D median debt in 2041 is below scenario A's (sanity, not a target).
- Bootstrap blocks only use years 1991–2025.

## Style

Readable code with short docstrings. Each equation in the code carries a one-line comment pointing to the step number in this spec. Vectorise over runs with numpy; the full run should take under a minute on a laptop.
