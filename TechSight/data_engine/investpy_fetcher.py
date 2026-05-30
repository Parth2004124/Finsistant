import pandas as pd
import investpy
from db_handler import save_ohlcv

def fetch_investpy_data(symbol: str, timeframe: str):
    """
    Fallback fetcher using investpy.
    timeframe: '1d', '1wk', '60m'
    Note: investpy uses different symbol conventions, usually the raw symbol without .NS
    """
    clean_sym = symbol.replace('.NS', '').replace('.BO', '')
    print(f"[{symbol} - {timeframe}] Fallback 1: Trying investpy ({clean_sym})...")
    
    try:
        # Investpy doesn't naturally support minute/hourly data easily via get_stock_historical_data
        # We will attempt daily data fallback. If timeframe is not '1d', we return None.
        if timeframe != '1d':
            print(f"[{symbol}] investpy fallback only supports Daily data currently.")
            return None
            
        import datetime
        end_date = datetime.datetime.now().strftime("%d/%m/%Y")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime("%d/%m/%Y")
        
        df = investpy.get_stock_historical_data(stock=clean_sym,
                                                country='india',
                                                from_date=start_date,
                                                to_date=end_date)
                                                
        if df is None or df.empty:
            return None
            
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        df.dropna(inplace=True)
        df = df.tail(200)
        
        # We don't save to DB here, the main engine handles saving to DB on success
        return df
    except Exception as e:
        print(f"[{symbol}] investpy fallback failed: {e}")
        return None
