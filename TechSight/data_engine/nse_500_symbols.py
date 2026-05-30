import pandas as pd
import requests
import io
import time

def get_nse_500_symbols():
    """
    Fetches the NIFTY 500 symbol list from NSE India.
    Returns a list of symbols formatted for yfinance (e.g., 'RELIANCE.NS').
    """
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.nseindia.com/',
        'Connection': 'keep-alive'
    }

    try:
        # NSE requires a session to be established first sometimes
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        time.sleep(1)
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        df = pd.read_csv(io.StringIO(response.text))
        symbols = df['Symbol'].tolist()
        
        # Append .NS for yfinance
        yf_symbols = [f"{sym}.NS" for sym in symbols]
        print(f"Successfully fetched {len(yf_symbols)} symbols from NSE.")
        return yf_symbols
    except Exception as e:
        print(f"Failed to fetch from NSE: {e}. Using fallback symbol list.")
        # Minimal fallback for testing if NSE blocks the request
        fallback = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS"]
        return fallback

if __name__ == "__main__":
    symbols = get_nse_500_symbols()
    print(f"Sample: {symbols[:5]}")
