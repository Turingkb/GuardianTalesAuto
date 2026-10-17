"""Replay reported daily-task failures and pass claim controls without device input."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FIX = "dev/2026-10-17/screenshots/"
CASES = [
    ("GT_Common_ConfirmTethysLevelUp", FIX + "tethys-level-up.png", True),
    ("GT_Common_ConfirmTethysLevelUp", FIX + "hub.png", False),
    ("GT_Common_ConfirmTethysLevelUp", FIX + "tethys-result.png", False),
    ("GT_Common_ConfirmTethysLevelUp", "dev/2026-10-15/screenshots/14_paid_gem_negative.png", False),
    ("GT_CollectSoulPoints_Click", FIX + "hub.png", True),
    ("GT_CollectSoulPoints_Click", FIX + "soul-after.png", True),
    ("GT_CollectSoulPoints_Click", FIX + "soul-large-run.png", False),
    ("GT_CollectSoulPoints_Click", "dev/screenshots/17_clean_hub.png", True),
    ("GT_Test_TethysFreeRemaining", "dev/2026-10-16/screenshots/01_tethys_free.png", True),
    ("GT_Test_TethysFreeRemaining", FIX + "tethys-result.png", True),
    ("GT_Test_TethysFreeRemaining", FIX + "hub.png", False),
    ("GT_Test_PassReady", FIX + "pass-reward-available.png", True),
    ("GT_Test_PassReady", FIX + "pass-goals.png", True),
    ("GT_Test_PassReady", FIX + "pass-world.png", True),
    ("GT_Test_PassReady", FIX + "pass-goals-claim.png", False),
    ("GT_Test_PassClaimAvailable", FIX + "pass-reward-available.png", True),
    ("GT_Test_PassClaimAvailable", FIX + "pass-goals.png", True),
    ("GT_Test_PassClaimAvailable", FIX + "invitational.png", False),
    ("GT_Test_PassClaimAvailable", FIX + "pass-celebration.png", False),
    ("GT_Test_PassClaimAvailable", FIX + "pass-world.png", False),
    ("GT_Test_PassClaimAvailable", FIX + "pass-goals-claim.png", False),
    ("GT_Test_PassClaimAvailable", "dev/2026-10-15/screenshots/14_paid_gem_negative.png", False),
    *[("GT_Test_PassBanner_" + kind, FIX + "invitational.png", True)
      for kind in ("guardian", "celebration", "world")],
]


def main():
    failed = 0
    with (ROOT / "dev/2026-10-17/recognition.log").open("wb") as log:
        for node, fixture, expected in CASES:
            command = [sys.executable, str(ROOT / "dev/run_task.py"), node, "--image", fixture]
            if not expected: command.append("--expect-miss")
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=30)
            failed += result.returncode != 0
            print(f"{'FAIL' if result.returncode else 'PASS'} {node} / {fixture}", flush=True)
    print(f"Daily recognition: {len(CASES) - failed}/{len(CASES)} passed", flush=True)
    return int(bool(failed))


if __name__ == "__main__": raise SystemExit(main())
