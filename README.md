# Somebody Always Pays: simulations

Code and data behind the simulation videos on the YouTube channel [Somebody Always Pays](https://www.youtube.com/@SomebodyAlwaysPays). Each folder is a self-contained model with its inputs, tests and published results. Run it, change an assumption, and see how the futures move.

| Folder | Video | What it simulates |
|---|---|---|
| [us-debt](us-debt/) | [Who Will ACTUALLY Pay America's $40 Trillion Debt?](https://youtu.be/Sm8ITrqb-Xo) | US federal debt held by the public, fiscal years 2027–2041, under four budget scenarios |
| [france-debt](france-debt/) | France Could Cut for 15 Years and STILL Owe More (out 14 November 2026). Background: [France Taxes More Than Almost Anyone. So Why Is It BROKE?](https://youtu.be/c2SStIaRtus) | France's general-government debt, 2027–2041, under four budget plans |

## Run a model

Python 3.11+ with NumPy, Matplotlib and pytest:

```sh
cd us-debt
python3 -m pip install numpy matplotlib pytest
python3 -m pytest
python3 run.py
```

A full run takes about ten seconds on a laptop. The seed is fixed, so `run.py` reproduces the files in `out/` exactly. Each folder's README explains the equations, every assumption and its source, and what the model leaves out.

These are conditional simulations: they show what happens under stated assumptions. They are not forecasts, and nothing here is financial or investment advice.

## Licence

[MIT](LICENSE). The input data in each model's data folder comes from public sources (US Treasury, CBO, OMB, BEA, Census, FRED, World Bank, INSEE and others), credited in each model's README.
