# Product Requirements Document
## CBBI Strategy Lab — Interactive Backtesting Web Application

**Version:** 1.0  
**Date:** April 2026  
**Author:** Solo Developer  
**Status:** Active Development  
**Repo:** `cbbi-strategy-lab`

---

## 1. Project Overview

### 1.1 Background

This web application is the public-facing deliverable of Phase 4 of the academic research project:
**"Optimizing Threshold Parameters and Asset Allocation Based on CBBI Indicators to Maximize Bitcoin Portfolio Performance"** (PKL Research, 2026).

Phases 1–3 of the research have been completed in a separate private repository (`PKL_v4`):
- **Phase 1:** Data pipeline — master dataset built from CBBI official XLSX + yfinance BTC open prices
- **Phase 2:** Indicator selection — Trolololo (Logarithmic Regression / Rainbow Chart) identified as the most statistically significant signal indicator via Spearman correlation analysis
- **Phase 3:** Optimization engine — Grid Search across ~1.29M parameter combinations, two scenarios

This repository (`cbbi-strategy-lab`) contains **only the web application**. The research pipeline code lives in PKL_v4 and is not reproduced here. Only its outputs (processed data + results JSON) are imported.

### 1.2 Application Purpose

Two distinct but integrated purposes:

| Purpose | Audience | Description |
|---|---|---|
| **Interactive Simulator** | Public / Investors | Run live backtests with any custom parameters on the full 2012–2026 dataset |
| **Research Results Viewer** | Academics / Lecturer | Read-only display of Phase 3 optimization outcomes, both scenarios side-by-side |

### 1.3 Signal Indicator

The application uses **Trolololo (Logarithmic Regression / Rainbow Chart)** as the trading signal column throughout — for both the simulator and the research results display. This is the indicator identified as most statistically significant in Phase 2 of the research via Spearman correlation across 5 lag windows.

---

## 2. Technical Architecture

### 2.1 Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Framework** | Streamlit 1.35+ | Native Python, zero frontend build step, Community Cloud deploy |
| **Backtest Engine** | Numba (`@njit`) | C-level JIT performance — <1s per simulation on 5,000 data points |
| **Charts** | Plotly (via `st.plotly_chart`) | Full interactivity: zoom, pan, hover, click-to-inspect |
| **Data** | Parquet via PyArrow | ~350KB master dataset; ~23MB trial logs loaded on-demand |
| **Caching** | `@st.cache_data` | Master dataset cached on first load; trial logs cached per scenario |
| **Deployment** | Streamlit Community Cloud | Free tier, auto-deploy from `main` branch |

### 2.2 Repository Structure

```
cbbi-strategy-lab/
├── app.py                          # Streamlit entry point (Home / nav hub)
├── PRD.md                          # This document
├── README.md                       # Public-facing repo description
├── requirements.txt                # Python dependencies
├── .gitignore
│
├── core/
│   ├── __init__.py
│   ├── engine.py                   # Numba backtest engine (adapted from PKL_v4)
│   ├── simulator.py                # High-level simulation wrapper → returns full history + metrics
│   ├── charts.py                   # All Plotly chart builder functions
│   └── data_loader.py              # Dataset loading + caching helpers
│
├── pages/
│   ├── 1_Simulator.py              # Page 1: Interactive backtesting simulator
│   ├── 2_Research_Results.py       # Page 2: Phase 3 optimization results (read-only)
│   └── 3_Documentation.py         # Page 3: Methodology, glossary, disclaimer
│
└── data/
    ├── master_dataset.parquet      # Clean daily BTC + CBBI data (2012–2026, 350KB)
    ├── optimal_params_summary.json # Phase 3 best params for both scenarios (5KB)
    └── trial_log/
        ├── scenario_1_grid_search_in_sample.parquet   # ~23MB — heatmap source
        └── scenario_2_grid_search_full.parquet        # ~23MB — heatmap source
```

### 2.3 Backtest Engine Design

The core engine (`core/engine.py`) contains two functions:

