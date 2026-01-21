import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

def add_obv_divergence(df: pd.DataFrame, config: dict = None) -> pd.DataFrame:
    df = df.copy()
    
    # 初始化列
    df['obv_bullish_div'] = 0
    df['obv_bearish_div'] = 0
    
    lookback = 50  # 可配置，后续加
    order = 10
    
    recent = df.tail(lookback * 2)
    if len(recent) < lookback:
        return df
    
    low_idx = argrelextrema(recent['low'].values, np.less_equal, order=order)[0]
    high_idx = argrelextrema(recent['high'].values, np.greater_equal, order=order)[0]
    
    obv_vals = recent['obv'].values
    
    price_tol = 0.01  # 1%
    obv_tol = 0.02    # 2%
    
    # 看涨背离
    if len(low_idx) >= 2:
        i1, i2 = low_idx[-2], low_idx[-1]
        if recent['low'].iloc[i2] < recent['low'].iloc[i1] * (1 - price_tol):
            if obv_vals[i2] > obv_vals[i1] * (1 + obv_tol):
                idx = recent.index[i2]
                df.loc[idx:, 'obv_bullish_div'] = 1
    
    # 看跌背离
    if len(high_idx) >= 2:
        i1, i2 = high_idx[-2], high_idx[-1]
        if recent['high'].iloc[i2] > recent['high'].iloc[i1] * (1 + price_tol):
            if obv_vals[i2] < obv_vals[i1] * (1 - obv_tol):
                idx = recent.index[i2]
                df.loc[idx:, 'obv_bearish_div'] = 1
    
    return df