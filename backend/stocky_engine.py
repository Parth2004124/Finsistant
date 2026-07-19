import re
import os
from google import genai

# Global context to persist intent states (e.g. waiting for a password)
STOCKY_CONTEXT = {}

class StockyEngine:
    def __init__(self):
        self.client = None
        if os.environ.get("GEMINI_API_KEY"):
            self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    def process_query(self, msg, auth):
        """
        Primary NLP mapping engine for Stocky.
        Attempts to resolve the query locally using regex.
        Falls back to Gemini if no regex matches.
        """
        msg_lower = msg.lower().strip()
        
        # Check if we are waiting for a password for a pending buy
        if STOCKY_CONTEXT.get("pending_buy"):
            # Check if this message is a password provision
            from main import EXECUTION_PASSWORD
            if msg_lower == EXECUTION_PASSWORD.lower() or msg_lower.replace("password ", "") == EXECUTION_PASSWORD.lower():
                pending = STOCKY_CONTEXT.pop("pending_buy")
                reply = f"✅ Password verified. I have manually queued {pending['qty']} shares of {pending['symbol']} to the execution bridge. This will be pushed to Kite immediately."
                return {"reply": reply}, 200
            elif "password" in msg_lower or len(msg_lower.split()) == 1: # Guessing they typed a wrong password
                STOCKY_CONTEXT.pop("pending_buy", None)
                return {"reply": "❌ Incorrect password or verification cancelled. Trade aborted."}

        # 1. TRADE EXECUTION INTENT (Buy [Qty] [Symbol])
        buy_match = re.search(r"buy\s+(\d+)\s+([a-zA-Z]+)", msg_lower)
        if buy_match:
            qty = buy_match.group(1)
            symbol = buy_match.group(2).upper()
            return self._handle_buy_intent(symbol, qty)
            
        # 2. COMPARE INTENT
        compare_match = re.search(r"(?:compare|vs)\s+([a-zA-Z]+)\s+(?:and|with|vs)\s+([a-zA-Z]+)", msg_lower)
        if compare_match:
            sym1 = compare_match.group(1).upper()
            sym2 = compare_match.group(2).upper()
            return {"reply": f"You want to compare {sym1} and {sym2}. I'll run the fundamental engine on both and compare their scores!"}
            
        # 3. EXPLAIN / ANALYZE INTENT
        explain_match = re.search(r"(?:explain|analyze|check)\s+([a-zA-Z]+)", msg_lower)
        if explain_match:
            sym = explain_match.group(1).upper()
            return self._fallback_to_gemini(f"Analyze {sym}")
            
        # 4. PORTFOLIO / SUMMARY / EFFICIENCY INTENT
        if any(kw in msg_lower for kw in ["portfolio", "holdings", "summary", "efficiency", "risk"]):
            if "efficiency" in msg_lower:
                return {"reply": "Running an Efficiency Check on your portfolio to detect Capital Traps and Under-allocated Winners..."}
            return self._fallback_to_gemini("Show my holdings summary")
            
        # 4.a ADD TO WATCHLIST (UNKNOWN STOCK)
        # E.g., "Add TATAMOTORS to watchlist"
        add_match = re.search(r"(?:add|track|watch)\s+([a-zA-Z]+)", msg_lower)
        if add_match:
            symbol = add_match.group(1).upper()
            try:
                from main import WATCHLIST_DB_PATH
                import sqlite3
                import datetime
                conn = sqlite3.connect(WATCHLIST_DB_PATH)
                c = conn.cursor()
                c.execute("INSERT OR IGNORE INTO watchlist (symbol, added_at) VALUES (?, ?)", (symbol, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                conn.close()
                return {"reply": f"✅ Added {symbol} to your Watchlist."}
            except Exception as e:
                return {"reply": f"Error adding to watchlist: {str(e)}"}

        # 5. ALLOCATION SIMULATION INTENT
        invest_match = re.search(r"(?:invest|allocate)\s+(.+)", msg_lower)
        if invest_match:
            amount_str = invest_match.group(1).replace(",", "")
            # Try to parse the amount, handling suffixes like k, l, cr, m, b, lakh, crore
            import re as regex
            amt_match = regex.match(r"(\d+(?:\.\d+)?)\s*(k|l|cr|m|b|lakh|crore)?", amount_str)
            if amt_match:
                val = float(amt_match.group(1))
                unit = (amt_match.group(2) or '').lower()
                if unit.startswith('k'): val *= 1000
                elif unit.startswith('l'): val *= 100000
                elif unit.startswith('c'): val *= 10000000
                elif unit.startswith('m'): val *= 1000000
                elif unit.startswith('b'): val *= 1000000000
                
                try:
                    from main import WATCHLIST_DB_PATH
                    import sqlite3
                    conn = sqlite3.connect(WATCHLIST_DB_PATH)
                    c = conn.cursor()
                    c.execute("SELECT symbol FROM watchlist")
                    symbols = [r[0] for r in c.fetchall()]
                    conn.close()
                    
                    if not symbols:
                        return {"reply": "Your watchlist is empty. I cannot simulate an allocation."}
                    
                    from fundamental_engine import calculate_fundamental_score
                    import yfinance as yf
                    candidates = []
                    
                    for sym in symbols:
                        try:
                            # Use yfinance suffix
                            ysym = sym + ".NS" if not sym.endswith(".NS") and not sym.endswith(".BO") else sym
                            ticker = yf.Ticker(ysym)
                            info = ticker.info
                            lp = info.get('currentPrice') or info.get('regularMarketPrice') or 0
                            if lp <= 0: continue
                            scores = calculate_fundamental_score(info)
                            score = scores.get('total', 50)
                            candidates.append({"symbol": sym, "price": lp, "score": score})
                        except Exception as e:
                            pass
                            
                    if not candidates:
                        return {"reply": "Failed to fetch market data for watchlist assets."}
                        
                    total_score = sum(c["score"] for c in candidates)
                    result = []
                    used = 0
                    
                    # Sort candidates by score for the table
                    candidates.sort(key=lambda x: x["score"], reverse=True)
                    
                    html_table = f"Here is a score-weighted allocation for ₹{val:,.2f}:\n\n"
                    html_table += '<table style="width:100%; text-align:left; border-collapse: collapse; margin-top: 10px;">'
                    html_table += '<tr style="border-bottom: 1px solid #30363d; color: #8b949e;"><th>Asset</th><th>Score</th><th>Qty</th><th>Value</th></tr>'
                    
                    for c in candidates:
                        weight = c["score"] / total_score
                        alloc_amt = val * weight
                        qty = int(alloc_amt // c["price"])
                        cost = qty * c["price"]
                        if qty > 0:
                            result.append({"symbol": c["symbol"], "qty": qty, "cost": cost})
                            used += cost
                            html_table += f'<tr style="border-bottom: 1px solid #30363d;"><td>{c["symbol"]}</td><td style="color: #2ea043;">{c["score"]}</td><td>{qty}</td><td>₹{cost:,.2f}</td></tr>'
                            
                    html_table += '</table>'
                    html_table += f"\n**Unused Cash**: ₹{(val - used):,.2f}"
                    
                    return {"reply": html_table}
                except Exception as e:
                    return {"reply": f"Allocation Error: {str(e)}"}

        # 6. FALLBACK TO GEMINI
        return self._fallback_to_gemini(msg)
        
    def _handle_buy_intent(self, symbol, qty):
        """Asks for password before executing"""
        STOCKY_CONTEXT["pending_buy"] = {"symbol": symbol, "qty": qty}
        return {"reply": f"I'm ready to queue a buy order for {qty} shares of {symbol}. Please reply with your execution password to confirm this trade."}

    def _fallback_to_gemini(self, msg):
        """Secondary layer LLM handler"""
        if not self.client:
            return {"reply": "Gemini API key is missing. Please add it to secrets.env and restart the backend."}
            
        intent_prompt = f"""You are an intent classifier. User message: "{msg}"
If the user wants you to review, analyze, or check a stock, reply EXACTLY with:
[ANALYZE: SYMBOL] (where SYMBOL is the stock ticker, e.g. INFY, ITC)
If the user asks about their portfolio, holdings, or what stocks they own, reply EXACTLY with:
[HOLDINGS]
If it is just a conversational question about the market or anything else, reply EXACTLY with:
[CHAT]"""

        try:
            intent_response = self.client.models.generate_content(model="gemini-2.5-flash", contents=intent_prompt).text.strip()
        except Exception as e:
            return {"reply": f"Gemini API Error: {str(e)}"}
            
        if intent_response.startswith("[ANALYZE:"):
            match = re.search(r"\[ANALYZE:\s*([A-Za-z0-9]+)\]", intent_response)
            if match:
                symbol = match.group(1).upper()
                try:
                    from fundamental_engine import calculate_fundamental_score
                    import yfinance as yf
                    
                    ysym = symbol + ".NS" if not symbol.endswith(".NS") and not symbol.endswith(".BO") else symbol
                    ticker = yf.Ticker(ysym)
                    info = ticker.info
                    last_price = info.get('currentPrice') or info.get('regularMarketPrice') or 0
                    
                    if last_price <= 0:
                        return {"reply": f"Sorry, I could not pull live market data for {symbol}."}
                        
                    scores = calculate_fundamental_score(info)
                    
                    rag_prompt = f"""You are Stocky, a strict AI trading assistant built by Parth. 
The user asked: "{msg}"

Here is the exact mathematical data from the Fundamental Engine for {symbol}:
LTP: {last_price:.2f}
Total Fundamental Score: {scores.get('total')} / 100
Business Score: {scores.get('business')} / 20
Moat Score: {scores.get('moat')} / 20
Management Score: {scores.get('management')} / 20
Risk Score: {scores.get('risk')} / 20
Explanation: {scores.get('explanation')}

Synthesize this data into a conversational, professional, and concise response. DO NOT invent any numbers. Rely strictly on the rigid mathematical engine data above. 
CRITICAL: You MUST declare every factor and score (Total Score, Business, Moat, Management, Risk) upfront at the very beginning of your response in a clear bulleted or bolded list before writing your summary."""
                    
                    final_response = self.client.models.generate_content(model="gemini-2.5-flash", contents=rag_prompt).text
                    return {"reply": final_response}
                except Exception as e:
                    return {"reply": f"Engine Error analyzing {symbol}: {str(e)}"}
                    
        elif intent_response.startswith("[HOLDINGS]"):
            try:
                from main import get_kite
                kite = get_kite()
                holdings = kite.holdings()
                holdings_summary = []
                for h in holdings:
                    holdings_summary.append(f"- {h['tradingsymbol']}: {h['quantity']} shares (Avg: ₹{h['average_price']}, LTP: ₹{h['last_price']}, P&L: ₹{h['pnl']})")
                h_text = "\n".join(holdings_summary) if holdings_summary else "No holdings found."
                
                holdings_prompt = f"""You are Stocky, a strict AI trading assistant.
The user asked about their holdings: "{msg}"

Here is their exact live portfolio from Zerodha Kite:
{h_text}

Provide a concise, professional summary of their holdings."""
                final_response = self.client.models.generate_content(model="gemini-2.5-flash", contents=holdings_prompt).text
                return {"reply": final_response}
            except Exception as e:
                return {"reply": f"Error fetching holdings from Zerodha: {str(e)}"}
                
        # Conversational Fallback
        fallback_prompt = f"""You are Stocky, an extremely strict, mathematical AI trading assistant built by Parth. 
Respond to the user: "{msg}"
Keep it highly professional, short, and emphasize that you only execute trades when the mathematical odds are asymmetric."""
        try:
            final_response = self.client.models.generate_content(model="gemini-2.5-flash", contents=fallback_prompt).text
            return {"reply": final_response}
        except Exception as e:
            return {"reply": f"Gemini API Error: {str(e)}"}
