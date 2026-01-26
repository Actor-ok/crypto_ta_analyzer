# 总体目标：完整回测引擎（支持ATR止损、风险百分比仓位、RR止盈）。
# 输入：增强DataFrame + 初始资金 + config.risk
# 输出：绩效字典（总收益、年化、最大回撤、胜率等） + 带equity曲线的DataFrame + 绘图
# 关键代码块：逐根K线遍历信号 → 计算仓位大小（风险%）→ ATR止损/TP → 更新equity。
# 关联：backtest_test.py调用验证策略绩效。

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def backtest_strategy(df: pd.DataFrame, initial_capital: float = 100000.0, config: dict = None) -> tuple:
    """
    增强版回测：逐笔交易 + ATR止损 + RR止盈 + 固定风险仓位
    只做多（现货）
    """
    if config is None:
        config = {}
    
    df = df.copy()
    df = df.reset_index(drop=False)  # 保留timestamp作为列
    
    risk_cfg = config.get('risk', {})
    risk_pct = risk_cfg.get('max_risk_per_trade', 0.02)
    atr_mult = risk_cfg.get('stop_loss_atr_multiplier', 2.0)
    tp_rr = risk_cfg.get('take_profit_rr', 2.0)
    use_atr = risk_cfg.get('use_atr_stop', True)
    
    equity = initial_capital
    position = 0.0  # 持仓数量（币数）
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    
    trades = []  # 记录完整交易
    
    df['equity'] = initial_capital
    df['position_value'] = 0.0
    df['trade_pnl'] = 0.0
    
    for i in range(1, len(df)):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        close = row['close']
        
        pnl_today = 0.0
        
        # 检查持仓是否触及止损/止盈
        if position > 0:
            # 止损
            if close <= stop_loss:
                exit_price = stop_loss  # 简化：假设触及即成交
                pnl = position * (exit_price - entry_price)
                equity += pnl
                trades.append({
                    'exit_type': 'stop_loss',
                    'pnl': pnl,
                    'return': (exit_price / entry_price - 1)
                })
                position = 0.0
            # 止盈
            elif close >= take_profit:
                exit_price = take_profit
                pnl = position * (exit_price - entry_price)
                equity += pnl
                trades.append({
                    'exit_type': 'take_profit',
                    'pnl': pnl,
                    'return': (exit_price / entry_price - 1)
                })
                position = 0.0
        
        # 新开仓（signal=1 且无持仓）
        if position == 0 and row['signal'] == 1:
            entry_price = close
            atr = row['atr'] if not pd.isna(row['atr']) else (close * 0.02)  # 备用2%
            
            stop_loss = entry_price - atr_mult * atr
            risk_per_coin = entry_price - stop_loss
            if risk_per_coin <= 0:
                continue  # 避免除零
            
            take_profit = entry_price + tp_rr * risk_per_coin
            
            risk_amount = equity * risk_pct
            position = risk_amount / risk_per_coin  # 买多少币
            
            trades.append({
                'entry': entry_price,
                'sl': stop_loss,
                'tp': take_profit,
                'position': position
            })
        
        # 主动平仓信号（signal=-1）
        elif position > 0 and row['signal'] == -1:
            exit_price = close
            pnl = position * (exit_price - entry_price)
            equity += pnl
            trades.append({
                'exit_type': 'signal_close',
                'pnl': pnl,
                'return': (exit_price / entry_price - 1)
            })
            position = 0.0
        
        # 更新股权
        df.loc[i, 'equity'] = equity
        df.loc[i, 'position_value'] = position * close
    
    # === 绩效指标 ===
    total_return = (equity - initial_capital) / initial_capital
    days = (df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).days + 1
    annual_return = (1 + total_return) ** (365 / days) - 1 if days > 0 else 0
    
    drawdown = df['equity'] / df['equity'].cummax() - 1
    max_drawdown = drawdown.min()
    
    completed_trades = [t for t in trades if 'pnl' in t]
    num_trades = len(completed_trades)
    win_rate = np.mean([t['pnl'] > 0 for t in completed_trades]) if num_trades > 0 else 0
    avg_return = np.mean([t['return'] for t in completed_trades]) if num_trades > 0 else 0
    profit_factor = np.sum([t['pnl'] for t in completed_trades if t['pnl'] > 0]) / \
                    abs(np.sum([t['pnl'] for t in completed_trades if t['pnl'] < 0])) if num_trades > 0 else 0
    
    performance = {
        'total_return': total_return,
        'annual_return': annual_return,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'avg_r_multiple': avg_return / risk_pct if risk_pct > 0 else 0,
        'profit_factor': profit_factor,
        'num_trades': num_trades,
        'final_equity': equity
    }
    
    # 股权曲线
    plt.figure(figsize=(16, 8))
    df.set_index('timestamp')['equity'].plot(title='Backtest Equity Curve (ATR SL + RR TP)')
    plt.ylabel('Equity (USDT)')
    plt.show()
    
    return performance, df.set_index('timestamp')

# 注意：backtest_test.py 中调用时传 config
# performance, df_backtest = backtest_strategy(df_enhanced, initial_capital=100000, config=config)