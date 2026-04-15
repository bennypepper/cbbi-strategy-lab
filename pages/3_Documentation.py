"""
pages/3_Documentation.py
========================
Methodology, glossary, and full disclaimer.
"""

import streamlit as st

st.set_page_config(page_title="Documentation · CBBI Strategy Lab", page_icon="📖", layout="wide")

st.markdown("## 📖 Documentation")
st.markdown(
    "<div style='opacity:0.5; font-size:0.88rem; margin-bottom:1.5rem;'>"
    "Methodology · Indicator glossary · Metric definitions · Research disclaimer"
    "</div>",
    unsafe_allow_html=True,
)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "What is CBBI?",
    "Strategy Logic",
    "Metric Glossary",
    "Research Methodology",
    "Disclaimer & Limitations",
])

# ── Tab 1: What is CBBI ───────────────────────────────────────────────────────
with tab1:
    st.markdown("""
### What is CBBI?

The **Crypto Bitcoin Bull/Bear Index (CBBI)** is a composite on-chain data indicator created by
Cole Garner that attempts to identify where Bitcoin is within its market cycle.

Rather than relying on price alone, CBBI aggregates 9 independent on-chain metrics that
historically correlate with Bitcoin's cyclical peaks and troughs. Each metric is normalized
to a scale of **0 to 100**, and CBBI blends them into a single Confidence Score.

> **0 = Deep bear market / accumulation zone**  
> **100 = Peak euphoria / distribution zone**

Data source: [cbbi.info](https://cbbi.info) · Dataset: 2012-01-01 to 2026-03-31

---

### The 9 CBBI Sub-Indicators

| Indicator | Internal Name | Description |
|---|---|---|
| **Trolololo** ⭐ | `trolololo` | Logarithmic Regression Band (Rainbow Chart) — **primary signal used in this app** |
| Pi Cycle Top | `pi_cycle` | Identifies cycle tops using moving average crossovers |
| RUPL | `rupl` | Relative Unrealized Profit / Loss across all wallets |
| RHODL Ratio | `rhodl_ratio` | Compares realized value of coins from different age bands |
| Puell Multiple | `puell_multiple` | Miner profitability relative to 1-year average |
| 2Y MA Multiplier | `two_year_ma_mult` | BTC price relative to 2-year moving average |
| MVRV Z-Score | `mvrv_zscore` | Market cap vs realized cap in standard deviations |
| Reserve Risk | `reserve_risk` | Confidence vs opportunity cost of long-term holders |
| Woobull NVT | `woobull` | Network Value to Transactions ratio |

---

### Why Trolololo?

Phase 2 of the underlying research performed **Spearman correlation analysis** across all 9 indicators
against forward Bitcoin returns at 7, 14, 30, 60, and 90-day lag windows on In-Sample data (2012–2020).

The analysis found that **Trolololo (Logarithmic Regression)** consistently showed the highest
composite score — combining both correlation strength and statistical significance (p < 0.05) —
across multiple lag windows. This makes it the most reliable indicator for threshold-based signal generation
within this research framework.

All simulations in this app use Trolololo as the signal column.
    """)

