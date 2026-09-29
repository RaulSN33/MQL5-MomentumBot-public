"""
Template for config/pairs.py (copy it: `cp config/pairs.example.py config/pairs.py`).
The real, tuned config is private and gitignored.

Keys must match the exact symbol name shown in your broker's MT5 Market
Watch (suffixes like ".a" / "m" vary by broker).

Each value is a settings dict:

    "lot"         fixed lot size to trade for that symbol (required)
    "sl_pips"     hard stop-loss distance from entry, in pips (required)
    "pip_size"    price value of 1 pip (optional). Leave it out for real FX
                  pairs -- it's derived from the symbol's point size
                  (point * 10 for 5-digit / 3-digit quotes). Set it
                  explicitly for crypto / metals / energy.
    "zone_width"  S/R zone width in price units (only used by the
                  sr_retest runner).

All values below are placeholders, not trading recommendations.
"""
from __future__ import annotations

# Which strategy src/portfolio_runner.py runs for every pair below:
#   "ema_cross"    -> src/strategy.py
#   "rsi_pullback" -> src/strategy_rsi_entry.py
STRATEGY = "ema_cross"

PAIRS: dict[str, dict] = {
    "EURUSD": {"lot": 0.01, "sl_pips": 50, "zone_width": 0.0010},
    "XAUUSD": {"lot": 0.01, "sl_pips": 300, "pip_size": 0.1, "zone_width": 2.0},
}
