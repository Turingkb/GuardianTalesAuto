@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem .NET apphost can be renamed; its MFAAvalonia DLL and JSON files must keep their names.
if not exist "%~dp0GTAssistant.exe" (
    if exist "%~dp0MFAAvalonia.exe" (
        move "%~dp0MFAAvalonia.exe" "%~dp0GTAssistant.exe" >nul
        if errorlevel 1 (
            echo [坎公骑冠剑助手] 无法重命名程序，请先关闭本项目的 GUI。
            pause
            exit /b 1
        )
    )
)
if not exist "%~dp0GTAssistant.exe" (
    echo [坎公骑冠剑助手] 缺少 GTAssistant.exe，请先导入 MFAAvalonia 运行包。
    pause
    exit /b 1
)
start "坎公骑冠剑助手" "%~dp0GTAssistant.exe"
