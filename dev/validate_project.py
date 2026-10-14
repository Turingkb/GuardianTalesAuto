"""Validate task/option references, pipeline jumps, template files and Agent names."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))
from actions import HANDLERS


def main():
    interface = json.loads((ROOT / "interface.json").read_text(encoding="utf-8"))
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
    assert (ROOT / interface["icon"]).is_file()
    print(f"Validated {len(nodes)} nodes, {len(interface['task'])} tasks, {len(HANDLERS)} Agent actions")
    return 0


if __name__ == "__main__": raise SystemExit(main())