# ── Tab 2: Strategy Logic ─────────────────────────────────────────────────────
with tab2:
    st.markdown("""
### Strategy Trading Logic

The strategy is a **threshold-based, fractional allocation** system. It does not predict price —
it reacts to on-chain cycle position.

#### Signal Rules

| Condition | Action | Amount |
|---|---|---|
| Trolololo < Buy Threshold | **BUY** | `alloc_buy_pct × current_cash` |
| Trolololo > Sell Threshold | **SELL** | `alloc_sell_pct × current_btc_holdings` |
| Buy Threshold ≤ Trolololo ≤ Sell Threshold | **HOLD** | No trade |

#### Execution (Anti-Lookahead Bias)

All trades follow the **T+1 execution rule** to prevent lookahead bias:

```
Day T:    Observe Trolololo[T]  →  Decision made (BUY / SELL / HOLD)
Day T+1:  Execute at BTC Open Price[T+1]
```

This ensures that no future information is used in trading decisions. The strategy only acts
on information available at market close on day T.

#### Fee Model

Each trade incurs a percentage fee applied to the gross transaction value:
- Default: **0.1%** (typical for Binance Spot trading)
- Configurable: 0% – 0.5% in Advanced Settings

Fee is deducted from the transaction amount:
- BUY: `net_amount = trade_amount × (1 - fee_rate)`
- SELL: `net_proceeds = gross_proceeds × (1 - fee_rate)`

#### Portfolio State

The portfolio tracks three values at all times:
- **Cash (USD)**: idle capital not yet deployed
- **BTC Held**: current Bitcoin position
- **Portfolio Value**: `cash + (btc_held × btc_close_price)`

Win Rate is calculated per SELL trade: a win is a SELL where net proceeds exceed the
average cost basis of the BTC that was sold.
    """)

# ── Tab 3: Metric Glossary ────────────────────────────────────────────────────
with tab3:
    st.markdown("""
### Metric Definitions

#### Total Return
The percentage gain (or loss) of the strategy portfolio from start to end:
```
Total Return = (Final Portfolio Value - Initial Capital) / Initial Capital
```
e.g., +234% means your $100,000 grew to $334,000.

---

#### Maximum Drawdown (MDD)
The largest peak-to-trough decline in portfolio value:
```
MDD = max over all periods: (Peak Value - Trough Value) / Peak Value
```
e.g., -62.8% means at the worst point, the portfolio had lost 62.8% of its peak value.
Lower is better. A high MDD means the strategy experienced large interim losses.

---

#### Sharpe Ratio
Risk-adjusted return, measuring return per unit of volatility:
```
Sharpe = (Mean Daily Return - Risk-Free Rate) / Std Dev of Daily Returns × √365
```
- Risk-free rate used: **4.0% per year** (US Treasury approximation)
- Sharpe > 1.0 is generally considered good for crypto
- Sharpe > 2.0 is excellent
- Negative Sharpe means the strategy underperformed the risk-free rate

---

#### Win Rate
The percentage of SELL trades that were profitable relative to average entry price:
```
Win Rate = (Profitable SELL Count) / (Total SELL Count)
```
Note: Win Rate only captures directional accuracy of sells, not the size of gains/losses.
A strategy with 40% win rate can still be profitable if wins are much larger than losses.

---

#### Trade Count
Total number of BUY + SELL transactions executed.
A count below 10 triggers a warning: statistical metrics like Win Rate and Sharpe
are not reliable with very few observations.

---

#### Buy & Hold Benchmark
A passive strategy that invests 100% of initial capital at day 1 and holds until the end.
Used as a performance baseline for the active strategy.
    """)

# ── Tab 4: Research Methodology ───────────────────────────────────────────────
with tab4:
    st.markdown("""
### Research Methodology

This application presents results from a 4-phase academic research project.

#### Phase 1 — Data Pipeline
- Source 1: CBBI official dataset (XLSX from cbbi.info) — all 9 indicators + composite score
- Source 2: BTC daily Open prices from yfinance (`BTC-USD`)
- Preprocessing: string parsing → float64, forward fill ≤ 7 days, date alignment
- Final dataset: 2012-01-01 to 2026-03-31 (~5,200 trading days)
- Validation: `validate_no_lookahead()` confirmed no backward fill was applied

#### Phase 2 — Indicator Selection
- Method: Spearman correlation (non-parametric, robust to non-normal distributions)
- Lag windows tested: 7, 14, 30, 60, 90 days forward
- Analysis restricted to **In-Sample data (2012–2020)** to prevent data leakage
- Composite score: `0.6 × |max_spearman_rho| + 0.4 × (1 - min_p_value_normalized)`
- Result: **Trolololo** ranked highest and was selected as the primary signal

#### Phase 3 — Optimization Engine
- Algorithm: **Grid Search** (exhaustive, deterministic)
- Parameter space: `45 × 46 × 25 × 25 = 1,293,750` combinations per run
- Parallelization: `joblib.Parallel` + Numba JIT (`@njit`) for inner loop
- 6 runs total: 2 scenarios × 3 objectives (Max Return, Min Drawdown, Max Sharpe)

#### Two Scenarios Explained

| | Scenario 1 | Scenario 2 |
|---|---|---|
| Optimization data | In-Sample (2012–2020) | Full dataset (2012–2026) |
| Validation | Forward test on OOS (2021–2026) | None |
| Lookahead bias | ❌ None — strictly isolated | ✅ Present by design |
| Research purpose | Prove robustness | Map historical ceiling |

#### In-Sample vs Out-of-Sample
- **In-Sample (IS)**: 2012-01-01 – 2020-12-31 — data used for optimization
- **Out-of-Sample (OOS)**: 2021-01-01 – 2026-03-31 — data held back for validation

OOS performance is the honest benchmark of how the optimized strategy would have performed
on data it never "saw" during training. Significant performance degradation from IS to OOS
is a warning sign of overfitting.

#### Manual Verification
20 representative trade points (bull, bear, sideways) were manually verified against the
backtest engine output. All 20 matched within `abs(delta) < 1e-6`.
    """)

