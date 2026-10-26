"""Refresh cached GUI task definitions before launch, preserving device settings."""

import json
import copy
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RENAMED = {"GT_SignIn": "GT_SignInAndSoul", "GT_ShopBenefits": "GT_ShopPurchase",
           "GT_AwakeningFreeSweep": "GT_GeneralDailySweep"}


def migrate_task_options(saved: list, names: list[str], definitions: dict) -> list[dict]:
    indexed = {}

    def collect(items):
        for item in items:
            if isinstance(item, dict):
                indexed[item["name"]] = copy.deepcopy(item)
                collect(item.get("sub_options", []))

    collect(saved)
    if "ShopFree" in indexed:
        free = indexed["ShopFree"].get("index", 0) == 0
        resource = indexed.get("ShopResources", {"name": "ShopResources", "index": 0})
        paid = resource.get("index", 0) == 1
        selected = indexed.get("ShopResourceProducts", {}).get("selected_cases", ["stamina"] if paid else [])
        selected = [name for name in selected if name != "free_coins"]
        if free: selected.append("free_coins")
        indexed["ShopResourceProducts"] = {"name": "ShopResourceProducts", "selected_cases": selected}
        resource["index"] = 1 if paid or free else 0
        indexed["ShopResources"] = resource

    def build(name):
        definition = definitions[name]
        item = copy.deepcopy(indexed.get(name, {"name": name}))
        children = list(definition.get("option", []))
        cases = definition.get("cases", [])
        if definition["type"] == "checkbox":
            selected = item.get("selected_cases", definition.get("default_case", []))
            selected = [case["name"] for case in cases if case["name"] in selected]
            item["selected_cases"] = selected
            item.setdefault("index", 0)
            for case in cases:
                if case["name"] in selected: children.extend(case.get("option", []))
        elif cases:
            default = next((i for i, case in enumerate(cases) if case["name"] == definition.get("default_case")), 0)
            index = item.get("index", default)
            if type(index) is not int or not 0 <= index < len(cases): index = default
            item["index"] = index
            children.extend(cases[index].get("option", []))
        if "inputs" in definition:
            data = item.get("data", {})
            item["data"] = {field["name"]: data.get(field["name"], field.get("default", "")) for field in definition["inputs"]}
            item.setdefault("index", 0)
        item.pop("sub_options", None)
        if children: item["sub_options"] = [build(child) for child in dict.fromkeys(children)]
        return item

    return [build(name) for name in names]


def migrate(config: dict, tasks: list[dict], option_definitions: dict | None = None) -> dict:
    definitions = {task["entry"]: task for task in tasks}
    cached = {}
    for task in config.get("TaskItems", []):
        entry = RENAMED.get(task.get("entry"), task.get("entry"))
        if entry in definitions:
            cached[entry] = {**task, **definitions[entry]}
            if "default_check" in task:
                cached[entry]["default_check"] = task["default_check"]
            saved = task.get("option", [])
            names = definitions[entry].get("option", [])
            if option_definitions is not None:
                cached[entry]["option"] = migrate_task_options(saved, names, option_definitions)
            elif any(isinstance(option, dict) for option in saved):
                cached[entry]["option"] = saved
    ordered = []
    for value in config.get("CurrentTasks", []):
        entry = value.split("<|||>")[-1]
        entry = RENAMED.get(entry, entry)
        if entry in definitions and entry not in ordered: ordered.append(entry)
    ordered.extend(entry for entry in definitions if entry not in ordered)
    # Sweep/gift tasks create new daily/pass goals. Claim only after earning them.
    for entry in ("GT_DailyRewards", "GT_ActivityRewards", "GT_PassRewards", "GT_CloseGame"):
        if entry in ordered:
            ordered.remove(entry)
            ordered.append(entry)
    config["TaskItems"] = [copy.deepcopy(cached.get(entry, definitions[entry])) for entry in ordered]
    if option_definitions is not None:
        for task in config["TaskItems"]:
            names = definitions[task["entry"]].get("option", [])
            if names:
                task["option"] = migrate_task_options(task.get("option", []), names, option_definitions)
            else:
                task.pop("option", None)
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
    interface = json.loads((ROOT / "interface.json").read_text(encoding="utf-8"))
    tasks = interface["task"]
    for path in (ROOT / "config/instances").glob("*.json"):
        original = path.read_text(encoding="utf-8")
        config = migrate(json.loads(original), tasks, interface["option"])
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
