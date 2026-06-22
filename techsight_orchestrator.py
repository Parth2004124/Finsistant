import sys
import os
import requests
import time
from datetime import datetime

# Add TechSight to path so we can import the engine
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, "TechSight", "core"))

from scoring_engine import ScoringEngine

def run_scan(is_amo):
    scan_type = "AMO Nightly Review" if is_amo else "Intraday 3:15 PM Auto-Exec Scan"
    print(f"\n[{datetime.now()}] Initiating TechSight Market Sweep: {scan_type}")
    
    import pandas as pd
    import yfinance as yf
    
    print("Fetching LIVE NIFTY 500 symbols from NSE...")
    try:
        url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
        df_nifty = pd.read_csv(url)
        symbols = df_nifty['Symbol'].tolist()
    except Exception as e:
        print("Failed to fetch from NSE. Falling back to NIFTY 50...")
        symbols = ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "ITC", "SBIN", "BHARTIARTL", "BAJFINANCE", "LARSEN"]
        
    yf_symbols = [f"{s}.NS" for s in symbols]
    
    print(f"Executing batched Volume & Momentum scan across {len(yf_symbols)} stocks...")
    
    # Fast batched download for the last 1 month to calculate 20-day average volume
    data = yf.download(yf_symbols, period="1mo", progress=False)
    
    viable_candidates = []
    
    # yf.download returns a multi-index DataFrame if multiple symbols
    if 'Volume' in data:
        volumes = data['Volume']
        closes = data['Close']
        
        for symbol in yf_symbols:
            try:
                sym_vol = volumes[symbol].dropna()
                sym_close = closes[symbol].dropna()
                
                if len(sym_vol) < 20: continue
                
                avg_vol_20 = sym_vol.iloc[-20:].mean()
                today_vol = sym_vol.iloc[-1]
                
                today_close = sym_close.iloc[-1]
                yesterday_close = sym_close.iloc[-2]
                
                # Check for Volume Anomaly (> 1.5x average) AND a Green Day
                if today_vol > (avg_vol_20 * 1.5) and today_close > yesterday_close:
                    clean_sym = symbol.replace(".NS", "")
                    viable_candidates.append({"symbol": clean_sym, "price": today_close})
            except Exception:
                continue
                
    if not viable_candidates:
        print("No stocks passed the initial Volume Gauntlet today.")
        return
    
    # --- PHASE 2: DEEP SCORING ---
    print("Running deep scoring on viable candidates...")
    engine = ScoringEngine()
    lucrative_trades = []
    
    for candidate in viable_candidates:
        print(f"Candidate passed initial volume gauntlet: {candidate['symbol']}")
        eval_result = engine.evaluate(candidate["symbol"], candidate["price"])
        
        if not eval_result:
            print(f"Dropped {candidate['symbol']}: Failed deep technical evaluation.")
            continue
            
        # Add the execution-specific flags (No quantity!)
        eval_result["transaction_type"] = "BUY"
        eval_result["order_type"] = "LIMIT"
        eval_result["exchange"] = "NSE"
        eval_result["is_amo"] = is_amo
        
        # Strict rules: Score >= 70 AND Confidence >= 55%
        tech_score = eval_result.get("technical_score", 0)
        confidence = eval_result.get("confidence", 0)
        
        if tech_score >= 70 and confidence >= 55:
            if confidence >= 70:
                eval_result["fundamental_flag"] = "RECOMMENDED: High Conviction"
            else:
                eval_result["fundamental_flag"] = "MANUAL CHECK: Moderate Conviction"
            lucrative_trades.append(eval_result)
        else:
            print(f"Dropped {candidate['symbol']}: Score={tech_score}, Confidence={confidence}%")

        
    # --- PHASE 3: STRICT TOP 3 FILTER ---
    # Sort by technical_score descending and slice top 3
    lucrative_trades.sort(key=lambda x: x.get("technical_score", 0), reverse=True)
    top_3_trades = lucrative_trades[:3]
        
    # --- PHASE 4: HANDOFF TO FLASK BACKEND ---
    print(f"Scan complete. Filtered down to the {len(top_3_trades)} absolute best setups out of 500. Pushing to Execution Bridge...")
    for trade in top_3_trades:
        print(f"[VERIFIED] {trade['tradingsymbol']} | Score: {trade.get('technical_score')} | Confidence: {trade.get('confidence')}%")
        try:
            resp = requests.post("http://127.0.0.1:8000/api/order", json=trade)
            if resp.status_code == 200:
                print(f"[SUCCESS] Queued {trade['tradingsymbol']}")
            else:
                print(f"[FAILED] {trade['tradingsymbol']}: {resp.text}")
        except Exception as e:
            print(f"[ERROR] Could not connect to local server for {trade['tradingsymbol']}: {e}")

    # --- PHASE 5: PORTFOLIO HOLDINGS SWEEP ---
    print("Sweeping current portfolio holdings for risk...")
    try:
        resp = requests.get("http://127.0.0.1:8000/api/portfolio")
        if resp.status_code == 200:
            portfolio = resp.json()
            for h in portfolio.get("holdings", []):
                sym = h["instrument"]
                qty = h["qty"]
                if qty <= 0: continue
                
                eval_result = engine.evaluate(sym, h["ltp"])
                if eval_result and (eval_result.get("technical_score", 100) < 50 or eval_result.get("confidence", 100) < 40):
                    print(f"RISK WARNING: {sym} score dropped to {eval_result.get('technical_score')}! Generating SELL suggestion.")
                    eval_result["transaction_type"] = "SELL"
                    eval_result["order_type"] = "MARKET"
                    eval_result["exchange"] = "NSE"
                    eval_result["is_amo"] = is_amo
                    eval_result["quantity"] = qty
                    eval_result["fundamental_flag"] = "CRITICAL: Score below 50"
                    
                    requests.post("http://127.0.0.1:8000/api/order", json=eval_result)
    except Exception as e:
        print(f"Failed portfolio sweep: {e}")

if __name__ == "__main__":
    # If --amo flag is passed, trades are queued as After Market Orders for review.
    # Otherwise, they are pushed as live limit orders (which auto-execute if they beat the rule thresholds).
    is_amo = "--amo" in sys.argv
    run_scan(is_amo)
