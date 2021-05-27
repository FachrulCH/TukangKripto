from datetime import datetime

import pandas as pd
from loguru import logger
from numpy import floor, maximum, mean, minimum, nan, ndarray
from numpy import sum as np_sum
from numpy import where
from pandas import DataFrame, Series

from tukang_kripto.app_state import AppState
from tukang_kripto.public_API import PublicAPI
from tukang_kripto.utils import get_latest_csv_transaction, in_rupiah


class TechnicalAnalysis:
    def __init__(self, data=DataFrame(), state=AppState()) -> None:
        """Technical Analysis object model

        Parameters
        ----------
        data : Pandas Time Series
            data[ts] = [ 'date', 'market', 'granularity', 'low', 'high', 'open', 'close', 'volume' ]
        """

        if not isinstance(data, DataFrame):
            raise TypeError("Data is not a Pandas dataframe.")

        if list(data.keys()) != [
            "date",
            "market",
            "granularity",
            "low",
            "high",
            "open",
            "close",
            "volume",
        ]:
            raise ValueError(
                "Data not not contain date, market, granularity, low, high, open, close, volume"
            )

        if not "close" in data.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        if not data["close"].dtype == "float64" and not data["close"].dtype == "int64":
            raise AttributeError(
                "Pandas DataFrame 'close' column not int64 or float64."
            )

        self.df = data
        self.levels = []

    def simple_moving_average(self, period: int) -> float:
        """Calculates the Simple Moving Average (SMA)"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period < 5 or period > 200:
            raise ValueError("Period is out of range")

        if len(self.df) < period:
            raise Exception("Data range too small.")

        return self.df.close.rolling(period, min_periods=1).mean()

    def exponential_moving_average(self, period: int) -> float:
        """Calculates the Exponential Moving Average (EMA)"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period < 5 or period > 200:
            raise ValueError("Period is out of range")

        if len(self.df) < period:
            raise Exception("Data range too small.")

        return self.df.close.ewm(span=period, adjust=False).mean()

    def add_sma(self, period: int) -> None:
        """Add the Simple Moving Average (SMA) to the DataFrame"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period < 5 or period > 200:
            raise ValueError("Period is out of range")

        if len(self.df) < period:
            raise Exception("Data range too small.")

        self.df["sma" + str(period)] = self.simple_moving_average(period)

    def add_ema(self, period: int) -> None:
        """Adds the Exponential Moving Average (EMA) the DateFrame"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period < 5 or period > 200:
            raise ValueError("Period is out of range")

        if len(self.df) < period:
            raise Exception("Data range too small.")

        self.df["ema" + str(period)] = self.exponential_moving_average(period)

    def add_golden_cross(self) -> None:
        """Add Golden Cross SMA5 over SMA20"""

        if "sma5" not in self.df:
            self.add_sma(5)

        if "sma20" not in self.df:
            self.add_sma(20)

        # self.df["goldencross"] = self.df["sma5"] > self.df["sma20"]
        previous_5 = self.df["sma5"].shift(1)
        previous_20 = self.df["sma20"].shift(1)
        self.df["golden_cross"] = (self.df["sma5"] > self.df["sma20"]) & (
            previous_5 <= previous_20
        )

        # EMA
        if not "ema5" or not "ema20" in self.df.columns:
            self.add_ema(5)
            self.add_ema(20)
        previous_5 = self.df["ema5"].shift(1)
        previous_20 = self.df["ema20"].shift(1)
        self.df["golden_cross_ema"] = (self.df["ema5"] > self.df["ema20"]) & (
            previous_5 <= previous_20
        )

    def add_death_cross(self) -> None:
        """Add Death Cross SMA5 over SMA20"""

        if "sma5" not in self.df:
            self.add_sma(5)

        if "sma20" not in self.df:
            self.add_sma(20)

        # self.df["deathcross"] = self.df["sma5"] < self.df["sma20"]
        previous_5 = self.df["sma5"].shift(1)
        previous_20 = self.df["sma20"].shift(1)
        self.df["deathcross"] = (self.df["sma5"] < self.df["sma20"]) & (
            previous_5 >= previous_20
        )

        # EMA
        if not "ema5" or not "ema20" in self.df.columns:
            self.add_ema(5)
            self.add_ema(20)
        previous_5e = self.df["ema5"].shift(1)
        previous_20e = self.df["ema20"].shift(1)
        self.df["death_cross_ema"] = (self.df["ema5"] < self.df["ema20"]) & (
            previous_5e >= previous_20e
        )

    def add_ema_buy_signals(self) -> None:
        """Adds the EMA12/EMA26 buy and sell signals to the DataFrame"""

        if not isinstance(self.df, DataFrame):
            raise TypeError("Pandas DataFrame required.")

        if not "close" in self.df.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        if (
            not self.df["close"].dtype == "float64"
            and not self.df["close"].dtype == "int64"
        ):
            raise AttributeError(
                "Pandas DataFrame 'close' column not int64 or float64."
            )

        if not "ema12" or not "ema26" in self.df.columns:
            self.add_ema(12)
            self.add_ema(26)

        # true if EMA12 is above the EMA26
        self.df["ema12gtema26"] = self.df.ema12 > self.df.ema26
        # true if the current frame is where EMA12 crosses over above
        self.df["ema12gtema26co"] = self.df.ema12gtema26.ne(
            self.df.ema12gtema26.shift()
        )
        self.df.loc[self.df["ema12gtema26"] == False, "ema12gtema26co"] = False

        # true if the EMA12 is below the EMA26
        self.df["ema12ltema26"] = self.df.ema12 < self.df.ema26
        # true if the current frame is where EMA12 crosses over below
        self.df["ema12ltema26co"] = self.df.ema12ltema26.ne(
            self.df.ema12ltema26.shift()
        )
        self.df.loc[self.df["ema12ltema26"] == False, "ema12ltema26co"] = False

    def add_sma_buy_signals(self) -> None:
        """Adds the SMA50/SMA200 buy and sell signals to the DataFrame"""

        if not isinstance(self.df, DataFrame):
            raise TypeError("Pandas DataFrame required.")

        if not "close" in self.df.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        if (
            not self.df["close"].dtype == "float64"
            and not self.df["close"].dtype == "int64"
        ):
            raise AttributeError(
                "Pandas DataFrame 'close' column not int64 or float64."
            )

        if not "sma50" or not "sma200" in self.df.columns:
            self.add_sma(50)
            self.add_sma(200)

        # true if SMA50 is above the SMA200
        self.df["sma50gtsma200"] = self.df.sma50 > self.df.sma200
        # true if the current frame is where SMA50 crosses over above
        self.df["sma50gtsma200co"] = self.df.sma50gtsma200.ne(
            self.df.sma50gtsma200.shift()
        )
        self.df.loc[self.df["sma50gtsma200"] == False, "sma50gtsma200co"] = False

        # true if the SMA50 is below the SMA200
        self.df["sma50ltsma200"] = self.df.sma50 < self.df.sma200
        # true if the current frame is where SMA50 crosses over below
        self.df["sma50ltsma200co"] = self.df.sma50ltsma200.ne(
            self.df.sma50ltsma200.shift()
        )
        self.df.loc[self.df["sma50ltsma200"] == False, "sma50ltsma200co"] = False

    def add_all(self) -> None:
        """Adds analysis to the DataFrame"""
        self.add_sma(20)
        self.add_sma(50)
        # self.addSMA(200)
        self.add_ema(12)
        self.add_ema(26)
        self.add_CMA(),
        self.add_golden_cross()
        self.add_death_cross()
        self.add_ema_buy_signals()
        self.add_fibonacci_bollinger_bands()
        self.add_relative_strength_index(14)
        self.add_MACD()
        self.add_on_balance_volume()
        self.add_elder_ray_index()
        self.add_MACD_buy_signals()
        self.add_sma_buy_signals()
        self.add_sma_buy_signals()
        self.add_MACD_buy_signals()

        """
        Candlestick References
        https://commodity.com/technical-analysis
        https://www.investopedia.com
        https://github.com/SpiralDevelopment/candlestick-patterns
        https://www.incrediblecharts.com/candlestick_patterns/candlestick-patterns-strongest.php
        """

        self.df["hammer"] = self.candle_hammer()
        self.df["shooting_star"] = self.candle_shooting_star()
        self.df["hanging_man"] = self.candle_hanging_man()
        self.df["inverted_hammer"] = self.candle_inverted_hammer()
        self.df["three_white_soldiers"] = self.candle_three_white_soldiers()
        self.df["three_black_crows"] = self.candle_three_black_crows()
        self.df["doji"] = self.candle_doji()
        self.df["three_line_strike"] = self.candle_three_line_strike()
        self.df["two_black_gapping"] = self.candle_two_black_gapping()
        self.df["morning_star"] = self.candle_morning_star()
        self.df["evening_star"] = self.candle_evening_star()
        self.df["abandoned_baby"] = self.candle_abandoned_baby()
        self.df["morning_doji_star"] = self.candle_morning_doji_star()
        self.df["evening_doji_star"] = self.candle_evening_doji_star()
        self.df["astral_buy"] = self.candle_astral_buy()
        self.df["astral_sell"] = self.candle_astral_sell()

    def get_data_frame(self) -> DataFrame:
        """Returns the Pandas DataFrame"""
        return self.df

    def candle_hammer(self) -> Series:
        """* Candlestick Detected: Hammer ("Weak - Reversal - Bullish Signal - Up"""
        return (
            (
                (self.df["high"] - self.df["low"])
                > 3 * (self.df["open"] - self.df["close"])
            )
            & (
                (
                    (self.df["close"] - self.df["low"])
                    / (0.001 + self.df["high"] - self.df["low"])
                )
                > 0.6
            )
            & (
                (
                    (self.df["open"] - self.df["low"])
                    / (0.001 + self.df["high"] - self.df["low"])
                )
                > 0.6
            )
        )

    def candle_shooting_star(self) -> Series:
        """* Candlestick Detected: Shooting Star ("Weak - Reversal - Bearish Pattern - Down")"""
        return (
            (
                (self.df["open"].shift(1) < self.df["close"].shift(1))
                & (self.df["close"].shift(1) < self.df["open"])
            )
            & (
                self.df["high"] - maximum(self.df["open"], self.df["close"])
                >= (abs(self.df["open"] - self.df["close"]) * 3)
            )
            & (
                (minimum(self.df["close"], self.df["open"]) - self.df["low"])
                <= abs(self.df["open"] - self.df["close"])
            )
        )

    def candle_hanging_man(self) -> Series:
        """* Candlestick Detected: Hanging Man ("Weak - Continuation - Bearish Pattern - Down")"""
        return (
            (
                (self.df["high"] - self.df["low"])
                > (4 * (self.df["open"] - self.df["close"]))
            )
            & (
                (
                    (self.df["close"] - self.df["low"])
                    / (0.001 + self.df["high"] - self.df["low"])
                )
                >= 0.75
            )
            & (
                (
                    (self.df["open"] - self.df["low"])
                    / (0.001 + self.df["high"] - self.df["low"])
                )
                >= 0.75
            )
            & (self.df["high"].shift(1) < self.df["open"])
            & (self.df["high"].shift(2) < self.df["open"])
        )

    def candle_inverted_hammer(self) -> Series:
        """* Candlestick Detected: Inverted Hammer ("Weak - Continuation - Bullish Pattern - Up")"""
        return (
            (
                (self.df["high"] - self.df["low"])
                > 3 * (self.df["open"] - self.df["close"])
            )
            & (
                (self.df["high"] - self.df["close"])
                / (0.001 + self.df["high"] - self.df["low"])
                > 0.6
            )
            & (
                (self.df["high"] - self.df["open"])
                / (0.001 + self.df["high"] - self.df["low"])
                > 0.6
            )
        )

    def candle_three_white_soldiers(self):
        """*** Candlestick Detected: Three White Soldiers ("Strong - Reversal - Bullish Pattern - Up")"""

        return (
            (
                (self.df["open"] > self.df["open"].shift(1))
                & (self.df["open"] < self.df["close"].shift(1))
            )
            & (self.df["close"] > self.df["high"].shift(1))
            & (
                self.df["high"] - maximum(self.df["open"], self.df["close"])
                < (abs(self.df["open"] - self.df["close"]))
            )
            & (
                (self.df["open"].shift(1) > self.df["open"].shift(2))
                & (self.df["open"].shift(1) < self.df["close"].shift(2))
            )
            & (self.df["close"].shift(1) > self.df["high"].shift(2))
            & (
                self.df["high"].shift(1)
                - maximum(self.df["open"].shift(1), self.df["close"].shift(1))
                < (abs(self.df["open"].shift(1) - self.df["close"].shift(1)))
            )
        )

    def candle_three_black_crows(self) -> Series:
        """* Candlestick Detected: Three Black Crows ("Strong - Reversal - Bearish Pattern - Down")"""
        return (
            (
                (self.df["open"] < self.df["open"].shift(1))
                & (self.df["open"] > self.df["close"].shift(1))
            )
            & (self.df["close"] < self.df["low"].shift(1))
            & (
                self.df["low"] - maximum(self.df["open"], self.df["close"])
                < (abs(self.df["open"] - self.df["close"]))
            )
            & (
                (self.df["open"].shift(1) < self.df["open"].shift(2))
                & (self.df["open"].shift(1) > self.df["close"].shift(2))
            )
            & (self.df["close"].shift(1) < self.df["low"].shift(2))
            & (
                self.df["low"].shift(1)
                - maximum(self.df["open"].shift(1), self.df["close"].shift(1))
                < (abs(self.df["open"].shift(1) - self.df["close"].shift(1)))
            )
        )

    def candle_doji(self) -> Series:
        """! Candlestick Detected: Doji ("Indecision")"""

        return (
            (
                (
                    abs(self.df["close"] - self.df["open"])
                    / (self.df["high"] - self.df["low"])
                )
                < 0.1
            )
            & (
                (self.df["high"] - maximum(self.df["close"], self.df["open"]))
                > (3 * abs(self.df["close"] - self.df["open"]))
            )
            & (
                (minimum(self.df["close"], self.df["open"]) - self.df["low"])
                > (3 * abs(self.df["close"] - self.df["open"]))
            )
        )

    def candle_three_line_strike(self) -> Series:
        """** Candlestick Detected: Three Line Strike ("Reliable - Reversal - Bullish Pattern - Up")"""

        return (
            (
                (self.df["open"].shift(1) < self.df["open"].shift(2))
                & (self.df["open"].shift(1) > self.df["close"].shift(2))
            )
            & (self.df["close"].shift(1) < self.df["low"].shift(2))
            & (
                self.df["low"].shift(1)
                - maximum(self.df["open"].shift(1), self.df["close"].shift(1))
                < (abs(self.df["open"].shift(1) - self.df["close"].shift(1)))
            )
            & (
                (self.df["open"].shift(2) < self.df["open"].shift(3))
                & (self.df["open"].shift(2) > self.df["close"].shift(3))
            )
            & (self.df["close"].shift(2) < self.df["low"].shift(3))
            & (
                self.df["low"].shift(2)
                - maximum(self.df["open"].shift(2), self.df["close"].shift(2))
                < (abs(self.df["open"].shift(2) - self.df["close"].shift(2)))
            )
            & (
                (self.df["open"] < self.df["low"].shift(1))
                & (self.df["close"] > self.df["high"].shift(3))
            )
        )

    def candle_two_black_gapping(self) -> Series:
        """*** Candlestick Detected: Two Black Gapping ("Reliable - Reversal - Bearish Pattern - Down")"""

        return (
            (
                (self.df["open"] < self.df["open"].shift(1))
                & (self.df["open"] > self.df["close"].shift(1))
            )
            & (self.df["close"] < self.df["low"].shift(1))
            & (
                self.df["low"] - maximum(self.df["open"], self.df["close"])
                < (abs(self.df["open"] - self.df["close"]))
            )
            & (self.df["high"].shift(1) < self.df["low"].shift(2))
        )

    def candle_morning_star(self) -> Series:
        """*** Candlestick Detected: Morning Star ("Strong - Reversal - Bullish Pattern - Up")"""

        return (
            (
                maximum(self.df["open"].shift(1), self.df["close"].shift(1))
                < self.df["close"].shift(2)
            )
            & (self.df["close"].shift(2) < self.df["open"].shift(2))
        ) & (
            (self.df["close"] > self.df["open"])
            & (
                self.df["open"]
                > maximum(self.df["open"].shift(1), self.df["close"].shift(1))
            )
        )

    def candle_evening_star(self) -> ndarray:
        """*** Candlestick Detected: Evening Star ("Strong - Reversal - Bearish Pattern - Down")"""

        return (
            (
                minimum(self.df["open"].shift(1), self.df["close"].shift(1))
                > self.df["close"].shift(2)
            )
            & (self.df["close"].shift(2) > self.df["open"].shift(2))
        ) & (
            (self.df["close"] < self.df["open"])
            & (
                self.df["open"]
                < minimum(self.df["open"].shift(1), self.df["close"].shift(1))
            )
        )

    def candle_abandoned_baby(self):
        """** Candlestick Detected: Abandoned Baby ("Reliable - Reversal - Bullish Pattern - Up")"""

        return (
            (self.df["open"] < self.df["close"])
            & (self.df["high"].shift(1) < self.df["low"])
            & (self.df["open"].shift(2) > self.df["close"].shift(2))
            & (self.df["high"].shift(1) < self.df["low"].shift(2))
        )

    def candle_morning_doji_star(self) -> Series:
        """** Candlestick Detected: Morning Doji Star ("Reliable - Reversal - Bullish Pattern - Up")"""

        return (self.df["close"].shift(2) < self.df["open"].shift(2)) & (
            abs(self.df["close"].shift(2) - self.df["open"].shift(2))
            / (self.df["high"].shift(2) - self.df["low"].shift(2))
            >= 0.7
        ) & (
            abs(self.df["close"].shift(1) - self.df["open"].shift(1))
            / (self.df["high"].shift(1) - self.df["low"].shift(1))
            < 0.1
        ) & (
            self.df["close"] > self.df["open"]
        ) & (
            abs(self.df["close"] - self.df["open"]) / (self.df["high"] - self.df["low"])
            >= 0.7
        ) & (
            self.df["close"].shift(2) > self.df["close"].shift(1)
        ) & (
            self.df["close"].shift(2) > self.df["open"].shift(1)
        ) & (
            self.df["close"].shift(1) < self.df["open"]
        ) & (
            self.df["open"].shift(1) < self.df["open"]
        ) & (
            self.df["close"] > self.df["close"].shift(2)
        ) & (
            (
                self.df["high"].shift(1)
                - maximum(self.df["close"].shift(1), self.df["open"].shift(1))
            )
            > (3 * abs(self.df["close"].shift(1) - self.df["open"].shift(1)))
        ) & (
            minimum(self.df["close"].shift(1), self.df["open"].shift(1))
            - self.df["low"].shift(1)
        ) > (
            3 * abs(self.df["close"].shift(1) - self.df["open"].shift(1))
        )

    def candle_evening_doji_star(self) -> Series:
        """** Candlestick Detected: Evening Doji Star ("Reliable - Reversal - Bearish Pattern - Down")"""

        return (self.df["close"].shift(2) > self.df["open"].shift(2)) & (
            abs(self.df["close"].shift(2) - self.df["open"].shift(2))
            / (self.df["high"].shift(2) - self.df["low"].shift(2))
            >= 0.7
        ) & (
            abs(self.df["close"].shift(1) - self.df["open"].shift(1))
            / (self.df["high"].shift(1) - self.df["low"].shift(1))
            < 0.1
        ) & (
            self.df["close"] < self.df["open"]
        ) & (
            abs(self.df["close"] - self.df["open"]) / (self.df["high"] - self.df["low"])
            >= 0.7
        ) & (
            self.df["close"].shift(2) < self.df["close"].shift(1)
        ) & (
            self.df["close"].shift(2) < self.df["open"].shift(1)
        ) & (
            self.df["close"].shift(1) > self.df["open"]
        ) & (
            self.df["open"].shift(1) > self.df["open"]
        ) & (
            self.df["close"] < self.df["close"].shift(2)
        ) & (
            (
                self.df["high"].shift(1)
                - maximum(self.df["close"].shift(1), self.df["open"].shift(1))
            )
            > (3 * abs(self.df["close"].shift(1) - self.df["open"].shift(1)))
        ) & (
            minimum(self.df["close"].shift(1), self.df["open"].shift(1))
            - self.df["low"].shift(1)
        ) > (
            3 * abs(self.df["close"].shift(1) - self.df["open"].shift(1))
        )

    def candle_astral_buy(self) -> Series:
        """*** Candlestick Detected: Astral Buy (Fibonacci 3, 5, 8)"""

        return (
            (self.df["close"] < self.df["close"].shift(3))
            & (self.df["low"] < self.df["low"].shift(5))
            & (self.df["close"].shift(1) < self.df["close"].shift(4))
            & (self.df["low"].shift(1) < self.df["low"].shift(6))
            & (self.df["close"].shift(2) < self.df["close"].shift(5))
            & (self.df["low"].shift(2) < self.df["low"].shift(7))
            & (self.df["close"].shift(3) < self.df["close"].shift(6))
            & (self.df["low"].shift(3) < self.df["low"].shift(8))
            & (self.df["close"].shift(4) < self.df["close"].shift(7))
            & (self.df["low"].shift(4) < self.df["low"].shift(9))
            & (self.df["close"].shift(5) < self.df["close"].shift(8))
            & (self.df["low"].shift(5) < self.df["low"].shift(10))
            & (self.df["close"].shift(6) < self.df["close"].shift(9))
            & (self.df["low"].shift(6) < self.df["low"].shift(11))
            & (self.df["close"].shift(7) < self.df["close"].shift(10))
            & (self.df["low"].shift(7) < self.df["low"].shift(12))
        )

    def candle_astral_sell(self) -> Series:
        """*** Candlestick Detected: Astral Sell (Fibonacci 3, 5, 8)"""

        return (
            (self.df["close"] > self.df["close"].shift(3))
            & (self.df["high"] > self.df["high"].shift(5))
            & (self.df["close"].shift(1) > self.df["close"].shift(4))
            & (self.df["high"].shift(1) > self.df["high"].shift(6))
            & (self.df["close"].shift(2) > self.df["close"].shift(5))
            & (self.df["high"].shift(2) > self.df["high"].shift(7))
            & (self.df["close"].shift(3) > self.df["close"].shift(6))
            & (self.df["high"].shift(3) > self.df["high"].shift(8))
            & (self.df["close"].shift(4) > self.df["close"].shift(7))
            & (self.df["high"].shift(4) > self.df["high"].shift(9))
            & (self.df["close"].shift(5) > self.df["close"].shift(8))
            & (self.df["high"].shift(5) > self.df["high"].shift(10))
            & (self.df["close"].shift(6) > self.df["close"].shift(9))
            & (self.df["high"].shift(6) > self.df["high"].shift(11))
            & (self.df["close"].shift(7) > self.df["close"].shift(10))
            & (self.df["high"].shift(7) > self.df["high"].shift(12))
        )

    def change_pct(self) -> DataFrame:
        """Close change percentage"""

        close_pc = self.df["close"] / self.df["close"].shift(1) - 1
        close_pc = close_pc.fillna(0)
        self.df["close_pc"] = close_pc
        # cumulative returns
        self.df["close_cpc"] = (1 + self.df["close_pc"]).cumprod()

    def cumulative_moving_average(self) -> float:
        """Calculates the Cumulative Moving Average (CMA)"""
        self.df["cma"] = self.df.close.expanding().mean()

    def calculate_relative_strength_index(self, series: int, interval: int = 14):
        """Calculates the RSI on a Pandas series of closing prices."""

        if not isinstance(series, Series):
            raise TypeError("Pandas Series required.")

        if not isinstance(interval, int):
            raise TypeError("Interval integer required.")

        if len(series) < interval:
            raise IndexError("Pandas Series smaller than interval.")

        diff = series.diff(1).dropna()

        sum_gains = 0 * diff
        sum_gains[diff > 0] = diff[diff > 0]
        avg_gains = sum_gains.ewm(com=interval - 1, min_periods=interval).mean()

        sum_losses = 0 * diff
        sum_losses[diff < 0] = diff[diff < 0]
        avg_losses = sum_losses.ewm(com=interval - 1, min_periods=interval).mean()

        rs = abs(avg_gains / avg_losses)
        rsi = 100 - 100 / (1 + rs)

        return rsi

    def add_fibonacci_bollinger_bands(
        self, interval: int = 20, multiplier: int = 3
    ) -> None:
        """Adds Fibonacci Bollinger Bands."""

        if not isinstance(interval, int):
            raise TypeError("Interval integer required.")

        if not isinstance(multiplier, int):
            raise TypeError("Multiplier integer required.")

        tp = (self.df["high"] + self.df["low"] + self.df["close"]) / 3
        sma = tp.rolling(interval).mean()
        sd = multiplier * tp.rolling(interval).std()

        sma = sma.fillna(0)
        sd = sd.fillna(0)

        self.df["fbb_mid"] = sma
        self.df["fbb_upper0_236"] = sma + (0.236 * sd)
        self.df["fbb_upper0_382"] = sma + (0.382 * sd)
        self.df["fbb_upper0_5"] = sma + (0.5 * sd)
        self.df["fbb_upper0_618"] = sma + (0.618 * sd)
        self.df["fbb_upper0_764"] = sma + (0.764 * sd)
        self.df["fbb_upper1"] = sma + (1 * sd)
        self.df["fbb_lower0_236"] = sma - (0.236 * sd)
        self.df["fbb_lower0_382"] = sma - (0.382 * sd)
        self.df["fbb_lower0_5"] = sma - (0.5 * sd)
        self.df["fbb_lower0_618"] = sma - (0.618 * sd)
        self.df["fbb_lower0_764"] = sma - (0.764 * sd)
        self.df["fbb_lower1"] = sma - (1 * sd)

    def get_fibonacci_retracement_levels(self, price: float = 0) -> dict:
        # validates price is numeric
        if not isinstance(price, int) and not isinstance(price, float):
            raise TypeError("Optional price is not numeric.")

        price_min = self.df.close.min()
        price_max = self.df.close.max()

        diff = price_max - price_min

        data = {}

        if price != 0 and (price <= price_min):
            data["ratio1"] = float(self.__truncate(price_min, 2))
        elif price == 0:
            data["ratio1"] = float(self.__truncate(price_min, 2))

        if price != 0 and (price > price_min) and (price <= (price_max - 0.768 * diff)):
            data["ratio1"] = float(self.__truncate(price_min, 2))
            data["ratio0_768"] = float(self.__truncate(price_max - 0.768 * diff, 2))
        elif price == 0:
            data["ratio0_768"] = float(self.__truncate(price_max - 0.768 * diff, 2))

        if (
            price != 0
            and (price > (price_max - 0.768 * diff))
            and (price <= (price_max - 0.618 * diff))
        ):
            data["ratio0_768"] = float(self.__truncate(price_max - 0.768 * diff, 2))
            data["ratio0_618"] = float(self.__truncate(price_max - 0.618 * diff, 2))
        elif price == 0:
            data["ratio0_618"] = float(self.__truncate(price_max - 0.618 * diff, 2))

        if (
            price != 0
            and (price > (price_max - 0.618 * diff))
            and (price <= (price_max - 0.5 * diff))
        ):
            data["ratio0_618"] = float(self.__truncate(price_max - 0.618 * diff, 2))
            data["ratio0_5"] = float(self.__truncate(price_max - 0.5 * diff, 2))
        elif price == 0:
            data["ratio0_5"] = float(self.__truncate(price_max - 0.5 * diff, 2))

        if (
            price != 0
            and (price > (price_max - 0.5 * diff))
            and (price <= (price_max - 0.382 * diff))
        ):
            data["ratio0_5"] = float(self.__truncate(price_max - 0.5 * diff, 2))
            data["ratio0_382"] = float(self.__truncate(price_max - 0.382 * diff, 2))
        elif price == 0:
            data["ratio0_382"] = float(self.__truncate(price_max - 0.382 * diff, 2))

        if (
            price != 0
            and (price > (price_max - 0.382 * diff))
            and (price <= (price_max - 0.286 * diff))
        ):
            data["ratio0_382"] = float(self.__truncate(price_max - 0.382 * diff, 2))
            data["ratio0_286"] = float(self.__truncate(price_max - 0.286 * diff, 2))
        elif price == 0:
            data["ratio0_286"] = float(self.__truncate(price_max - 0.286 * diff, 2))

        if price != 0 and (price > (price_max - 0.286 * diff)) and (price <= price_max):
            data["ratio0_286"] = float(self.__truncate(price_max - 0.286 * diff, 2))
            data["ratio0"] = float(self.__truncate(price_max, 2))
        elif price == 0:
            data["ratio0"] = float(self.__truncate(price_max, 2))

        if price != 0 and (price < (price_max + 0.272 * diff)) and (price >= price_max):
            data["ratio0"] = float(self.__truncate(price_max, 2))
            data["ratio1_272"] = float(self.__truncate(price_max + 0.272 * diff, 2))
        elif price == 0:
            data["ratio1_272"] = float(self.__truncate(price_max + 0.272 * diff, 2))

        if (
            price != 0
            and (price < (price_max + 0.414 * diff))
            and (price >= (price_max + 0.272 * diff))
        ):
            data["ratio1_272"] = float(self.__truncate(price_max, 2))
            data["ratio1_414"] = float(self.__truncate(price_max + 0.414 * diff, 2))
        elif price == 0:
            data["ratio1_414"] = float(self.__truncate(price_max + 0.414 * diff, 2))

        if (
            price != 0
            and (price < (price_max + 0.618 * diff))
            and (price >= (price_max + 0.414 * diff))
        ):
            data["ratio1_618"] = float(self.__truncate(price_max + 0.618 * diff, 2))
        elif price == 0:
            data["ratio1_618"] = float(self.__truncate(price_max + 0.618 * diff, 2))

        return data

    def get_fibonacci_upper(self, price: float = 0) -> float:
        if isinstance(price, int) or isinstance(price, float):
            if price > 0:
                fb = self.get_fibonacci_retracement_levels()
                for f in fb.values():
                    if f > price:
                        return f
        return price

    def get_trade_exit(self, price: float = 0) -> float:
        if isinstance(price, int) or isinstance(price, float):
            if price > 0:
                r = self.get_resistance(price)
                f = self.get_fibonacci_upper(price)
                if price < r and price < f:
                    r_margin = ((r - price) / price) * 100
                    f_margin = ((f - price) / price) * 100

                    if r_margin > 1 and f_margin > 1 and r <= f:
                        return r
                    elif r_margin > 1 and f_margin > 1 and f <= r:
                        return f
                    elif r_margin > 1 and f_margin < 1:
                        return r
                    elif f_margin > 1 and r_margin < 1:
                        return f

        return price

    def save_CSV(self, filename: str = "tradingdata.csv") -> None:
        """Saves the DataFrame to an uncompressed CSV."""

        if not isinstance(self.df, DataFrame):
            raise TypeError("Pandas DataFrame required.")

        try:
            self.df.to_csv(filename)
        except OSError:
            print("Unable to save: ", filename)

    def moving_average_convergence_divergence(self) -> DataFrame:
        """Calculates the Moving Average Convergence Divergence (MACD)"""

        if len(self.df) < 26:
            raise Exception("Data range too small.")

        if (
            not self.df["ema12"].dtype == "float64"
            and not self.df["ema12"].dtype == "int64"
        ):
            raise AttributeError(
                "Pandas DataFrame 'ema12' column not int64 or float64."
            )

        if (
            not self.df["ema26"].dtype == "float64"
            and not self.df["ema26"].dtype == "int64"
        ):
            raise AttributeError(
                "Pandas DataFrame 'ema26' column not int64 or float64."
            )

        df = DataFrame()
        df["macd"] = self.df["ema12"] - self.df["ema26"]
        df["signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        return df

    def add_MACD(self) -> None:
        """Adds the Moving Average Convergence Divergence (MACD) to the DataFrame"""

        df = self.moving_average_convergence_divergence()
        self.df["macd"] = df["macd"]
        self.df["signal"] = df["signal"]

    def add_on_balance_volume(self) -> ndarray:
        """Calculate On-Balance Volume (OBV)"""

        data = where(
            self.df["close"] == self.df["close"].shift(1),
            0,
            where(
                self.df["close"] > self.df["close"].shift(1),
                self.df["volume"],
                where(
                    self.df["close"] < self.df["close"].shift(1),
                    -self.df["volume"],
                    self.df.iloc[0]["volume"],
                ),
            ),
        ).cumsum()

        self.df["obv"] = data
        self.df["obv_pc"] = self.df["obv"].pct_change() * 100
        self.df["obv_pc"] = round(self.df["obv_pc"].fillna(0), 2)

    def add_relative_strength_index(self, period) -> DataFrame:
        """Calculate the Relative Strength Index (RSI)"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period < 7 or period > 21:
            raise ValueError("Period is out of range")

        # calculate relative strength index
        rsi = self.calculate_relative_strength_index(self.df["close"], period)
        # default to midway-50 for first entries
        rsi = rsi.fillna(50)
        self.df["rsi" + str(period)] = rsi
        self.df["rsi" + str(period)] = self.df["rsi" + str(period)].replace(nan, 50)

    def relative_strength_index(self, period) -> DataFrame:
        """Calculate the Relative Strength Index (RSI)"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period < 7 or period > 21:
            raise ValueError("Period is out of range")

        # calculate relative strength index
        rsi = self.calculate_relative_strength_index(self.df["close"], period)
        # default to midway-50 for first entries
        rsi = rsi.fillna(50)
        return rsi

    def add_elder_ray_index(self) -> None:
        """Add Elder Ray Index"""

        if "ema13" not in self.df:
            self.add_ema(13)

        self.df["elder_ray_bull"] = self.df["high"] - self.df["ema13"]
        self.df["elder_ray_bear"] = self.df["low"] - self.df["ema13"]

        # bear power’s value is negative but increasing (i.e. becoming less bearish)
        # bull power’s value is increasing (i.e. becoming more bullish)
        self.df["eri_buy"] = (
            (self.df["elder_ray_bear"] < 0)
            & (self.df["elder_ray_bear"] > self.df["elder_ray_bear"].shift(1))
        ) | ((self.df["elder_ray_bull"] > self.df["elder_ray_bull"].shift(1)))

        # bull power’s value is positive but decreasing (i.e. becoming less bullish)
        # bear power’s value is decreasing (i.e., becoming more bearish)
        self.df["eri_sell"] = (
            (self.df["elder_ray_bull"] > 0)
            & (self.df["elder_ray_bull"] < self.df["elder_ray_bull"].shift(1))
        ) | (self.df["elder_ray_bear"] < self.df["elder_ray_bear"].shift(1))

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

    def print_support_resistance_level(self, price: float = 0) -> None:
        if isinstance(price, int) or isinstance(price, float):
            df = self.get_support_resistance_levels()

            if len(df) > 0:
                df_last = df.tail(1)
                if float(df_last[0]) < price:
                    print(
                        " Support level of "
                        + str(df_last[0])
                        + " formed at "
                        + str(df_last.index[0]),
                        "\n",
                    )
                elif float(df_last[0]) > price:
                    print(
                        " Resistance level of "
                        + str(df_last[0])
                        + " formed at "
                        + str(df_last.index[0]),
                        "\n",
                    )
                else:
                    print(
                        " Support/Resistance level of "
                        + str(df_last[0])
                        + " formed at "
                        + str(df_last.index[0]),
                        "\n",
                    )

    def add_CMA(self) -> None:
        """Adds the Cumulative Moving Average (CMA) to the DataFrame"""
        self.df["cma"] = self.cumulative_moving_average()

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

    def add_MACD_buy_signals(self) -> None:
        """Adds the MACD/Signal buy and sell signals to the DataFrame"""

        if not isinstance(self.df, DataFrame):
            raise TypeError("Pandas DataFrame required.")

        if not "close" in self.df.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        if (
            not self.df["close"].dtype == "float64"
            and not self.df["close"].dtype == "int64"
        ):
            raise AttributeError(
                "Pandas DataFrame 'close' column not int64 or float64."
            )

        if not "macd" or not "signal" in self.df.columns:
            self.add_MACD()
            self.add_on_balance_volume()

        # true if MACD is above the Signal
        self.df["macdgtsignal"] = self.df.macd > self.df.signal
        # true if the current frame is where MACD crosses over above
        self.df["macdgtsignalco"] = self.df.macdgtsignal.ne(
            self.df.macdgtsignal.shift()
        )
        self.df.loc[self.df["macdgtsignal"] == False, "macdgtsignalco"] = False

        # true if the MACD is below the Signal
        self.df["macdltsignal"] = self.df.macd < self.df.signal
        # true if the current frame is where MACD crosses over below
        self.df["macdltsignalco"] = self.df.macdltsignal.ne(
            self.df.macdltsignal.shift()
        )
        self.df.loc[self.df["macdltsignal"] == False, "macdltsignalco"] = False

    def __truncate(self, f, n) -> float:
        return floor(f * 10 ** n) / 10 ** n

    def calculate_relative_strength_index(
        self, series: int, interval: int = 14
    ) -> float:
        """Calculates the RSI on a Pandas series of closing prices."""

        if not isinstance(series, Series):
            raise TypeError("Pandas Series required.")

        if not isinstance(interval, int):
            raise TypeError("Interval integer required.")

        if len(series) < interval:
            raise IndexError("Pandas Series smaller than interval.")

        diff = series.diff(1).dropna()

        sum_gains = 0 * diff
        sum_gains[diff > 0] = diff[diff > 0]
        avg_gains = sum_gains.ewm(com=interval - 1, min_periods=interval).mean()

        sum_losses = 0 * diff
        sum_losses[diff < 0] = diff[diff < 0]
        avg_losses = sum_losses.ewm(com=interval - 1, min_periods=interval).mean()

        rs = abs(avg_gains / avg_losses)
        rsi = 100 - 100 / (1 + rs)

        return rsi


# ================================


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
    state=None,
) -> str:
    # ema12gtema26co = bool(df_last["ema12gtema26co"].values[0])
    ema12ltema26 = bool(df_last["ema12ltema26"].values[0])
    ema12gtema26 = bool(df_last["ema12gtema26"].values[0])
    golden_cross = bool(df_last["golden_cross"].values[0])
    golden_cross_ema = bool(df_last["golden_cross_ema"].values[0])
    death_cross_ema = bool(df_last["death_cross_ema"].values[0])

    # candlestick detection
    hammer = bool(df_last["hammer"].values[0])
    inverted_hammer = bool(df_last["inverted_hammer"].values[0])
    hanging_man = bool(df_last["hanging_man"].values[0])
    shooting_star = bool(df_last["shooting_star"].values[0])
    three_white_soldiers = bool(df_last["three_white_soldiers"].values[0])
    three_black_crows = bool(df_last["three_black_crows"].values[0])
    morning_star = bool(df_last["morning_star"].values[0])
    evening_star = bool(df_last["evening_star"].values[0])
    three_line_strike = bool(df_last["three_line_strike"].values[0])
    abandoned_baby = bool(df_last["abandoned_baby"].values[0])
    morning_doji_star = bool(df_last["morning_doji_star"].values[0])
    evening_doji_star = bool(df_last["evening_doji_star"].values[0])
    two_black_gapping = bool(df_last["two_black_gapping"].values[0])

    # criteria for a buy signal
    to_debug = (
        ema12ltema26,
        ema12gtema26,
        golden_cross,
        golden_cross_ema,
        death_cross_ema,
    )

    if state.debug:
        logger.debug(
            "ema12ltema26 {}, ema12gtema26 {}, golden_cross {}, golden_cross_ema {}, death_cross_ema {},",
            ema12ltema26,
            ema12gtema26,
            golden_cross,
            golden_cross_ema,
            death_cross_ema,
        )
        logger.debug(
            "hammer {}, inverted_hammer {}, hanging_man {}, shooting_star {}, three_white_soldiers {}, three_black_crows {}, morning_star {}, evening_star {}, three_line_strike {}, abandoned_baby {}, morning_doji_star {}, evening_doji_star {}, two_black_gapping {}",
            hammer,
            inverted_hammer,
            hanging_man,
            shooting_star,
            three_white_soldiers,
            three_black_crows,
            morning_star,
            evening_star,
            three_line_strike,
            abandoned_baby,
            morning_doji_star,
            evening_doji_star,
            two_black_gapping,
        )
        logger.debug(
            "{} {} low {}, hi {}, op {}, cl {}, vol {}, eri_buy {}, eri_sell {}, macd>signal {} {} macd<signal {} {}",
            df_last["date"].values[0],
            df_last["market"].values[0],
            df_last["low"].values[0],
            df_last["high"].values[0],
            df_last["open"].values[0],
            df_last["close"].values[0],
            df_last["volume"].values[0],
            df_last["eri_buy"].values[0],
            df_last["eri_sell"].values[0],
            df_last["macdgtsignal"].values[0],
            df_last["macdgtsignalco"].values[0],
            df_last["macdltsignal"].values[0],
            df_last["macdltsignalco"].values[0],
        )

    if stop_loss(state):
        return "SELL"

    if golden_cross_ema and last_action != "BUY":
        return "BUY"

    # criteria for a sell signal
    if death_cross_ema and last_action not in ["", "SELL"]:
        return "SELL"

    return "WAIT"


