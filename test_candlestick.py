import ccxt
import pandas as pd
from utils.config_loader import load_config
from core.patterns.candlestick import detect_candlestick_patterns

# 获取真实数据测试（OKX BTC/USDT 1h，增加到1000根更保险）
okx = ccxt.okx({'enableRateLimit': True})  # 加限速避免API报错
data = okx.fetch_ohlcv('BTC/USDT', timeframe='1h', limit=1000)
df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.set_index('timestamp', inplace=True)

# 加载配置
config = load_config('default.yaml')  # 或试试 'volatile.yaml' 看差异

# 检测形态
df = detect_candlestick_patterns(df, config)

# === 新增：打印最近20根的所有形态列，检查是否有1 ===
print("最近20根K线的形态检测结果：")
print(df.tail(20)[[
    'open', 'high', 'low', 'close', 'volume',
    'doji', 'dragonfly_doji', 'gravestone_doji', 'long_legged_doji',
    'spinning_top', 'hammer', 'inverted_hammer',
    'bullish_engulfing', 'bearish_engulfing',
    'piercing', 'dark_cloud_cover',
    'morning_star', 'evening_star',
    'three_white_soldiers', 'three_black_crows'
]])

# === 如果想看整个数据集里有哪些形态出现了 ===
# === 统计各种形态在整个1000根数据中出现次数 ===
morph_columns = [
    'doji', 'dragonfly_doji', 'gravestone_doji', 'long_legged_doji',
    'spinning_top', 'hammer', 'inverted_hammer', 'shooting_star',
    'bullish_engulfing', 'bearish_engulfing',
    'piercing', 'dark_cloud_cover',
    'morning_star', 'evening_star',
    'three_white_soldiers', 'three_black_crows'
]

print("\n各种形态出现次数统计（全数据）：")
print(df[morph_columns].sum().sort_values(ascending=False))

# 保存方便你用Excel查看
df.to_csv('test_with_patterns_full.csv')