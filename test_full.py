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

# 2. 加载配置（试试 default 或 volatile）
config = load_config('default.yaml')

# 3. 增强DataFrame（指标 + 形态）
df_enhanced = enhance_dataframe(df, config)

# 4. 打印最近20根的关键信息
print("最近20根K线（带指标+形态）：")
print(df_enhanced.tail(20)[[
    'close', 'volume', 'rsi', 'macd_hist',
    'ema_short', 'bb_upper', 'bb_lower',
    'doji', 'hammer', 'bullish_engulfing', 'three_black_crows'
]])

# 5. 统计形态出现次数
morph_columns = ['doji', 'hammer', 'bullish_engulfing', 'morning_star', 
                 'three_white_soldiers', 'three_black_crows', 'bearish_engulfing']
print("\n形态出现次数统计：")
print(df_enhanced[morph_columns].sum().sort_values(ascending=False))

print("\n最近交易信号：")
print(df_enhanced[df_enhanced['signal'] != 0].tail(10)[['close', 'signal', 'rsi', 'three_black_crows', 'hammer']])

# 6. 可视化（最近100根，带标注）
plot_kline_with_signals(df_enhanced, title="BTC/USDT 技术分析（带信号标注）", num_candles=100)

# 7. 保存完整数据（方便Excel查看）
df_enhanced.to_csv('btc_enhanced_full.csv')
print("\n数据已保存到 btc_enhanced_full.csv")