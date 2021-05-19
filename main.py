import os
import sched
import sys
import time
from datetime import datetime

import pandas as pd

from tukang_kripto.app_state import AppState
from tukang_kripto.public_API import PublicAPI
from tukang_kripto.technical_analysis import TechnicalAnalysis
from tukang_kripto.utils import create_alert, print_red, print_green, print_yellow

s = sched.scheduler(time.time, time.sleep)


def getInterval(df: pd.DataFrame = pd.DataFrame()) -> pd.DataFrame:
    if len(df) == 0:
        return df
    else:
        # most recent entry
        return df.tail(1)


def getAction(
    now: datetime = datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
    app: PublicAPI = None,
    price: float = 0,
    df: pd.DataFrame = pd.DataFrame(),
    df_last: pd.DataFrame = pd.DataFrame(),
    last_action: str = "WAIT",
    debug: bool = False,
) -> str:

    ema12gtema26co = bool(df_last["ema12gtema26co"].values[0])
    ema12ltema26co = bool(df_last["ema12ltema26co"].values[0])

    # criteria for a buy signal
    if ema12gtema26co is True and last_action != "BUY":
        return "BUY"

    # criteria for a sell signal
    elif ema12ltema26co is True and last_action not in ["", "SELL"]:
        return "SELL"

    return "WAIT"


def executeJob(
    sc,
    app=PublicAPI(),
    state=AppState(),
    trading_data=pd.DataFrame(),
    market="BTC-USDT",
    pool_time=900,
):
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
    trading_data = app.getHistoricalData(market, 300)
    # analyse the market data
    trading_dataCopy = trading_data.copy()
    ta = TechnicalAnalysis(trading_dataCopy)
    ta.addAll()
    df = ta.getDataFrame()
    df_last = getInterval(df)
    if len(df_last) > 0:
        price = float(df_last["close"].values[0])
        now = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        state.action = getAction(now, app, price, df, df_last, state.last_action, False)
        # if a buy signal
        if state.action == "BUY":
            state.last_buy_price = price
            state.last_buy_high = state.last_buy_price
            print_green(f"=>   {state.action} @{price}")
            create_alert(state.action, f"I think the {market} is intresting at {price}!")
        elif state.action == "SELL":
            print_red(f"=>   {state.action} @{price}")
            create_alert(state.action, f"I think the {market} is NOT intresting at {price}!")
        else:
            print_yellow(f"=>   {state.action} @{price}")
            
        # poll every x second
        # 900 = 15 minutes
        list(map(s.cancel, s.queue))
        s.enter(pool_time, 1, executeJob, (sc, app, state))


if __name__ == "__main__":
    print("Bot lagi gelar lapak")
    # executeJob('asal')
    state = AppState()
    state2 = AppState()
    state3 = AppState()
    state4 = AppState()
    state5 = AppState()
    state6 = AppState()
    state7 = AppState()
    state8 = AppState()
    app = PublicAPI()
    s = sched.scheduler(time.time, time.sleep)

    def runApp():
        # run the first job immediately after starting
        # executeJob(s, app, state, market="MATIC-USD", pool_time=300)
        # executeJob(s, app, state2, market="1INCH-USD", pool_time=311)
        # executeJob(s, app, state3, market="BCH-USD", pool_time=322)
        executeJob(s, app, state4, market="DASH-USD", pool_time=333)
        # executeJob(s, app, state5, market="LTC-USD", pool_time=344)
        # executeJob(s, app, state6, market="ETH-USDT", pool_time=355)
        # executeJob(s, app, state7, market="BTC-USDT", pool_time=366)
        # executeJob(s, app, state8, market="ETC-USD", pool_time=377)

        s.run()

    try:
        runApp()
    # catches a keyboard break of app, exits gracefully
    except KeyboardInterrupt:
        print(datetime.now(), "Tutup lapak")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
