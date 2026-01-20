from ta.momentum import RSIIndicator, StochasticOscillator
import pandas as pd

def add_momentum_indicators(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    rsi_cfg = config['indicators']['rsi']
    df['rsi'] = RSIIndicator(df['close'], window=rsi_cfg['period']).rsi()
    
    # MACD 移到 trend.py 了（见下面）
    
    stoch_cfg = config['indicators']['stochastic']
    stoch = StochasticOscillator(df['high'], df['low'], df['close'], 
                                 window=stoch_cfg['period'], 
                                 smooth_window=stoch_cfg['smooth_k'])
    df['stoch_k'] = stoch.stoch()
    df['stoch_d'] = stoch.stoch_signal()
    
    return df