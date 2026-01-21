import pandas as pd
import numpy as np

def _calculate_basic_elements(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算基础元素：实体、上影线、下影线、价格区间、是否阳线
    """
    df = df.copy()
    
    df['body'] = np.abs(df['close'] - df['open'])
    df['range'] = df['high'] - df['low']  # 价格区间 at_range
    df['upper_shadow'] = df['high'] - np.maximum(df['open'], df['close'])
    df['lower_shadow'] = np.minimum(df['open'], df['close']) - df['low']
    df['is_bullish'] = df['close'] > df['open']  # 阳线
    df['is_bearish'] = df['close'] < df['open']  # 阴线
    
    # 避免除零
    df['body_ratio'] = np.where(df['range'] > 0, df['body'] / df['range'], 0)
    
    return df

def detect_candlestick_patterns(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    df = df.copy()
    df = _calculate_basic_elements(df)
    
    cfg = config['candlestick']
    
    long_shadow = cfg['long_shadow_ratio']  # ≥2倍实体
    small_body = cfg['small_body_ratio']     # <30%范围
    doji_body = cfg['doji_ratio']            # ≤5%范围
    very_small = cfg['very_small_body_ratio']  # 用于晨星/昏星中间
    
    # 初始化哈拉米列（防止缺失）
    df['bullish_harami'] = 0
    df['bearish_harami'] = 0
    df['bullish_harami_cross'] = 0
    df['bearish_harami_cross'] = 0
    
    # 单根K线形态
    # Doji 系列
    df['doji'] = (df['body_ratio'] <= doji_body).astype(int)
    df['dragonfly_doji'] = df['doji'] & (df['lower_shadow'] >= df['body'] * long_shadow) & (df['upper_shadow'] <= df['body'] * 0.1)
    df['gravestone_doji'] = df['doji'] & (df['upper_shadow'] >= df['body'] * long_shadow) & (df['lower_shadow'] <= df['body'] * 0.1)
    df['long_legged_doji'] = df['doji'] & (df['upper_shadow'] >= df['body'] * long_shadow) & (df['lower_shadow'] >= df['body'] * long_shadow)
    
    # Spinning Top
    df['spinning_top'] = (df['body_ratio'] <= small_body) & (df['upper_shadow'] >= df['body'] * long_shadow) & (df['lower_shadow'] >= df['body'] * long_shadow)
    
    # Hammer / Shooting Star 系列
    df['hammer'] = (
        (df['lower_shadow'] >= df['body'] * long_shadow) &
        (df['upper_shadow'] <= df['body'] * cfg['hammer_upper_shadow_ratio']) &
        (df['body_ratio'] <= small_body)
    )
    df['inverted_hammer'] = (
        (df['upper_shadow'] >= df['body'] * long_shadow) &
        (df['lower_shadow'] <= df['body'] * cfg['shooting_star_lower_shadow_ratio']) &
        (df['body_ratio'] <= small_body)
    )
    df['shooting_star'] = df['inverted_hammer']  # 逻辑相同，但上下文不同
    
    # 双根形态
    prev = df.shift(1)
    
    # 吞没（Engulfing）
    engulfing_bull = (
        prev['is_bearish'] & df['is_bullish'] &
        (df['open'] < prev['close']) & (df['close'] > prev['open'])
    )
    if cfg.get('engulfing_strict', True):
        engulfing_bull &= (df['open'] <= prev['low']) & (df['close'] >= prev['high'])  # 完全包住影线
    df['bullish_engulfing'] = engulfing_bull.astype(int)
    
    engulfing_bear = (
        prev['is_bullish'] & df['is_bearish'] &
        (df['open'] > prev['close']) & (df['close'] < prev['open'])
    )
    if cfg.get('engulfing_strict', True):
        engulfing_bear &= (df['open'] >= prev['high']) & (df['close'] <= prev['low'])
    df['bearish_engulfing'] = engulfing_bear.astype(int)
    
    # 刺穿 / 乌云
    df['piercing'] = (
        prev['is_bearish'] & df['is_bullish'] &
        (df['open'] < prev['low']) & (df['close'] > prev['body'].abs() / 2 + np.minimum(prev['open'], prev['close']))
    ).astype(int)
    
    df['dark_cloud_cover'] = (
        prev['is_bullish'] & df['is_bearish'] &
        (df['open'] > prev['high']) & (df['close'] < prev['body'].abs() / 2 + np.minimum(prev['open'], prev['close']))
    ).astype(int)
    
    # 三根形态
    prev2 = df.shift(2)
    
    # 晨星 / 昏星
    morning_star = (
        prev2['is_bearish'] & 
        (prev['body_ratio'] <= very_small) & 
        df['is_bullish'] &
        (df['close'] > prev2['body'].abs() / 2 + np.minimum(prev2['open'], prev2['close']))
    )
    df['morning_star'] = morning_star.astype(int)
    
    evening_star = (
        prev2['is_bullish'] & 
        (prev['body_ratio'] <= very_small) & 
        df['is_bearish'] &
        (df['close'] < prev2['body'].abs() / 2 + np.minimum(prev2['open'], prev2['close']))
    )
    df['evening_star'] = evening_star.astype(int)
    
    # 三白兵 / 三黑乌
    three_up = (df['is_bullish'] & prev['is_bullish'] & prev2['is_bullish'] &
                (df['close'] > prev['close']) & (prev['close'] > prev2['close']))
    df['three_white_soldiers'] = three_up.astype(int)
    
    three_down = (df['is_bearish'] & prev['is_bearish'] & prev2['is_bearish'] &
                  (df['close'] < prev['close']) & (prev['close'] < prev2['close']))
    df['three_black_crows'] = three_down.astype(int)
    
    # 分离线与跳空
    upward_separation = (
        prev['is_bearish'] & df['is_bullish'] &
        (df['open'] > prev['close']) &
        (df['body'] > prev['body'] * 0.8)
    )
    df['upward_separation'] = upward_separation.astype(int)
    
    downward_separation = (
        prev['is_bullish'] & df['is_bearish'] &
        (df['open'] < prev['close']) &
        (df['body'] > prev['body'] * 0.8)
    )
    df['downward_separation'] = downward_separation.astype(int)
    
    df['gap_up'] = (df['low'] > prev['high']).astype(int)
    df['gap_down'] = (df['high'] < prev['low']).astype(int)
    
    # === 新增：哈拉米形态 ===
    prev_open = prev['open']
    prev_close = prev['close']
    prev_body = np.abs(prev_close - prev_open)
    
    small_ratio = cfg.get('harami_small_body_ratio', 0.5)
    cross_doji_ratio = cfg.get('harami_cross_doji_ratio', cfg['doji_ratio'])  # 复用doji阈值
    
    # 哈拉米基础条件
    harami_body_cond = (df['body'] <= prev_body * small_ratio) & \
                       (df['open'] >= np.minimum(prev_open, prev_close)) & \
                       (df['close'] <= np.maximum(prev_open, prev_close))
    
    harami_cross_cond = harami_body_cond & (df['body_ratio'] <= cross_doji_ratio)
    
    # 看涨哈拉米（前阴后阳）
    bullish_harami_cond = harami_body_cond & prev['is_bearish'] & df['is_bullish']
    df['bullish_harami'] = bullish_harami_cond.astype(int)
    
    df['bullish_harami_cross'] = (harami_cross_cond & bullish_harami_cond).astype(int)
    
    # 看跌哈拉米（前阳后阴）
    bearish_harami_cond = harami_body_cond & prev['is_bullish'] & df['is_bearish']
    df['bearish_harami'] = bearish_harami_cond.astype(int)
    
    df['bearish_harami_cross'] = (harami_cross_cond & bearish_harami_cond).astype(int)

        # === 新增：三法形态（持续形态）===
    cfg_three = cfg.get('three_methods_small_ratio', 0.5)
    large_ratio = cfg.get('three_methods_large_ratio', 1.0)
    
    # 移位4根前数据（需要5根K线）
    prev1 = df.shift(1)
    prev2 = df.shift(2)
    prev3 = df.shift(3)
    prev4 = df.shift(4)
    
    # 上升三法（多头持续）
    rising_three = (
        prev4['is_bullish'] & (prev4['body'] > 0) &  # 第一根大阳
        prev3['is_bearish'] & (prev3['body'] <= prev4['body'] * cfg_three) &  # 小阴
        prev2['is_bearish'] & (prev2['body'] <= prev4['body'] * cfg_three) &
        prev1['is_bearish'] & (prev1['body'] <= prev4['body'] * cfg_three) &
        df['is_bullish'] & (df['body'] >= prev4['body'] * large_ratio) &  # 第五根大阳突破
        (df['close'] > prev4['close'])  # 收盘新高
    )
    df['rising_three_methods'] = rising_three.astype(int)
    
    # 下降三法（空头持续）
    falling_three = (
        prev4['is_bearish'] & (prev4['body'] > 0) &
        prev3['is_bullish'] & (prev3['body'] <= prev4['body'] * cfg_three) &
        prev2['is_bullish'] & (prev2['body'] <= prev4['body'] * cfg_three) &
        prev1['is_bullish'] & (prev1['body'] <= prev4['body'] * cfg_three) &
        df['is_bearish'] & (df['body'] >= prev4['body'] * large_ratio) &
        (df['close'] < prev4['close'])
    )
    df['falling_three_methods'] = falling_three.astype(int)
    
    return df