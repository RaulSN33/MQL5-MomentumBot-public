"""
Support/resistance break-and-retest strategy -- PRIVATE.

The implementation and its tuned parameters are not part of the public
showcase. This stub documents the contract used by src/runner_core_sr.py.
"""
from __future__ import annotations

from src.ohlc_data import OHLCData

TRIGGER_TIMEFRAME = "15min"

USE_TRAILING_STOP = False
TRAIL_START_ATR = 0.0


def compute_signal(ohlc: OHLCData, *, zone_width: float) -> dict:
    """
    Evaluate the last fully closed trigger bar.

    Args:
        ohlc:       1-minute MT5 history wrapped in OHLCData.
        zone_width: per-symbol price width used to build S/R zones.

    Returns a dict with at least:
        timestamp       pd.Timestamp
        signal          int            raw setup direction (1 / -1 / 0)
        state           str            internal state-machine label
        long_entry      bool
        short_entry     bool
        sl_price        float | None   broker-side stop for a fresh entry
        tp_price        float | None   broker-side target for a fresh entry
        rr              float | None   reward:risk of the proposed trade
        reject          str | None     why a setup was filtered out
        atr             float | None
        trail_sl_long   float | None   candidate trailing stop for longs
        trail_sl_short  float | None   candidate trailing stop for shorts
    """
    raise NotImplementedError("Strategy logic is private and not included in this repository.")
