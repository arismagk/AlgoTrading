from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
from pandas import DataFrame
import talib.abstract as ta


class RSIStrategy(IStrategy):
    """
    Simple RSI-based strategy for learning algo trading.
    - Buy when RSI crosses above oversold level (default 30)
    - Sell when RSI crosses above overbought level (default 70)
    """

    INTERFACE_VERSION = 3
    timeframe = "5m"

    # Minimal ROI: exit trade at these profit thresholds
    minimal_roi = {
        "0": 0.04,    # 4% profit at any time
        "30": 0.02,   # 2% profit after 30 minutes
        "60": 0.01,   # 1% profit after 60 minutes
        "120": 0      # Break-even after 2 hours
    }

    stoploss = -0.05  # 5% stop loss

    # Trailing stop: lock in profits as price rises
    trailing_stop = False

    # Hyperparameters (tunable via freqtrade hyperopt)
    buy_rsi = IntParameter(low=20, high=40, default=35, space="buy", optimize=True)
    sell_rsi = IntParameter(low=60, high=80, default=65, space="sell", optimize=True)
    rsi_period = IntParameter(low=7, high=21, default=14, space="buy", optimize=False)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=self.rsi_period.value)
        dataframe["ema_20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_50"] = ta.EMA(dataframe, timeperiod=50)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["rsi"] < self.buy_rsi.value) &          # RSI oversold
                (dataframe["ema_20"] > dataframe["ema_50"]) &       # Uptrend filter
                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["rsi"] > self.sell_rsi.value) &          # RSI overbought
                (dataframe["volume"] > 0)
            ),
            "exit_long",
        ] = 1
        return dataframe
