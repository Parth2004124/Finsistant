import time
import pyotp
import json
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from kiteconnect import KiteConnect

import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(os.path.dirname(BASE_DIR), "secrets.env"))

api_key = os.environ.get("KITE_API_KEY", "")
api_secret = os.environ.get("KITE_API_SECRET", "")
user_id = os.environ.get("KITE_USER_ID", "")
password = os.environ.get("KITE_PASSWORD", "")
totp_secret = os.environ.get("KITE_TOTP_SECRET", "")

def place_order():
    print("Starting VISIBLE Chrome...")
    options = Options()
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        login_url = f"https://kite.trade/connect/login?api_key={api_key}&v=3"
        print("Navigating to login URL...")
        driver.get(login_url)
        
        wait = WebDriverWait(driver, 60)
        
        print("Entering credentials...")
        user_id_field = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='text' and @id='userid']")))
        password_field = driver.find_element(By.XPATH, "//input[@type='password' and @id='password']")
        
        user_id_field.send_keys(user_id)
        password_field.send_keys(password)
        
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        
        print("Entering 2FA using global keystrokes...")
        time.sleep(3)
        totp_token = pyotp.TOTP(totp_secret).now()
        
        ActionChains(driver).send_keys(totp_token).perform()
        
        time.sleep(1)
        try:
            submit_2fa = driver.find_element(By.XPATH, "//button[@type='submit']")
            submit_2fa.click()
            print("Clicked 2FA submit.")
        except:
            print("No 2FA submit button found, assuming auto-submit.")
            
        time.sleep(3)
        
        if "/connect/authorize" in driver.current_url or "/connect/login" in driver.current_url:
            print("Checking for Authorize button...")
            try:
                auth_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Authorize') or contains(text(), 'I understand') or @type='submit']")
                print("Found auth button. Clicking...")
                auth_button.click()
                time.sleep(2)
            except Exception as e:
                pass
                
        print("WAITING FOR YOU TO AUTHORIZE IF NEEDED... (60s timeout)")
        
        wait.until(lambda d: "request_token" in d.current_url)
        
        final_url = driver.current_url
        print("Successfully redirected:", final_url)
        
        parsed_url = urlparse(final_url)
        params = parse_qs(parsed_url.query)
        request_token = params.get("request_token", [None])[0]
        
        if request_token:
            print("Got request token:", request_token)
            kite = KiteConnect(api_key=api_key)
            data = kite.generate_session(request_token, api_secret=api_secret)
            
            # Print the actual ACCESS token so we can save it for the backend!
            actual_access_token = data["access_token"]
            print(f"\n---> YOUR NEW ACCESS TOKEN: {actual_access_token} <---")
            
            with open('token.txt', 'w') as f:
                f.write(actual_access_token)
            
            print("\nPushing token to PythonAnywhere server...")
            try:
                import requests
                resp = requests.post("https://parthbhosale.pythonanywhere.com/api/update_token", json={
                    "secret": "my_super_secret_trading_key",
                    "token": actual_access_token
                })
                print("Server response:", resp.json())
            except Exception as e:
                print("Failed to push token to server:", e)
                
        else:
            print("Could not find request token in URL.")
            
    except Exception as e:
        print("Error during Selenium execution:", str(e))
    finally:
        time.sleep(5)
        driver.quit()

if __name__ == "__main__":
    place_order()
