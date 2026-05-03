@echo off
pushd %~dp0
if not exist .venv\Scripts\python.exe (
  echo Virtualenv python not found. Activate your environment or run: python run_server.py
  popd
  exit /b 1
)
start "Agent Server" .\.venv\Scripts\python.exe run_server.py
REM wait a few seconds then open browser
ping -n 4 127.0.0.1 >nul
start "" "http://127.0.0.1:8001/chat"
popd
