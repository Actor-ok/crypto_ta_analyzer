import pandas as pd
from scipy.signal import argrelextrema
import numpy as np

def detect_elliott_wave(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    df = df.copy()
    cfg = config.get('elliott', {})
    if not cfg.get('enabled', True):
        return df

    order = cfg.get('order', 20)

    df['wave_label'] = 'none'
    df['wave_confirmed'] = 0  # 确认波浪

    high_idx = argrelextrema(df['high'].values, np.greater_equal, order=order)[0]
    low_idx = argrelextrema(df['low'].values, np.less_equal, order=order)[0]

    all_idx = np.sort(np.concatenate((high_idx, low_idx)))

    if len(all_idx) >= 5:
        # 最近转折点价格
        points = []
        for idx in all_idx[-8:]:  # 最多8点（5浪+ABC）
            if idx in high_idx:
                points.append(('high', df['high'].iloc[idx]))
            else:
                points.append(('low', df['low'].iloc[idx]))

        # 简单规则：交替高低点
        labels = []
        current = 'low' if points[0][0] == 'low' else 'high'
        for i, (typ, price) in enumerate(points):
            labels.append(f'wave_{i+1}')
            if typ != current:
                current = typ

        # 3浪最长规则（简化）
        if len(points) >= 5:
            wave1_len = abs(points[1][1] - points[0][1])
            wave3_len = abs(points[3][1] - points[2][1])
            wave5_len = abs(points[5][1] - points[4][1])
            if wave3_len > wave1_len and wave3_len > wave5_len:
                df.loc[df.index[all_idx[-5]:], 'wave_confirmed'] = 1  # 确认5浪

        # 标记最近波浪
        for i, idx in enumerate(all_idx[-8:]):
            if i < len(labels):
                df.loc[df.index[idx]:, 'wave_label'] = labels[i]

    return df