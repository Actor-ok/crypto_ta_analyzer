import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def backtest_strategy(df: pd.DataFrame, initial_capital: float = 100000.0, risk_per_trade: float = 0.02) -> dict:
    """
    向量回测：基于signal列（1买, -1卖）
    假设：现货多头（只做多），固定风险仓位（单笔风险2%）
    """
    df = df.copy()
    df['signal'] = df['signal'].fillna(0)
    
    # 持仓：signal=1开多，signal=-1平仓（这里简化只做多，不做空）
    df['position'] = df['signal'].replace(-1, 0)  # -1视为平仓
    df['position'] = df['position'].fillna(method='ffill')  # 或 df['position'].ffill()
    df['position'] = df['position'].fillna(0)
    
    # 收益计算（下一根收盘价变动）
    df['returns'] = df['close'].pct_change()
    df['strategy_returns'] = df['position'].shift(1) * df['returns']  # 持仓后收益
    
    # 仓位管理：固定风险（假设止损ATR*2，简化用固定2%风险计算仓位大小）
    # 这里简化：全仓做多（risk_per_trade控制最大仓位比例）
    df['strategy_returns'] *= risk_per_trade if risk_per_trade < 1 else 1.0
    
    # 股权曲线
    df['cum_returns'] = (1 + df['strategy_returns']).cumprod()
    df['equity'] = initial_capital * df['cum_returns']
    
    # 绩效指标
    total_return = df['equity'].iloc[-1] / initial_capital - 1
    annual_return = (1 + total_return) ** (365 * 24 * 60 / len(df)) - 1  # 按1m周期年化
    
    drawdown = df['equity'] / df['equity'].cummax() - 1
    max_drawdown = drawdown.min()
    
    trades = df['signal'].abs().sum()  # 交易次数（简化）
    win_rate = (df['strategy_returns'] > 0).sum() / (df['strategy_returns'] != 0).sum() if trades > 0 else 0
    
    performance = {
        'total_return': total_return,
        'annual_return': annual_return,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'trades': trades,
        'final_equity': df['equity'].iloc[-1]
    }
    
    # 画股权曲线
    plt.figure(figsize=(16, 8))
    df['equity'].plot(title='Backtest Equity Curve')
    plt.ylabel('Equity (USDT)')
    plt.show()
    
    return performance, df