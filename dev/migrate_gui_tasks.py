"""Refresh cached GUI task definitions before launch, preserving device settings."""

import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RENAMED = {"GT_SignIn": "GT_SignInAndSoul", "GT_ShopBenefits": "GT_ShopPurchase",
           "GT_AwakeningFreeSweep": "GT_GeneralDailySweep"}


def migrate(config: dict, tasks: list[dict]) -> dict:
    definitions = {task["entry"]: task for task in tasks}
    cached = {}
    for task in config.get("TaskItems", []):
        entry = RENAMED.get(task.get("entry"), task.get("entry"))
        if entry in definitions:
            cached[entry] = {**task, **definitions[entry]}
            if "default_check" in task:
                cached[entry]["default_check"] = task["default_check"]
    config["TaskItems"] = [cached.get(task["entry"], task) for task in tasks]
    ordered = []
    for value in config.get("CurrentTasks", []):
        entry = value.split("<|||>")[-1]
        entry = RENAMED.get(entry, entry)
        if entry in definitions and entry not in ordered: ordered.append(entry)
    ordered.extend(entry for entry in definitions if entry not in ordered)
    config["CurrentTasks"] = [definitions[entry]["name"] + "<|||>" + entry for entry in ordered]
    return config


def main():
    # Process paths may be inaccessible under a restricted token. Checking names
    # conservatively prevents mistaking an unreadable path for a closed GUI.
    query = "@(Get-Process -Name GTAssistant,MFAAvalonia -ErrorAction SilentlyContinue).Count"
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", query],
                            capture_output=True, text=True, timeout=30,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode or not result.stdout.strip().isdigit():
        raise RuntimeError("Cannot verify GUI state before refreshing its task cache")
    if int(result.stdout.strip()):
        print("GUI is open; task cache refresh deferred until next launch")
        return 0
    tasks = json.loads((ROOT / "interface.json").read_text(encoding="utf-8"))["task"]
    for path in (ROOT / "config/instances").glob("*.json"):
        original = path.read_text(encoding="utf-8")
        config = migrate(json.loads(original), tasks)
        updated = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
        if original == updated:
            continue
        backup = ROOT / "backup/task-cache"
        backup.mkdir(parents=True, exist_ok=True)
        saved = backup / path.name
        if not saved.exists(): saved.write_text(original, encoding="utf-8")
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(updated, encoding="utf-8")
        temporary.replace(path)
    return 0


if __name__ == "__main__": raise SystemExit(main())
