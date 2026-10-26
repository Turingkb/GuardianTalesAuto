"""Replay observed shop currencies and paid-gem negatives without device input."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("GT_Test_Shop_diamond", "02_stamina_detail.png", True),
    ("GT_Test_Shop_gold", "02_stamina_detail.png", False),
    ("GT_Test_Shop_gold", "11_hammer_confirm.png", True),
    ("GT_Test_Shop_diamond", "11_hammer_confirm.png", False),
    ("GT_Test_Shop_star_piece", "12_growth_confirm.png", True),
    ("GT_Test_ShopPaid", "14_paid_gem_negative.png", True),
    ("GT_Test_ShopPaid", "02_stamina_detail.png", False),
    ("GT_Test_ShopQuantity", "02_stamina_detail.png", True),
    ("GT_Test_ShopQuantity", "11_hammer_confirm.png", False),
    ("GT_Test_ShopDiamondCompact", "dev/2026-10-16/screenshots/event-coffee-dialog.png", True),
    ("GT_Test_Shop_gold", "dev/2026-10-16/screenshots/event-coffee-dialog.png", False),
    ("GT_Test_ShopDiamondCompact", "dev/2026-10-16/screenshots/event-hero-crystal-dialog.png", True),
]


def main():
    failures = 0
    directory = ROOT / "dev/runtime"
    directory.mkdir(exist_ok=True)
    with (directory / "shop-recognition.log").open("wb") as log:
        for node, image, expected in CASES:
            fixture = image if image.startswith("dev/") else "dev/2026-10-15/screenshots/" + image
            command = [sys.executable, str(ROOT / "dev/run_task.py"), node,
                       "--image", fixture]
            if not expected: command.append("--expect-miss")
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=30)
            failures += result.returncode != 0
            print(f"{'PASS' if not result.returncode else 'FAIL'} {node} / {image}", flush=True)
    return int(bool(failures))


if __name__ == "__main__": raise SystemExit(main())
