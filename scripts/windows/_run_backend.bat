@echo off
rem 后端启动包装脚本（由 一键启动.bat 调用，不要直接双击）
cd /d "%~dp0..\..\backend" || exit /b 1
".venv\Scripts\python.exe" scripts\migrate_chat.py >> "%~dp0..\..\logs\backend.log" 2>&1 || exit /b 1
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 >> "%~dp0..\..\logs\backend.log" 2>&1
