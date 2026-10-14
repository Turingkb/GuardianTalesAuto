"""Replay saved screenshots with the real MaaFramework recognizers; no game input."""

import json
from pathlib import Path
import subprocess
import sys


CASES = [
    ("GT_StartUp_HubReady", "17_clean_hub.png", True),
    ("GT_StartUp_HubReady", "21_signin.png", False),
    ("GT_StartUp_HubReady", "52_free_dialog.png", False),
    ("GT_StartUp_HubReady", "26_missions.png", False),
    ("GT_SignIn_ClaimRegular", "21_signin.png", True),
    ("GT_SignIn_ClaimRegular", "17_clean_hub.png", False),
    ("GT_SignIn_ClaimEvent", "23_signin_claimed.png", True),
    ("GT_SignIn_ClaimEvent", "22_signin_detail.png", False),
    ("GT_Guild_Sign", "32_guild_sign.png", True),
    ("GT_Guild_Sign", "34_guild_signed.png", False),
    ("GT_Guild_AlreadySigned", "34_guild_signed.png", True),
    ("GT_Guild_AlreadySigned", "32_guild_sign.png", False),
    ("GT_Daily_ClaimAll", "37_daily_claimable.png", True),
    ("GT_Daily_ClaimAll", "30_daily.png", False),
    ("GT_Daily_Done", "30_daily.png", True),
    ("GT_Daily_Done", "37_daily_claimable.png", False),
    ("GT_Shop_ClaimSubscription", "40_shop_loaded.png", True),
    ("GT_Shop_ClaimSubscription", "50_shop_again.png", False),
    ("GT_Shop_ClaimFreeDaily", "51_shop_resource.png", True),
    ("GT_Shop_ConfirmFree", "52_free_dialog.png", True),
    ("GT_Shop_ConfirmFree", "12_hub.png", False),
    ("GT_Mail_ClaimAll", "18_mail.png", False),
    ("GT_Mail_Empty", "18_mail.png", True),
    ("GT_Common_DismissReward", "22_signin_detail.png", True),
    ("GT_Common_DismissReward", "33_guild_after_script.png", True),
    ("GT_Common_DismissReward", "38_daily_after_script.png", True),
    ("GT_Common_DismissReward", "53_free_reward.png", True),
    ("GT_Common_DismissReward", "17_clean_hub.png", False),
    ("GT_Common_ClosePromo", "07_after_notice.png", True),
    ("GT_Common_ClosePromo", "17_clean_hub.png", False),
    ("GT_Common_PageHeaderBright", "40_shop_loaded.png", True),
    ("GT_Common_PageHeaderBright", "52_free_dialog.png", False),
]


def main() -> int:
    directory = Path(__file__).resolve().parent
    root = directory.parent
    results = []
    with (directory / "recognition-check.log").open("w", encoding="utf-8") as log:
        for node, screenshot, hit in CASES:
            command = [sys.executable, str(directory / "run_task.py"), node,
                       "--image", str(directory / "screenshots" / screenshot), "--limit", "15"]
            if not hit:
                command.append("--expect-miss")
            completed = subprocess.run(command, cwd=root, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, timeout=25)
            passed = completed.returncode == 0
            result = {"node": node, "screenshot": screenshot, "expected_hit": hit, "passed": passed}
            results.append(result)
            log.write(json.dumps(result, ensure_ascii=False) + "\n")
            log.write(completed.stdout.decode("utf-8", errors="replace") + "\n")
            log.flush()
            print(f"{'PASS' if passed else 'FAIL'} {node} / {screenshot}", flush=True)
    (directory / "recognition-results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    passed = sum(result["passed"] for result in results)
    print(f"Recognition regression: {passed}/{len(results)} passed", flush=True)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
