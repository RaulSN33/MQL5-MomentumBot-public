from __future__ import annotations

import csv
import os
from datetime import datetime, timezone

import MetaTrader5 as mt5

TRADE_LOG_PATH = "trade_log.csv"
TRADE_LOG_FIELDS = [
    "logged_at",
    "event",
    "symbol",
    "direction",
    "volume",
    "price",
    "order_id",
    "retcode",
    "comment",
]


def log_trade_event(event: str, symbol: str, direction: str, result) -> None:
    is_new_file = not os.path.exists(TRADE_LOG_PATH)

    with open(TRADE_LOG_PATH, mode="a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRADE_LOG_FIELDS)
        if is_new_file:
            writer.writeheader()

        writer.writerow({
            "logged_at": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "symbol": symbol,
            "direction": direction,
            "volume": getattr(result, "volume", None),
            "price": getattr(result, "price", None),
            "order_id": getattr(result, "order", None),
            "retcode": getattr(result, "retcode", None),
            "comment": getattr(result, "comment", None),
        })


def get_open_position(symbol: str, magic: int):
    positions = mt5.positions_get(symbol=symbol)

    if not positions:
        return None

    for position in positions:
        if position.magic == magic:
            return position

    return None


def send_market_order(
    symbol: str,
    direction: str,
    volume: float,
    magic: int,
    deviation: int = 20,
    sl_price: float | None = None,
    tp_price: float | None = None,
    comment: str = "ema_trend_bot entry",
):
    order_type = mt5.ORDER_TYPE_BUY if direction == "long" else mt5.ORDER_TYPE_SELL
    tick = mt5.symbol_info_tick(symbol)
    price = tick.ask if direction == "long" else tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "deviation": deviation,
        "magic": magic,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    if sl_price is not None:
        request["sl"] = sl_price
    if tp_price is not None:
        request["tp"] = tp_price

    result = mt5.order_send(request)
    log_trade_event("entry", symbol, direction, result)

    return result


def close_position(position, deviation: int = 20, reason: str = "exit"):
    symbol = position.symbol
    is_long = position.type == mt5.POSITION_TYPE_BUY
    order_type = mt5.ORDER_TYPE_SELL if is_long else mt5.ORDER_TYPE_BUY
    tick = mt5.symbol_info_tick(symbol)
    price = tick.bid if is_long else tick.ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": position.volume,
        "type": order_type,
        "position": position.ticket,
        "price": price,
        "deviation": deviation,
        "magic": position.magic,
        "comment": f"ema_trend_bot {reason}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    log_trade_event(reason, symbol, "long" if is_long else "short", result)

    return result


def modify_position_sl(position, sl_price: float, tp_price: float | None = None):
    """
    Move the broker-side stop (and optionally the target) on an open position.
    Used by the S/R retest bot's structure trailing stop. Leaves the TP
    untouched when `tp_price` is None.
    """
    is_long = position.type == mt5.POSITION_TYPE_BUY

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": position.symbol,
        "position": position.ticket,
        "sl": sl_price,
        "tp": position.tp if tp_price is None else tp_price,
        "magic": position.magic,
    }

    result = mt5.order_send(request)
    log_trade_event(
        "modify_sl", position.symbol, "long" if is_long else "short", result
    )

    return result
