@echo off

chcp 65001 >nul

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ============================================================

echo   AI 数字化人才平台  -  一键启动

echo ============================================================

echo.

rem ---------- 路径 ----------

set MYSQL_HOME=D:\mysql-9.4.0-winx64

set ROOT=%~dp0

rem Backend and frontend are located at the repository root.

set "BACKEND=%ROOT%backend"

set "FRONTEND=%ROOT%frontend"

set LOGS=%ROOT%logs

set PY=%BACKEND%\.venv\Scripts\python.exe

if not exist "%LOGS%" mkdir "%LOGS%"

rem ---------- 前置检查 ----------

if not exist "%PY%" (

  echo [错误] 找不到后端虚拟环境：%PY%

  echo        请先执行：cd backend ^&^& python -m venv .venv ^&^& .venv\Scripts\python.exe -m pip install -r requirements.txt

  pause & exit /b 1

)

if not exist "%FRONTEND%\node_modules\vite\bin\vite.js" (

  echo [错误] 前端依赖缺失：%FRONTEND%\node_modules

  echo        请先执行：cd frontend ^&^& npm ci

  pause & exit /b 1

)

echo ------------------------------------------------------------

echo [1/6] MySQL (3306)

echo ------------------------------------------------------------

netstat -ano | findstr ":3306" | findstr "LISTENING" >nul

if errorlevel 1 (

  if not exist "%MYSQL_HOME%\bin\mysqld.exe" (

    echo [错误] 找不到 mysqld：%MYSQL_HOME%\bin\mysqld.exe

    pause & exit /b 1

  )

  echo   正在启动 mysqld ...

  start "mysqld" /min "%MYSQL_HOME%\bin\mysqld.exe" --port=3306 --datadir="%MYSQL_HOME%\data"

  call :wait_port 3306 20

  if errorlevel 1 (

    echo [错误] MySQL 未能在 40 秒内监听 3306

    pause & exit /b 1

  )

) else (

  echo   已在运行

)

echo.

echo ------------------------------------------------------------

echo [2/6] Redis (6379)  —— 可选，缺失不影响启动

echo ------------------------------------------------------------

netstat -ano | findstr ":6379" | findstr "LISTENING" >nul

if errorlevel 1 (

  echo   [提示] Redis 未运行。后端会标记 redis=false，但功能可用（仅会话黑名单降级）

  echo          如需启动：在本机 Redis 目录执行 redis-server.exe

) else (

  echo   已在运行

)

echo.

echo ------------------------------------------------------------

echo [3/6] Ollama 嵌入服务 (11434)  —— 语义检索/查重用

echo ------------------------------------------------------------

netstat -ano | findstr ":11434" | findstr "LISTENING" >nul

if errorlevel 1 (

  where ollama >nul 2>&1

  if errorlevel 1 (

    echo   [提示] 未检测到 ollama 命令，语义检索将不可用

  ) else (

    echo   正在启动 ollama serve ...

    start "ollama" /min cmd /c "ollama serve > ""%LOGS%\ollama.log"" 2>&1"

    call :wait_port 11434 20

    if errorlevel 1 echo   [提示] ollama 启动较慢，可稍后手动确认

  )

) else (

  echo   已在运行

)

echo.

echo ------------------------------------------------------------

echo [4/6] Milvus (19530)

echo ------------------------------------------------------------

netstat -ano | findstr ":19530" | findstr "LISTENING" >nul

if errorlevel 1 (
  where docker >nul 2>&1
  if errorlevel 1 (
    echo   [提示] 未检测到 Docker，语义检索将不可用
  ) else (
    docker start milvus26-etcd milvus26-minio milvus26-standalone >nul 2>&1
    if errorlevel 1 (
      echo   [提示] Milvus 容器未就绪，请检查 Docker 与 Milvus 配置
    ) else (
      call :wait_port 19530 30
      if errorlevel 1 echo   [提示] Milvus 尚未监听，可稍后检查
    )
  )
) else (
  echo   已在运行
)

echo.

echo ------------------------------------------------------------

echo [5/6] 后端 API  http://127.0.0.1:8000

echo ------------------------------------------------------------

netstat -ano | findstr ":8000" | findstr "LISTENING" >nul

if errorlevel 1 (

  echo   正在启动 uvicorn ...

  start "talent-api" /min cmd /c ""%ROOT%scripts\windows\_run_backend.bat""

  call :wait_port 8000 30

  if errorlevel 1 (

    echo [错误] 后端未能在 60 秒内监听 8000，请查看 %LOGS%\backend.log

    pause & exit /b 1

  )

) else (

  echo   已在运行

)

rem 健康检查

set HEALTH=down

for /f "delims=" %%H in ('curl -s --max-time 5 http://127.0.0.1:8000/api/health 2^>nul') do set HEALTH=%%H

echo   health: !HEALTH!

echo.

echo ------------------------------------------------------------

echo [6/6] 前端 Web  http://127.0.0.1:5174

echo ------------------------------------------------------------

netstat -ano | findstr ":5174" | findstr "LISTENING" >nul

if errorlevel 1 (

  echo   正在启动 vite ...

  start "talent-web" /min cmd /c ""%ROOT%scripts\windows\_run_frontend.bat""

  call :wait_port 5174 30

  if errorlevel 1 (

    echo [错误] 前端未能在 60 秒内监听 5174，请查看 %LOGS%\frontend.log

    pause & exit /b 1

  )

) else (

  echo   已在运行

)

echo.

echo ============================================================

echo   启动完成

echo ============================================================

echo   前端       http://127.0.0.1:5174

echo   接口文档   http://127.0.0.1:8000/docs

echo   健康检查   http://127.0.0.1:8000/api/health

echo   日志目录   %LOGS%

echo.

echo   演示账号（密码统一 123456）：

echo     hr_zhao    HR，简历/岗位/匹配/测评/培训

echo     admin      系统管理员

echo     emp_chen   普通员工，仅培训成长

echo.

echo   停止服务：双击 一键停止.bat

echo ============================================================

start "" http://127.0.0.1:5174

endlocal

exit /b 0

rem ============ 子过程：等待端口监听 ============

:wait_port

set PORT=%~1

set /a MAX=%~2

set /a N=0

:wait_loop

netstat -ano | findstr ":%PORT%" | findstr "LISTENING" >nul

if not errorlevel 1 exit /b 0

ping -n 3 127.0.0.1 >nul 2>&1

set /a N+=1

if %N% lss %MAX% goto wait_loop

exit /b 1

