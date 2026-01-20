import pandas as pd
from core.patterns.candlestick import detect_candlestick_patterns
from core.indicators import add_moving_averages, add_momentum_indicators, add_volume_indicators
from signals.signal_generator import generate_signals
from core.patterns.chart_patterns import detect_chart_patterns
from core.support_resistance import add_fibonacci_levels

def enhance_dataframe(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    # 加指标
    df = add_moving_averages(df, config)
    df = add_momentum_indicators(df, config)
    df = add_volume_indicators(df, config)
    
    # 加蜡烛形态
    df = detect_candlestick_patterns(df, config)

    df = generate_signals(df, config)

    # df = detect_chart_patterns(df, config)  # 新
    df = add_fibonacci_levels(df, config)   # 新
    
    return df