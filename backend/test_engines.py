import sys
import os
import json
import yfinance as yf

# Setup path to import from parent
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, '..', 'TechSight', 'core'))

try:
    from scoring_engine import ScoringEngine
except ImportError:
    print("Could not import TechSight ScoringEngine.")

def test_techsight(symbol):
    print(f"\n--- 1. TECHSIGHT ORCHESTRATOR (MACRO) ---")
    try:
        engine = ScoringEngine()
        # Fetch latest price robustly
        ticker = yf.Ticker(f"{symbol}.NS")
        hist = ticker.history(period="1mo")
        if hist.empty:
            print("Failed to fetch price data.")
            return
        price = hist['Close'].iloc[-1]
        
        result = engine.evaluate(symbol, price)
        if result:
            print(f"Result: LUCURATIVE TRADE FOUND!")
            print(f"Technical Score: {result['technical_score']}")
            print(f"Setup Type: {result['setup_type']}")
            print(f"CP (Entry): {result['entry_zone']}")
            print(f"TP (Target): {result['target']}")
            print(f"SL (Stop Loss): {result['stop_loss']}")
            print(f"HD (Hold Days): {result['expected_hold_days']}")
            print(f"Rationale:\n{result['why_lucrative']}")
        else:
            print(f"Result: Not deemed a lucrative trade by the orchestrator at this time.")
    except Exception as e:
        print(f"Error running TechSight: {e}")

def test_karlos(symbol):
    print(f"\n--- 2. KARLOS SIMULATOR (MICRO) ---")
    try:
        import subprocess
        import sqlite3
        import pandas as pd
        
        # Fetch historical data to feed Karlos
        ticker = yf.Ticker(f"{symbol}.NS")
        hist = ticker.history(period="3mo")
        
        ohlc = []
        for idx, row in hist.iterrows():
            ohlc.append({
                "time": idx.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "open": row["Open"],
                "high": row["High"],
                "low": row["Low"],
                "close": row["Close"]
            })
            
        conn = sqlite3.connect('trade_queue.db')
        c = conn.cursor()
        trade_id = "test_hesterbio"
        c.execute("DELETE FROM pending_trades WHERE id=?", (trade_id,))
        dummy_params = json.dumps({"ohlc": ohlc, "transaction_type": "BUY"})
        c.execute('''INSERT INTO pending_trades 
                     (id, symbol, setup_type, technical_score, confidence, rationale, entry_zone, stop_loss, target, rr_ratio, expected_hold_days, key_risks, fundamental_flag, market_context, status, generated_at, expires_at, trade_params)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                     (trade_id, symbol, "TEST_SETUP", 85, 0.9, json.dumps({"why_lucrative": "Test"}), "100-110", 90, 150, 2.0, "5-10", "None", "Neutral", "Bullish", "PENDING", "2026-06-29 10:00:00", "2026-06-30 10:00:00", dummy_params))
        conn.commit()
        
        print(f"Injected {len(ohlc)} historical candles into DB for Karlos. Simulating...")
        result = subprocess.run(['python', 'karlos_simulator.py', trade_id], capture_output=True, text=True)
        if result.stderr:
             print("Karlos Warnings/Errors:", result.stderr.strip())
        print(result.stdout.strip())
        
        c.execute("SELECT trade_params FROM pending_trades WHERE id=?", (trade_id,))
        row = c.fetchone()
        conn.close()
        
        if row and row[0]:
            params = json.loads(row[0])
            if "simulated_ohlc" in params:
                 sims = params["simulated_ohlc"]
                 print(f"Karlos successfully generated {len(sims)} simulated future candles!")
                 print(f"First simulated close: {sims[0]['close']}, Last simulated close: {sims[-1]['close']}")
            else:
                 print("Karlos did not generate simulated_ohlc data.")
        else:
            print("Karlos simulation did not save results.")
            
    except Exception as e:
        print(f"Error running Karlos: {e}")

def test_fundamentals(symbol):
    print(f"\n--- 3. FUNDAMENTAL ENGINE (BUSINESS/MOAT) ---")
    try:
        import subprocess
        result = subprocess.run(['python', 'fundamental_engine.py', symbol], capture_output=True, text=True)
        print(result.stdout.strip())
        
        import sqlite3
        conn = sqlite3.connect('fundamentals.db')
        c = conn.cursor()
        c.execute("SELECT scores_json FROM fundamentals WHERE symbol=?", (symbol,))
        row = c.fetchone()
        conn.close()
        
        if row:
            scores = json.loads(row[0])
            print(f"\nScores Breakdown: {json.dumps(scores, indent=2)}")
        else:
            print("Fundamental analysis did not save results.")
            
    except Exception as e:
        print(f"Error running Fundamentals: {e}")

if __name__ == "__main__":
    symbol = "HESTERBIO"
    print(f"=====================================")
    print(f"TESTING ALL 3 ENGINES FOR {symbol}")
    print(f"=====================================")
    
    test_fundamentals(symbol)
    test_karlos(symbol)
    test_techsight(symbol)
