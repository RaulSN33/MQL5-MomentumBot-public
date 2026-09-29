from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd


AGGREGATION = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
    }

class OHLCData: 

    
    def __init__(self, data: pd.DataFrame):
        self.frames = {
            "1Min":data.sort_index().copy()
        }

    def resample(
        self, timeframe:str
        ) -> pd.DataFrame:

        self.frames[timeframe] = (
            self.frames["1Min"]
            .resample(timeframe)
            .agg(AGGREGATION)
            .dropna(axis='index', how='all')
        )

        self.available_timeframes = list(self.frames.keys())
        
        return self.frames[timeframe]
    
    
    def add_indicator(
        self,
        timeframe: str,
        name: str,
        indicator, 
        **kwargs,
    ) -> None:
        frame = self.frames[timeframe]
        frame[name] = indicator(
            frame, **kwargs
        )
        
    def get_trends_df(
        self,
        timeframes,
        trend_column_name,
        trend_signal_timeframe,
        trend_signal_column
    ):
        trends = pd.DataFrame({
        frame: self.frames[frame][trend_column_name]
        for frame
        in timeframes
        })
        
        trends = trends.ffill()
        trends["signal"] = self.frames[trend_signal_timeframe][trend_signal_column].copy()
        self.trends = trends
        
        return self.trends
        
                
    def __getitem__(self, timeframe:str)-> pd.DataFrame:
        return self.frames[timeframe]








# class OHLCDataRobust:
#     OHLC_AGGREGATION = {
#         "Open": "first",
#         "High": "max",
#         "Low": "min",
#         "Close": "last",
# # "Volume": "sum",
#     }

#     ALLOWED_TIMEFRAMES = {
#         "1m": None,
#         "15m": "15min",
#         "30m": "30min",
#         "1h": "1h",
#         "4h": "4h",
#         "1d": "1D",
#     }

#     def __init__(self, data: pd.DataFrame):
#         self._data_1m = self._validate(data.copy())
#         self._cache: dict[str, pd.DataFrame] = {}

#     @staticmethod
#     def _validate(data: pd.DataFrame) -> pd.DataFrame:
#         required_columns = {"Open", "High", "Low", "Close"}
#         missing = required_columns - set(data.columns)

#         if missing:
#             raise ValueError(f"Missing required columns: {sorted(missing)}")

#         if not isinstance(data.index, pd.DatetimeIndex):
#             raise TypeError("DataFrame index must be a DatetimeIndex")

#         if data.index.has_duplicates:
#             raise ValueError("DatetimeIndex contains duplicate timestamps")

#         data = data.sort_index()

#         invalid_high = data["High"] < data[["Open", "Close", "Low"]].max(axis=1)
#         invalid_low = data["Low"] > data[["Open", "Close", "High"]].min(axis=1)

#         if invalid_high.any() or invalid_low.any():
#             raise ValueError("Invalid OHLC relationships detected")

#         return data

#     def get(
#         self,
#         timeframe: str = "1m",
#         *,
#         copy: bool = True,
#         include_incomplete: bool = False,
#     ) -> pd.DataFrame:
#         """
#         Return data for the requested timeframe.

#         Parameters
#         ----------
#         timeframe:
#             One of: 1m, 15m, 30m, 1h, 4h, 1d.
#         copy:
#             Return a copy to prevent accidental mutation.
#         include_incomplete:
#             Keep the most recent possibly incomplete candle.
#         """
#         if timeframe not in self.ALLOWED_TIMEFRAMES:
#             allowed = ", ".join(self.ALLOWED_TIMEFRAMES)
#             raise ValueError(
#                 f"Unsupported timeframe: {timeframe}. "
#                 f"Allowed values: {allowed}"
#             )

#         if timeframe == "1m":
#             result = self._data_1m
#         else:
#             result = self._get_resampled(timeframe)

#         if not include_incomplete and timeframe != "1m":
#             result = self._remove_incomplete_last_candle(result, timeframe)

#         return result.copy() if copy else result

