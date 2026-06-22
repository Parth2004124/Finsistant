import pandas as pd

class VolumeEngine:
    def __init__(self):
        pass
        
    def evaluate(self, df: pd.DataFrame) -> int:
        if df.empty or len(df) < 20:
            return 0
            
        vol = df['Volume']
        close = df['Close']
        open_price = df['Open']
        
        vol_sma20 = vol.rolling(window=20).mean()
        
        current_vol = vol.iloc[-1]
        avg_vol = vol_sma20.iloc[-1]
        
        score = 50 # Baseline
        
        # Check if today is up day and volume is high
        if close.iloc[-1] > open_price.iloc[-1]:
            if current_vol > avg_vol * 2.0:
                score += 40
            elif current_vol > avg_vol * 1.2:
                score += 20
        else:
            # Down day on high volume is bad
            if current_vol > avg_vol * 1.5:
                score -= 30
                
        # Ensure bounds
        return max(0, min(100, score))
