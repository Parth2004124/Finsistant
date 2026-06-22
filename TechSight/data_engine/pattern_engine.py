import pandas as pd

class PatternEngine:
    def __init__(self):
        pass
        
    def evaluate(self, df: pd.DataFrame) -> int:
        if df.empty or len(df) < 20:
            return 0
            
        # Very basic check for consolidation / tight bases
        # Look at the max and min over the last 10 days
        close = df['Close']
        recent_10 = close.tail(10)
        
        high_10 = recent_10.max()
        low_10 = recent_10.min()
        
        # Calculate depth of the base
        base_depth_pct = ((high_10 - low_10) / low_10) * 100
        
        score = 0
        # A tight base (< 5% depth) is excellent
        if base_depth_pct < 5.0:
            score = 90
        elif base_depth_pct < 10.0:
            score = 70
        elif base_depth_pct < 15.0:
            score = 40
            
        return score
