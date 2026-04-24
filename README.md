# CBBI Strategy Lab

Interactive Bitcoin backtesting simulator powered by CBBI on-chain indicators.

Built as the public deliverable of the research project:
"Optimizing Threshold Parameters and Asset Allocation Based on CBBI Indicators to Maximize Bitcoin Portfolio Performance" (PKL Research, 2026).

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://cbbi-strategy-lab.streamlit.app)

---

## Features

- **Strategy Simulator:** Run backtests with custom parameters on 14 years of Bitcoin data. Uses a Numba JIT-compiled backtest engine.
- **Live API Integration:** Switch between the static historical dataset and the Live CBBI API from Colintalkscrypto.
- **Dynamic Parameter Optimizer:** Recalculate optimal parameters against the current live CBBI formula to address Index Revision Bias caused by retroactive formula updates.
- **Historical Research Results:** View Phase 3 optimization outcomes from 1.29 million parameter combinations across multiple scenarios.
- **Interactive Charts:** Plotly integration for viewing equity curves, signal overlays, and sensitivity heatmaps.
- **User Interface:** Responsive interface with consistent styling and interactive tooltips.

## Signal Indicator

This application uses Trolololo (Logarithmic Regression / Rainbow Chart) as the primary trading signal. This indicator was identified as the most statistically significant CBBI sub-indicator based on Spearman correlation analysis.

## Running Locally

```bash
git clone https://github.com/bennypepper/cbbi-strategy-lab.git
cd cbbi-strategy-lab
pip install -r requirements.txt
streamlit run app.py
```

Requires Python 3.11 or higher.

## Project Structure

```text
cbbi-strategy-lab/
├── app.py                  # Home page and sidebar navigation
├── core/                   # Shared logic and utilities
│   ├── charts.py           # Plotly chart generation
│   ├── data_loader.py      # Historical CSV and Live API data fetching
│   ├── engine.py           # Numba JIT-compiled backtest engine
│   ├── optimizer.py        # Live parameter grid-search logic
│   ├── styles.py           # CSS styling
│   └── utils.py            # Formatting helpers
├── pages/                  # Streamlit application pages
│   ├── 1_Simulator.py      # Interactive simulator
│   ├── 2_Historical.py     # Static Phase 3 research results
│   ├── 3_Methodology.py    # Architectural and mathematical documentation
│   └── 4_Optimizer.py      # Parameter re-optimization for live deployment
└── data/                   # Datasets and state tracking
    ├── master_dataset.parquet      # Frozen snapshot data
    ├── optimal_params_summary.json # Phase 3 optimal parameters
    └── live_optimal_params.json    # Cached results from the Live Optimizer
```

## Disclaimer

This application is for educational and academic purposes only. All results are based on historical backtesting. Nothing here constitutes financial advice. Past performance does not guarantee future results.

## Research Context

- **Phase 1-3 repository:** Public research repo (https://github.com/bennypepper/cbbi-optimization-research)
- **Data sources:** CBBI official API (cbbi.info) and Yahoo Finance BTC-USD
- **Optimization:** Grid Search across 1,293,750 parameter combinations
- **Framework:** Undergraduate Research (PKL), 2026
