@echo off
chcp 65001 >nul
echo Запуск Backtester...

call "%~dp0venv\Scripts\python.exe" "%~dp0main.py"

if %errorlevel% neq 0 (
    echo Ошибка при запуске Backtester.
    pause
)
