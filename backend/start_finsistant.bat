@echo off
cd /d C:\Users\parth\.gemini\antigravity\scratch\backend
python selenium_login.py > selenium.log 2>&1
python start_server.py > server.log 2>&1
