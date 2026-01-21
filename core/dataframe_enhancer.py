import pandas as pd
from core.patterns.candlestick import detect_candlestick_patterns
from core.indicators import add_moving_averages, add_momentum_indicators, add_volume_indicators
from signals.signal_generator import generate_signals
from core.patterns.chart_patterns import detect_chart_patterns
from core.support_resistance import add_fibonacci_levels, add_support_resistance_levels
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema   # 新增这行
from core.indicators.divergence import add_divergence_indicators
from core.indicators.volume_divergence import add_obv_divergence
from core.indicators.obv_divergence import add_obv_divergence

def enhance_dataframe(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    # 加指标
    df = add_moving_averages(df, config)
    df = add_momentum_indicators(df, config)
    df = add_volume_indicators(df, config)
    
    # 加蜡烛形态
    df = detect_candlestick_patterns(df, config)

    # 加图表形态、支撑阻力、斐波（这些不依赖信号）
    df = detect_chart_patterns(df, config)                  # ← 移到这里
    df = add_support_resistance_levels(df, config)
    df = add_fibonacci_levels(df, config)

    df = add_divergence_indicators(df, config)  # ← 新增这行（放在信号前）

    df = add_obv_divergence(df, config)  # 放在信号前

    df = add_obv_divergence(df, config)

    # 最后生成信号（此时所有形态列都已存在）
    df = generate_signals(df, config)

    return df