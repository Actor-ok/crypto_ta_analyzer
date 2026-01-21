import pandas as pd

# 文件路径（假设 csv 在当前目录，如果不是请改路径）
csv_file = 'btc_usdt_swap_1m_history.csv'

# 读取 csv（只读必要列，节省内存）
print("正在读取 CSV 文件...")
df = pd.read_csv(csv_file, usecols=['timestamp_ms', 'datetime_utc'])  # 只读时间相关列

print(f"总行数：{len(df)}")

# 检查是否有 timestamp_ms 列（优先用它）
if 'timestamp_ms' in df.columns:
    print("使用 timestamp_ms 列转换时间...")
    df['timestamp'] = pd.to_datetime(df['timestamp_ms'], unit='ms')
else:
    raise ValueError("CSV 中没有 timestamp_ms 列！请检查列名。")

# 排序确保正确（有时数据乱序）
df = df.sort_values('timestamp')

# 输出时间范围
earliest = df['timestamp'].min()
latest = df['timestamp'].max()
span = latest - earliest

print("\n=== 时间范围检查结果 ===")
print(f"最早时间：{earliest} (UTC)")
print(f"最晚时间：{latest} (UTC)")
print(f"总跨度：{span}")
print(f"大约覆盖：{span.days} 天 {span.seconds // 3600} 小时")

# 额外：打印前5和后5行时间，确认数据完整性
print("\n前5根K线时间：")
print(df['timestamp'].head(5))

print("\n后5根K线时间：")
print(df['timestamp'].tail(5))

# 可选：如果有 datetime_utc 列，也对比一下
if 'datetime_utc' in df.columns:
    print("\n（参考）datetime_utc 列范围：")
    print(f"最早：{df['datetime_utc'].min()}")
    print(f"最晚：{df['datetime_utc'].max()}")