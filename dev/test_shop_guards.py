"""No-device checks for shop spending limits and rejected confirmation dialogs."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
import shop
import actions
from migrate_gui_tasks import migrate


class PurchaseDialog:
    def __init__(self, *, price="100", label="100", name="储备体力", currency=True, quantity="1"):
        self.price, self.label, self.name = price, label, name
        self.currency, self.quantity = currency, quantity
        self.taps, self.events = [], []

    def capture(self): return self
    def ocr(self, roi, expected=None):
        if roi == [390, 540, 250, 110]:
            return [{"text": "取消", "box": [507, 600, 40, 22]}]
        return [{"text": self.name, "box": [550, 285, 180, 30]}]
    def text(self, roi):
        if roi == [435, 270, 410, 80]: return self.name
        if roi == [660, 587, 200, 48]: return self.label
        if roi == [746, 590, 100, 42]: return self.price
        if roi == [375, 460, 548, 39]: return self.quantity
        return "16889"
    def has(self, roi, expected): return True
    def recognize(self, kind, params):
        if "currency" in params.get("template", ""): return {"matched": True} if self.currency else None
        return {"box": [0, 0, 1, 1]}
    def tap(self, *args): self.taps.append(args[:2])
    def log(self, event, **kwargs): self.events.append((event, kwargs))
    def save(self, *args): pass


class ShopGuards(unittest.TestCase):
    product = shop.Product("stamina", "资源", "储备体力", "diamond", 1, 100)

    def test_free_coin_caption_accepts_game_exclamation_only(self):
        for label in ("每日免费商品", "每日免费商品!", "每日免费商品！", "每日免费商品套餐"):
            screen = PurchaseDialog()
            screen.act = lambda *args: None
            screen.pause = lambda *args: None
            screen.ocr = lambda *args: [{"text": label, "box": [835, 440, 110, 20]}]
            expected = None if label.endswith("套餐") else (890, 360)
            self.assertEqual(shop.find_product(screen, "金币", free=True), expected)

    def test_shop_resource_loading_waits_without_input(self):
        screen = PurchaseDialog()
        screen.pause = lambda seconds: None
        with patch.object(screen, "recognize", side_effect=[None, None, {"box": [0, 0, 1, 1]}]):
            shop.require_shop(screen)
        self.assertEqual(screen.taps, [])

    def test_shop_loading_timeout_never_guesses_a_button(self):
        screen = PurchaseDialog()
        screen.pause = lambda seconds: None
        with patch.object(screen, "recognize", return_value=None), \
                patch.object(shop.time, "monotonic", side_effect=[0, 1, 31]), \
                self.assertRaises(RuntimeError):
            shop.require_shop(screen)
        self.assertEqual(screen.taps, [])

    def test_paid_defaults_are_empty(self):
        self.assertEqual(shop.plans({}), [])
        self.assertEqual(shop.plans({"stamina_count": 10}), [])
        self.assertEqual(shop.plans({"stamina_budget": 1000}), [])

    def test_limits_and_types(self):
        for key, value in [("count", -1), ("count", 101), ("count", True), ("budget", "100"), ("budget", -1)]:
            with self.assertRaises(ValueError): shop.plans({"stamina_" + key: value})

    def test_custom_name_and_currency_are_checked(self):
        for name, currency in [("", "diamond"), ("十连召唤", "diamond"), ("金币", "cash")]:
            with self.assertRaises(ValueError):
                shop.plans({"event_count": 1, "event_budget": 100, "event_name": name, "event_currency": currency})

    def test_read_valid_price(self):
        self.assertEqual(shop.inspect_purchase(PurchaseDialog(), self.product), (100, (752, 611)))

    def test_reject_cash_paid_gems_unknown_price_and_quantity(self):
        for kwargs in [{"label": "付费100"}, {"label": "￥6"}, {"price": "1O0"}, {"price": "0"},
                       {"name": "史诗突破锤"}, {"currency": False}, {"quantity": "2"}]:
            with self.subTest(kwargs=kwargs), self.assertRaises((ValueError, RuntimeError)):
                shop.inspect_purchase(PurchaseDialog(**kwargs), self.product)

    def test_budget_exceeded_only_cancels(self):
        screen = PurchaseDialog(price="101")
        with patch.object(shop, "find_product", return_value=(394, 300)):
            shop.purchase(screen, self.product, False)
        self.assertEqual(screen.taps, [(394, 300), (527, 611)])

    def test_preview_only_cancels(self):
        screen = PurchaseDialog()
        with patch.object(shop, "find_product", return_value=(394, 300)):
            shop.purchase(screen, self.product, True)
        self.assertEqual(screen.taps, [(394, 300), (527, 611)])

    def test_total_budget_stops_repeated_purchases(self):
        screen = PurchaseDialog()
        product = shop.Product("stamina", "资源", "储备体力", "diamond", 2, 100)
        with patch.object(shop, "find_product", return_value=(394, 300)), \
                patch.object(shop, "balance", side_effect=[1000, 900, 900]), patch.object(shop, "settle"):
            shop.purchase(screen, product, False)
        self.assertEqual(screen.taps.count((752, 611)), 1)
        self.assertEqual(screen.taps[-1], (527, 611))

    def test_unexpected_balance_change_stops_before_second_purchase(self):
        screen = PurchaseDialog()
        product = shop.Product("stamina", "资源", "储备体力", "diamond", 2, 1000)
        with patch.object(shop, "find_product", return_value=(394, 300)), \
                patch.object(shop, "balance", side_effect=[1000, 800]), patch.object(shop, "settle"), \
                self.assertRaises(RuntimeError):
            shop.purchase(screen, product, False)
        self.assertEqual(screen.taps.count((752, 611)), 1)

    def test_gui_migration_preserves_device_order_and_selection(self):
        tasks = [{"name": "Shop", "entry": "GT_ShopPurchase", "default_check": True},
                 {"name": "Sign", "entry": "GT_SignInAndSoul", "default_check": True}]
        config = {"AdbDevice": {"address": "test-device"},
                  "CurrentTasks": ["Shop<|||>GT_ShopBenefits", "Soul<|||>GT_CollectSoulPoints", "Sign<|||>GT_SignIn"],
                  "TaskItems": [{"entry": "GT_ShopBenefits", "default_check": False}]}
        migrated = migrate(config, tasks)
        self.assertEqual(migrated["AdbDevice"], {"address": "test-device"})
        self.assertEqual(migrated["CurrentTasks"], ["Shop<|||>GT_ShopPurchase", "Sign<|||>GT_SignInAndSoul"])
        self.assertFalse(migrated["TaskItems"][0]["default_check"])
        self.assertEqual(migrate(migrated, tasks), migrated)

    def test_unexpected_dialog_cancels_then_stops(self):
        screen = PurchaseDialog(name="召唤礼包")
        with patch.object(shop, "find_product", return_value=(394, 300)), self.assertRaises(RuntimeError):
            shop.purchase(screen, self.product, False)
        self.assertEqual(screen.taps, [(394, 300), (527, 611)])

    def test_no_boost_cancels_instead_of_spending(self):
        screen = PurchaseDialog()
        screen.has = lambda roi, expected: expected != "每日焕发"
        self.assertEqual(actions.execute_stamina_sweep(screen, 10, True, "red"), 0)
        self.assertEqual(screen.taps, [(536, 637)])

    def test_tethys_zero_free_never_opens_paid_dialog(self):
        screen = PurchaseDialog()
        screen.text = lambda roi: "0/3"
        self.assertTrue(actions.tethys_free(screen, {}))
        self.assertEqual(screen.taps, [])

    def test_tethys_requires_zero_diamonds_and_zero_exchanged_tickets(self):
        for cost, vouchers, count in [("0", "0/3", "3"), ("150", "1/3", "3"),
                                      ("0", "1/3", "3"), ("0", "0/3", "4")]:
            screen = PurchaseDialog()
            values = {(1070, 564, 60, 44): "3/3", (330, 385, 620, 40): count,
                      (870, 492, 75, 40): cost, (870, 540, 75, 40): vouchers}
            screen.text = lambda roi: values[tuple(roi)]
            with patch.object(actions, "finish_sweep"):
                if cost == "0" and vouchers == "0/3" and count == "3":
                    self.assertTrue(actions.tethys_free(screen, {}))
                    self.assertEqual(screen.taps, [(765, 637)])
                else:
                    with self.assertRaises(RuntimeError): actions.tethys_free(screen, {})
                    self.assertEqual(screen.taps, [])


if __name__ == "__main__": unittest.main(verbosity=2)
