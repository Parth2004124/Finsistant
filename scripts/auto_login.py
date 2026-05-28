import time
import pyotp
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from kiteconnect import KiteConnect

# --- CONFIGURATION ---
API_KEY = "your_api_key_here"
API_SECRET = "your_api_secret_here"
USER_ID = "your_user_id_here"
PASSWORD = "your_password_here"
TOTP_SECRET = "your_totp_secret_here" # Base32 secret string from Zerodha
# ---------------------

def get_request_token():
    """Automates the Kite login process and returns the request token."""
    
    # Set up Chrome options for headless mode (optional, remove headless to see the browser)
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Initialize WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # Initialize KiteConnect to get the login URL
        kite = KiteConnect(api_key=API_KEY)
        login_url = kite.login_url()
        print(f"Navigating to login URL: {login_url}")
        
        # Open the login page
        driver.get(login_url)
        wait = WebDriverWait(driver, 10)
        
        # 1. Enter User ID
        userid_field = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='text']")))
        userid_field.send_keys(USER_ID)
        
        # 2. Enter Password
        password_field = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='password']")))
        password_field.send_keys(PASSWORD)
        
        # Click login button
        login_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
        login_btn.click()
        
        # 3. Handle TOTP prompt
        totp_field = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='number' or @type='text']")))
        
        # Generate current TOTP using pyotp
        totp = pyotp.TOTP(TOTP_SECRET)
        current_totp = totp.now()
        print(f"Generated TOTP: {current_totp}")
        
        totp_field.send_keys(current_totp)
        
        # Wait for redirection back to your application
        wait.until(EC.url_contains("request_token="))
        
        # Extract the request token from the current URL
        current_url = driver.current_url
        parsed_url = urlparse(current_url)
        query_params = parse_qs(parsed_url.query)
        
        request_token = query_params.get("request_token", [None])[0]
        
        if request_token:
            print(f"Successfully extracted request_token: {request_token}")
            return request_token
        else:
            raise Exception("request_token not found in the redirect URL")
            
    finally:
        driver.quit()

def main():
    try:
        # 1. Get the request token automatically
        request_token = get_request_token()
        
        # 2. Exchange request token for access token
        kite = KiteConnect(api_key=API_KEY)
        data = kite.generate_session(request_token, api_secret=API_SECRET)
        
        # Extract the access token
        access_token = data["access_token"]
        print(f"Login successful! Access Token: {access_token}")
        
        # 3. Set the access token in the Kite instance
        kite.set_access_token(access_token)
        
        # 4. Verify connection by fetching profile
        profile = kite.profile()
        print(f"Logged in as: {profile['user_name']}")
        
        # (Optional) Save the access token to a file/database here to reuse for the day
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
