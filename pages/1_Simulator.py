"""
pages/1_Simulator.py
====================
Interactive backtesting simulator — Page 1 of CBBI Strategy Lab.
"""

import streamlit as st
import pandas as pd
import numpy as np

from core.data_loader import load_master_dataset, get_dataset_slice
from core.engine import run_backtest_full
from core.charts import build_equity_chart, build_cbbi_chart
from core.styles import inject_css

st.set_page_config(page_title="Simulator · CBBI Strategy Lab", page_icon="⚡", layout="wide")
inject_css()

# ── Presets ───────────────────────────────────────────────────────────────────
PRESETS = {
    "Conservative": dict(threshold_buy=10, threshold_sell=85, alloc_buy=5,  alloc_sell=5),
    "Moderate":     dict(threshold_buy=20, threshold_sell=75, alloc_buy=10, alloc_sell=10),
    "Aggressive":   dict(threshold_buy=30, threshold_sell=65, alloc_buy=20, alloc_sell=20),
    "Custom":       None,
}

# ── Load data ─────────────────────────────────────────────────────────────────
df_full = load_master_dataset()
DATA_MIN = df_full.index.min().date()
DATA_MAX = df_full.index.max().date()

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("## ⚡ Strategy Simulator")
st.markdown(
    "<div style='opacity:0.5; font-size:0.88rem; margin-bottom:1.5rem;'>"
    "Run live backtests with any custom parameters · Signal: <b>Trolololo</b> (Log Regression) · "
    "Execution: T+1 open price · Fee adjustable"
    "</div>",
    unsafe_allow_html=True,
)

# ── Layout: input (left) | results (right) ───────────────────────────────────
col_input, col_results = st.columns([2, 3], gap="large")

# ═══════════════════════════════════════════════════════════════════════════════
# INPUT PANEL
# ═══════════════════════════════════════════════════════════════════════════════
with col_input:
    st.markdown("#### Configuration")

    # Preset selector
    preset_name = st.selectbox(
        "Risk Preset",
        options=list(PRESETS.keys()),
        index=1,   # Default: Moderate
        help="Load a predefined parameter set or choose Custom to set manually.",
    )
    preset = PRESETS[preset_name]

    # Separator
    st.markdown("---")

    # Parameter sliders — pre-fill from preset
    buy_default  = preset["threshold_buy"]  if preset else 20
    sell_default = preset["threshold_sell"] if preset else 75
    ab_default   = preset["alloc_buy"]      if preset else 10
    as_default   = preset["alloc_sell"]     if preset else 10

    threshold_buy = st.slider(
        "📉 Buy Threshold",
        min_value=1, max_value=45,
        value=buy_default, step=1,
        help="BUY signal fires when Trolololo drops BELOW this value. Lower = more selective.",
    )
    threshold_sell = st.slider(
        "📈 Sell Threshold",
        min_value=55, max_value=100,
        value=sell_default, step=1,
        help="SELL signal fires when Trolololo rises ABOVE this value. Higher = more selective.",
    )

    st.markdown(
        f"<div class='info-strip' style='margin: 0.3rem 0 0.8rem;'>"
        f"Hold zone: <b>{threshold_buy} – {threshold_sell}</b> &nbsp;|&nbsp; "
        f"Spread: <b>{threshold_sell - threshold_buy} points</b>"
        f"</div>",
        unsafe_allow_html=True,
    )

    col_ab, col_as = st.columns(2)
    with col_ab:
        alloc_buy = st.slider("💰 Buy Alloc %", 1, 25, ab_default, 1,
                              help="% of available cash deployed per BUY signal.")
    with col_as:
        alloc_sell = st.slider("💸 Sell Alloc %", 1, 25, as_default, 1,
                               help="% of BTC holdings sold per SELL signal.")

    st.markdown("---")

    # Date range
    st.markdown("**📅 Simulation Period**")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_date = st.date_input("From", value=pd.Timestamp("2012-01-01").date(),
                                   min_value=DATA_MIN, max_value=DATA_MAX)
    with col_d2:
        end_date = st.date_input("To", value=DATA_MAX,
                                 min_value=DATA_MIN, max_value=DATA_MAX)

    # Initial capital
    initial_cash = st.number_input(
        "💵 Initial Capital (USD)",
        min_value=1_000, max_value=10_000_000,
        value=100_000, step=1_000,
        format="%d",
    )

    # Advanced settings
    with st.expander("⚙ Advanced Settings"):
        fee_rate_pct = st.slider(
            "Trading Fee %",
            min_value=0.0, max_value=0.5,
            value=0.1, step=0.05,
            format="%.2f%%",
            help="Per-transaction fee. Binance Spot = 0.1%. Coinbase = 0.2%. 0% = no fees.",
        )
        fee_rate = fee_rate_pct / 100.0

    # Validation
    valid = True
    if threshold_buy >= threshold_sell:
        st.error("⛔ Buy Threshold must be less than Sell Threshold.")
        valid = False
    if start_date >= end_date:
        st.error("⛔ Start date must be before end date.")
        valid = False
    if (pd.Timestamp(end_date) - pd.Timestamp(start_date)).days < 365:
        st.warning("⚠ Period is less than 1 year — results may not be meaningful.")

    # Run button
    run_clicked = st.button("▶ Run Simulation", type="primary", disabled=not valid)

