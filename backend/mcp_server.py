import os
import json
import requests
import subprocess
from mcp.server.fastmcp import FastMCP
from kiteconnect import KiteConnect

# Create the MCP server
mcp = FastMCP("Zerodha")

API_KEY = "dn5f72ctu7ey0jtr"

def get_kite():
    token_path = os.path.join(os.path.dirname(__file__), 'token.txt')
    token = open(token_path).read().strip() if os.path.exists(token_path) else ""
    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(token)
    return kite

@mcp.tool()
def get_holdings() -> str:
    """Fetch current portfolio holdings from Zerodha."""
    try:
        kite = get_kite()
        return json.dumps(kite.holdings(), indent=2)
    except Exception as e:
        return f"Error fetching holdings: {e}"

@mcp.tool()
def get_positions() -> str:
    """Fetch today's open positions from Zerodha."""
    try:
        kite = get_kite()
        return json.dumps(kite.positions(), indent=2)
    except Exception as e:
        return f"Error fetching positions: {e}"

@mcp.tool()
def queue_order(
    tradingsymbol: str, exchange: str, transaction_type: str, price: float, 
    setup_type: str, technical_score: float, confidence: float,
    why_lucrative: str, entry_zone: float, stop_loss: float, target: float, rr_ratio: float,
    expected_hold_days: str, key_risks: str, market_context: str,
    structure_score: int, volume_score: int, mtf_score: int, 
    order_type: str = "LIMIT", is_amo: bool = False
) -> str:
    """
    Queue an order through the Finsistant Dashboard Pipeline.
    Quantity is NOT determined here - the backend's Portfolio Allocation Engine will calculate it.
    You MUST provide strict technical analysis outputs for the rule engine.
    """
    try:
        payload = {
            "tradingsymbol": tradingsymbol,
            "exchange": exchange,
            "transaction_type": transaction_type,
            "price": price,
            "order_type": order_type,
            "is_amo": is_amo,
            "setup_type": setup_type,
            "technical_score": technical_score,
            "confidence": confidence,
            "score_breakdown": {
                "Structure": structure_score,
                "Volume": volume_score,
                "MTF": mtf_score
            },
            "why_lucrative": why_lucrative,
            "entry_zone": entry_zone,
            "stop_loss": stop_loss,
            "target": target,
            "rr_ratio": rr_ratio,
            "expected_hold_days": expected_hold_days,
            "key_risks": key_risks,
            "market_context": market_context
        }
        resp = requests.post("http://127.0.0.1:8000/api/order", json=payload)
        return f"Order queued successfully! Response: {resp.text}"
    except Exception as e:
        return f"Failed to queue order: {e}"

@mcp.tool()
def trigger_market_sweep(is_amo: bool = True) -> str:
    """
    Triggers the TechSight Orchestrator to scan the market for new setups.
    is_amo: If True, scans for end-of-day setups and queues them as AMOs for manual review. 
            If False, runs an intraday scan for immediate live auto-execution.
    """
    try:
        orchestrator_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "techsight_orchestrator.py")
        cmd = ["python", orchestrator_path]
        if is_amo:
            cmd.append("--amo")
            
        subprocess.Popen(cmd) # Run non-blocking
        return "Market sweep initiated in the background! Any found trades will appear in your queue."
    except Exception as e:
        return f"Failed to start scan: {e}"

@mcp.tool()
def get_pending_queue() -> str:
    """Fetches all trades currently waiting for human approval in the Finsistant queue."""
    try:
        resp = requests.get("http://127.0.0.1:8000/api/queue")
        return json.dumps(resp.json(), indent=2)
    except Exception as e:
        return f"Failed to fetch queue: {e}"

@mcp.tool()
def approve_trade(trade_id: str) -> str:
    """
    Manually approve a specific trade from the pending queue to fire it to Zerodha.
    trade_id: e.g. 'TRD-12345678'
    """
    try:
        payload = {"trade_ids": [trade_id]}
        resp = requests.post("http://127.0.0.1:8000/api/approve", json=payload)
        return resp.text
    except Exception as e:
        return f"Failed to approve trade: {e}"

if __name__ == "__main__":
    mcp.run(transport='stdio')
