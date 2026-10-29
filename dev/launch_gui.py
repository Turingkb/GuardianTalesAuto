"""Check the portable environment before launching the existing MFA GUI."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DOTNET_URL = "https://dotnet.microsoft.com/download/dotnet/10.0"


def find_dotnet() -> str | None:
    candidates = []
    for variable in ("ProgramFiles", "DOTNET_ROOT"):
        directory = os.environ.get(variable)
        if directory:
            candidates.append(str(Path(directory) / ("dotnet.exe" if variable == "DOTNET_ROOT" else "dotnet/dotnet.exe")))
    candidates.append(shutil.which("dotnet"))
    for candidate in candidates:
        if not candidate or not Path(candidate).is_file():
            continue
        with Path(candidate).open("rb") as file:
            header = file.read(64)
            if len(header) != 64 or header[:2] != b"MZ":
                continue
            file.seek(struct.unpack_from("<I", header, 60)[0])
            pe = file.read(6)
        if pe == b"PE\0\0\x64\x86":
            return candidate
    return None


def check_environment(root: Path) -> list[str]:
    problems = []
    if sys.version_info < (3, 10):
        problems.append("需要 Python 3.10 或以上；便携包请完整解压 runtimes/python。")
    if sys.platform != "win32" or sys.maxsize <= 2**32:
        problems.append("此运行包仅支持 Windows x64。")
    required = ["GTAssistant.exe", "MFAAvalonia.dll", "MFAAvalonia.deps.json",
                "MFAAvalonia.runtimeconfig.json", "interface.json", "agent/main.py",
                "runtimes/win-x64/native/MaaFramework.dll", "runtimes/win-x64/native/MaaAgentServer.dll",
                "resource/model/ocr/det.onnx", "resource/model/ocr/rec.onnx", "resource/model/ocr/keys.txt"]
    for name in required:
        if not (root / name).is_file():
            problems.append("缺少运行文件：" + name)
    dotnet = find_dotnet()
    runtimes = ""
    if dotnet:
        result = subprocess.run([dotnet, "--list-runtimes"], capture_output=True, text=True,
                                timeout=30, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode == 0:
            runtimes = result.stdout
    if not re.search(r"^Microsoft\.NETCore\.App 10\.", runtimes, re.MULTILINE):
        problems.append("未检测到 .NET 10 x64 Runtime。请从微软官方页面安装后重试：" + DOTNET_URL)
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check without opening the GUI or connecting a device")
    args = parser.parse_args()
    problems = check_environment(ROOT)
    if problems:
        for problem in problems:
            print("[MGA] " + problem)
        return 1
    print("[MGA] 运行文件、Python 与 .NET 10 检查通过。")
    if args.check:
        return 0
    interface = json.loads((ROOT / "interface.json").read_text(encoding="utf-8"))
    # A portable path is resolved by the GUI relative to the project directory.
    # The interpreter's explicit _pth also includes agent/ and dev/.
    if (ROOT / "runtimes/python/python.exe").is_file():
        expected = "runtimes/python/python.exe"
        if interface["agent"][0]["child_exec"] != expected:
            print("[MGA] 便携包的 Agent Python 路径不正确，请重新解压完整运行包。")
            return 1
    from migrate_gui_tasks import main as migrate
    if migrate():
        return 1
    subprocess.Popen([str(ROOT / "GTAssistant.exe")], cwd=ROOT,
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
