# 总体目标：OKX交易接口封装（支持Demo模拟盘，现货/永续合约）。
# 功能：下单、查余额、查持仓、拉最新K线、平仓等。
# 关键代码块：ccxt.okx初始化（带demo切换）+ 各种wrapper方法。
# 关联：实时交易脚本和GUI使用。

# core/live/trader_okx.py
import ccxt
import time
import pandas as pd
from typing import Dict

class OKXTrader:
    """
    OKX 交易接口（支持 Demo 模拟盘）
    - Demo模式：use_demo=True（虚拟资金，真实行情）
    - 合约示例：BTC/USDT:USDT (永续)
    - 现货示例：BTC/USDT
    """
    def __init__(self, api_key: str, secret: str, passphrase: str, use_demo: bool = True):
        self.exchange = ccxt.okx({
            'apiKey': api_key,
            'secret': secret,
            'password': passphrase,  # OKX 必需
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',  # 默认永续合约（改 'spot' 为现货）
            },
        })
        
        if use_demo:
            self.exchange.set_sandbox_mode(True)  # <--- 关键：切换到 Demo 环境
            print("OKX Trader 已初始化：Demo 模拟盘模式（虚拟资金，零风险）")
        else:
            print("OKX Trader 已初始化：实盘模式（小心使用！）")

    def set_leverage(self, symbol: str, leverage: int = 10):
        """设置杠杆（永续合约）"""
    try:
        self.exchange.set_leverage(leverage, symbol)
        print(f"设置 {symbol} 杠杆 {leverage}x 成功")
    except Exception as e:
        print(f"杠杆设置失败: {e}")

    def get_balance(self) -> Dict:
        """获取余额（总/可用）"""
        balance = self.exchange.fetch_balance()
        print("当前余额:", balance['total'])
        return balance

    def get_positions(self, symbol: str = None):
        """获取持仓"""
        positions = self.exchange.fetch_positions([symbol] if symbol else None)
        for pos in positions:
            print(f"持仓: {pos['symbol']} {pos['side']} {pos['contracts']} 盈亏: {pos['unrealizedPnl']}")
        return positions

    def place_order(self, symbol: str, side: str, amount: float, price: float = None, order_type: str = 'limit'):
        """
        下单
        - side: 'buy' / 'sell'
        - amount: 数量（合约张数或币数）
        - order_type: 'limit'（限价）或 'market'（市价）
        """
        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
                params={'tdMode': 'cross'}  # 合约全仓模式（可改 'isolated' 孤立）
            )
            print(f"下单成功: {side} {amount} {symbol} @ {price or '市价'} ID: {order['id']}")
            return order
        except Exception as e:
            print(f"下单失败: {e}")
            return None

    def close_position(self, symbol: str):
        """平仓（市价全平）"""
        positions = self.exchange.fetch_positions([symbol])
        for pos in positions:
            if float(pos['contracts']) != 0:
                side = 'sell' if pos['side'] == 'long' else 'buy'
                self.place_order(symbol, side, abs(float(pos['contracts'])), order_type='market')

    def fetch_latest_ohlcv(self, symbol: str, timeframe: str = '4h', limit: int = 1000) -> pd.DataFrame:
        """拉取最新K线"""
        raw = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(raw, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df