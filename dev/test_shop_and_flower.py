"""Checks for separate shop scopes, selectable products and flowering-stone costs."""

import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))
import actions
import shop
from update_shop_products import update


class FlowerScreen:
    def __init__(self, spend=10): self.taps, self.spend = [], spend
    def capture(self): return self
    def has(self, roi, expected): return expected != "每日焕发"
    def text(self, roi):
        return {(330, 435, 620, 40): "1", (623, 539, 121, 38): f"63(-{self.spend})",
                (808, 539, 134, 38): "2962"}[tuple(roi)]
    def tap(self, *args): self.taps.append(args[:2])
    def save(self, *args): pass
    def log(self, *args, **kwargs): pass


class FeatureTests(unittest.TestCase):
    def test_regular_and_event_shops_have_separate_plans(self):
        params = {"stamina_count": 1, "stamina_budget": 100,
                  "event_coffee_count": 1, "event_coffee_budget": 200}
        self.assertEqual([p.key for p in shop.plans(params, event_only=False)], ["stamina"])
        self.assertEqual([p.key for p in shop.plans(params, event_only=True)], ["event_coffee"])

    def test_event_default_does_not_claim_or_purchase_anything(self):
        with patch.object(shop, "select_category") as select:
            self.assertTrue(shop.shop_purchase(FlowerScreen(), {}, event_only=True))
            select.assert_not_called()

    def test_preset_product_needs_no_typed_name(self):
        product = shop.plans({"event_coffee_count": 1, "event_coffee_budget": 200,
                              "event_coffee_name": "不可覆盖固定商品"}, event_only=True)[0]
        self.assertEqual((product.name, product.currency), ("咖啡机", "diamond"))

    def test_product_generator_is_idempotent_and_event_overrides_are_separate(self):
        interface = json.loads((ROOT / "interface.json").read_text(encoding="utf-8"))
        before = copy.deepcopy(interface)
        update(interface, shop.PRODUCTS)
        self.assertEqual(interface, before)
        options = interface["option"]
        for case in options["EventShopProducts"]["cases"]:
            for child in case["option"]:
                option = options[child]
                for source in [option] + option.get("cases", []):
                    for node in source.get("pipeline_override", {}):
                        self.assertEqual(node, "GT_EventShop_Run")

    def test_main_list_removes_duplicate_manual_entries(self):
        interface = json.loads((ROOT / "interface.json").read_text(encoding="utf-8"))
        entries = {t["entry"] for t in interface["task"]}
        self.assertFalse(entries & {"GT_OpenMail", "GT_OpenResourceRift", "GT_OpenEvolutionRift", "GT_OpenDailyTasks"})
        self.assertTrue({"GT_FlowerSweep", "GT_EventShopPurchase", "GT_OpenActivity"} <= entries)
        self.assertEqual(sum(bool(t.get("default_check")) for t in interface["task"]), 10)

    def test_flower_zero_or_invalid_settings_never_tap(self):
        screen = FlowerScreen()
        self.assertTrue(actions.flower_sweep(screen, {"count": 0}))
        for params in [{"count": -1}, {"count": True}, {"attribute": "invalid"}]:
            with self.assertRaises(ValueError): actions.flower_sweep(screen, params)
        self.assertEqual(screen.taps, [])

    def test_flower_uses_selected_attribute(self):
        screen = FlowerScreen()
        with patch.object(actions, "execute_plain_sweep") as sweep:
            self.assertTrue(actions.flower_sweep(screen, {"count": 2, "attribute": "fire"}))
            sweep.assert_called_once_with(screen, 2, "flower", preview_only=False)
        self.assertEqual(screen.taps, [(737, 642)])

    def test_flower_preview_cancels_with_verified_ten_stamina(self):
        screen = FlowerScreen()
        self.assertEqual(actions.execute_plain_sweep(screen, 1, "flower", preview_only=True), 0)
        self.assertEqual(screen.taps, [(536, 637)])

    def test_plain_sweep_cost_mismatch_never_confirms(self):
        screen = FlowerScreen(spend=20)
        with self.assertRaises(RuntimeError): actions.execute_plain_sweep(screen, 1, "flower")
        self.assertEqual(screen.taps, [])

    def test_fullwidth_parentheses_match_the_same_product(self):
        self.assertEqual(shop.item_name("觉醒副本宝箱（70级）"), shop.item_name("觉醒副本宝箱(70级)"))


if __name__ == "__main__": unittest.main(verbosity=2)
