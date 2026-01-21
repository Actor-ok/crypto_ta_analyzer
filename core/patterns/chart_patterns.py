import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

def detect_chart_patterns(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    df = df.copy()
    cfg = config.get('chart_patterns', {})
    
    order = cfg.get('extrema_order', 30)
    tolerance = cfg.get('peak_trough_tolerance', 0.05)
    require_vol = cfg.get('require_volume_confirm', True)
    vol_mult = cfg.get('volume_multiplier', 1.5)
    min_bars = cfg.get('min_pattern_bars', 10)
    
    df['double_top'] = 0
    df['double_top_confirmed'] = 0
    df['double_bottom'] = 0
    df['double_bottom_confirmed'] = 0
    
    # 新增头肩初始化
    df['head_shoulders_top'] = 0
    df['head_shoulders_bottom'] = 0
    df['hs_top_confirmed'] = 0
    df['hs_bottom_confirmed'] = 0
    
    high_values = df['high'].values
    low_values = df['low'].values
    close_values = df['close'].values
    volume_values = df['volume'].values
    
    # 检测极值点
    highs_idx = argrelextrema(high_values, np.greater_equal, order=order)[0]
    lows_idx = argrelextrema(low_values, np.less_equal, order=order)[0]
    
    vol_ma20 = pd.Series(volume_values).rolling(20).mean().values
    
    # === 双顶检测（M形）===
    for i in range(len(highs_idx) - 2):
        idx1, idx2, idx3 = highs_idx[i], highs_idx[i+1], highs_idx[i+2]
        
        if idx3 - idx1 < min_bars:  # 形态太窄，跳过
            continue
            
        h1, h2, h3 = high_values[idx1], high_values[idx2], high_values[idx3]
        
        # 两峰相似（中间更高）
        if (h2 >= h1 * (1 - tolerance) and h2 >= h3 * (1 - tolerance) and
            abs(h1 - h3) / h2 <= tolerance):
            
            start = idx1
            end = idx3 + 1
            neckline = np.min(low_values[start:end])  # 颈线取最低点
            
            df.loc[df.index[idx2], 'double_top'] = 1
            
            # 确认：价格跌破颈线 + 可选放量
            breakout_mask = close_values[end:] < neckline
            if require_vol:
                vol_spike = volume_values[end:] > vol_ma20[end:] * vol_mult
                confirmed = breakout_mask & vol_spike
            else:
                confirmed = breakout_mask
                
            if confirmed.any():
                first_break_idx = np.where(confirmed)[0][0] + end
                if first_break_idx < len(df):
                    df.loc[df.index[first_break_idx]:, 'double_top_confirmed'] = 1
    
    # === 双底检测（W形）===
    for i in range(len(lows_idx) - 2):
        idx1, idx2, idx3 = lows_idx[i], lows_idx[i+1], lows_idx[i+2]
        
        if idx3 - idx1 < min_bars:
            continue
            
        l1, l2, l3 = low_values[idx1], low_values[idx2], low_values[idx3]
        
        if (l2 <= l1 * (1 + tolerance) and l2 <= l3 * (1 + tolerance) and
            abs(l1 - l3) / abs(l2) <= tolerance):
            
            start = idx1
            end = idx3 + 1
            neckline = np.max(high_values[start:end])
            
            df.loc[df.index[idx2], 'double_bottom'] = 1
            
            breakout_mask = close_values[end:] > neckline
            if require_vol:
                vol_spike = volume_values[end:] > vol_ma20[end:] * vol_mult
                confirmed = breakout_mask & vol_spike
            else:
                confirmed = breakout_mask
                
            if confirmed.any():
                first_break_idx = np.where(confirmed)[0][0] + end
                if first_break_idx < len(df):
                    df.loc[df.index[first_break_idx]:, 'double_bottom_confirmed'] = 1

        # === 头肩顶（看跌反转）===
    for i in range(len(highs_idx) - 4):  # 需要至少5个高点
        idx_ls, idx_head, idx_rs, idx_next1, idx_next2 = highs_idx[i:i+5]
        
        if idx_next2 - idx_ls < min_bars:
            continue
            
        prices = high_values[[idx_ls, idx_head, idx_rs]]
        ls, head, rs = prices
        
        # 头最高，两肩相似
        if (head > ls * (1 + tolerance) and head > rs * (1 + tolerance) and
            abs(ls - rs) / head <= cfg.get('shoulder_tolerance', 0.10)):
            
            # 颈线：连接两肩间最低点
            neck_start = idx_ls
            neck_end = idx_rs
            neckline = np.max(low_values[neck_start:neck_end])  # 保守取高点作为颈线
            
            df.loc[df.index[idx_head], 'head_shoulders_top'] = 1
            
            # 确认：跌破颈线 + 放量
            breakout_mask = close_values[neck_end:] < neckline
            if require_vol:
                vol_spike = volume_values[neck_end:] > vol_ma20[neck_end:] * vol_mult
                confirmed = breakout_mask & vol_spike
            else:
                confirmed = breakout_mask
                
            if confirmed.any():
                first_break = np.where(confirmed)[0][0] + neck_end
                if first_break < len(df):
                    df.loc[df.index[first_break]:, 'hs_top_confirmed'] = 1
    
    # === 头肩底（看涨反转）===
    for i in range(len(lows_idx) - 4):
        idx_ls, idx_head, idx_rs, idx_next1, idx_next2 = lows_idx[i:i+5]
        
        if idx_next2 - idx_ls < min_bars:
            continue
            
        prices = low_values[[idx_ls, idx_head, idx_rs]]
        ls, head, rs = prices
        
        if (head < ls * (1 - tolerance) and head < rs * (1 - tolerance) and
            abs(ls - rs) / abs(head) <= cfg.get('shoulder_tolerance', 0.10)):
            
            neck_start = idx_ls
            neck_end = idx_rs
            neckline = np.min(high_values[neck_start:neck_end])
            
            df.loc[df.index[idx_head], 'head_shoulders_bottom'] = 1
            
            breakout_mask = close_values[neck_end:] > neckline
            if require_vol:
                vol_spike = volume_values[neck_end:] > vol_ma20[neck_end:] * vol_mult
                confirmed = breakout_mask & vol_spike
            else:
                confirmed = breakout_mask
                
            if confirmed.any():
                first_break = np.where(confirmed)[0][0] + neck_end
                if first_break < len(df):
                    df.loc[df.index[first_break]:, 'hs_bottom_confirmed'] = 1

            # === 新增：三角形检测 ===
    # 对称三角形（上下趋势线收敛）
    df['symmetrical_triangle'] = 0
    df['ascending_triangle'] = 0
    df['descending_triangle'] = 0

    # 简化实现：用最近转折点判断收敛
    high_idx = argrelextrema(df['high'].values, np.greater_equal, order=order)[0]
    low_idx = argrelextrema(df['low'].values, np.less_equal, order=order)[0]

    if len(high_idx) >= 3 and len(low_idx) >= 3:
        # 上趋势线斜率（下降）
        upper_slope = (df['high'].iloc[high_idx[-1]] - df['high'].iloc[high_idx[-3]]) / (high_idx[-1] - high_idx[-3])
        # 下趋势线斜率（上升）
        lower_slope = (df['low'].iloc[low_idx[-1]] - df['low'].iloc[low_idx[-3]]) / (low_idx[-1] - low_idx[-3])

        convergence = upper_slope < 0 and lower_slope > 0  # 收敛
        flat_upper = abs(upper_slope) < tolerance * 0.1  # 上升三角（上平）
        flat_lower = abs(lower_slope) < tolerance * 0.1  # 下降三角（下平）

        if convergence:
            if flat_upper:
                df.loc[df.index[-1]:, 'ascending_triangle'] = 1
            elif flat_lower:
                df.loc[df.index[-1]:, 'descending_triangle'] = 1
            else:
                df.loc[df.index[-1]:, 'symmetrical_triangle'] = 1

    # === 新增：旗形/楔形（短期通道 + 放量突破）===
    df['bull_flag'] = 0
    df['bear_flag'] = 0
    df['wedge_up'] = 0
    df['wedge_down'] = 0

    # 简单通道检测（唐奇安或rolling）
    channel_period = cfg.get('channel_period', 20)
    upper_channel = df['high'].rolling(channel_period).max()
    lower_channel = df['low'].rolling(channel_period).min()
    channel_width = (upper_channel - lower_channel) / df['close']

    narrow_channel = channel_width < channel_width.rolling(50).mean() * 0.8  # 通道收窄

    if narrow_channel.iloc[-1] and volume_spike.iloc[-1]:
        if in_uptrend.iloc[-1]:
            df.loc[df.index[-1]:, 'bull_flag'] = 1
        else:
            df.loc[df.index[-1]:, 'bear_flag'] = 1

    # 楔形（收敛 + 方向）
    if convergence and upper_slope < 0 and lower_slope < 0:
        df.loc[df.index[-1]:, 'wedge_down'] = 1  # 下降楔
    elif convergence and upper_slope > 0 and lower_slope > 0:
        df.loc[df.index[-1]:, 'wedge_up'] = 1

        # === 新增：矩形通道（水平支撑阻力整理 + 突破）===
    df['rectangle'] = 0
    df['rectangle_break_up'] = 0
    df['rectangle_break_down'] = 0

    # 水平通道检测（价格在支撑阻力间震荡）
    support = df['low'].rolling(50).min()
    resistance = df['high'].rolling(50).max()
    range_pct = (resistance - support) / df['close']

    # 窄通道（震荡）
    narrow_range = range_pct < range_pct.rolling(100).mean() * 0.7

    # 多次触碰（简化：价格靠近支撑/阻力次数）
    near_support = df['low'] <= support * 1.01
    near_resistance = df['high'] >= resistance * 0.99
    touches = (near_support | near_resistance).rolling(50).sum() > 6  # >6次触碰

    rectangle_mask = narrow_range & touches

    if rectangle_mask.iloc[-1]:
        df.loc[df.index[-1]:, 'rectangle'] = 1

        # 突破判断
        if df['close'].iloc[-1] > resistance.iloc[-1] and volume_spike.iloc[-1]:
            df.loc[df.index[-1]:, 'rectangle_break_up'] = 1
        elif df['close'].iloc[-1] < support.iloc[-1] and volume_spike.iloc[-1]:
            df.loc[df.index[-1]:, 'rectangle_break_down'] = 1
    
    return df