import requests
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup
import time
from db_handler import get_connection

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.nseindia.com/',
    'Connection': 'keep-alive'
}

def fetch_fii_dii_data():
    """
    Fetches daily provisional FII/DII net activity from NSE.
    """
    url = "https://www.nseindia.com/api/fiidiiTradeReact"
    
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        time.sleep(1)
        resp = session.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        data = resp.json()
        
        # Parse data
        parsed_data = []
        for item in data:
            if 'category' in item and 'buyValue' in item:
                parsed_data.append({
                    'date': item.get('date'),
                    'category': item.get('category'),
                    'buy_value': item.get('buyValue'),
                    'sell_value': item.get('sellValue'),
                    'net_value': item.get('netValue')
                })
                
        if not parsed_data:
            print("Warning: No FII/DII data parsed.")
            return None
            
        df = pd.DataFrame(parsed_data)
        df['fetch_date'] = datetime.now().date()
        
        # Save to DB
        conn = get_connection()
        df.to_sql("fii_dii_daily", conn, if_exists="append", index=False)
        conn.close()
        
        print(f"Successfully fetched FII/DII data for {df.iloc[0]['date']}.")
        return df
        
    except Exception as e:
        print(f"Error fetching FII/DII data: {e}")
        return None

def fetch_bulk_deals():
    """
    Fetches daily bulk deals from NSE.
    """
    url = "https://www.nseindia.com/api/snapshot-capital-market-bulk-deals"
    
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        time.sleep(1)
        resp = session.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        data = resp.json().get('data', [])
        
        if not data:
            print("Warning: No bulk deals data parsed.")
            return None
            
        df = pd.DataFrame(data)
        df['fetch_date'] = datetime.now().date()
        
        # Standardize columns
        df = df.rename(columns={
            'symbol': 'Symbol',
            'clientName': 'Client_Name',
            'buyOrSell': 'Action',
            'quantity': 'Quantity',
            'tradePrice': 'Price',
            'remarks': 'Remarks'
        })
        
        # Save to DB
        conn = get_connection()
        df.to_sql("bulk_deals", conn, if_exists="append", index=False)
        conn.close()
        
        print(f"Successfully fetched {len(df)} bulk deals.")
        return df
        
    except Exception as e:
        print(f"Error fetching bulk deals: {e}")
        return None

if __name__ == "__main__":
    print("Fetching FII/DII...")
    fii = fetch_fii_dii_data()
    time.sleep(2)
    print("Fetching Bulk Deals...")
    bulk = fetch_bulk_deals()
