@echo off
chcp 65001 >nul
setlocal DisableDelayedExpansion
cd /d "%~dp0"
echo eBay Drafts - one-time setup
echo This installs the Python packages listed in requirements.txt.
echo It does not connect to eBay or need administrator access.
where py >nul 2>nul
if errorlevel 1 goto missing_python
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 goto missing_python
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
if not exist ".venv\Scripts\python.exe" goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -I -B run.py --register
if errorlevel 1 goto failed
pause
exit /b 0
:missing_python
echo Install Python 3.11 or newer for Windows from python.org, including the Python launcher.
echo Python 3.13 64-bit is a suitable choice. Then double-click this file again.
pause
exit /b 2
:failed
echo Setup did not finish. Read the error above, check your internet connection and try again.
pause
exit /b 2
