@echo off
chcp 65001 >nul
cd /d "%~dp0"
call .venv\Scripts\activate.bat
set PORT=8090
for /f "tokens=2 delims==" %%a in ('findstr /b /c:"port" config.ini') do set PORT=%%a
set PORT=%PORT: =%
echo === WEB NGUYEN QUAN dang chay ===
echo Tren may nay mo:          http://localhost:%PORT%
echo May khac / dien thoai:    http://[dia chi IPv4 ben duoi]:%PORT%
ipconfig | findstr /R /C:"IPv4"
echo Dong cua so nay = tat web.
start "" http://localhost:%PORT%
python -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%
pause
