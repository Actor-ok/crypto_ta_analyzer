import pandas as pd
from core.patterns.candlestick import detect_candlestick_patterns
from core.indicators import add_moving_averages, add_momentum_indicators, add_volume_indicators
from signals.signal_generator import generate_signals
from core.patterns.chart_patterns import detect_chart_patterns
from core.support_resistance import add_fibonacci_levels, add_support_resistance_levels
from core.indicators.divergence import add_divergence_indicators
from core.indicators.obv_divergence import add_obv_divergence
from core.patterns.elliott_wave import detect_elliott_wave
from core.patterns.trendlines import add_trendlines_and_channels  # 新增导入

# === 新增导入：跳空检测 ===
from core.patterns.gaps import detect_gaps

def enhance_dataframe(df: pd.DataFrame, config: dict, resample_to: str = None) -> pd.DataFrame:
    df = df.copy()
    
    if resample_to:
        rule_map = {
            '1m': '1T',
            '15m': '15T',
            '1h': '1h',
            '4h': '4h',
            '1d': '1D',
            '3d': '3D',
            '1w': '1W'
        }
        rule = rule_map.get(resample_to.lower())
        if rule is None:
            raise ValueError(f"不支持的 resample_to: {resample_to}")
        
        print(f"正在重采样到 {resample_to.upper()} 周期...")
        df = df.resample(rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        print(f"重采样完成，数据量: {len(df)} 根K线")
    
    if len(df) < 50:
        raise ValueError(f"数据太少（只有 {len(df)} 根K线），无法可靠计算指标。")

    df = add_moving_averages(df, config)
    df = add_momentum_indicators(df, config)
    df = add_volume_indicators(df, config)
    
    df = detect_candlestick_patterns(df, config)

    # === 强制调用跳空检测（带打印确认）===
    print("正在执行跳空检测（detect_gaps）...")
    df = detect_gaps(df, config)
    print(f"跳空检测完成，新列示例: gap_type 值计数\n{df['gap_type'].value_counts().head()}")

    df = detect_elliott_wave(df, config)

    df = detect_chart_patterns(df, config)

    df = add_trendlines_and_channels(df, config)  # 新增

    df = add_support_resistance_levels(df, config)
    df = add_fibonacci_levels(df, config)

    df = add_divergence_indicators(df, config)
    df = add_obv_divergence(df, config)

    df = generate_signals(df, config)

    return df