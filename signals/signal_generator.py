import pandas as pd
import numpy as np

def generate_signals(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    生成交易信号：1=买入, -1=卖出, 0=无信号/持仓
    当前逻辑以多头为主（现货），空头信号可后续扩展
    已整合：
    - 蜡烛反转形态
    - 蜡烛持续形态
    - 图表形态确认（双顶/双底、头肩）
    - 背离（RSI/MACD/OBV）
    - 跳空形态（新增：突破/持续跳空作为强趋势确认）
    - 趋势过滤 + 放量确认
    """
    df = df.copy()
    df['signal'] = 0  # 初始化信号列

    c = config['confirmation']
    i = config['indicators']

    # === 1. 趋势过滤：经典多头环境（收盘价 > EMA200）===
    in_uptrend = df['close'] > df['ema_very_long']

    # === 2. 放量确认（> 20期均量 1.5倍，经典突破要求）===
    vol_ma20 = df['volume'].rolling(20).mean()
    volume_spike = df['volume'] > vol_ma20 * 1.5

    # === 3. RSI 不过度极端（避免超买区追高）===
    rsi_not_extreme = (df['rsi'] < i['rsi']['overbought']) & (df['rsi'] > i['rsi']['oversold'])

    # === 4. 基础反转形态（多头）===
    bullish_reversal = (
        (df['hammer'] == 1) |
        (df['bullish_engulfing'] == 1) |
        (df['morning_star'] == 1) |
        (df['three_white_soldiers'] == 1) |
        (df['piercing'] == 1) |
        (df['dragonfly_doji'] == 1) |
        (df['doji'] == 1)
    ).astype(bool)

    # === 5. 基础反转形态（空头）===
    bearish_reversal = (
        (df['shooting_star'] == 1) |
        (df['bearish_engulfing'] == 1) |
        (df['evening_star'] == 1) |
        (df['three_black_crows'] == 1) |
        (df['dark_cloud_cover'] == 1) |
        (df['gravestone_doji'] == 1)
    ).astype(bool)

    # === 6. 持续形态（趋势延续）===
    bullish_continuation = (
        (df['tasuki_upside_gap'] == 1) |
        (df['side_by_side_white_lines'] == 1) |
        (df['separating_lines_up'] == 1) |
        (df['rising_three_methods'] == 1)
    ).astype(bool)

    bearish_continuation = (
        (df['upside_gap_two_crows'] == 1) |
        (df['tasuki_downside_gap'] == 1) |
        (df['separating_lines_down'] == 1) |
        (df['falling_three_methods'] == 1)
    ).astype(bool)

    # === 7. 图表形态确认（强信号）===
    chart_bullish_confirm = (
        (df['double_bottom_confirmed'] == 1) |
        (df['hs_bottom_confirmed'] == 1)
    ).astype(bool)

    chart_bearish_confirm = (
        (df['double_top_confirmed'] == 1) |
        (df['hs_top_confirmed'] == 1)
    ).astype(bool)

    # === 8. 背离信号（强反转确认）===
    rsi_bull_div = df.get('rsi_bullish_div', pd.Series(0, index=df.index)).astype(bool)
    rsi_bear_div = df.get('rsi_bearish_div', pd.Series(0, index=df.index)).astype(bool)
    macd_bull_div = df.get('macd_bullish_div', pd.Series(0, index=df.index)).astype(bool)
    macd_bear_div = df.get('macd_bearish_div', pd.Series(0, index=df.index)).astype(bool)
    obv_bull_div = df.get('obv_bullish_div', pd.Series(0, index=df.index)).astype(bool)
    obv_bear_div = df.get('obv_bearish_div', pd.Series(0, index=df.index)).astype(bool)

    bullish_divergence = (rsi_bull_div | macd_bull_div | obv_bull_div)
    bearish_divergence = (rsi_bear_div | macd_bear_div | obv_bear_div)

    # === 9. 新增：跳空信号（强趋势确认）===
    # 安全获取 gap_type（防止未调用 gaps.py 时出错）
    gap_type = df.get('gap_type', pd.Series('none', index=df.index))

    breakout_continuation_bull = gap_type.str.contains('breakaway_up|continuation_up')
    exhaustion_bull = gap_type.str.contains('exhaustion_up')  # 可选：作为潜在反转警告

    breakout_continuation_bear = gap_type.str.contains('breakaway_down|continuation_down')

    # === 10. 生成多头信号（多重确认）===
    long_signal = (
        in_uptrend &
        rsi_not_extreme &
        volume_spike &
        (
            bullish_reversal |
            chart_bullish_confirm |
            bullish_divergence |
            bullish_continuation |
            breakout_continuation_bull  # 新增：跳空突破/持续作为强确认
        )
    )

    # === 11. 生成空头信号（保守）===
    short_signal = (
        ~in_uptrend &
        rsi_not_extreme &
        volume_spike &
        (
            bearish_reversal |
            chart_bearish_confirm |
            bearish_divergence |
            bearish_continuation |
            breakout_continuation_bear
        )
    )

    # === 12. 赋值信号（多头优先）===
    df.loc[long_signal, 'signal'] = 1
    df.loc[short_signal & ~long_signal, 'signal'] = -1

        # 新增三角/旗形确认
    triangle_bull = (df['ascending_triangle'] == 1) | (df['symmetrical_triangle'] == 1)
    triangle_bear = (df['descending_triangle'] == 1)

    flag_bull = (df['bull_flag'] == 1) | (df['wedge_up'] == 1)
    flag_bear = (df['bear_flag'] == 1) | (df['wedge_down'] == 1)

    # 加到信号
    long_signal = long_signal | (in_uptrend & (triangle_bull | flag_bull) & volume_spike)

        # 新增矩形突破确认
    rectangle_bull = (df['rectangle_break_up'] == 1)
    rectangle_bear = (df['rectangle_break_down'] == 1)

    long_signal = long_signal | (in_uptrend & rectangle_bull)
    short_signal = short_signal | (~in_uptrend & rectangle_bear)

    wave_3 = df['wave_label'] == '3'  # 第3浪强买
    long_signal = long_signal | (in_uptrend & wave_3)


        # 新增：趋势线/通道突破确认
    trend_break_bull = df.get('trendline_break_up', pd.Series(False, index=df.index))
    trend_break_bear = df.get('trendline_break_down', pd.Series(False, index=df.index))

    long_signal = long_signal | (in_uptrend & trend_break_bull & volume_spike)
    short_signal = short_signal | (~in_uptrend & trend_break_bear & volume_spike)


        # 新增量价加强
    cmf_positive = df.get('cmf', pd.Series(0, index=df.index)) > 0
    volume_osc_positive = df.get('volume_osc', pd.Series(0, index=df.index)) > 0

    # 多头加强（资金流入 + 量增）
    long_signal = long_signal | (in_uptrend & cmf_positive & volume_osc_positive)

        # 新增量价确认
    cmf_positive = df.get('cmf', pd.Series(0, index=df.index)) > 0
    volume_osc_positive = df.get('volume_osc', pd.Series(0, index=df.index)) > 0
    close_above_vwap = df['close'] > df.get('vwap', df['close'])

    # 多头加强（资金流入 + 量增 + 价上均线）
    long_signal = long_signal | (in_uptrend & cmf_positive & volume_osc_positive & close_above_vwap)


        # 新增波浪确认
    wave_3 = df['wave_label'] == 'wave_3'
    wave_confirmed = df['wave_confirmed'] == 1

    long_signal = long_signal | (in_uptrend & wave_3 & wave_confirmed)


    return df