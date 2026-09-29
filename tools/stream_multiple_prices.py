import MetaTrader5 as mt5
import time
from datetime import datetime
import csv

def stream_prices(
        symbols:list[str]= ["BTCUSD"],
        poll_interval=0.5,
        log_to_csv=False
):

    # csv_path = f"{symbol}.csv"
    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
        return

    for symbol in symbols:
        if not mt5.symbol_select(symbol, True):
            print(f"Failed to select {symbol}, error code =", mt5.last_error())
            mt5.shutdown()
            return

        # print(f"Streaming {symbol}... press Ctrl+C to stop.\n")

    # csv_file = None
    # writer = None
    # if log_to_csv:
    #     csv_file = open(csv_path, mode="a", newline="")
    #     writer = csv.writer(csv_file)
    #     if csv_file.tell() == 0:
    #         writer.writerow(["time", "bid", "ask", "last", "volume"])

    last_time = {}
    for symbol in symbols:
        last_time[symbol] = None
    try:
        while True:
            for symbol in symbols:
                tick = mt5.symbol_info_tick(symbol)

                if tick is None:
                    print("No tick data, error code =", mt5.last_error())
                    time.sleep(poll_interval)
                    continue

                # only print/log when a new tick actually arrives
                if tick.time_msc != last_time[symbol]:
                    last_time[symbol] = tick.time_msc
                    ts = datetime.fromtimestamp(tick.time)

                    print(f"{symbol}  {ts}  bid={tick.bid}  ask={tick.ask}  last={tick.last}  vol={tick.volume}")

                    # if writer:
                    #     writer.writerow([ts, tick.bid, tick.ask, tick.last, tick.volume])
                    #     csv_file.flush()

                time.sleep(poll_interval)

    except KeyboardInterrupt:
        print("\nStopped streaming.")

    # finally:
    #     if csv_file:
    #         csv_file.close()
    #     mt5.shutdown()


if __name__ == "__main__":
    stream_prices(symbol=["BTCUSD", "ETHUSD"], poll_interval=0.5, log_to_csv=True)
