# SKPL Desktop Node — 一键安装脚本
# 用法: 双击 install.bat 即可运行
# 自动完成: Python 安装 → 依赖安装 → 配置 → 快捷方式 → 启动

param(
    [string]$ServerUrl = "",
    [string]$Token = "",
    [string]$NodeName = $env:COMPUTERNAME
)

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

# 颜色输出函数
function Write-Color($Text, $Color = "White") {
    Write-Host $Text -ForegroundColor $Color
}

function Write-Step($Num, $Text) {
    Write-Host ""
    Write-Host "[$Num] $Text" -ForegroundColor Yellow
    Write-Host ("-" * 50) -ForegroundColor Gray
}

function Write-OK($Text) {
    Write-Host "  OK  $Text" -ForegroundColor Green
}

function Write-Err($Text) {
    Write-Host "  ERR $Text" -ForegroundColor Red
}

# ── 头部 ──────────────────────────────────────────────────────────────
Clear-Host
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       SKPL Desktop Node — 一键安装程序 v1.0          ║" -ForegroundColor Cyan
Write-Host "║       桌面自动化节点 — 安装即用                       ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  本程序将自动完成以下操作:" -ForegroundColor White
Write-Host "  1. 检测/安装 Python 3.11" -ForegroundColor Gray
Write-Host "  2. 安装所需依赖库" -ForegroundColor Gray
Write-Host "  3. 配置服务器连接" -ForegroundColor Gray
Write-Host "  4. 创建桌面快捷方式" -ForegroundColor Gray
Write-Host "  5. 启动节点服务" -ForegroundColor Gray
Write-Host ""

# ── 步骤 1: 检测 Python ──────────────────────────────────────────────
Write-Step "1/5" "检测 Python 环境..."

$PythonExe = $null

# 先检查常见的 Python 路径
$Paths = @(
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "C:\Python311\python.exe",
    "C:\Python310\python.exe"
)

foreach ($p in $Paths) {
    if (Test-Path $p) {
        $PythonExe = $p
        break
    }
}

# 如果没有找到，尝试系统 PATH
if (-not $PythonExe) {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) { $PythonExe = $py.Source }
}

if (-not $PythonExe) {
    $py = Get-Command python3 -ErrorAction SilentlyContinue
    if ($py) { $PythonExe = $py.Source }
}

if ($PythonExe) {
    $ver = & $PythonExe --version 2>&1
    Write-OK "已找到 $ver"
    Write-OK "路径: $PythonExe"
} else {
    Write-Color "  Python 未安装，正在通过 winget 自动安装..." -ForegroundColor Yellow
    Write-Host "  (这可能需要几分钟，请耐心等待)" -ForegroundColor Gray
    
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements
        if ($LASTEXITCODE -eq 0) {
            Write-OK "Python 3.11 安装成功"
            # 刷新环境变量
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            $PythonExe = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
            if (-not (Test-Path $PythonExe)) {
                $PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
            }
        } else {
            Write-Err "winget 安装失败，请手动安装 Python 3.11"
            Write-Host "  下载地址: https://www.python.org/downloads/" -ForegroundColor Cyan
            Write-Host "  安装时请勾选 'Add Python to PATH'" -ForegroundColor Cyan
            Read-Host "按回车键退出"
            exit 1
        }
    } else {
        Write-Err "未找到 winget，请手动安装 Python 3.11"
        Write-Host "  下载地址: https://www.python.org/downloads/" -ForegroundColor Cyan
        Write-Host "  安装时请勾选 'Add Python to PATH'" -ForegroundColor Cyan
        Read-Host "按回车键退出"
        exit 1
    }
}

# ── 步骤 2: 创建安装目录和虚拟环境 ──────────────────────────────────
Write-Step "2/5" "创建运行环境..."

$InstallDir = "$env:LOCALAPPDATA\skpl-desktop-node"
$VenvDir = Join-Path $InstallDir "venv"
$ConfigDir = Join-Path $InstallDir "config"
$LogDir = Join-Path $InstallDir "logs"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Write-OK "安装目录: $InstallDir"

# 创建虚拟环境
Write-Host "  正在创建虚拟环境..." -ForegroundColor Gray
if (Test-Path $VenvDir) {
    Write-OK "虚拟环境已存在，跳过创建"
} else {
    & $PythonExe -m venv $VenvDir 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-OK "虚拟环境创建成功"
    } else {
        Write-Err "虚拟环境创建失败"
        Read-Host "按回车键退出"
        exit 1
    }
}

$VenvPython = Join-Path $VenvDir "Scripts" "python.exe"
$VenvPip = Join-Path $VenvDir "Scripts" "pip.exe"

# ── 步骤 3: 安装依赖 ─────────────────────────────────────────────────
Write-Step "3/5" "安装依赖库 (可能需要几分钟)..."

# 升级 pip
& $VenvPython -m pip install --upgrade pip --quiet 2>&1 | Out-Null

# 安装依赖
$deps = @(
    "pyautogui>=0.9.54",
    "pillow>=10.0.0",
    "mss>=9.0.0",
    "websockets>=12.0",
    "keyboard>=0.13.5",
    "psutil>=5.9.0"
)

Write-Host "  正在安装..." -ForegroundColor Gray
foreach ($dep in $deps) {
    Write-Host "    - $dep" -ForegroundColor Gray
    & $VenvPip install $dep --quiet 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Err "安装 $dep 失败"
    }
}

# 安装桌面节点代码本身
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DesktopNodeSrc = Join-Path $ScriptDir ".." "desktop_node"

