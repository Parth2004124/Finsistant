import sys
import os
import json
import sqlite3
import yfinance as yf
from datetime import datetime

def safe_float(val, multiplier=1.0, default=0.0):
    if val is None:
        return default
    try:
        return float(val) * multiplier
    except (ValueError, TypeError):
        return default

def calculate_fundamental_score(info):
    scores = {"business": 0, "moat": 0, "management": 0, "risk": 0, "total": 0, "explanation": ""}
    reasons = []

    # Map yfinance info to StockSight V2 metrics
    roe = safe_float(info.get('returnOnEquity'), 100)
    roce = safe_float(info.get('returnOnAssets'), 100) # Proxy for ROCE if not perfectly available
    salesGrowth = safe_float(info.get('revenueGrowth'), 100)
    profitGrowth = safe_float(info.get('earningsGrowth'), 100)
    opm = safe_float(info.get('operatingMargins'), 100)
    pe = safe_float(info.get('trailingPE'))
    mcap = safe_float(info.get('marketCap'), 1/(10**7)) # Convert to Crores
    beta = safe_float(info.get('beta'), default=1.0)
    ret1y = safe_float(info.get('52WeekChange'), 100)
    name = str(info.get('longName', info.get('shortName', ''))).upper()

    isAutoOrPower = any(k in name for k in ["MOTORS", "AUTO", "POWER", "ENERGY", "STEEL"])
    isFinancial = not isAutoOrPower and ((roce < 12 and roe > 15) or any(k in name for k in ["FINANCE", "BANK", "CAPITAL", "HOLDINGS"]))

    # Sales Growth
    if salesGrowth > 15: scores["business"] += 15
    elif salesGrowth > 8: scores["business"] += 10
    elif salesGrowth > 0: scores["business"] += 5
    elif salesGrowth > -10: 
        scores["business"] += 2
        reasons.append("Sales Drag")

    # Profit Growth
    if profitGrowth > 15: scores["business"] += 15
    elif profitGrowth > 8: scores["business"] += 10
    elif profitGrowth > 0: scores["business"] += 5
    elif profitGrowth > -20:
        scores["business"] += 2
        reasons.append("Profit Drag")

    if isFinancial:
        if roe > 15: scores["business"] += 10
        elif roe > 10: scores["business"] += 5
        elif roe > 5: scores["business"] += 2
    else:
        if opm > 20: scores["business"] += 10
        elif opm > 12: scores["business"] += 5
        elif opm > 8:
            scores["business"] += 2
            reasons.append("Low Margin")
            
    scores["business"] = min(40, scores["business"])

    # Moat
    if isFinancial:
        if roe > 18: scores["moat"] += 8
        elif roe > 12: scores["moat"] += 5
    else:
        if opm > 18: scores["moat"] += 5
        if roce > 20: scores["moat"] += 5
        
    if mcap > 20000: scores["moat"] += 5
    elif mcap > 5000: scores["moat"] += 3
    
    if profitGrowth > salesGrowth: scores["moat"] += 5
    if ret1y > 40: scores["moat"] = max(scores["moat"] + 5, 18)
    scores["moat"] = min(20, scores["moat"])

    # Management
    if pe > 0:
        if pe < 15 and (profitGrowth > 10 or roe > 15): scores["management"] += 20
        elif pe < 25: scores["management"] += 10
        elif pe < 60: scores["management"] += 5
    else:
        if mcap > 50000:
            scores["management"] += 10
            reasons.append("Turnaround Giant")
        elif mcap > 10000:
            scores["management"] += 5
            reasons.append("Recovering")
    scores["management"] = min(20, scores["management"])

    # Risk
    if mcap > 0:
        if mcap < 500:
            scores["risk"] -= 10
            reasons.append("Micro Cap Risk")
        elif mcap > 5000: scores["risk"] += 10
        elif mcap > 2000: scores["risk"] += 5
        
    if ret1y > 40: scores["risk"] += 10
    else:
        if beta < 1.1: scores["risk"] += 10
        elif beta < 1.3: scores["risk"] += 5
    scores["risk"] = max(0, min(20, scores["risk"]))

    # Total
    scores["total"] = scores["business"] + scores["moat"] + scores["management"] + scores["risk"]

    if pe < 15 and roe > 15 and profitGrowth > 0:
        scores["total"] += 15
        reasons.append("High Quality Value")
    elif pe < 12 and profitGrowth > 10:
        scores["total"] += 10
        reasons.append("Deep Value")
        
    # Extract Ratios for UI
    ratios = {
        "pe": pe,
        "pb": safe_float(info.get('priceToBook')),
        "debtToEquity": safe_float(info.get('debtToEquity')) / 100 if info.get('debtToEquity') else 0,
        "divYield": safe_float(info.get('dividendYield'), 100),
        "roe": roe,
        "roce": roce,
        "salesGrowth": salesGrowth,
        "profitGrowth": profitGrowth
    }
    
    # Generate NLP Analysis
    nlp_texts = []
    if ratios["pe"] > 0:
        if ratios["pe"] < 15: nlp_texts.append(f"Trading at an attractive valuation with a P/E of {ratios['pe']}, indicating potential deep value.")
        elif ratios["pe"] > 40: nlp_texts.append(f"Commands a premium valuation (P/E {ratios['pe']}), suggesting high growth expectations from the market.")
        else: nlp_texts.append(f"Valuation appears reasonable at a P/E of {ratios['pe']}.")
        
    if ratios["roe"] > 15 and ratios["roce"] > 15:
        nlp_texts.append(f"Capital efficiency is stellar, boasting an ROE of {ratios['roe']}% and ROCE of {ratios['roce']}%, which points to a strong economic moat and pricing power.")
    elif ratios["roe"] > 0 and ratios["roe"] < 8:
        nlp_texts.append(f"Profitability is currently subdued, with ROE sitting at a low {ratios['roe']}%.")
        
    if ratios["debtToEquity"] is not None:
        if ratios["debtToEquity"] < 0.5: nlp_texts.append(f"The balance sheet is healthy with a minimal Debt-to-Equity ratio of {round(ratios['debtToEquity'], 2)}.")
        elif ratios["debtToEquity"] > 2.0: nlp_texts.append(f"Leverage is quite high (Debt/Equity: {round(ratios['debtToEquity'], 2)}), introducing potential risk.")
        
    if ratios["salesGrowth"] > 15: nlp_texts.append(f"Top-line expansion remains robust with {ratios['salesGrowth']}% sales growth.")
    elif ratios["salesGrowth"] < 0: nlp_texts.append(f"Facing headwinds, evidenced by a {abs(ratios['salesGrowth'])}% contraction in sales.")

    scores["ratios"] = ratios
    scores["nlp"] = " ".join(nlp_texts) if nlp_texts else "Insufficient fundamental data to generate a reliable AI analysis."

    scores["total"] = min(99, scores["total"])
    
    if reasons:
        scores["explanation"] = " & ".join(reasons[:2])
    else:
        scores["explanation"] = "Stable" if scores["total"] > 50 else "Weak"

    return scores

