"""
core/charts.py
==============
Chart builders for CBBI Strategy Lab — light theme edition.

Key design decisions
--------------------
1. ALL text / axis / grid uses colors derived from the Streamlit light theme
   (bg=#fff8f1, text=#213448) — never near-white which would be invisible.

2. Equity curves are WEEKLY resampled for display.
   Daily BTC data has 5-15 % swings every single day. Plotting 1,500+ daily
   points on a linear or even log scale produces the "barcode" spike pattern.
   Resampling to weekly (~200 points) keeps the meaningful trend visible while
   removing noise that makes the chart unreadable. Metrics (return, drawdown,
   Sharpe) are still computed on full daily precision — only the visual is weekly.

3. Equity fill uses tonexty (strategy fills up to B&H, or down to a baseline)
   instead of tozeroy. tozeroy on a log-scale or any scale with large value
   swings creates visual stalagmites at every dip. tonexty fills the gap
   between two related lines, which is both prettier and more informative.

4. Signal chart: daily data kept (Trolololo index moves are meaningful per-day)
   but the line uses a moderate smoothing factor.

5. All chart functions return go.Figure so they are rendered with
   st.plotly_chart(..., use_container_width=True).
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

from core.engine import SimulationResult


# ── Light-theme color palette ─────────────────────────────────────────────────
# Background: #fff8f1 (cream)  Text: #213448 (dark navy)

COLORS = {
    "strategy":      "#0a7c6e",      # teal — primary strategy line
    "benchmark":     "#d97706",      # amber — B&H / HODL
    "buy_marker":    "#16a34a",      # green
    "sell_marker":   "#dc2626",      # red
    "buy_zone_fill": "rgba(22,163,74,0.09)",
    "sell_zone_fill":"rgba(220,38,38,0.08)",
    "signal_line":   "#0369a1",      # blue — Trolololo index
    "text":          "#213448",      # dark navy — matches Streamlit theme
    "text_muted":    "rgba(33,52,72,0.45)",
    "grid":          "rgba(33,52,72,0.08)",
    "axis_line":     "rgba(33,52,72,0.20)",
}

_FONT  = "Space Grotesk, Inter, Work Sans, sans-serif"
_TEXT  = COLORS["text"]
_MUTED = COLORS["text_muted"]
_GRID  = COLORS["grid"]

# Transparent bg so Streamlit's cream shows through
_PAPER = "rgba(0,0,0,0)"
_PLOT  = "rgba(0,0,0,0)"


# ── Compact log-scale dollar tick generator ───────────────────────────────────

def _log_dollar_ticks(min_v: float, max_v: float) -> tuple[list[float], list[str]]:
    """1-2-5 multiples per decade, compact labels: $500 $1K $2K $5K $10K …"""
    if min_v <= 0:
        min_v = 1.0

    def _fmt(v: float) -> str:
        if v >= 1e12: return f"${v/1e12:.4g}T"
        if v >= 1e9:  return f"${v/1e9:.4g}B"
        if v >= 1e6:  return f"${v/1e6:.4g}M"
        if v >= 1e3:  return f"${v/1e3:.4g}K"
        return f"${v:.4g}"

    lo = int(np.floor(np.log10(min_v)))
    hi = int(np.ceil(np.log10(max_v))) + 1
    vals: list[float] = []
    for exp in range(lo, hi):
        for m in [1, 2, 5]:
            v = m * (10 ** exp)
            if min_v * 0.4 <= v <= max_v * 2.5:
                vals.append(v)
    vals = sorted(set(vals))
    return vals, [_fmt(v) for v in vals]


def _compact_dollar_tickvals(min_v: float, max_v: float) -> tuple[list, list]:
    """One tick per decade."""
    if min_v <= 0:
        min_v = 1.0
    lo = int(np.floor(np.log10(min_v)))
    hi = int(np.ceil(np.log10(max_v)))
    vals = [10.0 ** d for d in range(lo, hi + 1)]

    def _fmt(v: float) -> str:
        if v >= 1e12: return f"${v/1e12:.4g}T"
        if v >= 1e9:  return f"${v/1e9:.4g}B"
        if v >= 1e6:  return f"${v/1e6:.4g}M"
        if v >= 1e3:  return f"${v/1e3:.4g}K"
        return f"${v:.4g}"

    return vals, [_fmt(v) for v in vals]


# ── Shared axis / layout helpers ──────────────────────────────────────────────

def _xaxis(dtick: str = "M12") -> dict:
    return dict(
        showgrid=True, gridcolor=_GRID, gridwidth=1,
        zeroline=False, showline=False,
        tickfont=dict(family=_FONT, size=11, color=_TEXT),
        title=None,
        dtick=dtick, tickformat="%Y",
    )


def _yaxis_linear(title: str | None = None) -> dict:
    return dict(
        showgrid=True, gridcolor=_GRID, gridwidth=1,
        zeroline=False, showline=False,
        tickfont=dict(family=_FONT, size=11, color=_TEXT),
        title=dict(text=title, font=dict(color=_TEXT, size=11)) if title else None,
    )


def _legend_top() -> dict:
    return dict(
        orientation="h", x=0, y=1.02, yanchor="bottom",
        bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)", borderwidth=0,
        font=dict(size=11, family=_FONT, color=_TEXT),
    )


def _base_layout(title: str, height: int, extra_margin_t: int = 80) -> dict:
    return dict(
        paper_bgcolor=_PAPER,
        plot_bgcolor=_PLOT,
        font=dict(color=_TEXT, family=_FONT, size=12),
        title=dict(
            text=title,
            font=dict(size=14, color=_TEXT, family=_FONT),
            x=0.0, xanchor="left",
            pad=dict(l=0, t=0, b=10),
        ),
        height=height,
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor=COLORS["grid"],
            font=dict(color=_TEXT, size=11, family=_FONT),
        ),
        legend=_legend_top(),
        margin=dict(l=70, r=24, t=extra_margin_t, b=44),
    )


# ── Weekly resampler ──────────────────────────────────────────────────────────

def _weekly(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    Resample a DatetimeIndex DataFrame to weekly frequency (Friday close).
    Uses .last() so the weekly value = end-of-week actual value.
    Only resamples the specified numeric columns.
    """
    return df[cols].resample("W").last().dropna(how="all")


