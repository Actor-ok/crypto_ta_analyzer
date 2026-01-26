# 目标：Streamlit网页版仪表盘（类似GUI，但更轻量），支持API配置、实时信号显示、持仓查询。

# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import ccxt
import time
from utils.config_loader import load_config
from core.dataframe_enhancer import enhance_dataframe
from live.trader_okx import OKXTrader  # <--- 路径（live 同级）

st.set_page_config(page_title="Crypto TA Analyzer 模拟交易仪表盘", layout="wide")
st.title("Crypto TA Analyzer 实时模拟交易（OKX Demo）")

# 侧边栏：API 配置 + 参数调整
st.sidebar.header("OKX API 配置（Demo 模拟盘）")
api_key = st.sidebar.text_input("API Key", type="password")
secret = st.sidebar.text_input("Secret", type="password")
passphrase = st.sidebar.text_input("Passphrase", type="password")
use_demo = st.sidebar.checkbox("Demo 模拟盘模式", value=True)

st.sidebar.header("策略参数（实时调整）")
config_name = st.sidebar.selectbox("配置档", ['default.yaml', 'aggressive.yaml'])
risk_pct = st.sidebar.slider("单笔风险 %", 1.0, 5.0, 3.0)
atr_mult = st.sidebar.slider("ATR止损倍数", 1.0, 5.0, 3.5)
rsi_ob = st.sidebar.slider("RSI 超买阈值", 70, 85, 80)
timeframe = st.sidebar.selectbox("信号周期", ['1h', '4h', '1d'], index=1)

symbol = 'BTC/USDT:USDT'  # 永续合约

if api_key and secret and passphrase:
    trader = OKXTrader(api_key, secret, passphrase, use_demo=use_demo)
    st.success("API 连接成功！Demo 模式虚拟交易")

    # 动态config
    config = load_config(config_name)
    config['risk']['max_risk_per_trade'] = risk_pct / 100
    config['risk']['stop_loss_atr_multiplier'] = atr_mult
    config['indicators']['rsi']['overbought'] = rsi_ob

    # 实时数据函数
    @st.cache_data(ttl=60)  # 60秒缓存
    def get_enhanced_data():
        exchange = ccxt.okx({'enableRateLimit': True})
        if use_demo:
            exchange.set_sandbox_mode(True)
        raw = exchange.fetch_ohlcv(symbol, timeframe, limit=500)
        df = pd.DataFrame(raw, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        df.set_index('ts', inplace=True)
        df.columns = ['open', 'high', 'low', 'close', 'volume']
        return enhance_dataframe(df, config)

    df_enhanced = get_enhanced_data()

    # 主面板
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(f"实时K线图 ({timeframe}周期)")

        fig = go.Figure(data=[go.Candlestick(x=df_enhanced.index,
                        open=df_enhanced['open'], high=df_enhanced['high'],
                        low=df_enhanced['low'], close=df_enhanced['close'], name='K线')])
        fig.add_scatter(x=df_enhanced.index, y=df_enhanced['ema_very_long'], name='EMA200', line=dict(color='orange'))
        fig.add_scatter(x=df_enhanced.index, y=df_enhanced['vwap'], name='VWAP', line=dict(color='purple', dash='dot'))

        # 信号箭头
        buy_signals = df_enhanced[df_enhanced['signal'] == 1]
        sell_signals = df_enhanced[df_enhanced['signal'] == -1]
        fig.add_scatter(x=buy_signals.index, y=buy_signals['low'] * 0.99, mode='markers',
                        marker=dict(symbol='triangle-up', size=20, color='green'), name='买入信号')
        fig.add_scatter(x=sell_signals.index, y=sell_signals['high'] * 1.01, mode='markers',
                        marker=dict(symbol='triangle-down', size=20, color='red'), name='卖出信号')

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("当前状态")
        latest = df_enhanced.iloc[-1]
        st.write(f"最新价格: **{latest['close']:.1f}**")
        st.write(f"当前信号: **{latest['signal']}** (1=买, -1=卖, 0=持仓)")
        st.write(f"时间: {df_enhanced.index[-1]}")

        if st.button("刷新持仓/余额"):
            with st.spinner("查询中..."):
                balance = trader.get_balance()
                st.write("### 余额")
                st.json(balance['total'])
                positions = trader.get_positions(symbol)
                st.write("### 持仓")
                st.json(positions)

    st.sidebar.info("参数调整后刷新页面生效 · 信号周期实时切换")

else:
    st.warning("请填写 OKX API 配置（Demo key 安全）开始监控")

st.caption("虚拟模拟交易 · 零风险测试 · 基于 aggressive 配置")