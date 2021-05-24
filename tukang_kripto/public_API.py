from datetime import datetime, timedelta

import pandas as pd
import requests

DEFAULT_MARKET = "BTC-USDT"
SUPPORTED_GRANULARITY = [60, 300, 900, 3600, 21600, 86400]
FREQUENCY_EQUIVALENTS = ["T", "5T", "15T", "H", "6H", "D"]
MAX_GRANULARITY = max(SUPPORTED_GRANULARITY)


class PublicAPI:
    def __init__(self) -> None:
        # options
        self.debug = False
        self.die_on_api_error = False
        self.api_url = "https://api.pro.coinbase.com"

    def get_historical_data(
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
        print(
            f"{now} Checking Coin '{market}' Candles at timeframe {granularity/60} minutes"
        )
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
