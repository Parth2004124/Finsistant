@echo off
echo =========================================
echo       Finsistant AI Startup Script
echo =========================================

cd /d "%~dp0"

echo [1/3] Starting Python Backend Server (Waitress + Ngrok)...
cd backend
start "Finsistant Backend" start_backend.bat
cd ..

echo [2/3] Starting React Frontend...
cd frontend
start /min "Finsistant Frontend" npm run dev
cd ..

echo [3/3] Starting TechSight Orchestrator...
start "TechSight Orchestrator" "C:\Users\parth\AppData\Local\Programs\Python\Python313\python.exe" techsight_orchestrator.py

echo.
echo All services have been launched!
pause
