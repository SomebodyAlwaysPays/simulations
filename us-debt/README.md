# US federal debt simulation

This model projects federal debt held by the public as a share of GDP from fiscal year 2027 through 2041. It draws 100,000 possible economic and fiscal histories for each of four budget scenarios, using the same random draws across scenarios. These are conditional simulations, not forecasts or probabilities of a particular policy being enacted. The starting point is the end of FY2026.

## Run

Python 3.11+, NumPy, Matplotlib, and pytest are required. The inputs are in `data/`, downloaded in early November 2026; the model performs no download. From this directory:

```sh
python3 -m pytest
python3 run.py
```

The default seed is 20261103. The run writes `out/summary.json`, percentile fans, 300 sample paths, crossing years, zero-shock central paths, `validation.json`, `sensitivity.csv`, and charts in `out/preview/`. Ratios are percentages of GDP unless otherwise stated, rates are annual percentages, and dollar values are in billions unless labelled per person or household. `200%+` means a crossing above 200%, not a cap on debt.

## How it works

Historical annual real growth, inflation and ten-year yield changes are jointly resampled in two-year blocks, preserving their historical pairing. Their deviations from the 1985–2025 means are added to the CBO macro path. Nominal GDP growth is `(1 + real growth) × (1 + inflation) − 1`, with rates in fractions. Yield deviations persist at 75% per year, and the ten-year yield also rises by 0.02 percentage points for each point of debt above CBO's path. The ten-year yield has a 0.5% floor; the bill rate uses the same market shock without the debt premium and has a zero floor.

Bills and floating notes reprice each year; a fraction of coupon debt refinances at the ten-year yield, including maturing debt and the previous deficit. Half of the year's refinancing affects the cash coupon rate. Interest is the effective rate times prior debt, divided by nominal GDP growth. The primary balance adds a growth stabilizer and persistent fiscal slippage to the scenario plan. Debt evolves as `prior debt × (1 + effective rate) / (1 + nominal growth) − primary balance`. The deficit equals interest minus the primary balance. Interest dollars are deflated to 2026 purchasing power; comparisons with Social Security, net Medicare, defense and revenue use CBO's shares.

| Scenario | Primary balance plan | Revenue adjustment |
|---|---|---:|
| A: Frozen | FY2026 underlying primary balance, −2.493% of GDP every year | −0.176 points |
| B: Current law | CBO primary balance less 0.176 points for tariff changes | −0.176 points |
| C: No tariffs | B less another 0.373 points | −0.549 points |
| D: 3% deficit | Interest less a deficit target declining by 0.75 points a year from 5.756%, with a 3% floor | −0.176 points |

In D, the plan responds to each run's interest bill. Growth and slippage shocks still move the realised deficit around its target.

## Inputs and assumptions

The starting debt ratio is 100.588%, nominal GDP $32,235.5bn, effective interest rate 3.355%, bill rate 3.686%, ten-year yield 5.13%, and deficit 6.181%. The underlying primary balance is −2.493% and underlying deficit 5.756%, excluding one-off tariff refunds. These come from Treasury Debt to the Penny, the Monthly Treasury Statement and BEA/FRED GDP and Treasury series as described in [SPEC.md](SPEC.md). The short-term share is 0.2446 and coupon rollover rate 0.132, from the September 2026 Monthly Statement of the Public Debt. Population is 343.1 million (BEA/FRED), households 134.79 million (Census/FRED), and the 1946 debt record is 106.1% (OMB Historical Table 7.1).

The CBO baseline supplies debt, primary balances, growth, inflation, interest rates, revenue, spending and GDP. The column-level sources and the assumptions used for late-year bill rates and defense are in [cbo_paths_SOURCES.md](data/cbo_paths_SOURCES.md). Historical GDP, the GDP deflator and the ten-year yield come from the supplied FRED files. Calendar-year averages are used; 1985's yield change uses 1984. The baseline history starts in 1985, with 1960–2025 tested in sensitivity.

Model assumptions without direct estimates are: 0.25 annual yield reversion; a 0.4 primary-balance response per point of real-growth deviation; fiscal slippage with persistence 0.5 and innovation standard deviation 0.5 points; and the interpretation that a one-year growth shortfall maps one-for-one into the GDP gap. The debt-yield coefficient of 0.02 comes from CBO Working Paper 2024-05. B's 0.176-point adjustment and C's additional 0.373 points derive from CBO's August and March 2026 tariff estimates respectively. D's 0.75-point annual pace is the midpoint of the 50–100 basis-point annual reduction described by Bessent in January 2026. The sensitivity file varies the assumptions and the debt-yield coefficient one at a time, including starting the ten-year yield on CBO's path.

## Validation and limitations

`validation.json` reports the untuned deterministic CBO replication and its annual gaps in debt, net interest and effective rates, along with the zero-shock B path against CBO, two cone comparisons and the central-path debt accounting identity. The CBO replication is a diagnostic, not a fit: different interest accounting, financing flows and other modelling choices can leave gaps. Quantile comparisons and event probabilities describe the specified model and historical resampling window, not calibrated confidence intervals.

The model excludes default, Fed rescue, panic jumps, deficit feedback to growth, TIPS indexation and stock-flow adjustments such as CBO's other means of financing. It applies no cap to debt. The 1985–2025 history is finite and may not represent future shocks; the fiscal scenarios and assumed reactions are stylised. See [SPEC.md](SPEC.md) for exact definitions, all sensitivity values and the output contract.

## Implementation choices

The D target is evaluated from the stated formula `max(3.0, 5.756 − 0.75 × (year − 2026))`. Thus the first target is 5.006%, whereas the illustrative sequence in the specification rounds it to 5.0%; the formula governs the calculation.

## License

[MIT](../LICENSE).
