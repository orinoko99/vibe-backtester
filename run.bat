@echo off
chcp 65001 >nul
echo Запуск бэктестера...
call venv\Scripts\activate.bat
python -m src.main
pause
