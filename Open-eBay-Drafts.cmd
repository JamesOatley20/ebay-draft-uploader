@echo off
chcp 65001 >nul
setlocal DisableDelayedExpansion
if not exist "%LOCALAPPDATA%\eBayDrafts\tool-path.txt" goto missing_app
set "Tool="
set /p "Tool="<"%LOCALAPPDATA%\eBayDrafts\tool-path.txt"
if not defined Tool goto missing_app
if not exist "%Tool%" goto missing_app
for %%I in ("%Tool%") do set "Python=%%~dpI.venv\Scripts\python.exe"
if not exist "%Python%" goto missing_app
"%Python%" -I -B "%Tool%" --batch "%~dp0."
set "Result=%ERRORLEVEL%"
pause
exit /b %Result%
:missing_app
echo Double-click Setup.cmd in the eBay app folder first, then open this file again.
pause
exit /b 2
