import yfinance as yf
import pandas as pd
import datetime

class DataFetcher:
    def __init__(self):
        pass

    def fetch_historical_data(self, symbol: str, period="1y") -> dict:
        """
        Fetches historical OHLCV data from Yahoo Finance.
        Handles the `.NS` suffix required for Indian stocks.
        Returns a dictionary with daily and weekly dataframes.
        """
        # Ensure it has .NS for Yahoo Finance NSE stocks unless it's an index like ^NSEI
        if symbol.startswith("^"):
            yf_symbol = symbol
        else:
            yf_symbol = symbol if symbol.endswith(".NS") else f"{symbol}.NS"
        
        try:
            ticker = yf.Ticker(yf_symbol)
            df_daily = ticker.history(period=period, timeout=15)
            
            if df_daily.empty:
                print(f"[DataFetcher] Warning: No data found for {yf_symbol}")
                return {"daily": pd.DataFrame(), "weekly": pd.DataFrame()}
                
            # Resample daily data to weekly data
            # Logic: Open is first, High is max, Low is min, Close is last, Volume is sum
            df_weekly = df_daily.resample('W-FRI').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            })
            
            # Drop incomplete weeks or NaN rows
            df_weekly.dropna(inplace=True)
            
            return {
                "daily": df_daily,
                "weekly": df_weekly
            }
        except Exception as e:
            print(f"[DataFetcher] Error fetching data for {yf_symbol}: {e}")
            return {"daily": pd.DataFrame(), "weekly": pd.DataFrame()}

# Quick test logic
if __name__ == "__main__":
    fetcher = DataFetcher()
    data = fetcher.fetch_historical_data("ITC")
    print("Daily tail:\n", data["daily"].tail())
    print("Weekly tail:\n", data["weekly"].tail())
