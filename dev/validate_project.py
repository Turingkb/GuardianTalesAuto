"""Validate task/option references, pipeline jumps, template files and Agent names."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))
from actions import HANDLERS


def main():
    interface = json.loads((ROOT / "interface.json").read_text(encoding="utf-8"))
    localized = json.loads((ROOT / interface["languages"]["zh_cn"]).read_text(encoding="utf-8"))
    assert localized["title"] == interface["title"], "Localized title/version is stale"
    assert localized["name"] == interface["label"], "Localized project name is stale"
    for field in ("license", "description", "contact", "welcome"):
        assert (ROOT / interface[field]).is_file(), f"Missing GUI information page: {field}"
    nodes = {}
    for file in (ROOT / "resource/pipeline").glob("*.json"):
        content = json.loads(file.read_text(encoding="utf-8"))
        duplicate = nodes.keys() & content.keys()
        assert not duplicate, f"Duplicate nodes: {duplicate}"
        nodes.update(content)

    def validate(node):
        for field in ("next", "on_error"):
            for ref in node.get(field, []):
                name = ref.split("]")[-1] if isinstance(ref, str) else ref["name"]
                assert name in nodes, f"Unknown jump: {name}"
        for field in ("all_of", "any_of"):
            for child in node.get(field, []):
                if isinstance(child, str): assert child in nodes, f"Unknown recognition: {child}"
                else: validate(child)
        templates = node.get("template", [])
        for template in ([templates] if isinstance(templates, str) else templates):
            assert (ROOT / "resource/image" / template).is_file(), template
        if node.get("custom_action"):
            assert node["custom_action"] in HANDLERS, node["custom_action"]

    for node in nodes.values(): validate(node)
    for task in interface["task"]:
        assert task["entry"] in nodes, task["entry"]
        for option in task.get("option", []): assert option in interface["option"], option
    def validate_option(name, parents=()):
        assert name in interface["option"], f"Unknown child option: {name}"
        assert name not in parents, f"Option cycle: {parents + (name,)}"
        option = interface["option"][name]
        for case in option.get("cases", []):
            for child in case.get("option", []): validate_option(child, parents + (name,))
            for node in case.get("pipeline_override", {}): assert node in nodes, node
        for node in option.get("pipeline_override", {}): assert node in nodes, node
    for name in interface["option"]: validate_option(name)
    # Independent option values must not replace each other's action parameters.
    field_targets = {}
    for option in interface["option"].values():
        for source in [option] + option.get("cases", []):
            for node, override in source.get("pipeline_override", {}).items():
                fields = override.get("custom_action_param", {}).keys()
                field_targets.setdefault(node, set()).update(fields)
    for node, fields in field_targets.items():
        assert len(fields) <= 1, f"GUI action parameters overwrite each other: {node}: {fields}"
    assert (ROOT / interface["icon"]).is_file()
    print(f"Validated {len(nodes)} nodes, {len(interface['task'])} tasks, {len(HANDLERS)} Agent actions")
    return 0


if __name__ == "__main__": raise SystemExit(main())