# ══════════════════════════════════════════════════════════════════════════════
# Chart 1: Equity Curve
# ══════════════════════════════════════════════════════════════════════════════

def build_equity_chart(result: SimulationResult) -> go.Figure:
    """
    Equity curve — Strategy vs Buy & Hold.

    Visual fixes vs previous version
    ---------------------------------
    - Weekly resampled data → eliminates daily spike noise
    - fill="tonexty": strategy fills up to itself from a zeroline trace;
      B&H sits on top. No fill-to-absolute-zero spikes.
    - Log Y axis with compact human-readable dollar ticks
    - All axis labels dark (#213448) — readable on cream background
    - Trade markers only at signal crossing edges (first buy after sell, vice versa)
    """
    ph = result.portfolio_history.copy()
    ph.index = pd.to_datetime(ph.index)

    # ── Weekly resample for display (daily precision kept for metrics) ─────────
    ph_w = _weekly(ph, ["portfolio_value", "buy_and_hold_value"])

    tlog = result.trade_log.copy()
    if not tlog.empty:
        tlog["Date"] = pd.to_datetime(tlog["Date"])

    fig = go.Figure()

    # ── Invisible zero-baseline so tonexty fills from bottom of chart area ─────
    # We fill the strategy area by stacking: zero-line (invisible) → strategy →
    # this avoids the "stalagmite" problem of tozeroy on log scale.
    # On log scale, tozeroy would mean filling to log(0) = -∞ at every point.
    # Instead we use a transparent fill between B&H and strategy.

    # Draw B&H first (bottom layer)
    fig.add_trace(go.Scatter(
        x=ph_w.index, y=ph_w["buy_and_hold_value"],
        name="Buy & Hold",
        line=dict(color=COLORS["benchmark"], width=1.5, dash="dot",
                  shape="spline", smoothing=1.0),
        mode="lines",
        opacity=0.75,
        hovertemplate="%{x|%Y-%m-%d} &nbsp;<b>%{y:$,.0f}</b><extra>Buy & Hold</extra>",
    ))

    # Strategy line with fill from B&H line (tonexty = fill between these two)
    fig.add_trace(go.Scatter(
        x=ph_w.index, y=ph_w["portfolio_value"],
        name="Strategy Equity",
        line=dict(color=COLORS["strategy"], width=1.8,
                  shape="spline", smoothing=1.0),
        fill="tonexty",
        fillcolor="rgba(10,124,110,0.08)",
        mode="lines",
        hovertemplate="%{x|%Y-%m-%d} &nbsp;<b>%{y:$,.0f}</b><extra>Strategy</extra>",
    ))

    # ── Trade markers on strategy line ────────────────────────────────────────
    if not tlog.empty:
        # Map trade dates to nearest weekly portfolio value
        ph_w_idx = ph_w["portfolio_value"]

        tlog_first = tlog.loc[tlog["Action"] != tlog["Action"].shift()].copy()
        tlog_rest = tlog.loc[tlog["Action"] == tlog["Action"].shift()].copy()

        for trades, symbol, color, label, visible in [
            (tlog_first[tlog_first["Action"] == "BUY"],  "triangle-up",   COLORS["buy_marker"],  "Buy", True),
            (tlog_first[tlog_first["Action"] == "SELL"], "triangle-down", COLORS["sell_marker"], "Sell", True),
            (tlog_rest[tlog_rest["Action"] == "BUY"],    "circle",        COLORS["buy_marker"],  "Subsequent Buys", "legendonly"),
            (tlog_rest[tlog_rest["Action"] == "SELL"],   "circle",        COLORS["sell_marker"], "Subsequent Sells", "legendonly"),
        ]:
            if trades.empty:
                continue
            trades = trades.copy()
            trades["value"] = ph_w_idx.reindex(trades["Date"], method="nearest").values
            trades = trades[trades["value"] > 0]
            if trades.empty:
                continue
            fig.add_trace(go.Scatter(
                x=trades["Date"], y=trades["value"],
                name=label,
                mode="markers",
                visible=visible,
                marker=dict(
                    symbol=symbol, color=color,
                    size=6 if visible is True else 4, opacity=0.85 if visible is True else 0.5,
                    line=dict(width=0),
                ),
                hovertemplate=(
                    "%{x|%Y-%m-%d}<br>"
                    "Portfolio: <b>%{y:$,.0f}</b>"
                    f"<extra>{label.upper()}</extra>"
                ),
            ))

    # ── Log Y axis ─────────────────────────────────────────────────────────────
    all_vals = pd.concat([ph_w["portfolio_value"], ph_w["buy_and_hold_value"]]).dropna()
    all_vals = all_vals[all_vals > 0]
    vmin, vmax = float(all_vals.min()), float(all_vals.max())
    tick_vals, tick_texts = _log_dollar_ticks(vmin, vmax)

    layout = _base_layout("Equity Curve — Strategy vs Buy & Hold", height=440)
    layout["xaxis"] = _xaxis()
    layout["yaxis"] = dict(
        type="log",
        tickvals=tick_vals, ticktext=tick_texts,
        showgrid=True, gridcolor=_GRID, gridwidth=1,
        zeroline=False, showline=False,
        tickfont=dict(family=_FONT, size=11, color=_TEXT),
        title=None,
    )
    fig.update_layout(**layout)
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# Chart 2: Trolololo Signal
# ══════════════════════════════════════════════════════════════════════════════

