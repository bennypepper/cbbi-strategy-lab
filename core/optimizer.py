"""
core/optimizer.py
=================
Dynamic Grid Search Optimizer for CBBI Strategy Lab.

Runs a Numba-JIT-compiled grid search over all (buy_threshold, sell_threshold,
alloc_buy, alloc_sell) combinations against any DataFrame.

Designed to be called against live CBBI API data so that optimal params
stay aligned with the current (ever-evolving) CBBI formula — addressing the
"Index Revision Bias" documented in our research.

Architecture note
-----------------
This is a WEBAPP extension for practical deployment.
The academic research (PKL_v4) was conducted on a frozen snapshot (master_dataset.parquet)
and its results are fixed. This optimizer produces a `live_optimal_params.json`
used only by the Simulator's "Live API" mode.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
import numba
import pandas as pd

from core.engine import warmup_numba

# ── Output path ───────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]
LIVE_PARAMS_PATH = _ROOT / "data" / "live_optimal_params.json"


# ── Grid search parameter space (mirrors PKL_v4 methodology) ────────────────
BUY_THRESHOLDS  = list(range(1, 50, 2))     # 1, 3, 5 … 49  (25 values)
SELL_THRESHOLDS = list(range(50, 101, 2))   # 50, 52 … 100  (26 values)
ALLOC_STEPS     = [0.01, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]  # 7 values each
# Total combinations: 25 × 26 × 7 × 7 = 31,850 — fast on Numba


@dataclass
class OptimizationResult:
    status: str                    # "success" | "error"
    total_combinations: int = 0
    elapsed_seconds: float = 0.0
    data_source: str = ""
    data_date_range: str = ""
    error_message: str = ""

    # Best params by objective
    max_return: dict = field(default_factory=dict)
    max_sharpe: dict = field(default_factory=dict)
    min_drawdown: dict = field(default_factory=dict)

    # Benchmark
    buy_and_hold: dict = field(default_factory=dict)


# ── Core Numba grid kernel ────────────────────────────────────────────────────

@numba.njit(cache=True, fastmath=True)
def _full_backtest_kernel(
    open_prices: np.ndarray,
    close_prices: np.ndarray,
    signal: np.ndarray,
    threshold_buy: float,
    threshold_sell: float,
    alloc_buy: float,
    alloc_sell: float,
    initial_cash: float,
    fee_rate: float,
) -> tuple:
    """
    Vectorised single backtest loop. Returns (total_return, sharpe, max_drawdown, trade_count).
    Uses same T+1 execution logic as production engine.
    """
    n = len(open_prices)
    cash = initial_cash
    btc = 0.0
    trade_count = 0
    peak = initial_cash

    daily_returns = np.empty(n - 1)

    prev_val = initial_cash

    for i in range(n - 1):
        sig = signal[i]
        exec_price = open_prices[i + 1]   # T+1 open execution

        if sig <= threshold_buy and exec_price > 0 and cash > 1.0:
            spend = cash * alloc_buy
            btc_bought = spend * (1.0 - fee_rate) / exec_price
            btc  += btc_bought
            cash -= spend
            trade_count += 1

        elif sig >= threshold_sell and exec_price > 0 and btc > 0.0:
            sell_btc = btc * alloc_sell
            proceeds = sell_btc * exec_price * (1.0 - fee_rate)
            cash += proceeds
            btc  -= sell_btc
            trade_count += 1

        port_val = cash + btc * close_prices[i + 1]
        if port_val > peak:
            peak = port_val

        dr = (port_val - prev_val) / prev_val if prev_val > 0 else 0.0
        daily_returns[i] = dr
        prev_val = port_val

    final_val = cash + btc * close_prices[-1]
    total_return = (final_val - initial_cash) / initial_cash

    # Sharpe (annualised, 252 trading days)
    mean_r = np.mean(daily_returns)
    std_r  = np.std(daily_returns)
    sharpe = (mean_r / std_r * np.sqrt(252)) if std_r > 1e-10 else 0.0

    # Max drawdown (running peak)
    running_peak = initial_cash
    max_dd = 0.0
    port_val = initial_cash
    for i in range(n):
        port_val = initial_cash + daily_returns[i - 1] * port_val if i > 0 else initial_cash
        # Simpler: recompute from daily_returns
    # Fast drawdown from daily_returns array
    cum = np.empty(n)
    cum[0] = initial_cash
    for i in range(1, n):
        cum[i] = cum[i - 1] * (1.0 + daily_returns[i - 1])
    for i in range(1, n):
        if cum[i - 1] > running_peak:
            running_peak = cum[i - 1]
        dd = (cum[i] - running_peak) / running_peak
        if dd < max_dd:
            max_dd = dd

    return total_return, sharpe, max_dd, trade_count


@numba.njit(cache=True, parallel=True, fastmath=True)
def _grid_search_kernel(
    open_prices: np.ndarray,
    close_prices: np.ndarray,
    signal: np.ndarray,
    buy_thresholds: np.ndarray,
    sell_thresholds: np.ndarray,
    alloc_buys: np.ndarray,
    alloc_sells: np.ndarray,
    initial_cash: float,
    fee_rate: float,
    results: np.ndarray,   # shape: (N_combos, 6) — buy, sell, abuy, asell, ret, sharpe, dd, tc
) -> None:
    """
    Parallel grid sweep. Writes each row of `results` in-place.
    results columns: buy_thresh, sell_thresh, alloc_buy, alloc_sell, total_return, sharpe, max_dd, trade_count
    """
    n_buy   = len(buy_thresholds)
    n_sell  = len(sell_thresholds)
    n_abuy  = len(alloc_buys)
    n_asell = len(alloc_sells)

    total = n_buy * n_sell * n_abuy * n_asell

    for idx in numba.prange(total):
        i_buy   = idx // (n_sell * n_abuy * n_asell)
        rem     = idx  % (n_sell * n_abuy * n_asell)
        i_sell  = rem  // (n_abuy * n_asell)
        rem2    = rem   % (n_abuy * n_asell)
        i_abuy  = rem2  // n_asell
        i_asell = rem2  % n_asell

        bt = buy_thresholds[i_buy]
        st = sell_thresholds[i_sell]
        ab = alloc_buys[i_abuy]
        as_ = alloc_sells[i_asell]

        if bt >= st:
            results[idx, 0] = bt
            results[idx, 1] = st
            results[idx, 2] = ab
            results[idx, 3] = as_
            results[idx, 4] = -999.0
            results[idx, 5] = -999.0
            results[idx, 6] = 0.0
            results[idx, 7] = 0.0
            continue

        ret, sharpe, dd, tc = _full_backtest_kernel(
            open_prices, close_prices, signal,
            bt, st, ab, as_, initial_cash, fee_rate,
        )

        results[idx, 0] = bt
        results[idx, 1] = st
        results[idx, 2] = ab
        results[idx, 3] = as_
        results[idx, 4] = ret
        results[idx, 5] = sharpe
        results[idx, 6] = dd
        results[idx, 7] = tc


def warmup_optimizer() -> None:
    """Pre-JIT the optimizer kernel with tiny dummy data."""
    warmup_numba()
    tiny = np.ones(20, dtype=np.float64) * 50000.0
    sig  = np.linspace(10, 90, 20)
    bts  = np.array([20.0, 30.0])
    sts  = np.array([60.0, 70.0])
    als  = np.array([0.10, 0.25])
    n    = len(bts) * len(sts) * len(als) * len(als)
    res  = np.zeros((n, 8), dtype=np.float64)
    _grid_search_kernel(tiny, tiny, sig, bts, sts, als, als, 100_000.0, 0.001, res)


def run_live_optimization(
    df: pd.DataFrame,
    initial_cash: float = 100_000.0,
    fee_rate: float = 0.001,
    progress_cb: Callable[[float, str], None] | None = None,
    split_date: str = "2021-01-01",
) -> OptimizationResult:
    """
    Run full grid search against the provided DataFrame (should be live CBBI data).

    Parameters
    ----------
    df           : DataFrame with btc_open, btc_close, trolololo columns; DatetimeIndex
    initial_cash : Starting capital
    fee_rate     : Per-trade fee
    progress_cb  : Optional (pct_float, status_str) callback for Streamlit progress bars
    split_date   : IS/OOS split date for in-sample optimization (default 2021-01-01)

    Returns      : OptimizationResult dataclass
    """
    if progress_cb:
        progress_cb(0.02, "Preparing data arrays…")

    # Use is-sample slice for optimization (prevents overfitting on OOS)
    df_is = df[df.index < split_date].copy()
    df_is = df_is.dropna(subset=["btc_open", "btc_close", "trolololo"])

    if len(df_is) < 200:
        return OptimizationResult(
            status="error",
            error_message=f"Insufficient IS data: only {len(df_is)} rows before {split_date}."
        )

    open_prices  = df_is["btc_open"].to_numpy(dtype=np.float64)
    close_prices = df_is["btc_close"].to_numpy(dtype=np.float64)
    signal       = df_is["trolololo"].to_numpy(dtype=np.float64)

    buy_arr  = np.array(BUY_THRESHOLDS,  dtype=np.float64)
    sell_arr = np.array(SELL_THRESHOLDS, dtype=np.float64)
    alloc_arr = np.array(ALLOC_STEPS,   dtype=np.float64)

    n_combos = len(buy_arr) * len(sell_arr) * len(alloc_arr) ** 2
    results_arr = np.zeros((n_combos, 8), dtype=np.float64)

    if progress_cb:
        progress_cb(0.08, f"Running {n_combos:,} combinations (Numba parallel)…")

    t0 = time.perf_counter()
    _grid_search_kernel(
        open_prices, close_prices, signal,
        buy_arr, sell_arr, alloc_arr, alloc_arr,
        initial_cash, fee_rate, results_arr,
    )
    elapsed = time.perf_counter() - t0

    if progress_cb:
        progress_cb(0.70, "Extracting best parameters…")

    # Filter invalid (buy >= sell) rows
    valid_mask = (results_arr[:, 0] < results_arr[:, 1]) & (results_arr[:, 4] > -999.0)
    valid = results_arr[valid_mask]

    if len(valid) == 0:
        return OptimizationResult(status="error", error_message="No valid combinations found.")

    def _best_row(arr: np.ndarray, col: int, maximize: bool) -> dict:
        idx = np.argmax(arr[:, col]) if maximize else np.argmin(arr[:, col])
        r = arr[idx]
        return {
            "threshold_buy":       int(r[0]),
            "threshold_sell":      int(r[1]),
            "allocation_buy_pct":  round(float(r[2]), 4),
            "allocation_sell_pct": round(float(r[3]), 4),
            "total_return":        round(float(r[4]), 6),
            "sharpe_ratio":        round(float(r[5]), 6),
            "max_drawdown":        round(float(r[6]), 6),
            "trade_count":         int(r[7]),
        }

    best_return   = _best_row(valid, 4, True)
    best_sharpe   = _best_row(valid, 5, True)
    best_drawdown = _best_row(valid, 6, False)  # least negative

    # Buy & Hold benchmark on IS period
    bh_start = float(open_prices[0])
    bh_end   = float(close_prices[-1])
    bh_return = (bh_end - bh_start) / bh_start if bh_start > 0 else 0.0

    if progress_cb:
        progress_cb(0.90, "Saving results…")

    date_min = str(df_is.index.min().date())
    date_max = str(df_is.index.max().date())

    result = OptimizationResult(
        status="success",
        total_combinations=n_combos,
        elapsed_seconds=round(elapsed, 2),
        data_source="live_cbbi_api",
        data_date_range=f"{date_min} → {date_max}",
        max_return=best_return,
        max_sharpe=best_sharpe,
        min_drawdown=best_drawdown,
        buy_and_hold={"total_return": round(bh_return, 6)},
    )

    # Persist to disk
    _save_result(result)

    if progress_cb:
        progress_cb(1.0, "Done!")

    return result


def _save_result(result: OptimizationResult) -> None:
    """Serialize OptimizationResult to live_optimal_params.json."""
    payload = {
        "generated_at":       time.strftime("%Y-%m-%d %H:%M:%S"),
        "status":             result.status,
        "total_combinations": result.total_combinations,
        "elapsed_seconds":    result.elapsed_seconds,
        "data_source":        result.data_source,
        "data_date_range":    result.data_date_range,
        "max_return":         result.max_return,
        "max_sharpe":         result.max_sharpe,
        "min_drawdown":       result.min_drawdown,
        "buy_and_hold":       result.buy_and_hold,
    }
    LIVE_PARAMS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LIVE_PARAMS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_live_params() -> dict | None:
    """Load live_optimal_params.json if it exists, else return None."""
    if not LIVE_PARAMS_PATH.exists():
        return None
    with open(LIVE_PARAMS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
