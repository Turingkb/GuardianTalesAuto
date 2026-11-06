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


class EventScreen:
    def __init__(self, *, found=True, sidebar=False, covered=False):
        self.state = "list"
        self.found, self.sidebar, self.covered = found, sidebar, covered
        self.taps = []
        self.swipes = 0
    def capture(self): return self
    def pause(self, *args): pass
    def log(self, *args, **kwargs): pass
    def act(self, kind, params): self.swipes += 1
    def has(self, roi, expected):
        if expected == "^活动$": return self.state in ("list", "sidebar")
        return self.state == "page" and not self.covered
    def recognize(self, kind, params):
        if params['template'] == "activity_title_capsule.png":
            return {'box': [74,22,118,25]} if self.state == "page" else None
        return {'box': [48,138,229,72]} if self.found else None
    def tap(self, x, y, *args):
        self.taps.append((x,y))
        self.state = ("sidebar" if self.sidebar and len(self.taps) == 1 else "page")


class EventNavigation(unittest.TestCase):
    def test_selected_banner_opens_without_tapping_machine_controls(self):
        screen = EventScreen()
        self.assertTrue(activity.open_event(screen, activity.EVENTS[0]))
        self.assertEqual(screen.taps, [(162,174)])

    def test_sidebar_is_closed_only_after_recognizing_activity_list(self):
        screen = EventScreen(sidebar=True)
        self.assertTrue(activity.open_event(screen, activity.EVENTS[0]))
        self.assertEqual(screen.taps, [(162,174), (350,365)])

    def test_absent_supported_banner_makes_no_taps(self):
        screen = EventScreen(found=False)
        self.assertFalse(activity.open_event(screen, activity.EVENTS[0]))
        self.assertEqual(screen.taps, [])
        self.assertEqual(screen.swipes, 7)

    def test_unknown_page_does_not_attempt_sidebar_toggle_or_claim(self):
        screen = EventScreen(covered=True)
        with patch.object(activity, 'wait_for', side_effect=[None, RuntimeError('unknown page')]), \
                self.assertRaises(RuntimeError):
            activity.open_event(screen, activity.EVENTS[0])
        self.assertEqual(screen.taps, [(162,174)])

    def test_new_event_claims_goals_and_returns_to_list_without_draw(self):
        screen = EventScreen()
        with patch.object(activity, 'open_event', side_effect=[True, False]), \
                patch.object(activity, 'claim_goals', return_value=2) as claim, \
                patch.object(activity, 'wait_for'):
            self.assertTrue(activity.activity_rewards(screen, {}))
        claim.assert_called_once_with(screen)
        self.assertEqual(screen.taps, [(1195,623), (1237,43), (40,360)])


if __name__ == '__main__': unittest.main(verbosity=2)
