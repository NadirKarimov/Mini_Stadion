@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where py >nul 2>nul
if %errorlevel%==0 set PY=py -3
if not exist .venv (
  echo Virtual muhit yaratilmoqda...
  %PY% -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env (
  copy .env.example .env
  echo.
  echo .env fayli yaratildi. BOT_TOKEN va ADMIN_IDS ni yozing.
  notepad .env
)
echo.
echo Ishga tushirish: start.bat
pause
