"""
pages/1_Simulator.py
====================
Interactive backtesting simulator — Page 1 of CBBI Strategy Lab.
"""

import streamlit as st
import pandas as pd
import numpy as np

from core.data_loader import load_master_dataset, fetch_cbbi_live, get_dataset_slice, load_research_results
from core.engine import run_backtest_full
from core.charts import build_equity_chart, build_cbbi_chart  # both now Plotly
from core.styles import inject_css
from core.utils import format_percentage, format_currency, format_number
from core.optimizer import load_live_params

st.set_page_config(page_title="Simulator · CBBI Strategy Lab", page_icon="⚡", layout="wide")
inject_css()

# ── Scenario definitions — names match CLI exactly ───────────────────────────
def _load_scenario_params(results: dict, obj_key: str) -> dict:
    """
    Mirror of CLI's load_optimal_params().
    Reads scenario_2.full_dataset.<obj_key> from the JSON results file.
    """
    FALLBACKS = {
        "max_return":   dict(threshold_buy=45, threshold_sell=64, alloc_buy=25, alloc_sell=25),
        "min_drawdown": dict(threshold_buy=1,  threshold_sell=55, alloc_buy=1,  alloc_sell=25),
        "max_sharpe":   dict(threshold_buy=13, threshold_sell=100,alloc_buy=25, alloc_sell=1),
    }
    try:
        p = results["scenario_2"]["full_dataset"][obj_key]
        return dict(
            threshold_buy  = int(p["threshold_buy"]),
            threshold_sell = int(p["threshold_sell"]),
            alloc_buy      = int(round(p["allocation_buy_pct"]  * 100)),
            alloc_sell     = int(round(p["allocation_sell_pct"] * 100)),
        )
    except (KeyError, TypeError):
        return FALLBACKS.get(obj_key, FALLBACKS["max_return"])

CUSTOM_LABEL = "🔧 Custom (Manual Configuration)"

SCENARIOS = {
    "📈 Maximum Return (Aggressive)":         ("max_return",   "Maximum Return"),
    "🛡️ Minimum Drawdown (Conservative)":   ("min_drawdown", "Minimum Drawdown"),
    "⚖️ Maximum Sharpe Ratio (Balanced)":  ("max_sharpe",   "Maximum Sharpe Ratio"),
}
HISTORICAL_SCENARIO_KEYS = list(SCENARIOS.keys())

# Live optimized presets (injected dynamically if optimizer has run)
LIVE_SCENARIOS = {
    "🌐 Live Optimized (Max Return)": "max_return",
    "🌐 Live Optimized (Min Drawdown)": "min_drawdown",
    "🌐 Live Optimized (Max Sharpe)": "max_sharpe",
}

# ── Load data + research results ─────────────────────────────────────────────
st.sidebar.markdown("### 🔌 API Settings")
data_source = st.sidebar.radio(
    "Data Source",
    options=["🗄️ Historical CSV (Default)", "🟢 Live CBBI API"],
    index=0,
    help="Switch between local snapshot and real-time live data directly from Colintalkscrypto API."
)

if "Live CBBI" in data_source:
    try:
        df_full = fetch_cbbi_live()
        st.sidebar.markdown(
            "<div style='font-size:0.8rem; background:rgba(10,124,110,0.1); border-left:3px solid #0a7c6e; padding:10px; margin-top:10px; line-height:1.5;'>"
            "<b>ℹ️ Live Data Context:</b><br/>"
            "Simulator applies your chosen slider parameters to <b>today's live CBBI values</b>. It <b>does not</b> automatically run a new grid search.<br/><br/>"
            "Because the index creator updates the formula and backfills data, live scores differ from the historical CSV. To find parameters optimized for today's formula, run the <b>Optimizer</b> page."
            "</div>",
            unsafe_allow_html=True
        )
    except Exception as e:
        st.sidebar.error(f"Failed to fetch live API: {e}")
        df_full = load_master_dataset()
else:
    df_full = load_master_dataset()

