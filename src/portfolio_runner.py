from __future__ import annotations

import time

from src import mt5_connector
from src import risk
from src.runner_core import run_symbol_once, seconds_until_next_poll
from src.strategy import compute_signal as ema_cross_signal
from src.strategy_rsi_entry import compute_signal as rsi_pullback_signal

MAGIC_BASE = 20260900  # distinct range from live_runner.MAGIC (20260823) to avoid collisions

# config/pairs.py :: STRATEGY picks one of these for the whole portfolio.
STRATEGIES = {
    "ema_cross": ema_cross_signal,
    "rsi_pullback": rsi_pullback_signal,
}


def resolve_strategy(name: str):
    try:
        return STRATEGIES[name]
    except KeyError:
        raise SystemExit(
            f"config/pairs.py STRATEGY={name!r} is not valid; "
            f"choose one of {sorted(STRATEGIES)}"
        )


def build_magic_map(pairs: dict) -> dict[str, int]:
    """One stable magic number per symbol, derived from its position in the config."""
    return {symbol: MAGIC_BASE + i for i, symbol in enumerate(pairs)}


def build_settings_map(pairs: dict) -> dict[str, risk.PairSettings]:
    return {symbol: risk.parse_settings(symbol, raw) for symbol, raw in pairs.items()}


def run_cycle(
    settings_map: dict[str, risk.PairSettings],
    magic_map: dict[str, int],
    cooldown: risk.Cooldown,
    compute_signal_fn,
) -> None:
    for symbol, settings in settings_map.items():
        try:
            run_symbol_once(
                symbol, settings, magic_map[symbol], cooldown,
                compute_signal_fn=compute_signal_fn,
            )
        except Exception as exc:
            print(f"[{symbol}] Error during run_once: {exc}")


def main() -> None:
    from config.pairs import PAIRS, STRATEGY

    if not PAIRS:
        print("config/pairs.py has no pairs configured. Add symbols and settings, then rerun.")
        return

    compute_signal_fn = resolve_strategy(STRATEGY)

    magic_map = build_magic_map(PAIRS)
    settings_map = build_settings_map(PAIRS)
    cooldown = risk.Cooldown()

    mt5_connector.connect()
    print(
        f"Connected. Strategy={STRATEGY!r}. "
        f"Trading {len(PAIRS)} pairs: {list(PAIRS)}"
    )

    try:
        while True:
            wait = seconds_until_next_poll()
            time.sleep(wait)
            run_cycle(settings_map, magic_map, cooldown, compute_signal_fn)

    except KeyboardInterrupt:
        print("\nStopped.")

    finally:
        mt5_connector.disconnect()


if __name__ == "__main__":
    main()
