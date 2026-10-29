"""Event goal claims cannot start challenges or spend event points."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
import activity_rewards as activity


class GoalScreen:
    def __init__(self, *, ready=True, yellow=True, label=True, credit=True):
        self.ready, self.yellow, self.label, self.credit = ready, yellow, label, credit
        self.balance = 2080
        self.taps = []
    def capture(self): return self
    def save(self, *args): pass
    def pause(self, *args): pass
    def log(self, *args, **kwargs): pass
    def has(self, roi, expected):
        if expected == "^一?键领取$": return self.label
        return self.ready
    def text(self, roi): return str(self.balance)
    def recognize(self, kind, params):
        value = self.yellow if params['roi'] == [1000, 640, 150, 40] else self.ready
        if params.get('lower') == [105,110,120]: value = not self.yellow
        return {'box':[0,0,1,1]} if value else None
    def tap(self, x, y, *args):
        self.taps.append((x,y))
        if (x,y) == (1078,659) and self.credit:
            self.balance += 300
            self.yellow = False


class ActivityClaims(unittest.TestCase):
    def test_disabled_button_never_submits(self):
        screen = GoalScreen(yellow=False)
        self.assertEqual(activity.claim_goals(screen), 0)
        self.assertEqual(screen.taps, [])

    def test_missing_claim_control_is_not_reported_as_completed(self):
        screen = GoalScreen(label=False)
        with self.assertRaises(RuntimeError): activity.claim_goals(screen)
        self.assertEqual(screen.taps, [])

    def test_unknown_button_color_is_not_reported_as_completed(self):
        screen = GoalScreen(yellow=False)
        screen.recognize = lambda kind, params: (None if params['roi'] == [1000,640,150,40]
                                                else {'box':[0,0,1,1]})
        with self.assertRaises(RuntimeError): activity.claim_goals(screen)
        self.assertEqual(screen.taps, [])

    def test_wrong_or_covered_page_cannot_claim(self):
        screen = GoalScreen(ready=False)
        self.assertFalse(activity.claim_available(screen))
        self.assertEqual(screen.taps, [])

    def test_claim_checks_points_increased_and_only_taps_claim(self):
        screen = GoalScreen()
        with patch.object(activity, 'reward_popup', return_value=False):
            self.assertEqual(activity.claim_goals(screen), 300)
        self.assertEqual(screen.balance, 2380)
        self.assertEqual(screen.taps, [(1078,659)])

    def test_unverified_result_never_resubmits(self):
        screen = GoalScreen(credit=False)
        with patch.object(activity, 'wait_for'), \
                patch.object(activity, 'reward_popup', return_value=False), \
                patch.object(activity.time, 'monotonic', side_effect=[0, 1, 20]), \
                self.assertRaises(RuntimeError):
            activity.claim_goals(screen)
        self.assertEqual(screen.taps, [(1078,659)])

    def test_ambiguous_points_prevent_submission(self):
        screen = GoalScreen()
        screen.text = lambda roi: '2?080'
        with self.assertRaises(RuntimeError): activity.claim_goals(screen)
        self.assertEqual(screen.taps, [])


if __name__ == '__main__': unittest.main(verbosity=2)
