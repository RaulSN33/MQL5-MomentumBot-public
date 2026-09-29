from __future__ import annotations

import pandas as pd
import MetaTrader5 as mt5
from dotenv import dotenv_values


def connect(
    config_path: str = "config/.env",
    server: str = "Pepperstone-Demo",
) -> None:
    config = dotenv_values(config_path)

    if not mt5.initialize():
        raise RuntimeError(f"mt5.initialize() failed, error code = {mt5.last_error()}")

    authorized = mt5.login(
        login=int(config["PPSTNUSSER"]),
        password=config["PPSTNPSWD"],
        server=server,
    )
    if not authorized:
        mt5.shutdown()
        raise RuntimeError(f"mt5.login() failed, error code = {mt5.last_error()}")


def disconnect() -> None:
    mt5.shutdown()


def fetch_ohlc(
    symbol: str,
    n_bars: int,
    timeframe=mt5.TIMEFRAME_M1,
) -> pd.DataFrame:
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n_bars)

    if rates is None or len(rates) == 0:
        raise RuntimeError(
            f"copy_rates_from_pos returned no data for {symbol}, "
            f"error code = {mt5.last_error()}"
        )

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df = df.set_index("time")
    df = df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
    })

    return df[["Open", "High", "Low", "Close"]]
