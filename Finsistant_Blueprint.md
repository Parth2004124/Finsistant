# Finsistant System Blueprint & Documentation

This document serves as the comprehensive architectural blueprint and user guide for **Finsistant**, an advanced algorithmic trading assistant and portfolio execution terminal.

---

## 1. Product Requirements Document (PRD)

### 1.1 Overview
Finsistant is a locally-hosted, highly automated algorithmic trading terminal designed to bridge the gap between technical stock screening and actual trade execution. It utilizes Large Language Models (LLMs) to score technical setups, calculates optimal risk-reward entry zones, and seamlessly executes orders via the Zerodha Kite API.

### 1.2 Target Audience
Active algorithmic and discretionary traders who want a centralized dashboard to review AI-generated trade setups, verify technical charts, and execute orders with 1-click execution bypassing manual broker terminal entry.

### 1.3 Key Features
- **TechSight Orchestrator:** A Python engine that scans technical data, feeds it to Google's Gemini Pro LLM, and generates highly structured, deterministic JSON trade setups (Score, Rationale, Entry, Stop Loss, Target).
- **Execution Terminal UI:** A sleek, dark-mode React frontend that acts as a mission control dashboard. It displays pending buys/sells, a portfolio summary, and a lightweight chart.
- **Kite Connect Integration:** Seamlessly routes approved trades directly to your Zerodha account using automated token extraction via Selenium, allowing for headless broker interaction.
- **Auto-Risk Calculation:** Automatically sizes positions (Quantity) based on a fixed risk appetite derived from the distance between the entry price and the stop loss.
- **Finsistant AI Chatbot:** A built-in LLM interface to query portfolio status or manually override/execute trades via natural language commands.
- **CORS Fallback Charting:** Fetches real weekly OHLC data from Yahoo Finance directly in the browser using a robust multi-proxy fallback loop, eliminating the need for a backend data bridge.

### 1.4 Non-Functional Requirements
- **Security:** Trade execution is gated by a secure environment variable execution password.
- **Resilience:** If the primary Selenium web-scraper fails to login to Kite, it gracefully falls back to a locally saved `token.txt` or a hardcoded emergency access token.

---

## 2. Tech Stack & Dependencies

Finsistant operates on a decoupled client-server architecture.

### 2.1 Frontend (React / Vite)
- **Framework:** React + Vite. Hosted locally or via GitHub Pages.
- **Styling:** Vanilla CSS (`index.css`) designed to mimic a professional Bloomberg-style dark terminal.
- **Charting:** `lightweight-charts` by TradingView for rendering local OHLC weekly candle charts with horizontal price lines indicating Targets, Entries, and Stop Losses.
- **Proxies:** Uses `api.allorigins.win`, `api.codetabs.com`, `corsproxy.io`, and `thingproxy.freeboard.io` in a loop to bypass Yahoo Finance CORS restrictions.

### 2.2 Backend (Python / Flask)
- **Framework:** Flask running on `localhost:8000`.
- **Integrations:**
  - `kiteconnect`: Official Zerodha Python SDK for order placement and portfolio fetching.
  - `google.generativeai`: Gemini Pro API for the conversational AI chatbot and technical setup scoring.
  - `selenium`: Automated headless Chrome webdriver to extract the Kite Request Token from the broker login flow.

---

## 3. Database Architecture

Finsistant uses local SQLite databases to maintain persistence across sessions.

### 3.1 `trade_queue.db` (Pending Trades)
Stores the AI-generated trade setups awaiting user approval.
- **Table:** `pending_trades`
- **Schema:**
  - `id` (TEXT): Unique trade UUID.
  - `symbol` (TEXT): NSE Stock Ticker.
  - `setup_type` (TEXT): E.g., Breakout, Mean Reversion.
  - `technical_score` (REAL): AI-assigned score (0-100).
  - `confidence` (REAL): Model confidence percentage.
  - `entry_zone` (TEXT): Entry price (automatically stripped of currency symbols `₹` by the frontend).
  - `stop_loss` (REAL) / `target` (REAL): Calculated levels.
  - `status` (TEXT): `ACTIVE`, `PENDING`, or `CLOSED`.

### 3.2 `database.db` (Trade History)
Maintains a log of executed and closed trades to calculate the portfolio win-rate and total PNL.
- **Endpoints:** The `/api/history` endpoint fetches this DB to calculate `total_closed` and `total_pnl` for the UI dashboard.

---

## 4. User Manual

Welcome to the Finsistant Terminal. Here is your operational flow.

### 4.1 System Initialization
1. Ensure your Google Gemini API Key and Kite credentials are set in the `.env` file or hardcoded locally.
2. Start the backend server by running `python main.py` in the `backend` directory (or double-click the `Start_Finsistant_Server.bat` file on your Desktop).
3. Access the frontend UI by navigating to your GitHub pages link or running `npm run dev` locally.

### 4.2 Generating Trade Setups
1. Click the **Scan Now** button in the UI. 
2. This triggers the `techsight_orchestrator.py` engine in the background, which evaluates the latest technical chart patterns and pushes new setups into `trade_queue.db`.
3. The Terminal UI will automatically populate the "Picks Table" with these new actionable setups.

### 4.3 Analyzing Trades
1. Click on any row in the **Picks Table**.
2. **Chart View:** The center screen will render the Weekly candlestick chart from Yahoo Finance, overlaying your Target (Green), Entry (Blue), and Stop Loss (Red).
3. **Analysis Terminal:** Located on the bottom left, this panel details the AI's rationale for the trade, the calculated position size (Qty), and the total capital required.

### 4.4 Trade Execution
All order execution is shielded by the execution password.
1. **Individual Execution:** With a trade selected, click **EXECUTE TRADE** in the Analysis Terminal or press the `Enter` key on your keyboard.
2. **Batch Execution:** Click the red **EXECUTE ALL** button to instantly fire all pending buy orders in the queue to Zerodha.
3. **Selling:** If the AI detects a risk flag, a stock will appear in the "SELL WARNINGS" box. Click **Sell Now** to exit the position.

### 4.5 AI Chatbot
1. Located on the right panel, use the chatbot to ask questions about the current market or your portfolio.
2. The bot is context-aware of your Kite holdings and can execute trades on your behalf if prompted with your password.