research = load_research_results()
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

    live_params = load_live_params() if "Live CBBI" in data_source else None
    
    if "Live CBBI" in data_source:
        if live_params and live_params.get("status") == "success":
            available_scenarios = list(LIVE_SCENARIOS.keys()) + [CUSTOM_LABEL]
        else:
            available_scenarios = [CUSTOM_LABEL]
            st.warning("⚠️ No Live Optimized parameters found. Run the Optimizer page first to unlock presets, or use Custom.")
    else:
        available_scenarios = HISTORICAL_SCENARIO_KEYS + [CUSTOM_LABEL]

    # Scenario selector — mirrors CLI options 1 / 2 / 3
    scenario_label = st.selectbox(
        "🎯 Optimization Target",
        options=available_scenarios,
        index=0,
        help="Choose a profile based on Grid Search results. "
             "Use optimal parameters, or select Custom for manual configuration.",
    )

    # Resolve params for the chosen scenario
    if scenario_label in LIVE_SCENARIOS and live_params:
        live_key = LIVE_SCENARIOS[scenario_label]
        live_data = live_params.get(live_key, {})
        obj_key = "__live__"
        scenario_name = scenario_label
        opt = dict(
            threshold_buy  = int(live_data.get("threshold_buy", 30)),
            threshold_sell = int(live_data.get("threshold_sell", 65)),
            alloc_buy      = int(round(live_data.get("allocation_buy_pct", 0.25) * 100)),
            alloc_sell     = int(round(live_data.get("allocation_sell_pct", 0.25) * 100)),
        )
    elif scenario_label in SCENARIOS:
        obj_key, scenario_name = SCENARIOS[scenario_label]
    else:
        obj_key = None
        scenario_name = "Custom"

    # Load optimal params for standard scenario (exactly like CLI)
    if obj_key is not None and obj_key != "__live__":
        opt = _load_scenario_params(research, obj_key)
    else:
        opt = dict(threshold_buy=20, threshold_sell=75, alloc_buy=10, alloc_sell=10)

    # Research info callout — mirrors CLI "INFORMASI RISET" block
    if scenario_label in LIVE_SCENARIOS and live_params:
        gen_at = live_params.get("generated_at", "Unknown")
        date_range = live_params.get("data_date_range", "")
        st.markdown(
            f"<div class='info-strip' style='margin:0.4rem 0 0.6rem; font-size:0.82rem; line-height:1.8;'>"
            f"<b>🌐 Live Optimized Parameters</b><br>"
            f"Generated: <b>{gen_at}</b><br>"
            f"Trained on: <b>{date_range}</b><br>"
            f"Buy ≤ <b>{opt['threshold_buy']}%</b> &nbsp;|&nbsp; Sell ≥ <b>{opt['threshold_sell']}%</b><br>"
            f"Alloc: <b>{opt['alloc_buy']}%</b> buy / <b>{opt['alloc_sell']}%</b> sell"
            f"</div>",
            unsafe_allow_html=True,
        )
    elif obj_key is not None and obj_key != "__live__":
        st.markdown(
            f"<div class='info-strip' style='margin:0.4rem 0 0.6rem; font-size:0.82rem; line-height:1.8;'>"
            f"<b>📊 Optimal Grid Search Configuration — {scenario_name}</b><br>"
            f"Buy Threshold &nbsp;: <b>&le;&nbsp;{opt['threshold_buy']}%</b>"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;"
            f"Sell Threshold : <b>&ge;&nbsp;{opt['threshold_sell']}%</b><br>"
            f"Buy Alloc &nbsp;&nbsp;: <b>{opt['alloc_buy']}%</b> of available Cash"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;"
            f"Sell Alloc : <b>{opt['alloc_sell']}%</b> of total BTC"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Separator
    st.markdown("---")

    # Parameter sliders — pre-filled from selected scenario
    buy_default  = opt["threshold_buy"]
    sell_default = opt["threshold_sell"]
    ab_default   = opt["alloc_buy"]
    as_default   = opt["alloc_sell"]

    threshold_buy = st.slider(
        "📉 Buy Threshold",
        min_value=1, max_value=99,
        value=buy_default, step=1,
        help="BUY signal fires when Trolololo is AT OR BELOW this value. Lower = more selective.",
    )
    threshold_sell = st.slider(
        "📈 Sell Threshold",
        min_value=2, max_value=100,
        value=sell_default, step=1,
        help="SELL signal fires when Trolololo is AT OR ABOVE this value. Higher = more selective.",
    )

    # Dynamic Rainbow Gradient Context
    buy_pct = threshold_buy
    sell_pct = threshold_sell
    hold_pct = sell_pct - buy_pct
    
    gradient_html = f"""
    <div style="margin: 0.5rem 0 1rem; padding: 12px; background: white; border: 2px solid #c9c2b8; box-shadow: 4px 4px 0px 0px rgba(33,52,72,0.1);">
        <div style="display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 600; margin-bottom: 6px;">
            <span style="color: #16a34a;">Buy Zone (&le;{threshold_buy})</span>
            <span style="color: #64748b;">Hold Zone ({hold_pct} pts)</span>
            <span style="color: #dc2626;">Sell Zone (&ge;{threshold_sell})</span>
        </div>
        <div style="display: flex; height: 16px; width: 100%; border-radius: 8px; overflow: hidden; border: 1px solid rgba(0,0,0,0.1);">
            <div style="width: {buy_pct}%; background: linear-gradient(90deg, #22c55e, #16a34a);"></div>
            <div style="width: {hold_pct}%; background: #f1f5f9; display: flex; align-items: center; justify-content: center;">
                <div style="width: 100%; height: 2px; background: repeating-linear-gradient(90deg, transparent, transparent 4px, #cbd5e1 4px, #cbd5e1 8px);"></div>
            </div>
            <div style="width: {100 - sell_pct}%; background: linear-gradient(90deg, #ef4444, #dc2626);"></div>
        </div>
    </div>
    """
    st.markdown(
        gradient_html, 
        unsafe_allow_html=True, 
        help="Visual representation of the Buy, Hold, and Sell zones based on your selected thresholds."
    )

    col_ab, col_as = st.columns(2)
    with col_ab:
        alloc_buy = st.slider("💰 Buy Alloc %", 1, 100, ab_default, 1,
                              help="% of available cash deployed per BUY signal.")
    with col_as:
        alloc_sell = st.slider("💸 Sell Alloc %", 1, 100, as_default, 1,
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

        # ── Helper formatters ─────────────────────────────────────────────────
        def _fmt_pct(v):    return format_percentage(v * 100)
        def _fmt_signed(v): return f"{v:+.2f}"

        final_pv    = m["final_portfolio_value"]
        final_bh    = bm["final_value"]
        diff_usd    = final_pv - final_bh
        outperforms = diff_usd >= 0
        diff_color  = "#0a7c6e" if outperforms else "#dc2626"
        diff_label  = "Strategy outperforms 🏆" if outperforms else "Strategy underperforms ⚠️"
        diff_abs    = abs(diff_usd)
        diff_prefix = "+" if outperforms else "-"
        diff_display = f"{diff_prefix}{format_currency(diff_abs)}"

        # ── Row 1: Hero cards — Portfolio Akhir vs HODL ───────────────────────
        hero1, hero2 = st.columns(2)
        with hero1:
            st.markdown(f"""
            <div class="metric-card" style="border-left:4px solid #0a7c6e">
              <div class="metric-label">💼 Final Portfolio</div>
              <div style="font-size:1.65rem;font-weight:800;margin:0.35rem 0;letter-spacing:-0.5px">
                {format_currency(final_pv)}
              </div>
              <div style="font-size:1rem;color:#0a7c6e;font-weight:700">
                {_fmt_pct(m['total_return'])}
              </div>
            </div>""", unsafe_allow_html=True)
        with hero2:
            st.markdown(f"""
            <div class="metric-card" style="border-left:4px solid #0369a1">
              <div class="metric-label">📦 HODL Comparison</div>
              <div style="font-size:1.65rem;font-weight:800;margin:0.35rem 0;letter-spacing:-0.5px">
                {format_currency(final_bh)}
              </div>
              <div style="font-size:1rem;color:#0369a1;font-weight:700">
                {_fmt_pct(bm['total_return'])}
              </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("")

        # ── Row 2: Core metric cards ──────────────────────────────────────────
        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label" style="text-transform:uppercase; font-size:0.75rem; letter-spacing:1px; color:var(--muted); margin-bottom:0.5rem;">MAX DRAWDOWN</div>
              <div style="font-size:1.65rem;font-weight:800;margin:0.2rem 0;color:var(--text);letter-spacing:-0.5px">
                {_fmt_pct(-m["max_drawdown"])}
              </div>
              <div style="font-size:0.85rem;color:var(--muted);font-weight:500;margin-top:0.3rem;">
                <span style="background:var(--bg-secondary);padding:2px 6px;border-radius:4px;">📅 {m.get("max_drawdown_date", "")}</span>
              </div>
            </div>""", unsafe_allow_html=True)
            
        with mc2:
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label" style="text-transform:uppercase; font-size:0.75rem; letter-spacing:1px; color:var(--muted); margin-bottom:0.5rem;">SHARPE RATIO</div>
              <div style="font-size:1.65rem;font-weight:800;margin:0.2rem 0;color:var(--text);letter-spacing:-0.5px">
                {m['sharpe_ratio']:.2f}
              </div>
              <div style="font-size:0.85rem;color:var(--muted);font-weight:500;margin-top:0.3rem;">
                <span style="background:var(--bg-secondary);padding:2px 6px;border-radius:4px;">⚖️ B&H: {bm['sharpe_ratio']:.2f}</span>
              </div>
            </div>""", unsafe_allow_html=True)
            
        with mc3:
            buys  = m.get("buy_count", 0)
            sells = m.get("sell_count", 0)
            wr_pct = m["win_rate"] * 100
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label" style="text-transform:uppercase; font-size:0.75rem; letter-spacing:1px; color:var(--muted); margin-bottom:0.5rem;">TOTAL TRADES & WIN RATE</div>
              <div style="font-size:1.65rem;font-weight:800;margin:0.2rem 0;color:var(--text);letter-spacing:-0.5px">
                {m['trade_count']} <span style="font-size:1rem;color:var(--muted);font-weight:600;">({wr_pct:.1f}%)</span>
              </div>
              <div style="font-size:0.85rem;color:var(--muted);font-weight:500;margin-top:0.3rem;">
                <span style="background:var(--bg-secondary);padding:2px 6px;border-radius:4px;">🟢 {buys} Buys &nbsp;🔴 {sells} Sells</span>
              </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("")

        # ── Row 3: Portfolio composition + vs HODL ────────────────────────────
        pc1, pc2 = st.columns(2)
        with pc1:
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label" style="text-transform:uppercase; font-size:0.75rem; letter-spacing:1px; color:var(--muted); margin-bottom:0.5rem;">REMAINING ASSETS (CASH & BTC)</div>
              <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.5rem;">
                <div>
                  <div style="font-size:1.35rem;font-weight:800;color:var(--text);letter-spacing:-0.5px">{format_currency(m['final_cash'])}</div>
                  <div style="font-size:0.85rem;color:var(--muted);font-weight:600">💵 Cash</div>
                </div>
                <div style="width:1px; height:40px; background:var(--border);"></div>
                <div style="text-align:right;">
                  <div style="font-size:1.35rem;font-weight:800;color:var(--text);letter-spacing:-0.5px">{format_number(m['final_btc'])}</div>
                  <div style="font-size:0.85rem;color:var(--muted);font-weight:600">₿ BTC</div>
                </div>
              </div>
            </div>""", unsafe_allow_html=True)
            
        with pc2:
            st.markdown(f"""
            <div class="metric-card" style="border-left:4px solid {diff_color}">
              <div class="metric-label" style="text-transform:uppercase; font-size:0.75rem; letter-spacing:1px; color:var(--muted); margin-bottom:0.5rem;">STRATEGY VS HODL</div>
              <div style="font-size:1.65rem;font-weight:800;margin:0.2rem 0;color:{diff_color};letter-spacing:-0.5px">
                {diff_display}
              </div>
              <div style="font-size:0.85rem;color:{diff_color};font-weight:600;margin-top:0.3rem;">
                {diff_label}
              </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("")

        # ── Charts ────────────────────────────────────────────────────────────
        chart_equity = build_equity_chart(result)
        st.plotly_chart(chart_equity, width='stretch')

        chart_cbbi = build_cbbi_chart(
            df_slice,
            threshold_buy=params["threshold_buy"],
            threshold_sell=params["threshold_sell"],
            trade_log=result.trade_log,
        )
        st.plotly_chart(chart_cbbi, width='stretch')

        # ── Auto-generated summary text ───────────────────────────────────────
        period_yrs = (pd.Timestamp(end_date) - pd.Timestamp(start_date)).days / 365
        buys  = m.get("buy_count", 0)
        sells = m.get("sell_count", 0)
        st.info(
            f"**Summary:** With a Buy Threshold of **{threshold_buy}** and Sell Threshold of **{threshold_sell}**, "
            f"the strategy generated a **{format_percentage(m['total_return']*100)} total return** "
            f"over {period_yrs:.1f} years, compared to **{format_percentage(bm['total_return']*100)}** with HODL. "
            f"Total **{m['trade_count']} trades** (🟢 {buys} buys · 🔴 {sells} sells) "
            f"with a win rate of **{m['win_rate']*100:.1f}%**. "
            f"Final portfolio: **{format_currency(final_pv)}** vs HODL **{format_currency(final_bh)}** — {diff_label}."
        )

# ═══════════════════════════════════════════════════════════════════════════════
# FULL-WIDTH TRANSACTION HISTORY
# ═══════════════════════════════════════════════════════════════════════════════
if "sim_result" in st.session_state:
    st.markdown("---")
    st.markdown("### 📋 Transaction History")
    
    result = st.session_state["sim_result"]
    params = st.session_state["sim_params"]
    threshold_buy = params["threshold_buy"]
    threshold_sell = params["threshold_sell"]
    
    tlog = result.trade_log
    if tlog.empty:
        st.caption("No transactions were executed with these parameters.")
    else:
        n_trades = len(tlog)
        
        # Determine the start and end dates used in the simulation
        df_slice = st.session_state["sim_df_slice"]
        sim_start_date = df_slice.index.min().strftime('%d %b %Y')
        sim_end_date = df_slice.index.max().strftime('%d %b %Y')
        period_label = f"{sim_start_date} – {sim_end_date}"

        st.markdown(
            f"<div style='font-size:0.85rem; opacity:0.65; margin-bottom:0.6rem;'>"
            f"<b>{n_trades} transactions</b> found during the simulation period &nbsp;·&nbsp; {period_label}"
            f"</div>",
            unsafe_allow_html=True,
        )

        n_show = st.slider(
            "Show last N transactions",
            10, min(500, n_trades), min(100, n_trades), 10,
            key="tlog_slider",
        )
        tlog_show = tlog.tail(n_show).reset_index(drop=True).copy()
        tlog_show.insert(0, "#", range(n_trades - len(tlog_show) + 1, n_trades + 1))
        tlog_show["Date"] = pd.to_datetime(tlog_show["Date"]).dt.strftime("%Y-%m-%d")

        def _highlight_action(row):
            color = (
                "background-color: rgba(34,197,94,0.12)"  if row["Action"] == "BUY"
                else "background-color: rgba(239,68,68,0.12)" if row["Action"] == "SELL"
                else ""
            )
            return [color] * len(row)

        styled = (
            tlog_show.style
            .apply(_highlight_action, axis=1)
            .format({
                "BTC Price":      format_currency,
                "Amount (USD)":   format_currency,
                "BTC Amount":     "{:,.6f}",
                "CBBI Index":     "{:.1f}%",
                "Cash After":     format_currency,
                "BTC Held After": "{:,.6f}",
                "Equity After":   format_currency,
            })
        )

        st.dataframe(
            styled,
            use_container_width=True,
            height=400,
            column_config={
                "#":             st.column_config.NumberColumn("#",            width="small"),
                "Date":          st.column_config.TextColumn("Date",           width="small"),
                "Action":        st.column_config.TextColumn("Action",         width="small"),
                "BTC Price":     st.column_config.TextColumn("BTC Price"),
                "Amount (USD)":  st.column_config.TextColumn("Amount (USD)"),
                "BTC Amount":    st.column_config.TextColumn("Amount (BTC)"),
                "CBBI Index":    st.column_config.TextColumn("Index",          width="small"),
                "Cash After":    st.column_config.TextColumn("Cash After"),
                "BTC Held After":st.column_config.TextColumn("BTC After"),
                "Equity After":  st.column_config.TextColumn("Equity"),
            },
        )

        csv_data = tlog.to_csv(index=False)
        st.download_button(
            "⬇ Export Transaction History (CSV)",
            data=csv_data,
            file_name=f"sim_trade_log_{scenario_name.replace(' ', '_').lower()}.csv",
            mime="text/csv",
        )
