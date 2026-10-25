"""Replay the real princess chest and reward images without device input."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FIX = "dev/2026-10-25/princess/"
CASES = [
    ("GT_PrincessChest_Open", FIX + "current.png", True),
    ("GT_PrincessChest_Open", FIX + "claimed-hub.png", False),
    ("GT_PrincessChest_Open", FIX + "chest-open.png", False),
    ("GT_PrincessChest_Result", FIX + "chest-open.png", True),
    ("GT_PrincessChest_Result", FIX + "current.png", False),
    ("GT_Common_DismissReward", FIX + "chest-open.png", True),
    ("GT_PrincessChest_Open", "dev/2026-10-15/screenshots/14_paid_gem_negative.png", False),
    ("GT_PrincessChest_Result", "dev/2026-10-15/screenshots/14_paid_gem_negative.png", False),
]


def main() -> int:
    failed = 0
    with (ROOT / FIX / "recognition.log").open("wb") as log:
        for node, fixture, expected in CASES:
            command = [sys.executable, "dev/run_task.py", node, "--image", fixture]
            if not expected:
                command.append("--expect-miss")
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=30)
            failed += result.returncode != 0
            print(f"{'FAIL' if result.returncode else 'PASS'} {node} / {fixture}", flush=True)
    print(f"Princess recognition: {len(CASES)-failed}/{len(CASES)} passed", flush=True)
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
