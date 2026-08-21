@echo off
setlocal
echo Checking for Python 3.10.7...
py -3.10 -c "import sys; raise SystemExit(0 if sys.version_info[:3] == (3,10,7) else 1)" >nul 2>nul
if errorlevel 1 (
  echo WARNING: Exact Python 3.10.7 was not confirmed. The code targets Python 3.10.7.
  py -3.10 --version
  choice /M "Continue using py -3.10 anyway"
  if errorlevel 2 exit /b 1
)
py -3.10 -m venv .venv
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
echo Virtual environment ready.
endlocal
