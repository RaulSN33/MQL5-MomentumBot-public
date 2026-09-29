from __future__ import annotations

import csv
import os
from datetime import datetime, timedelta, timezone

import MetaTrader5 as mt5

from src import mt5_connector
from src import execution
from src import risk
from src.ohlc_data import OHLCData
from src.strategy import compute_signal

N_BARS = 43_200  # ~30 days of 1-min bars, enough history for higher-timeframe indicators
POLL_BUFFER_SECONDS = 10  # wait a bit past the 5-min mark for MT5 to publish the closed bar

SIGNAL_LOG_PATH = "signal_log.csv"
SIGNAL_LOG_FIELDS = [
    "logged_at", "symbol", "bar_timestamp", "signal",
    "long_entry", "short_entry", "long_exit", "short_exit", "position",
    "action", "is_choppy", "atr",
]


def log_signal(symbol: str, signal: dict, position_state: str, action: str) -> None:
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
            "long_entry": signal["long_entry"],
            "short_entry": signal["short_entry"],
            "long_exit": signal["long_exit"],
            "short_exit": signal["short_exit"],
            "position": position_state,
            "action": action,
            "is_choppy": signal["is_choppy"],
            "atr": signal["atr"],
        })


def seconds_until_next_poll() -> float:
    now = datetime.now()
    next_bucket_minute = (now.minute // 5 + 1) * 5
    next_run = now.replace(second=0, microsecond=0) + timedelta(
        minutes=next_bucket_minute - now.minute
    )
    next_run += timedelta(seconds=POLL_BUFFER_SECONDS)

    return (next_run - now).total_seconds()


def _open_with_stop(
    symbol: str,
    direction: str,
    settings: risk.PairSettings,
    magic: int,
) -> None:
    dist = risk.stop_distance(settings)
    tick = mt5.symbol_info_tick(symbol)
    ref = tick.ask if direction == "long" else tick.bid
    sl = risk.stop_price(symbol, direction, ref, dist)
    execution.send_market_order(symbol, direction, settings.lot, magic, sl_price=sl)


def run_symbol_once(
    symbol: str,
    settings: risk.PairSettings,
    magic: int,
    cooldown: risk.Cooldown,
    n_bars: int = N_BARS,
    compute_signal_fn=compute_signal,
) -> None:
    raw = mt5_connector.fetch_ohlc(symbol, n_bars)
    ohlc = OHLCData(raw)
    signal = compute_signal_fn(ohlc)
    bar_ts = signal["timestamp"]

    position = execution.get_open_position(symbol, magic)
    position_state = "flat"
    action = "none"

    if position is None:
        wants_entry = signal["long_entry"] or signal["short_entry"]
        direction = "long" if signal["long_entry"] else "short"

        if wants_entry and signal["is_choppy"]:
            action = "entry_skipped_chop"
        elif wants_entry and cooldown.is_blocked(symbol, bar_ts):
            action = "entry_skipped_cooldown"
        elif wants_entry:
            _open_with_stop(symbol, direction, settings, magic)
            position_state = direction
            action = f"entry_{direction}"
    else:
        is_long = position.type == mt5.POSITION_TYPE_BUY
        position_state = "long" if is_long else "short"
        wants_exit = (is_long and signal["long_exit"]) or (
            not is_long and signal["short_exit"]
        )

        if risk.stop_breached(position, settings):
            execution.close_position(position, reason="exit_stop")
            cooldown.record_exit(symbol, bar_ts)
            position_state = "flat"
            action = "exit_stop"
        elif wants_exit and signal["is_choppy"]:
            action = "exit_suppressed_chop"
        elif wants_exit:
            execution.close_position(position, reason="exit")
            cooldown.record_exit(symbol, bar_ts)
            position_state = "flat"
            action = f"exit_{'long' if is_long else 'short'}"

    log_signal(symbol, signal, position_state, action)

    atr_now = signal["atr"]
    atr_str = "n/a" if atr_now is None else f"{atr_now:.5g}"

    print(f"[{symbol}] [{bar_ts}] signal={signal['signal']} "
          f"atr={atr_str} chop={signal['is_choppy']} "
          f"action={action} -> {position_state}")