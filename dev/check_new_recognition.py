"""Replay new positive/negative fixtures without clicking the device."""

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("GT_Test_DailyBoostSelected", "debug/agent/gold-before-confirm.png", True),
    ("GT_Test_DailyBoostSelected", "dev/2026-10-14/screenshots/08_awake_dialog.png", False),
    ("GT_Common_DismissReward", "dev/2026-10-14/screenshots/18_subscription_reward.png", True),
    ("GT_Common_PromoOptOut", "dev/screenshots/07_after_notice.png", True),
    ("GT_Common_PromoOptOut", "dev/2026-10-14/screenshots/02_hub.png", False),
    ("GT_Mail_ClaimAll", "dev/2026-10-14/screenshots/03_mail_rewards.png", True),
    ("GT_Mail_ConfirmClaim", "dev/2026-10-14/screenshots/04_mail_after_click.png", True),
    ("GT_Mail_ConfirmClaim", "dev/2026-10-14/screenshots/03_mail_rewards.png", False),
    ("GT_Mail_ConfirmClaim", "dev/2026-10-14/screenshots/02_hub.png", False),
    ("GT_Friends_GiftAll", "dev/2026-10-14/screenshots/01_current.png", True),
    ("GT_Friends_GiftAll", "dev/2026-10-14/screenshots/02_hub.png", False),
    ("GT_Friends_AckSent", "dev/2026-10-14/screenshots/06_friends_after.png", True),
    ("GT_Friends_AckSent", "dev/2026-10-14/screenshots/01_current.png", False),
    ("GT_Common_AckSweepResult", "dev/2026-10-14/screenshots/10_awake_complete.png", True),
    ("GT_Common_AckSweepResult", "dev/2026-10-14/screenshots/09_awake_result.png", False),
    ("GT_Common_CancelSweepDialog", "dev/2026-10-14/screenshots/08_awake_dialog.png", True),
    ("GT_Common_CancelSweepDialog", "dev/2026-10-14/screenshots/17_evo_dialog.png", True),
    ("GT_Common_CancelHeroSettings", "dev/2026-10-14/screenshots/14_evolution_heroes.png", True),
    ("GT_Common_CancelHeroSettings", "dev/2026-10-14/screenshots/17_evo_dialog.png", False),
]


def main():
    results = []
    with (ROOT / "dev/2026-10-14/new-recognition.log").open("w", encoding="utf-8") as log:
        for node, fixture, expected in CASES:
            command = [sys.executable, str(ROOT / "dev/run_task.py"), node, "--image", fixture]
            if not expected: command.append("--expect-miss")
            result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=25)
            passed = result.returncode == 0
            results.append({"node": node, "fixture": fixture, "expected": expected, "passed": passed})
            log.write(result.stdout.decode("utf-8", errors="replace"))
            log.write(result.stderr.decode("utf-8", errors="replace"))
            print(f"{'PASS' if passed else 'FAIL'} {node} / {fixture}", flush=True)
    (ROOT / "dev/2026-10-14/new-recognition-results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return int(not all(result["passed"] for result in results))


if __name__ == "__main__": raise SystemExit(main())
