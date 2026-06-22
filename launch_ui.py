import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

print("Starting VISIBLE Chrome for Dashboard...")
options = Options()
options.add_argument('--window-size=1920,1080')
options.add_experimental_option("detach", True)
options.add_experimental_option("excludeSwitches", ["enable-automation"])

try:
    driver = webdriver.Chrome(options=options)
    driver.get("https://Parth2004124.github.io/Finsistant-UI/")
    print("Dashboard launched.")
except Exception as e:
    print(f"Failed to launch: {e}")
