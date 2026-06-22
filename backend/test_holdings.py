from main import get_kite
import sys
try:
    kite = get_kite()
    print("Kite obj:", kite)
    hold = kite.holdings()
    print("HOLDINGS:", hold)
except Exception as e:
    print("EXCEPTION:", str(e))
sys.stdout.flush()
