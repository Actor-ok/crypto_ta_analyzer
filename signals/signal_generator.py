import pandas as pd
import numpy as np

def generate_signals(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    生成交易信号：1=买入, -1=卖出, 0=持仓
    当前已整合：
    - 蜡烛反转形态（含哈拉米/十字哈拉米）
    - 双顶/双底确认（强信号）
    - 头肩顶/底确认（强信号）
    - RSI/MACD 背离（强信号）
    - 支撑/阻力强度加强（靠近高强度支撑/阻力时增强信号）
    """
    df = df.copy()
    df['signal'] = 0
    
    c = config['confirmation']
    i = config['indicators']
    
    # 趋势过滤（价格 > 200EMA 为多头，加密经典）
    in_uptrend = df['close'] > df['ema_very_long']
    
    # 放量（>20期均量1.5倍，文档放量确认）
    vol_ma20 = df['volume'].rolling(20).mean()
    volume_spike = df['volume'] > vol_ma20 * 1.5
    
    # RSI超卖/超买
    rsi_oversold = df['rsi'] < i['rsi']['oversold']
    rsi_overbought = df['rsi'] > i['rsi']['overbought']
    
    # MACD 金叉/死叉（hist穿越0轴）
    macd_bull = (df['macd_hist'] > 0) & (df['macd_hist'].shift(1) <= 0)
    macd_bear = (df['macd_hist'] < 0) & (df['macd_hist'].shift(1) >= 0)
    
    # 看涨蜡烛形态组（含哈拉米）
    bullish_pattern = df[[
        'hammer', 'inverted_hammer', 'bullish_engulfing', 'morning_star', 
        'three_white_soldiers', 'piercing', 'dragonfly_doji',
        'bullish_harami', 'bullish_harami_cross'
    ]].max(axis=1) == 1
    
    # 看跌蜡烛形态组（含哈拉米）
    bearish_pattern = df[[
        'shooting_star', 'bearish_engulfing', 'evening_star', 
        'three_black_crows', 'dark_cloud_cover', 'gravestone_doji',
        'bearish_harami', 'bearish_harami_cross'
    ]].max(axis=1) == 1
    
    # 图表形态强信号（双顶/双底 + 头肩确认）——安全访问
    double_bottom_conf = df.get('double_bottom_confirmed', pd.Series(0, index=df.index))
    hs_bottom_conf = df.get('hs_bottom_confirmed', pd.Series(0, index=df.index))
    strong_bullish_pattern = (double_bottom_conf | hs_bottom_conf).astype(int)
    
    double_top_conf = df.get('double_top_confirmed', pd.Series(0, index=df.index))
    hs_top_conf = df.get('hs_top_confirmed', pd.Series(0, index=df.index))
    strong_bearish_pattern = (double_top_conf | hs_top_conf).astype(int)
    
    # 背离强信号（RSI 或 MACD）
    rsi_bull_div = df.get('rsi_bullish_div', pd.Series(0, index=df.index))
    macd_bull_div = df.get('macd_bullish_div', pd.Series(0, index=df.index))
    bullish_div = (rsi_bull_div | macd_bull_div).astype(int)
    
    rsi_bear_div = df.get('rsi_bearish_div', pd.Series(0, index=df.index))
    macd_bear_div = df.get('macd_bearish_div', pd.Series(0, index=df.index))
    bearish_div = (rsi_bear_div | macd_bear_div).astype(int)
    
    # === 新增：支撑/阻力强度加强 ===
    # 靠近高强度支撑（任意支撑强度≥3，且价格在1%内）
    strong_support_near = (
        ((df['close'] - df.get('support_1', pd.Series(np.nan, index=df.index))).abs() / df['close'] < 0.01) &
        (df.get('support_1_strength', pd.Series(0, index=df.index)) >= 3) |
        ((df['close'] - df.get('support_2', pd.Series(np.nan, index=df.index))).abs() / df['close'] < 0.01) &
        (df.get('support_2_strength', pd.Series(0, index=df.index)) >= 3) |
        ((df['close'] - df.get('support_3', pd.Series(np.nan, index=df.index))).abs() / df['close'] < 0.01) &
        (df.get('support_3_strength', pd.Series(0, index=df.index)) >= 3)
    )
    
    # 靠近高强度阻力（对称）
    strong_resistance_near = (
        ((df['close'] - df.get('resistance_1', pd.Series(np.nan, index=df.index))).abs() / df['close'] < 0.01) &
        (df.get('resistance_1_strength', pd.Series(0, index=df.index)) >= 3) |
        ((df['close'] - df.get('resistance_2', pd.Series(np.nan, index=df.index))).abs() / df['close'] < 0.01) &
        (df.get('resistance_2_strength', pd.Series(0, index=df.index)) >= 3) |
        ((df['close'] - df.get('resistance_3', pd.Series(np.nan, index=df.index))).abs() / df['close'] < 0.01) &
        (df.get('resistance_3_strength', pd.Series(0, index=df.index)) >= 3)
    )
    
    # 买入信号：标准多重确认 OR 强形态/背离 OR 形态+强支撑
    buy = (
        (bullish_pattern & rsi_oversold & (volume_spike | macd_bull) & in_uptrend) |
        (strong_bullish_pattern == 1) & in_uptrend |
        (bullish_pattern & (bullish_div == 1)) |
        (bullish_pattern & strong_support_near)  # 新增：形态+强支撑直接加强
    )
    
    # 卖出信号（对称）
    sell = (
        (bearish_pattern & rsi_overbought & (volume_spike | macd_bear) & (~in_uptrend)) |
        (strong_bearish_pattern == 1) & (~in_uptrend) |
        (bearish_pattern & (bearish_div == 1)) |
        (bearish_pattern & strong_resistance_near)  # 新增：形态+强阻力直接加强
    )
    
    df.loc[buy, 'signal'] = 1
    df.loc[sell, 'signal'] = -1

        # 持续形态组
    continuation_bull = df.get('rising_three_methods', pd.Series(0, index=df.index)) == 1
    continuation_bear = df.get('falling_three_methods', pd.Series(0, index=df.index)) == 1
    
    # 买入加强：趋势中持续形态加仓
    buy = buy | (continuation_bull & in_uptrend)
    
    # 卖出加强
    sell = sell | (continuation_bear & (~in_uptrend))

        # 背离强信号（扩展OBV）
    obv_bull_div = df.get('obv_bullish_div', pd.Series(0, index=df.index))
    obv_bear_div = df.get('obv_bearish_div', pd.Series(0, index=df.index))
    
    bullish_div = (rsi_bull_div | macd_bull_div | obv_bull_div).astype(int)
    bearish_div = (rsi_bear_div | macd_bear_div | obv_bear_div).astype(int)


        # 背离强信号（扩展OBV量价背离）
    obv_bull_div = df.get('obv_bullish_div', pd.Series(0, index=df.index))
    obv_bear_div = df.get('obv_bearish_div', pd.Series(0, index=df.index))
    
    bullish_div = (rsi_bull_div | macd_bull_div | obv_bull_div).astype(int)
    bearish_div = (rsi_bear_div | macd_bear_div | obv_bear_div).astype(int)

        # 扩展OBV背离
    obv_bull_div = df.get('obv_bullish_div', pd.Series(0, index=df.index))
    obv_bear_div = df.get('obv_bearish_div', pd.Series(0, index=df.index))
    
    bullish_div = (rsi_bull_div | macd_bull_div | obv_bull_div).astype(int)
    bearish_div = (rsi_bear_div | macd_bear_div | obv_bear_div).astype(int)
    
    return df