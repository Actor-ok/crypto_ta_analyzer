import pandas as pd
from utils.config_loader import load_config
from core.dataframe_enhancer import enhance_dataframe

try:
    # 1. 加载数据
    df = pd.read_csv('btc_usdt_swap_1m_history.csv', nrows=5000)

    print("原始列名（加载后）：", df.columns.tolist())

    # === 修复 volume 兼容：显式选择一个优先列 ===
    volume_priority = ['volume_usdt', 'volume_btc', 'volume_contracts']
    selected_volume_col = None
    for col in volume_priority:
        if col in df.columns:
            selected_volume_col = col
            break
    
    if selected_volume_col is None:
        raise ValueError("数据中没有找到任何 volume 列！")
    
    df = df.rename(columns={selected_volume_col: 'volume'})
    other_volume_cols = [c for c in volume_priority if c in df.columns and c != 'volume']
    df = df.drop(columns=other_volume_cols)
    
    print(f"选中 volume 列：{selected_volume_col} → 'volume'")
    # ================================================

    # 处理时间索引（必须在选列前，因为需要 timestamp_ms）
    df['timestamp'] = pd.to_datetime(df['timestamp_ms'], unit='ms')
    df.set_index('timestamp', inplace=True)
    
    # 强制升序（旧→新）
    df = df.sort_index(ascending=True)
    
    # 现在安全选列（只保留 OHLCV）
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    print(f"测试数据：{len(df)} 条，从 {df.index[0]} 到 {df.index[-1]}")

    # 2. 增强
    config = load_config('default.yaml')
    df_enhanced = enhance_dataframe(df, config)
    print("增强完成，列总数：", len(df_enhanced.columns))

    # 3. 自动检测新列
    base_columns = {'open', 'high', 'low', 'close', 'volume', 'timestamp_ms', 'datetime_utc', 'confirm',
                    'body', 'range', 'upper_shadow', 'lower_shadow', 'is_bullish',
                    'rsi', 'macd', 'macd_signal', 'macd_hist', 'ema_short', 'ema_medium', 'ema_long', 'ema_very_long',
                    'bb_upper', 'bb_mid', 'bb_lower', 'obv',
                    'hammer', 'bullish_engulfing', 'morning_star', 'three_white_soldiers', 'three_black_crows'}
    
    new_columns = [col for col in df_enhanced.columns if col not in base_columns and 
                   ('fib' in col or 'double' in col or 'head' in col or 'triangle' in col or 
                    'gap' in col or 'separation' in col or 'round' in col or 'support' in col or 'resistance' in col)]
    
    print("\n检测到的新形态/支撑列：", new_columns or "无（可能数据短或order太大）")
    
    if new_columns:
        print("\n新形态出现次数：")
        print(df_enhanced[new_columns].sum().sort_values(ascending=False))
        
        print("\n最近有新形态的行：")
        # 如果没有 'signal' 列，避免报错
        display_cols = new_columns + ['close']
        if 'signal' in df_enhanced.columns:
            display_cols += ['signal']
        print(df_enhanced[df_enhanced[new_columns].any(axis=1)].tail(10)[display_cols])
    
    # 4. 保存结果
    df_enhanced.to_csv('test_new_patterns_result.csv')
    print("\n测试结果保存到 test_new_patterns_result.csv")

except Exception as e:
    import traceback
    traceback.print_exc()
    print("错误详情：", e)