def calculate_porters_score(info):
    mcap = safe_float(info.get('marketCap') or info.get('enterpriseValue'), 1e-7)  # in Crores
    roce = safe_float(info.get('returnOnEquity')) * 100 # Approx proxy since ROCE isn't direct
    roe = safe_float(info.get('returnOnEquity')) * 100
    sales_growth = safe_float(info.get('revenueGrowth')) * 100
    profit_growth = safe_float(info.get('earningsGrowth')) * 100
    opm = safe_float(info.get('operatingMargins')) * 100

    p_score = {'entrants': 0, 'suppliers': 0, 'buyers': 0, 'substitutes': 0, 'rivalry': 0, 'total': 0}

    if mcap > 10000 and roce > 20: p_score['entrants'] = 20
    elif mcap > 5000 and roce > 15: p_score['entrants'] = 15
    elif mcap > 2000: p_score['entrants'] = 10
    else: p_score['entrants'] = 5

    if opm > 25: p_score['suppliers'] = 20
    elif opm > 18: p_score['suppliers'] = 15
    elif opm > 10: p_score['suppliers'] = 10
    else: p_score['suppliers'] = 5

    if roe > 22: p_score['buyers'] = 20
    elif roe > 16: p_score['buyers'] = 15
    elif roe > 12: p_score['buyers'] = 10
    else: p_score['buyers'] = 5

    if sales_growth > 15: p_score['substitutes'] = 20
    elif sales_growth > 10: p_score['substitutes'] = 15
    elif sales_growth > 5: p_score['substitutes'] = 10
    else: p_score['substitutes'] = 5

    if profit_growth > 15: p_score['rivalry'] = 20
    elif profit_growth > 10: p_score['rivalry'] = 15
    elif profit_growth > 0: p_score['rivalry'] = 10
    else: p_score['rivalry'] = 5

    p_score['total'] = min(99, sum(p_score.values()) - p_score['total'])
    return p_score

def main():
    if len(sys.argv) < 2:
        print("Usage: python fundamental_engine.py <symbol> [--is-holding]")
        sys.exit(1)
        
    symbol = sys.argv[1].upper()
    is_holding = 1 if "--is-holding" in sys.argv else 0
    db_path = "fundamentals.db"
    
    # Initialize DB
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Check if we need to recreate the table (missing is_holding column)
    c.execute("PRAGMA table_info(fundamentals)")
    columns = [col[1] for col in c.fetchall()]
    if "is_holding" not in columns:
        c.execute("DROP TABLE IF EXISTS fundamentals")
        
    c.execute('''
        CREATE TABLE IF NOT EXISTS fundamentals (
            symbol TEXT PRIMARY KEY,
            scores_json TEXT,
            last_updated DATETIME,
            is_holding INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    
    print(f"Fetching fundamental data for {symbol}...")
    
    # Format symbol for yfinance (append .NS if it's an Indian stock)
    yf_sym = symbol
    if not symbol.endswith(".NS") and not symbol.endswith(".BO"):
        yf_sym = f"{symbol}.NS"
        
    ticker = yf.Ticker(yf_sym)
    try:
        info = ticker.info
    except Exception as e:
        print(f"yfinance network error for {yf_sym}: {e}")
        c.execute("INSERT OR REPLACE INTO fundamentals VALUES (?, ?, ?, ?)", 
                  (symbol, json.dumps({"error": "Network timeout fetching data"}), datetime.now().isoformat(), is_holding))
        conn.commit()
        conn.close()
        sys.exit(0)
    
    if not info or ('regularMarketPrice' not in info and 'currentPrice' not in info and 'previousClose' not in info):
        print(f"Could not fetch reliable data for {yf_sym}")
        # Insert a failed record
        c.execute("INSERT OR REPLACE INTO fundamentals VALUES (?, ?, ?, ?)", 
                  (symbol, json.dumps({"error": "Data unavailable"}), datetime.now().isoformat(), is_holding))
        conn.commit()
        conn.close()
        sys.exit(0)
        
    scores = calculate_fundamental_score(info)
    scores['porters'] = calculate_porters_score(info)
    print(f"Calculated scores: {scores}")
    
    c.execute("INSERT OR REPLACE INTO fundamentals VALUES (?, ?, ?, ?)", 
              (symbol, json.dumps(scores), datetime.now().isoformat(), is_holding))
    conn.commit()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    main()
