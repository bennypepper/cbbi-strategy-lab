"""
core/charts.py
==============
All Plotly chart builder functions for CBBI Strategy Lab.
Each function returns a go.Figure ready for st.plotly_chart().
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from core.engine import SimulationResult

# ── Color palette ─────────────────────────────────────────────────────────────
COLORS = {
    "strategy":   "#00907a",   # deep teal
    "benchmark":  "#d97706",   # warm amber (replaces bitcoin orange)
    "btc_price":  "#94a3b8",   # slate blue-grey
    "buy_marker": "#16a34a",   # dark green
    "sell_marker":"#dc2626",   # dark red
    "buy_line":   "#16a34a",
    "sell_line":  "#dc2626",
    "hold_zone":  "rgba(84,119,146,0.06)",
    "signal_line":"#547792",   # steel blue
    "bg":         "#ffffff",
    "grid":       "rgba(33,52,72,0.07)",
    "text":       "#213448",
}

_LAYOUT_BASE = dict(
    paper_bgcolor="#fff8f1",
    plot_bgcolor="#ffffff",
    font=dict(color=COLORS["text"], family="Space Grotesk, Work Sans, sans-serif", size=12),
    xaxis=dict(
        gridcolor=COLORS["grid"],
        zeroline=False,
        linecolor="#d4cdc4",
        showspikes=True,
        spikecolor="rgba(33,52,72,0.15)",
        spikethickness=1,
    ),
    yaxis=dict(gridcolor=COLORS["grid"], zeroline=False, linecolor="#d4cdc4"),
    legend=dict(
        bgcolor="rgba(255,248,241,0.95)",
        bordercolor="#c9c2b8",
        borderwidth=1,
    ),
    hovermode="x unified",
    margin=dict(l=60, r=20, t=50, b=40),
)


def _apply_base_layout(fig: go.Figure, title: str = "") -> go.Figure:
    layout = dict(_LAYOUT_BASE)
    layout["title"] = dict(
        text=title,
        font=dict(size=15, color=COLORS["text"]),
        x=0.02,
    )
    fig.update_layout(**layout)
    return fig


# ── Chart 1: Equity Curve ─────────────────────────────────────────────────────

def build_equity_chart(result: SimulationResult) -> go.Figure:
    """
    Dual-axis equity chart:
    - Left Y:  Strategy portfolio value + B&H benchmark
    - Right Y: BTC close price (secondary axis)
    - Markers: BUY (triangle-up green) and SELL (triangle-down red)
    """
    ph   = result.portfolio_history
    tlog = result.trade_log

    fig = go.Figure()

    # Strategy portfolio
    fig.add_trace(go.Scatter(
        x=ph.index,
        y=ph["portfolio_value"],
        name="Strategy",
        line=dict(color=COLORS["strategy"], width=2),
        fill="tozeroy",
        fillcolor="rgba(0,144,122,0.07)",
        hovertemplate="<b>Strategy</b>: $%{y:,.0f}<extra></extra>",
    ))

    # Buy & Hold benchmark
    fig.add_trace(go.Scatter(
        x=ph.index,
        y=ph["buy_and_hold_value"],
        name="Buy & Hold",
        line=dict(color=COLORS["benchmark"], width=1.5, dash="dot"),
        hovertemplate="<b>B&H</b>: $%{y:,.0f}<extra></extra>",
    ))

    # BTC close price (secondary axis)
    fig.add_trace(go.Scatter(
        x=ph.index,
        y=ph["btc_close"],
        name="BTC Price",
        line=dict(color=COLORS["btc_price"], width=1),
        yaxis="y2",
        hovertemplate="<b>BTC</b>: $%{y:,.0f}<extra></extra>",
        opacity=0.5,
    ))

    # Trade markers
    if not tlog.empty:
        buys  = tlog[tlog["Action"] == "BUY"]
        sells = tlog[tlog["Action"] == "SELL"]

        if not buys.empty:
            # Map buy execution dates to portfolio values
            buy_portfolio_vals = ph["portfolio_value"].reindex(buys["Date"]).ffill()
            fig.add_trace(go.Scatter(
                x=buys["Date"],
                y=buy_portfolio_vals.values,
                name="BUY",
                mode="markers",
                marker=dict(
                    symbol="triangle-up",
                    color=COLORS["buy_marker"],
                    size=7,
                    line=dict(width=0.5, color="white"),
                ),
                hovertemplate=(
                    "<b>BUY</b><br>"
                    "Amount: $%{customdata[0]:,.0f}<br>"
                    "BTC Price: $%{customdata[1]:,.0f}"
                    "<extra></extra>"
                ),
                customdata=buys[["Amount (USD)", "Exec Price (BTC Open)"]].values,
            ))

        if not sells.empty:
            sell_portfolio_vals = ph["portfolio_value"].reindex(sells["Date"]).ffill()
            fig.add_trace(go.Scatter(
                x=sells["Date"],
                y=sell_portfolio_vals.values,
                name="SELL",
                mode="markers",
                marker=dict(
                    symbol="triangle-down",
                    color=COLORS["sell_marker"],
                    size=7,
                    line=dict(width=0.5, color="white"),
                ),
                hovertemplate=(
                    "<b>SELL</b><br>"
                    "Amount: $%{customdata[0]:,.0f}<br>"
                    "BTC Price: $%{customdata[1]:,.0f}"
                    "<extra></extra>"
                ),
                customdata=sells[["Amount (USD)", "Exec Price (BTC Open)"]].values,
            ))

    fig.update_layout(
        yaxis2=dict(
            title="BTC Price (USD)",
            overlaying="y",
            side="right",
            gridcolor="rgba(0,0,0,0)",
            tickformat="$,.0f",
            showgrid=False,
        ),
        yaxis=dict(tickformat="$,.0f"),
    )

    _apply_base_layout(fig, "Portfolio Value vs Buy & Hold")
    fig.update_layout(height=420)
    return fig


# ── Chart 2: CBBI Trolololo Signal ───────────────────────────────────────────

def build_cbbi_chart(
    df: pd.DataFrame,
    threshold_buy: int,
    threshold_sell: int,
    signal_column: str = "trolololo",
) -> go.Figure:
    """
    CBBI signal chart with threshold lines and hold-zone shading.
    """
    fig = go.Figure()

    # Signal line
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df[signal_column],
        name="Trolololo",
        line=dict(color=COLORS["signal_line"], width=1.5),
        hovertemplate="<b>Trolololo</b>: %{y:.1f}<extra></extra>",
        fill="tozeroy",
        fillcolor="rgba(84,119,146,0.06)",
    ))

    # Hold zone shading
    fig.add_hrect(
        y0=threshold_buy, y1=threshold_sell,
        fillcolor=COLORS["hold_zone"],
        line_width=0,
        annotation_text="HOLD ZONE",
        annotation_position="right",
        annotation_font=dict(color="rgba(33,52,72,0.35)", size=10),
    )

    # Buy threshold line
    fig.add_hline(
        y=threshold_buy,
        line=dict(color=COLORS["buy_line"], width=1.5, dash="dash"),
        annotation_text=f"Buy ≤ {threshold_buy}",
        annotation_position="left",
        annotation_font=dict(color=COLORS["buy_line"], size=10),
    )

    # Sell threshold line
    fig.add_hline(
        y=threshold_sell,
        line=dict(color=COLORS["sell_line"], width=1.5, dash="dash"),
        annotation_text=f"Sell ≥ {threshold_sell}",
        annotation_position="left",
        annotation_font=dict(color=COLORS["sell_line"], size=10),
    )

    _apply_base_layout(fig, "Trolololo Signal with Thresholds")
    fig.update_layout(
        height=280,
        yaxis=dict(range=[0, 105], title="Trolololo (0–100)"),
    )
    return fig


# ── Chart 3: IS vs OOS Equity (Research Results) ─────────────────────────────

def build_is_oos_equity_chart(
    df: pd.DataFrame,
    params: dict,
    title: str = "In-Sample vs Out-of-Sample Equity",
) -> go.Figure:
    """
    Equity curve for research results page with IS/OOS shading.
    Reruns backtest from precomputed params on full dataset.
    """
    from core.engine import run_backtest_full

    result = run_backtest_full(
        df,
        threshold_buy=int(params["threshold_buy"]),
        threshold_sell=int(params["threshold_sell"]),
        alloc_buy_pct=float(params["allocation_buy_pct"]),
        alloc_sell_pct=float(params["allocation_sell_pct"]),
        initial_cash=100_000.0,
        fee_rate=0.001,
    )

    ph = result.portfolio_history
    # IS/OOS split date
    split_date = "2021-01-01"

    fig = go.Figure()

    # IS phase shading
    is_data = ph[ph.index < split_date]
    oos_data = ph[ph.index >= split_date]

    fig.add_trace(go.Scatter(
        x=is_data.index,
        y=is_data["portfolio_value"],
        name="Strategy (IS 2012–2020)",
        line=dict(color=COLORS["strategy"], width=2),
        fill="tozeroy",
        fillcolor="rgba(0,144,122,0.08)",
    ))
    fig.add_trace(go.Scatter(
        x=oos_data.index,
        y=oos_data["portfolio_value"],
        name="Strategy (OOS 2021–2026)",
        line=dict(color="#0369a1", width=2),
        fill="tozeroy",
        fillcolor="rgba(3,105,161,0.06)",
    ))
    fig.add_trace(go.Scatter(
        x=ph.index,
        y=ph["buy_and_hold_value"],
        name="Buy & Hold",
        line=dict(color=COLORS["benchmark"], width=1, dash="dot"),
    ))

    # Vertical line at IS/OOS split
    # Plotly needs a numeric ms-epoch value when the x-axis is datetime
    split_ms = int(pd.Timestamp(split_date).timestamp() * 1000)
    fig.add_vline(
        x=split_ms,
        line=dict(color="rgba(33,52,72,0.25)", width=1, dash="dash"),
        annotation_text="IS | OOS split",
        annotation_position="top",
        annotation_font=dict(color="rgba(33,52,72,0.5)", size=10),
    )

    _apply_base_layout(fig, title)
    fig.update_layout(height=350, yaxis=dict(tickformat="$,.0f"))
    return fig


# ── Chart 4: Degradation Bar Chart ───────────────────────────────────────────

def build_degradation_chart(degradation: dict) -> go.Figure:
    """
    Bar chart showing IS→OOS degradation per objective.
    degradation: scenario_1.degradation from optimal_params_summary.json
    """
    objectives = list(degradation.keys())
    metric_labels = {
        "return_degradation_pct": "Return Degradation %",
        "sharpe_degradation_pct": "Sharpe Degradation %",
        "drawdown_degradation_pct": "Drawdown Change %",
    }

    fig = go.Figure()

    for metric_key, metric_label in metric_labels.items():
        values = [degradation[obj].get(metric_key, 0) for obj in objectives]
        colors_bar = [
            COLORS["buy_marker"] if abs(v) < 20 else
            "#FBBF24" if abs(v) < 40 else
            COLORS["sell_marker"]
            for v in values
        ]
        fig.add_trace(go.Bar(
            name=metric_label,
            x=[o.replace("_", " ").title() for o in objectives],
            y=values,
            marker_color=colors_bar,
            hovertemplate=f"<b>{metric_label}</b>: %{{y:.1f}}%<extra></extra>",
        ))

    _apply_base_layout(fig, "IS → OOS Performance Degradation")
    fig.update_layout(
        barmode="group",
        height=320,
        yaxis=dict(ticksuffix="%", title="Degradation (%)"),
    )
    return fig


# ── Chart 5: Sensitivity Heatmap ─────────────────────────────────────────────

def build_sensitivity_heatmap(
    pivot_df: pd.DataFrame,
    title: str = "Return Sensitivity: Buy vs Sell Threshold",
    metric_label: str = "Total Return",
) -> go.Figure:
    """
    px.imshow heatmap from pivot_df built by data_loader.build_heatmap_matrix().
    Rows = sell threshold, Columns = buy threshold.
    """
    # Clip extreme values for better color scale visibility
    display_df = pivot_df.copy()
    p99 = float(np.nanpercentile(display_df.values, 99))
    display_df = display_df.clip(upper=p99)

    # Format x/y as int labels
    x_labels = [int(c) for c in display_df.columns]
    y_labels = [int(r) for r in display_df.index]

    fig = px.imshow(
        display_df.values,
        x=x_labels,
        y=y_labels,
        color_continuous_scale="RdYlGn",
        aspect="auto",
        labels=dict(x="Buy Threshold", y="Sell Threshold", color=metric_label),
    )
    fig.update_traces(
        hovertemplate=(
            "Buy Threshold: %{x}<br>"
            "Sell Threshold: %{y}<br>"
            f"{metric_label}: %{{z:,.1f}}<extra></extra>"
        )
    )
    _apply_base_layout(fig, title)
    fig.update_layout(
        height=420,
        coloraxis_colorbar=dict(
            title=dict(text=metric_label, font=dict(size=11)),
            tickfont=dict(size=10),
        ),
    )
    return fig


# ── Chart 6: Comparison Bar (Scenario 1 OOS vs Scenario 2 vs B&H) ────────────

def build_comparison_chart(results: dict) -> go.Figure:
    """
    Side-by-side bar chart: S1 OOS vs S2 Full vs Buy & Hold.
    Metrics: Total Return | Max Drawdown | Sharpe Ratio
    """
    s1_oos = results["scenario_1"]["out_of_sample"]["max_return"]
    s2_full = results["scenario_2"]["full_dataset"]["max_return"]
    bh_oos  = results["buy_and_hold_benchmark"]["out_of_sample"]
    bh_full = results["buy_and_hold_benchmark"]["full_dataset"]

    metrics = ["total_return", "max_drawdown", "sharpe_ratio"]
    labels  = ["Total Return", "Max Drawdown", "Sharpe Ratio"]

    groups = {
        "S1 OOS (Validated)": [s1_oos.get(m, 0) for m in metrics],
        "S2 Full (Exploration)": [s2_full.get(m, 0) for m in metrics],
        "Buy & Hold (OOS)": [bh_oos.get(m, 0) for m in metrics],
    }
    group_colors = [COLORS["strategy"], "#A78BFA", COLORS["benchmark"]]

    fig = go.Figure()
    for (grp, vals), color in zip(groups.items(), group_colors):
        fig.add_trace(go.Bar(
            name=grp,
            x=labels,
            y=vals,
            marker_color=color,
            hovertemplate=f"<b>{grp}</b>: %{{y:.3f}}<extra></extra>",
        ))

    _apply_base_layout(fig, "Performance Comparison")
    fig.update_layout(barmode="group", height=320)
    return fig
