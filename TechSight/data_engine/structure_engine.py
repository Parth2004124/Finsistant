import pandas as pd
import numpy as np

class StructureEngine:
    def __init__(self):
        pass
        
    def evaluate(self, df: pd.DataFrame) -> int:
        if df.empty or len(df) < 200:
            return 0
            
        close = df['Close']
        
        # Calculate MAs
        ema21 = close.ewm(span=21, adjust=False).mean()
        sma50 = close.rolling(window=50).mean()
        sma200 = close.rolling(window=200).mean()
        
        current_close = close.iloc[-1]
        current_ema21 = ema21.iloc[-1]
        current_sma50 = sma50.iloc[-1]
        current_sma200 = sma200.iloc[-1]
        
        score = 0
        
        # 1. Above 200 SMA (Long term trend)
        if current_close > current_sma200:
            score += 30
        
        # 2. Above 50 SMA (Medium term)
        if current_close > current_sma50:
            score += 25
            
        # 3. Above 21 EMA (Short term momentum)
        if current_close > current_ema21:
            score += 20
            
        # 4. Moving Average Alignment (21 > 50 > 200)
        if current_ema21 > current_sma50 > current_sma200:
            score += 25
            
        return score
