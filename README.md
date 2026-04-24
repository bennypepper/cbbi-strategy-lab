# CBBI Strategy Lab

**Interactive Bitcoin backtesting simulator powered by CBBI on-chain indicators.**

Built as the public deliverable of Phase 4 of the research project:
*"Optimizing Threshold Parameters and Asset Allocation Based on CBBI Indicators to Maximize Bitcoin Portfolio Performance"* (PKL Research, 2026)

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://cbbi-strategy-lab.streamlit.app)

---

## 🌟 Key Features

- **⚡ Strategy Simulator:** Run live backtests with fully custom parameters on 14 years of Bitcoin data. Powered by a highly-optimized Numba JIT-compiled backtest engine.
- **🔄 Live API Integration:** Seamlessly switch between the frozen historical academic dataset (CSV) and the real-time **Live CBBI API** directly from Colintalkscrypto.
- **⚙️ Dynamic Parameter Optimizer:** A dedicated tool to recalculate optimal parameters against today's live CBBI formula, mitigating the effects of "Index Revision Bias" caused by retroactive formula updates.
- **🔬 Historical Research Results:** Explore Phase 3 optimization outcomes from 1.29M parameter combinations across multiple academic scenarios.
- **📊 Interactive Charts:** Premium UI with Plotly integration. Zoom, pan, and hover on equity curves, CBBI signal overlays, and sensitivity heatmaps.
- **✨ Premium UI/UX:** A highly polished, 100% English, fully responsive interface featuring neo-brutalism typography, glassmorphism cards, and interactive tooltip integrations.

## 📉 Signal Indicator

This app uses **Trolololo (Logarithmic Regression / Rainbow Chart)** as the primary trading signal — identified as the most statistically significant CBBI sub-indicator through rigorous Spearman correlation analysis.

## 🚀 Running Locally

```bash
git clone https://github.com/bennypepper/cbbi-strategy-lab.git
cd cbbi-strategy-lab
pip install -r requirements.txt
streamlit run app.py
```

*Requires Python 3.11+ (Python 3.12+ recommended for advanced formatting compatibilities).*

## 📁 Project Structure

```text
cbbi-strategy-lab/
├── app.py                  # Home page & sidebar navigation entry point
├── core/                   # Shared logic and utilities
│   ├── charts.py           # Plotly chart building functions
│   ├── data_loader.py      # Historical CSV & Live API data fetching
│   ├── engine.py           # Core Numba JIT-compiled backtest engine
│   ├── optimizer.py        # Live parameter grid-search optimizer logic
│   ├── styles.py           # Global CSS injection & premium UI styling
│   └── utils.py            # Formatting helpers (currency, percentage)
├── pages/                  # Streamlit application pages
│   ├── 1_Simulator.py      # Interactive sandbox simulator
│   ├── 2_Historical.py     # Static Phase 3 academic research results
│   ├── 3_Methodology.py    # Architectural and mathematical documentation
│   └── 4_Optimizer.py      # Dynamic parameter re-optimization for live deployment
└── data/                   # Datasets and state tracking
    ├── master_dataset.parquet      # Frozen snapshot data
    ├── optimal_params_summary.json # Phase 3 academic optimal parameters
    └── live_optimal_params.json    # Cached results from the Live Optimizer
```

## ⚠️ Disclaimer

This application is for educational and academic purposes only. All results are based on historical backtesting. **Nothing here constitutes financial advice.** Past performance does not guarantee future results.

## 📚 Research Context

- **Phase 1–3 repository:** Private research repo (`PKL_v4`)
- **Data sources:** CBBI official API (`cbbi.info`) + Yahoo Finance `BTC-USD`
- **Optimization:** Grid Search across 1,293,750 parameter combinations
- **Framework:** Undergraduate Research (PKL), 2026
