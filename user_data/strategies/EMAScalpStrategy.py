from freqtrade.strategy import IStrategy, IntParameter
from pandas import DataFrame
import talib.abstract as ta


class EMAScalpStrategy(IStrategy):
    """
    Aggressive EMA scalping strategy.
    Buy when fast EMA crosses above slow EMA (momentum up).
    Sell when fast EMA crosses below slow EMA or profit target hit.
    Designed for maximum trade frequency on 5m candles.
    """

    INTERFACE_VERSION = 3
    timeframe = "5m"

    minimal_roi = {
        "0":  0.01,   # 1% anytime
        "15": 0.005,  # 0.5% after 15 min
        "30": 0.002,  # 0.2% after 30 min
        "60": 0       # break-even after 1 hour
    }

    stoploss = -0.01

    trailing_stop = True
    trailing_stop_positive = 0.005
    trailing_stop_positive_offset = 0.008
    trailing_only_offset_is_reached = True

    # EMA periods — short and fast for scalping
    ema_fast = IntParameter(low=5,  high=15, default=9,  space="buy", optimize=True)
    ema_slow = IntParameter(low=16, high=30, default=21, space="buy", optimize=True)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)
        dataframe["rsi"]      = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # Fast EMA just crossed above slow EMA (momentum turning bullish)
                (dataframe["ema_fast"] > dataframe["ema_slow"]) &
                (dataframe["ema_fast"].shift(1) <= dataframe["ema_slow"].shift(1)) &

                # Not already overbought
                (dataframe["rsi"] < 70) &

                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # Fast EMA crossed below slow EMA (momentum turning bearish)
                (dataframe["ema_fast"] < dataframe["ema_slow"]) &
                (dataframe["ema_fast"].shift(1) >= dataframe["ema_slow"].shift(1))
            ) |
            # RSI overbought
            (dataframe["rsi"] > 75),
            "exit_long",
        ] = 1
        return dataframe
