# Windows x64 便携包

## 使用

完整解压 ZIP 到有写入权限的文件夹，双击 `run_gui.bat`。运行包包含 GUI、框架原生库、安卓输入辅助组件、中文 OCR 模型及 Python 3.14.10，不需要另装 Python 或配置其 PATH。首次在 GUI 中选择模拟器。

需要 .NET 10 Runtime（Windows x64）。启动器检查实际 x64 dotnet 的 `Microsoft.NETCore.App 10.x`，缺少时显示微软官方安装页面，不自动下载或安装系统组件。

`GTAssistant.bat --check` 只检查环境，不连接设备或开始任务。不在压缩包预览窗口内直接运行程序。

首启模板明确使用 `BeforeTask=None`、`AfterTask=None`，不自动运行游戏任务或退出。GUI 仍可能在首次打开时尝试连接；没有选择设备时的连接失败提示，需要通过设备列表选择自己的模拟器处理。

更新时先解压到新目录，保留旧包和配置；按需复制自己的 `config/`，然后通过启动器迁移任务。不要删除或覆盖正在使用的目录。`GTAssistant.exe` 的文件名继续兼容原有快捷方式，总调度若直接运行 EXE，须先通过启动器完成环境检查和配置迁移。

## 构建

在 Windows x64、已安装 Python 3.10+ 与 Git 的开发环境中：

```powershell
python -m unittest discover -s dev -p "test_*.py"
python dev/validate_project.py
python dev/build_portable.py --ref HEAD
```

代码必须先提交。构建只读取指定 Git 提交，不复制工作区的个人配置或未提交修改。输出在 `dist/`，文件名包含版本、平台及源提交短哈希；已经存在的构建目录或压缩包不会被覆盖。失败后检查原目录，可用 `--output dist/retry` 重新构建。

下载缓存默认是 `dev/runtime/release-downloads`。`dev/release.lock.json` 固定官方 URL、版本和 SHA-256，包括：

- MFAAvalonia 2.16.2、MaaFramework 5.12.3；Windows x64 发布资产校验值来自 GitHub Release 元数据。
- Python 3.14.10 x64 embeddable ZIP；校验值来自 Python.org 对应版本页面。
- MaaCommonAssets 指定提交的中文 OCR 文件和许可证；文件与本项目原有实测模型一致。
- 上游 GUI、框架和配套 MaaAgentBinary 源码归档，以供许可证审阅与对应源码获取。

锁定输入校验失败即停止，不在运行时自动升级。便携 Python 的 `_pth` 显式配置本项目的 `agent/` 和 `dev/`，避免依赖开发者电脑的 Python 环境。

构建器会从官方输入组装新目录、重命名 GUI apphost 并嵌入本项目图标，随后用包内 Python 加载任务资源、原生 DLL 和实际中文 OCR。测试诊断写入包外的 `.checks/`，不进入发布 ZIP。

## 产物和发布

- `MGA-v<版本>-win-x64-<提交>.zip`：便携运行目录。
- 同名 `.zip.sha256`：外部压缩包 SHA-256，供下载后校验。
- 包内 `build-info.json`：完整源提交、固定输入及打包修改说明。
- 包内 `manifest.sha256.json`：打包前文件校验清单，不包含清单自身；用户启动后生成的配置和日志不属于初始清单。
- 包内 `source/`、`licenses/`：本项目和主要上游组件的对应源码、许可证。

发布时将 ZIP 与 `.sha256` 一起上传至与实际源提交对应的 GitHub Release，附上当前依赖要求与已执行验证。构建命令不创建远程标签、不上传资产，也不改变仓库公开状态。

本机干净目录检查不能代替未安装任何运行时的 Windows 虚拟机验收。游戏任务的验证范围仍以项目实测记录为准，打包通过不代表所有游戏版式都已适配。
