# 从源码恢复本地运行环境

仓库维护脚本源码、任务定义、UI模板与当前图标。GUI二进制、OCR模型、用户配置、账号截图、日志和旧版备份保留在本地，不提交Git。

本次开发使用 MaaFramework 5.12.3、MFAAvalonia 2.16.2、Windows x64 Python 3.14（Agent仅使用标准库）。

新电脑上需准备上述运行时，将MFAAvalonia文件放入项目根目录，MaaFramework原生库放入 `runtimes/win-x64/native`，输入组件放入 `libs/MaaAgentBinary`，OCR模型放入 `resource/model/ocr`。保留各组件的许可证，来源与版本见根目录 `THIRD_PARTY_NOTICES.md`。安装与此GUI匹配的.NET 10 Runtime（Windows x64）。

Python最低版本3.10，开发机使用3.14；`python --version` 应能在命令行正常执行，`interface.json` 的 `agent.child_exec` 默认为 `python`，启动器同样使用PATH中的Python。若系统使用其它命令名称，需同时调整该字段和 `GTAssistant.bat`，不要照搬开发者的绝对路径。随后在GUI选择自己的ADB设备和模拟器路径。

开发截图回归依赖本地保存的 `dev/screenshots` 和 `dev/2026-10-14/screenshots`，仓库不附带账号画面。`dev/validate_project.py` 与 `dev/test_sweep_guards.py` 可用于源码静态及决策验证。

项目任务不会抽卡或现金充值。用户明确勾选并配置的商品可能消耗游戏内金币、钻石或星片。游戏UI模板与参考素材的权利归原权利人；本仓库不宣称获得游戏素材的再授权。
