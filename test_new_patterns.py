import pandas as pd
from utils.config_loader import load_config
from core.dataframe_enhancer import enhance_dataframe

try:
    # 1. 加载数据（你的本地1m大文件）
    df = pd.read_csv('btc_usdt_swap_1m_history.csv', nrows=5000)

    print("原始列名（加载后）：", df.columns.tolist())

    # === 修复 volume 兼容 ===
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

    # 设置时间索引（根据你的列名调整）
    if 'timestamp_ms' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp_ms'], unit='ms')
    elif 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    df = df[['open', 'high', 'low', 'close', 'volume']]

    # 加载配置
    config = load_config('default.yaml')

    # === 新增：选择检测周期（1m数据最适合这里演示重采样）===
    chosen_timeframe = '4h'  # <-- 推荐 '4h' 或 '1h'（减少噪音），'1m' 为原始

    # 增强
    df_enhanced = enhance_dataframe(df, config, resample_to=chosen_timeframe)

    # 检测新列（包含所有可能的新形态/支撑阻力等）
    original_cols = ['open', 'high', 'low', 'close', 'volume']
    new_columns = [col for col in df_enhanced.columns 
                   if col not in original_cols + ['signal'] 
                   and ('gap' in col or 'tasuki' in col or 'separating' in col or 'two_crows' in col 
                        or 'side_by_side' in col or 'support' in col or 'resistance' in col)]
    
    print("\n检测到的新形态/支撑列：", new_columns or "无（可能数据短或order太大）")
    
    if new_columns:
        print("\n新形态出现次数：")
        print(df_enhanced[new_columns].sum().sort_values(ascending=False))
        
        print("\n最近有新形态的行：")
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