import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

def detect_chart_patterns(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    df = df.copy()
    cfg = config.get('chart_patterns', {})
    order = cfg.get('extrema_order', 20)
    
    print(f"[DEBUG] detect_chart_patterns 开始，order={order}, 数据长度={len(df)}")
    
    df['double_top'] = 0
    df['double_bottom'] = 0
    
    high_values = df['high'].values
    low_values = df['low'].values
    
    # 强制1D + squeeze
    highs_idx = argrelextrema(high_values, np.greater_equal, order=order)[0].squeeze().ravel()
    lows_idx = argrelextrema(low_values, np.less_equal, order=order)[0].squeeze().ravel()
    
    print(f"[DEBUG] highs_idx shape: {highs_idx.shape}, 数量: {len(highs_idx)}")
    
    tolerance = cfg.get('peak_trough_tolerance', 0.05)
    
    # 双顶（全标量索引）
    if len(highs_idx) >= 3:
        for i in range(len(highs_idx) - 2):
            idx1 = int(highs_idx[i])  # 强制标量int
            idx2 = int(highs_idx[i + 1])
            idx3 = int(highs_idx[i + 2])
            
            h1 = high_values[idx1]
            h2 = high_values[idx2]
            h3 = high_values[idx3]
            
            if h2 >= h1 * (1 - tolerance) and h2 >= h3 * (1 - tolerance) and abs(h1 - h3) / h2 <= tolerance:
                start = min(idx1, idx2, idx3)
                end = max(idx1, idx2, idx3) + 1
                neckline = np.min(low_values[start:end])
                
                if df['close'].iloc[-1] < neckline:
                    df['double_top'].iloc[idx3:] = 1
                    print(f"[DEBUG] 检测到双顶 at {idx3}")
    
    # 双底
    if len(lows_idx) >= 3:
        for i in range(len(lows_idx) - 2):
            idx1 = int(lows_idx[i])
            idx2 = int(lows_idx[i + 1])
            idx3 = int(lows_idx[i + 2])
            
            l1 = low_values[idx1]
            l2 = low_values[idx2]
            l3 = low_values[idx3]
            
            if l2 <= l1 * (1 + tolerance) and l2 <= l3 * (1 + tolerance) and abs(l1 - l3) / abs(l2) <= tolerance:
                start = min(idx1, idx2, idx3)
                end = max(idx1, idx2, idx3) + 1
                neckline = np.max(high_values[start:end])
                
                if df['close'].iloc[-1] > neckline:
                    df['double_bottom'].iloc[idx3:] = 1
                    print(f"[DEBUG] 检测到双底 at {idx3}")
    
    print("[DEBUG] detect_chart_patterns 结束")
    return df