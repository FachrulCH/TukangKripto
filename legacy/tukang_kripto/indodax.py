import datetime
import math
import os

import ccxt
from loguru import logger

from tukang_kripto import utils
from tukang_kripto.technical_analysis import calculate_profit
from tukang_kripto.utils import get_latest_csv_transaction, in_rupiah, print_red


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

    def get_best_ask_price(self, stop_loss):
        # harga jual
        book = self.api.fetch_order_book(self.config["symbol"])
        if stop_loss:
            sell_price = book["asks"][0][0]
            print_red(f"RUGI BANDAR, HAKA aja lah {sell_price}")
            return int(sell_price)

        if self.config.get("sell_with_profit_only", False):
            sell_price = book["asks"][3][0]
            new_sell_price = self.calculate_sell_price(sell_price)
            logger.warning(
                f"JUAL UNTUNG: {in_rupiah(sell_price)} --> {in_rupiah(new_sell_price)}"
            )
            return int(new_sell_price)
        return int(book["asks"][2][0])

    def get_top_sale_price(self, index=0):
        book = self.api.fetch_order_book(self.config["symbol"]).get("asks")
        # return top 3 selling price
        return int(book[index][0])

    def get_best_bids_price(self):
        # harga beli
        try:
            book = self.api.fetch_order_book(self.config["symbol"])
            order_book_price = book["bids"][1][0]
            return order_book_price
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

    def get_balance_all(self):
        balances = self.api.fetch_free_balance()
        return balances

    def buy_coin(self, percentage=100, limit_budget=0):
        idr = self.get_balance_idr()
        budget = int(percentage / 100 * idr)

        if budget < 10000:
            print_red(f"Aduuh kurang budget euy, sekarang ada {idr} maunya {budget}")
            return False, 0, 0, 0

        if 10000 < limit_budget < idr:
            print("Using limited budget")
            budget = limit_budget

        target_price = self.get_best_bids_price()
        coin_buy = round(budget / target_price, 8)
        logger.warning(
            "BELI {}, Budget {}, koin: {}, Dengan harga {}",
            self.config["symbol"],
            budget,
            coin_buy,
            target_price,
        )
        # indodax.create_order('BTC/IDR', 'limit', 'buy', 0.00004784, 540542000)

        response = self.api.create_order(
            self.config["symbol"], "limit", "buy", coin_buy, target_price
        )
        return (
            response.get("info").get("success") == "1",
            coin_buy,
            target_price,
            budget,
        )

    def sell_coin(self, percentage=100, stop_loss=False):
        coin = self.get_balance_coin()
        if math.isclose(coin, 0.0):
            print_red(f"Aduuh gapunya koin euy, sekarang ada {coin}")
            return False, -10, 0, 0

        coin_sell = round(percentage / 100 * coin, 8)
        sell_at = self.get_best_ask_price(stop_loss)
        buy_at = self.get_last_buy_price()
        profit = calculate_profit(buy_at, sell_at)
        estimate_amount = coin_sell * sell_at
        logger.success(
            "JUAL {} Posisi {}%:  Koin {}, beli {}, jual {}",
            self.config["symbol"],
            profit,
            coin_sell,
            in_rupiah(buy_at),
            in_rupiah(sell_at),
        )

        # indodax.create_order('BTC/IDR', 'limit', 'sell', 0.00004784, 540542000)
        response = self.api.create_order(
            self.config["symbol"], "limit", "sell", coin_sell, sell_at
        )
        return (
            response.get("info").get("success") == "1",
            coin_sell,
            sell_at,
            estimate_amount,
        )

    def get_history_trade(self, order=None, since=None, params={}):
        self.api.load_markets()
        if since is None:
            yesterday = datetime.date.today() - datetime.timedelta(1)
            since = int(yesterday.strftime("%s"))

        request = {"order": "desc", "since": since}
        market = self.api.market(self.config["symbol"])
        request["pair"] = market["id"]
        response = self.api.privatePostTradeHistory(self.api.extend(request, params))
        data = response["return"]["trades"]
        if order is not None:
            return utils.filter_by(data, "type", order)
        else:
            return data

    def get_latest_trade_data(self, order="buy"):
        trade_data = self.get_history_trade(order)
        last_trade = trade_data[0]
        return {"last_buy_price": last_trade["price"]}

    def calculate_sell_price(self, target_sell_price):
        min_profit = float(self.config.get("minimum_profit_percentage", 0))
        last_price = self.get_last_buy_price()
        if last_price:
            min_sell_profit = round(last_price + (last_price * min_profit / 100))
            logger.warning(
                "\n=>   Perhitungan cuan target_sell_price: {} min_sell_profit: {}",
                in_rupiah(target_sell_price),
                in_rupiah(min_sell_profit),
            )
            if target_sell_price < min_sell_profit:
                return min_sell_profit
        return target_sell_price

    def get_last_buy_price(self):
        last_buy = get_latest_csv_transaction(self.config["symbol"], "buy")
        if len(last_buy) > 1:
            # found data
            return float(last_buy[4])
        print("Last buy price not found")
        return 0
