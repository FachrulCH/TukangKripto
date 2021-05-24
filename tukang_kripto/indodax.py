import os

import ccxt


class Indodax:
    def __init__(self, config):
        key = os.getenv('INDODAX_KEY')
        secret = os.getenv('INDODAX_SECRET')
        self.api = ccxt.indodax({
            'apiKey': key,
            'secret': secret,
        })
        self.config = config

    def get_best_ask_price(self):
        # harga jual
        book = self.api.fetch_order_book(self.config['symbol'])
        return book['asks'][0][0]

    def get_best_bids_price(self):
        # harga beli
        book = self.api.fetch_order_book(self.config['symbol'])
        return book['bids'][0][0]
