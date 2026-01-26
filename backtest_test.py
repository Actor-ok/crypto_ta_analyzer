import pandas as pd
from utils.config_loader import load_config
from core.dataframe_enhancer import enhance_dataframe
from backtest.engine import backtest_strategy

# 1. 加载CSV（大文件优化 + 智能列选择）
print("正在加载 CSV 文件...")
df = pd.read_csv('btc_usdt_swap_1m_history.csv', low_memory=False)

# 打印实际列名（关键调试！）
print("CSV原始列名：", df.columns.tolist())

# === 智能volume列优先级（推荐USDT成交额 > BTC量 > 合约数）===
volume_priority = ['volume_usdt', 'volume_btc', 'volume_contracts', 'volume']
selected_volume = None
for col in volume_priority:
    if col in df.columns:
        selected_volume = col
        break

if selected_volume is None:
    raise ValueError("未找到任何volume相关列！")

if selected_volume != 'volume':
    df = df.rename(columns={selected_volume: 'volume'})
    print(f"使用 {selected_volume} 作为 volume 列")

# 保留必要列 + 时间戳
required_cols = ['open', 'high', 'low', 'close', 'volume', 'timestamp_ms']
missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    raise ValueError(f"缺失必要列：{missing_cols}")

df = df[required_cols]

print(f"加载数据成功：{len(df)} 条")

# 2. 设置时间索引并排序（确保升序，resample 正常工作）
df['timestamp'] = pd.to_datetime(df['timestamp_ms'], unit='ms')
df.set_index('timestamp', inplace=True)
df = df.sort_index(ascending=True)  # 升序（旧 → 新）
df = df.drop(columns=['timestamp_ms'])  # 清理多余列

print(f"排序后数据范围：从 {df.index[0]} 到 {df.index[-1]}（共 {len(df)} 条）")

# 3. 加载配置
config = load_config('aggressive.yaml')  # 或切换 'default.yaml' / 'high_frequency.yaml'

# === 选择回测周期（支持任意pandas resample规则）===
# 推荐：'15min', '30min', '1h', '4h', '1d'
# pandas别名：'15T' = 15min, '30T' = 30min
strategy_timeframe = '30min'  # <--- 修改这里测试不同周期，例如 '30min' 或 '15min'

print(f"正在重采样到 {strategy_timeframe.upper()} 周期...")

# === 通用OHLCV重采样（open first, high max, low min, close last, volume sum）===
ohlc_dict = {
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}

# 执行重采样（支持任意周期，如 '30min', '15min', '4h' 等）
df = df.resample(strategy_timeframe.upper()).agg(ohlc_dict)

# 丢弃NaN行（重采样开头/结尾可能有）
df = df.dropna()

print(f"重采样完成，数据量: {len(df)} 根K线")

# 4. 数据增强 + 回测
print("正在增强数据框（计算指标、形态、信号）...")
df_enhanced = enhance_dataframe(df, config)  # 已重采样，无需传 resample_to

# 保险再排序
df_enhanced = df_enhanced.sort_index()

# 5. 回测
print("正在执行回测...")
performance, df_backtest = backtest_strategy(df_enhanced, initial_capital=100000, config=config)

# === 输出统计 ===
print("\n新图表形态统计：")
chart_cols = ['symmetrical_triangle', 'ascending_triangle', 'descending_triangle', 
              'bull_flag', 'bear_flag', 'rectangle', 'double_top', 'double_bottom']
available_chart = [col for col in chart_cols if col in df_enhanced.columns]
if available_chart:
    print(df_enhanced[available_chart].sum())
else:
    print("无图表形态列")

print("\n趋势线突破统计：")
if 'trendline_break_up' in df_enhanced.columns:
    print(df_enhanced['trendline_break_up'].sum(), "向上突破")
    print(df_enhanced['trendline_break_down'].sum(), "向下突破")
else:
    print("无趋势线突破列")

print("\n量价指标统计：")
if 'cmf' in df_enhanced.columns:
    print("CMF >0 次数:", (df_enhanced['cmf'] > 0).sum())
if 'volume_osc' in df_enhanced.columns:
    print("Volume Osc >0 次数:", (df_enhanced['volume_osc'] > 0).sum())

print("\n波浪统计：")
if 'wave_label' in df_enhanced.columns:
    print(df_enhanced['wave_label'].value_counts())
if 'wave_confirmed' in df_enhanced.columns:
    print("确认5浪次数:", df_enhanced['wave_confirmed'].sum())

print("\n回测绩效：")
for k, v in performance.items():
    if isinstance(v, float):
        print(f"{k}: {v:.4f}")
    else:
        print(f"{k}: {v}")

# 保存结果
df_backtest.to_parquet('backtest_result.parquet')
print("\n回测结果已保存到 backtest_result.parquet（更快更小）")