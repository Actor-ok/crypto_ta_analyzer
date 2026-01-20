import pandas as pd
from utils.config_loader import load_config
from core.dataframe_enhancer import enhance_dataframe
from backtest.engine import backtest_strategy

# 1. 加载CSV（大文件优化）
df = pd.read_csv('btc_usdt_swap_1m_history.csv', low_memory=False)

# 打印实际列名（关键调试！）
print("CSV原始列名：", df.columns.tolist())

# 标准列重命名（根据你的截图调整，常见OKX列）
# 标准列重命名（根据你的实际列名调整）
column_mapping = {
    'timestamp_ms': 'timestamp_ms',  # 时间戳列（保持）
    'open': 'open',
    'high': 'high',
    'low': 'low',
    'close': 'close',
    'volume_usdt': 'volume',         # <--- 关键：用USDT量作为volume（推荐）
    # 'volume_btc': 'volume',        # 备选：如果想用BTC量，注释上行，启用这行
    # 'volume_contracts': 'volume',  # 备选：合约张数
}

df = df.rename(columns=column_mapping)

# 检查是否成功有 volume 列
if 'volume' not in df.columns:
    raise ValueError(f"未找到交易量列！可用列: {df.columns.tolist()} 请手动调整mapping")

# 时间索引
df['timestamp'] = pd.to_datetime(df['timestamp_ms'], unit='ms')
df.set_index('timestamp', inplace=True)

# 只保留标准OHLCV
df = df[['open', 'high', 'low', 'close', 'volume']]

print(f"加载数据成功：{len(df)} 条，从 {df.index[0]} 到 {df.index[-1]}")
print("最终列名：", df.columns.tolist())

# 2. 增强 + 回测（同之前）
config = load_config('default.yaml')  # 或 volatile.yaml 测试高波动
df_enhanced = enhance_dataframe(df, config)

performance, df_backtest = backtest_strategy(df_enhanced, initial_capital=100000, risk_per_trade=0.02)

print("\n回测绩效：")
for k, v in performance.items():
    print(f"{k}: {v:.4f}" if isinstance(v, float) else f"{k}: {v}")

df_backtest.to_parquet('backtest_result.parquet')
print("\n回测结果已保存到 backtest_result.parquet（更快更小）")