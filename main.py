import os
import sched
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
import requests
from pandas import DataFrame, Series

DEFAULT_MARKET = "BTC-USDT"
SUPPORTED_GRANULARITY = [60, 300, 900, 3600, 21600, 86400]
FREQUENCY_EQUIVALENTS = ["T", "5T", "15T", "H", "6H", "D"]
MAX_GRANULARITY = max(SUPPORTED_GRANULARITY)
s = sched.scheduler(time.time, time.sleep)


class PublicAPI:
    def __init__(self) -> None:
        # options
        self.debug = False
        self.die_on_api_error = False
        self.api_url = "https://api.pro.coinbase.com"

    def getHistoricalData(
        self,
        market: str = DEFAULT_MARKET,
        granularity: int = MAX_GRANULARITY,
        iso8601start: str = "",
        iso8601end: str = "",
    ) -> pd.DataFrame:

        # validates granularity is an integer
        if not isinstance(granularity, int):
            raise TypeError("Granularity integer required.")

        # validates the granularity is supported by Coinbase Pro
        if not granularity in SUPPORTED_GRANULARITY:
            raise TypeError(
                "Granularity options: " + ", ".join(map(str, SUPPORTED_GRANULARITY))
            )

        # validates the ISO 8601 start date is a string (if provided)
        if not isinstance(iso8601start, str):
            raise TypeError("ISO8601 start integer as string required.")

        # validates the ISO 8601 end date is a string (if provided)
        if not isinstance(iso8601end, str):
            raise TypeError("ISO8601 end integer as string required.")

        # if only a start date is provided
        if iso8601start != "" and iso8601end == "":
            multiplier = int(granularity / 60)

            # calculate the end date using the granularity
            iso8601end = str(
                (
                    datetime.strptime(iso8601start, "%Y-%m-%dT%H:%M:%S.%f")
                    + timedelta(minutes=granularity * multiplier)
                ).isoformat()
            )

        # resp = self.authAPI('GET', f"products/{market}/candles?granularity={granularity}&start={iso8601start}&end={iso8601end}")
        now = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        print(f"Checking Coin {market} Candles at {now}")
        resp = requests.get(
            f"{self.api_url}/products/{market}/candles?granularity={granularity}&start={iso8601start}&end={iso8601end}"
        ).json()
        # print(resp)
        # convert the API response into a Pandas DataFrame
        df = pd.DataFrame(
            resp, columns=["epoch", "low", "high", "open", "close", "volume"]
        )
        # reverse the order of the response with earliest last
        df = df.iloc[::-1].reset_index()

        try:
            freq = FREQUENCY_EQUIVALENTS[SUPPORTED_GRANULARITY.index(granularity)]
        except:
            freq = "D"

        # convert the DataFrame into a time series with the date as the index/key
        try:
            tsidx = pd.DatetimeIndex(
                pd.to_datetime(df["epoch"], unit="s"), dtype="datetime64[ns]", freq=freq
            )
            df.set_index(tsidx, inplace=True)
            df = df.drop(columns=["epoch", "index"])
            df.index.names = ["ts"]
            df["date"] = tsidx
        except ValueError:
            tsidx = pd.DatetimeIndex(
                pd.to_datetime(df["epoch"], unit="s"), dtype="datetime64[ns]"
            )
            df.set_index(tsidx, inplace=True)
            df = df.drop(columns=["epoch", "index"])
            df.index.names = ["ts"]
            df["date"] = tsidx

        df["market"] = market
        df["granularity"] = granularity

        # re-order columns
        df = df[
            ["date", "market", "granularity", "low", "high", "open", "close", "volume"]
        ]

        return df


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

        self.df["goldencross"] = self.df["sma5"] > self.df["sma20"]

    def addDeathCross(self) -> None:
        """Add Death Cross SMA5 over SMA20"""

        if "sma5" not in self.df:
            self.addSMA(5)

        if "sma20" not in self.df:
            self.addSMA(20)

        self.df["deathcross"] = self.df["sma5"] < self.df["sma20"]

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


class AppState:
    def __init__(self):
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
        # self.last_buy_value = 0
        self.last_buy_fee = 0
        self.last_buy_high = 0
        self.last_df_index = ""
        self.sell_count = 0
        self.sell_sum = 0


