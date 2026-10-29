"""Exercise GUI overrides through the bundled MaaFramework, without a device."""

import ctypes as ct
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))
from native import Native
import shop
from settings import resolve_task_settings
from update_sweep_options import update as update_sweeps


class DeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ROOT / "runtimes/win-x64/native/MaaFramework.dll").is_file():
            raise unittest.SkipTest("Bundled Windows MaaFramework runtime is not installed")
        cls.native = Native(ROOT)
        cls.create = cls.native.bind("MaaResourceCreate", ct.c_void_p)
        cls.destroy = cls.native.bind("MaaResourceDestroy", None, ct.c_void_p)
        cls.override = cls.native.bind("MaaResourceOverridePipeline", ct.c_uint8, ct.c_void_p, ct.c_char_p)
        cls.get = cls.native.bind("MaaResourceGetNodeData", ct.c_uint8, ct.c_void_p, ct.c_char_p, ct.c_void_p)

    def setUp(self):
        self.resource = self.create()
        self.addCleanup(self.destroy, self.resource)
        self.interface = json.loads((ROOT / "interface.json").read_text(encoding="utf-8"))
        self.put(json.loads((ROOT / "resource/pipeline/shop_settings.json").read_text(encoding="utf-8")))

    def put(self, data):
        self.assertTrue(self.override(self.resource, json.dumps(data).encode()))

    def node_data(self, name):
        buffer = self.native.create_string()
        try:
            self.assertTrue(self.get(self.resource, name.encode(), buffer))
            return json.loads(self.native.read_string(buffer))
        finally:
            self.native.destroy_string(buffer)

    def log(self, *args, **kwargs):
        pass

    def deliver(self, name, values):
        definition = self.interface["option"][name]
        override = json.dumps(definition.get("pipeline_override", {}))
        for field, value in values.items():
            override = override.replace('"{' + field + '}"', json.dumps(value))
        self.put(json.loads(override))

    def test_separate_count_currency_and_free_options_survive_native_overrides(self):
        free = next(case for case in self.interface["option"]["ShopResourceProducts"]["cases"] if case["name"] == "free_coins")
        self.put(free["pipeline_override"])
        for key, count, currency in (("green", 1, 1), ("legendary", 3, 0), ("hammer", 1, 0)):
            self.deliver("ShopItem_" + key, {"count": count})
            self.put(self.interface["option"]["ShopItem_" + key + "Currency"]["cases"][currency]["pipeline_override"])
        with patch.object(shop, "select_category", return_value=True), patch.object(shop, "purchase") as purchase:
            self.assertTrue(shop.shop_purchase(self, {"read_settings": True, "preview_only": True}))
        result = {call.args[1].key: (call.args[1].count, call.args[1].currency) for call in purchase.call_args_list}
        self.assertEqual(result, {"free": (1, "free"), "green": (1, "diamond"),
                                  "legendary": (3, "gold"), "hammer": (1, "gold")})
        self.assertTrue(all(call.args[2] for call in purchase.call_args_list))

    def test_custom_name_count_and_currency_survive_and_remain_event_only(self):
        self.deliver("ShopItem_event", {"name": "咖啡机", "count": 2})
        self.put(self.interface["option"]["ShopItem_eventCurrency"]["cases"][3]["pipeline_override"])
        with patch.object(shop, "select_category", return_value=True), patch.object(shop, "purchase") as purchase:
            shop.shop_purchase(self, {"read_settings": True}, event_only=True)
        product = purchase.call_args.args[1]
        self.assertEqual((product.name, product.count, product.currency), ("咖啡机", 2, "star_piece"))

    def test_unselected_goods_never_inherit_another_goods_count(self):
        self.deliver("ShopItem_hammer", {"count": 1})
        with patch.object(shop, "select_category", return_value=True), patch.object(shop, "purchase") as purchase:
            shop.shop_purchase(self, {"read_settings": True})
        self.assertEqual([call.args[1].key for call in purchase.call_args_list], ["hammer"])

    def test_sweep_count_attribute_mode_and_boost_all_reach_agent(self):
        pipeline = json.loads((ROOT / "resource/pipeline/sweep.json").read_text(encoding="utf-8"))
        settings = update_sweeps(self.interface, pipeline)
        self.put(settings)
        self.deliver("EvolutionCount", {"count": 7})
        for name, index in (("EvolutionBoost", 1), ("EvolutionAttribute", 5), ("EvolutionMode", 1)):
            self.put(self.interface["option"][name]["cases"][index]["pipeline_override"])
        params = resolve_task_settings(self, pipeline["GT_Sweep_Evolution"]["custom_action_param"])
        self.assertEqual(params, {"count": 7, "boost_only": False, "attribute": "water", "mode": "selected"})

    def test_flower_zero_and_attribute_survive_together(self):
        pipeline = json.loads((ROOT / "resource/pipeline/sweep.json").read_text(encoding="utf-8"))
        self.put(update_sweeps(self.interface, pipeline))
        self.deliver("FlowerCount", {"count": 0})
        self.put(self.interface["option"]["FlowerAttribute"]["cases"][4]["pipeline_override"])
        params = resolve_task_settings(self, pipeline["GT_Sweep_Flower"]["custom_action_param"])
        self.assertEqual(params, {"count": 0, "attribute": "fire"})

    def test_parameterless_actions_accept_native_json_null(self):
        self.assertEqual(resolve_task_settings(self, None), {})


if __name__ == "__main__": unittest.main()
