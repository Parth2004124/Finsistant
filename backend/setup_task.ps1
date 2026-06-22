$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\Users\parth\.gemini\antigravity\scratch\backend\selenium_login.py" -WorkingDirectory "C:\Users\parth\.gemini\antigravity\scratch\backend"
$trigger = New-ScheduledTaskTrigger -Daily -At 8:45AM
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable
Register-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -TaskName "FinsistantTokenRefresh" -Description "Automated daily Zerodha login" -User $env:USERNAME -Force
