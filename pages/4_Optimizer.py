"""
pages/4_Optimizer.py
====================
Dynamic Grid Search Optimizer — Live Parameter Updater.

This page runs a Numba-accelerated grid search over live BTC price data
(fetched from Yahoo Finance) with Trolololo computed independently via
logarithmic regression. This eliminates dependence on the CBBI API and
resolves the "Index Revision Bias" documented in our research limitations.

Academic context
----------------
The core research (the core research repository) was conducted on a frozen snapshot (master_dataset.parquet).
That snapshot is permanently fixed — changing it would compromise reproducibility.

This optimizer is a practical DEPLOYMENT extension: it finds parameters that
actually work in production against today's fresh data, using the same
deterministic Trolololo formula as the research snapshot.

See: Research Results → Research Notes → Limitation: Index Recalculation Risk
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd

from core.styles import inject_css
from core.data_loader import fetch_live_dataset
from core.optimizer import (
    run_live_optimization,
    load_live_params,
    warmup_optimizer,
    BUY_THRESHOLDS,
    SELL_THRESHOLDS,
    ALLOC_STEPS,
    LIVE_PARAMS_PATH,
)

# Pre-compute total combinations for display
n_combos = len(BUY_THRESHOLDS) * len(SELL_THRESHOLDS) * len(ALLOC_STEPS) ** 2

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Optimizer — CBBI Strategy Lab",
    page_icon="⚙️",
    layout="wide",
)
inject_css()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_pct(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{v*100:.1f}%"

def _fmt_dd(v: float) -> str:
    return f"{v*100:.1f}%"

def _fmt_num(v) -> str:
    return f"{v:,}"


# ── Page header ───────────────────────────────────────────────────────────────

st.markdown("""
<div style="margin-bottom:1.5rem">
  <div style="font-size:0.78rem;font-weight:700;letter-spacing:0.14em;
              text-transform:uppercase;color:var(--accent);margin-bottom:0.3rem">
    CBBI STRATEGY LAB
  </div>
  <h1 style="font-size:2rem;font-weight:800;margin:0 0 0.4rem 0;line-height:1.15">
    ⚙️ Dynamic Parameter Optimizer
  </h1>
  <p style="font-size:0.95rem;color:var(--muted);max-width:660px;margin:0">
    Re-optimize strategy parameters against <strong>fresh live BTC price data</strong>
    (Yahoo Finance) with Trolololo computed via independent logarithmic regression.
    No reliance on the CBBI API — signal values are deterministic and reproducible.
  </p>
</div>
""", unsafe_allow_html=True)

# ── Context banner ────────────────────────────────────────────────────────────

st.info(
    "📌 **Research Scope Note** — The academic backtest used a frozen snapshot. "
    "This optimizer is a *practical extension* outside that scope. "
    "Results here are for live deployment only — not for comparing against the IS/OOS research findings.",
    icon=None,
)

st.markdown("---")

# ── Search space summary ──────────────────────────────────────────────────────

n_combos = len(BUY_THRESHOLDS) * len(SELL_THRESHOLDS) * len(ALLOC_STEPS) ** 2

col_a, col_b, col_c, col_d = st.columns(4)
with col_a:
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">Buy Thresholds</div>
      <div class="metric-value">{len(BUY_THRESHOLDS)}</div>
      <div class="metric-subtext">{BUY_THRESHOLDS[0]} → {BUY_THRESHOLDS[-1]} (step 2)</div>
    </div>""", unsafe_allow_html=True)
with col_b:
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">Sell Thresholds</div>
      <div class="metric-value">{len(SELL_THRESHOLDS)}</div>
      <div class="metric-subtext">{SELL_THRESHOLDS[0]} → {SELL_THRESHOLDS[-1]} (step 2)</div>
    </div>""", unsafe_allow_html=True)
with col_c:
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">Allocation Steps</div>
      <div class="metric-value">{len(ALLOC_STEPS)} × {len(ALLOC_STEPS)}</div>
      <div class="metric-subtext">Buy & Sell independently</div>
    </div>""", unsafe_allow_html=True)
