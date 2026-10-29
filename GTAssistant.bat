@echo off
chcp 65001 >nul
cd /d "%~dp0"
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
python "%~dp0dev\migrate_gui_tasks.py"
if errorlevel 1 (
    echo [MGA 坎公助手] 更新任务配置失败，请查看以上错误。
    pause
    exit /b 1
)
start "MGA 坎公助手" "%~dp0GTAssistant.exe"
