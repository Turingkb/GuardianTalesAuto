"""Guard narrow task settings and the GUI information-page references."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InterfaceText(unittest.TestCase):
    def test_evolution_labels_fit_the_narrow_settings_columns(self):
        interface = json.loads((ROOT / "interface.json").read_text(encoding="utf-8"))
        for name in ("EvolutionAttribute", "EvolutionMode"):
            option = interface["option"][name]
            self.assertLessEqual(len(option["label"]), 6)
            self.assertTrue(option.get("description"))
        for case in interface["option"]["EvolutionMode"]["cases"]:
            self.assertLessEqual(len(case["label"]), 6)

    def test_information_pages_and_localized_brand_are_current(self):
        interface = json.loads((ROOT / "interface.json").read_text(encoding="utf-8"))
        localized = json.loads((ROOT / interface["languages"]["zh_cn"]).read_text(encoding="utf-8"))
        self.assertEqual(localized["title"], interface["title"])
        self.assertEqual(localized["name"], interface["label"])
        for field in ("license", "description", "welcome", "contact"):
            self.assertTrue((ROOT / interface[field]).is_file())
        about = (ROOT / interface["description"]).read_text(encoding="utf-8")
        self.assertIn("MaaFramework", about)
        self.assertIn("MFAAvalonia", about)


if __name__ == "__main__": unittest.main()
