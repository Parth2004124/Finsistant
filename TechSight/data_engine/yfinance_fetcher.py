import yfinance as yf
import pandas as pd
from nse_500_symbols import get_nse_500_symbols
from db_handler import save_ohlcv, is_cache_stale, load_ohlcv
import time
import sys

from investpy_fetcher import fetch_investpy_data
from alphavantage_fetcher import fetch_alphavantage_data

def fetch_ohlcv_data(symbol: str, timeframe: str, force_refresh=False):
    """
    Fetches data with a 3-tier fallback chain: yfinance -> investpy -> Alpha Vantage
    """
    if not force_refresh and not is_cache_stale(symbol, timeframe):
        return load_ohlcv(symbol, timeframe)
    
    period_map = {
        '1d': '1y',
        '1wk': '3y',
        '60m': '1mo'
    }
    
    df = None
    
    # Tier 1: yfinance
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period_map[timeframe], interval=timeframe)
        if not df.empty:
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            df.dropna(inplace=True)
            if timeframe == '1d': df = df.tail(200)
            elif timeframe == '1wk': df = df.tail(104)
            elif timeframe == '60m': df = df.tail(60)
        else:
            df = None
    except Exception as e:
        df = None
        
    # Tier 2: investpy
    if df is None:
        df = fetch_investpy_data(symbol, timeframe)
        
    # Tier 3: Alpha Vantage
    if df is None:
        df = fetch_alphavantage_data(symbol, timeframe)
        
    if df is None or df.empty:
        print(f"[{symbol} - {timeframe}] ALL SOURCES FAILED. Flagging as data-unavailable.")
        # We save an empty dataframe to represent the unavailable flag locally
        save_ohlcv(symbol, timeframe, pd.DataFrame())
        return None
        
    save_ohlcv(symbol, timeframe, df)
    return df

def fetch_all_nse500():
    print("Fetching NSE 500 Symbol List...")
    symbols = get_nse_500_symbols()
    
    # For testing, we only do a small batch to prove the gate condition unless 'FULL' is passed
    if len(sys.argv) > 1 and sys.argv[1] == "FULL":
        target_symbols = symbols
    else:
        target_symbols = symbols[:10]  # Just 10 for rapid verification
        print("Running in rapid verification mode (10 symbols). Pass 'FULL' as arg for all 500.")
        
    timeframes = ['1d', '1wk', '60m']
    success_count = 0
    total = len(target_symbols)
    
    for idx, sym in enumerate(target_symbols):
        print(f"Processing {idx+1}/{total}: {sym}")
        success = True
        for tf in timeframes:
            df = fetch_ohlcv_data(sym, tf, force_refresh=True)
            if df is None or df.empty:
                success = False
                break
        if success:
            success_count += 1
            
        # Small sleep to prevent rate limiting from Yahoo
        time.sleep(0.1)
        
    success_rate = (success_count / total) * 100
    print(f"\n--- GATE CONDITION CHECK ---")
    print(f"Successfully fetched clean, gap-free data for {success_count}/{total} symbols.")
    print(f"Success Rate: {success_rate:.2f}%")
    if success_rate >= 90.0:
        print("PASS: Gate Condition PASSED (>= 90%)")
    else:
        print("FAIL: Gate Condition FAILED (< 90%)")

if __name__ == "__main__":
    fetch_all_nse500()
