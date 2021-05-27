from tukang_kripto import configs


class AppState:
    def __init__(self, name="BTC-USDT"):
        self.action = "WAIT"
        self.buy_count = 0
        self.buy_state = ""
        self.buy_sum = 0
        self.eri_text = ""
        self.fib_high = 0
        self.fib_low = 0
        self.iterations = 0
        self.last_action = ""
        self.last_buy_size = 0
        self.last_buy_price = 0
        self.last_buy_filled = 0
        self.last_sell_price = 0
        # self.last_buy_value = 0
        self.last_buy_fee = 0
        self.last_buy_high = 0
        self.last_df_index = ""
        self.last_close_price = 0
        self.sell_count = 0
        self.sell_sum = 0
        self.coin_name = name
        self.configs = configs.coin(name)
        self.config_trade = configs.coin(name).get("indodax", {})
        self.debug = configs.run_in_debug()
        self.market_price = 0
