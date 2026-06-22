import pandas as pd

class RSEngine:
    def __init__(self):
        pass
        
    def evaluate(self, df: pd.DataFrame) -> int:
        # In a fully fleshed out system, we would pass NIFTY 50 df here
        # For this implementation, we will use a pseudo-RS measuring 
        # the stock's absolute 20-day return against a baseline 2% expected return.
        if df.empty or len(df) < 20:
            return 0
            
        close = df['Close']
        current = close.iloc[-1]
        past_20 = close.iloc[-20]
        
        pct_change = ((current - past_20) / past_20) * 100
        
        score = 0
        if pct_change > 10:
            score = 100
        elif pct_change > 5:
            score = 80
        elif pct_change > 2:
            score = 50
        elif pct_change > 0:
            score = 30
            
        return score
