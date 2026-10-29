# 坎公助手的程序文件

主程序名保留 `GTAssistant.exe`，以兼容现有快捷方式与总调度；界面名称为“MGA 坎公助手”。
双击 `GTAssistant.bat` 或原有 `run_gui.bat` 均可启动同一程序。首次导入原版运行包后，启动器会将 `MFAAvalonia.exe` 改名为 `GTAssistant.exe`。

只重命名 .NET apphost EXE。`MFAAvalonia.dll`、`MFAAvalonia.deps.json` 和 `MFAAvalonia.runtimeconfig.json` 以及 `libs/`、`runtimes/` 是加载依赖，保留其原名。`MaaPiCli.exe` 保留框架命令行工具原名，仍由 `run_cli.bat` 启动。

`GTAssistant.exe` 内嵌图标已替换为 `logo-v2.ico` 中的小公主笑脸。若上游更新恢复默认图标，关闭助手后执行 `python dev/set_exe_icon.py` 即可重新嵌入；原程序会备份到 `backup/`。`python dev/set_exe_icon.py --verify` 只校验内嵌图标，不修改文件。

文件管理器显示旧图标时，执行 `python dev/refresh_icon_cache.py`：先逐尺寸核验内嵌图标，再更新时间戳并通知Windows刷新图标缓存，不替换运行中的EXE，不关闭助手、不重启Explorer。已核验工作目录快捷方式的图标指向 `logo-v2.ico`。可在文件管理器按F5刷新显示。

## 结束后行为

任务列表末尾的“关闭游戏”默认不勾选，使用MaaFramework的 `StopApp` 关闭 `com.bilibili.snake`，保留助手与MuMu。要关闭游戏时将其放在所有游戏任务之后；不需要启动游戏或返回大厅才能执行。

退出助手使用现有GUI设置：**设置 → 启动设置 → 结束后操作 → 关闭本程序**。默认“无”，不增加退出助手的脚本任务，也不修改用户当前退出设置。该选项在MFAAvalonia 2.16.2中已提供，界面绑定 `AfterTaskList/AfterTask`，实例配置键为 `AfterTask`，退出值为 `CloseMFA`。
来源：[固定版本设置界面](https://github.com/MaaXYZ/MFAAvalonia/blob/v2.16.2/MFAAvalonia/Views/UserControls/Settings/StartSettingsUserControl.axaml)、[设置选项](https://github.com/MaaXYZ/MFAAvalonia/blob/v2.16.2/MFAAvalonia/ViewModels/UsersControls/Settings/StartSettingsUserControlModel.cs)。

工作目录中的独立 `MaaFramework-win-x86_64-v5.12.3/` 和 `MFAAvalonia-v2.16.2-win-x64/` 为导入来源和开发参考，不是当前程序的运行路径，日常运行可以将它们移走或归档。离线查看框架头文件、文档或恢复原始运行包时仍可能用到。

项目内的 `resource/pipeline/`、`resource/image/`、`resource/model/` 是实际任务、识别模板和OCR模型，必须保留。`agent/`、`config/`、`libs/`、`runtimes/` 同样是当前运行所需。
`dev/screenshots/` 等开发截图不是运行依赖，但截图回归测试会使用它们，因此继续完善脚本时建议保留。

本次不删除目录。自带 GUI 更新器可能恢复上游 EXE 文件名；此时继续用 `GTAssistant.bat` 启动即可重新统一文件名。
