# 架构来源、致谢与第三方声明

MGA 是基于 MaaFramework 的《坎公骑冠剑》自动化资源项目。通用桌面界面使用 MFAAvalonia，游戏流水线、识别模板、参数配置与 Python Agent 在本仓库维护。项目名称和图标替换不代表通用框架由 MGA 原创。

| 来源 | 使用范围 | 固定版本与许可证 |
| --- | --- | --- |
| [MaaFramework](https://github.com/MaaXYZ/MaaFramework) | Pipeline、OCR、图像识别、ADB 控制和 EmulatorExtras 截图能力 | [v5.12.3](https://github.com/MaaXYZ/MaaFramework/tree/v5.12.3)，[LGPL-3.0](https://github.com/MaaXYZ/MaaFramework/blob/v5.12.3/LICENSE.md) |
| [MFAAvalonia](https://github.com/MaaXYZ/MFAAvalonia) | Avalonia 桌面 GUI、任务配置、运行日志、设置、更新与结束后操作 | [v2.16.2](https://github.com/MaaXYZ/MFAAvalonia/tree/v2.16.2)，[GPL-3.0](https://github.com/MaaXYZ/MFAAvalonia/blob/v2.16.2/LICENSE) |
| [MaaAgentBinary](https://github.com/MaaXYZ/MaaAgentBinary) | 上游运行包中的安卓输入辅助组件 | 随框架包配套，AGPL-3.0；以实际分发包的 LICENSE 为准 |
| [M9A](https://github.com/MAA1999/M9A) | 日常任务组织、GUI 使用体验与模拟器截图方式的开发参考 | [AGPL-3.0](https://github.com/MAA1999/M9A/blob/main/LICENSE)；不是 MGA 的游戏脚本运行入口 |

感谢 MaaXYZ、MFAAvalonia、M9A 及其贡献者。MFAAvalonia 自身使用的 Avalonia、SukiUI、MaaFramework.Binding.CSharp 等依赖，请同时保留上游的声明和对应许可证。

## 本仓库与运行包

根目录 `LICENSE` 只授予本项目有权授权的原创代码和文档的 MIT 权利，不将第三方代码、游戏画面、角色设计或商标重新许可为 MIT。

当前 Git 仓库不保存 MaaFramework/MFAAvalonia 二进制、OCR 模型或个人运行配置。运行时应从固定版本的上游项目取得，并保留其许可证和源代码获取方式。`licenses/` 留存主要运行组件的许可证文本。

本机 `GTAssistant.exe` 来源于 MFAAvalonia 2.16.2 的 .NET apphost，修改仅为文件名和图标资源；配套 DLL 保留原名。本仓库的 `dev/set_exe_icon.py` 提供图标修改方法，`GTAssistant.bat` 提供文件名处理方法。分发整合运行包时还应附带上游相应版本源码及修改说明，遵守各组件的分发条件。

## 游戏素材

游戏名称、角色、UI 画面及商标归各自权利人所有。识别模板来自开发时游戏截图的局部裁剪，仅用于定位界面。小公主图标是参考游戏角色形象生成的像素图，不构成对原角色权利的取得或再授权。项目与游戏开发商、发行商和运营商无隶属关系，也不暗示其认可或担保。
