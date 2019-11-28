
schtasks /create /tn "CMDB Agent Task." /ru system /tr C:\cmdb_win_agent.exe /sc DAILY /st 01:00:00

start %systemroot%\tasks

echo Create task success...

pause

rem del /f create-cmdb-task.bat
