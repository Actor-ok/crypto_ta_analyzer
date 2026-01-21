import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

def add_obv_divergence(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    df = df.copy()
    
    cfg = config['indicators'].get('obv_divergence', {})
    if not cfg.get('enabled', True):
        return df
    
    lookback = cfg.get('lookback', 60)
    order = cfg.get('extrema_order', 12)
    price_tol = cfg.get('price_tolerance', 0.01)
    obv_tol = cfg.get('obv_tolerance', 0.02)
    
    # 强制初始化列
    if 'obv_bullish_div' not in df.columns:
        df['obv_bullish_div'] = 0
    if 'obv_bearish_div' not in df.columns:
        df['obv_bearish_div'] = 0
    
    recent = df.tail(lookback * 3)
    if len(recent) < lookback or 'obv' not in recent.columns:
        return df
    
    low_idx = argrelextrema(recent['low'].values, np.less_equal, order=order)[0]
    high_idx = argrelextrema(recent['high'].values, np.greater_equal, order=order)[0]
    
    obv_vals = recent['obv'].values
    
    # 看涨背离
    if len(low_idx) >= 2:
        i1, i2 = low_idx[-2], low_idx[-1]
        if recent['low'].iloc[i2] < recent['low'].iloc[i1] * (1 - price_tol):
            if obv_vals[i2] > obv_vals[i1] * (1 + obv_tol):
                df.loc[recent.index[i2]:, 'obv_bullish_div'] = 1
    
    # 看跌背离
    if len(high_idx) >= 2:
        i1, i2 = high_idx[-2], high_idx[-1]
        if recent['high'].iloc[i2] > recent['high'].iloc[i1] * (1 + price_tol):
            if obv_vals[i2] < obv_vals[i1] * (1 - obv_tol):
                df.loc[recent.index[i2]:, 'obv_bearish_div'] = 1
    
    return df