def build_cbbi_chart(
    df: pd.DataFrame,
    threshold_buy: int,
    threshold_sell: int,
    signal_column: str = "trolololo",
    trade_log: pd.DataFrame | None = None,
) -> go.Figure:
    """
    Trolololo index with colored threshold bands and trade markers.

    Visual improvements
    -------------------
    - Signal data kept daily (Trolololo daily values are meaningful)
    - Line smoothing=0.6 — removes single-day noise spikes without
      distorting the real shape of the index cycle
    - Green band fill 0→buy_threshold, red band fill sell_threshold→100
      implemented correctly via two paired traces (tonexty)
    - Threshold dashed lines with readable dark labels
    - All markers denoised (first crossing only)
    """
    sig_df = df[[signal_column]].reset_index()
    sig_df.columns = ["date", "signal"]
    sig_df["date"] = pd.to_datetime(sig_df["date"])
    sig_df = sig_df[sig_df["signal"] > 0.001].copy()

    n = len(sig_df)
    dates = sig_df["date"]

    fig = go.Figure()

    # ── Buy zone: 0 → threshold_buy filled green ──────────────────────────────
    fig.add_trace(go.Scatter(
        x=dates, y=[0.0] * n,
        mode="lines", line=dict(width=0),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=[float(threshold_buy)] * n,
        name=f"Buy Zone (≤{threshold_buy})",
        mode="lines", line=dict(width=0),
        fill="tonexty",
        fillcolor=COLORS["buy_zone_fill"],
        hoverinfo="skip",
    ))

    # ── Sell zone: threshold_sell → 100 filled red ────────────────────────────
    fig.add_trace(go.Scatter(
        x=dates, y=[float(threshold_sell)] * n,
        mode="lines", line=dict(width=0),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=[100.0] * n,
        name=f"Sell Zone (≥{threshold_sell})",
        mode="lines", line=dict(width=0),
        fill="tonexty",
        fillcolor=COLORS["sell_zone_fill"],
        hoverinfo="skip",
    ))

    # ── Signal line ────────────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=sig_df["date"], y=sig_df["signal"],
        name="Trolololo Index",
        mode="lines",
        line=dict(
            color=COLORS["signal_line"], width=1.6,
            shape="spline", smoothing=0.6,
        ),
        hovertemplate="%{x|%Y-%m-%d} &nbsp;<b>%{y:.1f}</b><extra>Trolololo</extra>",
    ))

    # ── Threshold dashed horizontal lines ─────────────────────────────────────
    fig.add_hline(
        y=threshold_buy,
        line=dict(color=COLORS["buy_marker"], width=1.5, dash="dash"),
        annotation_text=f"Buy ≤ {threshold_buy}",
        annotation_position="top left",
        annotation_font=dict(color=COLORS["buy_marker"], size=11, family=_FONT),
    )
    fig.add_hline(
        y=threshold_sell,
        line=dict(color=COLORS["sell_marker"], width=1.5, dash="dash"),
        annotation_text=f"Sell ≥ {threshold_sell}",
        annotation_position="top left",
        annotation_font=dict(color=COLORS["sell_marker"], size=11, family=_FONT),
    )

    # ── Trade markers ─────────────────────────────────────────────────────────
    if trade_log is not None and not trade_log.empty:
        tlog = trade_log.copy()
        tlog["Date"] = pd.to_datetime(tlog["Date"])
        
        tlog_first = tlog.loc[tlog["Action"] != tlog["Action"].shift()].copy()
        tlog_rest = tlog.loc[tlog["Action"] == tlog["Action"].shift()].copy()

        sig_idx = sig_df.set_index("date")["signal"]

        for subset, symbol, color, label, visible in [
            (tlog_first[tlog_first["Action"] == "BUY"],  "triangle-up",   COLORS["buy_marker"],  "Buy Signal", True),
            (tlog_first[tlog_first["Action"] == "SELL"], "triangle-down", COLORS["sell_marker"], "Sell Signal", True),
            (tlog_rest[tlog_rest["Action"] == "BUY"],    "circle",        COLORS["buy_marker"],  "Subsequent Buys", "legendonly"),
            (tlog_rest[tlog_rest["Action"] == "SELL"],   "circle",        COLORS["sell_marker"], "Subsequent Sells", "legendonly"),
        ]:
            if subset.empty:
                continue
            subset = subset.copy()
            subset["signal"] = sig_idx.reindex(subset["Date"], method="nearest").values
            fig.add_trace(go.Scatter(
                x=subset["Date"], y=subset["signal"],
                name=label, mode="markers",
                visible=visible,
                marker=dict(
                    symbol=symbol, color=color,
                    size=6 if visible is True else 4, opacity=0.85 if visible is True else 0.5,
                    line=dict(width=0),
                ),
                hovertemplate=(
                    "%{x|%Y-%m-%d}<br>"
                    f"Signal: <b>%{{y:.1f}}</b>"
                    f"<extra>{label}</extra>"
                ),
            ))

    layout = _base_layout(
        f"Trolololo Index with Signals  —  Buy ≤ {threshold_buy}  |  Sell ≥ {threshold_sell}",
        height=300,
        extra_margin_t=70,
    )
    layout["xaxis"] = _xaxis()
    layout["yaxis"] = dict(
        range=[-3, 107],
        showgrid=True, gridcolor=_GRID, gridwidth=1,
        zeroline=False, showline=False,
        tickvals=[0, 20, 40, 60, 80, 100],
        tickfont=dict(family=_FONT, size=11, color=_TEXT),
        title=dict(text="Trolololo Index (0–100)", font=dict(color=_TEXT, size=11)),
    )
    fig.update_layout(**layout)
    return fig


