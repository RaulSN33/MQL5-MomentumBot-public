"""
Price-action support/resistance zone builder -- PRIVATE.

Used internally by src/strategy_sr_entry.py. Not included in the public
showcase.
"""
from __future__ import annotations

import pandas as pd


def build_support_resistance_zones(df: pd.DataFrame, zone_width: float, **kwargs) -> pd.DataFrame:
    """Return a registry of S/R zones (bounds, origin, activation time) for `df`."""
    raise NotImplementedError("Zone detection is private and not included in this repository.")
