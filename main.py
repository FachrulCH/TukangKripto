import json
import os
import sched
import sys
import time
from datetime import datetime

import pandas as pd
import schedule

from tukang_kripto.app_state import AppState
from tukang_kripto.public_API import PublicAPI
from tukang_kripto.technical_analysis import TechnicalAnalysis
from tukang_kripto.utils import (create_alert, print_green, print_red,
                                 print_yellow)

s = sched.scheduler(time.time, time.sleep)


def getInterval(df: pd.DataFrame = pd.DataFrame()) -> pd.DataFrame:
    if len(df) == 0:
        return df
    else:
        # most recent entry
        return df.tail(1)


def getAction(
    now=datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
    app: PublicAPI = None,
    price: float = 0,
    df: pd.DataFrame = pd.DataFrame(),
    df_last: pd.DataFrame = pd.DataFrame(),
    last_action: str = "WAIT",
    debug: bool = False,
) -> str:
    # ema12gtema26co = bool(df_last["ema12gtema26co"].values[0])
    ema12ltema26co = bool(df_last["ema12ltema26co"].values[0])
    ema12gtema26 = bool(df_last["ema12gtema26"].values[0])
    goldencross = bool(df_last["goldencross"].values[0])

    # criteria for a buy signal
    if ema12gtema26 is True and goldencross is True and last_action != "BUY":
        return "BUY"

    # criteria for a sell signal
    elif ema12ltema26co is True and last_action not in ["", "SELL"]:
        return "SELL"

    return "WAIT"


def executeJob(app=PublicAPI(), state=AppState(), market="BTC-USDT", time_frame=900):
    """Trading bot job which runs at a scheduled interval"""
    # increment state.iterations
    state.iterations = state.iterations + 1
    # supported time:
    # 1m = 60
    # 5m = 300
    # 15m = 900
    # 1h = 3600
    # 6h = 21600
    # 1d = 86400
    trading_data = app.getHistoricalData(market, time_frame)
    # analyse the market data
    trading_dataCopy = trading_data.copy()
    ta = TechnicalAnalysis(trading_dataCopy)
    ta.addAll()
    df = ta.getDataFrame()
    df_last = getInterval(df)
    # print(df)
    if len(df_last) > 0:
        price = float(df_last["close"].values[0])
        now = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        state.action = getAction(now, app, price, df, df_last, state.last_action, False)

        # if a buy signal
        if state.action == "BUY":
            state.last_buy_price = price
            state.last_buy_high = state.last_buy_price
            print_green(f"=>   {state.action} @{price}")
            create_alert(
                state.action, f"I think the {market} is intresting at {price}!"
            )
        elif state.action == "SELL":
            print_red(f"=>   {state.action} @{price}")
            create_alert(
                state.action, f"I think the {market} is NOT intresting at {price}!"
            )
        else:
            print_yellow(f"=>   {state.action} @{price}")


if __name__ == "__main__":
    print("Bot lagi gelar lapak")
    f = open("config.json")
    config_data = json.load(f)

    # executeJob('asal')
    app = PublicAPI()
    states = {}

    def runApp():
        for config in config_data["configs"]:
            if config["market"] not in states.keys():
                states[config["market"]] = AppState()

            # First execution init
            executeJob(
                app, states[config["market"]], config["market"], config["time_frame"]
            )

            print(
                f"Membuat job pengecekan {config['market']} setiap {config['pool_time']} detik"
            )
            schedule.every(config["pool_time"]).seconds.do(
                executeJob,
                app,
                states[config["market"]],
                config["market"],
                config["time_frame"],
            )

        while True:
            schedule.run_pending()
            time.sleep(1)

    try:
        runApp()
    # catches a keyboard break of app, exits gracefully
    except KeyboardInterrupt:
        print(datetime.now(), "Tutup lapak")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
