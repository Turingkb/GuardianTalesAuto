@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "MGA_PYTHON=%~dp0runtimes\python\python.exe"
if not exist "%MGA_PYTHON%" set "MGA_PYTHON=python"
rem .NET apphost can be renamed; its MFAAvalonia DLL and JSON files must keep their names.
if not exist "%~dp0GTAssistant.exe" (
    if exist "%~dp0MFAAvalonia.exe" (
        move "%~dp0MFAAvalonia.exe" "%~dp0GTAssistant.exe" >nul
        if errorlevel 1 (
            echo [MGA 坎公助手] 无法重命名程序，请先关闭本项目的 GUI。
            pause
            exit /b 1
        )
    )
)
if not exist "%~dp0GTAssistant.exe" (
    echo [MGA 坎公助手] 缺少 GTAssistant.exe，请先导入 MFAAvalonia 运行包。
    pause
    exit /b 1
)
"%MGA_PYTHON%" "%~dp0dev\launch_gui.py" %*
if errorlevel 1 (
    echo [MGA 坎公助手] 启动检查未通过，请查看以上错误。
    pause
    exit /b 1
)
exit /b 0
