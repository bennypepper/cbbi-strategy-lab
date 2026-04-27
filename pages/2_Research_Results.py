"""
pages/2_Research_Results.py
============================
Phase 3 optimization results — read-only display.
"""

import json
import streamlit as st
import pandas as pd

from core.data_loader import (
    load_master_dataset,
    load_research_results,
    load_scenario1_log,
    load_scenario2_log,
    build_heatmap_matrix,
)
from core.charts import (
    build_is_oos_equity_chart,
    build_degradation_chart,
    build_sensitivity_heatmap,
    build_comparison_chart,
)
from core.styles import inject_css
from core.utils import format_percentage

st.set_page_config(page_title="Research Results · CBBI Strategy Lab", page_icon="🔬", layout="wide")
inject_css()

# ── Load data ─────────────────────────────────────────────────────────────────
results = load_research_results()
df_full = load_master_dataset()

s1 = results["scenario_1"]
s2 = results["scenario_2"]
bh = results["buy_and_hold_benchmark"]

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("## 🔬 Research Results")
st.markdown(
    "<div style='opacity:0.5; font-size:0.88rem; margin-bottom:1rem;'>"
    "Phase 3 optimization outcomes · 1,293,750 trials per scenario · "
    f"Generated: {results['metadata']['generated_at']}"
    "</div>",
    unsafe_allow_html=True,
)

