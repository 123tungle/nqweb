@echo off
cd /d "%~dp0"
set TEN_DV=NQW_Web
set NSSM=%~dp0nssm.exe
if not exist "%NSSM%" ( echo Thieu nssm.exe trong thu muc nay. & pause & exit /b 1 )
if not exist ".venv\Scripts\python.exe" ( echo Chua co .venv. Chay setup.bat truoc. & pause & exit /b 1 )
set PYTHON=%~dp0.venv\Scripts\python.exe

"%NSSM%" stop %TEN_DV% >nul 2>nul
"%NSSM%" remove %TEN_DV% confirm >nul 2>nul

"%NSSM%" install %TEN_DV% "%PYTHON%" "-m uvicorn app.main:app --host 127.0.0.1 --port 8090"
"%NSSM%" set %TEN_DV% AppDirectory "%~dp0"
"%NSSM%" set %TEN_DV% DisplayName "Web Nguyen Quan"
"%NSSM%" set %TEN_DV% Start SERVICE_AUTO_START
"%NSSM%" set %TEN_DV% AppStdout "%~dp0data\web_service.log"
"%NSSM%" set %TEN_DV% AppStderr "%~dp0data\web_service.log"
"%NSSM%" set %TEN_DV% AppExit Default Restart
"%NSSM%" set %TEN_DV% AppRestartDelay 3000
"%NSSM%" start %TEN_DV%
echo === XONG. Dich vu %TEN_DV% da chay. ===
pause