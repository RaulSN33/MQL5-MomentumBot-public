"""
Per-trade risk controls layered on top of any signal strategy:

  * per-asset hard stop-loss (broker-side `sl` on the order, plus a
    bot-side reconcile every poll in case the broker SL is missing)
  * a re-entry cooldown so a symbol that was just closed can't be
    re-entered for a few bars -- kills the in/out/in/out churn during
    sideways stretches.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import MetaTrader5 as mt5

COOLDOWN_BARS = 3               # bars to block re-entry after a close
TRIGGER_TF = pd.Timedelta("5min")

REQUIRED_KEYS = ("lot", "sl_pips")


@dataclass(frozen=True)
class PairSettings:
    symbol: str
    lot: float
    sl_pips: float
    pip_size_override: float | None = None


def parse_settings(symbol: str, raw) -> PairSettings:
    """
    Accepts the settings dict from config/pairs.py. Kept lenient enough to
    also swallow a bare float (old config shape) so nothing explodes on a
    half-migrated config -- but sl_pips is then unknown and stops are off.
    """
    if isinstance(raw, (int, float)):
        return PairSettings(symbol=symbol, lot=float(raw), sl_pips=0.0)

    missing = [k for k in REQUIRED_KEYS if k not in raw]
    if missing:
        raise KeyError(f"{symbol}: config/pairs.py entry missing {missing}")

    return PairSettings(
        symbol=symbol,
        lot=float(raw["lot"]),
        sl_pips=float(raw["sl_pips"]),
        pip_size_override=(
            float(raw["pip_size"]) if raw.get("pip_size") is not None else None
        ),
    )


def resolve_pip_size(settings: PairSettings) -> float:
    """
    Explicit override wins. Otherwise use the FX convention: 1 pip is the
    last whole digit before the fractional pipette, i.e. point * 10 for
    5-digit / 3-digit quotes, point * 1 otherwise.
    """
    if settings.pip_size_override is not None:
        return settings.pip_size_override

    info = mt5.symbol_info(settings.symbol)
    if info is None:
        raise RuntimeError(
            f"{settings.symbol}: mt5.symbol_info returned None; "
            f"set an explicit pip_size in config/pairs.py"
        )

    factor = 10 if info.digits in (3, 5) else 1
    return info.point * factor


def stop_distance(settings: PairSettings) -> float:
    """Stop-loss distance in price units. 0.0 disables the stop."""
    if settings.sl_pips <= 0:
        return 0.0
    return settings.sl_pips * resolve_pip_size(settings)


def stop_price(symbol: str, direction: str, ref_price: float, dist: float) -> float | None:
    """
    Broker-side SL price for a fresh entry, clamped to the symbol's minimum
    stop distance and rounded to its digits. `direction` is "long"/"short".
    """
    if dist <= 0:
        return None

    info = mt5.symbol_info(symbol)
    if info is not None:
        min_dist = (info.trade_stops_level or 0) * info.point
        dist = max(dist, min_dist)
        digits = info.digits
    else:
        digits = 5

    raw = ref_price - dist if direction == "long" else ref_price + dist
    return round(raw, digits)


def stop_breached(position, settings: PairSettings) -> bool:
    """
    True when the live price has traded through the stop. Prefers the
    broker-side SL stored on the position; falls back to recomputing from
    the entry price if the position has no SL attached.
    """
    is_long = position.type == mt5.POSITION_TYPE_BUY

    level = position.sl if position.sl and position.sl > 0 else None
    if level is None:
        dist = stop_distance(settings)
        if dist <= 0:
            return False
        level = (
            position.price_open - dist
            if is_long
            else position.price_open + dist
        )

    tick = mt5.symbol_info_tick(position.symbol)
    if tick is None:
        return False
    price = tick.bid if is_long else tick.ask

    return price <= level if is_long else price >= level


class Cooldown:
    """
    Tracks the bar timestamp until which each symbol is blocked from
    re-entry. In-memory only -- a bot restart clears it, which at worst
    allows one early re-entry.
    """

    def __init__(self, bars: int = COOLDOWN_BARS):
        self._blocked_until: dict[str, pd.Timestamp] = {}
        self._delta = bars * TRIGGER_TF

    def record_exit(self, symbol: str, bar_ts: pd.Timestamp) -> None:
        self._blocked_until[symbol] = bar_ts + self._delta

    def is_blocked(self, symbol: str, bar_ts: pd.Timestamp) -> bool:
        until = self._blocked_until.get(symbol)
        return until is not None and bar_ts < until
