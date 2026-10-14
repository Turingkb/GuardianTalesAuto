@echo off
chcp 65001 >nul
rem =====================================================================
rem  GuardianTalesAuto 启动器
rem
rem  直接双击本脚本即可，等价于运行工程根目录的 MaaPiCli.exe。
rem
rem  说明：MaaPiCli 会把「MaaFramework.dll 所在目录」当作项目根，
rem       所以本工程根目录下同时存放了 MaaPiCli.exe 与框架的全部 DLL
rem        （见 README.md「运行时文件」一节），双击运行不需要任何环境配置。
rem
rem  菜单速查：
rem    1. Switch controller  切换控制器（换模拟器/换端口时用）
rem    2. Switch resource    切换资源包
rem    3. Add task           添加任务（勾选要跑的任务）
rem    4. Move task          调整任务顺序（自上而下依次执行）
rem    5. Delete task        删除任务
rem    6. Run tasks          开始执行
rem    7. Exit               退出
rem =====================================================================

cd /d "%~dp0"
rem GUI 会整理原生库到 runtimes。CLI 则仍需在工程根目录找到 DLL。
if exist "%~dp0runtimes\win-x64\native\MaaFramework.dll" (
    for %%F in ("%~dp0runtimes\win-x64\native\*.dll") do copy /Y "%%~fF" "%~dp0" >nul
)
if exist "%~dp0libs\MaaAgentBinary" (
    xcopy /E /I /Y "%~dp0libs\MaaAgentBinary" "%~dp0MaaAgentBinary" >nul
)
echo [GuardianTalesAuto] 工程目录: %CD%
echo [GuardianTalesAuto] 提示：想跑哪个任务，先按 3 添加，再按 6 执行。
echo.
"%~dp0MaaPiCli.exe"
pause
