from __future__ import annotations

import time

from src import mt5_connector
from src import risk
from src.runner_core import run_symbol_once, seconds_until_next_poll

SYMBOL = "BTCUSD"
MAGIC = 20260823
SETTINGS = risk.parse_settings(SYMBOL, {"lot": 0.05, "sl_pips": 3000, "pip_size": 1.0})

_cooldown = risk.Cooldown()


def run_once() -> None:
    run_symbol_once(SYMBOL, SETTINGS, MAGIC, _cooldown)


def main() -> None:
    mt5_connector.connect()
    print(f"Connected. Trading {SYMBOL} at {SETTINGS.lot} lots, magic={MAGIC}.")

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
