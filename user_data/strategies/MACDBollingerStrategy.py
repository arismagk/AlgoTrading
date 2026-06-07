from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
import talib.abstract as ta


class MACDBollingerStrategy(IStrategy):
    """
    MACD + Bollinger Bands + EMA 200 strategy.

    Entry: MACD crosses above signal line, price below BB middle, price above EMA 200
    Exit:  MACD crosses below signal line OR price hits upper Bollinger Band
    Timeframe: 1h (higher quality signals than 5m)
    """

    INTERFACE_VERSION = 3
    timeframe = "1h"

    minimal_roi = {
        "0":   0.04,   # 4% profit anytime
        "60":  0.025,  # 2.5% after 1 candle (1h)
        "120": 0.015,  # 1.5% after 2 candles (2h)
        "240": 0.005,  # 0.5% after 4 candles (4h)
        "360": 0       # break-even after 6h
    }

    stoploss = -0.05

    # Trailing stop: locks in profit once trade moves in our favour
    trailing_stop = True
    trailing_stop_positive = 0.02          # lock in 2% once profitable
    trailing_stop_positive_offset = 0.03  # activate after 3% profit reached
    trailing_only_offset_is_reached = True

    # Tunable parameters
    bb_period = IntParameter(low=14, high=26, default=20, space="buy", optimize=True)
    bb_std    = DecimalParameter(low=1.5, high=2.5, default=2.0, space="buy", optimize=True)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Long-term trend filter
        dataframe["ema_200"] = ta.EMA(dataframe, timeperiod=200)

        # MACD (12, 26, 9) — industry standard settings
        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe["macd"]       = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"]   = macd["macdhist"]

        # Bollinger Bands
        bb = ta.BBANDS(
            dataframe,
            timeperiod=self.bb_period.value,
            nbdevup=float(self.bb_std.value),
            nbdevdn=float(self.bb_std.value)
        )
        dataframe["bb_lower"]  = bb["lowerband"]
        dataframe["bb_middle"] = bb["middleband"]
        dataframe["bb_upper"]  = bb["upperband"]

        # RSI as overbought guard
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # ATR for reference (useful for future stop-loss tuning)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # 1. Long-term trend: price above EMA 200
                (dataframe["close"] > dataframe["ema_200"]) &

                # 2. MACD fresh crossover upward (momentum shifting bullish)
                (dataframe["macd"] > dataframe["macdsignal"]) &
                (dataframe["macd"].shift(1) <= dataframe["macdsignal"].shift(1)) &

                # 3. Price below BB middle (buying the dip, not chasing)
                (dataframe["close"] < dataframe["bb_middle"]) &

                # 4. RSI not already overbought
                (dataframe["rsi"] < 70) &

                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # MACD crosses below signal (momentum turning bearish)
                (
                    (dataframe["macd"] < dataframe["macdsignal"]) &
                    (dataframe["macd"].shift(1) >= dataframe["macdsignal"].shift(1))
                ) |
                # Price hits upper Bollinger Band (take profit at resistance)
                (dataframe["close"] > dataframe["bb_upper"])
            ),
            "exit_long",
        ] = 1
        return dataframe