**1. `run_backtest_numba()` — Fast metrics-only (JIT compiled)**
- Accepts numpy arrays: signals, prices_open, prices_close
- Parameters: threshold_buy, threshold_sell, alloc_buy_pct, alloc_sell_pct, initial_cash, fee_rate
- Returns: total_return, max_drawdown, sharpe_ratio, wins, sell_count, trade_count
- Use: Grid search, repeated evaluation (already in PKL_v4, copied as-is)

**2. `run_backtest_full()` — Full trace (Python-level, used by simulator)**
- Same logic as above, but additionally tracks per-day:
  - `portfolio_value` array
  - `cash` array
  - `btc_held` array
  - `trade_log` list (date, action, signal_value, exec_price, amount)
- Returns: `SimulationResult` dataclass
- Use: Simulator page charts and trade log table
- Performance: ~0.3–0.8s for 5,000 days (acceptable; runs once per button click)

**Numba JIT Warmup:** On app startup, `run_backtest_numba` is called once with dummy data to pre-compile the JIT function. This eliminates the ~3s cold-start delay on first user click.

### 2.4 Data Flow

```
User clicks "Run Simulation"
    │
    ▼
pages/1_Simulator.py          reads slider/input values
    │
    ▼
core/simulator.py             validate params → load dataset slice → call engine
    │
    ├─► core/data_loader.py   @st.cache_data: load master_dataset.parquet once
    │
    └─► core/engine.py        run_backtest_full() → SimulationResult
    │
    ▼
pages/1_Simulator.py          render metrics cards + 3 charts + trade log table
    │
    └─► core/charts.py        build_equity_chart(), build_cbbi_chart(), build_metrics_cards()
```

---

## 3. Pages & UI Specification

### 3.1 Page 0 — Home (`app.py`)

**Purpose:** Landing page and navigation hub.

**Content:**
- App title: "CBBI Strategy Lab"
- Subtitle: "Bitcoin backtesting powered by CBBI on-chain indicators"
- What is CBBI — 2-sentence explainer
- What is Trolololo — 1-sentence explainer (the signal used throughout)
- Two CTA cards → Simulator | Research Results
- Academic context strip: "Built as part of undergraduate research, 2026"
- Disclaimer footer: "Historical backtesting — not financial advice"

### 3.2 Page 1 — Simulator (`pages/1_Simulator.py`)

**Purpose:** Interactive backtesting with fully custom parameters. User-driven exploration.

#### 3.2.1 Input Panel (left column, ~35% width)

```
┌─────────────────────────────────────┐
│  ⚡ Risk Preset                       │
│  [Dropdown: Conservative / Moderate / Aggressive / Custom]
│                                     │
│  📉 Buy Threshold      [slider 1–45]  │
│  📈 Sell Threshold     [slider 55–100]│
│  💰 Buy Allocation     [slider 1–25%] │
│  💸 Sell Allocation    [slider 1–25%] │
│                                     │
│  📅 Date Range                       │
│  From: [date_input]  To: [date_input]│
│                                     │
│  💵 Initial Capital  [$100,000]      │
│                                     │
│  ▸ Advanced Settings (expandable)   │
│    Fee Rate: [0.0% – 0.5%]          │
│                                     │
│  [▶ Run Simulation]  ← primary CTA  │
└─────────────────────────────────────┘
```

**Preset definitions:**

| Preset | Buy Threshold | Sell Threshold | Alloc Buy | Alloc Sell |
|---|---|---|---|---|
| Conservative | 10 | 85 | 5% | 5% |
| Moderate | 20 | 75 | 10% | 10% |
| Aggressive | 30 | 65 | 20% | 20% |
| Custom | (user-defined) | — | — | — |

**Validation rules:**
- threshold_buy must be < threshold_sell (show `st.error` if violated)
- Date range minimum: 1 year
- Initial capital minimum: $1,000

#### 3.2.2 Results Panel (right column, ~65% width)

Shown only after simulation runs. While running: `st.spinner("Running simulation...")`.

**Metrics Row (4 cards across):**

