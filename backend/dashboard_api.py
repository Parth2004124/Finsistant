from fastapi import FastAPI, APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Initialize the router for TechSight dashboard endpoints
techsight_router = APIRouter(prefix="/api/techsight", tags=["techsight"])

# Pydantic Models for the Dashboard
class TradeSetup(BaseModel):
    id: str
    symbol: str
    date_generated: str
    setup_type: str # e.g., "Breakout", "Mean Reversion"
    logic_explanation: str # Plain-English explanation
    technical_score: float
    confidence_score: float
    entry_price: float
    stop_loss: float
    target: float
    risk_reward: float
    status: str # "PENDING_APPROVAL", "APPROVED", "REJECTED", "AUTO_APPROVED"

class EngineStatus(BaseModel):
    is_running: bool
    current_phase: str
    last_scan_time: str
    total_symbols_scanned: int
    pending_approvals_count: int

# Mock Database for testing the Android UI
MOCK_PENDING_TRADES = [
    TradeSetup(
        id="TRD-001",
        symbol="TCS",
        date_generated=datetime.now().strftime("%Y-%m-%d"),
        setup_type="Breakout",
        logic_explanation="Technical Score: 89/100. Strong Daily Breakout with 1.8x Average Volume. Weekly trend aligns bullish. Sector (IT) RS > 1.",
        technical_score=89.0,
        confidence_score=92.5,
        entry_price=4100.0,
        stop_loss=3950.0,
        target=4550.0,
        risk_reward=3.0,
        status="PENDING_APPROVAL"
    ),
    TradeSetup(
        id="TRD-002",
        symbol="HDFCBANK",
        date_generated=datetime.now().strftime("%Y-%m-%d"),
        setup_type="Mean Reversion",
        logic_explanation="Technical Score: 78/100. Extreme oversold on RSI (14) with positive MACD divergence at major Weekly Support zone.",
        technical_score=78.0,
        confidence_score=75.0,
        entry_price=1450.0,
        stop_loss=1410.0,
        target=1570.0,
        risk_reward=3.0,
        status="PENDING_APPROVAL"
    )
]

@techsight_router.get("/status", response_model=EngineStatus)
async def get_engine_status():
    """
    Returns the real-time health and execution status of the TechSight engine.
    Used by the Android Dashboard to show the "Live Progress" ring.
    """
    return EngineStatus(
        is_running=False,
        current_phase="IDLE (Awaiting EOD)",
        last_scan_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_symbols_scanned=500,
        pending_approvals_count=len(MOCK_PENDING_TRADES)
    )

@techsight_router.get("/approvals", response_model=List[TradeSetup])
async def get_pending_approvals():
    """
    Returns the list of trades waiting for human-in-the-loop authorization.
    """
    return MOCK_PENDING_TRADES

@techsight_router.post("/approvals/authorize")
async def authorize_batch(trade_ids: List[str]):
    """
    Called by the Android App when the user hits 'Approve Batch'.
    Transitions trades from PENDING_APPROVAL to queued Kite limits.
    """
    return {"status": "success", "message": f"Authorized {len(trade_ids)} trades for Kite execution."}
