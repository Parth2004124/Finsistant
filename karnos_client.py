import os
import requests
import logging
import time

logger = logging.getLogger("KarnosClient")

KARNOS_API_ENDPOINT = os.getenv("KARNOS_API_ENDPOINT", "http://karnos-engine.local/api/v1/analyze")
KARNOS_API_KEY = os.getenv("KARNOS_API_KEY", "mock-key")
KARNOS_TIMEOUT_SECONDS = int(os.getenv("KARNOS_TIMEOUT", 15))

def send_charts_to_karnos(symbol, chart_paths):
    """
    Stage 4 & 5: Karnos Integration & Fault Tolerance
    Sends the generated charts to the Karnos AI prediction engine.
    
    Returns a strict dictionary of expected outputs:
    - direction
    - confidence
    - expected_movement
    - predicted_trend
    - explanation
    """
    logger.info(f"Preparing to send {len(chart_paths)} charts to Karnos for {symbol}")
    
    files = []
    for path in chart_paths:
        if os.path.exists(path):
            files.append(('charts', (os.path.basename(path), open(path, 'rb'), 'image/png')))
        else:
            logger.error(f"Chart missing for Karnos payload: {path}")
            
    if len(files) != 3:
        logger.warning("Did not find exactly 3 charts. Karnos analysis might be degraded or fail.")
        
    payload = {
        "symbol": symbol,
        "request_type": "technical_validation"
    }
    
    headers = {
        "Authorization": f"Bearer {KARNOS_API_KEY}"
    }

    try:
        # Stage 5: Fault Tolerance (Timeout)
        logger.info(f"POST {KARNOS_API_ENDPOINT} - Timeout: {KARNOS_TIMEOUT_SECONDS}s")
        start_time = time.time()
        # In a real environment, this uncommented block would execute:
        '''
        response = requests.post(
            KARNOS_API_ENDPOINT,
            data=payload,
            files=files,
            headers=headers,
            timeout=KARNOS_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        data = response.json()
        '''
        
        # MOCK RESPONSE (Since Karnos engine is hypothetical/unprovided)
        logger.warning("Using MOCK Karnos response. Replace with actual HTTP call in production.")
        time.sleep(1.2) # Simulate network delay
        latency = round((time.time() - start_time) * 1000, 2)
        logger.info(f"Karnos responded in {latency}ms")
        
        data = {
            "direction": "BULLISH",
            "confidence": 88,
            "expected_movement": "4.5%",
            "predicted_trend": "UPTREND",
            "explanation": "Karnos detected strong accumulation in the 6-month trend and breakout structure on the 15m execution chart."
        }
        
        # Ensure we close file handles
        for _, file_tuple in files:
            file_tuple[1].close()
            
        return data

    except requests.exceptions.Timeout:
        logger.error(f"Stage 5 Fault: Karnos API timed out after {KARNOS_TIMEOUT_SECONDS} seconds for {symbol}")
        for _, file_tuple in files: file_tuple[1].close()
        raise Exception("Karnos Timeout")
    except requests.exceptions.RequestException as e:
        logger.error(f"Stage 5 Fault: Karnos API connection error for {symbol}: {e}")
        for _, file_tuple in files: file_tuple[1].close()
        raise Exception(f"Karnos Network Error: {e}")
    except Exception as e:
        logger.error(f"Stage 5 Fault: Unexpected error calling Karnos for {symbol}: {e}")
        for _, file_tuple in files: file_tuple[1].close()
        raise Exception(f"Karnos Unexpected Error: {e}")
