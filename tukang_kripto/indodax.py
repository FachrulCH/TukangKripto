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
            return book["bids"][0][0]
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

    def buy_coin(self, percentage=100, limit_budget=0):
        idr = self.get_balance_idr()
        budget = int(percentage / 100 * idr)

        if budget < 10000:
            print_red(f"Aduuh kurang budget euy, sekarang ada {idr} maunya {budget}")
            return False, 0

        if limit_budget > 10000:
            print("masuk limit")
            budget = limit_budget

        target_price = self.get_best_bids_price()
        coin_buy = round(budget / target_price, 8)
        logger.info(
            "Beli {}, Budget {}, koin: {}, Dengan harga {}", self.config["symbol"], budget, coin_buy, target_price
        )
        response = self.api.create_order(
            self.config["symbol"], "limit", "buy", coin_buy, target_price
        )
        return response.get("info").get("success") == "1", coin_buy

    def sell_coin(self, percentage=100):
        coin = self.get_balance_coin()

        if coin < 0:
            print_red(f"Aduuh gapunya koin euy, sekarang ada {coin}")
            return False, 0

        coin_sell = percentage / 100 * coin
        target_price = self.get_best_bids_price()
        logger.info(
            "Jual ", self.config["symbol"], "limit", "sell", coin_sell, target_price
        )
        response = self.api.create_order(
            self.config["symbol"], "limit", "sell", coin_sell, target_price
        )
        return response.get("info").get("success") == "1", coin_sell
