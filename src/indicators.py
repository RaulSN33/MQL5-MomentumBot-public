from __future__ import annotations

import numpy as np
import pandas as pd


def ema(
    df: pd.DataFrame,
    column: str,
    window: int,
) -> pd.Series:
    return df[column].ewm(span=window, adjust=False).mean()


def ema_trend(
    df: pd.DataFrame,
    fast: str,
    slow: str,
) -> pd.Series:
    """
    1 Uptrend
    0 Downtrend
    """
    helper = df["Close"].to_frame()
    helper["trend"] = np.where(
        df[fast] > df[slow],
        1,
        0,
    )
    return helper["trend"]


def ema_cross_signal(df: pd.DataFrame) -> pd.Series:
    return df["trend"].diff()


def atr(
    df: pd.DataFrame,
    window: int = 14,
) -> pd.Series:
    """
    Wilder's Average True Range. Volatility-normalises thresholds so a
    single setting works across BTC / FX / metals.
    """
    high = df["High"]
    low = df["Low"]
    prev_close = df["Close"].shift(1)

    true_range = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return true_range.ewm(alpha=1 / window, adjust=False).mean()


def rsi(
    df: pd.DataFrame,
    column: str = "Close",
    window: int = 14,
) -> pd.Series:
    """
    Wilder's Relative Strength Index. Uses the same `ewm(alpha=1/window)`
    smoothing as `atr` above, so this matches the classic MT5 / TradingView
    RSI rather than a plain rolling mean.

    Edge cases:
      * avg_loss == 0 (pure gains over the window) -> RSI = 100
      * avg_gain == avg_loss == 0 (perfectly flat)  -> RSI = 50 (neutral)
      * first row (no diff available)               -> NaN
    """
    delta = df[column].diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    avg_gain = gain.ewm(alpha=1 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False).mean()

    rs = avg_gain / avg_loss
    out = 100.0 - 100.0 / (1.0 + rs)

    out = out.where(avg_loss != 0, 100.0)
    out = out.where(~((avg_gain == 0) & (avg_loss == 0)), 50.0)
    if len(out):
        out.iloc[0] = np.nan

    return out
