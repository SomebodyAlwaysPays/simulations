# Sources for cbo_paths.csv (read 2026-11-03 in the browser from cbo.gov xlsx files; values copied, not re-estimated)

All fiscal years. Percentages are % of GDP unless the column is a rate (percent per year).

| Column | 2026–2036 | 2037–2041 |
|---|---|---|
| debt_pct | CBO, The Budget and Economic Outlook: 2026 to 2036 (Feb 11, 2026), Table 1-1 / 1-3, file 51118-2026-02-Budget-Projections.xlsx | CBO, Long-Term Budget Outlook Data 2026 to 2056 (Feb 25, 2026), 51119-2026-02-25-LTBO-Budget.xlsx, sheet 1 |
| primary_balance_pct | LTBO sheet 1 "Primary deficit (-)" (adjusted to exclude timing shifts); 2026–2036 equal the Outlook's adjusted values | LTBO sheet 1 |
| real_growth, deflator | Outlook economic data 51135-2026-02-Economic-Projections.xlsx, sheet "3. Fiscal Year", real GDP and GDP price index, % change | LTBO econ 57054-2026-02-LTBO-econ.xlsx, sheet 1 (calendar-year rates) |
| y10, bill3m | 51135 sheet "3. Fiscal Year", 10-Year Treasury note, 3-Month Treasury bill | y10: LTBO econ sheet 1 nominal 10-year rate; bill3m: ASSUMPTION, held at the 2036 value |
| avg_rate | Outlook Table 1-3 "Average interest rate on debt held by the public" | LTBO-based CBO letter 62758 (Sep 24, 2026) Supplemental Table 1 |
| net_interest_pct, revenue_pct, customs_pct, social_security_pct, medicare_net_pct | LTBO sheet 1 (Medicare is net of offsetting receipts). Customs note in LTBO: "Values do not account for effects of the Supreme Court's February 20, 2026, ruling on tariffs." | LTBO sheet 1 |
| defense_pct | Outlook Table 3-1, defense discretionary outlays % GDP (not timing-adjusted) | ASSUMPTION: 2036 defense share of total discretionary (2.355/4.804 = 0.490) times LTBO discretionary (4.738, 4.689, 4.657, 4.641, 4.641) |
| gdp_bn | Outlook FY GDP | CBO letter 62758 Supplemental Table 1 |

CBO higher-rate scenario (letter 62758, Supplemental Table 2, rates rising to 1 pp above baseline): debt 124.253% (2036), 141.2% (2041), 222.094% (2056).