def get_last_buy_price(coin_symbol):
    last_buy = get_latest_csv_transaction(coin_symbol, "buy")
    if len(last_buy) > 1:
        # found data
        return float(last_buy[4])
    print("Last buy price not found")
    return None


def calculate_profit(buy_price, sell_price):
    if not buy_price or not sell_price:
        return 0
    return round((sell_price - buy_price) / buy_price * 100, 2)


def stop_loss(state: AppState):
    loss_rate = state.config_trade.get("maximum_loss_percentage", 0)
    if loss_rate == 0 or state.market_price == 0:
        return False

    max_loss_rate = float(loss_rate) / 100
    last_price = get_last_buy_price(state.config_trade["symbol"])
    if last_price:
        max_loss = round(last_price - (last_price * max_loss_rate))
        print("Market price: ", state.market_price)
        if state.market_price <= max_loss:
            logger.warning(
                f"STOP LOSS max_loss_rate:{max_loss_rate}, last_buy: {in_rupiah(last_price)}, max_lost: {in_rupiah(max_loss)}, market_price {in_rupiah(state.market_price)}"
            )
            return True
    logger.warning(
        f"MASIH AMAN Terkendali, lanjutkan!  max_loss_rate:{max_loss_rate}, last_buy: {in_rupiah(last_price)}, max_lost: {in_rupiah(max_loss)}, market_price {in_rupiah(state.market_price)}"
    )
    return False
