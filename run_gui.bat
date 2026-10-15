@echo off
chcp 65001 >nul
call "%~dp0GTAssistant.bat"
exit /b %errorlevel%
