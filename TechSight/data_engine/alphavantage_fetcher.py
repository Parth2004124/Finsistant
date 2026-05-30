import pandas as pd
import requests

# Hardcoded free tier key for fallback
ALPHA_VANTAGE_KEY = "demo" # Replace with real key if needed

def fetch_alphavantage_data(symbol: str, timeframe: str):
    """
    Fallback fetcher using Alpha Vantage.
    timeframe: '1d', '1wk', '60m'
    """
    clean_sym = symbol.replace('.NS', '.BSE') # AlphaVantage uses BSE heavily for India, or raw symbol
    print(f"[{symbol} - {timeframe}] Fallback 2: Trying Alpha Vantage ({clean_sym})...")
    
    function_map = {
        '1d': 'TIME_SERIES_DAILY',
        '1wk': 'TIME_SERIES_WEEKLY',
        '60m': 'TIME_SERIES_INTRADAY'
    }
    
    if timeframe not in function_map:
        return None
        
    func = function_map[timeframe]
    url = f"https://www.alphavantage.co/query?function={func}&symbol={clean_sym}&apikey={ALPHA_VANTAGE_KEY}"
    
    if timeframe == '60m':
        url += "&interval=60min"
        
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        # Alpha vantage keys depend on the function
        key_map = {
            '1d': 'Time Series (Daily)',
            '1wk': 'Weekly Time Series',
            '60m': 'Time Series (60min)'
        }
        
        ts_key = key_map[timeframe]
        if ts_key not in data:
            print(f"[{symbol}] AlphaVantage returned error or limit reached: {data.get('Note', data.get('Information', 'Unknown Error'))}")
            return None
            
        time_series = data[ts_key]
        df = pd.DataFrame.from_dict(time_series, orient='index')
        df.rename(columns={
            '1. open': 'Open',
            '2. high': 'High',
            '3. low': 'Low',
            '4. close': 'Close',
            '5. volume': 'Volume'
        }, inplace=True)
        
        df = df.astype(float)
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        
        if timeframe == '1d':
            df = df.tail(200)
        elif timeframe == '1wk':
            df = df.tail(104)
        elif timeframe == '60m':
            df = df.tail(60)
            
        return df
    except Exception as e:
        print(f"[{symbol}] AlphaVantage fallback failed: {e}")
        return None
