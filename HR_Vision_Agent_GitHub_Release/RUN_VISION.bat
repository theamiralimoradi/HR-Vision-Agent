@echo off
cd /d "%~dp0"
if not exist ".env" echo [WARNING] .env not found. Copy .env.example to .env and set GAPGPT_API_KEY / GAPGPT_BASE_URL.
if exist ".venv\Scripts\python.exe" (set "PY=.venv\Scripts\python.exe") else (
  echo Creating virtual environment...
  py -3 -m venv .venv || python -m venv .venv
  set "PY=.venv\Scripts\python.exe"
)
"%PY%" -c "import streamlit, pymupdf, PIL, openai, docx, openpyxl, dotenv, pypdf" 2>nul || (
  echo Installing requirements...
  "%PY%" -m pip install -r requirements.txt || (echo Install failed & pause & exit /b 1)
)
echo Open http://localhost:8518  (use exactly this address)
"%PY%" -m streamlit run app_vision.py --server.port 8518 --server.address 127.0.0.1
pause
