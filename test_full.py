import ccxt
import pandas as pd
from utils.config_loader import load_config
from core.dataframe_enhancer import enhance_dataframe
from utils.plotter import plot_kline_with_signals

# 1. 获取数据（OKX BTC/USDT 1h，拿2000根确保有足够历史）
okx = ccxt.okx({'enableRateLimit': True})
data = okx.fetch_ohlcv('BTC/USDT', timeframe='1h', limit=2000)
df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.set_index('timestamp', inplace=True)

# 2. 加载配置
config = load_config('default.yaml')

# === 新增：选择策略周期 ===
strategy_timeframe = '1h'  # <-- 修改这里：'1h' 日内，'4h'/'1d' 波段，None 原始周期

# 3. 增强DataFrame
df_enhanced = enhance_dataframe(df, config, resample_to=strategy_timeframe)

# 4. 打印最近20根的关键信息
print(df_enhanced.tail(20)[[
    'close', 'ema_short', 'ema_medium', 'rsi', 'macd', 'signal',
    'doji', 'hammer', 'bullish_engulfing', 'three_black_crows'
]])

# 5. 统计形态出现次数
morph_columns = ['doji', 'hammer', 'bullish_engulfing', 'morning_star', 
                 'three_white_soldiers', 'three_black_crows', 'bearish_engulfing']
print("\n形态出现次数统计：")
print(df_enhanced[morph_columns].sum().sort_values(ascending=False))

print("\n最近交易信号：")
print(df_enhanced[df_enhanced['signal'] != 0].tail(10)[['close', 'signal', 'rsi', 'three_black_crows', 'hammer']])

# 6. 可视化（最近100根）
plot_kline_with_signals(df_enhanced, title="BTC/USDT 技术分析（带信号标注）", num_candles=100)

# 7. 保存完整数据
df_enhanced.to_csv('btc_enhanced_full.csv')
print("\n数据已保存到 btc_enhanced_full.csv")