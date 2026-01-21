import pandas as pd
from ta.volume import OnBalanceVolumeIndicator, ChaikinMoneyFlowIndicator, VolumeWeightedAveragePrice

def add_volume_indicators(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    df = df.copy()
    
    # 原有 OBV
    df['obv'] = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume']).on_balance_volume()
    
    # 新增 CMF (Chaikin Money Flow)
    cmf_cfg = config['indicators'].get('cmf', {'period': 20})
    df['cmf'] = ChaikinMoneyFlowIndicator(
        high=df['high'], low=df['low'], close=df['close'], volume=df['volume'],
        window=cmf_cfg['period']
    ).chaikin_money_flow()
    
    # 新增 Volume Oscillator (短-长均量百分比)
    vo_cfg = config['indicators'].get('volume_osc', {'short': 5, 'long': 10})
    short_ma = df['volume'].rolling(vo_cfg['short']).mean()
    long_ma = df['volume'].rolling(vo_cfg['long']).mean()
    df['volume_osc'] = (short_ma - long_ma) / long_ma * 100
    
    # 新增 VWAP (成交量加权均价)
    df['vwap'] = VolumeWeightedAveragePrice(
        high=df['high'], low=df['low'], close=df['close'], volume=df['volume']
    ).volume_weighted_average_price()
    
    return df