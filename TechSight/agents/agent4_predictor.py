import os
import sys
import pandas as pd
import numpy as np

# Add data_engine to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data_engine'))
from data_fetcher import DataFetcher

class Agent4Predictor:
    def __init__(self):
        self.fetcher = DataFetcher()
        self.cached_nifty_context = None

    def predict_hold_days(self, atr14: float, target_price: float, current_price: float) -> str:
        """
        Mathematically projects the expected number of trading days to hit the target.
        """
        if atr14 <= 0 or current_price >= target_price:
            return "1-3 days"
            
        distance_to_target = target_price - current_price
        
        # We assume a stock moves roughly 0.4 ATR directionally per day on average in a trend
        directional_velocity_per_day = atr14 * 0.4
        
        expected_days_raw = distance_to_target / directional_velocity_per_day
        expected_days = int(round(expected_days_raw))
        
        # Bound the prediction
        expected_days = max(2, min(45, expected_days))
        
        return f"{expected_days}-{expected_days+3} days"

    def predict_market_regime(self) -> str:
        """
        Fetches the NIFTY 50 index (^NSEI) and predicts the short-term market regime.
        Caches the result to avoid fetching it for every single stock in a sweep.
        """
        if self.cached_nifty_context:
            return self.cached_nifty_context
            
        nifty_data = self.fetcher.fetch_historical_data("^NSEI", period="6mo")
        df_nifty = nifty_data["daily"]
        
        if df_nifty.empty:
            self.cached_nifty_context = "Neutral (Index Data Unavailable)"
            return self.cached_nifty_context
            
        close = df_nifty['Close']
        sma50 = close.rolling(window=50).mean().iloc[-1]
        ema21 = close.ewm(span=21, adjust=False).mean().iloc[-1]
        current_close = close.iloc[-1]
        
        context = ""
        if current_close > ema21 and ema21 > sma50:
            context = "Bullish Alignment: Broad market supporting long setups."
        elif current_close < sma50:
            context = "Risk-Off Regime: Nifty below 50-SMA. Expect higher failure rates."
        elif current_close > sma50 and current_close < ema21:
            context = "Choppy/Sideways: Short term pullback in a broader uptrend."
        else:
            context = "Neutral/Mixed Market"
            
        self.cached_nifty_context = context
        return context

    def predict_risks(self, breakdown: dict) -> str:
        """
        Synthesizes specific risks based on the internal conflict between the 7 engine scores.
        """
        risks = []
        
        if breakdown.get("MTF", 100) < 40:
            risks.append("Daily momentum faces stiff resistance from a bearish Weekly trend.")
            
        if breakdown.get("Volume", 100) > 70 and breakdown.get("Pattern", 100) < 40:
            risks.append("High volume anomaly but lacks a tight structural base; susceptible to sudden pullbacks.")
            
        if breakdown.get("Volatility", 100) < 30:
            risks.append("High current volatility (wide bands/high ATR). Stop loss probability is elevated.")
            
        if breakdown.get("Momentum", 100) < 40:
            risks.append("Momentum indicators (RSI/MACD) are lagging the price action.")
            
        if not risks:
            return "No severe internal engine conflicts detected."
            
        return " | ".join(risks)

if __name__ == "__main__":
    predictor = Agent4Predictor()
    print("Hold Days:", predictor.predict_hold_days(15.0, 1050, 1000))
    print("Regime:", predictor.predict_market_regime())
    print("Risks:", predictor.predict_risks({"MTF": 30, "Volume": 80, "Pattern": 20}))
