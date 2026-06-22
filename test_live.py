import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, 'TechSight', 'core'))
sys.path.append(os.path.join(BASE_DIR, 'TechSight', 'data_engine'))
sys.path.append(os.path.join(BASE_DIR, 'TechSight', 'agents'))

from data_fetcher import DataFetcher
from scoring_engine import ScoringEngine
from agent4_predictor import Agent4Predictor

def run_live_proof(symbol):
    print(f"\n--- LIVE MARKET DATA PROOF FOR {symbol} ---")
    
    fetcher = DataFetcher()
    market_data = fetcher.fetch_historical_data(symbol)
    
    df_daily = market_data["daily"]
    df_weekly = market_data["weekly"]
    
    if df_daily.empty:
        print("ERROR: No data fetched from Yahoo Finance.")
        return
        
    last_price = df_daily['Close'].iloc[-1]
    last_date = df_daily.index[-1].strftime('%Y-%m-%d')
    print(f"Data Date: {last_date}")
    print(f"LTP (Last Traded Price): {last_price}")
    
    # Calculate real ATR mathematically just to print it explicitly
    high = df_daily['High']
    low = df_daily['Low']
    close = df_daily['Close']
    import pandas as pd
    tr = pd.DataFrame({
        'tr1': high - low, 
        'tr2': (high - close.shift(1)).abs(), 
        'tr3': (low - close.shift(1)).abs()
    }).max(axis=1)
    atr14 = tr.rolling(window=14).mean().iloc[-1]
    print(f"Real 14-Day ATR: {atr14}")
    
    engine = ScoringEngine()
    result = engine.evaluate(symbol, last_price, df_daily, df_weekly)
    
    print("\n--- 7 ENGINE MATHEMATICAL SCORES ---")
    for k, v in result["score_breakdown"].items():
        print(f"{k}: {v}/100")
        
    print("\n--- RISK MANAGEMENT MATH ---")
    print(f"Entry: {result['entry_zone']}")
    print(f"Stop Loss (1.5x ATR): {result['stop_loss']}")
    print(f"Target (3.5x ATR): {result['target']}")
    
    print("\n--- PREDICTOR (AGENT 4) ---")
    print(f"Predicted Hold Days: {result['expected_hold_days']}")
    print(f"Market Regime (NIFTY): {result['market_context']}")
    print(f"Identified Risks: {result['key_risks']}")
    
run_live_proof("ITC")
run_live_proof("RELIANCE")
