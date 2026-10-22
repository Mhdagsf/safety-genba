@echo off
title PT. FUJISEAT INDONESIA - Safety Genba Web System
cd /d "%~dp0"
echo ========================================================
echo  PT. FUJISEAT INDONESIA - SYSTEM SAFETY GENBA D26A
echo ========================================================

:: Cek dependensi Python
python -c "import flask, openpyxl, PIL" 2>nul
if %errorlevel% neq 0 (
    echo Menginstal dependensi yang dibutuhkan...
    pip install -r requirements.txt
)

echo Membuka aplikasi di browser (http://127.0.0.1:5050)...
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:5050"
python app.py
pause

