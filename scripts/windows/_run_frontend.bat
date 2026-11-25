@echo off
rem 前端启动包装脚本（由 一键启动.bat 调用，不要直接双击）
cd /d "%~dp0..\..\frontend" || exit /b 1
node "node_modules\vite\bin\vite.js" --host 127.0.0.1 --port 5174 >> "%~dp0..\..\logs\frontend.log" 2>&1
