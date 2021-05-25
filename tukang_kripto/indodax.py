import os

import ccxt
from loguru import logger

from tukang_kripto.utils import print_red


class Indodax:
    def __init__(self, config):
        key = os.getenv("INDODAX_KEY")
        secret = os.getenv("INDODAX_SECRET")
        self.api = ccxt.indodax(
            {
                "apiKey": key,
                "secret": secret,
            }
        )
        self.config = config

    def get_best_ask_price(self):
        # harga jual
        book = self.api.fetch_order_book(self.config["symbol"])
        return book["asks"][3][0]

    def get_best_bids_price(self):
        # harga beli
        try:
            book = self.api.fetch_order_book(self.config["symbol"])
            return book["bids"][1][0]
        except Exception as e:
            logger.error("Indodax Error euy")
            logger.error(e)
            return None

    def get_balance_idr(self):
        balances = self.api.fetch_free_balance()
        return balances["IDR"]

    def get_balance_coin(self):
        coin = self.config["symbol"].split("/")[0]
        balances = self.api.fetch_free_balance()
        return balances[coin]

    def buy_coin(self, percentage=100, limit_budget=0, last_sell_price=0):
        idr = self.get_balance_idr()
        budget = int(percentage / 100 * idr)

        if budget < 10000:
            print_red(f"Aduuh kurang budget euy, sekarang ada {idr} maunya {budget}")
            return False, 0

        if 10000 < limit_budget < idr:
            print("masuk limit")
            budget = limit_budget

        target_price = self.get_best_bids_price()
        if last_sell_price > 0:
            est_profit = round((last_sell_price - target_price) / target_price * 100, 2)
            logger.success(f"Profit beli: {est_profit}%")
            
        coin_buy = round(budget / target_price, 8)
        logger.warning(
            "Beli {}, Budget {}, koin: {}, Dengan harga {}",
            self.config["symbol"],
            budget,
            coin_buy,
            target_price,
        )
        # indodax.create_order('BTC/IDR', 'limit', 'buy', 0.00004784, 540542000)

        response = self.api.create_order(
            self.config["symbol"], "limit", "buy", coin_buy, target_price
        )
        return response.get("info").get("success") == "1", coin_buy, target_price

    def sell_coin(self, percentage=100, last_buy_price=0):
        coin = self.get_balance_coin()

        if coin < 0:
            print_red(f"Aduuh gapunya koin euy, sekarang ada {coin}")
            return False, 0

        coin_sell = percentage / 100 * coin
        target_price = self.get_best_bids_price()
        if last_buy_price > 0:
            est_profit = round((target_price - last_buy_price) / target_price * 100, 2)
            logger.success(f"Profit Jual: {est_profit}%")

        logger.warning(
            "Jual {}, koin: {}, Dengan harga {}",
            self.config["symbol"],
            coin_sell,
            target_price,
        )
        # indodax.create_order('BTC/IDR', 'limit', 'sell', 0.00004784, 540542000)
        response = self.api.create_order(
            self.config["symbol"], "limit", "sell", coin_sell, target_price
        )
        return response.get("info").get("success") == "1", coin_sell, target_price
