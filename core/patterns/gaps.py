# 总体目标：检测四类跳空（突破、持续、耗尽、普通），并分类上下方向。
# 输入：OHLCV + config.gaps
# 输出：gap_up/down、gap_type（breakaway_up等）、gap_size_pct
# 关键代码块：比较low>前high或high<前low检测跳空 → 用EMA趋势 + 近期高低点判断类型。
# 关联：强趋势确认信号。

import pandas as pd
import numpy as np

def detect_gaps(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    检测四类跳空形态（尼森+Murphy经典分类）
    - breakaway_gap: 突破跳空（趋势开始，放量）
    - continuation_gap: 持续跳空（趋势中途）
    - exhaustion_gap: 耗尽跳空（趋势末端，反转迹象）
    - common_gap: 普通跳空（小幅度，忽略）
    """
    df = df.copy()
    
    cfg = config.get('gaps', {})

    cfg = config.get('gaps', {})
    if not cfg.get('enabled', True):
        print("跳空检测已禁用（config gaps.enabled = false）")
        return df
    
    print("跳空检测逻辑开始执行...")

    min_gap_pct = cfg.get('min_gap_pct', 0.005)      # 最小跳空比例（加密默认0.5%，1m可用0.001）
    volume_mult = cfg.get('volume_multiplier', 1.5)  # 放量倍数（突破/持续需放量）
    trend_period = cfg.get('trend_period', 50)      # 判断趋势强度（close > EMA50 为多头）
    
    # 初始化列
    df['gap_up'] = 0      # 向上跳空标记
    df['gap_down'] = 0    # 向下跳空标记
    df['gap_type'] = 'none'  # 跳空类型：breakaway/continuation/exhaustion/common/none
    
    # 计算基础元素
    prev = df.shift(1)
    gap_up_mask = df['open'] > prev['high'] * (1 + min_gap_pct)
    gap_down_mask = df['open'] < prev['low'] * (1 - min_gap_pct)
    
    gap_size_pct = np.abs(df['open'] - prev['close']) / prev['close']
    
    # 放量判断
    vol_ma = df['volume'].rolling(20).mean()
    volume_spike = df['volume'] > vol_ma * volume_mult
    
    # 趋势判断（多头：close > EMA50）
    ema_trend = df['ema_medium']  # 假设 medium 是50期（你的config medium=50？）
    in_uptrend = df['close'] > ema_trend
    in_downtrend = df['close'] < ema_trend
    
    # 位置判断（趋势中/末端）
    recent_high = df['high'].rolling(trend_period).max()
    recent_low = df['low'].rolling(trend_period).min()
    near_recent_high = df['high'] >= recent_high * 0.99
    near_recent_low = df['low'] <= recent_low * 1.01
    
    # === 分类逻辑 ===
    # 向上跳空
    up_gap = gap_up_mask & volume_spike
    df.loc[gap_up_mask, 'gap_up'] = 1
    
    df.loc[up_gap & in_uptrend & ~near_recent_high, 'gap_type'] = 'breakaway_up'      # 突破（趋势初）
    df.loc[up_gap & in_uptrend & ~near_recent_high, 'gap_type'] = 'continuation_up'   # 持续（中途）
    df.loc[up_gap & in_uptrend & near_recent_high, 'gap_type'] = 'exhaustion_up'      # 耗尽（末端）
    df.loc[gap_up_mask & ~up_gap, 'gap_type'] = 'common_up'                           # 普通
    
    # 向下跳空（类似）
    down_gap = gap_down_mask & volume_spike
    df.loc[gap_down_mask, 'gap_down'] = 1
    
    df.loc[down_gap & in_downtrend & ~near_recent_low, 'gap_type'] = 'breakaway_down'
    df.loc[down_gap & in_downtrend & ~near_recent_low, 'gap_type'] = 'continuation_down'
    df.loc[down_gap & in_downtrend & near_recent_low, 'gap_type'] = 'exhaustion_down'
    df.loc[gap_down_mask & ~down_gap, 'gap_type'] = 'common_down'
    
    # 额外：跳空大小（pct）
    df['gap_size_pct'] = gap_size_pct.where(gap_up_mask | gap_down_mask, 0)
    
    print(f"检测到向上跳空: {gap_up_mask.sum()} 次，放量突破: {up_gap.sum()} 次")

    return df