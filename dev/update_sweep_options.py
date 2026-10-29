"""Isolate sweep inputs so one GUI option cannot overwrite another."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def update(interface: dict, pipeline: dict) -> dict:
    settings = {}
    for node, definition in pipeline.items():
        if not node.startswith("GT_Sweep_") or "custom_action_param" not in definition:
            continue
        defaults = definition["custom_action_param"]
        fields = defaults.get("settings_fields", list(defaults))
        for field in fields:
            settings[node + "_Setting_" + field] = {
                "action": "Custom", "custom_action": definition["custom_action"],
                "custom_action_param": {field: defaults[field]}}
        defaults.update(settings_node=node, settings_fields=fields)
    for option in interface["option"].values():
        for source in [option] + option.get("cases", []):
            overrides = source.get("pipeline_override", {})
            for node in list(overrides):
                params = overrides[node].get("custom_action_param", {})
                if node not in pipeline or not node.startswith("GT_Sweep_") or not params:
                    continue
                del overrides[node]
                for field, value in params.items():
                    overrides[node + "_Setting_" + field] = {"custom_action_param": {field: value}}
    return settings


def main():
    interface_path = ROOT / "interface.json"
    pipeline_path = ROOT / "resource/pipeline/sweep.json"
    interface = json.loads(interface_path.read_text(encoding="utf-8"))
    pipeline = json.loads(pipeline_path.read_text(encoding="utf-8"))
    settings = update(interface, pipeline)
    for path, content in ((interface_path, interface), (pipeline_path, pipeline),
                          (ROOT / "resource/pipeline/sweep_settings.json", settings)):
        path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__": main()
