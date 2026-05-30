import sys

# Redirect stdout and stderr to prevent pythonw.exe crashes on Windows
sys.stdout = open('dashboard.log', 'w')
sys.stderr = open('dashboard_err.log', 'w')

from flask import Blueprint, jsonify, request
from datetime import datetime

techsight_bp = Blueprint('techsight_bp', __name__, url_prefix='/api/techsight')

MOCK_PENDING_TRADES = [
    {
        "id": "TRD-001",
        "symbol": "TCS",
        "date_generated": datetime.now().strftime("%Y-%m-%d"),
        "setup_type": "Breakout",
        "logic_explanation": "Technical Score: 89/100. Strong Daily Breakout with 1.8x Average Volume. Weekly trend aligns bullish. Sector (IT) RS > 1.",
        "technical_score": 89.0,
        "confidence_score": 92.5,
        "entry_price": 4100.0,
        "stop_loss": 3950.0,
        "target": 4550.0,
        "risk_reward": 3.0,
        "status": "PENDING_APPROVAL"
    },
    {
        "id": "TRD-002",
        "symbol": "HDFCBANK",
        "date_generated": datetime.now().strftime("%Y-%m-%d"),
        "setup_type": "Mean Reversion",
        "logic_explanation": "Technical Score: 78/100. Extreme oversold on RSI (14) with positive MACD divergence at major Weekly Support zone.",
        "technical_score": 78.0,
        "confidence_score": 75.0,
        "entry_price": 1450.0,
        "stop_loss": 1410.0,
        "target": 1570.0,
        "risk_reward": 3.0,
        "status": "PENDING_APPROVAL"
    }
]

@techsight_bp.route("/status", methods=["GET"])
def get_engine_status():
    return jsonify({
        "is_running": False,
        "current_phase": "IDLE (Awaiting EOD)",
        "last_scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_symbols_scanned": 500,
        "pending_approvals_count": len(MOCK_PENDING_TRADES)
    })

@techsight_bp.route("/approvals", methods=["GET"])
def get_pending_approvals():
    return jsonify(MOCK_PENDING_TRADES)

@techsight_bp.route("/approvals/authorize", methods=["POST"])
def authorize_batch():
    req = request.json or {}
    trade_ids = req.get("trade_ids", [])
    return jsonify({"status": "success", "message": f"Authorized {len(trade_ids)} trades for Kite execution."})
