import os
import logging
import yfinance as yf
import mplfinance as mpf
import pandas as pd

logger = logging.getLogger("KarnosChartGenerator")

CHART_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "karnos_charts")
if not os.path.exists(CHART_DIR):
    os.makedirs(CHART_DIR)

def get_symbol_data(symbol, period, interval):
    """
    Fetch historical data from yfinance for charting.
    Ensures `.NS` suffix is appended if not present, assuming Indian markets.
    """
    ticker = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False, timeout=15)
        if data.empty:
            logger.warning(f"No data found for {ticker} at {interval} interval.")
            return None
            
        # yf.download can return a multi-index columns in newer versions when fetching a single ticker,
        # but typically it's a flat index. Flatten if multi-index.
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
            
        return data
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {e}")
        return None

def apply_standard_style():
    """Returns a standardized mplfinance style for consistent Karnos inputs."""
    mc = mpf.make_marketcolors(
        up='g', down='r', 
        edge='inherit', 
        wick='inherit', 
        volume='in', 
        ohlc='inherit'
    )
    s = mpf.make_mpf_style(
        marketcolors=mc, 
        gridstyle='--', 
        gridcolor='#e0e0e0', 
        base_mpf_style='charles'
    )
    return s

def generate_karnos_charts(symbol):
    """
    Generates 3 standardized charts for a given stock symbol:
    1. 6-Month Daily (Trend view) with 20/50 SMA
    2. 1-Month Daily (Momentum view) with Volume
    3. 5-Day 15-Minute (Execution view)
    
    Returns a list of absolute file paths to the generated charts.
    """
    logger.info(f"Generating Karnos charts for {symbol}...")
    
    style = apply_standard_style()
    chart_paths = []
    
    # Define the 3 chart configurations
    configs = [
        {
            "id": "trend",
            "period": "6mo",
            "interval": "1d",
            "mav": (20, 50),
            "volume": False
        },
        {
            "id": "momentum",
            "period": "1mo",
            "interval": "1d",
            "mav": (9,),
            "volume": True
        },
        {
            "id": "execution",
            "period": "5d",
            "interval": "15m",
            "mav": (), # Could use VWAP but keeping it simple for consistency
            "volume": True
        }
    ]
    
    for config in configs:
        data = get_symbol_data(symbol, config["period"], config["interval"])
        if data is None or len(data) < 20:
            logger.error(f"Insufficient data for {symbol} - {config['id']} chart.")
            continue
            
        filename = f"{symbol}_{config['id']}.png"
        filepath = os.path.join(CHART_DIR, filename)
        
        try:
            # Generate the chart with fixed dimensions (1200x800) and tight layout
            kwargs = dict(
                type='candle',
                volume=config["volume"],
                style=style,
                figsize=(12, 8),
                tight_layout=True,
                savefig=filepath,
                axisoff=True # Remove axis labels/ticks so AI only sees pattern shape
            )
            
            if config["mav"]:
                kwargs["mav"] = config["mav"]
                
            mpf.plot(data, **kwargs)
            chart_paths.append(filepath)
            
        except Exception as e:
            logger.error(f"Failed to generate {config['id']} chart for {symbol}: {e}")
            
    return chart_paths
