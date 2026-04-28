"""
core/data_loader.py
===================
Data loading helpers with Streamlit cache decorators.
All paths are relative to the repo root (data/).

Methodology update (2026-04-27):
  fetch_cbbi_live() has been replaced with fetch_live_dataset().
  Live data is now sourced entirely from yfinance BTC-USD prices.
  The Trolololo indicator is computed independently via compute_trolololo()
  (core/trolololo.py), eliminating dependency on the CBBI API and
  Index Revision Bias.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import yfinance as yf

from core.trolololo import compute_trolololo

# ── Paths ─────────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH  = _ROOT / "data" / "master_dataset.parquet"
RESULTS_PATH  = _ROOT / "data" / "optimal_params_summary.json"
TRIAL_LOG_DIR = _ROOT / "data" / "trial_log"

SCENARIO_1_LOG = TRIAL_LOG_DIR / "scenario_1_grid_search_in_sample.parquet"
SCENARIO_2_LOG = TRIAL_LOG_DIR / "scenario_2_grid_search_full.parquet"


@st.cache_data(ttl=43200, show_spinner=False)  # Cache for 12 hours
def load_smart_dataset() -> pd.DataFrame:
    """
    Hybrid Data Pipeline (Smart Appending):
    1. Loads the massive static master_dataset.parquet (2012 to 2026-03-15).
    2. Checks the last date in the static dataset.
    3. Fetches ONLY the missing daily BTC-USD prices from Yahoo Finance up to today.
    4. Computes Trolololo for the entire combined price history instantly.
    5. Caches the result so it's lightning fast for 12 hours.

    This removes the need for users to choose between "Historical" and "Live" modes,
    providing a seamless, always-up-to-date experience.
    """
    # 1. Load static historical data
    df_static = pd.read_parquet(DATASET_PATH)
    if not isinstance(df_static.index, pd.DatetimeIndex):
        df_static.index = pd.to_datetime(df_static.index)
    
    last_date = df_static.index.max()

    # 2. Fetch the delta (missing days)
    # Add a day to start_date to avoid fetching the overlapping day, though yfinance handles dates flexibly
    start_fetch = (last_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    
    try:
        raw_new = yf.download("BTC-USD", start=start_fetch, auto_adjust=True, progress=False)
        
        if not raw_new.empty:
            if isinstance(raw_new.columns, pd.MultiIndex):
                raw_new.columns = raw_new.columns.get_level_values(0)
            
            raw_new.index = pd.to_datetime(raw_new.index).tz_localize(None)
            raw_new = raw_new.sort_index()
            
            df_new = pd.DataFrame(index=raw_new.index)
            df_new["btc_close"] = raw_new["Close"].squeeze()
            df_new["btc_open"]  = raw_new["Open"].squeeze()
            
            # Combine static and new (only for overlapping columns needed for simulation)
            # Other CBBI columns (pi_cycle, etc.) will naturally become NaN or we can ffill them.
            # We don't trade on them, so it's fine.
            df_combined = pd.concat([df_static, df_new])
            
            # 3. Compute Trolololo across the whole timeline
            # Trolololo is independent, so it computes instantly
            df_combined["trolololo"] = compute_trolololo(df_combined["btc_close"].dropna())
            
            # Fill down other indicators purely for cosmetic charts if needed
            df_combined = df_combined.ffill()
            
            return df_combined
            
    except Exception as e:
        # Graceful fallback: If yfinance is down or rate-limited, just return static dataset.
        print(f"Failed to fetch live delta data: {e}. Falling back to static dataset.")
    
    return df_static



def get_dataset_slice(
    df: pd.DataFrame,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Return date-filtered slice of the master dataset."""
    mask = (df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))
    return df.loc[mask].copy()


@st.cache_data(show_spinner=False)
def load_research_results() -> dict:
    """Load optimal_params_summary.json (Phase 3 output)."""
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner="Loading Scenario 1 trial log...")
def load_scenario1_log() -> pd.DataFrame:
    """Load Scenario 1 (IS) trial log. Cached after first access."""
    return pd.read_parquet(SCENARIO_1_LOG)


@st.cache_data(show_spinner="Loading Scenario 2 trial log...")
def load_scenario2_log() -> pd.DataFrame:
    """Load Scenario 2 (Full) trial log. Cached after first access."""
    return pd.read_parquet(SCENARIO_2_LOG)


def build_heatmap_matrix(
    trial_log: pd.DataFrame,
    metric: str = "total_return",
) -> pd.DataFrame:
    """
    Aggregate trial log into a (buy_threshold x sell_threshold) pivot matrix
    by taking the max of `metric` across all allocation combinations.

    Returns a DataFrame suitable for px.imshow().
    Rows = sell threshold (55–100), Columns = buy threshold (1–45).
    """
    buy_col  = "threshold_buy"
    sell_col = "threshold_sell"

    pivot = (
        trial_log
        .groupby([buy_col, sell_col])[metric]
        .max()
        .reset_index()
        .pivot(index=sell_col, columns=buy_col, values=metric)
        .sort_index(ascending=False)   # sell threshold: high at top
    )
    return pivot


def get_dataset_date_range(df: pd.DataFrame) -> tuple[str, str]:
    """Return (min_date_str, max_date_str) of the dataset."""
    return str(df.index.min().date()), str(df.index.max().date())
