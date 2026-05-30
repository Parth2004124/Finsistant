import sqlite3
import pandas as pd
import os
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(__file__), "techsight_data.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def save_ohlcv(symbol: str, timeframe: str, df: pd.DataFrame):
    """
    Saves OHLCV dataframe to SQLite. 
    Tables are named like 'RELIANCE_NS_1d'.
    """
    if df is None or df.empty:
        return
    
    clean_symbol = symbol.replace(".", "_")
    table_name = f"{clean_symbol}_{timeframe}"
    
    conn = get_connection()
    # Reset index so Datetime becomes a column
    df_to_save = df.reset_index()
    # Convert timezone-aware datetimes to timezone-naive before saving to SQLite
    if 'Datetime' in df_to_save.columns:
        if pd.api.types.is_datetime64tz_dtype(df_to_save['Datetime']):
            df_to_save['Datetime'] = df_to_save['Datetime'].dt.tz_localize(None)
    elif 'Date' in df_to_save.columns:
         if pd.api.types.is_datetime64tz_dtype(df_to_save['Date']):
            df_to_save['Date'] = df_to_save['Date'].dt.tz_localize(None)
            
    df_to_save.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()

def load_ohlcv(symbol: str, timeframe: str) -> pd.DataFrame:
    """
    Loads OHLCV from SQLite. Returns empty DataFrame if not found.
    """
    clean_symbol = symbol.replace(".", "_")
    table_name = f"{clean_symbol}_{timeframe}"
    
    conn = get_connection()
    try:
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql_query(query, conn)
        # Re-set index
        if 'Datetime' in df.columns:
            df['Datetime'] = pd.to_datetime(df['Datetime'])
            df.set_index('Datetime', inplace=True)
        elif 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
        conn.close()
        return df
    except sqlite3.OperationalError:
        # Table doesn't exist
        conn.close()
        return pd.DataFrame()

def is_cache_stale(symbol: str, timeframe: str) -> bool:
    """
    Checks if the cached data is stale.
    A simple check: if the last date in the cache is not today (or within the last 1-2 days).
    For a production system, this could check the exact last market close.
    """
    df = load_ohlcv(symbol, timeframe)
    if df.empty:
        return True
    
    last_date = df.index[-1]
    if isinstance(last_date, str):
        last_date = pd.to_datetime(last_date)
        
    days_diff = (datetime.now().date() - last_date.date()).days
    
    # If the last candle is older than 2 days, consider it stale (handles weekends loosely)
    # A stricter check can be implemented later.
    return days_diff > 2
