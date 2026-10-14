@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "%~dp0MFAAvalonia.exe" (
    echo [坎公骑冠剑助手] 缺少 MFAAvalonia.exe。
    pause
    exit /b 1
)
rem 使用完整路径，避免系统中其它同名 Maa GUI 的应用注册项。
start "坎公骑冠剑助手" "%~dp0MFAAvalonia.exe"
