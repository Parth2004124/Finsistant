import math

class PortfolioAllocationEngine:
    def __init__(self):
        self.MAX_CAPITAL_PER_STOCK = 5000.0
        # In a real system, we'd fetch actual available capital from Zerodha:
        # self.available_capital = get_kite().margins()['equity']['net']
        self.mock_available_capital = 100000.0 
        
    def calculate_allocation(self, symbol: str, technical_score: float, confidence: float, current_price: float) -> dict:
        """
        Agent 2 Requirements:
        - Portfolio Allocation separates capital allocation from the analysis engine.
        - Never exceed Rs 5000 per stock.
        """
        
        # 1. Allocation Amount Decision
        # Even if we have 1,00,000, we strictly cap at 5,000 to ensure diversification.
        # Future improvement: We could scale down the 5,000 limit if confidence is very low, 
        # but the hard cap is strictly enforced here.
        allocation_amount = min(self.mock_available_capital, self.MAX_CAPITAL_PER_STOCK)
        
        # 2. Position Sizing
        if current_price <= 0:
            quantity = 0
        else:
            quantity = math.floor(allocation_amount / current_price)
            
        return {
            "symbol": symbol,
            "allocation_amount": allocation_amount,
            "calculated_quantity": quantity,
            "max_position_size": self.MAX_CAPITAL_PER_STOCK,
            "portfolio_weight": (allocation_amount / self.mock_available_capital) if self.mock_available_capital > 0 else 0
        }