def getInterval(df: pd.DataFrame = pd.DataFrame()) -> pd.DataFrame:
    if len(df) == 0:
        return df
    else:
        # most recent entry
        return df.tail(1)


def getAction(
    now: datetime = datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
    app: PublicAPI = None,
    price: float = 0,
    df: pd.DataFrame = pd.DataFrame(),
    df_last: pd.DataFrame = pd.DataFrame(),
    last_action: str = "WAIT",
    debug: bool = False,
) -> str:

    ema12gtema26co = bool(df_last["ema12gtema26co"].values[0])
    ema12ltema26co = bool(df_last["ema12ltema26co"].values[0])

    # criteria for a buy signal
    if ema12gtema26co is True and last_action != "BUY":
        return "BUY"

    # criteria for a sell signal
    elif ema12ltema26co is True and last_action not in ["", "SELL"]:
        return "SELL"

    return "WAIT"


def create_alert(title="Hey, there", message="I have something"):
    command = f"""
    osascript -e 'display notification "{message}" with title "{title}"'
    """
    os.system(command)

def print_red(message):
    # print to console with color red
    print(f"\033[91m{message}\033[0m")


def print_green(message):
    # print to console with color red
    print(f"\033[92m{message}\033[0m")


def print_yellow(message):
    # print to console with color red
    print(f"\033[93m{message}\033[0m")



def executeJob(
    sc,
    app=PublicAPI(),
    state=AppState(),
    trading_data=pd.DataFrame(),
    market="BTC-USDT",
    pool_time=900,
):
    """Trading bot job which runs at a scheduled interval"""
    # increment state.iterations
    state.iterations = state.iterations + 1
    # supported time:
    # 1m = 60
    # 5m = 300
    # 15m = 900
    # 1h = 3600
    # 6h = 21600
    # 1d = 86400
    trading_data = app.getHistoricalData(market, 900)
    # analyse the market data
    trading_dataCopy = trading_data.copy()
    ta = TechnicalAnalysis(trading_dataCopy)
    ta.addAll()
    df = ta.getDataFrame()
    df_last = getInterval(df)
    if len(df_last) > 0:
        price = float(df_last["close"].values[0])
        now = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        state.action = getAction(now, app, price, df, df_last, state.last_action, False)
        # if a buy signal
        if state.action == "BUY":
            state.last_buy_price = price
            state.last_buy_high = state.last_buy_price
            print_green(f"=>   {state.action} @{price}")
            create_alert(state.action, f"I think the {market} is intresting at {price}!")
        elif state.action == "SELL":
            print_red(f"=>   {state.action} @{price}")
        else:
            print_yellow(f"=>   {state.action} @{price}")
            
        # poll every x second
        # 900 = 15 minutes
        list(map(s.cancel, s.queue))
        s.enter(pool_time, 1, executeJob, (sc, app, state))


if __name__ == "__main__":
    print("Bot lagi gelar lapak")
    # executeJob('asal')
    state = AppState()
    state2 = AppState()
    state3 = AppState()
    state4 = AppState()
    state5 = AppState()
    state6 = AppState()
    state7 = AppState()
    state8 = AppState()
    app = PublicAPI()
    s = sched.scheduler(time.time, time.sleep)

    def runApp():
        # run the first job immediately after starting
        executeJob(s, app, state, market="MATIC-USD", pool_time=900)
        executeJob(s, app, state2, market="1INCH-USD", pool_time=901)
        executeJob(s, app, state3, market="BCH-USD", pool_time=902)
        executeJob(s, app, state4, market="DASH-USD", pool_time=903)
        executeJob(s, app, state5, market="LTC-USD", pool_time=904)
        executeJob(s, app, state6, market="ETH-USDT", pool_time=905)
        executeJob(s, app, state7, market="BTC-USDT", pool_time=906)
        executeJob(s, app, state8, market="ETC-USD", pool_time=907)

        s.run()

    try:
        runApp()
    # catches a keyboard break of app, exits gracefully
    except KeyboardInterrupt:
        print(datetime.now(), "Tutup lapak")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