| Card | Value | Delta vs B&H |
|---|---|---|
| Total Return | e.g. +741% | vs Buy & Hold same period |
| Max Drawdown | e.g. -62.8% | — |
| Sharpe Ratio | e.g. 1.03 | — |
| Win Rate | e.g. 67.0% (from N trades) | — |

- If `trade_count < 10`: show orange warning badge "⚠ Low trade count — statistical metrics unreliable"

**Chart 1 — Equity Curve (full height):**
- Area chart: strategy portfolio value (USD)
- Line: Buy & Hold benchmark (scaled to same initial capital)
- Secondary Y-axis: BTC close price
- Trade markers: ▲ BUY (green), ▼ SELL (red) on portfolio curve
- Zoom/pan fully enabled via Plotly

**Chart 2 — CBBI Trolololo Signal:**
- Line: daily Trolololo value (0–100)
- Dashed red line: Buy Threshold
- Dashed green line: Sell Threshold
- Shaded region between thresholds = "Hold Zone"
- X-axis synchronized with Chart 1

**Trade Log Table:**
- `st.dataframe()` with column config
- Columns: Date | Action | Trolololo Value | Exec Price (BTC Open T+1) | Amount (USD) | Portfolio Value After
- BUY rows highlighted green, SELL rows highlighted red
- Download button: "⬇ Export Trade Log (CSV)"

#### 3.2.3 Summary Statement (below charts)

Auto-generated text summarizing result:
> "With a Buy Threshold of 20 and Sell Threshold of 75, your strategy generated a **+234.5% total return** from Jan 2012 to Mar 2026, compared to Buy & Hold at **+12,117%** over the same period. The strategy completed **312 trades** with a win rate of **68.2%**."

---

### 3.3 Page 2 — Research Results (`pages/2_Research_Results.py`)

**Purpose:** Display Phase 3 optimization results. Read-only — no user inputs. Data source: `optimal_params_summary.json` + trial log parquets.

#### 3.3.1 Header Banner

Brief explanation of the two research scenarios (Scenario 1: Academic Validation vs Scenario 2: Maximum Exploration). Note that Trolololo is the signal indicator used.

#### 3.3.2 Scenario 1 — Academic Validation Approach

**Tab layout:** `[Max Return] | [Min Drawdown] | [Max Sharpe]`

Each tab shows:
- Parameter table: Buy | Sell | Alloc Buy | Alloc Sell
- IS metrics: Return | MDD | Sharpe | Win Rate | Trade Count
- OOS metrics: same columns
- Degradation row: Return ∆ | MDD ∆ | Sharpe ∆
- Degradation interpretation badge: 🟢 Robust / 🟡 Moderate / 🔴 Overfit

**IS vs OOS Equity Chart:**
- Two lines: IS period equity curve + OOS period equity curve
- Grey background shading to distinguish IS vs OOS date ranges
- Trade markers visible

**Degradation Bar Chart:**
- Grouped bar per objective: Return degradation % | Sharpe degradation %
- Color: green if degradation < 20%, yellow 20–40%, red > 40%

#### 3.3.3 Scenario 2 — Maximum Exploration Approach

**⚠ Disclaimer Box** (must appear BEFORE any numbers):
```
┌─────────────────────────────────────────────────────┐
│ ⚠  IMPORTANT DISCLOSURE                             │
│                                                     │
│ The following results were obtained by optimizing   │
│ on the ENTIRE historical dataset (2012–2026).       │
│ This configuration cannot be used as a predictive   │
│ trading signal. The purpose is solely to map the    │
│ absolute historical performance ceiling of the      │
│ Trolololo indicator.                                │
└─────────────────────────────────────────────────────┘
```

**Tab layout:** `[Max Return] | [Min Drawdown] | [Max Sharpe]`

Each tab shows:
- Parameter table
- Full dataset metrics
- Full equity curve chart

#### 3.3.4 Comparison Panel

**Side-by-side table:** Scenario 1 OOS vs Scenario 2 Full vs Buy & Hold
- Rows: Total Return | Max Drawdown | Sharpe Ratio
- Columns: S1 OOS | S2 Full | B&H
- Color coding: green = best in row, red = worst

