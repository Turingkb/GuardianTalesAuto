"""Assemble a Windows portable package from a Git commit and pinned official inputs."""

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = {"GTAssistant.bat", "run_gui.bat", "run_cli.bat", "README.md", "LICENSE", "ABOUT.md",
         "CONTACT.md", "WELCOME.md", "THIRD_PARTY_NOTICES.md", "logo-v2.ico",
         "dev/launch_gui.py", "dev/migrate_gui_tasks.py", "dev/set_exe_icon.py",
         "dev/validate_project.py", "dev/smoke_portable.py", "dev/release.lock.json",
         "dev/repository-setup.md", "dev/public-readiness.md", "dev/portable-release.md", "interface.json"}
PREFIXES = ("agent/", "assets/", "resource/pipeline/", "resource/image/", "licenses/")
HOSTS = {"github.com", "codeload.github.com", "raw.githubusercontent.com", "www.python.org"}
FIRST_LAUNCH_SETTINGS = {"BeforeTask": "None", "AfterTask": "None", "AutoConnectAfterRefresh": False}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as file:
        while block := file.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def destination(root: Path, name: str) -> Path:
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or ".." in path.parts or "\\" in name or ":" in name:
        raise ValueError(f"Unsafe archive path: {name!r}")
    target = root.joinpath(*path.parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Archive path escapes target: {name!r}")
    return target


def extract(archive: zipfile.ZipFile, root: Path, select) -> None:
    if sum(info.file_size for info in archive.infolist()) > 2 * 1024**3:
        raise ValueError("Archive exceeds the extraction size limit")
    for info in archive.infolist():
        name = select(info.filename)
        if name is None or info.is_dir():
            continue
        if stat.S_ISLNK(info.external_attr >> 16):
            raise ValueError("Archive symlinks are not accepted: " + info.filename)
        target = destination(root, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as source, target.open("wb") as output:
            shutil.copyfileobj(source, output)


def fetch(component: dict, cache: Path) -> Path:
    url = urllib.parse.urlsplit(component["url"])
    if url.scheme != "https" or url.hostname not in HOSTS or url.username or url.password:
        raise ValueError("Dependency URL must use an approved official HTTPS host")
    target = destination(cache, component["file"])
    if not target.exists():
        partial = target.with_suffix(target.suffix + ".part")
        request = urllib.request.Request(component["url"], headers={"User-Agent": "MGA-portable-builder"})
        with urllib.request.urlopen(request, timeout=180) as source, partial.open("wb") as output:
            shutil.copyfileobj(source, output)
        if digest(partial) != component["sha256"]:
            raise ValueError("Downloaded SHA-256 mismatch: " + component["file"])
        partial.replace(target)
    if digest(target) != component["sha256"]:
        raise ValueError("Cached SHA-256 mismatch: " + component["file"])
    print("Verified " + component["file"], flush=True)
    return target


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(ref: str, cache: Path, output: Path) -> Path:
    commit = subprocess.check_output(["git", "rev-parse", "--verify", "--end-of-options", ref + "^{commit}"], cwd=ROOT).decode().strip()
    epoch = int(subprocess.check_output(["git", "show", "-s", "--format=%ct", commit], cwd=ROOT))
    source = subprocess.check_output(["git", "archive", "--format=zip", commit], cwd=ROOT)
    with zipfile.ZipFile(io.BytesIO(source)) as snapshot:
        interface = json.loads(snapshot.read("interface.json"))
        lock = json.loads(snapshot.read("dev/release.lock.json"))
        version = interface["version"]
        if not all(part.isdigit() for part in version.split(".")) or len(version.split(".")) != 3:
            raise ValueError("Package version must have three numeric components")
        folder = "MGA-v" + version + "-win-x64"
        output.mkdir(parents=True, exist_ok=True)
        cache.mkdir(parents=True, exist_ok=True)
        stage = output / (folder + "-" + commit[:7])
        stage.mkdir()  # Never reuse a possibly dirty package directory.
        extract(snapshot, stage, lambda name: name if name in FILES or name.startswith(PREFIXES) else None)
    inputs = {item["id"]: (item, fetch(item, cache)) for item in lock["components"]}
    with zipfile.ZipFile(inputs["gui"][1]) as archive:
        extract(archive, stage, lambda name: name if name.startswith(("libs/", "runtimes/"))
                or name in {"MFAAvalonia.exe", "MFAAvalonia.dll", "MFAAvalonia.deps.json",
                            "MFAAvalonia.runtimeconfig.json", "libloader.dll"} else None)
    with zipfile.ZipFile(inputs["framework"][1]) as archive:
        def framework_path(name):
            if name == "bin/MaaPiCli.exe":
                return "MaaPiCli.exe"
            if name.startswith("bin/") and name.endswith(".dll") and "/plugins/" not in name:
                return "runtimes/win-x64/native/" + name[len("bin/"):]
            if name.startswith("share/MaaAgentBinary/"):
                return "libs/MaaAgentBinary/" + name[len("share/MaaAgentBinary/"):]
            return None
        extract(archive, stage, framework_path)
    with zipfile.ZipFile(inputs["python"][1]) as archive:
        extract(archive, stage / "runtimes/python", lambda name: name)
    python_path = stage / "runtimes/python"
    (python_path / "python314._pth").write_text("python314.zip\n.\n../../agent\n../../dev\n", encoding="utf-8")
    for key, (_, path) in inputs.items():
        if key.startswith("ocr_") and key != "ocr_license":
            model = stage / "resource/model/ocr" / key[len("ocr_"):]
            model.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, model)
        elif key.endswith("_source"):
            target = stage / "source/upstream" / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    shutil.copyfile(inputs["ocr_license"][1], stage / "licenses/MaaCommonAssets-MIT.txt")
    shutil.copyfile(python_path / "LICENSE.txt", stage / "licenses/Python-LICENSE.txt")
    (stage / "source/MGA-source.zip").write_bytes(source)
    interface["agent"][0]["child_exec"] = "runtimes/python/python.exe"
    write_json(stage / "interface.json", interface)
    (stage / "MFAAvalonia.exe").rename(stage / "GTAssistant.exe")
    subprocess.run([sys.executable, str(stage / "dev/set_exe_icon.py"), "--exe", str(stage / "GTAssistant.exe"),
                    "--icon", str(stage / "logo-v2.ico")], check=True, cwd=stage)
    # The icon tool preserves a local backup. A release contains only the final executable.
    backup = stage / "backup"
    if backup.exists():
        if not backup.resolve().is_relative_to(stage.resolve()):
            raise ValueError("Unexpected backup path")
        shutil.rmtree(backup)
    config = stage / "config"
    config.mkdir()
    write_json(config / "config.template.json", FIRST_LAUNCH_SETTINGS)
    package_readme = ("# MGA 便携包 " + version + "\n\n解压全部文件，双击 `run_gui.bat` 启动。"
                      "已内置 Python、OCR 模型和框架；需要 .NET 10 x64 Runtime，启动时会检查。"
                      "首次自行选择模拟器，不包含开发者账号配置。\n\n"
                      "需要检查环境时运行 `GTAssistant.bat --check`。升级请解压到新目录，备份旧配置后按需迁移，"
                      "不要覆盖或删除正在使用的 config。\n\n---\n\n")
    readme = stage / "README.md"
    readme.write_text(package_readme + readme.read_text(encoding="utf-8"), encoding="utf-8")
    write_json(stage / "build-info.json", {"project": "MGA", "version": version, "commit": commit,
               "source_date_epoch": epoch, "inputs": lock,
               "modifications": ["MFAAvalonia apphost renamed and icon replaced; assemblies unchanged",
                                 "Python _pth includes project agent and dev modules",
                                 "Project Interface selects embedded Python; no personal configuration"]})
    check_package(stage)
    subprocess.run([str(python_path / "python.exe"), "-X", "utf8", "-B", str(stage / "dev/validate_project.py")], check=True, cwd=output)
    subprocess.run([str(python_path / "python.exe"), "-X", "utf8", "-B", str(stage / "dev/smoke_portable.py")], check=True, cwd=output)
    check_package(stage)
    manifest = {path.relative_to(stage).as_posix(): digest(path) for path in sorted(stage.rglob("*")) if path.is_file()}
    write_json(stage / "manifest.sha256.json", manifest)
    archive_path = output / (folder + "-" + commit[:7] + ".zip")
    if archive_path.exists():
        raise FileExistsError(archive_path)
    timestamp = datetime.fromtimestamp(max(epoch, 315532800), timezone.utc).timetuple()[:6]
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                info = zipfile.ZipInfo(folder + "/" + path.relative_to(stage).as_posix(), date_time=timestamp)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes())
    archive_path.with_suffix(".zip.sha256").write_text(digest(archive_path) + "  " + archive_path.name + "\n", encoding="ascii")
    print("PACKAGE " + str(archive_path), flush=True)
    return archive_path


def check_package(root: Path) -> None:
    forbidden = {"logs", "debug", "backup", "temp", "automation", ".git", "__pycache__"}
    for path in root.iterdir():
        if path.name in forbidden or path.name == "appsettings.json":
            raise ValueError("Personal or generated content in package: " + path.name)
    actual_config = {path.name for path in (root / "config").iterdir()}
    if actual_config != {"config.template.json"}:
        raise ValueError("Package configuration must only contain the safe first-launch template")
    if json.loads((root / "config/config.template.json").read_text(encoding="utf-8")) != FIRST_LAUNCH_SETTINGS:
        raise ValueError("First-launch configuration must not start tasks or close the GUI automatically")
    binary = root / "libs/MaaAgentBinary/maatouch/universal/maatouch"
    if not binary.is_file() or binary.stat().st_size < 10000:
        raise ValueError("Android input component is missing or a placeholder")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD", help="Exact committed source to package; uncommitted files are excluded")
    parser.add_argument("--cache", type=Path, default=ROOT / "dev/runtime/release-downloads")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    build(args.ref, args.cache.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
