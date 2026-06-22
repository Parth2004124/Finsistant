import pandas as pd
import numpy as np

class MomentumEngine:
    def __init__(self):
        pass
        
    def _calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def evaluate(self, df: pd.DataFrame) -> int:
        if df.empty or len(df) < 30:
            return 0
            
        close = df['Close']
        rsi = self._calculate_rsi(close)
        current_rsi = rsi.iloc[-1]
        
        # MACD
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        
        current_macd = macd.iloc[-1]
        current_signal = signal.iloc[-1]
        
        score = 0
        
        # RSI between 50 and 70 is ideal bullish momentum
        if 50 <= current_rsi <= 70:
            score += 50
        elif current_rsi > 70:
            score += 30 # Overbought, but still strong
        elif 40 <= current_rsi < 50:
            score += 10
            
        # MACD bullish cross
        if current_macd > current_signal:
            score += 30
        if current_macd > 0:
            score += 20
            
        return score