**Sensitivity Heatmaps (2 total):**

| Heatmap | Source Data | X-axis | Y-axis | Color = |
|---|---|---|---|---|
| Scenario 1 (IS) | `scenario_1_is.parquet` | Buy Threshold (1–45) | Sell Threshold (55–100) | Best Total Return at optimal allocation |
| Scenario 2 (Full) | `scenario_2_full.parquet` | Buy Threshold (1–45) | Sell Threshold (55–100) | Best Total Return at optimal allocation |

*Heatmap data processing:* For each (buy, sell) pair, take the max total_return across all allocation combos. Loaded lazily with `@st.cache_data(ttl=3600)`.

**Export Panel:**
- Download: `optimal_params_summary.json`
- Download: Scenario 1 top-100 results (CSV, filtered by max_return)
- Download: Scenario 2 top-100 results (CSV, filtered by max_return)

---

### 3.4 Page 3 — Documentation (`pages/3_Documentation.py`)

**Content sections:**

1. **What is CBBI?** — Composite Bitcoin Bull/Bear Index explanation
2. **What is Trolololo?** — Logarithmic Regression Band / Rainbow Chart indicator, why it was selected
3. **Indicator Overview Table** — all 9 CBBI sub-indicators, one-line description each
4. **Strategy Logic** — how Buy/Sell/Hold signals work with thresholds
5. **Metric Glossary** — Total Return, Max Drawdown, Sharpe Ratio, Win Rate with plain-language definitions
6. **Understanding Lookahead Bias** — why Scenario 2 results can't be used forward
7. **In-Sample vs Out-of-Sample** — research methodology explanation
8. **Research Limitations** — market cycles, signal frequency, data recency
9. **Disclaimer** — full investment disclaimer
10. **Data Sources** — CBBI official, yfinance, date ranges

---

## 4. Data Specification

### 4.1 Master Dataset (`data/master_dataset.parquet`)

Source: PKL_v4 Phase 1 pipeline output. Do not regenerate in this repo.

| Column | Type | Description |
|---|---|---|
| `date` | DatetimeIndex | Daily, 2012-01-01 to 2026-03-31 |
| `btc_close` | float64 | BTC closing price (signal day T) |
| `btc_open` | float64 | BTC opening price (execution day T+1) |
| `cbbi_confidence` | float64 | Composite CBBI score [0–100] |
| `trolololo` | float64 | **Primary signal column** — Log Regression [0–100] |
| `pi_cycle` | float64 | Pi Cycle Top [0–100] |
| `rupl` | float64 | Relative Unrealized P&L [0–100] |
| `rhodl_ratio` | float64 | RHODL Ratio [0–100] |
| `puell_multiple` | float64 | Puell Multiple [0–100] |
| `two_year_ma_mult` | float64 | 2Y MA Multiplier [0–100] |
| `mvrv_zscore` | float64 | MVRV Z-Score [0–100] |
| `reserve_risk` | float64 | Reserve Risk [0–100] |
| `woobull` | float64 | Woobull NVT [0–100] |
| `fill_flag` | bool | True if forward-filled |
| `phase` | str | `"in_sample"` or `"out_of_sample"` |

### 4.2 Results JSON (`data/optimal_params_summary.json`)

Generated by PKL_v4 Phase 3. Contains:
- `metadata.generated_at`, `metadata.total_trials_per_run`
- `scenario_1.in_sample.{max_return, min_drawdown, max_sharpe}` — each with params + metrics
- `scenario_1.out_of_sample.{max_return, min_drawdown, max_sharpe}` — OOS evaluation of IS-optimal params
- `scenario_1.degradation.{max_return, min_drawdown, max_sharpe}` — IS→OOS degradation %
- `scenario_2.full_dataset.{max_return, min_drawdown, max_sharpe}` — full dataset results
- `scenario_2.disclosure` — mandatory disclosure string
- `buy_and_hold_benchmark.{in_sample, out_of_sample, full_dataset}` — B&H metrics

### 4.3 Trial Logs (`data/trial_log/`)

