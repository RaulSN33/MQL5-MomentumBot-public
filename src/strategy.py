"""
Trend-following entry strategy -- PRIVATE.

The implementation is not part of the public showcase. This stub documents
the contract the runners (src/runner_core.py, src/portfolio_runner.py) rely
on, so the rest of the architecture stays readable and importable.
"""
from __future__ import annotations

from src.ohlc_data import OHLCData


def compute_signal(ohlc: OHLCData) -> dict:
    """
    Evaluate the last fully closed trigger bar and return a signal dict.

    Args:
        ohlc: 1-minute MT5 history wrapped in OHLCData; the strategy resamples
              it to whatever timeframes it needs.

    Returns a dict with at least:
        timestamp    pd.Timestamp  close time of the evaluated trigger bar
        signal       int           raw trigger value (1 / -1 / 0)
        long_entry   bool          open a long if flat
        short_entry  bool          open a short if flat
        long_exit    bool          close an open long
        short_exit   bool          close an open short
        is_choppy    bool          market-regime filter: suppress entries/exits
        atr          float | None  current volatility, for logging
    """
    raise NotImplementedError("Strategy logic is private and not included in this repository.")
