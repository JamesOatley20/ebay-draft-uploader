@echo off
chcp 65001 >nul
setlocal DisableDelayedExpansion
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Double-click Setup.cmd first, then open Start.cmd again.
    pause
    exit /b 2
)
".venv\Scripts\python.exe" -I -B run.py
set "Result=%ERRORLEVEL%"
pause
exit /b %Result%
