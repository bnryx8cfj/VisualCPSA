@echo off
if not exist .venv\Scripts\python.exe (
  echo Virtual environment not found. Run create_venv.bat first.
  exit /b 1
)
.venv\Scripts\python.exe -m unittest discover -s tests
