import pandas as pd
from utils.config_loader import load_config
from core.dataframe_enhancer import enhance_dataframe
from backtest.engine import backtest_strategy

# 1. 加载CSV（大文件优化）
df = pd.read_csv('btc_usdt_swap_1m_history.csv', low_memory=False)

# 打印实际列名（关键调试！）
print("CSV原始列名：", df.columns.tolist())

# 标准列重命名（根据你的实际列名调整）
column_mapping = {
    'open': 'open',
    'high': 'high',
    'low': 'low',
    'close': 'close',
    'volume_usdt': 'volume',         # <--- 优先用USDT成交额作为volume（推荐）
    # 'volume_btc': 'volume',        # 备选：如果想用BTC量，注释上行，启用这行
    # 'volume_contracts': 'volume',  # 合约量（少用）
}

df = df.rename(columns=column_mapping)

# 保留必要列
required_cols = ['open', 'high', 'low', 'close', 'volume']
missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    raise ValueError(f"缺失必要列：{missing_cols}")

df = df[required_cols + ['timestamp_ms']]  # 保留时间戳列

print(f"加载数据成功：{len(df)} 条")

# 2. 设置时间索引并排序（关键修复：确保升序，resample 正常工作）
if 'timestamp_ms' in df.columns:
    df['timestamp'] = pd.to_datetime(df['timestamp_ms'], unit='ms')
else:
    raise ValueError("没有找到 timestamp_ms 列！")

df.set_index('timestamp', inplace=True)
df = df.sort_index(ascending=True)  # <--- 关键：升序（旧 → 新）
print(f"排序后数据范围：从 {df.index[0]} 到 {df.index[-1]}（共 {len(df)} 条）")

# 3. 加载配置
# config = load_config('default.yaml')  # 或 'volatile.yaml' 测试高波动
config = load_config('aggressive.yaml')

# === 选择回测周期 ===
# '1m'：高频（原始）   '15m'/'1h'：日内   '4h'/'1d'：波段/趋势（推荐4h，噪音少）
strategy_timeframe = '4h'  # <--- 你的近3年数据足够，4h 会产生 ~6000 根K线

# 4. 增强 + 回测
df_enhanced = enhance_dataframe(df, config, resample_to=strategy_timeframe)
df_enhanced = df_enhanced.sort_index()  # 保险再排序（虽已升序）

performance, df_backtest = backtest_strategy(df_enhanced, initial_capital=100000, config=config)

print("\n新图表形态统计：")
print(df_enhanced[['symmetrical_triangle', 'ascending_triangle', 'descending_triangle', 'bull_flag', 'bear_flag']].sum())


print("\n趋势线突破统计：")
print(df_enhanced['trendline_break_up'].sum(), "向上突破")
print(df_enhanced['trendline_break_down'].sum(), "向下突破")


print("\n量价指标统计：")
print("CMF >0 次数:", (df_enhanced['cmf'] > 0).sum())
print("Volume Osc >0 次数:", (df_enhanced['volume_osc'] > 0).sum())


print("\n波浪统计：")
print(df_enhanced['wave_label'].value_counts())
print("确认5浪次数:", df_enhanced['wave_confirmed'].sum())


print("\n回测绩效：")
for k, v in performance.items():
    print(f"{k}: {v:.4f}" if isinstance(v, float) else f"{k}: {v}")

df_backtest.to_parquet('backtest_result.parquet')
print("\n回测结果已保存到 backtest_result.parquet（更快更小）")