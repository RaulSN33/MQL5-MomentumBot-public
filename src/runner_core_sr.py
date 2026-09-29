"""
Entry / trade-management orchestration for the S/R break-and-retest strategy
(src/strategy_sr_entry.py).

Separate from src/runner_core.py: 15min trigger and a per-trade dynamic stop
AND target attached broker-side.

Exits are the broker SL/TP. While a position is open the only thing this runner
does is ratchet the stop forward (never loosen it) when the strategy proposes
a better level. A fresh setup that appears while a position is open is skipped.
"""
from __future__ import annotations

import csv
import os
from datetime import datetime, timedelta, timezone

import MetaTrader5 as mt5

from src import execution
from src import mt5_connector
from src.ohlc_data import OHLCData
from src.strategy_sr_entry import (
    TRAIL_START_ATR,
    USE_TRAILING_STOP,
    compute_signal,
)

N_BARS = 43_200  # ~30 days of 1-min bars; plenty for the 15min zone history
POLL_BUFFER_SECONDS = 10
TRIGGER_MINUTES = 15

SIGNAL_LOG_PATH = "signal_log_sr.csv"
SIGNAL_LOG_FIELDS = [
    "logged_at", "symbol", "bar_timestamp", "signal", "state",
    "long_entry", "short_entry", "sl_price", "tp_price", "rr", "reject",
    "atr", "action",
]


def seconds_until_next_poll(trigger_minutes: int = TRIGGER_MINUTES) -> float:
    now = datetime.now()
    next_bucket_minute = (now.minute // trigger_minutes + 1) * trigger_minutes
    next_run = now.replace(second=0, microsecond=0) + timedelta(
        minutes=next_bucket_minute - now.minute
    )
    next_run += timedelta(seconds=POLL_BUFFER_SECONDS)
    return (next_run - now).total_seconds()


def _digits(symbol: str) -> int:
    info = mt5.symbol_info(symbol)
    return info.digits if info is not None else 5


def _min_stop_distance(symbol: str) -> float:
    info = mt5.symbol_info(symbol)
    if info is None:
        return 0.0
    return (info.trade_stops_level or 0) * info.point


def _finalise_levels(
    symbol: str, direction: str, ref: float, sl: float, tp: float
) -> tuple[float, float]:
    """
    Round SL/TP to the symbol's digits and push each out to at least the
    broker's minimum stop distance from the entry reference. Levels only move
    AWAY from price here, never closer.
    """
    digits = _digits(symbol)
    min_dist = _min_stop_distance(symbol)

    if direction == "long":
        sl = min(sl, ref - min_dist)
        tp = max(tp, ref + min_dist)
    else:
        sl = max(sl, ref + min_dist)
        tp = min(tp, ref - min_dist)

    return round(sl, digits), round(tp, digits)


def log_signal(symbol: str, signal: dict, action: str) -> None:
    is_new_file = not os.path.exists(SIGNAL_LOG_PATH)
    with open(SIGNAL_LOG_PATH, mode="a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SIGNAL_LOG_FIELDS)
        if is_new_file:
            writer.writeheader()
        writer.writerow({
            "logged_at": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "bar_timestamp": signal["timestamp"],
            "signal": signal["signal"],
            "state": signal["state"],
            "long_entry": signal["long_entry"],
            "short_entry": signal["short_entry"],
            "sl_price": signal["sl_price"],
            "tp_price": signal["tp_price"],
            "rr": signal["rr"],
            "reject": signal["reject"],
            "atr": signal["atr"],
            "action": action,
        })


def _skip_reason(signal: dict) -> str:
    """Why a non-zero signal did not become an entry (for the log)."""
    return f"skip_{signal['reject']}" if signal["reject"] else "none"


def _maybe_trail(symbol: str, position, signal: dict) -> str:
    """Ratchet the broker stop forward to the strategy's trail level. Returns an action."""
    if not USE_TRAILING_STOP or signal["atr"] in (None, 0):
        return "hold"

    is_long = position.type == mt5.POSITION_TYPE_BUY
    cand = signal["trail_sl_long"] if is_long else signal["trail_sl_short"]
    if cand is None:
        return "hold"

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return "hold"
    px = tick.bid if is_long else tick.ask

    onside = (
        (px - position.price_open) if is_long else (position.price_open - px)
    )
    if onside < TRAIL_START_ATR * signal["atr"]:
        return "hold"

    digits = _digits(symbol)
    min_dist = _min_stop_distance(symbol)
    cand = round(cand, digits)
    cur = position.sl or 0.0

    improves = (
        (is_long and cand > cur and cand <= px - min_dist)
        or (not is_long and (cur == 0.0 or cand < cur) and cand >= px + min_dist)
    )
    if not improves:
        return "hold"

    execution.modify_position_sl(position, cand)
    return "trail_sl"


def run_symbol_once(
    symbol: str,
    lot: float,
    magic: int,
    zone_width: float,
    n_bars: int = N_BARS,
    compute_signal_fn=compute_signal,
) -> None:
    raw = mt5_connector.fetch_ohlc(symbol, n_bars)
    ohlc = OHLCData(raw)
    signal = compute_signal_fn(ohlc, zone_width=zone_width)
    bar_ts = signal["timestamp"]

    position = execution.get_open_position(symbol, magic)
    action = "none"

    wants_entry = signal["long_entry"] or signal["short_entry"]
    direction = "long" if signal["long_entry"] else "short"

    if position is not None:
        action = _maybe_trail(symbol, position, signal)
        if action == "hold" and (wants_entry or signal["signal"] != 0):
            action = "skip_in_position"
    elif signal["signal"] != 0 and not wants_entry:
        action = _skip_reason(signal)
    elif wants_entry:
        tick = mt5.symbol_info_tick(symbol)
        ref = tick.ask if direction == "long" else tick.bid
        sl, tp = _finalise_levels(
            symbol, direction, ref, signal["sl_price"], signal["tp_price"]
        )
        execution.send_market_order(
            symbol, direction, lot, magic,
            sl_price=sl, tp_price=tp, comment="sr_retest entry",
        )
        signal = {**signal, "sl_price": sl, "tp_price": tp}
        action = f"entry_{direction}"

    log_signal(symbol, signal, action)

    atr_now = signal["atr"]
    atr_str = "n/a" if atr_now is None else f"{atr_now:.5g}"
    rr = signal["rr"]
    rr_str = "n/a" if rr is None else f"{rr:.2f}"
    print(
        f"[{symbol}] [{bar_ts}] sig={signal['signal']} state={signal['state']} "
        f"atr={atr_str} rr={rr_str} "
        f"sl={signal['sl_price']} tp={signal['tp_price']} -> {action}"
    )
