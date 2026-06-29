import sys
import os
import time
import requests
from datetime import datetime
import logging

# Set up logging for the new Orchestrator
logging.basicConfig(
    filename='karnos_orchestrator.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("KarnosOrchestrator")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# Import the existing technical scanner
from techsight_orchestrator import run_scan
from chart_generator import generate_karnos_charts

def generate_charts(stock_symbol):
    """
    Stage 3: Generate 3 standardized charts for Karnos.
    """
    logger.info(f"Generating standardized charts for {stock_symbol}...")
    return generate_karnos_charts(stock_symbol)

from karnos_client import send_charts_to_karnos

def analyze_with_karnos(stock_symbol, charts):
    """
    Stage 4: Send charts to Karnos AI.
    Uses the external karnos_client module which implements strict fault tolerance.
    """
    return send_charts_to_karnos(stock_symbol, charts)

def merge_decisions(tech_trade, karnos_result):
    """
    Stage 6: Merge technical analysis with Karnos prediction.
    """
    logger.info(f"Fusing decisions for {tech_trade['tradingsymbol']}...")
    fused_trade = tech_trade.copy()
    fused_trade["karnos_confidence"] = karnos_result.get("confidence", 0)
    fused_trade["karnos_direction"] = karnos_result.get("direction", "UNKNOWN")
    fused_trade["karnos_explanation"] = karnos_result.get("explanation", "")
    
    # Calculate combined confidence (Example: Average of tech and Karnos)
    tech_conf = fused_trade.get("confidence", 0)
    fused_trade["combined_confidence"] = (tech_conf + fused_trade["karnos_confidence"]) / 2
    
    return fused_trade

def push_async_update(fused_trade):
    """
    Stage 7 (Async): Update the pre-existing trade on the Flask backend with Karnos validation.
    """
    trade_id = fused_trade.get("trade_id")
    if not trade_id:
        logger.error(f"Cannot update trade for {fused_trade.get('tradingsymbol')} - no trade_id found!")
        return

    logger.info(f"Async update for {fused_trade['tradingsymbol']} (ID: {trade_id}) to API...")
    try:
        resp = requests.put(f"http://127.0.0.1:8000/api/order/{trade_id}", json=fused_trade)
        if resp.status_code == 200:
            logger.info(f"Successfully updated UI for {fused_trade['tradingsymbol']} with Karnos data.")
        else:
            logger.error(f"Failed to update API for {fused_trade['tradingsymbol']}: {resp.text}")
    except Exception as e:
        logger.error(f"Could not connect to update API for {fused_trade['tradingsymbol']}: {e}")

def run_master_pipeline(is_amo):
    logger.info(f"--- STARTED KARNOS ORCHESTRATOR PIPELINE --- (AMO: {is_amo})")
    
    # 1. Execute Technical Scanner
    logger.info("Executing Stage 2: TechSight Scanner...")
    # We will modify techsight_orchestrator to return trades instead of posting them
    top_trades, sell_suggestions = run_scan(is_amo, push_to_api=True)
    
    logger.info(f"Received {len(top_trades)} buy candidates and {len(sell_suggestions)} sell candidates.")
    
    all_trades = top_trades + sell_suggestions
    
    for trade in all_trades:
        sym = trade['tradingsymbol']
        try:
            # 2. Generate Charts
            charts = generate_charts(sym)
            
            # 3. Karnos Analysis (With Fault Tolerance)
            logger.info(f"Executing Stage 4 & 5: Karnos Integration for {sym}...")
            karnos_result = None
            try:
                # Mock timeout logic wrapped in try-catch
                karnos_result = analyze_with_karnos(sym, charts)
            except Exception as karnos_err:
                logger.warning(f"Karnos AI failed for {sym}: {karnos_err}. Falling back to technical-only.")
                
            # 4. Merge Decisions
            if karnos_result:
                final_trade = merge_decisions(trade, karnos_result)
            else:
                final_trade = trade # Fallback to original technical trade
                
            # 5. Push Async Update to UI
            push_async_update(final_trade)
            
        except Exception as e:
            logger.error(f"Critical error processing pipeline for {sym}: {e}")
            
    logger.info("--- ORCHESTRATOR PIPELINE COMPLETE ---")

if __name__ == "__main__":
    is_amo = "--amo" in sys.argv
    run_master_pipeline(is_amo)
