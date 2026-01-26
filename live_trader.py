# live_trader.py
import time
import pandas as pd
from utils.config_loader import load_config
from core.dataframe_enhancer import enhance_dataframe
from live.trader_okx import OKXTrader  # <--- 注意路径（live 同级）

# === 配置（填你的 Demo key）===
API_KEY = '65175512-273a-4a64-a677-cae2c5ef8801'
SECRET = '578BBE01036A21D2A25CC56000C20689'
PASSPHRASE = '2002WsL1013./'
USE_DEMO = True

SYMBOL = 'BTC/USDT:USDT'  # 永续合约（现货改 'BTC/USDT'）
TIMEFRAME = '4h'          # 信号周期
ORDER_SIZE = 0.001        # 小单（虚拟扣 ~100 USDT）

config = load_config('aggressive.yaml')  # 激进配置

trader = OKXTrader(API_KEY, SECRET, PASSPHRASE, use_demo=USE_DEMO)

print("实时模拟交易启动（Ctrl+C 停止）\n")

position = 0  # 简单持仓跟踪（0=空，1=多，-1=空）

while True:
    try:
        # 拉最新K线
        df = trader.fetch_latest_ohlcv(SYMBOL, TIMEFRAME, limit=1000)
        
        # 增强 + 信号
        df_enhanced = enhance_dataframe(df, config)
        latest = df_enhanced.iloc[-1]
        signal = latest['signal']
        
        print(f"时间: {df_enhanced.index[-1]} | 价格: {latest['close']:.1f} | 信号: {signal}")
        
        # 简单执行：信号变多/空时下单（避免重复）
        if signal == 1 and position <= 0:
            trader.place_order(SYMBOL, 'buy', ORDER_SIZE, order_type='market')
            position = 1
        elif signal == -1 and position >= 0:
            trader.place_order(SYMBOL, 'sell', ORDER_SIZE, order_type='market')
            position = -1
        
        # 打印持仓/余额
        trader.get_balance()
        trader.get_positions(SYMBOL)
        
        time.sleep(180)  # 3分钟（4h周期够）
        
    except Exception as e:
        print(f"错误: {e}")
        time.sleep(60)