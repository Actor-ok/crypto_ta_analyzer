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
    
    return df