with col_d:
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">Total Combinations</div>
      <div class="metric-value">{n_combos:,}</div>
      <div class="metric-subtext">Parallel Numba execution</div>
    </div>""", unsafe_allow_html=True)


# ── Existing results (if any) ─────────────────────────────────────────────────

st.markdown("### 📊 Current Live Parameters")

existing = load_live_params()
if existing and existing.get("status") == "success":
    gen_at = existing.get("generated_at", "Unknown")
    date_range = existing.get("data_date_range", "Unknown")
    elapsed = existing.get("elapsed_seconds", 0)
    total_c = existing.get("total_combinations", 0)

    st.markdown(f"""
    <div class="metric-card" style="margin-bottom:1rem">
      <div class="metric-label">Last Optimization Run</div>
      <div class="metric-value" style="font-size:1.2rem">{gen_at}</div>
      <div class="metric-subtext">
        Trained on: {date_range} &nbsp;·&nbsp;
        {total_c:,} combinations &nbsp;·&nbsp;
        {elapsed}s runtime
      </div>
    </div>""", unsafe_allow_html=True)

    mr = existing.get("max_return", {})
    ms = existing.get("max_sharpe", {})
    md = existing.get("min_drawdown", {})

    col1, col2, col3 = st.columns(3)

    for col, obj_data, obj_label, accent in [
        (col1, mr, "🏆 Max Return", "#0a7c6e"),
        (col2, ms, "📐 Max Sharpe", "#0369a1"),
        (col3, md, "🛡️ Min Drawdown", "#7c3aed"),
    ]:
        with col:
            if obj_data:
                ret_pct = _fmt_pct(obj_data.get("total_return", 0))
                st.markdown(f"""
                <div class="metric-card" style="border-left:4px solid {accent}">
                  <div class="metric-label">{obj_label}</div>
                  <div style="margin-top:0.6rem;font-size:0.88rem;line-height:1.8">
                    <b>Buy ≤ {obj_data.get('threshold_buy')}</b> &nbsp;|&nbsp;
                    <b>Sell ≥ {obj_data.get('threshold_sell')}</b><br>
                    Alloc: {obj_data.get('allocation_buy_pct',0)*100:.0f}% buy /
                           {obj_data.get('allocation_sell_pct',0)*100:.0f}% sell<br>
                    Return: <b>{ret_pct}</b> &nbsp;·&nbsp;
                    Sharpe: <b>{obj_data.get('sharpe_ratio',0):.2f}</b><br>
                    Drawdown: <b>{_fmt_dd(obj_data.get('max_drawdown',0))}</b> &nbsp;·&nbsp;
                    Trades: <b>{obj_data.get('trade_count',0)}</b>
                  </div>
                </div>""", unsafe_allow_html=True)
else:
    st.warning(
        "No live optimization has been run yet. "
        "Click **Run Optimization** below to generate live-aligned parameters.",
        icon="⚠️",
    )


# ── Run optimizer ─────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("### 🚀 Run New Optimization")

with st.expander("⚙️ Advanced Settings", expanded=False):
    split_date = st.text_input(
        "IS/OOS Split Date (parameters optimized on IS period only)",
        value="2021-01-01",
        help="Data before this date is used for in-sample optimization. OOS data is never seen during training.",
    )
    initial_cash = st.number_input(
        "Initial Capital (USD)", value=100_000, step=10_000, min_value=1_000,
    )
    fee_rate = st.number_input(
        "Trading Fee Rate", value=0.001, step=0.0005, format="%.4f", min_value=0.0,
    )

st.markdown(
    f"""
    <div style="background:var(--bg-card);border:1.5px solid var(--border);
                border-radius:8px;padding:1rem 1.2rem;margin-bottom:1rem;
                font-size:0.88rem;color:var(--muted)">
      This will fetch the latest BTC price data from <strong>Yahoo Finance</strong>,
      compute Trolololo via logarithmic regression, then run
      <strong>{n_combos:,} parallel backtests</strong> using Numba JIT compilation.
      Typical runtime: <strong>5&ndash;20 seconds</strong> depending on your CPU.
    </div>""",
    unsafe_allow_html=True,
)

run_btn = st.button("⚙️ Run Optimization", type="primary", use_container_width=True)

if run_btn:
    progress_bar  = st.progress(0.0)
    status_text   = st.empty()

    def _progress(pct: float, msg: str) -> None:
        progress_bar.progress(min(pct, 1.0))
        status_text.markdown(f"*{msg}*")

    try:
        # Step 1: Fetch live data
        _progress(0.01, "Fetching live BTC price data from Yahoo Finance...")
        df_live = fetch_live_dataset()

        # Step 2: Warm up Numba (first run only — compiles JIT kernels)
        _progress(0.04, "Warming up Numba JIT compiler (first run only)…")
        warmup_optimizer()

        # Step 3: Run grid search
        result = run_live_optimization(
            df_live,
            initial_cash=float(initial_cash),
            fee_rate=float(fee_rate),
            progress_cb=_progress,
            split_date=split_date,
        )

        progress_bar.progress(1.0)

        if result.status == "success":
            status_text.empty()
            st.success(
                f"✅ Optimization complete — {result.total_combinations:,} combinations "
                f"in **{result.elapsed_seconds}s** — results saved to `data/live_optimal_params.json`"
            )
            st.rerun()

        else:
            status_text.error(f"❌ Error: {result.error_message}")

    except Exception as e:
        status_text.empty()
        st.error(f"❌ Unexpected error: {e}")
        st.exception(e)


# ── How to use results in Simulator ──────────────────────────────────────────

st.markdown("---")
st.markdown("### 🔗 Using These Results in the Simulator")
st.markdown("""
After running the optimizer:

1. **Go to the Simulator page** (`← Simulator` in the sidebar)
2. **Select `🟢 Live CBBI API`** as your data source
3. **Set parameters manually** from the table above (e.g. Max Return recommendation)
4. Run the simulation — you're now using parameters that reflect today's live CBBI formula

> 💡 The optimizer targets the **in-sample period** (before your split date) to prevent overfitting.
> You can then validate OOS performance directly in the Simulator using the Live API data.
""")

# ── Index revision bias explainer ─────────────────────────────────────────────

with st.expander("📚 Why independent Trolololo calculation was chosen"):
    st.markdown("""
    **Colin's CBBI is not static.** When he adds, removes, or modifies an indicator
    (e.g., removing Stock-to-Flow, reweighting Pi Cycle), his algorithm retroactively
    recalculates the entire CBBI history back to 2011.

    This means:
    - The score for `2021-01-01` in our frozen `master_dataset.parquet` is **63.65**
    - The same date via the live CBBI API (2026-04-17) was **78.13**

    **A 14.5-point drift on one day.** Across thousands of days, this shifts when
    every single buy/sell signal fires.

    **The solution:** Instead of fetching from the CBBI API, the Trolololo indicator
    is computed **independently** from BTC price data using a power-law logarithmic
    regression model (`core/trolololo.py`). This formula is deterministic — it
    produces the same value for any given BTC price history, regardless of what
    Colin changes in his index.

    The research snapshot (frozen) used this same formula. So the live optimizer
    is now consistent with the academic research by design.

    ---
    *For the academic research paper*, this phenomenon is documented as a limitation
    under "Index Revision Risk." The frozen dataset remains the canonical research
    artifact — it is reproducible. This optimizer is the practical deployment solution.
    """)