#     def _get_resampled(self, timeframe: str) -> pd.DataFrame:
#         if timeframe in self._cache:
#             return self._cache[timeframe]

#         rule = self.ALLOWED_TIMEFRAMES[timeframe]

#         # Only aggregate columns that actually exist.
#         aggregation = {
#             column: method
#             for column, method in self.OHLC_AGGREGATION.items()
#             if column in self._data_1m.columns
#         }

#         resampled = (
#             self._data_1m
#             .resample(
#                 rule,
#                 label="left",
#                 closed="left",
#                 origin="start_day",
#             )
#             .agg(aggregation)
#             .dropna(subset=["Open", "High", "Low", "Close"], how="all")
#         )

#         self._cache[timeframe] = resampled
#         return resampled

#     def _remove_incomplete_last_candle(
#         self,
#         data: pd.DataFrame,
#         timeframe: str,
#     ) -> pd.DataFrame:
#         if data.empty:
#             return data

#         rule = self.ALLOWED_TIMEFRAMES[timeframe]
#         expected_end = data.index[-1] + pd.tseries.frequencies.to_offset(rule)
#         last_observation = self._data_1m.index[-1]

#         if last_observation < expected_end - pd.Timedelta(minutes=1):
#             return data.iloc[:-1]

#         return data

#     def add_indicator(
#         self,
#         name: str,
#         function: Callable[..., pd.Series],
#         *,
#         timeframe: str = "1m",
#         overwrite: bool = False,
#         **kwargs: Any,
#     ) -> pd.Series:
#         """
#         Calculate an indicator and add it to a specific timeframe.

#         The function receives the timeframe's DataFrame as its first argument
#         and must return a Series aligned to that DataFrame's index.
#         """
#         dataframe = self.get(
#             timeframe,
#             copy=False,
#             include_incomplete=True,
#         )

#         if name in dataframe.columns and not overwrite:
#             raise ValueError(
#                 f"Column {name!r} already exists in timeframe {timeframe!r}"
#             )

#         result = function(dataframe.copy(), **kwargs)

#         if not isinstance(result, pd.Series):
#             raise TypeError("Indicator function must return a pandas Series")

#         if not result.index.equals(dataframe.index):
#             result = result.reindex(dataframe.index)

#         dataframe[name] = result
#         return dataframe[name].copy()

#     def add_indicators(
#         self,
#         function: Callable[..., pd.DataFrame],
#         *,
#         timeframe: str = "1m",
#         overwrite: bool = False,
#         **kwargs: Any,
#     ) -> pd.DataFrame:
#         """
#         Add an indicator function that returns multiple columns.
#         """
#         dataframe = self.get(
#             timeframe,
#             copy=False,
#             include_incomplete=True,
#         )

#         result = function(dataframe.copy(), **kwargs)

#         if not isinstance(result, pd.DataFrame):
#             raise TypeError("Indicator function must return a DataFrame")

#         result = result.reindex(dataframe.index)

#         duplicated = set(result.columns) & set(dataframe.columns)

#         if duplicated and not overwrite:
#             raise ValueError(
#                 f"Columns already exist: {sorted(duplicated)}"
#             )

#         dataframe[result.columns] = result
#         return result.copy()

#     # def append(self, new_data: pd.DataFrame) -> None:
#     #     """
#     #     Add new 1-minute observations and invalidate resampling caches.
#     #     """
#     #     combined = pd.concat([self._data_1m, new_data])

#     #     # If the latest version of a candle should replace the old one:
#     #     combined = combined[~combined.index.duplicated(keep="last")]

#     #     self._data_1m = self._validate(combined)
#     #     self._cache.clear()

#     # def clear_cache(self) -> None:
#     #     self._cache.clear()

#     def __repr__(self) -> str:
#         start = self._data_1m.index.min()
#         end = self._data_1m.index.max()

#         return (
#             f"OHLCData(rows={len(self._data_1m)}, "
#             f"start={start}, end={end}, "
#             f"cached_timeframes={list(self._cache)})"
#         )