# ── Shared research-page base layout ─────────────────────────────────────────

def _research_layout(fig: go.Figure, title: str, height: int) -> go.Figure:
    fig.update_layout(
        paper_bgcolor=_PAPER,
        plot_bgcolor=_PLOT,
        font=dict(color=_TEXT, family=_FONT, size=12),
        title=dict(
            text=title,
            font=dict(size=14, color=_TEXT, family=_FONT),
            x=0.02,
        ),
        height=height,
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor=_GRID,
            font=dict(color=_TEXT, size=11, family=_FONT),
        ),
        legend=_legend_top(),
        margin=dict(l=70, r=24, t=80, b=44),
        xaxis=dict(
            showgrid=True, gridcolor=_GRID,
            zeroline=False, showline=False,
            tickfont=dict(family=_FONT, size=11, color=_TEXT),
        ),
        yaxis=dict(
            showgrid=True, gridcolor=_GRID,
            zeroline=False, showline=False,
            tickfont=dict(family=_FONT, size=11, color=_TEXT),
        ),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# Chart 3: IS vs OOS Equity (Research page)
# ══════════════════════════════════════════════════════════════════════════════

def build_is_oos_equity_chart(
    df: pd.DataFrame,
    params: dict,
    title: str = "In-Sample vs Out-of-Sample Equity",
) -> go.Figure:
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

    ph = result.portfolio_history.copy()
    ph.index = pd.to_datetime(ph.index)
    split_date = "2021-01-01"

    # Weekly resample
    ph_w = _weekly(ph, ["portfolio_value", "buy_and_hold_value"])

    is_w  = ph_w[ph_w.index < split_date]
    oos_w = ph_w[ph_w.index >= split_date]

    fig = go.Figure()

    # B&H (bottom layer, dashed amber)
    fig.add_trace(go.Scatter(
        x=ph_w.index, y=ph_w["buy_and_hold_value"],
        name="Buy & Hold",
        line=dict(color=COLORS["benchmark"], width=1.5, dash="dot",
                  shape="spline", smoothing=1.0),
        opacity=0.75,
        hovertemplate="%{x|%Y-%m-%d}&nbsp;<b>$%{y:,.0f}</b><extra>B&H</extra>",
    ))

    # IS strategy (teal, fill to B&H)
    fig.add_trace(go.Scatter(
        x=is_w.index, y=is_w["portfolio_value"],
        name="Strategy IS (2012–2020)",
        line=dict(color=COLORS["strategy"], width=1.8,
                  shape="spline", smoothing=1.0),
        fill="tonexty",
        fillcolor="rgba(10,124,110,0.09)",
        hovertemplate="%{x|%Y-%m-%d}&nbsp;<b>$%{y:,.0f}</b><extra>IS Strategy</extra>",
    ))

    # OOS strategy (blue, no fill — sits visually separate)
    fig.add_trace(go.Scatter(
        x=oos_w.index, y=oos_w["portfolio_value"],
        name="Strategy OOS (2021–2026)",
        line=dict(color="#0369a1", width=1.8,
                  shape="spline", smoothing=1.0),
        fill="tonexty",
        fillcolor="rgba(3,105,161,0.07)",
        hovertemplate="%{x|%Y-%m-%d}&nbsp;<b>$%{y:,.0f}</b><extra>OOS Strategy</extra>",
    ))

    # IS | OOS split vertical line
    split_ts = int(pd.Timestamp(split_date).timestamp() * 1000)
    fig.add_vline(
        x=split_ts,
        line=dict(color=COLORS["axis_line"], width=1.2, dash="dash"),
        annotation_text="IS | OOS split",
        annotation_position="top",
        annotation_font=dict(color=_MUTED, size=10, family=_FONT),
    )

    # Log Y
    all_v = pd.concat([ph_w["portfolio_value"], ph_w["buy_and_hold_value"]]).dropna()
    all_v = all_v[all_v > 0]
    tick_vals, tick_texts = (
        _compact_dollar_tickvals(float(all_v.min()), float(all_v.max()))
        if len(all_v) else ([1e2, 1e4, 1e6], ["$100", "$10K", "$1M"])
    )

    _research_layout(fig, title, height=360)
    fig.update_layout(
        yaxis=dict(
            type="log",
            tickvals=tick_vals, ticktext=tick_texts,
            title=dict(text="Portfolio Value", font=dict(color=_TEXT, size=11)),
            showgrid=True, gridcolor=_GRID,
            zeroline=False, showline=False,
            tickfont=dict(family=_FONT, size=11, color=_TEXT),
        ),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# Chart 4: Degradation Bar
# ══════════════════════════════════════════════════════════════════════════════

def build_degradation_chart(degradation: dict) -> go.Figure:
    objectives = list(degradation.keys())
    metric_labels = {
        "return_degradation_pct":   "Return Degradation %",
        "sharpe_degradation_pct":   "Sharpe Degradation %",
        "drawdown_degradation_pct": "Drawdown Change %",
    }
    metric_colors = {
        "return_degradation_pct":   COLORS["sell_marker"],
        "sharpe_degradation_pct":   "#f87171",
        "drawdown_degradation_pct": "#d97706",
    }

    fig = go.Figure()
    for metric_key, metric_label in metric_labels.items():
        values = [degradation[obj].get(metric_key, 0) for obj in objectives]
        fig.add_trace(go.Bar(
            name=metric_label,
            x=[o.replace("_", " ").title() for o in objectives],
            y=values,
            marker_color=metric_colors[metric_key],
            marker_line=dict(width=0),
            opacity=0.85,
            hovertemplate=f"<b>{metric_label}</b>: %{{y:.1f}}%<extra></extra>",
        ))

    _research_layout(fig, "IS → OOS Performance Degradation by Objective", height=320)
    fig.update_layout(
        barmode="group",
        yaxis=dict(
            ticksuffix="%",
            title=dict(text="Degradation (%)", font=dict(color=_TEXT, size=11)),
            showgrid=True, gridcolor=_GRID,
            zeroline=True, zerolinecolor=COLORS["axis_line"], zerolinewidth=1,
            tickfont=dict(family=_FONT, size=11, color=_TEXT),
        ),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# Chart 5: Sensitivity Heatmap
# ══════════════════════════════════════════════════════════════════════════════

def build_sensitivity_heatmap(
    pivot_df: pd.DataFrame,
    title: str = "Return Sensitivity: Buy vs Sell Threshold",
    metric_label: str = "Total Return",
) -> go.Figure:
    display_df = pivot_df.copy()
    p99 = float(np.nanpercentile(display_df.values, 99))
    display_df = display_df.clip(upper=p99)

    x_labels = [int(c) for c in display_df.columns]
    y_labels = [int(r) for r in display_df.index]

    fig = px.imshow(
        display_df.values,
        x=x_labels, y=y_labels,
        color_continuous_scale="RdYlGn",
        aspect="auto",
        labels=dict(x="Buy Threshold", y="Sell Threshold", color=metric_label),
    )
    fig.update_traces(hovertemplate=(
        "Buy Threshold: <b>%{x}</b><br>"
        "Sell Threshold: <b>%{y}</b><br>"
        f"{metric_label}: <b>%{{z:,.1f}}</b><extra></extra>"
    ))
    _research_layout(fig, title, height=440)
    fig.update_layout(
        coloraxis_colorbar=dict(
            title=dict(text=metric_label, font=dict(size=11, color=_TEXT)),
            tickfont=dict(size=10, family=_FONT, color=_TEXT),
        ),
        xaxis=dict(
            title=dict(text="Buy Threshold", font=dict(color=_TEXT, size=11)),
            tickfont=dict(family=_FONT, size=10, color=_TEXT),
        ),
        yaxis=dict(
            title=dict(text="Sell Threshold", font=dict(color=_TEXT, size=11)),
            tickfont=dict(family=_FONT, size=10, color=_TEXT),
        ),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# Chart 6: Performance Comparison (3-panel bar)
# ══════════════════════════════════════════════════════════════════════════════

def build_comparison_chart(results: dict) -> go.Figure:
    """
    Three-panel grouped bar: Total Return (log scale) | Max Drawdown | Sharpe.
    All axis labels fully readable on light background.
    """
    s1_oos  = results["scenario_1"]["out_of_sample"]["max_return"]
    s2_full = results["scenario_2"]["full_dataset"]["max_return"]
    bh_oos  = results["buy_and_hold_benchmark"]["out_of_sample"]

    scenarios = ["S1 OOS\n(Validated)", "S2 Full\n(Exploration)", "Buy & Hold\n(OOS)"]
    colors    = [COLORS["strategy"], "#7c3aed", COLORS["benchmark"]]

    def _pct(v):     return v * 100
    def _s(d, k):    return d.get(k, 0) or 0

    returns   = [_pct(_s(s1_oos, "total_return")),
                 _pct(_s(s2_full, "total_return")),
                 _pct(_s(bh_oos,  "total_return"))]
    drawdowns = [_pct(_s(s1_oos, "max_drawdown")),
                 _pct(_s(s2_full, "max_drawdown")),
                 _pct(_s(bh_oos,  "max_drawdown"))]
    sharpes   = [_s(s1_oos, "sharpe_ratio"),
                 _s(s2_full, "sharpe_ratio"),
                 _s(bh_oos,  "sharpe_ratio")]

    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=["Total Return (%)", "Max Drawdown (%)", "Sharpe Ratio"],
        horizontal_spacing=0.10,
    )

    for i, (scen, col) in enumerate(zip(scenarios, colors)):
        label = scen.replace("\n", " ")
        fig.add_trace(go.Bar(
            name=label, x=[label], y=[returns[i]], marker_color=col,
            marker_line=dict(width=0), opacity=0.85,
            showlegend=(i == 0),
            hovertemplate=f"<b>{label}</b><br>Return: %{{y:,.1f}}%<extra></extra>",
        ), row=1, col=1)
        fig.add_trace(go.Bar(
            name=label, x=[label], y=[drawdowns[i]], marker_color=col,
            marker_line=dict(width=0), opacity=0.85,
            showlegend=False,
            hovertemplate=f"<b>{label}</b><br>Drawdown: %{{y:.1f}}%<extra></extra>",
        ), row=1, col=2)
        fig.add_trace(go.Bar(
            name=label, x=[label], y=[sharpes[i]], marker_color=col,
            marker_line=dict(width=0), opacity=0.85,
            showlegend=False,
            hovertemplate=f"<b>{label}</b><br>Sharpe: %{{y:.3f}}<extra></extra>",
        ), row=1, col=3)

    # Log scale for Total Return panel
    ret_pos = [r for r in returns if r > 0]
    if ret_pos:
        lo = max(0, int(np.floor(np.log10(min(ret_pos)))))
        hi = int(np.ceil(np.log10(max(ret_pos)))) + 1
        log_ticks = [10.0 ** d for d in range(lo, hi)]

        def _pct_fmt(v: float) -> str:
            if v >= 1e9: return f"{v/1e9:.4g}B%"
            if v >= 1e6: return f"{v/1e6:.4g}M%"
            if v >= 1e3: return f"{v/1e3:.4g}K%"
            return f"{v:.4g}%"

        log_tick_texts = [_pct_fmt(v) for v in log_ticks]
    else:
        log_ticks, log_tick_texts = [1, 100, 10000], ["1%", "100%", "10K%"]

    _tick_font = dict(family=_FONT, size=10, color=_TEXT)

    fig.update_yaxes(
        type="log", tickvals=log_ticks, ticktext=log_tick_texts,
        title_text="Return (%)",
        title_font=dict(color=_TEXT, size=11),
        tickfont=_tick_font,
        showgrid=True, gridcolor=_GRID,
        row=1, col=1,
    )
    fig.update_yaxes(
        ticksuffix="%",
        title_text="Drawdown (%)",
        title_font=dict(color=_TEXT, size=11),
        tickfont=_tick_font,
        showgrid=True, gridcolor=_GRID,
        row=1, col=2,
    )
    fig.update_yaxes(
        title_text="Sharpe Ratio",
        title_font=dict(color=_TEXT, size=11),
        tickfont=_tick_font,
        showgrid=True, gridcolor=_GRID,
        row=1, col=3,
    )
    fig.update_xaxes(tickfont=_tick_font)

    fig.update_layout(
        paper_bgcolor=_PAPER,
        plot_bgcolor=_PLOT,
        font=dict(color=_TEXT, family=_FONT, size=12),
        title=dict(
            text="Performance Comparison — S1 OOS vs S2 Full vs Buy & Hold",
            font=dict(size=14, color=_TEXT, family=_FONT),
            x=0.02,
        ),
        height=380,
        showlegend=True,
        legend=dict(
            orientation="h", x=0, y=1.10,
            bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)",
            font=dict(size=11, family=_FONT, color=_TEXT),
        ),
        barmode="group",
        margin=dict(l=70, r=24, t=80, b=44),
    )
    # Subplot title font — must match light theme
    for ann in fig.layout.annotations:
        ann.font.update(size=12, color=_TEXT, family=_FONT)

    return fig
