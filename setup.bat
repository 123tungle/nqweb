@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === CAI DAT WEB NGUYEN QUAN ===
where py >nul 2>nul
if errorlevel 1 (
  echo Chua co Python. Tai Python 3.11 tai https://www.python.org/downloads/windows/ , khi cai nho tick "Add python.exe to PATH".
  pause & exit /b 1
)
if not exist .venv (
  echo Tao moi truong Python...
  py -3.11 -m venv .venv 2>nul || py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 ( echo LOI cai thu vien. & pause & exit /b 1 )
if not exist config.ini (
  copy config.ini.example config.ini >nul
  echo.
  echo Da tao file config.ini. Dien mat khau SQL Server roi LUU LAI, dong Notepad de tiep tuc.
  notepad config.ini
)
python kiem_tra.py
if errorlevel 1 ( pause & exit /b 1 )
echo.
echo === CAI DAT XONG. Chay run.bat de mo web. ===
pause
