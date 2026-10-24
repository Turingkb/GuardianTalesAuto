"""Decision tests for spending guards and evolution ownership/progress boundaries."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
import actions


class Dialog:
    def __init__(self, count="3", diamonds="0", vouchers="0", allowance="7/10"):
        self.values = {(330, 365, 620, 39): count, (870, 468, 73, 40): diamonds,
                       (870, 519, 73, 40): vouchers, (853, 539, 88, 39): allowance,
                       (330, 385, 620, 40): "1", (623, 493, 121, 38): "42(-10)",
                       (808, 493, 134, 38): "2,965"}
        self.taps, self.events = [], []

    def capture(self): return self
    def has(self, roi, expected): return True
    def text(self, roi): return self.values[tuple(roi)]
    def recognize(self, *args): return {"matched": True}
    def tap(self, *point): self.taps.append(point[:2])
    def log(self, event, **details): self.events.append((event, details))
    def save(self, *args): pass


class Guards(unittest.TestCase):
    def test_evolution_closes_known_points_popup_before_next_hero(self):
        screen = Dialog()
        screen.pause = lambda seconds: None
        screen.has = lambda roi, expected: (roi == [45, 260, 350, 65]
                                            or not screen.taps)
        actions.wait_evolution_page(screen)
        self.assertEqual(screen.taps, [(640, 660)])

    def test_evolution_unknown_overlay_never_clicks_settings(self):
        screen = Dialog()
        screen.pause = lambda seconds: None
        screen.has = lambda *args: False
        with patch.object(actions.time, "monotonic", side_effect=[0, 1, 13]), \
                self.assertRaises(RuntimeError):
            actions.choose_evolution_hero(screen, (404, 333))
        self.assertEqual(screen.taps, [])

    def test_stamina_cost_formats(self):
        for text, expected in [("71(-71)", (71, 71)), ("2,965(-29)", (2965, 29)),
                               ("2，965", (2965, 0)), ("42（−10）", (42, 10))]:
            self.assertEqual(actions.stamina_cost(text), expected)

    def test_ambiguous_or_excess_cost_rejected(self):
        for text in ["42(+10)", "2(-10)", "42/86", "", "2,965(-?29)"]:
            with self.assertRaises(ValueError): actions.stamina_cost(text)

    def test_free_awake_submits_verified_count(self):
        screen = Dialog()
        with patch.object(actions, "finish_sweep") as finish:
            self.assertTrue(actions.awake_free(screen, {}))
            finish.assert_called_once_with(screen, 3, "awakening")
        self.assertEqual(screen.taps, [(744, 611)])

    def test_awake_rejects_every_paid_or_invalid_case(self):
        for params in [{"diamonds": "300"}, {"vouchers": "1"}, {"count": "4"},
                       {"count": "0"}, {"diamonds": "O"}, {"count": "3/3"}]:
            screen = Dialog(**params)
            with self.assertRaises((ValueError, RuntimeError)): actions.awake_free(screen, {})
            self.assertEqual(screen.taps, [])

    def test_empty_boost_cancels_without_spending(self):
        screen = Dialog(allowance="0/10")
        self.assertEqual(actions.execute_stamina_sweep(screen, 10, True, "gold"), 0)
        self.assertEqual(screen.taps, [(536, 637)])

    def test_boost_count_is_capped_to_remaining(self):
        screen = Dialog(allowance="1/10")
        with patch.object(actions, "set_counter") as set_count, patch.object(actions, "finish_sweep"):
            self.assertEqual(actions.execute_stamina_sweep(screen, 10, True, "gold"), 1)
            set_count.assert_called_once_with(screen, 1)
        self.assertEqual(screen.taps, [(744, 637)])

    def test_invalid_allowance_never_submits(self):
        for text in ["11/10", "7/1O", "7", "-1/10"]:
            screen = Dialog(allowance=text)
            with self.assertRaises(RuntimeError): actions.execute_stamina_sweep(screen, 10, True, "gold")
            self.assertEqual(screen.taps, [])

    def test_cost_mismatch_never_submits(self):
        screen = Dialog()
        screen.values[(623, 493, 121, 38)] = "42(-20)"
        with patch.object(actions, "set_counter"), self.assertRaises(RuntimeError):
            actions.execute_stamina_sweep(screen, 1, True, "items")
        self.assertEqual(screen.taps, [])

    def test_zero_configuration_never_inputs(self):
        screen = Dialog()
        self.assertTrue(actions.resource_sweep(screen, {"kind": "gold", "count": 0}))
        self.assertTrue(actions.evolution_sweep(screen, {"count": 0}))
        self.assertEqual(screen.taps, [])

    def test_invalid_configuration_never_inputs(self):
        for params in [{"kind": "gold", "count": -1}, {"kind": "gold", "count": 101},
                       {"kind": "gold", "boost_only": "false"}, {"kind": "summon"}]:
            screen = Dialog()
            with self.assertRaises(ValueError): actions.resource_sweep(screen, params)
            self.assertEqual(screen.taps, [])

    def test_hero_candidate_requires_owned_and_incomplete_total(self):
        screen = Dialog()
        screen.ocr = lambda *args: [{"text": "37/320", "box": [668, 535, 40, 18]}]
        screen.text = lambda roi: "37/1160"
        self.assertEqual(actions.evolution_candidate(screen), (691, 475))
        screen.text = lambda roi: "1160/1160"
        self.assertIsNone(actions.evolution_candidate(screen))
        screen.ocr = lambda *args: [{"text": "17/1160", "box": [350, 275, 60, 20]}]
        self.assertIsNone(actions.evolution_candidate(screen))

    def test_auto_evolution_moves_to_next_attribute_without_spending_on_finished_one(self):
        screen = Dialog()
        with patch.object(actions, "choose_evolution_hero", side_effect=[False, True]) as choose, \
                patch.object(actions, "execute_stamina_sweep", return_value=1) as sweep:
            self.assertTrue(actions.evolution_sweep(screen, {"count": 1, "mode": "auto"}))
        self.assertEqual([call.args[1] for call in choose.call_args_list], [(404, 333), (804, 333)])
        self.assertEqual(screen.taps, [(737, 395)])
        sweep.assert_called_once_with(screen, 1, True, "evolution")

    def test_manual_evolution_keeps_game_selection(self):
        screen = Dialog()
        with patch.object(actions, "choose_evolution_hero") as choose, \
                patch.object(actions, "execute_stamina_sweep", return_value=2) as sweep:
            self.assertTrue(actions.evolution_sweep(screen, {"count": 2, "mode": "selected", "attribute": "water"}))
        choose.assert_not_called()
        self.assertEqual(screen.taps, [(1137, 642)])
        sweep.assert_called_once_with(screen, 2, True, "evolution")


if __name__ == "__main__": unittest.main(verbosity=2)
