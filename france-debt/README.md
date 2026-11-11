# France general-government debt simulation

This model projects France's general-government debt as a share of GDP from end-2026 through 2041. It runs 100,000 possible economic and fiscal histories for each of four budget plans, with the same random draws in every plan, so the plans differ only in policy. These are conditional simulations under stated assumptions. They are not forecasts.

## Run

You need Python 3.11+ with NumPy, Matplotlib and pytest. The inputs are in `research/data/` (World Bank and FRED files downloaded on 30 October 2026), and the model downloads nothing. From this directory:

```sh
python3 -m pytest
python3 run.py
```

The default seed is 20261030, and a run reproduces `out/` exactly.

**What the run writes:**
- `out/summary.json`;
- for each plan: percentile fans, 300 sample paths, first-crossing histograms and a zero-shock central path;
- `validation.json` and `sensitivity.csv`;
- charts in `out/preview/`.

**Units:**
- Debt and balances are percent of GDP.
- Rates are annual percentages.
- Money is billions of euros unless labelled per resident.
- `200%+` marks the first year debt exceeds 200%. It is not a cap.

## How it works

**Shared history.** Every year draws a two-year block of real French history from 1991–2025. The same calendar years supply real GDP growth, GDP-deflator inflation and the change in the German 10-year yield, so their joint history is preserved. Blocks wrap from 2025 back to 1991. Growth and inflation enter as deviations from their 1991–2025 means, added to central values of 1.0% real growth and 1.8% inflation. Nominal growth is `(1 + real growth) × (1 + inflation) − 1`, with rates as fractions.

**Interest rates.**
- The German yield mean-reverts towards 3.0% at speed 0.25 a year, plus its historical shock.
- France's spread over Germany rises by 0.0573 points for every point of debt above the starting 119.3%. It also has persistence 0.5 and noise with standard deviation 0.30 points, and it never falls below 0.20 points.
- The 10-year OAT yield is the Bund yield plus the spread.

**Rolling the debt over.** Each year 13% of the debt, plus the previous year's deficit, refinances at that year's OAT yield. The effective interest rate blends the old rate with the new yield in that proportion. This is why rate rises reach France slowly.

**Debt.**
- The primary balance is the plan, plus 0.5 times the real-growth gap, plus persistent fiscal slippage (persistence 0.5, standard deviation 0.5 points).
- Debt evolves as `b(t) = b(t−1) × (1 + i(t)) / (1 + g(t)) − pb(t)`.
- Interest is `i(t) × b(t−1) / (1 + g(t))`.
- The deficit is interest minus the primary balance.
- Interest in euros is deflated to 2026 euros.

| Plan | Primary balance, % of GDP |
|---|---|
| A: Nothing changes | −2.9 every year (the 2026 position frozen) |
| B: Half the effort | +0.3 points a year from −2.9 until 0, then held at 0 |
| C: The official plan | 2027 −2.3, 2028 −1.7 (IMF Article IV 2026 baseline), 2029 −0.9, 2030 −0.2, then +0.5 from 2031 |
| D: Cour des comptes path | +0.6 points a year from −2.9 until +1.8, then held at +1.8 |

## Results in brief

| Plan | Median debt 2041 | Owes more in 2041 than end-2026 | Debt above 200% at some point | Median cumulative interest per resident, 2027–2041 (2026 euros) |
|---|---:|---:|---:|---:|
| A | 203.8% | 100% | 56.6% | €49,833 |
| B | 159.1% | 99.1% | 4.5% | €40,322 |
| C | 138.4% | 87.4% | 0.5% | €34,749 |
| D | 126.5% | 66.2% | 0.1% | €33,522 |

Growth matters more than any market assumption tested. In plan C, the median 2041 debt ends at 120.7% of GDP with 1.5% central real growth and at 158.7% with 0.5%. The other one-at-a-time sensitivity runs are in `out/sensitivity.csv`.

## Inputs and sources

Every number and its source is in [config.py](config.py). Full descriptions are in [SPEC.md](SPEC.md).

| Input | Value | Source |
|---|---|---|
| Debt, end-2026 | 119.3% of GDP | 2027 budget bill forecast, Oct 2026; INSEE Q2 2026 actual 119.0% |
| Nominal GDP 2026 | €3,045bn | Derived from INSEE Q2 2026 debt and ratio |
| Effective interest rate | 2.2% | Cour des comptes (Jun 2026) interest bill divided by average debt |
| Primary balance 2026 | −2.9% of GDP | Government 2026 deficit forecast of 5.4%, minus interest |
| German 10-year yield | 3.35% | Bundesbank, 27 Oct 2026 |
| OAT–Bund spread | 1.59 points | 27 Oct 2026 |
| Revenue | 52.2% of GDP | INSEE Première no. 2106, May 2026 |
| Population | 69.1 million | INSEE Première no. 2087, Jan 2026 |
| Refinancing share | 13% a year | Candriam/AFP Oct 2026; Agence France Trésor average maturity, Sep 2026 |
| Spread slope | 0.0573 points per point of debt | European Commission Discussion Paper 141 (Pamies, Carnot & Patarau, 2021), Table 1 |

**Historical series:**
- World Bank NY.GDP.MKTP.KD.ZG (real GDP growth);
- World Bank NY.GDP.DEFL.KD.ZG (GDP deflator);
- FRED IRLTLT01DEM156N (German 10-year yield, monthly, averaged by year).

**Assumptions without a direct estimate:**
- the 3.0% long-run Bund yield and the 0.25 reversion speed;
- the 1.20-point spread intercept;
- the 0.5 cyclical budget sensitivity;
- the slippage process.

Each one is varied in the sensitivity file.

## Validation and limitations

`validation.json` reports three checks:
- **IMF replication.** A deterministic run with IMF inputs gives 120.5% and 122.4% of GDP for 2027 and 2028, against the IMF's 120.3% and 121.1%.
- **Spread of outcomes.** The five-year-ahead P90–P10 width is 20.5 points, against references of 19.5 to 37.8 points from the European Commission, the Banque de France and the ECB.
- **Accounting identity.** On the central path, debt changes add up exactly.

Nothing is tuned to match these checks.

**What the model leaves out:**
- market panic, default and an ECB rescue;
- inflation-linked debt and stock-flow adjustments;
- any feedback from deficits to growth.

New borrowing pays the 10-year OAT yield rather than a full maturity schedule, which makes the model somewhat conservative. Plans C and D do not rank the same way in every year: C adjusts faster early on, so its 2031 median is lower than D's. By 2041 the medians rank A highest through D lowest.

## Implementation notes

- **Interest formula.** The interest formula in the spec's step 8 carries an extra `× 100`. The code omits it, because debt is already in percent of GDP and the extra factor would make the 2026 interest bill 100 times too large.
- **Spread slope.** Version 1.0 used slopes of 0.03 and 0.06 around a 130% kink. Version 1.2 uses the single slope the cited paper reports. The kink stays in the code for sensitivity runs and is inactive in the base case.
- **Cyclical term.** It is always measured against the 1.0% benchmark, including in growth sensitivity runs.

## License

[MIT](../LICENSE).
