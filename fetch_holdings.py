from kiteconnect import KiteConnect
import os
from dotenv import load_dotenv

load_dotenv('secrets.env')
kite = KiteConnect(api_key=os.environ.get('KITE_API_KEY'))
kite.set_access_token('FcGa5JXkQ7yD9NH3WlZEKtzPVj3Zqs3Z')

holdings = kite.holdings()
print('HOLDINGS:')
for h in holdings:
    print(f"{h['tradingsymbol']}: {h['quantity']} shares, Avg: {h['average_price']}, LTP: {h['last_price']}, PnL: {h['pnl']}")
