# test_trader_okx.py
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
sys.path.insert(0, project_root)

from live.trader_okx import OKXTrader

if __name__ == "__main__":
    API_KEY = '65175512-273a-4a64-a677-cae2c5ef8801'      # <--- 用 Demo key
    SECRET = '578BBE01036A21D2A25CC56000C20689'
    PASSPHRASE = '2002WsL1013./'         # <--- 确认正确
    USE_DEMO = True

    try:
        trader = OKXTrader(API_KEY, SECRET, PASSPHRASE, use_demo=USE_DEMO)
        
        print("\n=== 余额测试 ===")
        balance = trader.get_balance()
        print(balance)
        
    except Exception as e:
        print(f"认证失败详情: {e}")
        print("建议：用 OKX Demo 页面新建专用 Demo API key")