@echo off
TITLE SentinEL - Autonomous Supply Chain Agent

echo ===================================================
echo        SENTINEL AI - PRODUCTION CONTROL
echo ===================================================
echo.
echo Select Operation Mode:
echo [1] SIMULATION MODE (Deterministic, Mock Data)
echo [2] LIVE DATA MODE (GDELT, AIS, OpenWeather)
echo.

set /p mode="Enter choice (1 or 2): "

echo.
echo [Initializing Environment...]
pip install -r requirements.txt > nul 2>&1

echo.
echo [Starting High-Performance Dashboard...]
start /b python -m uvicorn src.dashboard.app:app --host 0.0.0.0 --port 8000

echo Waiting for Dashboard...
timeout /t 4 /nobreak >nul
start http://localhost:8000

echo.
if "%mode%"=="2" (
    echo [CONNECTING TO LIVE STREAMS...]
    echo The Agent is now pulling real-time data from GDELT/AIS.
    python -m src.demo_live_windows
) else (
    echo [STARTING SIMULATION CORE...]
    python -m src.demo_windows
)

echo.
echo ===================================================
echo     SESSION ENDED
echo ===================================================
pause
