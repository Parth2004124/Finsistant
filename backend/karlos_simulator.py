import sys
import os
import json
import sqlite3
import pandas as pd
import warnings
from datetime import datetime
warnings.filterwarnings('ignore')

def log_msg(msg):
    with open("karlos.log", "a") as f:
        f.write(f"[{datetime.now()}] {msg}\n")
    print(msg)

# Point to the Kronos repo for the model architecture
sys.path.append(r"C:\Users\parth\Desktop\Kronos")
try:
    from model import Kronos, KronosTokenizer, KronosPredictor
except ImportError as e:
    print(f"Failed to import Kronos: {e}")
    sys.exit(1)

def simulate_trade(trade_id):
    db_path = "trade_queue.db"
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT trade_params, symbol FROM pending_trades WHERE id = ?", (trade_id,))
    row = c.fetchone()
    if not row:
        print(f"Trade ID {trade_id} not found.")
        conn.close()
        return

    trade_params = json.loads(row[0])
    symbol = row[1]
    
    ohlc = trade_params.get("ohlc", [])
    if not ohlc:
        print("Historical OHLC data missing in DB, fetching fresh data from backend...")
        import requests
        try:
            res = requests.get(f"http://127.0.0.1:8000/api/chart/{symbol}")
            data = res.json()
            if data.get("status") == "success":
                ohlc = data.get("data", [])
        except Exception as e:
            print(f"Failed to fetch fresh OHLC data: {e}")
            
    if not ohlc:
        print("No historical OHLC data found for simulation even after fetch attempt.")
        # Update progress to error state so frontend doesn't hang
        trade_params["karlos_progress"] = -1 
        c.execute("UPDATE pending_trades SET trade_params = ? WHERE id = ?", (json.dumps(trade_params), trade_id))
        conn.commit()
        conn.close()
        return
        
    print(f"Starting Karlos simulation for {symbol} with {len(ohlc)} historical candles...")
    
    def update_progress(pct):
        trade_params["karlos_progress"] = pct
        c.execute("UPDATE pending_trades SET trade_params = ? WHERE id = ?", (json.dumps(trade_params), trade_id))
        conn.commit()

    update_progress(10)

    # Convert orchestrator OHLC to DataFrame for Kronos
    # Kronos requires: open, high, low, close, volume, amount, timestamps
    df_data = []
    for candle in ohlc:
        df_data.append({
            "timestamps": pd.to_datetime(candle["time"]),
            "open": candle["open"],
            "high": candle["high"],
            "low": candle["low"],
            "close": candle["close"],
            "volume": 1000000.0, # Mock volume since orchestrator only provided price
            "amount": 10000000.0 # Mock amount
        })
    df = pd.DataFrame(df_data)

    update_progress(25)

    # 1. Load Model and Tokenizer from local cache
    print("Loading Kronos AI model...")
    cache_dir = r"C:\Users\parth\Desktop\Kronos_model"
    
    # We use local paths or cache dir. The user's cache contains Kronos-mini
    update_progress(40)
    tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-2k", cache_dir=cache_dir)
    update_progress(60)
    model = Kronos.from_pretrained("NeoQuasar/Kronos-mini", cache_dir=cache_dir)
    update_progress(75)
    predictor = KronosPredictor(model, tokenizer, max_context=512)

    # 2. Prepare Data
    lookback = len(df)
    pred_len = 5 # 1/4th of 15 days is ~4-5 days
    
    x_df = df[['open', 'high', 'low', 'close', 'volume', 'amount']]
    x_timestamp = df['timestamps']
    
    # Generate future timestamps (skip weekends if possible, but basic freq='B' works)
    last_date = df['timestamps'].iloc[-1]
    y_timestamp = pd.Series(pd.date_range(start=last_date + pd.Timedelta(days=1), periods=pred_len, freq='B'))

    update_progress(85)
    print("Running inference...")
    # 3. Make Prediction
    pred_df = predictor.predict(
        df=x_df,
        x_timestamp=x_timestamp,
        y_timestamp=y_timestamp,
        pred_len=pred_len,
        T=1.0,
        top_p=0.9,
        sample_count=1,
        verbose=False
    )
    
    print("Inference complete.")
    
    # Format simulated OHLC back to JSON
    simulated_ohlc = []
    for i in range(len(pred_df)):
        simulated_ohlc.append({
            "time": y_timestamp[i].strftime("%Y-%m-%d"),
            "open": float(pred_df['open'].iloc[i]),
            "high": float(pred_df['high'].iloc[i]),
            "low": float(pred_df['low'].iloc[i]),
            "close": float(pred_df['close'].iloc[i])
        })
        
    # Append to trade_params
    trade_params["simulated_ohlc"] = simulated_ohlc
    
    c.execute("UPDATE pending_trades SET trade_params = ? WHERE id = ?", (json.dumps(trade_params), trade_id))
    conn.commit()
    conn.close()
    
    print(f"Successfully saved {pred_len} simulated candles to trade {trade_id}!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python karlos_simulator.py <trade_id>")
        sys.exit(1)
    
    simulate_trade(sys.argv[1])
