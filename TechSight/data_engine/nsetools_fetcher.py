import yfinance as yf
import time

def fetch_live_quote(symbol: str):
    """
    Fetches live quote data using yfinance since NSE India WAF blocks direct API calls.
    Provides LTP, Day High, Day Low. Delivery % is set to 0.0 for live polling and updated via EOD Bhavcopy in Volume Engine.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        
        data = {
            'symbol': symbol,
            'ltp': info.last_price,
            'day_high': info.day_high,
            'day_low': info.day_low,
            'open_interest': 0.0,
            'delivery_percentage': 0.0 # Handled in Volume Engine via EOD Bhavcopy
        }
            
        print(f"[{symbol}] Live Quote: {data['ltp']} | Day High: {data['day_high']} | Day Low: {data['day_low']}")
        return data
        
    except Exception as e:
        print(f"[{symbol}] Error fetching live quote from yfinance: {e}")
        return None

if __name__ == "__main__":
    test_symbols = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ZOMATO.NS"]
    for sym in test_symbols:
        fetch_live_quote(sym)
        time.sleep(0.5)
