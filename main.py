import os
import sys
import time
from datetime import datetime

import schedule

from tukang_kripto import configs
from tukang_kripto.app_state import AppState
from tukang_kripto.indodax import Indodax
from tukang_kripto.public_API import PublicAPI
from tukang_kripto.technical_analysis import TechnicalAnalysis, getAction, getInterval
from tukang_kripto.utils import (
    create_alert,
    print_green,
    print_red,
    print_yellow,
    in_rupiah,
)

from loguru import logger
logger.add("running.log", rotation="1 day", format="{time} {level} {message}")    # Once the file is too old, it's rotated

def executeJob(app=PublicAPI(), state=AppState(), market="BTC-USDT", time_frame=900):
    """Trading bot job which runs at a scheduled interval"""
    # increment state.iterations
    state.iterations = state.iterations + 1
    # print(state.iterations, state.last_action)
    # supported time:
    # 1m = 60
    # 5m = 300
    # 15m = 900
    # 1h = 3600
    # 6h = 21600
    # 1d = 86400
    trading_data = app.get_historical_data(market, time_frame)
    # analyse the market data
    trading_dataCopy = trading_data.copy()
    ta = TechnicalAnalysis(trading_dataCopy, state)
    ta.add_all()
    df = ta.get_data_frame()
    df_last = getInterval(df)
    # print(df)
    if len(df_last) > 0:
        price = float(df_last["close"].values[0])
        now = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        state.action = getAction(
            now, app, price, df, df_last, state.last_action, False, state
        )

        trade_conf = configs.coin(market)["indodax"]
        indodax = Indodax(trade_conf)
        price_changes = 0
        if state.last_close_price > 0:
            price_changes = round(
                ((price - state.last_close_price) / state.last_close_price * 100), 2
            )

        state.last_close_price = price
        # if a buy signal
        if state.action == "BUY":
            state.last_action = "BUY"
            state.last_buy_price = price
            state.last_buy_high = state.last_buy_price
            harga = indodax.get_best_bids_price()

            logger.info(f"=>   {state.action} {in_rupiah(harga)}")
            if configs.enable_desktop_alert():
                create_alert(
                    f"{state.action} {market}",
                    f"I think the {market} is intresting at {in_rupiah(harga)}!",
                )
            bought, bought_coin = indodax.buy_coin(int(trade_conf["buy_percentage"]))
            state.buy_count += int(bought)
            state.buy_sum += float(bought_coin)
            logger.info("Buy Count: {} Amount {}", state.buy_count, state.buy_sum)

        elif state.action == "SELL":
            state.last_action = "SELL"
            harga = indodax.get_best_ask_price()
            logger.info(f"=>   {state.action} {in_rupiah(harga)}")
            if configs.enable_desktop_alert():
                create_alert(
                    f"{state.action} {market}",
                    f"I think the {market} is NOT intresting at {in_rupiah(harga)}!",
                )
            sold, sold_coin = indodax.sell_coin(int(trade_conf["sell_percentage"]))
            state.sell_count += int(sold)
            state.sell_sum += float(sold_coin)
            logger.info("Sell Count: {} Amount {}", state.sell_count, state.sell_sum)
        else:
            state.last_action = "WAIT"
            harga = indodax.get_best_bids_price()
            logger.info(
                f"=>   {state.action} {str(df_last['date'].values[0])[:16]} {in_rupiah(harga)} / {price_changes}%"
            )
            # print(state.debug)


if __name__ == "__main__":
    print("Bot lagi gelar lapak")
    logger.info("Siap Memulai!")
    config_data = configs.read_config()

    # executeJob('asal')
    app = PublicAPI()
    states = {}

    def runApp():
        for coin in configs.all_coins():
            if coin["market"] not in states.keys():
                states[coin["market"]] = AppState(coin["market"])

            # First execution init
            executeJob(app, states[coin["market"]], coin["market"], coin["time_frame"])
            logger.info(
                f"Membuat job pengecekan {coin['market']} setiap {coin['pool_time']} detik"
            )
            schedule.every(coin["pool_time"]).seconds.do(
                executeJob,
                app,
                states[coin["market"]],
                coin["market"],
                coin["time_frame"],
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
            for coin in configs.all_coins():
                if coin["market"] in states.keys():
                    print_red(f'coin_name: {states[coin["market"]].coin_name}')
                    print_green(f'buy_count: {states[coin["market"]].buy_count}')
                    print_green(f'buy_sum: {states[coin["market"]].buy_sum}')
                    print("sell_count:", states[coin["market"]].sell_count)
                    print("sell_sum:", states[coin["market"]].sell_sum)
                    print_yellow("=========== \n")
            sys.exit(0)
        except SystemExit:
            os._exit(0)
