import pandas as pd
import numpy as np

def add_fibonacci_levels(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    df = df.copy()
    cfg = config['fibonacci']
    lookback = cfg['swing_lookback']
    
    # 安全rolling（min_periods避免前部NaN）
    high_roll = df['high'].rolling(window=lookback, min_periods=lookback//2).max()
    low_roll = df['low'].rolling(window=lookback, min_periods=lookback//2).min()
    
    # 找最近有效swing（从后往前找，避免数据倒序影响）
    high_idx = high_roll.iloc[-lookback:].idxmax() if not high_roll.empty else np.nan
    low_idx = low_roll.iloc[-lookback:].idxmin() if not low_roll.empty else np.nan
    
    if pd.isna(high_idx) or pd.isna(low_idx):
        for level in cfg['levels']:
            df[f'fib_{level:.3f}'] = np.nan
        df['round_support'] = np.nan
        return df
    
    swing_high = df['high'].loc[high_idx]
    swing_low = df['low'].loc[low_idx]
    diff = swing_high - swing_low
    if diff <= 0:
        diff = 1e-8  # 防除零
    
    for level in cfg['levels']:
        fib_price = swing_high - diff * level
        df[f'fib_{level:.3f}'] = fib_price  # 常量水平线
    
    # 整数关口（BTC用10000或5000调整）
    df['round_support'] = np.round(df['close'] / 5000) * 5000
    
    return df