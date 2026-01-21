import ccxt
import pandas as pd
from utils.config_loader import load_config
from core.dataframe_enhancer import enhance_dataframe  # 注意：现在用 enhance_dataframe

# 获取真实数据测试（OKX BTC/USDT 1h，增加到1000根更保险）
okx = ccxt.okx({'enableRateLimit': True})  # 加限速避免API报错
data = okx.fetch_ohlcv('BTC/USDT', timeframe='1h', limit=1000)
df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.set_index('timestamp', inplace=True)

# 加载配置
config = load_config('default.yaml')  # 或试试 'volatile.yaml' 看差异

# === 新增：选择检测周期 ===
# None 或 '1m'：使用原始周期
# '1h'：日内交易   '4h'/'1d'：波段交易（形态更清晰）
chosen_timeframe = '1h'  # <-- 这里改你想要的周期（当前数据已是1h，可试 '4h' 看重采样效果）

# 使用新的增强入口（包含重采样）
df_enhanced = enhance_dataframe(df, config, resample_to=chosen_timeframe)

# === 打印最近20根的所有形态列，检查是否有1 ===
print("最近20根K线的形态检测结果：")
print(df_enhanced.tail(20)[[
    'doji', 'dragonfly_doji', 'gravestone_doji', 'long_legged_doji',
    'spinning_top', 'hammer', 'inverted_hammer', 'shooting_star',
    'bullish_engulfing', 'bearish_engulfing',
    'piercing', 'dark_cloud_cover',
    'morning_star', 'evening_star',
    'three_white_soldiers', 'three_black_crows',
    # 新增的持续形态（可根据需要增删）
    'upside_gap_two_crows', 'tasuki_upside_gap', 'tasuki_downside_gap',
    'side_by_side_white_lines', 'separating_lines_up', 'separating_lines_down'
]])

# === 统计各种形态在整个数据中出现次数 ===
morph_columns = [
    'doji', 'dragonfly_doji', 'gravestone_doji', 'long_legged_doji',
    'spinning_top', 'hammer', 'inverted_hammer', 'shooting_star',
    'bullish_engulfing', 'bearish_engulfing',
    'piercing', 'dark_cloud_cover',
    'morning_star', 'evening_star',
    'three_white_soldiers', 'three_black_crows',
    # 新增持续形态
    'upside_gap_two_crows', 'tasuki_upside_gap', 'tasuki_downside_gap',
    'side_by_side_white_lines', 'separating_lines_up', 'separating_lines_down'
]

print("\n各种形态出现次数统计（全数据）：")
print(df_enhanced[morph_columns].sum().sort_values(ascending=False))

# 保存方便你用Excel查看
df_enhanced.to_csv('test_with_patterns_full.csv')
print("\n保存完成：test_with_patterns_full.csv")