# ═══════════════════════════════════════════════════════════════════════════════
# RESULTS PANEL
# ═══════════════════════════════════════════════════════════════════════════════
with col_results:

    if not run_clicked and "sim_result" not in st.session_state:
        st.markdown("""
        <div style="
          display: flex; flex-direction: column; align-items: center;
          justify-content: center; min-height: 400px; opacity: 0.35;
          gap: 1rem; text-align: center;
        ">
          <div style="font-size: 3rem;">⚡</div>
          <div style="font-size: 1rem;">Configure parameters on the left<br>and click <b>Run Simulation</b></div>
        </div>
        """, unsafe_allow_html=True)

    else:
        # ── Run simulation ────────────────────────────────────────────────────
        if run_clicked:
            df_slice = get_dataset_slice(df_full, str(start_date), str(end_date))

            if len(df_slice) < 30:
                st.error("Not enough data in the selected date range.")
                st.stop()

            with st.spinner("Running backtest..."):
                result = run_backtest_full(
                    df_slice,
                    threshold_buy=threshold_buy,
                    threshold_sell=threshold_sell,
                    alloc_buy_pct=alloc_buy / 100.0,
                    alloc_sell_pct=alloc_sell / 100.0,
                    initial_cash=float(initial_cash),
                    fee_rate=fee_rate,
                )
            st.session_state["sim_result"] = result
            st.session_state["sim_df_slice"] = df_slice
            st.session_state["sim_params"] = dict(
                threshold_buy=threshold_buy,
                threshold_sell=threshold_sell,
            )

        result   = st.session_state["sim_result"]
        df_slice = st.session_state["sim_df_slice"]
        params   = st.session_state["sim_params"]
        m        = result.metrics
        bm       = result.benchmark_metrics

        # ── Low sample warning ────────────────────────────────────────────────
        if result.low_sample_warning:
            st.markdown(
                "<div class='warn-badge'>⚠ Low trade count (&lt; 10) — "
                "statistical metrics may not be reliable</div>",
                unsafe_allow_html=True,
            )
            st.markdown("")

        # ── Metric cards ──────────────────────────────────────────────────────
        mc1, mc2, mc3, mc4 = st.columns(4)

        def _fmt_pct(v):  return f"{v*100:+.1f}%"
        def _fmt_signed(v): return f"{v:+.2f}"

        with mc1:
            bh_r = bm["total_return"]
            st.metric(
                "Total Return",
                _fmt_pct(m["total_return"]),
                delta=f"B&H: {_fmt_pct(bh_r)}",
                delta_color="off",
            )
        with mc2:
            st.metric("Max Drawdown", _fmt_pct(-m["max_drawdown"]))
        with mc3:
            st.metric(
                "Sharpe Ratio",
                f"{m['sharpe_ratio']:.2f}",
                delta=f"B&H: {bm['sharpe_ratio']:.2f}",
                delta_color="off",
            )
        with mc4:
            wr_pct = m["win_rate"] * 100
            st.metric(
                "Win Rate",
                f"{wr_pct:.1f}%",
                delta=f"{m['trade_count']} trades",
                delta_color="off",
                help="Win rate = % of SELL trades that were profitable vs avg entry price.",
            )

        st.markdown("")

        # ── Equity chart ──────────────────────────────────────────────────────
        fig_equity = build_equity_chart(result)
        st.plotly_chart(fig_equity, width='stretch')

        # ── CBBI signal chart ─────────────────────────────────────────────────
        fig_cbbi = build_cbbi_chart(
            df_slice,
            threshold_buy=params["threshold_buy"],
            threshold_sell=params["threshold_sell"],
        )
        st.plotly_chart(fig_cbbi, width='stretch')

        # ── Auto-generated summary text ───────────────────────────────────────
        period_yrs = (pd.Timestamp(end_date) - pd.Timestamp(start_date)).days / 365
        st.info(
            f"**Summary:** With a Buy Threshold of **{threshold_buy}** and Sell Threshold of "
            f"**{threshold_sell}**, your strategy generated a **{m['total_return']*100:+.1f}% total return** "
            f"over {period_yrs:.1f} years, compared to Buy & Hold at **{bh_r*100:+.1f}%** "
            f"over the same period. "
            f"The strategy completed **{m['trade_count']}** trades "
            f"with a win rate of **{m['win_rate']*100:.1f}%** "
            f"and a maximum drawdown of **{m['max_drawdown']*100:.1f}%**."
        )

        # ── Trade log ─────────────────────────────────────────────────────────
        st.markdown("#### 📋 Trade Log")

        tlog = result.trade_log
        if tlog.empty:
            st.caption("No trades were executed with these parameters.")
        else:
            # Style BUY/SELL rows
            def _highlight_action(row):
                if row["Action"] == "BUY":
                    return ["background-color: rgba(34,197,94,0.1)"] * len(row)
                elif row["Action"] == "SELL":
                    return ["background-color: rgba(239,68,68,0.1)"] * len(row)
                return [""] * len(row)

            n_show = st.slider("Show last N trades", 10, min(500, len(tlog)), min(50, len(tlog)), 10)
            tlog_show = tlog.tail(n_show).copy()
            tlog_show["Date"] = tlog_show["Date"].dt.strftime("%Y-%m-%d")

            styled = tlog_show.style.apply(_highlight_action, axis=1).format({
                "Exec Price (BTC Open)": "${:,.2f}",
                "Amount (USD)":          "${:,.2f}",
                "Portfolio Value After": "${:,.2f}",
                "Trolololo Signal":      "{:.1f}",
            })

            st.dataframe(styled, width='stretch', height=320)

            # Download button
            csv = tlog.to_csv(index=False)
            st.download_button(
                "⬇ Export Full Trade Log (CSV)",
                data=csv,
                file_name=f"cbbi_trade_log_buy{threshold_buy}_sell{threshold_sell}.csv",
                mime="text/csv",
            )
