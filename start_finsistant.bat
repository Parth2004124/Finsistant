@echo off
echo =========================================
echo       Finsistant AI Startup Script
echo =========================================

:: Get the directory of this batch file
cd /d "%~dp0"

echo [1/2] Starting Python Backend Server...
:: start /min opens it in a minimized background window
start /min "Finsistant Backend" python backend/main.py

echo [2/2] Starting React Frontend...
cd frontend
start /min "Finsistant Frontend" npm run dev
cd ..

echo.
echo All services have been launched in the background!
echo.
echo Dashboard: http://localhost:5173
echo API:       http://127.0.0.1:8000
echo.
echo To stop the servers, you can close the minimized command prompt windows.
pause