# ── Scenario explanation banner ───────────────────────────────────────────────
with st.expander("📖 Understanding the Two Scenarios", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
**Scenario 1 — Academic Validation**
- Optimization runs on **2012–2020** data only (In-Sample)
- Optimal parameters are then tested on **2021–2026** data (Out-of-Sample)
- No lookahead bias — OOS data was never seen during optimization
- Purpose: prove strategy robustness and generalizability
- Signal: Trolololo (Logarithmic Regression)
        """)
    with c2:
        st.markdown("""
**Scenario 2 — Maximum Exploration**
- Optimization runs on the **full 2012–2026** dataset
- No train/test split — all data used for optimization
- ⚠ Contains lookahead bias **by design**
- Purpose: map the absolute performance ceiling of the indicator
- Useful as a reference point, not a tradeable strategy
        """)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SCENARIO 1 — ACADEMIC VALIDATION
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### Scenario 1 — Academic Validation Approach")

tab_ret, tab_dd, tab_sharpe = st.tabs(["Max Return", "Min Drawdown", "Max Sharpe"])

OBJECTIVE_KEYS = {
    "Max Return":   "max_return",
    "Min Drawdown": "min_drawdown",
    "Max Sharpe":   "max_sharpe",
}

DEGRADATION_THRESHOLDS = {"🟢 Robust": 20, "🟡 Moderate": 40}


def _degradation_badge(pct: float) -> str:
    ap = abs(pct)
    if ap < 20:
        return "🟢 Robust"
    elif ap < 40:
        return "🟡 Moderate"
    else:
        return "🔴 Overfit"


def _render_scenario1_tab(obj_key: str):
    is_data  = s1["in_sample"][obj_key]
    oos_data = s1["out_of_sample"][obj_key]
    deg_data = s1["degradation"][obj_key]

    # Parameter + metrics table
    st.markdown("**Optimal Parameters (from In-Sample optimization)**")
    params_table = pd.DataFrame({
        "Parameter": ["Buy Threshold", "Sell Threshold", "Buy Allocation", "Sell Allocation"],
        "Value": [
            f"{int(is_data['threshold_buy'])}",
            f"{int(is_data['threshold_sell'])}",
            f"{is_data['allocation_buy_pct']*100:.0f}%",
            f"{is_data['allocation_sell_pct']*100:.0f}%",
        ],
    })
    st.dataframe(params_table, width='content', hide_index=True, height=180)

    st.markdown("")
    mc1, mc2, mc3 = st.columns(3)

    with mc1:
        st.markdown("**In-Sample (2012–2020)**")
        st.metric("Total Return",  format_percentage(is_data['total_return'] * 100))
        st.metric("Max Drawdown",  f"{is_data['max_drawdown'] * 100:.1f}%")
        st.metric("Sharpe Ratio",  f"{is_data['sharpe_ratio']:.3f}")
        st.metric("Win Rate",      f"{is_data['win_rate'] * 100:.1f}%")
        st.metric("Trade Count",   f"{int(is_data['trade_count']):,}")

    with mc2:
        st.markdown("**Out-of-Sample (2021–2026)**")
        st.metric("Total Return",  format_percentage(oos_data['total_return'] * 100))
        st.metric("Max Drawdown",  f"{oos_data['max_drawdown'] * 100:.1f}%")
        st.metric("Sharpe Ratio",  f"{oos_data['sharpe_ratio']:.3f}")
        st.metric("Win Rate",      f"{oos_data['win_rate'] * 100:.1f}%")
        st.metric("Trade Count",   f"{int(oos_data['trade_count']):,}")
        if oos_data["trade_count"] == 0:
            st.markdown(
                "<div style='background:rgba(10,124,110,0.08); border-left:4px solid #0a7c6e; padding:0.85rem 1rem; margin-top:0.5rem; font-size:0.84rem; line-height:1.6;'>"
                "<b>📊 No OOS trades triggered — expected with independent Trolololo</b><br>"
                f"The optimal buy threshold is <b>{int(is_data['threshold_buy'])}</b> (Trolololo ≤ {int(is_data['threshold_buy'])}%). "
                "With the independently computed Trolololo (log regression on BTC-USD prices, re-calibrated 2026-04-27), "
                "the signal never fell below this threshold during the OOS period (2021–2026). "
                "No buy signals means no sell signals, so all metrics show 0. "
                "This is a research finding — the Min Drawdown strategy's extreme selectivity prevents any activity "
                "in the bull/sideways market conditions of 2021–2026."
                "</div>",
                unsafe_allow_html=True,
            )
        elif oos_data["trade_count"] < 10:
            st.markdown("<div class='warn-badge'>⚠ Low trade count</div>", unsafe_allow_html=True)

    with mc3:
        st.markdown("**IS → OOS Degradation**")
        ret_deg = deg_data["return_degradation_pct"]
        shp_deg = deg_data["sharpe_degradation_pct"]
        dd_deg  = deg_data["drawdown_degradation_pct"]

        st.metric("Return Degradation",  f"{ret_deg:.1f}%")
        st.metric("Sharpe Degradation",  f"{shp_deg:.1f}%")
        st.metric("Drawdown Change",      f"{dd_deg:.1f}%")
        st.markdown("")
        badge = _degradation_badge(ret_deg)
        st.markdown(f"**Overall Assessment:** {badge}")

    # Buy & Hold comparison
    st.markdown("")
    st.caption(
        f"📊 Buy & Hold benchmark — IS: **{format_percentage(bh['in_sample']['total_return']*100)}** | "
        f"OOS: **{format_percentage(bh['out_of_sample']['total_return']*100)}** | "
        f"Full: **{format_percentage(bh['full_dataset']['total_return']*100)}**"
    )

    # IS vs OOS equity chart
    st.markdown("**Equity Curve: In-Sample vs Out-of-Sample**")
    fig = build_is_oos_equity_chart(df_full, is_data, title=f"Strategy Equity ({obj_key.replace('_', ' ').title()})")
    st.plotly_chart(fig, width='stretch')


with tab_ret:
    _render_scenario1_tab("max_return")

with tab_dd:
    _render_scenario1_tab("min_drawdown")

with tab_sharpe:
    _render_scenario1_tab("max_sharpe")

# Degradation bar chart
st.markdown("**IS → OOS Degradation by Objective**")
fig_deg = build_degradation_chart(s1["degradation"])
st.plotly_chart(fig_deg, width='stretch')

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SCENARIO 2 — MAXIMUM EXPLORATION
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### Scenario 2 — Maximum Exploration Approach")

# Mandatory disclosure — must appear before numbers
st.markdown("""
<div class="disclosure-box">
  ⚠️ <strong>IMPORTANT DISCLOSURE</strong><br><br>
  The following results were obtained by optimizing across the <strong>entire historical dataset (2012–2026)</strong>.
  This process uses what is known as <em>lookahead bias</em> — the optimizer had access to data that would not have
  been available at the time of trading.<br><br>
  These configurations <strong>cannot be used as predictive trading signals</strong>. The sole purpose of Scenario 2
  is to map the <strong>absolute historical performance ceiling</strong> of the Trolololo indicator —
  i.e., the best a strategy <em>could have done</em> with perfect hindsight. This serves as an academic reference point,
  not a tradeable result.
</div>
""", unsafe_allow_html=True)

st.markdown("")

s2_tab_ret, s2_tab_dd, s2_tab_sharpe = st.tabs(["Max Return", "Min Drawdown", "Max Sharpe"])


def _render_scenario2_tab(obj_key: str):
    full_data = s2["full_dataset"][obj_key]

    params_table = pd.DataFrame({
        "Parameter": ["Buy Threshold", "Sell Threshold", "Buy Allocation", "Sell Allocation"],
        "Value": [
            f"{int(full_data['threshold_buy'])}",
            f"{int(full_data['threshold_sell'])}",
            f"{full_data['allocation_buy_pct']*100:.0f}%",
            f"{full_data['allocation_sell_pct']*100:.0f}%",
        ],
    })
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown("**Optimal Parameters (Full Dataset)**")
        st.dataframe(params_table, width='content', hide_index=True, height=180)
        st.markdown("")
        st.metric("Total Return",  format_percentage(full_data['total_return'] * 100))
        st.metric("Max Drawdown",  f"{full_data['max_drawdown'] * 100:.1f}%")
        st.metric("Sharpe Ratio",  f"{full_data['sharpe_ratio']:.3f}")
        st.metric("Win Rate",      f"{full_data['win_rate'] * 100:.1f}%")
        st.metric("Trade Count",   f"{int(full_data['trade_count']):,}")
    with c2:
        st.markdown("**Equity Curve (Full Dataset 2012–2026)**")
        fig = build_is_oos_equity_chart(
            df_full, full_data,
            title=f"Scenario 2 Equity ({obj_key.replace('_', ' ').title()})"
        )
        st.plotly_chart(fig, width='stretch')


with s2_tab_ret:
    _render_scenario2_tab("max_return")

with s2_tab_dd:
    _render_scenario2_tab("min_drawdown")

with s2_tab_sharpe:
    _render_scenario2_tab("max_sharpe")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# COMPARISON PANEL
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### Overall Comparison")

# Side-by-side comparison table
s1_oos = s1["out_of_sample"]["max_return"]
s2_full = s2["full_dataset"]["max_return"]
bh_oos  = bh["out_of_sample"]

comp_df = pd.DataFrame({
    "Metric": ["Total Return", "Max Drawdown", "Sharpe Ratio"],
    "Scenario 1 (OOS, Validated)": [
        format_percentage(s1_oos['total_return']*100),
        f"{s1_oos['max_drawdown']*100:.1f}%",
        f"{s1_oos['sharpe_ratio']:.3f}",
    ],
    "Scenario 2 (Full, Exploration)": [
        format_percentage(s2_full['total_return']*100),
        f"{s2_full['max_drawdown']*100:.1f}%",
        f"{s2_full['sharpe_ratio']:.3f}",
    ],
    "Buy & Hold (OOS period)": [
        format_percentage(bh_oos['total_return']*100),
        f"{bh_oos['max_drawdown']*100:.1f}%",
        f"{bh_oos['sharpe_ratio']:.3f}",
    ],
}).set_index("Metric")

st.dataframe(comp_df, width='stretch')
fig_comp = build_comparison_chart(results)
st.plotly_chart(fig_comp, width='stretch')

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SENSITIVITY HEATMAPS (lazy-loaded)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### Parameter Sensitivity Heatmaps")
st.markdown(
    "<div style='opacity:0.5; font-size:0.85rem; margin-bottom:1rem;'>"
    "Each cell shows the maximum total return achievable at that "
    "(Buy Threshold, Sell Threshold) combination, across all allocation percentages. "
    "Large files — may take a few seconds to load."
    "</div>",
    unsafe_allow_html=True,
)

hc1, hc2 = st.columns(2)

with hc1:
    st.markdown("**Scenario 1 — In-Sample Sensitivity**")
    if st.button("Load S1 Heatmap", key="load_s1_hm"):
        with st.spinner("Building Scenario 1 heatmap..."):
            s1_log = load_scenario1_log()
            pivot  = build_heatmap_matrix(s1_log, metric="total_return")
            fig_hm = build_sensitivity_heatmap(
                pivot,
                title="S1 In-Sample: Total Return by Threshold Pair",
            )
        st.plotly_chart(fig_hm, width='stretch')

with hc2:
    st.markdown("**Scenario 2 — Full Dataset Sensitivity**")
    if st.button("Load S2 Heatmap", key="load_s2_hm"):
        with st.spinner("Building Scenario 2 heatmap..."):
            s2_log = load_scenario2_log()
            pivot  = build_heatmap_matrix(s2_log, metric="total_return")
            fig_hm = build_sensitivity_heatmap(
                pivot,
                title="S2 Full Dataset: Total Return by Threshold Pair",
            )
        st.plotly_chart(fig_hm, width='stretch')

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# EXPORT PANEL
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### Export Data")

ec1, ec2, ec3 = st.columns(3)

with ec1:
    json_bytes = json.dumps(results, indent=2).encode("utf-8")
    st.download_button(
        "⬇ optimal_params_summary.json",
        data=json_bytes,
        file_name="optimal_params_summary.json",
        mime="application/json",
    )

with ec2:
    if st.button("Prepare S1 Top-100 CSV"):
        with st.spinner("Loading..."):
            s1_log = load_scenario1_log()
            top100 = s1_log.nlargest(100, "total_return")
        st.download_button(
            "⬇ scenario1_top100.csv",
            data=top100.to_csv(index=False),
            file_name="scenario1_top100_max_return.csv",
            mime="text/csv",
        )

with ec3:
    if st.button("Prepare S2 Top-100 CSV"):
        with st.spinner("Loading..."):
            s2_log = load_scenario2_log()
            top100 = s2_log.nlargest(100, "total_return")
        st.download_button(
            "⬇ scenario2_top100.csv",
            data=top100.to_csv(index=False),
            file_name="scenario2_top100_max_return.csv",
            mime="text/csv",
        )
