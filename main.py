import os
import sys
import time
from datetime import datetime

import schedule
from loguru import logger

from tukang_kripto import configs
from tukang_kripto.app_state import AppState
from tukang_kripto.indodax import Indodax
from tukang_kripto.public_API import PublicAPI
from tukang_kripto.technical_analysis import (
    TechnicalAnalysis,
    calculate_profit,
    getAction,
    getInterval,
)
from tukang_kripto.utils import (
    create_alert,
    create_csv_transaction,
    in_rupiah,
    print_green,
    print_red,
    print_yellow,
)

logger.add(
    "running_{time}.log", rotation="1 day", format="{time} {level} {message}"
)  # Once the file is too old, it's rotated


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
        harga = indodax.get_best_bids_price()
        if not harga:
            # Possibly error from indodax
            # exit the execution
            logger.warning("Skip bang, keknya indodax error")
            return False

        price_changes = "0%"
        if state.market_price > 0:
            price_changes = f"{calculate_profit(state.market_price, harga)}%"
        state.market_price = harga  # update new price
        state.last_close_price = price
        logger.warning(
            f"\n=>   {state.action} {str(df_last['date'].values[0])[:16]} {in_rupiah(harga)} / {price_changes}"
        )
        # if a buy signal
        if state.action == "BUY":
            state.last_action = "BUY"
            state.last_buy_high = state.last_buy_price
            percentage = int(trade_conf.get("buy_percentage", 100))
            limit_budget = trade_conf.get("limit_budget", 0)

            # prevent overbought (2 times without selling, it will cost budget for other)
            if state.buy_count > state.sell_count:
                logger.warning(
                    "Kebanyakan beli, yang tadi {} koin aja belum di jual :P {} {} -",
                    state.last_buy_size,
                    state.buy_count,
                    state.sell_count,
                )
                return None

            bought, bought_coin, price_per_coin, buy_amount = indodax.buy_coin(
                percentage, limit_budget
            )
            if bought:
                state.buy_count += int(bought)
                state.buy_sum += float(bought_coin)
                state.last_buy_size = float(bought_coin)
                state.last_buy_price = price_per_coin
                state.trend = "bullish"
                state.in_position = True
                transaction = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "coin_name": trade_conf["symbol"],
                    "type": "buy",
                    "coin_amount": bought_coin,
                    "price": price_per_coin,
                    "amount": buy_amount,
                }
                create_csv_transaction(trade_conf["symbol"], transaction)

            logger.info(
                "Buy Count: {} Amount {} Rp{}",
                state.buy_count,
                state.buy_sum,
                price_per_coin,
            )
            if configs.enable_notification():
                create_alert(
                    f"{state.action} '{market}' #{state.buy_count}",
                    f"Udah naik{price_changes}, kita beli di harga {in_rupiah(price_per_coin)} sebanyak {bought_coin}!",
                )

        elif state.action == "SELL":
            state.last_action = "SELL"
            state.trend = "bearish"
            price_per_coin = 0
            if state.in_position:
                sold, sold_coin, price_per_coin, estimate_amount = indodax.sell_coin(
                    int(trade_conf["sell_percentage"]), stop_loss=state.on_stop_loss
                )
                logger.info(
                    "Sell Count: {} Amount {}", state.sell_count, state.sell_sum
                )
                if sold:
                    state.sell_count += 1
                    state.sell_sum += float(sold_coin)
                    state.last_sell_price = price_per_coin

                    # reset stop loss state
                    state.on_stop_loss = False
                    transaction = {
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "coin_name": trade_conf["symbol"],
                        "type": "sell",
                        "coin_amount": sold_coin,
                        "price": int(price_per_coin),
                        "amount": int(estimate_amount),
                    }
                    create_csv_transaction(trade_conf["symbol"], transaction)

                if sold_coin <= 0:
                    # not in position holding coin
                    state.in_position = False
            else:
                sold_coin = 0
                logger.critical("Mau JUAL tapi lagi ga megang koin :(")

            if configs.enable_desktop_alert():
                create_alert(
                    f"{state.action} '{market}'",
                    f"Kita jual {sold_coin} di {in_rupiah(price_per_coin)}/coin!",
                )
        else:
            state.last_action = "WAIT"
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
            coin_name = coin["market"].split("-")[0]
            # First execution init
            executeJob(app, states[coin["market"]], coin["market"], coin["time_frame"])
            create_csv_transaction(coin_name)
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
