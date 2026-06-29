@echo off
cd /d "%~dp0"
echo =================================================== >> techsight_orchestrator.log
echo [ %DATE% %TIME% ] Starting scheduled TechSight sweep... >> techsight_orchestrator.log

:: Check if backend server is running on port 8000
netstat -ano | findstr :8000 > nul
if %errorlevel% neq 0 (
    echo [ %DATE% %TIME% ] Backend server not running on port 8000. Launching... >> techsight_orchestrator.log
    start /min "Finsistant Backend" "C:\Users\parth\AppData\Local\Programs\Python\Python313\python.exe" backend/main.py
    :: Wait 5 seconds for the backend to spin up and bind the port using ping (timeout fails under redirection)
    ping 127.0.0.1 -n 6 > nul
) else (
    echo [ %DATE% %TIME% ] Backend server is already running on port 8000. >> techsight_orchestrator.log
)

"C:\Users\parth\AppData\Local\Programs\Python\Python313\python.exe" techsight_orchestrator.py >> techsight_orchestrator.log 2>&1
echo [ %DATE% %TIME% ] Scheduled TechSight sweep completed. >> techsight_orchestrator.log
