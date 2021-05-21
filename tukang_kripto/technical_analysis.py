from pandas import DataFrame


class TechnicalAnalysis:
    def __init__(self, data=DataFrame()) -> None:
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

    def simpleMovingAverage(self, period: int) -> float:
        """Calculates the Simple Moving Average (SMA)"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period < 5 or period > 200:
            raise ValueError("Period is out of range")

        if len(self.df) < period:
            raise Exception("Data range too small.")

        return self.df.close.rolling(period, min_periods=1).mean()

    def exponentialMovingAverage(self, period: int) -> float:
        """Calculates the Exponential Moving Average (EMA)"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period < 5 or period > 200:
            raise ValueError("Period is out of range")

        if len(self.df) < period:
            raise Exception("Data range too small.")

        return self.df.close.ewm(span=period, adjust=False).mean()

    def addSMA(self, period: int) -> None:
        """Add the Simple Moving Average (SMA) to the DataFrame"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period < 5 or period > 200:
            raise ValueError("Period is out of range")

        if len(self.df) < period:
            raise Exception("Data range too small.")

        self.df["sma" + str(period)] = self.simpleMovingAverage(period)

    def addEMA(self, period: int) -> None:
        """Adds the Exponential Moving Average (EMA) the DateFrame"""

        if not isinstance(period, int):
            raise TypeError("Period parameter is not perioderic.")

        if period < 5 or period > 200:
            raise ValueError("Period is out of range")

        if len(self.df) < period:
            raise Exception("Data range too small.")

        self.df["ema" + str(period)] = self.exponentialMovingAverage(period)

    def addGoldenCross(self) -> None:
        """Add Golden Cross SMA5 over SMA20"""

        if "sma5" not in self.df:
            self.addSMA(5)

        if "sma20" not in self.df:
            self.addSMA(20)

        # self.df["goldencross"] = self.df["sma5"] > self.df["sma20"]
        previous_5 = self.df['sma5'].shift(1)
        previous_20 = self.df['sma20'].shift(1)
        self.df["goldencross"] = ((self.df['sma5'] > self.df['sma20']) & (previous_5 <= previous_20))

    def addDeathCross(self) -> None:
        """Add Death Cross SMA5 over SMA20"""

        if "sma5" not in self.df:
            self.addSMA(5)

        if "sma20" not in self.df:
            self.addSMA(20)

        # self.df["deathcross"] = self.df["sma5"] < self.df["sma20"]
        previous_5 = self.df['sma5'].shift(1)
        previous_20 = self.df['sma20'].shift(1)
        self.df["deathcross"] = ((self.df['sma5'] < self.df['sma20']) & (previous_5 >= previous_20))

    def addEMABuySignals(self) -> None:
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
            self.addEMA(12)
            self.addEMA(26)

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

    def addSMABuySignals(self) -> None:
        """Adds the SMA50/SMA200 buy and sell signals to the DataFrame"""

        if not isinstance(self.df, DataFrame):
            raise TypeError('Pandas DataFrame required.')

        if not 'close' in self.df.columns:
            raise AttributeError("Pandas DataFrame 'close' column required.")

        if not self.df['close'].dtype == 'float64' and not self.df['close'].dtype == 'int64':
            raise AttributeError(
                "Pandas DataFrame 'close' column not int64 or float64.")

        if not 'sma50' or not 'sma200' in self.df.columns:
            self.addSMA(50)
            self.addSMA(200)

        # true if SMA50 is above the SMA200
        self.df['sma50gtsma200'] = self.df.sma50 > self.df.sma200
        # true if the current frame is where SMA50 crosses over above
        self.df['sma50gtsma200co'] = self.df.sma50gtsma200.ne(self.df.sma50gtsma200.shift())
        self.df.loc[self.df['sma50gtsma200'] == False, 'sma50gtsma200co'] = False

        # true if the SMA50 is below the SMA200
        self.df['sma50ltsma200'] = self.df.sma50 < self.df.sma200
        # true if the current frame is where SMA50 crosses over below
        self.df['sma50ltsma200co'] = self.df.sma50ltsma200.ne(self.df.sma50ltsma200.shift())
        self.df.loc[self.df['sma50ltsma200'] == False, 'sma50ltsma200co'] = False

    def addAll(self) -> None:
        """Adds analysis to the DataFrame"""
        self.addSMA(20)
        self.addSMA(50)
        # self.addSMA(200)
        self.addEMA(12)
        self.addEMA(26)
        self.addGoldenCross()
        self.addDeathCross()
        self.addEMABuySignals()

    def getDataFrame(self) -> DataFrame:
        """Returns the Pandas DataFrame"""
        return self.df
