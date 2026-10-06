@echo off
REM Chay bao cao cuoi ngay - canh gio theo bang NQW_BaoCaoEmailCf
cd /d "%~dp0\.."
python tien_ich\bao_cao_cuoi_ngay.py %*
