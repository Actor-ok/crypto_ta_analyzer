# 总体目标：高级K线绘图（mplfinance），带信号标注、布林、EMA、RSI、MACD多面板。
# 输入：增强DataFrame + 参数
# 输出：交互式图表（plt.show()）
# 关键代码块：make_addplot叠加各种线/柱状图 + 信号箭头标注。

import mplfinance as mpf
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def plot_kline_with_signals(df: pd.DataFrame, title: str = "K线技术分析", num_candles: int = 100):
    """
    完美版：K线 + 信号标注 + 布林带 + EMA线 + RSI + MACD + 成交量
    """
    df_plot = df.tail(num_candles).copy()
    
    add_plots = []
    
    # 看涨信号（绿色大↑）
    bullish_mask = (
        (df_plot['hammer'] == 1) |
        (df_plot['bullish_engulfing'] == 1) |
        (df_plot['morning_star'] == 1) |
        (df_plot['three_white_soldiers'] == 1) |
        (df_plot['piercing'] == 1) |
        (df_plot['dragonfly_doji'] == 1)
    )
    if bullish_mask.any():
        bullish_data = pd.Series(np.nan, index=df_plot.index)
        bullish_data[bullish_mask] = df_plot['low'][bullish_mask] * 0.99
        add_plots.append(mpf.make_addplot(bullish_data, type='scatter', markersize=300, marker='^', color='lime'))
    
    # 看跌信号（红色大↓）
    bearish_mask = (
        (df_plot['shooting_star'] == 1) |
        (df_plot['bearish_engulfing'] == 1) |
        (df_plot['evening_star'] == 1) |
        (df_plot['three_black_crows'] == 1) |
        (df_plot['dark_cloud_cover'] == 1) |
        (df_plot['gravestone_doji'] == 1)
    )
    if bearish_mask.any():
        bearish_data = pd.Series(np.nan, index=df_plot.index)
        bearish_data[bearish_mask] = df_plot['high'][bearish_mask] * 1.01
        add_plots.append(mpf.make_addplot(bearish_data, type='scatter', markersize=300, marker='v', color='red'))
    
    # 布林带
    add_plots.extend([
        mpf.make_addplot(df_plot['bb_upper'], color='gray', alpha=0.6),
        mpf.make_addplot(df_plot['bb_mid'], color='blue', alpha=0.8),
        mpf.make_addplot(df_plot['bb_lower'], color='gray', alpha=0.6),
    ])
    
    # EMA线
    add_plots.extend([
        mpf.make_addplot(df_plot['ema_short'], color='orange', alpha=0.8),
        mpf.make_addplot(df_plot['ema_medium'], color='purple', alpha=0.8),
        mpf.make_addplot(df_plot['ema_long'], color='green', alpha=0.8),
    ])
    
    # RSI 面板1
    add_plots.append(mpf.make_addplot(df_plot['rsi'], panel=1, color='purple', ylim=(0,100), ylabel='RSI'))
    
    # MACD 面板2
    add_plots.extend([
        mpf.make_addplot(df_plot['macd'], panel=2, color='blue'),
        mpf.make_addplot(df_plot['macd_signal'], panel=2, color='orange'),
        mpf.make_addplot(df_plot['macd_hist'], panel=2, type='bar', color='gray', alpha=0.6, ylabel='MACD'),
    ])
    
    # 主图绘制
    mpf.plot(
        df_plot,
        type='candle',
        style='charles',
        title=title,
        ylabel='Price',
        addplot=add_plots,
        volume=True,  # 成交量在主图下方
        panel_ratios=(6, 1, 1),  # 3个面板：主图大 + RSI + MACD
        figsize=(20,12),
        show_nontrading=False
    )
    plt.show()