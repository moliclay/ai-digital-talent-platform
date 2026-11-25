@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo   AI 数字化人才平台  -  一键停止
echo ============================================================
echo.

set KILLED=0

rem ---------- 1. 停前端 (5174) ----------
echo ------------------------------------------------------------
echo [1/3] 前端 Web (5174)
echo ------------------------------------------------------------
call :kill_port 5174 "前端"

rem ---------- 2. 停后端 (8000) ----------
echo.
echo ------------------------------------------------------------
echo [2/3] 后端 API (8000)
echo ------------------------------------------------------------
call :kill_port 8000 "后端"

rem ---------- 3. 兜底：按进程名清理 uvicorn / vite ----------
echo.
echo ------------------------------------------------------------
echo [3/3] 兜底清理残留进程
echo ------------------------------------------------------------
rem Windows 11 已弃用 wmic，改用 PowerShell 按命令行关键字清理
rem 传项目路径过滤，避免误杀其它项目的 uvicorn/vite
call :kill_by_cmdline "vite"
call :kill_by_cmdline "uvicorn"

echo.
echo ============================================================
echo   停止完成
echo ============================================================
echo.
echo   以下服务未停止（可能被其它项目使用，需手动执行）：
echo     MySQL   :  taskkill /IM mysqld.exe /F
echo     Ollama  :  taskkill /IM ollama.exe /F
echo     Redis   :  taskkill /IM redis-server.exe /F
echo.
echo   端口状态核对：
call :check_port 5174
call :check_port 8000
echo ============================================================
endlocal
exit /b 0

rem ============ 按端口杀进程 ============
:kill_port
set PORT=%~1
set LABEL=%~2
set FOUND=0
for /f "tokens=5" %%A in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
  set FOUND=1
  echo   结束 %LABEL% 进程 PID=%%A
  taskkill /F /T /PID %%A >nul 2>&1
  set /a KILLED+=1
)
if !FOUND!==0 echo   %LABEL% 未在运行（端口 %PORT% 空闲）
exit /b 0

rem ============ 按命令行关键字清理（调用 scripts/windows/_kill_by_keyword.ps1）============
:kill_by_cmdline
set KW=%~1
rem The helper resolves this workspace from its own path.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows\_kill_by_keyword.ps1" -Keyword "%KW%"
exit /b 0

rem ============ 核对端口是否已释放 ============
:check_port
set PORT=%~1
netstat -ano | findstr ":%PORT%" | findstr "LISTENING" >nul
if errorlevel 1 (
  echo     %PORT%  : 已释放
) else (
  echo     %PORT%  : [警告] 仍在监听
)
exit /b 0
