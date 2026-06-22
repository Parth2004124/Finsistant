import pandas as pd
import numpy as np

class VolatilityEngine:
    def __init__(self):
        pass
        
    def evaluate(self, df: pd.DataFrame) -> int:
        if df.empty or len(df) < 20:
            return 0
            
        high = df['High']
        low = df['Low']
        close = df['Close']
        
        # Calculate True Range
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        
        atr14 = tr.rolling(window=14).mean()
        
        # Bollinger Bands Width (proxy for volatility squeeze)
        sma20 = close.rolling(window=20).mean()
        std20 = close.rolling(window=20).std()
        upper = sma20 + (std20 * 2)
        lower = sma20 - (std20 * 2)
        bb_width = (upper - lower) / sma20
        
        current_bb_width = bb_width.iloc[-1]
        current_atr_pct = (atr14.iloc[-1] / close.iloc[-1]) * 100
        
        score = 0
        
        # Volatility contraction (VCP) is bullish for setups
        if current_bb_width < 0.05: # Very tight bands
            score += 60
        elif current_bb_width < 0.10:
            score += 40
            
        if current_atr_pct < 2.0: # Low daily volatility
            score += 40
        elif current_atr_pct < 4.0:
            score += 20
            
        return score