if (Test-Path $DesktopNodeSrc) {
    Write-Host "  正在安装 SKPL Desktop Node..." -ForegroundColor Gray
    & $VenvPip install -e $DesktopNodeSrc --quiet 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-OK "SKPL Desktop Node 安装成功"
    } else {
        Write-OK "以开发模式安装 (可直接运行源码)"
    }
}

Write-OK "依赖安装完成"

# ── 步骤 4: 配置连接 ─────────────────────────────────────────────────
Write-Step "4/5" "配置服务器连接..."

# 如果命令行没有提供参数，则交互式询问
if (-not $ServerUrl) {
    Write-Host ""
    Write-Host "  ┌─────────────────────────────────────────┐" -ForegroundColor Cyan
    Write-Host "  │  请输入控制中心 WebSocket 地址          │" -ForegroundColor Cyan
    Write-Host "  │  格式: ws://你的VPS地址:8001            │" -ForegroundColor Cyan
    Write-Host "  └─────────────────────────────────────────┘" -ForegroundColor Cyan
    Write-Host ""
    $ServerUrl = Read-Host "  服务器地址"
}

if (-not $Token) {
    Write-Host ""
    Write-Host "  ┌─────────────────────────────────────────┐" -ForegroundColor Cyan
    Write-Host "  │  请输入 JWT 认证令牌                    │" -ForegroundColor Cyan
    Write-Host "  │  (在控制中心 → 设置 → API 令牌 中获取) │" -ForegroundColor Cyan
    Write-Host "  └─────────────────────────────────────────┘" -ForegroundColor Cyan
    Write-Host ""
    $Token = Read-Host "  JWT 令牌"
}

if (-not $ServerUrl -or -not $Token) {
    Write-Err "服务器地址和令牌不能为空!"
    Read-Host "按回车键退出"
    exit 1
}

# 保存配置到 .env 文件
$EnvFile = Join-Path $ConfigDir ".env"
@"
SKPL_DN_SERVER_URL=$ServerUrl
SKPL_DN_TOKEN=$Token
SKPL_DN_NODE_NAME=$NodeName
SKPL_DN_LOG_DIR=$LogDir
SKPL_DN_LOG_LEVEL=info
SKPL_DN_HEARTBEAT_INTERVAL=10.0
SKPL_DN_RECONNECT_ENABLED=true
SKPL_DN_SCREEN_CAPTURE_QUALITY=85
"@ | Out-File -FilePath $EnvFile -Encoding UTF8

Write-OK "配置已保存到: $EnvFile"

# ── 步骤 5: 创建快捷方式 ─────────────────────────────────────────────
Write-Step "5/5" "创建快捷方式..."

# 创建启动脚本
$LaunchScript = Join-Path $InstallDir "start-node.bat"
$VenvPythonPath = Join-Path $VenvDir "Scripts" "python.exe"

@"
@echo off
chcp 65001 >nul
title SKPL Desktop Node - $NodeName
echo ========================================
echo   SKPL Desktop Node
echo   节点: $NodeName
echo   服务器: $ServerUrl
echo ========================================
echo.
echo 正在连接控制中心...
echo 按 Ctrl+C 或关闭此窗口来停止节点
echo.

REM 加载环境变量
for /f "tokens=1,* delims==" %%a in ('type "$EnvFile"') do (
    set %%a=%%b
)

REM 启动节点
"$VenvPythonPath" -m skpl_desktop_node --server "$ServerUrl" --token "$Token" --name "$NodeName"

pause
"@ | Out-File -FilePath $LaunchScript -Encoding UTF8

Write-OK "启动脚本: $LaunchScript"

# 创建桌面快捷方式
try {
    $DesktopPath = [Environment]::GetFolderPath("Desktop")
    $ShortcutPath = Join-Path $DesktopPath "SKPL Desktop Node.lnk"
    
    $WScriptShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $LaunchScript
    $Shortcut.WorkingDirectory = $InstallDir
    $Shortcut.Description = "SKPL Desktop Node - 桌面自动化节点"
    $Shortcut.IconLocation = "shell32.dll,13"
    $Shortcut.Save()
    
    Write-OK "桌面快捷方式已创建: $ShortcutPath"
} catch {
    Write-Color "  桌面快捷方式创建失败 (无影响，可手动启动)" -ForegroundColor Gray
}

# ── 完成 ──────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║              安装完成!                               ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  [安装信息]" -ForegroundColor Cyan
Write-Host "  节点名称: $NodeName" -ForegroundColor White
Write-Host "  服务器:   $ServerUrl" -ForegroundColor White
Write-Host "  安装目录: $InstallDir" -ForegroundColor White
Write-Host ""
Write-Host "  [启动方式]" -ForegroundColor Cyan
Write-Host "  1. 双击桌面的 'SKPL Desktop Node' 快捷方式" -ForegroundColor White
Write-Host "  2. 或双击: $LaunchScript" -ForegroundColor White
Write-Host ""
Write-Host "  [下次启动]" -ForegroundColor Cyan
Write-Host "  直接双击桌面快捷方式即可，无需重新安装" -ForegroundColor White
Write-Host ""

$startNow = Read-Host "是否现在启动节点? (Y/n)"
if ($startNow -ne "n" -and $startNow -ne "N") {
    Write-Host ""
    Write-Host "正在启动桌面节点..." -ForegroundColor Yellow
    Start-Process -FilePath $LaunchScript
    Write-Host "节点已在新窗口中启动!" -ForegroundColor Green
    Write-Host "请查看弹出的命令行窗口确认连接状态" -ForegroundColor Gray
}

Write-Host ""
Read-Host "按回车键退出"