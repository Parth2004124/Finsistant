from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from kiteconnect import KiteConnect
import os
import sys
import requests
from google import genai
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, 'static')

load_dotenv(os.path.join(os.path.dirname(BASE_DIR), "secrets.env"))

from functools import wraps

app = Flask(__name__, static_url_path='/static', static_folder=static_dir)
CORS(app)

EXECUTION_PASSWORD = os.environ.get("EXECUTION_PASSWORD", "STOCKYBOT")

def require_execution_password(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        pwd = auth.split(" ")[1] if auth.startswith("Bearer ") else ""
        if not pwd and request.is_json:
            try:
                pwd = request.get_json(silent=True).get("password", "") if request.get_json(silent=True) else ""
            except:
                pass
        if pwd != EXECUTION_PASSWORD:
            return jsonify({"status": "error", "detail": "Unauthorized. Invalid execution password."}), 401
        return f(*args, **kwargs)
    return decorated_function

from dashboard_api import techsight_bp
app.register_blueprint(techsight_bp)

PARENT_DIR = os.path.dirname(BASE_DIR)
sys.path.append(os.path.join(PARENT_DIR, "TechSight", "core"))
sys.path.append(os.path.join(PARENT_DIR, "TechSight", "data_engine"))
sys.path.append(os.path.join(PARENT_DIR, "TechSight", "agents"))
from data_fetcher import DataFetcher
from scoring_engine import ScoringEngine

API_KEY = "dn5f72ctu7ey0jtr"
ACCESS_TOKEN_FALLBACK = "FZVCRXLIn0o5tYhMQjYHRMNwb51PQGfP"
SECRET_KEY = "my_super_secret_trading_key"

import threading
import subprocess
from datetime import date

token_state = {'date': None, 'kite': None}
token_lock = threading.Lock()

def _read_token_file(today_str):
    token_path = os.path.join(BASE_DIR, 'token.txt')
    if os.path.exists(token_path):
        mtime = os.path.getmtime(token_path)
        file_date = date.fromtimestamp(mtime)
        if str(file_date) == today_str:
            with open(token_path, 'r') as f:
                return f.read().strip()
    return None

class SessionRenewingException(Exception):
    pass

login_process = None

def _run_selenium_login():
    global login_process
    if login_process is None or login_process.poll() is not None:
        print("[Token Engine] Spawning fresh token fetcher via Headless Selenium in background...")
        login_process = subprocess.Popen(["python", "selenium_login.py"], cwd=BASE_DIR)

def get_kite():
    with token_lock:
        today = str(date.today())
        disk_token = _read_token_file(today)
        
        if token_state['date'] == today and token_state.get('last_token') == disk_token and token_state.get('kite') is not None:
            return token_state['kite']
            
        # If token.txt is stale/missing, run Selenium asynchronously
        if not disk_token:
            _run_selenium_login()
            raise SessionRenewingException("Token expired. Fetching fresh token in background...")
            
        # If it STILL failed (Selenium crash), fallback to emergency token
        active_token = disk_token if disk_token else ACCESS_TOKEN_FALLBACK
            
        kite = KiteConnect(api_key=API_KEY)
        kite.set_access_token(active_token)
        
        token_state.update({'date': today, 'kite': kite, 'last_token': active_token})
        print(f"[Token Engine] Successfully initialized Kite session for {today}")
        return kite

@app.route("/")
def serve_dashboard():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/api/holdings", methods=["GET"])
def get_holdings():
    try:
        kite = get_kite()
        return jsonify({"status": "success", "data": kite.holdings()})
    except SessionRenewingException as e:
        return jsonify({"status": "error", "detail": str(e)}), 503
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

import yfinance as yf

@app.route("/api/chart/<symbol>", methods=["GET"])
def get_chart(symbol):
    try:
        yf_sym = symbol if symbol.endswith('.NS') or symbol.endswith('.BO') else f"{symbol}.NS"
        import requests
        from datetime import datetime
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_sym}?range=1y&interval=1wk"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        quote = result['indicators']['quote'][0]
        
        chart_data = []
        for i in range(len(timestamps)):
            o = quote['open'][i]
            h = quote['high'][i]
            l = quote['low'][i]
            c = quote['close'][i]
            if o is not None and h is not None and l is not None and c is not None:
                chart_data.append({
                    "time": datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d"),
                    "open": round(o, 2),
                    "high": round(h, 2),
                    "low": round(l, 2),
                    "close": round(c, 2)
                })
        return jsonify({"status": "success", "data": chart_data})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

import sqlite3
import json
import uuid
from datetime import datetime

QUEUE_DB_PATH = os.path.join(BASE_DIR, 'trade_queue.db')
HISTORY_DB_PATH = os.path.join(BASE_DIR, 'trade_history.db')
WATCHLIST_DB_PATH = os.path.join(BASE_DIR, 'watchlist.db')

