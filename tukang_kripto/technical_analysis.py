from datetime import datetime

import pandas as pd
from loguru import logger
from numpy import maximum, minimum, ndarray
from pandas import DataFrame, Series

from tukang_kripto.app_state import AppState
from tukang_kripto.public_API import PublicAPI


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
        self.add_golden_cross()
        self.add_death_cross()
        self.add_ema_buy_signals()

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

    if golden_cross_ema and last_action != "BUY":
        return "BUY"

    # criteria for a sell signal
    elif death_cross_ema and last_action not in ["", "SELL"]:
        return "SELL"

    return "WAIT"
