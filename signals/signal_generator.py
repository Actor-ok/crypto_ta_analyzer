import pandas as pd
import numpy as np

def generate_signals(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    生成交易信号：1=买入, -1=卖出, 0=持仓
    严格按文档“综合交易策略”：形态 + 指标 + 成交量 + 支撑/趋势 多重确认
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
    
    # RSI超卖/超买 + 背离简化（这里先用超卖超买）
    rsi_oversold = df['rsi'] < i['rsi']['oversold']
    rsi_overbought = df['rsi'] > i['rsi']['overbought']
    
    # MACD金叉/死叉
    macd_bull = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
    macd_bear = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))
    
    # 看涨形态组
    bullish_pattern = df[['hammer', 'bullish_engulfing', 'morning_star', 
                          'three_white_soldiers', 'piercing', 'dragonfly_doji']].max(axis=1) == 1
    
    # 看跌形态组
    bearish_pattern = df[['shooting_star', 'bearish_engulfing', 'evening_star', 
                          'three_black_crows', 'dark_cloud_cover', 'gravestone_doji']].max(axis=1) == 1
    
    # 买入信号（反转形态 + 超卖/金叉 + 放量 + 趋势支持）
    buy = bullish_pattern & rsi_oversold & (volume_spike | macd_bull) & in_uptrend
    df.loc[buy, 'signal'] = 1
    
    # 卖出信号
    sell = bearish_pattern & rsi_overbought & (volume_spike | macd_bear) & (~in_uptrend)
    df.loc[sell, 'signal'] = -1
    
    return df