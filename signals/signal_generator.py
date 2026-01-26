import pandas as pd
import numpy as np

def generate_signals(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    生成交易信号：1=买入, -1=卖出, 0=无信号/持仓
    当前逻辑以多头为主（现货），空头信号可后续扩展
    已整合所有形态/量价/波浪/趋势线等
    """
    df = df.copy()
    df['signal'] = 0

    c = config.get('confirmation', {})
    i = config.get('indicators', {})

    index = df.index
    long_signal = pd.Series(False, index=index)
    short_signal = pd.Series(False, index=index)

    # 趋势过滤
    in_uptrend = df['close'] > df['ema_very_long']

    # 放量
    vol_ma20 = df['volume'].rolling(20).mean()
    volume_spike = df['volume'] > vol_ma20 * 1.5

    # RSI合理
    rsi_overbought = i['rsi'].get('overbought', 70)
    rsi_oversold = i['rsi'].get('oversold', 30)
    rsi_not_extreme = (df['rsi'] < rsi_overbought) & (df['rsi'] > rsi_oversold)

    # 蜡烛反转
    bullish_reversal = (
        (df['hammer'] == 1) |
        (df['bullish_engulfing'] == 1) |
        (df['morning_star'] == 1) |
        (df['three_white_soldiers'] == 1) |
        (df['piercing'] == 1) |
        (df['dragonfly_doji'] == 1) |
        (df['doji'] == 1)
    ).astype(bool)

    bearish_reversal = (
        (df['shooting_star'] == 1) |
        (df['bearish_engulfing'] == 1) |
        (df['evening_star'] == 1) |
        (df['three_black_crows'] == 1) |
        (df['dark_cloud_cover'] == 1) |
        (df['gravestone_doji'] == 1)
    ).astype(bool)

    # 蜡烛持续
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

    # 图表确认
    chart_bullish_confirm = (
        (df['double_bottom_confirmed'] == 1) |
        (df['hs_bottom_confirmed'] == 1)
    ).astype(bool)

    chart_bearish_confirm = (
        (df['double_top_confirmed'] == 1) |
        (df['hs_top_confirmed'] == 1)
    ).astype(bool)

    # 三角/旗形/矩形
    triangle_bull = (df['ascending_triangle'] == 1) | (df['symmetrical_triangle'] == 1)
    triangle_bear = (df['descending_triangle'] == 1)
    flag_bull = (df['bull_flag'] == 1) | (df['wedge_up'] == 1)
    flag_bear = (df['bear_flag'] == 1) | (df['wedge_down'] == 1)
    rectangle_bull = (df['rectangle_break_up'] == 1)
    rectangle_bear = (df['rectangle_break_down'] == 1)

    # 背离
    bullish_divergence = (
        df.get('rsi_bullish_div', 0).astype(bool) |
        df.get('macd_bullish_div', 0).astype(bool) |
        df.get('obv_bullish_div', 0).astype(bool)
    )
    bearish_divergence = (
        df.get('rsi_bearish_div', 0).astype(bool) |
        df.get('macd_bearish_div', 0).astype(bool) |
        df.get('obv_bearish_div', 0).astype(bool)
    )

    # 跳空
    gap_type = df.get('gap_type', 'none')
    breakout_continuation_bull = gap_type.str.contains('breakaway_up|continuation_up')
    breakout_continuation_bear = gap_type.str.contains('breakaway_down|continuation_down')

    # 趋势线突破
    trend_break_bull = df.get('trendline_break_up', False)
    trend_break_bear = df.get('trendline_break_down', False)

    # 量价加强
    cmf_positive = df.get('cmf', 0) > 0
    volume_osc_positive = df.get('volume_osc', 0) > 0
    close_above_vwap = df['close'] > df.get('vwap', df['close'])

    # 波浪
    wave_3 = df['wave_label'] == 'wave_3'
    wave_confirmed = df['wave_confirmed'] == 1

    # === 生成多头信号（逐步叠加）===
    long_signal = (
        in_uptrend &
        rsi_not_extreme &
        volume_spike &
        (
            bullish_reversal |
            bullish_continuation |
            chart_bullish_confirm |
            bullish_divergence |
            breakout_continuation_bull
        )
    )

    long_signal = long_signal | (in_uptrend & (triangle_bull | flag_bull | rectangle_bull) & volume_spike)
    long_signal = long_signal | (in_uptrend & trend_break_bull & volume_spike)
    long_signal = long_signal | (in_uptrend & cmf_positive & volume_osc_positive & close_above_vwap)
    long_signal = long_signal | (in_uptrend & wave_3 & wave_confirmed)

    # === 宽松过滤：只防超买追高（频率高，质量仍OK）===
    rsi_no_chase_high = df['rsi'] < 65  # 宽松防追高
    long_signal = long_signal & rsi_no_chase_high

    # === 空头信号（保守）===
    short_signal = (
        ~in_uptrend &
        rsi_not_extreme &
        volume_spike &
        (
            bearish_reversal |
            bearish_continuation |
            chart_bearish_confirm |
            bearish_divergence |
            breakout_continuation_bear
        )
    )

    short_signal = short_signal | (~in_uptrend & (triangle_bear | flag_bear | rectangle_bear) & volume_spike)
    short_signal = short_signal | (~in_uptrend & trend_break_bear & volume_spike)

    # === 赋值（多头优先）===
    df.loc[long_signal, 'signal'] = 1
    df.loc[short_signal & ~long_signal, 'signal'] = -1

    return df