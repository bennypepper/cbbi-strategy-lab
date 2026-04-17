"""
core/engine.py
==============
Backtest engine adapted from PKL_v4/src/optimization/engine.py.

Two functions:
  - run_backtest_numba()  : JIT-compiled, returns scalars only. Used for fast
                            repeated evaluation (e.g., heatmap lookups if needed).
  - run_backtest_full()   : Pure Python. Same logic but additionally returns
                            per-day portfolio history and trade log. Used by the
                            simulator page to render charts.

Anti-Lookahead Bias Rule (enforced in both functions):
  - Signal ← trolololo[T]  (close of day T)
  - Execution ← btc_open[T+1]  (open of day T+1)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from numba import njit


# ── Numba JIT engine ─────────────────────────────────────────────────────────

@njit
def run_backtest_numba(
    signals: np.ndarray,
    prices_open: np.ndarray,
    prices_close: np.ndarray,
    threshold_buy: int,
    threshold_sell: int,
    alloc_buy_pct: float,
    alloc_sell_pct: float,
    initial_cash: float = 100_000.0,
    fee_rate: float = 0.001,
):
    """
    Numba JIT-compiled backtest loop (C-level performance).

    Parameters
    ----------
    signals       : daily Trolololo values [0–100]
    prices_open   : daily BTC open prices (execution T+1)
    prices_close  : daily BTC close prices (signal evaluation)
    threshold_buy : signal < threshold_buy  → BUY
    threshold_sell: signal > threshold_sell → SELL
    alloc_buy_pct : fraction of cash to deploy per BUY (0.01–0.25)
    alloc_sell_pct: fraction of BTC to sell per SELL (0.01–0.25)
    initial_cash  : starting USD balance
    fee_rate      : trading fee per transaction (0.001 = 0.1%)

    Returns
    -------
    tuple: (total_return, max_drawdown, sharpe_ratio, wins, sell_count, trade_count)
    """
    n_days = len(signals)

    cash = initial_cash
    btc = 0.0
    trade_count = 0
    wins = 0
    sell_count = 0

    portfolio_value = np.zeros(n_days, dtype=np.float64)
    daily_returns   = np.zeros(n_days, dtype=np.float64)

    avg_entry_price = 0.0
    portfolio_value[0] = initial_cash

    for i in range(n_days - 1):
        sig      = signals[i]
        p_exec   = prices_open[i + 1]   # T+1 open — execution price
        p_close  = prices_close[i]      # T close — valuation

        curr_val = cash + (btc * p_close)
        portfolio_value[i] = curr_val
        if i > 0:
            prev = portfolio_value[i - 1]
            daily_returns[i] = (curr_val - prev) / prev if prev > 0 else 0.0

        if sig <= threshold_buy:
            trade_amount = cash * alloc_buy_pct
            if trade_amount > 1.0:  # Minimum $1 guard — prevents dust buys (matches CLI)
                fee        = trade_amount * fee_rate
                net_usd    = trade_amount - fee
                btc_bought = net_usd / p_exec
                total_cost = (btc * avg_entry_price) + trade_amount
                btc       += btc_bought
                if btc > 0:
                    avg_entry_price = total_cost / btc
                cash -= trade_amount
                trade_count += 1

        elif sig >= threshold_sell:
            btc_sold = btc * alloc_sell_pct
            if btc_sold > 0.000001:  # Minimum BTC dust guard (matches CLI)
                gross_usd = btc_sold * p_exec
                fee       = gross_usd * fee_rate
                net_usd   = gross_usd - fee
                cost_sold = btc_sold * avg_entry_price
                cash     += net_usd
                btc      -= btc_sold
                trade_count += 1
                if net_usd > cost_sold:
                    wins += 1
                sell_count += 1

    # Final day valuation
    portfolio_value[n_days - 1] = cash + (btc * prices_close[n_days - 1])
    prev = portfolio_value[n_days - 2]
    daily_returns[n_days - 1] = (
        (portfolio_value[n_days - 1] - prev) / prev if prev > 0 else 0.0
    )

    # ── Metrics ──────────────────────────────────────────────────────────────
    total_return = (portfolio_value[-1] - initial_cash) / initial_cash

    max_drawdown = 0.0
    peak = portfolio_value[0]
    for i in range(n_days):
        if portfolio_value[i] > peak:
            peak = portfolio_value[i]
        dd = (peak - portfolio_value[i]) / peak if peak > 0 else 0.0
        if dd > max_drawdown:
            max_drawdown = dd

    mean_ret = np.mean(daily_returns)
    std_ret  = np.std(daily_returns)
    rf_daily = 0.04 / 365.0
    sharpe_ratio = 0.0
    if std_ret > 0:
        sharpe_ratio = ((mean_ret - rf_daily) / std_ret) * np.sqrt(365.0)

    return total_return, max_drawdown, sharpe_ratio, wins, sell_count, trade_count


# ── Full trace engine (Python-level) ─────────────────────────────────────────

@dataclass
class SimulationResult:
    """Full output of a simulator run."""
    portfolio_history: pd.DataFrame   # columns: date, portfolio_value, cash, btc_held
    trade_log: pd.DataFrame           # columns: date, action, signal_value, exec_price, amount_usd, portfolio_value_after
    metrics: dict                     # total_return, max_drawdown, sharpe_ratio, win_rate, trade_count
    benchmark_metrics: dict           # buy_and_hold: total_return, max_drawdown, sharpe_ratio
    low_sample_warning: bool
    params: dict                      # echo of input params


def run_backtest_full(
    df: pd.DataFrame,
    threshold_buy: int,
    threshold_sell: int,
    alloc_buy_pct: float,
    alloc_sell_pct: float,
    initial_cash: float = 100_000.0,
    fee_rate: float = 0.001,
    signal_column: str = "trolololo",
) -> SimulationResult:
    """
    Full-trace backtest — same logic as Numba engine but also tracks
    per-day portfolio state and individual trade log.

    Parameters
    ----------
    df            : master_dataset slice (DatetimeIndex, must contain signal_column,
                    btc_open, btc_close)
    threshold_buy : signal < threshold_buy  → BUY
    threshold_sell: signal > threshold_sell → SELL
    alloc_buy_pct : 0.01–0.25 (fraction of cash per BUY)
    alloc_sell_pct: 0.01–0.25 (fraction of BTC per SELL)
    initial_cash  : starting USD balance
    fee_rate      : per-trade fee (0.001 = 0.1%)
    signal_column : default 'trolololo'

    Returns
    -------
    SimulationResult
    """
    df = df.dropna(subset=[signal_column, "btc_open", "btc_close"]).copy()
    n = len(df)

    signals      = df[signal_column].values.astype(np.float64)
    prices_open  = df["btc_open"].values.astype(np.float64)
    prices_close = df["btc_close"].values.astype(np.float64)
    dates        = df.index

    cash            = initial_cash
    btc             = 0.0
    avg_entry_price = 0.0
    trade_count     = 0
    wins            = 0
    sell_count      = 0

    pv   = np.zeros(n, dtype=np.float64)
    cash_arr = np.zeros(n, dtype=np.float64)
    btc_arr  = np.zeros(n, dtype=np.float64)
    dr   = np.zeros(n, dtype=np.float64)

    trade_rows: list = []

    pv[0]       = initial_cash
    cash_arr[0] = initial_cash
    btc_arr[0]  = 0.0

    for i in range(n - 1):
        sig    = signals[i]
        p_exec = prices_open[i + 1]   # T+1 open
        p_val  = prices_close[i]      # T close for valuation

        curr_val    = cash + (btc * p_val)
        pv[i]       = curr_val
        cash_arr[i] = cash
        btc_arr[i]  = btc

        if i > 0:
            prev = pv[i - 1]
            dr[i] = (curr_val - prev) / prev if prev > 0 else 0.0

        action = None

        if sig <= threshold_buy:
            trade_amount = cash * alloc_buy_pct
            if trade_amount > 1.0:  # Minimum $1 guard — prevents dust buys (matches CLI)
                fee        = trade_amount * fee_rate
                net_usd    = trade_amount - fee
                btc_bought = net_usd / p_exec
                total_cost = (btc * avg_entry_price) + trade_amount
                btc       += btc_bought
                avg_entry_price = total_cost / btc if btc > 0 else 0.0
                cash -= trade_amount
                trade_count += 1
                action = ("BUY", trade_amount, btc_bought)

        elif sig >= threshold_sell:
            btc_sold = btc * alloc_sell_pct
            if btc_sold > 0.000001:  # Minimum BTC dust guard (matches CLI)
                gross_usd = btc_sold * p_exec
                fee       = gross_usd * fee_rate
                net_usd   = gross_usd - fee
                cost_sold = btc_sold * avg_entry_price
                cash     += net_usd
                btc      -= btc_sold
                trade_count += 1
                if net_usd > cost_sold:
                    wins += 1
                sell_count += 1
                action = ("SELL", gross_usd, btc_sold)

        if action is not None:
            exec_date = dates[i + 1] if i + 1 < n else dates[i]
            equity_after = cash + btc * p_exec
            trade_rows.append({
                "Date":           exec_date,
                "Action":         action[0],
                "BTC Price":      round(p_exec, 2),
                "Amount (USD)":   round(action[1], 2),
                "BTC Amount":     round(action[2], 6),   # exact BTC qty bought/sold
                "CBBI Index":     round(sig, 1),
                "Cash After":     round(cash, 2),
                "BTC Held After": round(btc, 6),
                "Equity After":   round(equity_after, 2),
            })

    # Final day
    pv[n - 1]       = cash + (btc * prices_close[n - 1])
    cash_arr[n - 1] = cash
    btc_arr[n - 1]  = btc
    prev = pv[n - 2] if n >= 2 else initial_cash
    dr[n - 1] = (pv[n - 1] - prev) / prev if prev > 0 else 0.0

    # ── Metrics ──────────────────────────────────────────────────────────────
    total_return = (pv[-1] - initial_cash) / initial_cash

    max_drawdown = 0.0
    peak = pv[0]
    for i in range(n):
        if pv[i] > peak:
            peak = pv[i]
        dd = (peak - pv[i]) / peak if peak > 0 else 0.0
        if dd > max_drawdown:
            max_drawdown = dd

    mean_ret = float(np.mean(dr))
    std_ret  = float(np.std(dr))
    rf_daily = 0.04 / 365.0
    sharpe_ratio = 0.0
    if std_ret > 0:
        sharpe_ratio = ((mean_ret - rf_daily) / std_ret) * np.sqrt(365.0)

    win_rate = float(wins) / sell_count if sell_count > 0 else 0.0

    # ── Portfolio history DataFrame ───────────────────────────────────────────
    portfolio_history = pd.DataFrame({
        "date":            dates,
        "portfolio_value": pv,
        "cash":            cash_arr,
        "btc_held":        btc_arr,
        "btc_close":       prices_close,
    }).set_index("date")

    # ── Buy & Hold benchmark ──────────────────────────────────────────────────
    # Use open[0] entry with fee deducted — matches CLI behavior exactly
    _bh_btc   = (initial_cash * (1.0 - fee_rate)) / prices_open[0]
    bh_values = _bh_btc * prices_close
    bh_return = (_bh_btc * prices_close[-1] - initial_cash) / initial_cash
    bh_daily_ret = np.diff(prices_close) / prices_close[:-1]
    bh_daily_ret = np.concatenate([[0.0], bh_daily_ret])

    bh_mdd = 0.0
    bh_peak = prices_close[0]
    for p in prices_close:
        if p > bh_peak:
            bh_peak = p
        bh_dd = (bh_peak - p) / bh_peak if bh_peak > 0 else 0.0
        if bh_dd > bh_mdd:
            bh_mdd = bh_dd

    bh_mean = float(np.mean(bh_daily_ret))
    bh_std  = float(np.std(bh_daily_ret))
    bh_sharpe = ((bh_mean - rf_daily) / bh_std * np.sqrt(365.0)) if bh_std > 0 else 0.0

    portfolio_history["buy_and_hold_value"] = bh_values

    # ── Trade log ─────────────────────────────────────────────────────────────
    trade_log = pd.DataFrame(trade_rows) if trade_rows else pd.DataFrame(
        columns=[
            "Date", "Action", "BTC Price", "Amount (USD)",
            "BTC Amount", "CBBI Index", "Cash After",
            "BTC Held After", "Equity After",
        ]
    )

    return SimulationResult(
        portfolio_history=portfolio_history,
        trade_log=trade_log,
        metrics={
            "total_return":  total_return,
            "max_drawdown":  max_drawdown,
            "sharpe_ratio":  sharpe_ratio,
            "win_rate":      win_rate,
            "trade_count":   trade_count,
        },
        benchmark_metrics={
            "total_return": bh_return,
            "max_drawdown": bh_mdd,
            "sharpe_ratio": bh_sharpe,
        },
        low_sample_warning=(trade_count < 10),
        params={
            "threshold_buy":   threshold_buy,
            "threshold_sell":  threshold_sell,
            "alloc_buy_pct":   alloc_buy_pct,
            "alloc_sell_pct":  alloc_sell_pct,
            "initial_cash":    initial_cash,
            "fee_rate":        fee_rate,
            "signal_column":   signal_column,
        },
    )


def warmup_numba() -> None:
    """Pre-compile Numba JIT function on app startup to eliminate user-facing delay."""
    dummy = np.ones(100, dtype=np.float64)
    run_backtest_numba(dummy, dummy, dummy, 20, 75, 0.10, 0.10, 100_000.0, 0.001)
