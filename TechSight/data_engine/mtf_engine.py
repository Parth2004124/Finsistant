import pandas as pd

class MTFEngine:
    def __init__(self):
        pass
        
    def evaluate(self, df_daily: pd.DataFrame, df_weekly: pd.DataFrame) -> int:
        if df_daily.empty or df_weekly.empty or len(df_weekly) < 20:
            return 0
            
        # Daily trend
        d_close = df_daily['Close']
        d_sma50 = d_close.rolling(window=50).mean().iloc[-1]
        d_trend_up = d_close.iloc[-1] > d_sma50
        
        # Weekly trend
        w_close = df_weekly['Close']
        w_sma20 = w_close.rolling(window=20).mean().iloc[-1]
        w_trend_up = w_close.iloc[-1] > w_sma20
        
        score = 0
        if w_trend_up:
            score += 60 # Weekly trend is king
        if d_trend_up:
            score += 40 # Daily alignment
            
        return score
