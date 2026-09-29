import numpy as np
import pandas as pd


def generate_intraday_ohlc(
    n_bars=100,
    frequency="15Min",
    start_price=100.0,
    drift=0.0,
    volatility=0.01,
    start_date="2025-01-01",
    seed=None,
):
    """
    Generate synthetic intraday OHLC stock data.

    Parameters
    ----------
    n_bars : int
        Number of bars to generate.
    frequency : str
        One of: '15m', '30m', '1h', '4h'
    start_price : float
        Initial price.
    drift : float
        Mean return per bar.
    volatility : float
        Volatility per bar.
    start_date : str
        First trading day.
    seed : int
        Random seed.

    Returns
    -------
    pd.DataFrame
        Datetime-indexed OHLC data.
    """

    if seed is not None:
        np.random.seed(seed)

    # Market hours
    market_open = pd.Timedelta(hours=8, minutes=30)
    market_close = pd.Timedelta(hours=16, minutes=30)

    freq_map = {
        "1Min": pd.Timedelta(minutes=1),
        "5Min": pd.Timedelta(minutes=5),
        "15Min": pd.Timedelta(minutes=15),
        "30Min": pd.Timedelta(minutes=30),
        "1H": pd.Timedelta(hours=1),
        "4H": pd.Timedelta(hours=4),
    }

    if frequency not in freq_map:
        raise ValueError(
            "frequency must be one of ['1Min','5Min','15Min','30Min','1H','4H']"
        )

    bar_size = freq_map[frequency]

    # Build valid trading timestamps
    timestamps = []

    current_day = pd.Timestamp(start_date)

    while len(timestamps) < n_bars:

        current_time = current_day + market_open

        while current_time <= current_day + market_close:

            timestamps.append(current_time)

            if len(timestamps) >= n_bars:
                break

            current_time += bar_size

        current_day += pd.Timedelta(days=1)

    timestamps = timestamps[:n_bars]

    # Simulate close prices
    returns = np.random.normal(
        loc=drift,
        scale=volatility,
        size=n_bars
    )

    close = np.empty(n_bars)
    close[0] = start_price

    for i in range(1, n_bars):
        close[i] = close[i - 1] * np.exp(returns[i])

    # Open = previous close
    open_ = np.empty(n_bars)
    open_[0] = start_price
    open_[1:] = close[:-1]

    # Intrabar excursions
    intrabar_noise = np.random.uniform(
        0.001,
        volatility * 2,
        n_bars
    )

    high = np.maximum(open_, close) * (1 + intrabar_noise)
    low = np.minimum(open_, close) * (1 - intrabar_noise)

    df = pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
        },
        index=pd.DatetimeIndex(timestamps, name="Datetime"),
    )

    return df