"""
Live runner for the S/R break-and-retest strategy over every symbol in
config/pairs.py.

Polls once per closed 15min bar (+10s). Uses its own MAGIC_BASE range so it
never collides with the other runners (src/live_runner.py magic 20260823,
src/portfolio_runner.py base 20260900). Do NOT run this on a symbol that
another runner is already trading -- you'd get double exposure.

`lot` and `zone_width` are read from each config entry; `sl_pips` / `pip_size`
are ignored (the strategy supplies a dynamic stop and target per trade).
"""
from __future__ import annotations

import time

from src import mt5_connector
from src.runner_core_sr import run_symbol_once, seconds_until_next_poll

MAGIC_BASE = 20260950  # distinct from live_runner (20260823) and portfolio_runner (20260900+)


def build_magic_map(pairs: dict) -> dict[str, int]:
    return {symbol: MAGIC_BASE + i for i, symbol in enumerate(pairs)}


def run_cycle(
    lot_map: dict[str, float],
    magic_map: dict[str, int],
    zone_width_map: dict[str, float],
) -> None:
    for symbol, lot in lot_map.items():
        try:
            run_symbol_once(symbol, lot, magic_map[symbol], zone_width_map[symbol])
        except Exception as exc:
            print(f"[{symbol}] Error during run_symbol_once: {exc}")


def main() -> None:
    from config.pairs import PAIRS

    if not PAIRS:
        print("config/pairs.py has no pairs configured. Add symbols, then rerun.")
        return

    missing_zone_width = [s for s, raw in PAIRS.items() if "zone_width" not in raw]
    if missing_zone_width:
        raise ValueError(
            f"config/pairs.py is missing 'zone_width' for: {missing_zone_width} "
            "-- the S/R strategy's zone builder needs a per-symbol price "
            "distance (see src/zones.py's build_support_resistance_zones)."
        )

    lot_map = {symbol: float(raw["lot"]) for symbol, raw in PAIRS.items()}
    zone_width_map = {symbol: float(raw["zone_width"]) for symbol, raw in PAIRS.items()}
    magic_map = build_magic_map(PAIRS)

    mt5_connector.connect()
    print(
        f"Connected. Strategy='sr_retest' (15min). "
        f"Trading {len(PAIRS)} pairs: {list(PAIRS)}"
    )

    try:
        while True:
            wait = seconds_until_next_poll()
            time.sleep(wait)
            run_cycle(lot_map, magic_map, zone_width_map)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        mt5_connector.disconnect()


if __name__ == "__main__":
    main()
