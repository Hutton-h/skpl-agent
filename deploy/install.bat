@echo off
chcp 65001 >nul
powershell.exe -ExecutionPolicy Bypass -NoProfile -Command "& { Invoke-Expression (Get-Content -Raw '%~dp0install.ps1') }"
pause