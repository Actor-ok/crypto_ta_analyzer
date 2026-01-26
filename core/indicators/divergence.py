# 总体目标：检测RSI和MACD的看涨/看跌背离（隐藏背离也部分支持）。
# 输入：已有rsi/macd的DataFrame + config.divergence
# 输出：rsi_bullish_div、rsi_bearish_div、macd_bullish_div、macd_bearish_div（从检测点起持续标记1）
# 关键代码块：使用argrelextrema找极值点 → 比较最近两个极值点的价格 vs 指标值差异。
# 关联：信号生成时作为反转确认。

import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

def add_divergence_indicators(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    df = df.copy()
    cfg = config['indicators'].get('divergence', {})
    
    if not cfg.get('enabled', True):
        return df
    
    lookback = cfg.get('lookback', 50)
    order = cfg.get('extrema_order', 10)
    price_tol = cfg.get('price_tolerance', 0.01)
    ind_tol = cfg.get('indicator_tolerance', 0.02)
    
    # 初始化列
    df['rsi_bullish_div'] = 0
    df['rsi_bearish_div'] = 0
    df['macd_bullish_div'] = 0
    df['macd_bearish_div'] = 0
    
    # 限制回看范围（性能）
    recent = df.tail(lookback * 2)
    if len(recent) < lookback:
        return df
    
    low_idx = argrelextrema(recent['low'].values, np.less_equal, order=order)[0]
    high_idx = argrelextrema(recent['high'].values, np.greater_equal, order=order)[0]
    
    rsi_vals = recent['rsi'].values
    macd_hist_vals = recent['macd_hist'].values
    
    # 辅助函数：检测背离
    def check_bullish_div(price_idx, ind_vals):
        if len(price_idx) < 2:
            return None
        i1, i2 = price_idx[-2], price_idx[-1]  # 最近两个低点
        if recent['low'].iloc[i2] < recent['low'].iloc[i1] * (1 - price_tol):  # 价格新低
            if ind_vals[i2] > ind_vals[i1] * (1 + ind_tol):  # 指标更高低
                return i2
        return None
    
    def check_bearish_div(price_idx, ind_vals):
        if len(price_idx) < 2:
            return None
        i1, i2 = price_idx[-2], price_idx[-1]
        if recent['high'].iloc[i2] > recent['high'].iloc[i1] * (1 + price_tol):  # 价格新高
            if ind_vals[i2] < ind_vals[i1] * (1 - ind_tol):  # 指标更低高
                return i2
        return None
    
    # RSI 看涨/看跌背离
    rsi_bull = check_bullish_div(low_idx, rsi_vals)
    rsi_bear = check_bearish_div(high_idx, rsi_vals)
    
    # MACD hist 看涨/看跌背离
    macd_bull = check_bullish_div(low_idx, macd_hist_vals)
    macd_bear = check_bearish_div(high_idx, macd_hist_vals)
    
    # 标记到全 df（从检测点开始，或仅单根标记）
    if rsi_bull is not None:
        idx = recent.index[rsi_bull]
        df.loc[idx:, 'rsi_bullish_div'] = 1  # 从检测点起持续标记（便于信号）
    if rsi_bear is not None:
        idx = recent.index[rsi_bear]
        df.loc[idx:, 'rsi_bearish_div'] = 1
    if macd_bull is not None:
        idx = recent.index[macd_bull]
        df.loc[idx:, 'macd_bullish_div'] = 1
    if macd_bear is not None:
        idx = recent.index[macd_bear]
        df.loc[idx:, 'macd_bearish_div'] = 1
    
    return df