import sys
import json
import sqlite3
import yfinance as yf
import numpy as np
import google.generativeai as genai
import os
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

# Configure Gemini
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    try:
        with open("token.txt", "r") as f:
            API_KEY = f.read().strip()
    except:
        pass
genai.configure(api_key=API_KEY)

WATCHLIST_DB_PATH = "watchlist.db"

def run_quant_analysis(symbol):
    print(f"Starting Quantitative CFA Analysis for {symbol}...")
    
    # 1. Fetch Fundamental Data
    ticker = yf.Ticker(f"{symbol}.NS")
    info = ticker.info
    
    metrics = {
        "P/E Ratio": info.get("trailingPE", "N/A"),
        "Forward P/E": info.get("forwardPE", "N/A"),
        "P/B Ratio": info.get("priceToBook", "N/A"),
        "Debt to Equity": info.get("debtToEquity", "N/A"),
        "ROE": info.get("returnOnEquity", "N/A"),
        "ROA": info.get("returnOnAssets", "N/A"),
        "Free Cash Flow": info.get("freeCashflow", "N/A"),
        "Operating Margin": info.get("operatingMargins", "N/A"),
        "Profit Margin": info.get("profitMargins", "N/A"),
        "Current Ratio": info.get("currentRatio", "N/A"),
        "Beta": info.get("beta", "N/A"),
        "52W High": info.get("fiftyTwoWeekHigh", "N/A"),
        "52W Low": info.get("fiftyTwoWeekLow", "N/A"),
        "Dividend Yield": info.get("dividendYield", "N/A"),
    }
    
    # 2. Fetch Historical Price Data (1 Year)
    hist = ticker.history(period="1y")
    if hist.empty:
        raise ValueError("No historical data found for symbol.")
        
    prices = hist['Close'].values
    dates = hist.index
    
    # 3. Quantitative Regression (Polynomial Degree 2 for trend curving)
    X = np.arange(len(prices)).reshape(-1, 1)
    y = prices
    
    # Polynomial Regression
    poly = PolynomialFeatures(degree=2)
    X_poly = poly.fit_transform(X)
    model = LinearRegression()
    model.fit(X_poly, y)
    y_pred = model.predict(X_poly)
    
    # Calculate Standard Deviation for Support/Resistance Channels
    std_dev = np.std(y - y_pred)
    
    # Project 30 days into the future
    future_X = np.arange(len(prices), len(prices) + 30).reshape(-1, 1)
    future_X_poly = poly.transform(future_X)
    future_pred = model.predict(future_X_poly)
    
    # Format Regression Data for Lightweight Charts
    regression_points = []
    # Start projection from last 30 days of actual data to show continuity
    for i in range(len(prices) - 30, len(prices)):
        date_str = dates[i].strftime("%Y-%m-%d")
        regression_points.append({
            "time": date_str,
            "value": float(y_pred[i]),
            "upper": float(y_pred[i] + std_dev),
            "lower": float(y_pred[i] - std_dev)
        })
        
    last_date = dates[-1]
    for i in range(30):
        future_date = last_date + timedelta(days=i+1)
        # Skip weekends roughly
        if future_date.weekday() < 5:
            regression_points.append({
                "time": future_date.strftime("%Y-%m-%d"),
                "value": float(future_pred[i]),
                "upper": float(future_pred[i] + std_dev),
                "lower": float(future_pred[i] - std_dev)
            })
            
    # 4. Generate CFA-Level Report using Gemini
    prompt = f"""
    You are a Chartered Financial Analyst (CFA) performing a deep-dive quantitative and fundamental analysis on {symbol} (Indian Stock Market).
    
    Here are the core quantitative and fundamental metrics extracted today:
    {json.dumps(metrics, indent=2)}
    
    Quantitative Regression Analysis (Polynomial Degree 2 over 1 Year):
    - Current Price: {prices[-1]:.2f}
    - Trend: {"Upward Curve" if model.coef_[2] > 0 else "Downward Curve"}
    - Projected 30-Day Target (Regression Line): {future_pred[-1]:.2f}
    - Standard Deviation (Volatility Channel): {std_dev:.2f}
    
    The user wants a highly visual and concise summary that includes rich charting data. Do NOT output a wall of text.
    You must output EXACTLY a valid JSON object matching this schema, without any markdown formatting (do NOT wrap in ```json ... ```):
    {{
      "detailed_analysis": "Provide a comprehensive 2-paragraph CFA verdict on the stock's quantitative and fundamental setup. Discuss the trend, standard deviation, valuation context (P/E, ROE), and risk-reward conviction.",
      "kpis": [
        {{ "label": "Trend", "value": "Strong Upward", "color": "#238636" }},
        {{ "label": "Valuation", "value": "Overvalued", "color": "#ff5f56" }},
        {{ "label": "30D Target", "value": "1350", "color": "#1e90ff" }},
        {{ "label": "Risk/Reward", "value": "Favorable", "color": "#238636" }}
      ],
      "doughnut_chart": [
        {{ "name": "Bullish", "value": 65, "fill": "#238636" }},
        {{ "name": "Neutral", "value": 20, "fill": "#1e90ff" }},
        {{ "name": "Bearish", "value": 15, "fill": "#ff5f56" }}
      ],
      "bar_chart": [
        {{ "name": "Current P/E", "value": 25, "fill": "#8b949e" }},
        {{ "name": "Forward P/E", "value": 22, "fill": "#58a6ff" }},
        {{ "name": "ROE", "value": 15, "fill": "#d2a8ff" }}
      ]
    }}
    
    Rules for JSON generation:
    1. Provide exactly 4 to 6 KPIs with hex colors based on sentiment.
    2. Provide exactly 3 entries in `doughnut_chart` representing conviction probabilities (must sum to 100), keeping the exact fill colors from the schema.
    3. Provide exactly 3 to 5 key financial metrics in `bar_chart` comparing valuations or growth, filling them with visually distinct cool/neutral colors. Choose the most relevant metrics from the provided data. Convert string values (like "15.4%") to plain numbers (like 15.4) for the chart "value" field.
    4. Output ONLY the raw JSON string. Do NOT add markdown tags.
    """
    
    model_ai = genai.GenerativeModel('gemini-2.5-flash')
    response = model_ai.generate_content(prompt)
    report = response.text.strip()

    
    # Strip markdown if Gemini accidentally included it
    if report.startswith("```json"):
        report = report[7:]
    if report.endswith("```"):
        report = report[:-3]
    report = report.strip()

    
    # 5. Save to Database
    conn = sqlite3.connect(WATCHLIST_DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE watchlist SET quant_report = ?, regression_points = ? WHERE symbol = ?",
        (report, json.dumps(regression_points), symbol)
    )
    conn.commit()
    conn.close()
    
    print(f"Successfully generated and saved CFA Quantitative Analysis for {symbol}.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python quant_analyzer.py <SYMBOL>")
        sys.exit(1)
    
    symbol = sys.argv[1]
    run_quant_analysis(symbol)
