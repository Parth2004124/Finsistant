from flask import Flask, request, jsonify, send_from_directory
from kiteconnect import KiteConnect
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_url_path='/static', static_folder=static_dir)

from dashboard_api import techsight_bp
app.register_blueprint(techsight_bp)

API_KEY = "dn5f72ctu7ey0jtr"
ACCESS_TOKEN_FALLBACK = "FZVCRXLIn0o5tYhMQjYHRMNwb51PQGfP"
SECRET_KEY = "my_super_secret_trading_key"

def get_access_token():
    token_path = os.path.join(BASE_DIR, 'token.txt')
    if os.path.exists(token_path):
        with open(token_path, 'r') as f:
            return f.read().strip()
    return ACCESS_TOKEN_FALLBACK

@app.route("/")
def serve_dashboard():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/api/holdings", methods=["GET"])
def get_holdings():
    try:
        kite = KiteConnect(api_key=API_KEY)
        kite.set_access_token(get_access_token())
        return jsonify({"status": "success", "data": kite.holdings()})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

@app.route("/api/order", methods=["POST"])
def place_order():
    try:
        req = request.json
        kite = KiteConnect(api_key=API_KEY)
        kite.set_access_token(get_access_token())
        
        tt = kite.TRANSACTION_TYPE_BUY if req.get("transaction_type", "").upper() == "BUY" else kite.TRANSACTION_TYPE_SELL
        variety = kite.VARIETY_AMO if req.get("is_amo") else kite.VARIETY_REGULAR
        ot = kite.ORDER_TYPE_LIMIT if req.get("order_type", "").upper() == "LIMIT" else kite.ORDER_TYPE_MARKET
        
        order_id = kite.place_order(
            variety=variety,
            exchange=req.get("exchange", "BSE"),
            tradingsymbol=req.get("tradingsymbol"),
            transaction_type=tt,
            quantity=req.get("quantity"),
            price=req.get("price", 0.0),
            product=kite.PRODUCT_CNC,
            order_type=ot
        )
        return jsonify({"status": "success", "order_id": order_id})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

@app.route("/api/update_token", methods=["POST"])
def update_token():
    req = request.json
    if req.get("secret") != SECRET_KEY:
        return jsonify({"status": "error", "detail": "Unauthorized"}), 401
    
    new_token = req.get("token")
    if not new_token:
        return jsonify({"status": "error", "detail": "No token provided"}), 400
        
    token_path = os.path.join(BASE_DIR, 'token.txt')
    with open(token_path, 'w') as f:
        f.write(new_token)
        
    return jsonify({"status": "success", "message": "Token updated successfully"})

if __name__ == "__main__":
    import uvicorn
    # Listen on all interfaces so the Android emulator or physical phone can reach it
    uvicorn.run(app, host="0.0.0.0", port=8000)
