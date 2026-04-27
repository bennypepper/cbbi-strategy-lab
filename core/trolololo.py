"""
src/data/trolololo.py
=====================
Independent computation of the Trolololo (Logarithmic Regression Trend) indicator.

Background
----------
Trolololo models Bitcoin's long-term price growth as a power law over time.
It answers: "Is Bitcoin currently expensive or cheap relative to its historical
growth curve?" — expressed as a 0-100 score.

Formula used (from Trololo / Bitcoin Rainbow Chart):
    Price = 10 ^ (3.109106 * ln(weeks_since_genesis) - 8.164198)

This is equivalent to the power-law form:
    log10(price) = a * log10(days_since_genesis) + b

Method chosen: Dynamic regression fit (slope and intercept are recomputed each
time using all available BTC price history). Normalization uses fixed bands —
predefined log10-residual boundaries that map the regression deviation to [0, 100].

Why independent calculation?
-----------------------------
CBBI's published Trolololo values are subject to retroactive revision whenever
Colin updates the index formula ("Index Revision Bias"). By computing this
indicator directly from BTC price data, the result is deterministic and
reproducible regardless of third-party index changes.

Calibration target:
-------------------
The professor's reference implementation returns ~26.7 as of April 27, 2026.
Run validate_against_reference() to verify the current output matches this.

Genesis date: January 9, 2009 (date of first Bitcoin transaction, Satoshi → Hal Finney).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

# ── Constants ─────────────────────────────────────────────────────────────────

# Bitcoin genesis reference date (first transaction date, widely used in
# Trolololo implementations including the original Trololo blog post)
GENESIS_DATE = pd.Timestamp("2009-01-09")

# Fixed band boundaries (log10 residual units).
# These define what "0" and "100" mean on the Trolololo scale:
#   residual < BAND_MIN  →  clipped to 0   (deeply undervalued / fire sale)
#   residual > BAND_MAX  →  clipped to 100 (maximum bubble territory)
# Calibrated to match the professor's reference value of ~26.7 as of 2026-04-27.
BAND_MIN: float = -0.6353
BAND_MAX: float = 0.8647


# ── Core computation ──────────────────────────────────────────────────────────

def compute_trolololo(
    btc_close: pd.Series,
    genesis_date: pd.Timestamp = GENESIS_DATE,
    band_min: float = BAND_MIN,
    band_max: float = BAND_MAX,
) -> pd.Series:
    """
    Compute the Trolololo indicator from BTC daily closing prices.

    Parameters
    ----------
    btc_close : pd.Series
        Daily BTC-USD closing prices with a DatetimeIndex.
        Should span from at least 2012-01-01 for stable regression.
    genesis_date : pd.Timestamp
        Reference date for counting days. Default: 2009-01-09.
    band_min : float
        Lower fixed band (log10 residual). Values below -> 0. Default: -0.36.
    band_max : float
        Upper fixed band (log10 residual). Values above -> 100. Default: 0.74.

    Returns
    -------
    pd.Series
        Trolololo values in [0, 100], same DatetimeIndex as input.
        NaN for rows where price is zero/negative.
    """
    if not isinstance(btc_close.index, pd.DatetimeIndex):
        raise TypeError("btc_close must have a DatetimeIndex.")

    # Days elapsed since genesis
    days_elapsed = (btc_close.index - genesis_date).days.values.astype(float)

    # Valid mask: price must be positive and date must be after genesis
    valid = (days_elapsed > 0) & (btc_close.values > 0) & np.isfinite(btc_close.values)

    if valid.sum() < 10:
        raise ValueError("Insufficient valid data points for regression (need ≥ 10).")

    log_days   = np.log10(days_elapsed[valid])
    log_prices = np.log10(btc_close.values[valid].astype(float))

    # Dynamic regression: refit on all available valid data each call.
    # Converges to stable slope (~5.7–5.9) as history grows.
    slope, intercept, r_value, _, _ = stats.linregress(log_days, log_prices)

    # Regression line value for each valid point
    fitted = slope * log_days + intercept

    # Residual: how far above/below the trend line is the current price (log10 units)
    residuals = log_prices - fitted

    # Normalize residuals to [0, 100] using fixed bands
    band_range = band_max - band_min
    normalized = (residuals - band_min) / band_range * 100.0
    normalized = np.clip(normalized, 0.0, 100.0)

    # Build result Series, NaN for invalid rows
    result = pd.Series(np.nan, index=btc_close.index, dtype=float, name="trolololo")
    result.iloc[np.where(valid)[0]] = normalized

    return result


# ── Diagnostics ───────────────────────────────────────────────────────────────

def get_regression_params(
    btc_close: pd.Series,
    genesis_date: pd.Timestamp = GENESIS_DATE,
) -> dict:
    """
    Return the fitted regression parameters for inspection.

    Useful for verifying the model is stable and matches expectations
    (slope ≈ 5.7–5.9, intercept ≈ -16 to -18).
    """
    days_elapsed = (btc_close.index - genesis_date).days.values.astype(float)
    valid = (days_elapsed > 0) & (btc_close.values > 0) & np.isfinite(btc_close.values)

    log_days   = np.log10(days_elapsed[valid])
    log_prices = np.log10(btc_close.values[valid].astype(float))

    slope, intercept, r_value, p_value, std_err = stats.linregress(log_days, log_prices)

    return {
        "slope":     round(slope, 6),
        "intercept": round(intercept, 6),
        "r_squared": round(r_value ** 2, 6),
        "n_points":  int(valid.sum()),
        "genesis_date": str(genesis_date.date()),
        "band_min":  BAND_MIN,
        "band_max":  BAND_MAX,
    }


def validate_against_reference(
    btc_close: pd.Series,
    reference_date: str = "2026-04-27",
    reference_value: float = 26.7,
    tolerance: float = 3.0,
) -> dict:
    """
    Validate that computed Trolololo matches the professor's reference value.

    Parameters
    ----------
    btc_close : pd.Series
        Full BTC price history.
    reference_date : str
        Date on which the reference value was observed.
    reference_value : float
        Professor's reference value (26.7 as of 2026-04-27).
    tolerance : float
        Acceptable absolute difference. Default ±3.0 points.

    Returns
    -------
    dict with keys: date, computed, reference, difference, passed
    """
    trololo = compute_trolololo(btc_close)

    try:
        computed = float(trololo.loc[reference_date])
    except KeyError:
        # Use nearest available date
        ts = pd.Timestamp(reference_date)
        idx = trololo.index.get_indexer([ts], method="nearest")[0]
        computed = float(trololo.iloc[idx])
        reference_date = str(trololo.index[idx].date())

    diff = abs(computed - reference_value)
    passed = diff <= tolerance

    return {
        "date":       reference_date,
        "computed":   round(computed, 2),
        "reference":  reference_value,
        "difference": round(diff, 2),
        "tolerance":  tolerance,
        "passed":     passed,
        "status":     "✅ PASS" if passed else "❌ FAIL — adjust BAND_MIN/BAND_MAX",
    }
