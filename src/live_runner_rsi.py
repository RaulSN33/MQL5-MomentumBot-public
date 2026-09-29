"""
Single-symbol live runner for the RSI14-pullback entry variant
(src/strategy_rsi_entry.py).

Identical to src/live_runner.py except it injects the RSI `compute_signal`
and uses a distinct MAGIC, so it can run alongside the EMA-cross bot on
the same symbol without the two fighting over one position.
"""
from __future__ import annotations

import time

from src import mt5_connector
from src import risk
from src.runner_core import run_symbol_once, seconds_until_next_poll
from src.strategy_rsi_entry import compute_signal as rsi_compute_signal

SYMBOL = "BTCUSD"
MAGIC = 20261001  # distinct from live_runner.MAGIC (20260823) / portfolio base (20260900)
SETTINGS = risk.parse_settings(SYMBOL, {"lot": 0.05, "sl_pips": 3000, "pip_size": 1.0})

_cooldown = risk.Cooldown()


def run_once() -> None:
    run_symbol_once(
        SYMBOL, SETTINGS, MAGIC, _cooldown, compute_signal_fn=rsi_compute_signal
    )


def main() -> None:
    mt5_connector.connect()
    print(f"Connected. Trading {SYMBOL} (RSI pullback) at {SETTINGS.lot} lots, magic={MAGIC}.")

    try:
        while True:
            wait = seconds_until_next_poll()
            time.sleep(wait)

            try:
                run_once()
            except Exception as exc:
                print(f"Error during run_once: {exc}")

    except KeyboardInterrupt:
        print("\nStopped.")

    finally:
        mt5_connector.disconnect()


if __name__ == "__main__":
    main()
