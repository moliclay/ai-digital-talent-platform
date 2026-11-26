@echo off
setlocal
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows\_services.ps1" -Mode Stop
set "result=%errorlevel%"
if not "%result%"=="0" pause
exit /b %result%
