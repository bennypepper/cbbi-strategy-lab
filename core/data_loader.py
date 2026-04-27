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


@st.cache_data(show_spinner=False)
def load_master_dataset() -> pd.DataFrame:
    """
    Load master_dataset.parquet and cache for the entire session.
    DatetimeIndex, all CBBI indicators + btc_open/close columns.
    """
    df = pd.read_parquet(DATASET_PATH)
    # Ensure DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    return df


@st.cache_data(ttl=3600, show_spinner="Fetching live BTC data...")
def fetch_live_dataset() -> pd.DataFrame:
    """
    Fetch current BTC-USD prices from Yahoo Finance and compute Trolololo
    independently using logarithmic regression (core/trolololo.py).

    No dependency on the CBBI API. Eliminates Index Revision Bias.
    Cached for 1 hour (ttl=3600).

    Returns a DataFrame with DatetimeIndex and at minimum:
      - btc_close  : BTC daily close price
      - btc_open   : BTC daily open price (same as close for live rows)
      - trolololo  : independently computed Trolololo [0-100]
    """
    raw = yf.download("BTC-USD", start="2012-01-01", auto_adjust=True, progress=False)
    if raw.empty:
        raise RuntimeError("yfinance returned no data for BTC-USD.")

    # Flatten MultiIndex columns if present (yfinance >= 0.2.x)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    # Ensure timezone-naive DatetimeIndex
    raw.index = pd.to_datetime(raw.index).tz_localize(None)
    raw = raw.sort_index()

    df = pd.DataFrame(index=raw.index)
    df["btc_close"] = raw["Close"].squeeze()
    df["btc_open"]  = raw["Open"].squeeze()

    # Compute Trolololo independently from BTC close prices
    df["trolololo"] = compute_trolololo(df["btc_close"].dropna().reindex(df.index))

    df = df.dropna(subset=["btc_close"])
    return df


# Backward-compatibility alias — remove after all callers are updated
def fetch_cbbi_live() -> pd.DataFrame:
    """Deprecated: use fetch_live_dataset() instead."""
    return fetch_live_dataset()



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
