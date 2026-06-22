import os
import sys
import pandas as pd
import itertools

# Setup paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, 'core'))
sys.path.append(os.path.join(BASE_DIR, 'data_engine'))

from scoring_engine import ScoringEngine
from data_fetcher import DataFetcher

class Agent3Tester:
    def __init__(self):
        self.fetcher = DataFetcher()
        self.engine = ScoringEngine()
        
    def run_backtest(self, symbols: list, weights: dict, min_score: float = 80.0, min_rr: float = 2.0):
        """
        Runs a historical simulation on a list of symbols using specific weights.
        Returns metrics dict.
        """
        # Temporarily override the engine's weights
        self.engine.weights = weights
        
        trades = []
        
        for symbol in symbols:
            market_data = self.fetcher.fetch_historical_data(symbol, period="1y")
            df_daily = market_data["daily"]
            
            if df_daily.empty:
                continue
                
            # Pre-calculate weekly to save time
            df_weekly_full = market_data["weekly"]
            
            # Start from day 50 to ensure MAs have data
            for i in range(50, len(df_daily) - 10):
                current_date = df_daily.index[i]
                slice_daily = df_daily.iloc[:i+1]
                
                # Sliced weekly (up to the current week)
                slice_weekly = df_weekly_full[df_weekly_full.index <= current_date]
                if slice_weekly.empty:
                    continue
                    
                current_price = slice_daily['Close'].iloc[-1]
                
                # Evaluate
                result = self.engine.evaluate(symbol, current_price, df_daily=slice_daily, df_weekly=slice_weekly)
                if not result:
                    continue
                    
                score = result["technical_score"]
                rr = result["rr_ratio"]
                
                if score >= min_score and rr >= min_rr:
                    # Signal Generated. Simulate Forward.
                    forward_data = df_daily.iloc[i+1:]
                    entry_price = current_price
                    stop_loss = result["stop_loss"]
                    target = result["target"]
                    
                    outcome = self._simulate_forward(forward_data, entry_price, stop_loss, target)
                    if outcome:
                        trades.append(outcome)
                        
        if not trades:
            return {"win_rate": 0, "total_pnl": 0, "trades": 0}
            
        wins = sum(1 for t in trades if t["win"])
        total_pnl = sum(t["pnl_pct"] for t in trades)
        
        return {
            "win_rate": (wins / len(trades)) * 100,
            "total_pnl": total_pnl,
            "trades": len(trades)
        }

    def _simulate_forward(self, forward_data: pd.DataFrame, entry: float, stop: float, target: float):
        """
        Looks at forward daily data to see if Stop or Target was hit first.
        """
        for _, row in forward_data.iterrows():
            high = row['High']
            low = row['Low']
            
            # Check target first (optimistic)
            if high >= target:
                return {"win": True, "pnl_pct": ((target - entry) / entry) * 100}
            # Check stop loss
            if low <= stop:
                return {"win": False, "pnl_pct": ((stop - entry) / entry) * 100}
                
        # If neither hit, mark as neutral or slightly negative holding cost
        return None

    def optimize(self, symbols: list):
        """
        Runs a grid search over possible weight configurations to find the highest win rate.
        """
        print(f"Starting Optimization Engine across {len(symbols)} symbols...")
        
        # Test 3 different weight configurations
        test_configs = [
            # Config 1: Balanced (Current)
            {"Structure": 0.25, "Volume": 0.20, "MTF": 0.15, "Momentum": 0.10, "Pattern": 0.10, "RS": 0.10, "Volatility": 0.10},
            # Config 2: High Structure & Trend focus
            {"Structure": 0.35, "Volume": 0.15, "MTF": 0.20, "Momentum": 0.10, "Pattern": 0.05, "RS": 0.10, "Volatility": 0.05},
            # Config 3: Breakout / Momentum focus
            {"Structure": 0.15, "Volume": 0.30, "MTF": 0.10, "Momentum": 0.20, "Pattern": 0.05, "RS": 0.05, "Volatility": 0.15}
        ]
        
        best_win_rate = 0
        best_config = test_configs[0]
        
        for idx, weights in enumerate(test_configs):
            print(f"\nEvaluating Config {idx + 1}...")
            metrics = self.run_backtest(symbols, weights, min_score=65.0, min_rr=2.0)
            print(f"Results: {metrics['trades']} trades | Win Rate: {metrics['win_rate']:.1f}% | Total PnL: {metrics['total_pnl']:.2f}%")
            
            if metrics["win_rate"] > best_win_rate and metrics["trades"] > 0:
                best_win_rate = metrics["win_rate"]
                best_config = weights
                
        print("\n=== OPTIMIZATION COMPLETE ===")
        print(f"Best Configuration Win Rate: {best_win_rate:.1f}%")
        print("Optimal Weights:")
        for k, v in best_config.items():
            print(f"  {k}: {v}")
        return best_config

if __name__ == "__main__":
    tester = Agent3Tester()
    symbols = ["RELIANCE", "HDFCBANK", "TCS", "INFY", "ITC"]
    tester.optimize(symbols)
