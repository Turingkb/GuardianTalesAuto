"""Guard checks for pass claims, Thetis counters and final-task ordering."""

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))
import actions
import pass_rewards as passes
from migrate_gui_tasks import migrate


class ClaimScreen:
    def __init__(self, *, yellow=True, bright=True, header=True, label=True):
        self.yellow, self.bright, self.header, self.label = yellow, bright, header, label
        self.taps = []

    def capture(self): return self
    def save(self, *args): pass
    def log(self, *args, **kwargs): pass
    def pause(self, *args): pass
    def has(self, roi, expected):
        if expected == "^邀请赛$": return self.header
        if expected == "^全部领取$": return self.label
        return True
    def recognize(self, kind, params):
        value = self.yellow if params.get("roi") == [1076, 635, 148, 36] else self.bright
        return {"box": [0, 0, 1, 1]} if value else None
    def tap(self, *args): self.taps.append(args[:2])


class DailyClaims(unittest.TestCase):
    def test_pass_navigation_waits_through_loading_without_extra_taps(self):
        screen = ClaimScreen()
        with patch.object(passes, "page_ready", side_effect=[False, False, True]):
            passes.wait_ready(screen)
        self.assertEqual(screen.taps, [])

    def test_pass_tab_waits_for_active_color_after_page_appears(self):
        screen = ClaimScreen()
        with patch.object(screen, "recognize", side_effect=[None, {"box": [0, 0, 1, 1]}]), \
                patch.object(passes, "page_ready", return_value=True):
            passes.wait_ready(screen, phase="goals")
        self.assertEqual(screen.taps, [])

    def test_pass_navigation_timeout_never_clicks_unknown_page(self):
        screen = ClaimScreen()
        with patch.object(passes, "page_ready", return_value=False), \
                patch.object(passes.time, "monotonic", side_effect=[0, 1, 13]), \
                self.assertRaises(RuntimeError):
            passes.wait_ready(screen)
        self.assertEqual(screen.taps, [])

    def test_disabled_or_wrong_claim_button_never_clicks(self):
        for kwargs in [{"yellow": False}, {"label": False}]:
            screen = ClaimScreen(**kwargs)
            self.assertEqual(passes.claim_all(screen, "guardian", "rewards"), 0)
            self.assertEqual(screen.taps, [])

    def test_covered_or_wrong_page_never_clicks(self):
        for kwargs in [{"bright": False}, {"header": False}]:
            screen = ClaimScreen(**kwargs)
            with self.assertRaises(RuntimeError): passes.claim_all(screen, "guardian", "rewards")
            self.assertEqual(screen.taps, [])

    def test_claim_only_uses_the_all_claim_button(self):
        screen = ClaimScreen()
        with patch.object(passes, "claim_available", side_effect=[True, False]), \
                patch.object(passes, "settle_claim"):
            self.assertEqual(passes.claim_all(screen, "celebration", "rewards"), 1)
        self.assertEqual(screen.taps, [(1150, 651)])

    def test_claim_retries_are_bounded(self):
        screen = ClaimScreen()
        with patch.object(passes, "settle_claim"), self.assertRaises(RuntimeError):
            passes.claim_all(screen, "celebration", "rewards")
        self.assertEqual(screen.taps, [(1150, 651)] * 3)

    def test_unknown_result_does_not_guess_a_confirmation(self):
        screen = ClaimScreen()
        with patch.object(passes, "reward_popup", return_value=False), \
                patch.object(passes, "page_ready", return_value=False), \
                patch.object(passes.time, "monotonic", side_effect=[0, 1, 20]), \
                self.assertRaises(RuntimeError):
            passes.settle_claim(screen)
        self.assertEqual(screen.taps, [])

    def test_reward_popup_requires_both_title_and_close_hint(self):
        screen = ClaimScreen()
        screen.has = lambda roi, expected: expected == "^领取奖励$"
        self.assertFalse(passes.reward_popup(screen))
        screen.has = lambda roi, expected: expected != "^领取奖励$"
        self.assertFalse(passes.reward_popup(screen))

    def test_tethys_reads_digits_without_the_ticket_icon(self):
        screen = ClaimScreen()
        values = {(1030, 564, 100, 44): "区3/3", (1070, 564, 60, 44): "3/3",
                  (330, 385, 620, 40): "3", (870, 492, 75, 40): "0", (870, 540, 75, 40): "0/3"}
        screen.text = lambda roi: values[tuple(roi)]
        with patch.object(actions, "finish_sweep"):
            self.assertTrue(actions.tethys_free(screen, {}))
        self.assertEqual(screen.taps, [(765, 637)])

    def test_new_reward_tasks_go_before_existing_close_game(self):
        interface = json.loads((ROOT / "interface.json").read_text(encoding="utf-8"))
        tasks = interface["task"]
        config = {"CurrentTasks": ["Close<|||>GT_CloseGame", "Hub<|||>GT_EnsureHub"], "TaskItems": []}
        migrated = migrate(config, tasks)
        self.assertTrue(migrated["CurrentTasks"][-1].endswith("<|||>GT_CloseGame"))
        entries = [value.split("<|||>")[-1] for value in migrated["CurrentTasks"]]
        self.assertLess(entries.index("GT_PassRewards"), entries.index("GT_CloseGame"))


if __name__ == "__main__": unittest.main(verbosity=2)
