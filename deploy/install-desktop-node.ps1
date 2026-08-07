# SKPL Desktop Node — Windows Installer Script
# Run this script in PowerShell to install and configure the desktop node.
#
# Usage:
#   .\install-desktop-node.ps1 -ServerUrl "ws://your-vps:8000" -Token "your-jwt-token"
#
# Parameters:
#   -ServerUrl   : WebSocket URL of the control center (required)
#   -Token       : JWT authentication token (required)
#   -NodeName    : Human-readable node name (default: computer hostname)
#   -InstallDir  : Installation directory (default: $env:LOCALAPPDATA\skpl-desktop-node)
#   -PythonPath  : Path to Python executable (auto-detected if not provided)

param(
    [Parameter(Mandatory=$true)]
    [string]$ServerUrl,

    [Parameter(Mandatory=$true)]
    [string]$Token,

    [string]$NodeName = $env:COMPUTERNAME,

    [string]$InstallDir = "$env:LOCALAPPDATA\skpl-desktop-node",

    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " SKPL Desktop Node Installer v0.2.0" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Check Python ────────────────────────────────────────────────────
Write-Host "[1/5] Checking Python installation..." -ForegroundColor Yellow

if ($PythonPath -eq "") {
    $PythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $PythonPath) {
        $PythonPath = (Get-Command python3 -ErrorAction SilentlyContinue).Source
    }
    if (-not $PythonPath) {
        Write-Host "ERROR: Python not found. Please install Python 3.10+ from https://python.org" -ForegroundColor Red
        exit 1
    }
}

$PythonVersion = & $PythonPath --version 2>&1
Write-Host "  Found: $PythonVersion ($PythonPath)" -ForegroundColor Green

# ── Step 2: Create directories ──────────────────────────────────────────────
Write-Host "[2/5] Creating installation directory..." -ForegroundColor Yellow

$DataDir = Join-Path $InstallDir "data"
$LogDir = Join-Path $InstallDir "logs"
$ConfigDir = Join-Path $InstallDir "config"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null

Write-Host "  Install directory: $InstallDir" -ForegroundColor Green

# ── Step 3: Install dependencies ────────────────────────────────────────────
Write-Host "[3/5] Installing Python dependencies..." -ForegroundColor Yellow

# Create requirements file
$RequirementsPath = Join-Path $ConfigDir "requirements.txt"
@"
# SKPL Desktop Node dependencies
pyautogui>=0.9.54
pillow>=10.0.0
mss>=9.0.0
websockets>=12.0
keyboard>=0.13.5
psutil>=5.9.0
"@ | Out-File -FilePath $RequirementsPath -Encoding UTF8

& $PythonPath -m pip install -r $RequirementsPath --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install dependencies" -ForegroundColor Red
    exit 1
}
Write-Host "  Dependencies installed successfully" -ForegroundColor Green

# ── Step 4: Create configuration ────────────────────────────────────────────
Write-Host "[4/5] Creating configuration..." -ForegroundColor Yellow

$EnvFile = Join-Path $ConfigDir ".env"
@"
# SKPL Desktop Node Configuration
SKPL_DN_SERVER_URL=$ServerUrl
SKPL_DN_TOKEN=$Token
SKPL_DN_NODE_NAME=$NodeName
SKPL_DN_DATA_DIR=$DataDir
SKPL_DN_LOG_DIR=$LogDir
SKPL_DN_LOG_LEVEL=info
SKPL_DN_MAX_CONCURRENT_ACTIONS=3
SKPL_DN_RECONNECT_MAX_ATTEMPTS=-1
SKPL_DN_RECONNECT_BASE_DELAY=1.0
SKPL_DN_RECONNECT_MAX_DELAY=60.0
SKPL_DN_HEARTBEAT_INTERVAL=10.0
SKPL_DN_HEARTBEAT_TIMEOUT=30.0
SKPL_DN_SCREEN_CAPTURE_METHOD=pyautogui
SKPL_DN_SCREEN_CAPTURE_QUALITY=85
SKPL_DN_GROUNDING_ENABLED=false
SKPL_DN_GROUNDING_DEVICE=cpu
SKPL_DN_OCR_ENABLED=false
"@ | Out-File -FilePath $EnvFile -Encoding UTF8

Write-Host "  Config saved to: $EnvFile" -ForegroundColor Green

# ── Step 5: Create launch script ────────────────────────────────────────────
Write-Host "[5/5] Creating launch scripts..." -ForegroundColor Yellow

# Batch file for easy launch
$BatchPath = Join-Path $InstallDir "start-node.bat"
@"
@echo off
echo Starting SKPL Desktop Node...
echo Node: $NodeName
echo Server: $ServerUrl
echo.

REM Load environment variables
for /f "tokens=*" %%a in ($ConfigDir\.env) do set %%a

REM Start the desktop node
cd /d "$InstallDir"
"$PythonPath" -m skpl_agent.desktop_node.cli ^
    --server "$ServerUrl" ^
    --token "$Token" ^
    --name "$NodeName" ^
    --log-level info

pause
"@ | Out-File -FilePath $BatchPath -Encoding ASCII

# PowerShell launch script
$PsLaunchPath = Join-Path $InstallDir "start-node.ps1"
@"
# SKPL Desktop Node — Launch Script
param(
    [string]$LogLevel = "info"
)

`$env:SKPL_DN_SERVER_URL = "$ServerUrl"
`$env:SKPL_DN_TOKEN = "$Token"
`$env:SKPL_DN_NODE_NAME = "$NodeName"
`$env:SKPL_DN_DATA_DIR = "$DataDir"
`$env:SKPL_DN_LOG_DIR = "$LogDir"
`$env:SKPL_DN_LOG_LEVEL = `$LogLevel

Write-Host "Starting SKPL Desktop Node..." -ForegroundColor Cyan
Write-Host "  Node: $NodeName" -ForegroundColor Gray
Write-Host "  Server: $ServerUrl" -ForegroundColor Gray

& "$PythonPath" -m skpl_agent.desktop_node.cli `
    --server "$ServerUrl" `
    --token "$Token" `
    --name "$NodeName" `
    --log-level `$LogLevel
"@ | Out-File -FilePath $PsLaunchPath -Encoding UTF8

# Create Start Menu shortcut
$ShortcutPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\SKPL Desktop Node.lnk"
$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$PsLaunchPath`""
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.Description = "SKPL Desktop Node"
$Shortcut.Save()

Write-Host "  Launch scripts created:" -ForegroundColor Green
Write-Host "    $BatchPath" -ForegroundColor Gray
Write-Host "    $PsLaunchPath" -ForegroundColor Gray
Write-Host "  Start Menu shortcut created" -ForegroundColor Gray

# ── Done ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start the desktop node:" -ForegroundColor White
Write-Host "  1. Double-click 'SKPL Desktop Node' in Start Menu" -ForegroundColor Gray
Write-Host "  2. Or run: $BatchPath" -ForegroundColor Gray
Write-Host "  3. Or run: powershell -File `"$PsLaunchPath`"" -ForegroundColor Gray
Write-Host ""
Write-Host "The node will connect to: $ServerUrl" -ForegroundColor Gray
Write-Host "Node name: $NodeName" -ForegroundColor Gray
Write-Host ""