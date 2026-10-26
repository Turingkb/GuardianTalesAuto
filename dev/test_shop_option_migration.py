"""Preserve shop selections while nesting inputs under product checkboxes."""

import copy
import json
from pathlib import Path
import unittest

from migrate_gui_tasks import migrate


class ShopOptionMigration(unittest.TestCase):
    def setUp(self):
        self.interface = json.loads((Path(__file__).resolve().parents[1] / "interface.json").read_text(encoding="utf-8"))

    def run_migration(self, saved):
        config = {"TaskItems": [{"entry": "GT_ShopPurchase", "default_check": False, "option": saved}]}
        migrated = migrate(config, self.interface["task"], self.interface["option"])
        task = next(task for task in migrated["TaskItems"] if task["entry"] == "GT_ShopPurchase")
        return migrated, task

    def test_counts_currency_and_free_preference_survive_regrouping(self):
        saved = [{"name": "ShopFree", "index": 0}, {"name": "ShopResources", "index": 1, "sub_options": [
            {"name": "ShopItem_stamina", "data": {"count": "3", "budget": "0"}},
            {"name": "ShopItem_staminaCurrency", "index": 1}]}]
        migrated, task = self.run_migration(saved)
        resource = next(option for option in task["option"] if option["name"] == "ShopResources")
        group = resource["sub_options"][0]
        self.assertEqual(set(group["selected_cases"]), {"stamina", "free_coins"})
        self.assertEqual(group["sub_options"][0]["data"], {"count": "3"})
        self.assertEqual(group["sub_options"][1]["index"], 1)
        self.assertFalse(task["default_check"])
        self.assertEqual(migrate(copy.deepcopy(migrated), self.interface["task"], self.interface["option"]), migrated)

    def test_free_coins_do_not_turn_on_stamina_purchases(self):
        _, task = self.run_migration([{"name": "ShopFree", "index": 0}, {"name": "ShopResources", "index": 0}])
        resource = next(option for option in task["option"] if option["name"] == "ShopResources")
        self.assertEqual(resource["index"], 1)
        self.assertEqual(resource["sub_options"][0]["selected_cases"], ["free_coins"])

    def test_disabled_free_and_resource_options_stay_disabled(self):
        _, task = self.run_migration([{"name": "ShopFree", "index": 1}, {"name": "ShopResources", "index": 0}])
        resource = next(option for option in task["option"] if option["name"] == "ShopResources")
        self.assertEqual(resource["index"], 0)


if __name__ == "__main__": unittest.main(verbosity=2)
