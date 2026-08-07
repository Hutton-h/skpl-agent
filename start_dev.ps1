#!/usr/bin/env pwsh
<#
.SYNOPSIS
    SKPL Agent 开发环境进程守护脚本
.DESCRIPTION
    自动启动后端和前端服务，监控进程状态，崩溃后自动重启。
    使用 Ctrl+C 停止所有服务。
#>

param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [switch]$NoFrontend
)

$ErrorActionPreference = "Stop"
$script:BackendProcess = $null
$script:FrontendProcess = $null
$script:Running = $true

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Success($msg) { Write-Host "[OK]   $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Error($msg) { Write-Host "[ERR]  $msg" -ForegroundColor Red }

function Stop-All {
    if ($script:Running) {
        Write-Info "Stopping all services..."
        $script:Running = $false
        if ($script:BackendProcess -and !$script:BackendProcess.HasExited) {
            $script:BackendProcess.Kill($true)
        }
        if ($script:FrontendProcess -and !$script:FrontendProcess.HasExited) {
            $script:FrontendProcess.Kill($true)
        }
        Write-Success "All services stopped"
    }
}

function Test-PortAvailable($port) {
    $listener = $null
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
        $listener.Start()
        return $true
    } catch { return $false }
    finally { if ($listener) { $listener.Stop() } }
}

function Start-Backend {
    if (!(Test-PortAvailable $BackendPort)) {
        Write-Warn "Port $BackendPort already in use, backend may be running"
        return $true
    }
    Write-Info "Starting backend (port $BackendPort)..."
    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = "python"
    $psi.Arguments = "-m skpl_agent"
    $psi.WorkingDirectory = $BackendDir
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.EnvironmentVariables["PYTHONUNBUFFERED"] = "1"
    $script:BackendProcess = [System.Diagnostics.Process]::new()
    $script:BackendProcess.StartInfo = $psi
    $script:BackendProcess.add_OutputDataReceived({
        if ($EventArgs.Data) { Write-Host "[BACKEND] $($EventArgs.Data)" -ForegroundColor DarkGray }
    })
    $script:BackendProcess.add_ErrorDataReceived({
        if ($EventArgs.Data) { Write-Host "[BACKEND] $($EventArgs.Data)" -ForegroundColor DarkRed }
    })
    try {
        $script:BackendProcess.Start() | Out-Null
        $script:BackendProcess.BeginOutputReadLine()
        $script:BackendProcess.BeginErrorReadLine()
        for ($i = 0; $i -lt 60; $i++) {
            Start-Sleep -Seconds 1
            if ($script:BackendProcess.HasExited) {
                Write-Error "Backend exited (code: $($script:BackendProcess.ExitCode))"
                return $false
            }
            if (!(Test-PortAvailable $BackendPort)) {
                Write-Success "Backend ready (port $BackendPort)"
                return $true
            }
        }
        Write-Error "Backend startup timeout"
        return $false
    } catch { Write-Error "Backend error: $_"; return $false }
}

function Start-Frontend {
    if (!(Test-PortAvailable $FrontendPort)) {
        Write-Warn "Port $FrontendPort already in use"
        return $true
    }
    Write-Info "Starting frontend (port $FrontendPort)..."
    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = "npx"
    $psi.Arguments = "vite --host 127.0.0.1 --port $FrontendPort"
    $psi.WorkingDirectory = $FrontendDir
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $script:FrontendProcess = [System.Diagnostics.Process]::new()
    $script:FrontendProcess.StartInfo = $psi
    $script:FrontendProcess.add_OutputDataReceived({
        if ($EventArgs.Data) { Write-Host "[FRONTEND] $($EventArgs.Data)" -ForegroundColor DarkGray }
    })
    $script:FrontendProcess.add_ErrorDataReceived({
        if ($EventArgs.Data) { Write-Host "[FRONTEND] $($EventArgs.Data)" -ForegroundColor DarkYellow }
    })
    try {
        $script:FrontendProcess.Start() | Out-Null
        $script:FrontendProcess.BeginOutputReadLine()
        $script:FrontendProcess.BeginErrorReadLine()
        for ($i = 0; $i -lt 30; $i++) {
            Start-Sleep -Seconds 1
            if ($script:FrontendProcess.HasExited) {
                Write-Error "Frontend exited (code: $($script:FrontendProcess.ExitCode))"
                return $false
            }
            if (!(Test-PortAvailable $FrontendPort)) {
                Write-Success "Frontend ready (port $FrontendPort)"
                return $true
            }
        }
        Write-Error "Frontend startup timeout"
        return $false
    } catch { Write-Error "Frontend error: $_"; return $false }
}

function Watch-Processes {
    $backendRestarts = 0
    $frontendRestarts = 0
    $maxRestarts = 10
    while ($script:Running) {
        if ($script:BackendProcess -and $script:BackendProcess.HasExited) {
            Write-Warn "Backend exited (code: $($script:BackendProcess.ExitCode))"
            $backendRestarts++
            if ($backendRestarts -gt $maxRestarts) { Write-Error "Max restarts reached"; break }
            Write-Info "Restarting backend (attempt $backendRestarts)..."
            Start-Sleep -Seconds 3
            if (Start-Backend) { Write-Success "Backend restarted" }
        }
        if (!$NoFrontend -and $script:FrontendProcess -and $script:FrontendProcess.HasExited) {
            Write-Warn "Frontend exited (code: $($script:FrontendProcess.ExitCode))"
            $frontendRestarts++
            if ($frontendRestarts -gt $maxRestarts) { Write-Error "Max restarts reached"; break }
            Write-Info "Restarting frontend (attempt $frontendRestarts)..."
            Start-Sleep -Seconds 3
            if (Start-Frontend) { Write-Success "Frontend restarted" }
        }
        Start-Sleep -Seconds 5
    }
}

# Main
Write-Host "`n=== SKPL Agent Dev Daemon ===`n" -ForegroundColor Cyan
[Console]::CancelKeyPress += {
    Write-Host "`nCtrl+C received, stopping..."
    Stop-All
    exit 0
}
if (!(Test-Path $BackendDir)) { Write-Error "Backend dir not found: $BackendDir"; exit 1 }
if (!(Test-Path $FrontendDir)) { Write-Error "Frontend dir not found: $FrontendDir"; exit 1 }
if (!(Start-Backend)) { Write-Error "Backend failed"; Stop-All; exit 1 }
if (!$NoFrontend) { if (!(Start-Frontend)) { Write-Error "Frontend failed"; Stop-All; exit 1 } }
Write-Host "`nAll services started!`n  Backend: http://127.0.0.1:$BackendPort`n  Frontend: http://127.0.0.1:$FrontendPort`n  Ctrl+C to stop`n" -ForegroundColor Green
Watch-Processes