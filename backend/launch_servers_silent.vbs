Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\parth\.gemini\antigravity\scratch\backend"
WshShell.Run "cmd /c python start_server.py > server.log 2>&1", 0, False
WshShell.Run "cmd /c python dashboard_api.py > dashboard.log 2>&1", 0, False
Set WshShell = Nothing
