@echo off
if not exist .venv\Scripts\activate.bat (
  echo Virtual environment not found. Run create_venv.bat first.
  exit /b 1
)
call .venv\Scripts\activate.bat
python --version
