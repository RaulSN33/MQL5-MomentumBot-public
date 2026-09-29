from __future__ import annotations

import argparse

from src import live_runner
from src import live_runner_sr
from src import portfolio_runner


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a trading bot.")
    parser.add_argument(
        "--mode",
        choices=["single", "portfolio", "sr_retest"],
        default="portfolio",
        help=(
            "single = single-symbol runner (src/live_runner.py); "
            "portfolio = every pair in config/pairs.py, strategy picked by "
            "config/pairs.py STRATEGY (default); "
            "sr_retest = S/R break-and-retest runner (src/live_runner_sr.py), "
            "every pair in config/pairs.py, 15min trigger, its own magic range. "
            "Do not also run a pair's symbol under single/portfolio at the same time."
        ),
    )
    args = parser.parse_args()

    if args.mode == "single":
        live_runner.main()
    elif args.mode == "sr_retest":
        live_runner_sr.main()
    else:
        portfolio_runner.main()


if __name__ == "__main__":
    main()