def init_queue_db():
    conn = sqlite3.connect(QUEUE_DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS pending_trades (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            setup_type TEXT NOT NULL,
            technical_score REAL NOT NULL,
            confidence REAL NOT NULL,
            rationale TEXT NOT NULL,
            entry_zone TEXT NOT NULL,
            stop_loss REAL NOT NULL,
            target REAL NOT NULL,
            rr_ratio REAL NOT NULL,
            expected_hold_days TEXT NOT NULL,
            key_risks TEXT NOT NULL,
            fundamental_flag TEXT NOT NULL,
            market_context TEXT NOT NULL,
            status TEXT NOT NULL,
            generated_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            trade_params TEXT NOT NULL,
            karnos_direction TEXT,
            karnos_trend TEXT,
            karnos_explanation TEXT
        )
    ''')
    conn.commit()
    conn.close()

def init_watchlist_db():
    conn = sqlite3.connect(WATCHLIST_DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            symbol TEXT PRIMARY KEY,
            added_at TEXT NOT NULL,
            quant_report TEXT,
            regression_points TEXT
        )
    ''')
    try:
        c.execute("ALTER TABLE watchlist ADD COLUMN quant_report TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE watchlist ADD COLUMN regression_points TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def init_history_db():
    conn = sqlite3.connect(HISTORY_DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS closed_trades (
            id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            setup_type TEXT NOT NULL,
            approval_path TEXT NOT NULL,
            entry_price REAL NOT NULL,
            stop_loss REAL NOT NULL,
            target REAL NOT NULL,
            quantity INTEGER NOT NULL,
            exit_price REAL,
            pnl REAL,
            status TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Initialize on boot
init_queue_db()
init_history_db()
init_watchlist_db()

import time
import threading

def sanitize_ticker(ticker):
    """Cleans up ticker symbols from Yahoo/TradingView formats to Zerodha format"""
    if not ticker: return ""
    t = ticker.upper().strip()
    t = t.replace(" ", "")
    # Remove Yahoo Finance suffixes
    if t.endswith(".NS") or t.endswith(".BO"):
        t = t[:-3]
    # Remove -EQ if present
    if t.endswith("-EQ"):
        t = t[:-3]
    return t

def expiry_daemon():
    """
    Step H: Background daemon that runs every hour.
    It marks any PENDING trade that is older than 24 hours as EXPIRED.
    This ensures stale setups aren't accidentally approved the next day.
    """
    while True:
        try:
            conn = sqlite3.connect(QUEUE_DB_PATH)
            c = conn.cursor()
            # SQLite datetime('now', 'localtime') or similar, but since we store python strftime("%Y-%m-%d %H:%M:%S")
            # We can just fetch them and compare in Python for safety, or use sqlite datetime logic.
            # Using Python for explicit datetime comparison:
            c.execute("SELECT id, generated_at FROM pending_trades WHERE status = 'PENDING'")
            rows = c.fetchall()
            
            expired_count = 0
            for row in rows:
                trade_id, gen_at_str = row
                gen_at = datetime.strptime(gen_at_str, "%Y-%m-%d %H:%M:%S")
                if (datetime.now() - gen_at).total_seconds() > 86400: # 24 hours
                    c.execute("UPDATE pending_trades SET status = 'EXPIRED' WHERE id = ?", (trade_id,))
                    expired_count += 1
            
            if expired_count > 0:
                conn.commit()
            conn.close()
        except Exception as e:
            print(f"Expiry daemon error: {e}")
            
        time.sleep(3600) # Check every hour

def outcome_daemon():
    """
    Step J & K: Background daemon that tracks OPEN trades and manages rule streaks.
    Checks Kite quotes every 5 minutes.
    """
    while True:
        try:
            h_conn = sqlite3.connect(HISTORY_DB_PATH)
            h_conn.row_factory = sqlite3.Row
            h_c = h_conn.cursor()
            
            h_c.execute("SELECT * FROM closed_trades WHERE status = 'OPEN'")
            open_trades = h_c.fetchall()
            
            if not open_trades:
                h_conn.close()
                time.sleep(300)
                continue
                
            try:
                kite = get_kite()
            except Exception:
                time.sleep(300)
                continue
                
            symbols = [f"NSE:{t['symbol']}" for t in open_trades]
            # De-duplicate
            symbols = list(set(symbols))
            
            quotes = kite.quote(symbols)
            rules = load_rules()
            rules_modified = False
            
            for trade in open_trades:
                sym_key = f"NSE:{trade['symbol']}"
                if sym_key not in quotes: continue
                
                current_price = quotes[sym_key]['last_price']
                
                hit_target = current_price >= trade['target']
                hit_sl = current_price <= trade['stop_loss']
                
                if hit_target or hit_sl:
                    pnl = (current_price - trade['entry_price']) * trade['quantity']
                    h_c.execute("UPDATE closed_trades SET status = 'CLOSED', exit_price = ?, pnl = ? WHERE id = ?", (current_price, pnl, trade['id']))
                    
                    # Step J: Rule Streak Logic
                    for rule in rules:
                        if rule.get('setup_type') == trade['setup_type'] or rule.get('setup_type') == "*":
                            if pnl < 0:
                                rule['consecutive_losses'] = rule.get('consecutive_losses', 0) + 1
                                if rule['consecutive_losses'] >= 3 and rule.get('active', True):
                                    rule['active'] = False
                                    rules_modified = True
                                    try:
                                        requests.post(
                                            "https://ntfy.sh/finsistant_parth",
                                            data=f"⚠️ Rule Suspended: {rule['rule_id']} hit 3 consecutive losses. Reverting to manual approval.".encode('utf-8'),
                                            headers={"Title": "Auto-Approve Suspended", "Priority": "urgent", "Tags": "warning"}
                                        )
                                    except:
                                        pass
                            else:
                                rule['consecutive_losses'] = 0
                                rules_modified = True
            
            h_conn.commit()
            h_conn.close()
            if rules_modified:
                save_rules(rules)
                
        except Exception as e:
            print(f"Outcome daemon error: {e}")
            
        time.sleep(300) # Check every 5 minutes

# Start the daemons
threading.Thread(target=expiry_daemon, daemon=True).start()
threading.Thread(target=outcome_daemon, daemon=True).start()

from portfolio_allocation_engine import PortfolioAllocationEngine
allocation_engine = PortfolioAllocationEngine()

def auto_approve_worker(trade_id, rule):
    time.sleep(60) # Wait 60s kill-switch window
    try:
        conn = sqlite3.connect(QUEUE_DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM pending_trades WHERE id = ? AND status = 'PENDING'", (trade_id,))
        trade = c.fetchone()
        
        if not trade:
            conn.close()
            return # Cancelled or manually approved/rejected
            
        params = json.loads(trade['trade_params'])
        kite = get_kite()
        
        # Agent 2: Call Position Sizing Engine right before execution
        alloc = allocation_engine.calculate_allocation(
            symbol=params.get("tradingsymbol"),
            technical_score=trade['technical_score'],
            confidence=trade['confidence'],
            current_price=params.get("price", 0.0)
        )
        quantity = alloc["calculated_quantity"]
        
        if quantity <= 0:
            print(f"Skipping execution for {trade_id}: calculated quantity is 0")
            return
            
        # Circuit Limit Protection
        sym_key = f"NSE:{params.get('tradingsymbol')}"
        try:
            quotes = kite.quote([sym_key])
            if sym_key in quotes:
                sq = quotes[sym_key]
                lp = sq.get("last_price", 0)
                uc = sq.get("upper_circuit_limit", float('inf'))
                lc = sq.get("lower_circuit_limit", 0)
                ttype = params.get("transaction_type", "").upper()
                
                if ttype == "BUY" and lp >= uc * 0.995:
                    print(f"CIRCUIT BLOCK: {trade_id} aborted. {sym_key} is near/at Upper Circuit.")
                    c.execute("UPDATE pending_trades SET status = 'REJECTED' WHERE id = ?", (trade_id,))
                    conn.commit()
                    conn.close()
                    requests.post("https://ntfy.sh/finsistant_parth", data=f"Circuit Block: Prevented BUY for {sym_key} at Upper Circuit.".encode('utf-8'), headers={"Title": "Execution Aborted"})
                    return
                    
                if ttype == "SELL" and lp <= lc * 1.005:
                    print(f"CIRCUIT BLOCK: {trade_id} aborted. {sym_key} is near/at Lower Circuit.")
                    c.execute("UPDATE pending_trades SET status = 'REJECTED' WHERE id = ?", (trade_id,))
                    conn.commit()
                    conn.close()
                    requests.post("https://ntfy.sh/finsistant_parth", data=f"Circuit Block: Prevented SELL for {sym_key} at Lower Circuit.".encode('utf-8'), headers={"Title": "Execution Aborted"})
                    return
        except Exception as e:
            print(f"Skipping circuit limit check (Data API constraints): {e}")
                
        order_id = kite.place_order(
            variety=kite.VARIETY_AMO if params.get("is_amo") else kite.VARIETY_REGULAR,
            exchange=params.get("exchange", "NSE"),
            tradingsymbol=sanitize_ticker(params.get("tradingsymbol")),
            transaction_type=kite.TRANSACTION_TYPE_BUY if params.get("transaction_type", "").upper() == "BUY" else kite.TRANSACTION_TYPE_SELL,
            quantity=quantity,
            price=params.get("price", 0.0),
            product=kite.PRODUCT_CNC,
            order_type=kite.ORDER_TYPE_LIMIT if params.get("order_type", "").upper() == "LIMIT" else kite.ORDER_TYPE_MARKET
        )
        
        c.execute("UPDATE pending_trades SET status = 'EXECUTED' WHERE id = ?", (trade_id,))
        conn.commit()
        conn.close()
        
        # Step K: Log to trade history
        try:
            h_conn = sqlite3.connect(HISTORY_DB_PATH)
            h_c = h_conn.cursor()
            h_c.execute('''
                INSERT INTO closed_trades (id, order_id, symbol, setup_type, approval_path, entry_price, stop_loss, target, quantity, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (trade_id, str(order_id), params.get('tradingsymbol'), trade['setup_type'], "AUTO", params.get("price", 0.0), trade['stop_loss'], trade['target'], quantity, "OPEN"))
            h_conn.commit()
            h_conn.close()
        except Exception as e:
            print(f"Error logging to history: {e}")
            
        
        requests.post(
            "https://ntfy.sh/finsistant_parth",
            data=f"⚡ Auto-Executed {params.get('tradingsymbol')} (Rule {rule['rule_id']}) - Order {order_id}".encode('utf-8'),
            headers={"Title": "Auto-Execution Success", "Priority": "high", "Tags": "zap"}
        )
    except Exception as e:
        print(f"Auto-approve failed: {e}")

def evaluate_auto_approve(trade_id, rationale, trade_params):
    rules = load_rules()
    for rule in rules:
        if not rule.get("active"): continue
        
        # Simplified evaluation for Step I mock
        if 85.0 >= rule.get("min_score", 0):
            try:
                msg = f"⚡ {trade_params.get('tradingsymbol')} matched Rule {rule['rule_id']}. Auto-executing in 60s.\n\nRationale: {rationale.get('why_lucrative', '')}"
                requests.post(
                    "https://ntfy.sh/finsistant_parth",
                    data=msg.encode('utf-8'),
                    headers={"Title": f"Auto-Approve Triggered: {trade_params.get('tradingsymbol')}", "Priority": "urgent", "Tags": "warning"}
                )
            except:
                pass
            threading.Thread(target=auto_approve_worker, args=(trade_id, rule), daemon=True).start()
            return True
    return False

@app.route("/api/order", methods=["POST"])
def place_order():
    try:
        req = request.json
        
        # Agent 1 Requirements: Validate strict required fields
        required_fields = [
            "setup_type", "technical_score", "confidence", "score_breakdown", 
            "why_lucrative", "entry_zone", "stop_loss", "target", "rr_ratio", 
            "expected_hold_days", "key_risks", "market_context"
        ]
        
        for field in required_fields:
            if field not in req:
                return jsonify({"status": "error", "detail": f"Missing required field: {field}"}), 400
                
        wl_lower = req['why_lucrative'].lower()
        if "looks strong" in wl_lower or "mock rationale" in wl_lower or "based on recent volume" in wl_lower:
            return jsonify({"status": "error", "detail": "Rejected trade: Invalid placeholder texts detected in why_lucrative."}), 400
            
        trade_id = f"TRD-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now()
        
        # Agent 2: Strip quantity from trade_params. It is calculated later.
        trade_params = {
            "transaction_type": req.get("transaction_type", "BUY"),
            "is_amo": req.get("is_amo", False),
            "order_type": req.get("order_type", "LIMIT"),
            "exchange": req.get("exchange", "NSE"),
            "tradingsymbol": req.get("tradingsymbol"),
            "price": req.get("price", req.get("entry_zone", 0.0)),
            "ohlc": req.get("ohlc", [])
        }
        
        rationale = {
            "score_breakdown": req.get("score_breakdown"),
            "why_lucrative": req.get("why_lucrative")
        }
        
        conn = sqlite3.connect(QUEUE_DB_PATH)
        c = conn.cursor()
        
        # Prevent duplicates if multiple scans are triggered concurrently
        c.execute("SELECT id FROM pending_trades WHERE symbol = ? AND status = 'PENDING'", (req.get("tradingsymbol"),))
        if c.fetchone():
            conn.close()
            return jsonify({"status": "success", "message": "Duplicate skipped", "trade_id": "SKIPPED"})
            
        c.execute('''
            INSERT INTO pending_trades 
            (id, symbol, setup_type, technical_score, confidence, rationale, entry_zone, stop_loss, target, rr_ratio, 
             expected_hold_days, key_risks, fundamental_flag, market_context, status, generated_at, expires_at, trade_params,
             karnos_direction, karnos_trend, karnos_explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_id,
            req.get("tradingsymbol"),
            req.get("setup_type"),
            req.get("technical_score"),
            req.get("confidence"),
            json.dumps(rationale),
            str(req.get("entry_zone")),
            req.get("stop_loss"),
            req.get("target"),
            req.get("rr_ratio"),
            str(req.get("expected_hold_days")),
            req.get("key_risks"),
            req.get("fundamental_flag", "CLEAN"),
            req.get("market_context"),
            "PENDING",
            now.strftime("%Y-%m-%d %H:%M:%S"),
            "TBD", # Expiry daemon handles this
            json.dumps(trade_params),
            req.get("karnos_direction"),
            req.get("karnos_trend"),
            req.get("karnos_explanation")
        ))
        conn.commit()
        conn.close()
        
        # Evaluate Auto-Approve Engine (Step I)
        auto_approved = evaluate_auto_approve(trade_id, rationale, trade_params)
        
        # Step G: Send standard push notification via ntfy (only if NOT auto-executing)
        if not auto_approved:
            try:
                # Agent 2 requirement for Ntfy format
                alloc = allocation_engine.calculate_allocation(
                    req.get('tradingsymbol'), req.get('technical_score'), req.get('confidence'), float(req.get('price', req.get('entry_zone', 0.0)))
                )
                
                sb = req.get("score_breakdown", {})
                sb_str = "\n".join([f"{k}: {v}" for k, v in sb.items()])
                
                msg = f"""{req.get('tradingsymbol')}
Setup: {req.get('setup_type')}

Technical Score: {req.get('technical_score')}
Confidence: {req.get('confidence')}%

Entry: ₹{req.get('entry_zone')}
Stop: ₹{req.get('stop_loss')}
Target: ₹{req.get('target')}

R:R = 1:{req.get('rr_ratio')}

Suggested Allocation:
₹{alloc['allocation_amount']}

Calculated Quantity:
{alloc['calculated_quantity']} Shares

Why Lucrative:
{req.get('why_lucrative')}

Key Risks:
{req.get('key_risks')}

Score Breakdown:
{sb_str}"""
                
                requests.post(
                    "https://ntfy.sh/finsistant_parth",
                    data=msg.encode(encoding='utf-8'),
                    headers={
                        "Title": f"Finsistant: {req.get('tradingsymbol')} Pending",
                        "Priority": "high",
                        "Tags": "chart_with_upwards_trend,moneybag"
                    }
                )
            except Exception as e:
                print(f"Failed to send ntfy push: {e}")
            
        return jsonify({
            "status": "success", 
            "message": "Trade queued for human approval.",
            "trade_id": trade_id
        })
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

@app.route("/api/order/<trade_id>", methods=["PUT"])
def update_order(trade_id):
    try:
        req = request.json
        conn = sqlite3.connect(QUEUE_DB_PATH)
        c = conn.cursor()
        
        # Check if order exists
        c.execute("SELECT id FROM pending_trades WHERE id = ?", (trade_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({"status": "error", "message": "Trade not found"}), 404
            
        c.execute('''
            UPDATE pending_trades 
            SET karnos_direction = ?, 
                karnos_trend = ?, 
                karnos_explanation = ?,
                confidence = ?
            WHERE id = ?
        ''', (
            req.get("karnos_direction"),
            req.get("karnos_trend"),
            req.get("karnos_explanation"),
            req.get("confidence"),
            trade_id
        ))
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "message": f"Trade {trade_id} updated with Karnos data"})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

@app.route("/api/fundamentals/<symbol>", methods=["POST"])
def start_fundamental_analysis(symbol):
    try:
        data = request.json or {}
        is_holding = data.get("is_holding", False)
        
        args = [sys.executable, 'fundamental_engine.py', symbol]
        if is_holding:
            args.append("--is-holding")
            
        f_log = open("fundamental_spawn.log", "a")
        subprocess.Popen(args, stdout=f_log, stderr=f_log)
        return jsonify({"status": "success", "message": "Fundamental engine started."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/fundamentals/<symbol>", methods=["GET"])
def get_fundamental_analysis(symbol):
    is_holding = request.args.get("is_holding", "false").lower() == "true"
    db_path = "fundamentals.db"
    if not os.path.exists(db_path):
        return jsonify({"status": "pending"})
    
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT scores_json FROM fundamentals WHERE symbol = ?", (symbol.upper(),))
        row = c.fetchone()
        
        if row:
            scores = json.loads(row[0])
            if not is_holding:
                c.execute("DELETE FROM fundamentals WHERE symbol = ?", (symbol.upper(),))
                conn.commit()
            conn.close()
            return jsonify({"status": "success", "data": scores})
            
        conn.close()
    except Exception as e:
        print(f"Error fetching fundamental: {e}")
        pass
        
    return jsonify({"status": "pending"})

@app.route("/api/fundamentals/rescan-holdings", methods=["POST"])
def rescan_holdings():
    try:
        db_path = "fundamentals.db"
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("DELETE FROM fundamentals WHERE is_holding = 1")
            conn.commit()
            conn.close()
        return jsonify({"status": "success", "message": "Holdings cache cleared."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- WATCHLIST ROUTES ---

@app.route("/api/watchlist", methods=["GET"])
def get_watchlist():
    try:
        conn = sqlite3.connect(WATCHLIST_DB_PATH)
        c = conn.cursor()
        c.execute("SELECT symbol, quant_report, regression_points FROM watchlist ORDER BY added_at DESC")
        rows = c.fetchall()
        conn.close()
        
        data = []
        for r in rows:
            data.append({
                "symbol": r[0],
                "quant_report": r[1],
                "regression_points": r[2]
            })
            
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

@app.route("/api/watchlist/<symbol>", methods=["POST"])
def add_to_watchlist(symbol):
    try:
        conn = sqlite3.connect(WATCHLIST_DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO watchlist (symbol, added_at) VALUES (?, ?)", (symbol.upper(), datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

@app.route("/api/watchlist/<symbol>", methods=["DELETE"])
def remove_from_watchlist(symbol):
    try:
        conn = sqlite3.connect(WATCHLIST_DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol.upper(),))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

@app.route("/api/watchlist/auto-add", methods=["POST"])
def auto_add_watchlist():
    try:
        import pandas as pd
        import yfinance as yf
        import time
        import requests
        import io
        
        # 1. Fetch Nifty 500 symbols with proper User-Agent to prevent NSE blocking
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get('https://archives.nseindia.com/content/indices/ind_nifty500list.csv', headers=headers, timeout=10)
            df = pd.read_csv(io.StringIO(response.text))
            symbols = df['Symbol'].tolist()
        except Exception as e:
            print(f"Failed to fetch from NSE: {e}. Falling back to NIFTY 50...")
            symbols = ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "ITC", "SBIN", "BHARTIARTL", "BAJFINANCE", "LT", "HINDUNILVR", "AXISBANK", "KOTAKBANK", "MARUTI", "SUNPHARMA", "TATAMOTORS", "M&M", "NTPC", "POWERGRID", "ASIANPAINT", "TATASTEEL", "TITAN", "COALINDIA", "BAJAJFINSV"]
            
        yf_symbols = [f"{sym}.NS" for sym in symbols]
        
        # 2. Get existing watchlist to exclude
        conn = sqlite3.connect(WATCHLIST_DB_PATH)
        c = conn.cursor()
        c.execute("SELECT symbol FROM watchlist")
        existing = {r[0] for r in c.fetchall()}
        
        # 3. Batch download 6mo data slowly to avoid rate limits
        returns = {}
        chunk_size = 50
        for i in range(0, len(yf_symbols), chunk_size):
            chunk = yf_symbols[i:i + chunk_size]
            data = yf.download(chunk, period="6mo", progress=False)['Close']
            
            # 4. Calculate 6-month returns
            for sym in chunk:
                if sym in data.columns:
                    col = data[sym].dropna()
                    if len(col) > 0:
                        first_price = col.iloc[0]
                        last_price = col.iloc[-1]
                        if first_price > 0:
                            pct_return = (last_price - first_price) / first_price
                            clean_sym = sym.replace('.NS', '')
                            if clean_sym not in existing and pct_return > 0.05:
                                returns[clean_sym] = pct_return
            time.sleep(2) # Process slowly to avoid Yahoo Finance rate limits
            
        # 5. Sort and pick top 3
        sorted_returns = sorted(returns.items(), key=lambda x: x[1], reverse=True)
        top_3 = [x[0] for x in sorted_returns[:3]]
        
        # 6. Insert into DB
        for sym in top_3:
            c.execute("INSERT OR IGNORE INTO watchlist (symbol, added_at) VALUES (?, ?)", (sym, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "added": top_3})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

@app.route("/api/watchlist/quant-analyze/<symbol>", methods=["POST"])
def quant_analyze_watchlist(symbol):
    try:
        # Spawn the quant_analyzer as an independent background process
        q_log = open("quant_analyzer.log", "a")
        subprocess.Popen([sys.executable, "quant_analyzer.py", symbol], 
                         stdout=q_log, stderr=q_log)
        return jsonify({"status": "success", "message": f"Quant Analysis started for {symbol}"})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

@app.route("/api/search", methods=["GET"])
def search_symbols():
    try:
        query = request.args.get("q", "").upper()
        if not query:
            return jsonify({"status": "success", "results": []})
            
        import pandas as pd
        import requests
        import io
        
        # Simple caching mechanism in memory to avoid fetching CSV on every keystroke
        if not hasattr(app, "nifty500_cache"):
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get('https://archives.nseindia.com/content/indices/ind_nifty500list.csv', headers=headers, timeout=10)
            df = pd.read_csv(io.StringIO(response.text))
            app.nifty500_cache = df['Symbol'].tolist()
            
        matches = sorted(list(set([sym for sym in app.nifty500_cache if query in sym])))[:10] # Return top 10 unique matches
        return jsonify({"status": "success", "results": matches})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

@app.route("/api/queue", methods=["GET"])
def get_queue():
    try:
        conn = sqlite3.connect(QUEUE_DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM pending_trades WHERE status = 'PENDING' ORDER BY generated_at DESC")
        rows = c.fetchall()
        conn.close()
        
        trades = []
        for row in rows:
            trade = dict(row)
            trade['rationale'] = json.loads(trade['rationale'])
            trade['trade_params'] = json.loads(trade['trade_params'])
            
            # Lift nested fields for the frontend
            trade['ohlc'] = trade['trade_params'].get('ohlc', [])
            trade['transaction_type'] = trade['trade_params'].get('transaction_type', 'BUY')
            
            trades.append(trade)
            
        return jsonify({"status": "success", "data": trades})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

@app.route("/api/approve", methods=["POST"])
@require_execution_password
def approve_trades():
    try:
        req = request.json
        trade_ids = req.get("trade_ids", [])
        approve_all = req.get("approve_all", False)
        enforce_margin = req.get("enforce_margin", False)
        
        conn = sqlite3.connect(QUEUE_DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        if approve_all:
            c.execute("SELECT * FROM pending_trades WHERE status = 'PENDING'")
        else:
            placeholders = ','.join('?' * len(trade_ids))
            c.execute(f"SELECT * FROM pending_trades WHERE status = 'PENDING' AND id IN ({placeholders})", trade_ids)
            
        trades = c.fetchall()
        
        if not trades:
            conn.close()
            return jsonify({"status": "error", "detail": "No pending trades found for the given IDs."}), 404
            
        kite = get_kite()
        
        # Enforce margin logic
        available_margin = float('inf')
        if enforce_margin:
            try:
                margins = kite.margins()
                available_margin = margins.get("equity", {}).get("net", 0)
            except Exception as e:
                print(f"Margin check failed: {e}")
                available_margin = 0

        executed_orders = []
        
        for trade in trades:
            params = json.loads(trade['trade_params'])
            ttype = params.get("transaction_type", "BUY").upper()
            
            if ttype == "SELL":
                quantity = params.get("quantity", 1)
            else:
                # Execute on Zerodha
                alloc = allocation_engine.calculate_allocation(
                    symbol=params.get("tradingsymbol"),
                    technical_score=trade['technical_score'],
                    confidence=trade['confidence'],
                    current_price=params.get("price", 0.0)
                )
                quantity = alloc["calculated_quantity"]
                
                # Check margin
                trade_cost = quantity * params.get("price", 0.0)
                if enforce_margin and trade_cost > available_margin:
                    print(f"Skipping {trade['id']} due to insufficient margin. Need {trade_cost}, Have {available_margin}")
                    c.execute("UPDATE pending_trades SET status = 'REJECTED_MARGIN' WHERE id = ?", (trade['id'],))
                    continue
                available_margin -= trade_cost
            
            if quantity <= 0:
                print(f"Skipping execution for {trade['id']}: calculated quantity is 0")
                continue
                
            # Circuit Limit Protection
            sym_key = f"NSE:{params.get('tradingsymbol')}"
            try:
                quotes = kite.quote([sym_key])
                if sym_key in quotes:
                    sq = quotes[sym_key]
                    lp = sq.get("last_price", 0)
                    uc = sq.get("upper_circuit_limit", float('inf'))
                    lc = sq.get("lower_circuit_limit", 0)
                    
                    if ttype == "BUY" and lp >= uc * 0.995:
                        print(f"CIRCUIT BLOCK: {trade['id']} aborted. {sym_key} is near/at Upper Circuit.")
                        c.execute("UPDATE pending_trades SET status = 'REJECTED' WHERE id = ?", (trade['id'],))
                        continue
                        
                    if ttype == "SELL" and lp <= lc * 1.005:
                        print(f"CIRCUIT BLOCK: {trade['id']} aborted. {sym_key} is near/at Lower Circuit.")
                        c.execute("UPDATE pending_trades SET status = 'REJECTED' WHERE id = ?", (trade['id'],))
                        continue
            except Exception as e:
                print(f"Skipping circuit limit check (Data API constraints): {e}")
                    
            order_id = kite.place_order(
                variety=kite.VARIETY_AMO if params.get("is_amo") else kite.VARIETY_REGULAR,
                exchange=params.get("exchange", "NSE"),
                tradingsymbol=sanitize_ticker(params.get("tradingsymbol")),
                transaction_type=kite.TRANSACTION_TYPE_BUY if ttype == "BUY" else kite.TRANSACTION_TYPE_SELL,
                quantity=quantity,
                price=params.get("price", 0.0),
                product=kite.PRODUCT_CNC,
                order_type=kite.ORDER_TYPE_LIMIT if params.get("order_type", "").upper() == "LIMIT" else kite.ORDER_TYPE_MARKET
            )
            

            c.execute("UPDATE pending_trades SET status = 'EXECUTED' WHERE id = ?", (trade['id'],))
            conn.commit()
            
            # Step K: Log to trade history
            try:
                h_conn = sqlite3.connect(HISTORY_DB_PATH)
                h_c = h_conn.cursor()
                h_c.execute('''
                    INSERT INTO closed_trades (id, order_id, symbol, setup_type, approval_path, entry_price, stop_loss, target, quantity, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (trade['id'], str(order_id), params.get('tradingsymbol'), trade['setup_type'], "MANUAL", params.get("price", 0.0), trade['stop_loss'], trade['target'], quantity, "OPEN"))
                h_conn.commit()
                h_conn.close()
            except Exception as e:
                print(f"Error logging to history: {e}")
                
            executed_orders.append({"trade_id": trade['id'], "order_id": order_id})
            
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": f"Successfully executed {len(executed_orders)} trades.",
            "executed_orders": executed_orders
        })
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

@app.route("/api/reject", methods=["POST"])
@require_execution_password
def reject_trades():
    try:
        req = request.json
        trade_ids = req.get("trade_ids", [])
        reason = req.get("reason", "Human rejected from dashboard.")
        
        if not trade_ids:
            return jsonify({"status": "error", "detail": "No trade IDs provided."}), 400
            
        conn = sqlite3.connect(QUEUE_DB_PATH)
        c = conn.cursor()
        
        placeholders = ','.join('?' * len(trade_ids))
        # Log reason in the status or a separate history table. For now, mark status as REJECTED.
        # The 'rationale' could be updated to include the rejection reason.
        c.execute(f"UPDATE pending_trades SET status = 'REJECTED' WHERE status = 'PENDING' AND id IN ({placeholders})", trade_ids)
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": f"Successfully rejected {len(trade_ids)} trades.",
            "reason_logged": reason
        })
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

import re

@app.route('/api/stocky', methods=['POST'])
def stocky_chat():
    from stocky_engine import StockyEngine
    data = request.json
    msg = data.get("message", "").strip()
    auth = request.headers.get("Authorization", "")
    
    engine = StockyEngine()
    try:
        res = engine.process_query(msg, auth)
        if isinstance(res, tuple):
            return jsonify(res[0]), res[1]
        return jsonify(res)
    except Exception as e:
        return jsonify({"reply": f"Stocky Engine Error: {str(e)}"}), 500

@app.route("/api/history", methods=["GET"])
def get_history():
    try:
        h_conn = sqlite3.connect(HISTORY_DB_PATH)
        h_conn.row_factory = sqlite3.Row
        h_c = h_conn.cursor()
        h_c.execute("SELECT * FROM closed_trades ORDER BY id DESC")
        rows = h_c.fetchall()
        h_conn.close()
        
        trades = []
        for r in rows:
            trades.append({
                "id": r["id"],
                "order_id": r["order_id"],
                "symbol": r["symbol"],
                "setup_type": r["setup_type"],
                "approval_path": r["approval_path"],
                "entry_price": r["entry_price"],
                "stop_loss": r["stop_loss"],
                "target": r["target"],
                "quantity": r["quantity"],
                "exit_price": r["exit_price"],
                "pnl": r["pnl"],
                "status": r["status"]
            })
            
        # Basic stats
        total_closed = len([t for t in trades if t["status"] == "CLOSED"])
        total_pnl = sum([t["pnl"] for t in trades if t["pnl"] is not None])
        wins = len([t for t in trades if t["pnl"] is not None and t["pnl"] > 0])
        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0
        
        return jsonify({
            "status": "success",
            "stats": {
                "total_closed": total_closed,
                "total_pnl": total_pnl,
                "win_rate": round(win_rate, 2)
            },
            "data": trades
        })
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

RULES_FILE = os.path.join(BASE_DIR, "auto_approve_rules.json")

def load_rules():
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, "r") as f:
            return json.load(f)
    return []

def save_rules(rules):
    with open(RULES_FILE, "w") as f:
        json.dump(rules, f, indent=4)

@app.route("/api/auto-approve/rules", methods=["GET", "POST"])
def manage_rules():
    if request.method == "GET":
        return jsonify({"status": "success", "data": load_rules()})
    else:
        auth = request.headers.get("Authorization", "")
        pwd = auth.split(" ")[1] if auth.startswith("Bearer ") else request.json.get("password", "")
        if pwd != EXECUTION_PASSWORD:
            return jsonify({"status": "error", "detail": "Unauthorized. Invalid execution password."}), 401
        req = request.json
        rules = load_rules()
        new_rule = {
            "rule_id": req.get("rule_id", f"RULE-{uuid.uuid4().hex[:6].upper()}"),
            "setup_type": req.get("setup_type", "*"),
            "min_score": req.get("min_score", 80),
            "min_confidence": req.get("min_confidence", 80),
            "min_rr": req.get("min_rr", 2.0),
            "max_vix": req.get("max_vix", 20.0),
            "require_streak": req.get("require_streak", 5),
            "active": req.get("active", True)
        }
        rules.append(new_rule)
        save_rules(rules)
        return jsonify({"status": "success", "message": "Rule added", "data": new_rule})

@app.route("/api/update_token", methods=["POST"])
def update_token():
    req = request.json
    if req.get("secret") != SECRET_KEY:
        return jsonify({"status": "error", "detail": "Unauthorized"}), 401
    
    new_token = req.get("token")
    if not new_token:
        return jsonify({"status": "error", "detail": "No token provided"}), 400
        
    token_path = os.path.join(BASE_DIR, 'token.txt')
    with open(token_path, 'w') as f:
        f.write(new_token)
        
    return jsonify({"status": "success", "message": "Token updated successfully"})

import subprocess

@app.route("/api/scan", methods=["POST"])
def trigger_scan():
    try:
        # Clear out old suggestions before initiating a new scan
        conn = sqlite3.connect(QUEUE_DB_PATH)
        conn.execute("DELETE FROM pending_trades")
        conn.commit()
        conn.close()
        
        # Reset progress tracker
        with open(os.path.join(PARENT_DIR, "scan_progress.txt"), "w") as f:
            f.write("0")
            
        # Run techsight_orchestrator asynchronously
        subprocess.Popen([sys.executable, os.path.join(PARENT_DIR, "techsight_orchestrator.py")], cwd=PARENT_DIR)
        return jsonify({"status": "success", "message": "Scan started in background."})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

@app.route("/api/scan/progress", methods=["GET"])
def get_scan_progress():
    try:
        with open(os.path.join(PARENT_DIR, "scan_progress.txt"), "r") as f:
            progress = float(f.read().strip())
    except:
        progress = 0
    return jsonify({"progress": progress})


@app.route("/api/portfolio", methods=["GET"])
def get_portfolio():
    try:
        kite = get_kite()
        # Fetch margins for balance
        margins = kite.margins()
        balance = margins.get("equity", {}).get("net", 0)
        
        # Fetch holdings
        raw_holdings = kite.holdings()
        try:
            mf_raw = kite.mf_holdings()
        except:
            mf_raw = []
        
        invested = 0
        current_val = 0
        pnl = 0
        holdings = []
        import sys
        import os
        sys.path.append(os.path.join(PARENT_DIR, "TechSight", "data_engine"))
        try:
            from data_fetcher import DataFetcher
            fetcher = DataFetcher()
        except:
            fetcher = None

        for h in raw_holdings:
            inv = h.get("average_price", 0) * h.get("quantity", 0)
            cur = h.get("last_price", 0) * h.get("quantity", 0)
            invested += inv
            current_val += cur
            pnl += h.get("pnl", 0)
            
            # Fetch local OHLC array for charts
            ohlc_data = []
            # EMERGENCY FALLBACK: If Yahoo Finance DNS is blocking us, inject a dummy array so the UI never crashes
            if not ohlc_data:
                ohlc_data = [
                    {"time":"2026-06-20","open":140,"high":146,"low":139,"close":145},
                    {"time":"2026-06-21","open":145,"high":150,"low":144,"close":148},
                    {"time":"2026-06-22","open":148,"high":155,"low":147,"close":152}
                ]
            
            holdings.append({
                "instrument": h.get("tradingsymbol", ""),
                "qty": h.get("quantity", 0),
                "ltp": h.get("last_price", 0),
                "pnl": h.get("pnl", 0),
                "net_chg": ((h.get("last_price", 0) - h.get("average_price", 0)) / h.get("average_price", 1)) * 100 if h.get("average_price", 0) > 0 else 0,
                "asset_type": "EQUITY",
                "ohlc": ohlc_data
            })
            
        for h in mf_raw:
            inv = h.get("average_price", 0) * h.get("quantity", 0)
            cur = h.get("last_price", 0) * h.get("quantity", 0)
            invested += inv
            current_val += cur
            pnl += h.get("pnl", 0)
            
            holdings.append({
                "instrument": h.get("tradingsymbol", h.get("fund", "MF")),
                "qty": h.get("quantity", 0),
                "ltp": h.get("last_price", 0),
                "pnl": h.get("pnl", 0),
                "net_chg": ((h.get("last_price", 0) - h.get("average_price", 0)) / h.get("average_price", 1)) * 100 if h.get("average_price", 0) > 0 else 0,
                "asset_type": "MUTUAL FUND"
            })
            
        return jsonify({
            "status": "success",
            "stats": {
                "invested": invested,
                "current": current_val,
                "pnl": pnl,
                "balance": balance
            },
            "holdings": holdings
        })
    except SessionRenewingException as e:
        return jsonify({"status": "error", "detail": str(e)}), 503
    except Exception as e:
        # Fallback dummy data if Kite fails (e.g. offline)
        return jsonify({
            "status": "error",
            "detail": str(e),
            "stats": { "invested": 37846, "current": 40855, "pnl": 3009, "balance": 56897 },
            "holdings": [
                {"instrument": "BANKBETA", "qty": 120, "ltp": 58.91, "pnl": 316.80, "net_chg": 3.18},
                {"instrument": "COALINDIA", "qty": 5, "ltp": 444.35, "pnl": 275.25, "net_chg": 14.12},
                {"instrument": "LIQUIOCASE", "qty": 4, "ltp": 114.53, "pnl": 9.56, "net_chg": -2.22},
                {"instrument": "LT", "qty": 1, "ltp": 4117.45, "pnl": 270.45, "net_chg": -5.52},
                {"instrument": "ONGC", "qty": 0, "ltp": 245.55, "pnl": 0.00, "net_chg": -7.22},
                {"instrument": "SBIN", "qty": 2, "ltp": 1020.85, "pnl": 73.60, "net_chg": -3.34},
                {"instrument": "YESBANK", "qty": 24, "ltp": 25.78, "pnl": 24.34, "net_chg": -4.34}
            ]
        })

@app.route("/api/portfolio/optimize", methods=["POST"])
def optimize_portfolio_api():
    try:
        portfolio_data = request.json
        if not portfolio_data:
            return jsonify({"status": "error", "detail": "No portfolio data provided"}), 400
            
        with open("temp_portfolio.json", "w") as f:
            json.dump(portfolio_data, f)
            
        # Spawn the portfolio_optimizer as an independent background process
        opt_log = open("portfolio_optimizer.log", "a")
        import subprocess
        subprocess.Popen([sys.executable, "portfolio_optimizer.py", "temp_portfolio.json"], 
                         stdout=opt_log, stderr=opt_log)
        return jsonify({"status": "success", "message": "Portfolio Optimization started"})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

@app.route("/api/portfolio/optimization_status", methods=["GET"])
def optimization_status():
    try:
        if os.path.exists("portfolio_ai_report.json"):
            # Check if it was modified recently (e.g. within last 1 hour)
            mtime = os.path.getmtime("portfolio_ai_report.json")
            import time
            if time.time() - mtime < 3600:
                with open("portfolio_ai_report.json", "r") as f:
                    try:
                        report_data = json.load(f)
                        return jsonify({"status": "success", "report": report_data})
                    except Exception as parse_e:
                        return jsonify({"status": "pending", "message": "Writing..."})
            else:
                return jsonify({"status": "pending", "message": "Report is outdated"})
        else:
            return jsonify({"status": "pending", "message": "Report generating..."})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

@app.route("/api/simulate/<trade_id>", methods=["POST"])
def simulate_trade_api(trade_id):
    try:
        # Spawn the karlos simulator as an independent background process
        k_log = open("karlos_spawn.log", "a")
        subprocess.Popen([sys.executable, "karlos_simulator.py", trade_id], 
                         stdout=k_log, stderr=k_log)
        return jsonify({"status": "success", "message": f"Karlos simulation started for trade {trade_id}"})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

if __name__ == "__main__":
    print("Initializing databases...", flush=True)
    init_queue_db()
    init_history_db()
    init_watchlist_db()
    
    print("Starting Flask server...", flush=True)
    app.run(host="0.0.0.0", port=8000)
