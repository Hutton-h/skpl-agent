@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   SKPL Agent - 启动中...
echo ========================================

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python。请先安装 Python 3.10+。
    echo   下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Node.js。请先安装 Node.js 18+。
    echo   下载地址: https://nodejs.org/
    pause
    exit /b 1
)

:: Check backend dependencies
echo [1/4] 检查后端依赖...
if not exist ".venv\Scripts\python.exe" (
    echo   .venv 不存在，创建虚拟环境...
    python -m venv .venv
    echo   安装后端依赖（这可能需要几分钟）...
    .venv\Scripts\python.exe -m pip install -e ".[service,context,web,update,vdb-milvus,rag,memory-mem0]" --quiet
    if %errorlevel% neq 0 (
        echo [错误] 后端依赖安装失败！
        pause
        exit /b 1
    )
    echo   [OK] 后端依赖安装完成
)

:: Check frontend dependencies
echo [2/4] 检查前端依赖...
if not exist "frontend\node_modules" (
    echo   node_modules 不存在，安装前端依赖...
    cd frontend
    call npm install
    if %errorlevel% neq 0 (
        echo [错误] 前端依赖安装失败！
        pause
        exit /b 1
    )
    cd ..
    echo   [OK] 前端依赖安装完成
)

:: Build frontend
echo [3/4] 构建前端（这可能需要几分钟）...
cd frontend
call npx vite build
if %errorlevel% neq 0 (
    echo [错误] 前端构建失败！
    pause
    exit /b 1
)
cd ..
echo   [OK] 前端构建完成

:: Start services
echo [4/4] 启动服务...
echo.
start "SKPL Backend" .venv\Scripts\python.exe -m skpl_agent --port 8000
start "SKPL Frontend" python serve_frontend.py

echo.
echo ========================================
echo   启动完成！
echo   后端: http://localhost:8000
echo   前端: http://localhost:4173
echo ========================================
echo.
echo 按任意键退出此窗口...
pause >nul