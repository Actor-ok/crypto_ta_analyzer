import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

def add_trendlines_and_channels(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    df = df.copy()
    cfg = config.get('trendlines', {})
    if not cfg.get('enabled', True):
        return df

    order = cfg.get('extrema_order', 20)
    channel_period = cfg.get('channel_period', 20)

    # 找转折点
    high_idx = argrelextrema(df['high'].values, np.greater_equal, order=order)[0]
    low_idx = argrelextrema(df['low'].values, np.less_equal, order=order)[0]

    # 上趋势线（最近3高点拟合）
    df['upper_trendline'] = np.nan
    if len(high_idx) >= 3:
        x = high_idx[-3:]
        y = df['high'].iloc[x]
        slope, intercept = np.polyfit(x, y, 1)
        df['upper_trendline'] = slope * np.arange(len(df)) + intercept

    # 下趋势线（最近3低点拟合）
    df['lower_trendline'] = np.nan
    if len(low_idx) >= 3:
        x = low_idx[-3:]
        y = df['low'].iloc[x]
        slope, intercept = np.polyfit(x, y, 1)
        df['lower_trendline'] = slope * np.arange(len(df)) + intercept

    # 唐奇安通道（备用）
    df['donchian_upper'] = df['high'].rolling(channel_period).max()
    df['donchian_lower'] = df['low'].rolling(channel_period).min()

    # 突破信号
    df['trendline_break_up'] = (df['close'] > df['upper_trendline']) | (df['close'] > df['donchian_upper'])
    df['trendline_break_down'] = (df['close'] < df['lower_trendline']) | (df['close'] < df['donchian_lower'])

    # 通道宽度（窄通道 = 整理）
    df['channel_width_pct'] = (df['donchian_upper'] - df['donchian_lower']) / df['close']

    return df