# ── Tab 5: Disclaimer & Limitations ──────────────────────────────────────────
with tab5:
    st.markdown("""
### ⚠ Investment Disclaimer

**CBBI Strategy Lab is an academic research tool built for educational purposes only.**

Nothing on this platform constitutes financial advice, investment advice, trading advice,
or any other type of advice. The content on this application should not be used as the
basis for any financial decision.

Historical backtesting results are **not a guarantee of future performance**. Past
performance in financial markets is not indicative of future results. Markets, especially
cryptocurrency markets, can behave in ways that are entirely different from historical patterns.

**Bitcoin and cryptocurrency markets involve substantial risk of loss.** You should never
invest money that you cannot afford to lose entirely.

By using this application, you acknowledge that:
1. All results are based on historical simulations, not live or forward-looking signals
2. Scenario 2 results contain intentional lookahead bias and cannot be used for trading
3. The research authors are not financial advisors or licensed investment professionals
4. This tool was developed as part of undergraduate academic research (PKL 2026)

---

### Research Limitations

The following limitations should be considered when interpreting results:

**1. Market Cycle Coverage**  
The Bitcoin dataset (2012–2026) covers approximately 3–4 full market cycles.
This is a small sample size for statistical inference. Parameters optimal over 3 cycles
may not generalize to future cycles with different characteristics.

**2. Signal Frequency in OOS Period**  
The Out-of-Sample period (2021–2026) exhibited different CBBI dynamics than the In-Sample
period. The CBBI Trolololo indicator spent extended periods in the "hold zone," generating
fewer trades than during In-Sample. This is a feature of the market cycle, not a system failure.

**3. Data Recency**  
Data is frozen at 2026-03-31. The application does not update with live prices.
Results do not reflect market conditions after this date.

**4. Execution Assumptions**  
The backtest assumes:
- Infinite liquidity (any amount can be bought/sold at the stated open price)
- No slippage beyond the fee rate
- No partial fills or order failures
- BTC open price as the sole execution price (no intraday variation modeled)

**5. Parameter Overfitting**  
Despite the IS/OOS split, Grid Search with 1.29M combinations on a finite dataset
may still select parameters that are overfit to historical noise patterns.
The OOS forward test provides evidence of generalizability, but is not proof of robustness.

---

### Data Sources

| Source | Data | Coverage |
|---|---|---|
| [CBBI Official (cbbi.info)](https://cbbi.info) | 9 sub-indicators + Confidence Score | 2011-06-27 – 2026-03-15 |
| Yahoo Finance (via yfinance) | BTC-USD daily Open price | 2012-01-01 – 2026-03-31 |

This application is not affiliated with, endorsed by, or connected to CBBI, cbbi.info,
Cole Garner, Yahoo Finance, or any cryptocurrency exchange.
    """)
