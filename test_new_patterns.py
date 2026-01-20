import pandas as pd
from utils.config_loader import load_config
from core.dataframe_enhancer import enhance_dataframe

try:
    # 1. 加载数据（优先parquet加速，否则CSV小样本）
    if pd.io.parquet.get_engine('auto'):  # 检查parquet可用
        try:
            df = pd.read_parquet('btc_enhanced.parquet')  # 如果有保存的中间
            print("加载中间parquet加速")
        except:
            df = pd.read_csv('btc_usdt_swap_1m_history.csv', nrows=5000)  # 更多根测试形态
    else:
        df = pd.read_csv('btc_usdt_swap_1m_history.csv', nrows=5000)

    # 处理列 + 时间索引
    print("原始列名：", df.columns.tolist())
    df = df.rename(columns={'volume_usdt': 'volume', 'volume_btc': 'volume', 'volume_contracts': 'volume'})  # 自动兼容
    df['timestamp'] = pd.to_datetime(df['timestamp_ms'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df[['open', 'high', 'low', 'close', 'volume']]

    print(f"测试数据：{len(df)} 条，从 {df.index[0]} 到 {df.index[-1]}")

    # 2. 增强
    config = load_config('default.yaml')  # 或 'volatile.yaml'
    df_enhanced = enhance_dataframe(df, config)
    print("增强完成，列总数：", len(df_enhanced.columns))

    # 3. 自动检测新列（避免硬编码报错）
    base_columns = {'open', 'high', 'low', 'close', 'volume', 'timestamp_ms', 'datetime_utc', 'confirm',
                    'body', 'range', 'upper_shadow', 'lower_shadow', 'is_bullish',  # 基础
                    'rsi', 'macd', 'macd_signal', 'macd_hist', 'ema_short', 'ema_medium', 'ema_long', 'ema_very_long',
                    'bb_upper', 'bb_mid', 'bb_lower', 'obv',  # 指标
                    'hammer', 'bullish_engulfing', 'morning_star', 'three_white_soldiers', 'three_black_crows'}  # 旧形态示例
    
    new_columns = [col for col in df_enhanced.columns if col not in base_columns and 
                   ('fib' in col or 'double' in col or 'head' in col or 'triangle' in col or 
                    'gap' in col or 'separation' in col or 'round' in col)]
    
    print("\n检测到的新形态/支撑列：", new_columns or "无（可能数据短或order太大）")
    
    if new_columns:
        print("\n新形态出现次数：")
        print(df_enhanced[new_columns].sum().sort_values(ascending=False))
        
        print("\n最近有新形态的行：")
        print(df_enhanced[df_enhanced[new_columns].any(axis=1)].tail(10)[new_columns + ['close', 'signal']])
    
    # 4. 保存测试结果
    df_enhanced.to_csv('test_new_patterns_result.csv')
    print("\n测试结果保存到 test_new_patterns_result.csv")

except Exception as e:
    print("错误详情：", e)
    print("建议：检查core/support_resistance.py是否正确添加列，或config extrema_order太小")