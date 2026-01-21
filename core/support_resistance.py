import pandas as pd
import numpy as np                  # 顶部必须有
from scipy.signal import argrelextrema   # 必须有（用于 add_support_resistance_levels）

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
    swing_low = df['low'].loc[high_idx]
    diff = swing_high - swing_low
    if diff <= 0:
        diff = 1e-8  # 防除零
    
    for level in cfg['levels']:
        fib_price = swing_high - diff * level
        df[f'fib_{level:.3f}'] = fib_price  # 常量水平线
    
    # 整数关口（BTC用10000或5000调整）
    df['round_support'] = np.round(df['close'] / 5000) * 5000
    
    return df

def add_support_resistance_levels(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    df = df.copy()
    cfg = config.get('chart_patterns', {})
    order = cfg.get('extrema_order', 30)  # 默认大值，避免噪声
    
    high_values = df['high'].values
    low_values = df['low'].values
    
    # 找局部极值（peaks=阻力候选, troughs=支撑候选）
    resistance_idx = argrelextrema(high_values, np.greater, order=order)[0]
    support_idx = argrelextrema(low_values, np.less, order=order)[0]
    
    # 为每行构建 top 3 动态 levels（向前看，早期行用 NaN 填充）
    resistance_levels = np.full((len(df), 3), np.nan)
    support_levels = np.full((len(df), 3), np.nan)
    
    for i in range(len(df)):
        # 阻力：到当前行为止的所有 peaks，取价格最高的前3（降序）
        prev_res_idx = resistance_idx[resistance_idx <= i]
        if len(prev_res_idx) > 0:
            top_res = np.sort(high_values[prev_res_idx])[-3:]
            resistance_levels[i, :len(top_res)] = top_res[::-1]  # 最高在前
        
        # 支撑：到当前行为止的所有 troughs，取价格最低的前3（升序）
        prev_sup_idx = support_idx[support_idx <= i]
        if len(prev_sup_idx) > 0:
            top_sup = np.sort(low_values[prev_sup_idx])[:3]
            support_levels[i, :len(top_sup)] = top_sup
    
    # 添加到 df（推荐列方式，避免数组广播问题）
    df['resistance_1'] = resistance_levels[:, 0]
    df['resistance_2'] = resistance_levels[:, 1]
    df['resistance_3'] = resistance_levels[:, 2]
    df['support_1'] = support_levels[:, 0]
    df['support_2'] = support_levels[:, 1]
    df['support_3'] = support_levels[:, 2]

        # === 新增：强度计算（历史触碰次数） ===
    touch_tol = config.get('support_resistance', {}).get('touch_tolerance_pct', 0.005)
    
    # 初始化强度列
    df['support_1_strength'] = 0
    df['support_2_strength'] = 0
    df['support_3_strength'] = 0
    df['resistance_1_strength'] = 0
    df['resistance_2_strength'] = 0
    df['resistance_3_strength'] = 0
    
    # 逐行计算（从后往前，避免未来数据）
    for i in range(len(df)):
        close = df['close'].iloc[i]
        
        # 支撑强度
        for j in range(1, 4):
            sup_col = f'support_{j}'
            str_col = f'support_{j}_strength'
            if sup_col in df.columns and not pd.isna(df[sup_col].iloc[i]):
                level = df[sup_col].iloc[i]
                # 历史触碰：之前所有close在level ± tol内
                historical = df['close'].iloc[:i+1]  # 到当前包括
                touches = ((historical >= level * (1 - touch_tol)) & 
                           (historical <= level * (1 + touch_tol))).sum()
                df.loc[df.index[i], str_col] = touches
        
        # 阻力强度（同理）
        for j in range(1, 4):
            res_col = f'resistance_{j}'
            str_col = f'resistance_{j}_strength'
            if res_col in df.columns and not pd.isna(df[res_col].iloc[i]):
                level = df[res_col].iloc[i]
                historical = df['close'].iloc[:i+1]
                touches = ((historical >= level * (1 - touch_tol)) & 
                           (historical <= level * (1 + touch_tol))).sum()
                df.loc[df.index[i], str_col] = touches
    
    # 如果下游一定要数组，可额外加
    # df.attrs['resistance_levels'] = resistance_levels
    # df.attrs['support_levels'] = support_levels
        
    return df