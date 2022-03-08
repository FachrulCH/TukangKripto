from numpy import mean
from numpy import sum as np_sum
from pandas import DataFrame, Series


class Chartis:
    fast_periods = 5
    slow_periods = 20
    fast_sma = "sma5"
    fast_ema = "ema5"
    slow_sma = "sma20"
    slow_ema = "ema20"

    def __init__(self, data=DataFrame()):
        if not isinstance(data, DataFrame):
            raise TypeError("Data is not accepted, required Pandas dataframe")

        if list(data.keys()) != [
            "date", "market", "granularity",
            "low", "high", "open", "close", "volume"
        ]:
            raise ValueError("Data is not contain expected format")

        if not data["close"].dtype not in ["float64", "int64"]:
            raise AttributeError("DataFrame column is not int64 or float64")

        self.df = data
        self.levels = []
        self.previous_5_sma = None
        self.previous_20_sma = None
        self.previous_5_ema = None
        self.previous_20_ema = None

    def indicators(self):
        self.add_golden_cross()
        self.add_death_cross()

    def validate_period(self, period, minimum=5, maximum=200):
        if not isinstance(period, int):
            raise TypeError("Period parameter is not valid")

        if period < minimum or period > maximum:
            raise ValueError("Period is out of range")

        if len(self.df) < period:
            raise Exception("Data range too small.")

    def simple_moving_average(self, period: int) -> float:
        """Calculates the Simple Moving Average (SMA)"""

        self.validate_period(period)
        return self.df.close.rolling(period, min_periods=1).mean()

    def exponential_moving_average(self, period: int):
        """Calculates the Exponential Moving Average (EMA)"""

        self.validate_period(period)
        return self.df.close.ewm(span=period, adjust=False).mean()

    def add_ema(self, period: int) -> None:
        """Adds the Exponential Moving Average (EMA) the DateFrame"""

        self.validate_period(period)
        self.df["ema" + str(period)] = self.exponential_moving_average(period)

    def add_sma(self, period: int) -> None:
        """Add the Simple Moving Average (SMA) to the DataFrame"""

        self.validate_period(period)
        self.df["sma" + str(period)] = self.simple_moving_average(period)

    def verify_ma_present(self):
        sma5 = self.fast_sma
        sma20 = self.slow_sma
        ema5 = self.fast_ema
        ema20 = self.slow_ema
        period5 = self.fast_periods
        period20 = self.slow_periods

        if sma5 not in self.df:
            self.add_sma(period5)

        if sma20 not in self.df:
            self.add_sma(period20)

        if ema5 not in self.df:
            self.add_ema(period5)

        if ema20 not in self.df:
            self.add_ema(period20)

        self.previous_5_sma = self.df[sma5].shift(1)
        self.previous_20_sma = self.df[sma20].shift(1)

    def add_golden_cross(self) -> None:
        """Add Golden Cross MA5 over MA20"""
        self.verify_ma_present()
        sma5 = self.fast_sma
        sma20 = self.slow_sma
        ema5 = self.fast_ema
        ema20 = self.slow_ema

        # self.df["goldencross"] = self.df["sma5"] > self.df["sma20"]
        self.df["golden_cross_sma"] = (self.df[sma5] > self.df[sma20]) & (self.previous_5_sma <= self.previous_20_sma)
        self.df["golden_cross_ema"] = (self.df[ema5] > self.df[ema20]) & (self.previous_5_ema <= self.previous_20_ema)

    def add_death_cross(self) -> None:
        """Add Death Cross MA5 over MA20"""
        self.verify_ma_present()
        sma5 = self.fast_sma
        sma20 = self.slow_sma
        ema5 = self.fast_ema
        ema20 = self.slow_ema

        self.df["death_cross_sma"] = (self.df[sma5] < self.df[sma20]) & (self.previous_5_sma >= self.previous_20_sma)
        self.df["death_cross_ema"] = (self.df[ema5] < self.df[ema20]) & (self.previous_5_ema >= self.previous_20_ema)

    def change_pct(self) -> DataFrame:
        """Close change percentage"""

        close_pc = self.df["close"] / self.df["close"].shift(1) - 1
        close_pc = close_pc.fillna(0)
        self.df["close_pc"] = close_pc
        # cumulative returns
        self.df["close_cpc"] = (1 + self.df["close_pc"]).cumprod()

    def __calculate_support_resistance_levels(self):
        """Support and Resistance levels. (private function)"""

        for i in range(2, self.df.shape[0] - 2):
            if self.__is_support(self.df, i):
                l = self.df["low"][i]
                if self.__is_far_from_level(l):
                    self.levels.append((i, l))
            elif self.__is_resistance(self.df, i):
                l = self.df["high"][i]
                if self.__is_far_from_level(l):
                    self.levels.append((i, l))
        return self.levels

    def __is_support(self, df, i) -> bool:
        """Is support level? (private function)"""

        c1 = df["low"][i] < df["low"][i - 1]
        c2 = df["low"][i] < df["low"][i + 1]
        c3 = df["low"][i + 1] < df["low"][i + 2]
        c4 = df["low"][i - 1] < df["low"][i - 2]
        support = c1 and c2 and c3 and c4
        return support

    def __is_resistance(self, df, i) -> bool:
        """Is resistance level? (private function)"""

        c1 = df["high"][i] > df["high"][i - 1]
        c2 = df["high"][i] > df["high"][i + 1]
        c3 = df["high"][i + 1] > df["high"][i + 2]
        c4 = df["high"][i - 1] > df["high"][i - 2]
        resistance = c1 and c2 and c3 and c4
        return resistance

    def __is_far_from_level(self, l) -> float:
        """Is far from support level? (private function)"""

        s = mean(self.df["high"] - self.df["low"])
        return np_sum([abs(l - x) < s for x in self.levels]) == 0

    def get_support_resistance_levels(self) -> Series:
        """Calculate the Support and Resistance Levels"""

        self.levels = []
        self.__calculate_support_resistance_levels()
        levels_ts = {}
        for level in self.levels:
            levels_ts[self.df.index[level[0]]] = level[1]
        # add the support levels to the DataFrame
        return Series(levels_ts)

    def get_resistance(self, price: float = 0) -> float:
        if isinstance(price, int) or isinstance(price, float):
            if price > 0:
                sr = self.get_support_resistance_levels()
                for r in sr.sort_values():
                    if r > price:
                        return r

        return price
