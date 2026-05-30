import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from db_handler import get_connection
import os

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept-Language': 'en-US,en;q=0.9'
}

def fetch_chartink_watchlist():
    """
    Fetches the pre-filtered watchlist from Chartink.
    Condition: NSE 500 -> Above 200 DMA, Volume > 1.2x avg, RSI 40-65.
    """
    url = "https://chartink.com/screener/process"
    
    # We first need to get the CSRF token from the main page
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        r = session.get("https://chartink.com/screener")
        soup = BeautifulSoup(r.text, 'html.parser')
        csrf_token = soup.select_one('meta[name="csrf-token"]')['content']
        
        # This is a sample condition string simulating the blueprint requirement
        # In production, you would create the scan on Chartink and use its specific condition payload
        condition = {
            "scan_clause": "( {33489} ( latest close > latest sma ( close,200 ) and latest volume > 1.2 * latest sma ( volume,20 ) and latest rsi ( 14 ) >= 40 and latest rsi ( 14 ) <= 65 ) )"
        }
        
        session.headers.update({'X-CSRF-TOKEN': csrf_token})
        resp = session.post(url, data=condition, timeout=15)
        resp.raise_for_status()
        
        data = resp.json()
        df = pd.DataFrame(data['data'])
        
        if df.empty:
            print("Chartink returned 0 symbols. Gate Condition failed.")
            return None
            
        # Standardize for yfinance (append .NS)
        df['nsecode'] = df['nsecode'] + ".NS"
        
        # Save to CSV
        output_path = os.path.join(os.path.dirname(__file__), "watchlist.csv")
        df.to_csv(output_path, index=False)
        print(f"Chartink Watchlist saved to {output_path} with {len(df)} symbols.")
        return df
        
    except Exception as e:
        print(f"Chartink Scrape Error: {e}")
        return None

def fetch_screener_fundamentals(symbol: str):
    """
    Scrapes fundamental data (D/E, Pledge %, CFO) from Screener.in
    """
    clean_sym = symbol.replace('.NS', '')
    url = f"https://www.screener.in/company/{clean_sym}/consolidated/"
    
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        # If consolidated doesn't exist, fallback to standalone
        if r.status_code == 404:
            url = f"https://www.screener.in/company/{clean_sym}/"
            r = requests.get(url, headers=HEADERS, timeout=10)
            
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        
        ratios = {}
        ratios['symbol'] = symbol
        
        # Extract ratios from the top list
        top_ratios = soup.select('.company-ratios li')
        for item in top_ratios:
            name = item.select_one('.name').text.strip()
            val_span = item.select_one('.number')
            if val_span:
                val = val_span.text.replace(',', '').strip()
                try:
                    ratios[name] = float(val)
                except:
                    ratios[name] = None
                    
        # Parse specific required fields (Debt/Equity, Promoter, Pledge)
        data = {
            'symbol': symbol,
            'debt_to_equity': ratios.get('Debt to equity', 0.0),
            'promoter_holding': ratios.get('Promoter holding', 0.0),
            'pledged_percentage': ratios.get('Pledged percentage', 0.0),
        }
        
        print(f"[{symbol}] Screener Data: D/E: {data['debt_to_equity']} | Pledge: {data['pledged_percentage']}%")
        return data
        
    except Exception as e:
        print(f"[{symbol}] Screener Error: {e}")
        return None

if __name__ == "__main__":
    print("Running Chartink Scraper...")
    df = fetch_chartink_watchlist()
    if df is not None:
        print("Running Screener.in Scraper for top 3 symbols...")
        for sym in df['nsecode'].head(3):
            fetch_screener_fundamentals(sym)
            time.sleep(1)
