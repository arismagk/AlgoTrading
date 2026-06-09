from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
import talib.abstract as ta


class MACDBollingerStrategy(IStrategy):
    """
    Bollinger Band Bounce + MACD Momentum strategy.

    Core idea: buy when price bounces off the lower Bollinger Band
    while MACD momentum is building and the medium-term trend is up.

    Fixes vs previous version:
    - 15m timeframe (more signals than 1h, cleaner than 5m)
    - EMA 50/100 instead of EMA 200 (available after ~1 day, not 8 days)
    - MACD histogram growing (not just crossover) — many more entries
    - Volume confirmation added
    - Tighter stop loss for faster loss cutting
    """

    INTERFACE_VERSION = 3
    timeframe = "15m"

    minimal_roi = {
        "0":   0.03,    # 3% anytime
        "30":  0.02,    # 2% after 30 min
        "60":  0.01,    # 1% after 1 hour
        "120": 0.005,   # 0.5% after 2 hours
        "180": 0        # break-even after 3 hours
    }

    stoploss = -0.03

    trailing_stop = True
    trailing_stop_positive = 0.015         # lock in 1.5% once profitable
    trailing_stop_positive_offset = 0.025  # activate after 2.5% profit
    trailing_only_offset_is_reached = True

    # Tunable parameters
    bb_period  = IntParameter(low=14, high=26, default=20,  space="buy", optimize=True)
    bb_std     = DecimalParameter(low=1.5, high=2.5, default=2.0, space="buy", optimize=True)
    rsi_buy    = IntParameter(low=25, high=55, default=50,  space="buy", optimize=True)
    volume_factor = DecimalParameter(low=1.0, high=2.0, default=1.2, space="buy", optimize=True)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Medium-term trend filter (needs ~1 day of 15m data, not 8 days)
        dataframe["ema_50"]  = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_100"] = ta.EMA(dataframe, timeperiod=100)

        # MACD
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
        dataframe["bb_width"]  = (dataframe["bb_upper"] - dataframe["bb_lower"]) / dataframe["bb_middle"]

        # RSI
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # Volume moving average for confirmation
        dataframe["volume_ma"] = ta.SMA(dataframe["volume"], timeperiod=20)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # 1. Medium-term uptrend: EMA 50 above EMA 100
                (dataframe["ema_50"] > dataframe["ema_100"]) &

                # 2. Price bouncing off lower Bollinger Band
                # Previous candle was near/below lower band, current is recovering
                (dataframe["close"].shift(1) <= dataframe["bb_lower"].shift(1) * 1.005) &
                (dataframe["close"] > dataframe["close"].shift(1)) &

                # 3. MACD histogram is positive and growing (momentum building)
                (dataframe["macdhist"] > dataframe["macdhist"].shift(1)) &
                (dataframe["macdhist"] > dataframe["macdhist"].shift(2)) &

                # 4. RSI not overbought (recovering from oversold or neutral)
                (dataframe["rsi"] < self.rsi_buy.value) &

                # 5. Volume above average (genuine move, not low-volume noise)
                (dataframe["volume"] > dataframe["volume_ma"] * float(self.volume_factor.value)) &

                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # Price reached upper Bollinger Band (take profit zone)
                (dataframe["close"] > dataframe["bb_upper"]) |

                # MACD histogram turning negative (momentum reversing)
                (
                    (dataframe["macdhist"] < 0) &
                    (dataframe["macdhist"] < dataframe["macdhist"].shift(1))
                ) |

                # RSI overbought
                (dataframe["rsi"] > 75)
            ),
            "exit_long",
        ] = 1
        return dataframe
