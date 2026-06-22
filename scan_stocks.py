import sys
import os
import yfinance as yf

BASE_DIR = os.path.dirname(os.path.abspath('test_live.py'))
sys.path.append(os.path.join(BASE_DIR, 'TechSight', 'core'))
sys.path.append(os.path.join(BASE_DIR, 'TechSight', 'data_engine'))
sys.path.append(os.path.join(BASE_DIR, 'TechSight', 'agents'))

from data_fetcher import DataFetcher
from scoring_engine import ScoringEngine

engine = ScoringEngine()
fetcher = DataFetcher()

symbols = ['HDFCBANK', 'INFY', 'TCS', 'SBIN', 'BHARTIARTL', 'LT', 'ITC', 'RELIANCE', 'ICICIBANK', 'HINDUNILVR']

best_score = 0
best_sym = ''

for sym in symbols:
    try:
        market_data = fetcher.fetch_historical_data(sym)
        df_daily = market_data['daily']
        df_weekly = market_data['weekly']
        
        yf_sym = f'{sym}.NS'
        last_price = yf.Ticker(yf_sym).history(period='1d')['Close'].iloc[-1]
        
        result = engine.evaluate(sym, last_price, df_daily, df_weekly)
        print(f'{sym}: {result["confidence"]}')
        if result['confidence'] > best_score:
            best_score = result['confidence']
            best_sym = sym
    except Exception as e:
        print(f'Error evaluating {sym}: {e}')

print(f'\nBEST STOCK: {best_sym} with confidence {best_score}')
