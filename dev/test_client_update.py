"""Client upgrades fail clearly; resource downloads wait without tapping start."""

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'agent'))
from actions import client_update_required


class ClientUpdates(unittest.TestCase):
    def test_client_upgrade_reports_required_action_without_device_input(self):
        with self.assertRaisesRegex(RuntimeError, '客户端需要更新'):
            client_update_required(object(), {})

    def test_both_entry_routes_check_updates_before_tapping_start(self):
        startup = json.loads((ROOT / 'resource/pipeline/startup.json').read_text(encoding='utf-8'))
        common = json.loads((ROOT / 'resource/pipeline/common.json').read_text(encoding='utf-8'))
        for route in (startup['GT_StartUp_Route'], common['GT_Common_HubRoute']):
            for guard in ('GT_StartUp_ClientUpdateRequired', '[JumpBack]GT_StartUp_WaitResourceDownload'):
                self.assertLess(route['next'].index(guard), route['next'].index('[JumpBack]GT_StartUp_TapStartByVersion'))
        download = startup['GT_StartUp_WaitResourceDownload']
        self.assertEqual(download['action'], 'DoNothing')
        self.assertLessEqual(download['max_hit'] * download['post_delay'], 600000)
        self.assertEqual(len(download['all_of']), 2)
        self.assertEqual(len(startup['GT_StartUp_ClientUpdateRequired']['all_of']), 2)


if __name__ == '__main__': unittest.main()
