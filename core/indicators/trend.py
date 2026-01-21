from ta.trend import EMAIndicator, SMAIndicator, MACD  # <--- 添加 MACD 这里
from ta.volatility import BollingerBands
from ta.volatility import AverageTrueRange
import pandas as pd

def add_moving_averages(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    ind = config['indicators']['ema']
    df['ema_short'] = EMAIndicator(df['close'], window=ind['short']).ema_indicator()
    df['ema_medium'] = EMAIndicator(df['close'], window=ind['medium']).ema_indicator()
    df['ema_long'] = EMAIndicator(df['close'], window=ind['long']).ema_indicator()
    df['ema_very_long'] = EMAIndicator(df['close'], window=ind['very_long']).ema_indicator()
    
    bb = BollingerBands(df['close'], window=config['indicators']['bollinger']['period'], 
                        window_dev=config['indicators']['bollinger']['std_dev'])
    df['bb_mid'] = bb.bollinger_mavg()
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_lower'] = bb.bollinger_lband()
    df['bb_width'] = bb.bollinger_wband()  # 带宽（挤压判断）
    
    # === 新增 MACD ===
    macd_cfg = config['indicators']['macd']
    macd = MACD(df['close'], window_slow=macd_cfg['slow'], 
                window_fast=macd_cfg['fast'], window_sign=macd_cfg['signal'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_hist'] = macd.macd_diff()

    # === 新增 ATR ===
    atr_cfg = config['indicators'].get('atr', {'period': 14})  # 默认14期
    atr_period = atr_cfg.get('period', 14)
    df['atr'] = AverageTrueRange(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        window=atr_period
    ).average_true_range()
    
    # 可选：ATR百分比（用于固定百分比止损备用）
    df['atr_pct'] = df['atr'] / df['close']
    
    return df