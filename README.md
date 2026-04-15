# CBBI Strategy Lab

**Interactive Bitcoin backtesting simulator powered by CBBI on-chain indicators.**

Built as the public deliverable of Phase 4 of the research project:
*"Optimizing Threshold Parameters and Asset Allocation Based on CBBI Indicators to Maximize Bitcoin Portfolio Performance"* (PKL Research, 2026)

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-url.streamlit.app)

---

## Features

- **⚡ Strategy Simulator** — Run live backtests with fully custom parameters on 14 years of Bitcoin data (2012–2026). Powered by a Numba JIT-compiled backtest engine.
- **🔬 Research Results** — Explore Phase 3 optimization outcomes from 1.29M parameter combinations across two research scenarios.
- **📊 Interactive Charts** — Zoom, pan, and hover on equity curves, CBBI signal overlays, and sensitivity heatmaps.
- **⬇ Data Export** — Download trade logs, top-100 parameter sets, and full results JSON.

## Signal Indicator

This app uses **Trolololo (Logarithmic Regression / Rainbow Chart)** as the primary trading signal — identified as the most statistically significant CBBI sub-indicator through Spearman correlation analysis.

## Running Locally

```bash
git clone https://github.com/YOUR_USERNAME/cbbi-strategy-lab.git
cd cbbi-strategy-lab
pip install -r requirements.txt
streamlit run app.py
```

Python 3.11+ recommended.

## Project Structure

```
cbbi-strategy-lab/
├── app.py                  # Home page + entry point
├── core/
│   ├── engine.py           # Numba backtest engine
│   ├── data_loader.py      # Cached data loaders
│   └── charts.py           # Plotly chart builders
├── pages/
│   ├── 1_Simulator.py      # Interactive simulator
│   ├── 2_Research_Results.py
│   └── 3_Documentation.py
└── data/
    ├── master_dataset.parquet
    ├── optimal_params_summary.json
    └── trial_log/
```

## Disclaimer

This application is for educational and academic purposes only. All results are based on historical backtesting. Nothing here constitutes financial advice. Past performance does not guarantee future results.

## Research Context

- **Phase 1–3 repository:** Private research repo (PKL_v4)
- **Data sources:** CBBI official dataset (cbbi.info) + Yahoo Finance BTC-USD
- **Optimization:** Grid Search across 1,293,750 parameter combinations
- **Framework:** PKL Undergraduate Research, 2026
