@echo off
cd /d "%~dp0"

if not exist "app.py" (
    echo ERROR: app.py not found.
    echo Make sure run_app.bat is in the project root alongside app.py.
    pause
    exit /b 1
)

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not on PATH.
    echo Install Python 3.10+ from https://python.org and try again.
    pause
    exit /b 1
)

echo Starting Creative Automation Pipeline...
echo Press Ctrl+C to stop the server.
echo.

rem Open the browser after a 3-second delay in a separate background process.
rem The main window runs Flask so logs remain visible here.
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:5000"

python app.py

echo.
echo Server stopped.
pause
