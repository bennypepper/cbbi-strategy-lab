"""
core/data_loader.py
===================
Data loading helpers with Streamlit cache decorators.
All paths are relative to the repo root (data/).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import requests

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


@st.cache_data(ttl=3600, show_spinner="Fetching Live CBBI Data...")
def fetch_cbbi_live() -> pd.DataFrame:
    """
    Fetch the latest CBBI data from colintalkscrypto API once per hour.
    Returns a DataFrame formatted exactly like the master_dataset.
    """
    url = "https://colintalkscrypto.com/cbbi/data/latest.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://colintalkscrypto.com/cbbi/"
    }
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    
    # The API returns dictionary objects where the keys are Unix timestamps.
    # Convert 'Price' -> 'btc_open', 'Confidence' -> 'trolololo'
    # Colin's 'Confidence' is the CBBI index score (which we call trolololo in our dataset)
    price_series = pd.Series(data.get("Price", {}), name="btc_open")
    cbbi_series = pd.Series(data.get("Confidence", {}), name="trolololo")
    
    # Combine them
    df = pd.concat([price_series, cbbi_series], axis=1)
    
    # The index is string unix timestamps, we must convert it to DatetimeIndex
    df.index = pd.to_datetime(df.index.astype(int), unit='s')
    
    # Filter to match our standard starting point of 2012 generally or keep all
    df = df.sort_index()
    df["btc_close"] = df["btc_open"]
    return df



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
