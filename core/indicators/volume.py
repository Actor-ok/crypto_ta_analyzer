from ta.volume import OnBalanceVolumeIndicator
import pandas as pd

def add_volume_indicators(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    df['obv'] = OnBalanceVolumeIndicator(df['close'], df['volume']).on_balance_volume()
    return df