| File | Size | Contents |
|---|---|---|
| `scenario_1_grid_search_in_sample.parquet` | ~23MB | All 1.29M IS trials: params + metrics |
| `scenario_2_grid_search_full.parquet` | ~23MB | All 1.29M full-dataset trials: params + metrics |

Columns: `threshold_buy, threshold_sell, allocation_buy_pct, allocation_sell_pct, total_return, max_drawdown, sharpe_ratio, win_rate, trade_count`

Loaded lazily (only when Research Results page is visited and heatmap is requested).

---

## 5. Performance Requirements

| Action | Target | Method |
|---|---|---|
| App initial load | < 5s | Pre-load + JIT warmup in `app.py` |
| Dataset load (first time) | < 2s | `@st.cache_data` persists across reruns |
| Simulation run (5,000 days) | < 1s | Numba JIT — C-level loops |
| Heatmap generation | < 8s first, instant after | `@st.cache_data(ttl=3600)` per scenario |
| Trade log table render | < 0.5s | `st.dataframe()` with column config |

**Numba JIT Warmup Strategy:**
```python
# In app.py at startup — run once to pre-compile
import numpy as np
from core.engine import run_backtest_numba
_dummy = np.ones(100, dtype=np.float64)
run_backtest_numba(_dummy, _dummy, _dummy, 20, 75, 0.10, 0.10, 100000.0, 0.001)
```

---

## 6. Deployment Specification

| Aspect | Config |
|---|---|
| Platform | Streamlit Community Cloud (streamlit.io/cloud) |
| Runtime | Python 3.11 |
| Entry point | `app.py` |
| Packages | `requirements.txt` |
| Memory | ~512MB (master dataset + one trial log in memory) |
| Data files | Committed to repo (under 50MB Git LFS threshold) |
| Branch | `main` → auto-deploy |
| Cold start | ~10–15s (Numba compilation included); spinner shown |

### requirements.txt
```
streamlit>=1.35.0
pandas>=2.0.0
numpy>=1.24.0
numba>=0.58.0
plotly>=5.18.0
pyarrow>=14.0.0
```

---

## 7. Out of Scope

The following items are explicitly **not** in scope for this application:

- Live data fetching from CBBI API or yfinance (data is static, frozen at 2026-03-31)
- User accounts, authentication, or saved sessions
- OOS sensitivity heatmap (only 3 OOS evaluations exist — insufficient for heatmap)
- Multi-indicator compound signals (app uses Trolololo exclusively)
- Real-time trading recommendations or forward signals
- Mobile-first responsive design (target: desktop ≥ 1280px, tablet ≥ 768px)
- Data update pipeline (belongs in PKL_v4, not this repo)

---

## 8. Success Criteria

- [ ] App loads and is publicly accessible via Streamlit Community Cloud URL
- [ ] Simulator runs any valid parameter combination and returns results in < 1s
- [ ] Equity curve, CBBI chart, and trade log all render correctly post-simulation
- [ ] Research Results page displays both scenarios with disclaimer visible before Scenario 2 numbers
- [ ] Sensitivity heatmaps render correctly from trial log parquets
- [ ] Download buttons return valid CSV and JSON files
- [ ] Numba JIT warmup eliminates cold-start delay on first simulation click
- [ ] All three pages navigable without error on Chrome, Firefox, Edge

---

## 9. Development Phases

| Phase | Scope | Status |
|---|---|---|
| **9.1 Foundation** | Project structure, `core/engine.py`, `core/data_loader.py`, `requirements.txt`, `app.py` home page | ⏳ |
| **9.2 Simulator** | `core/simulator.py`, `core/charts.py`, `pages/1_Simulator.py` full implementation | ⏳ |
| **9.3 Research Results** | `pages/2_Research_Results.py`, heatmap builder, comparison table | ⏳ |
| **9.4 Documentation** | `pages/3_Documentation.py`, full content | ⏳ |
| **9.5 Polish & Deploy** | UI refinement, Numba warmup, deploy to Streamlit Cloud | ⏳ |
