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
    """
    主函数：检测所有蜡烛图形态
    config: 从 yaml 加载的 candlestick 部分
    """
    cfg = config['candlestick']
    df = _calculate_basic_elements(df)
    
    # ==================== 单根K线形态 ====================
    
    # 长影线判断
    long_lower_shadow = df['lower_shadow'] >= df['body'] * cfg['long_shadow_ratio']
    long_upper_shadow = df['upper_shadow'] >= df['body'] * cfg['long_shadow_ratio']
    
    # 小实体
    small_body = df['body_ratio'] <= cfg['small_body_ratio']
    very_small_body = df['body_ratio'] <= cfg['very_small_body_ratio']
    
    # 十字星（包括变体）
    doji = df['body_ratio'] <= cfg['doji_ratio']
    
    # 锤头线（Hammer）：下影长 + 上影短 + 小实体（通常在下跌趋势，但这里先检测形态）
    hammer_condition = (
        long_lower_shadow &
        (df['upper_shadow'] <= df['body'] * cfg['hammer_upper_shadow_ratio']) &
        small_body
    )
    df['hammer'] = hammer_condition.astype(int)
    
    # 上吊线（Hanging Man）：结构同锤头，但通常在上涨趋势（后续信号层判断趋势）
    df['hanging_man'] = hammer_condition.astype(int)  # 结构相同，后续区分趋势
    
    # 倒锤头/射击之星（Inverted Hammer / Shooting Star）
    inverted_hammer_condition = (
        long_upper_shadow &
        (df['lower_shadow'] <= df['body'] * cfg['shooting_star_lower_shadow_ratio']) &
        small_body
    )
    df['inverted_hammer'] = inverted_hammer_condition.astype(int)  # 看涨变体
    df['shooting_star'] = inverted_hammer_condition.astype(int)  # 看跌变体，后续区分
    
    # 纺锤线（Spinning Top）：小实体 + 长上下影线
    spinning_top = small_body & long_lower_shadow & long_upper_shadow
    df['spinning_top'] = spinning_top.astype(int)
    
    # 十字星变体
    df['doji'] = doji.astype(int)
    df['dragonfly_doji'] = doji & long_lower_shadow  # 蜻蜓十字（潜在看涨）
    df['gravestone_doji'] = doji & long_upper_shadow  # 墓碑十字（潜在看跌）
    df['long_legged_doji'] = doji & long_lower_shadow & long_upper_shadow
    
    # ==================== 2-3根组合反转形态 ====================
    
    # 辅助：前一根、前两根
    prev1 = df.shift(1)
    prev2 = df.shift(2)
    
    # 1. 吞没形态（Engulfing）
    bullish_engulfing = (
        prev1['is_bearish'] & df['is_bullish'] &  # 前阴后阳
        (df['open'] < prev1['close']) &
        (df['close'] > prev1['open']) &
        (df['body'] > prev1['body'] if cfg['engulfing_strict'] else True)  # 可选严格完全包住
    )
    bearish_engulfing = (
        prev1['is_bullish'] & df['is_bearish'] &
        (df['open'] > prev1['close']) &
        (df['close'] < prev1['open']) &
        (df['body'] > prev1['body'] if cfg['engulfing_strict'] else True)
    )
    df['bullish_engulfing'] = bullish_engulfing.astype(int)
    df['bearish_engulfing'] = bearish_engulfing.astype(int)
    
    # 2. 刺穿形态（Piercing） / 乌云盖顶（Dark Cloud Cover）
    piercing = (
        prev1['is_bearish'] & df['is_bullish'] &
        (df['open'] < prev1['low']) &  # 跳空低开（加密可放宽）
        (df['close'] > prev1['open'] + (prev1['close'] - prev1['open']) * cfg['piercing_ratio'])
    )
    dark_cloud = (
        prev1['is_bullish'] & df['is_bearish'] &
        (df['open'] > prev1['high']) &
        (df['close'] < prev1['open'] - (prev1['open'] - prev1['close']) * cfg['piercing_ratio'])
    )
    df['piercing'] = piercing.astype(int)
    df['dark_cloud_cover'] = dark_cloud.astype(int)
    
    # 3. 晨星（Morning Star） / 昏星（Evening Star）
    morning_star = (
        prev2['is_bearish'] &                                 # 第一根长阴
        very_small_body.shift(1) &                           # 中间小实体/十字
        df['is_bullish'] &                                   # 第三根阳
        (df['close'] > prev2['open'] + prev2['body'] * 0.5)   # 第三根深入第一根实体一半以上
    )
    evening_star = (
        prev2['is_bullish'] &
        very_small_body.shift(1) &
        df['is_bearish'] &
        (df['close'] < prev2['open'] - prev2['body'] * 0.5)
    )
    df['morning_star'] = morning_star.astype(int)
    df['evening_star'] = evening_star.astype(int)
    
    # 4. 三白兵（Three White Soldiers） / 三黑鸦（Three Black Crows）
    three_soldiers = (
        df['is_bullish'] &
        prev1['is_bullish'] &
        prev2['is_bullish'] &
        (df['close'] > prev1['close']) &
        (prev1['close'] > prev2['close']) &
        (df['open'] > prev1['open']) &   # 逐步高于前开盘
        (prev1['open'] > prev2['open'])
    )
    three_crows = (
        df['is_bearish'] &
        prev1['is_bearish'] &
        prev2['is_bearish'] &
        (df['close'] < prev1['close']) &
        (prev1['close'] < prev2['close']) &
        (df['open'] < prev1['open']) &
        (prev1['open'] < prev2['open'])
    )
    df['three_white_soldiers'] = three_soldiers.astype(int)
    df['three_black_crows'] = three_crows.astype(int)
    
    # ==================== 持续形态（Continuation） ====================
    
    # 上升分离线（Upward Separation Lines）：大阳后大阴开盘高于前收盘（看涨持续）
    upward_separation = (
        prev1['is_bullish'] & df['is_bearish'] &
        (df['open'] > prev1['close']) &
        (df['body'] > prev1['body'] * 0.8)  # 力度类似
    )
    df['upward_separation'] = upward_separation.astype(int)
    
    # 下降分离线（Downward）：反之，看跌持续
    downward_separation = (
        prev1['is_bearish'] & df['is_bullish'] &
        (df['open'] < prev1['close']) &
        (df['body'] > prev1['body'] * 0.8)
    )
    df['downward_separation'] = downward_separation.astype(int)
    
    # 跳空窗口（Gap）：加密少见，但可检测
    gap_up = df['low'] > prev1['high']
    gap_down = df['high'] < prev1['low']
    df['gap_up'] = gap_up.astype(int)  # 潜在支撑
    df['gap_down'] = gap_down.astype(int)  # 潜在阻力
    
    # 注意：持续形态常在趋势中途加仓（信号层用）

    return df

# 可选：后期在信号层添加成交量/趋势确认
