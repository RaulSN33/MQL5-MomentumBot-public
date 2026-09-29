"""
Oscillator-based entry variant -- PRIVATE.

Drop-in alternative to src/strategy.py: same execution path, different entry
trigger. Selected via config/pairs.py STRATEGY = "rsi_pullback".
"""
from __future__ import annotations

from src.ohlc_data import OHLCData


def compute_signal(ohlc: OHLCData) -> dict:
    """Same contract as src/strategy.py::compute_signal."""
    raise NotImplementedError("Strategy logic is private and not included in this repository.")
