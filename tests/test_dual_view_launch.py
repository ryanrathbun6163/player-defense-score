"""Regression checks for the scoped launch adaptation; no process/GPU actions."""
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/outputs/ball_tracking/dual_view_context_v0_1/launch_v0_1'


def module(name):
    spec = importlib.util.spec_from_file_location('dual_view_test_' + name, BASE / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class LaunchReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.readiness = module('readiness_snapshot')

    def observation(self, **changes):
        value = {'at_utc': datetime.now(timezone.utc).isoformat(),
                 'debug_mode_enabled': True, 'settings_changed': False,
                 'historical_restoration_receipt': self.readiness.binding(self.readiness.RESTORATION),
                 'observed_accessibility_text': 'Debug Mode Toggle switch On'}
        value.update(changes)
        return value

    def test_fresh_observation_does_not_claim_new_setting_change(self):
        self.readiness.require_ui(self.observation())
        with self.assertRaises(ValueError):
            self.readiness.require_ui(self.observation(settings_changed=True))

    def test_stale_off_future_and_unbound_observations_rejected(self):
        for changes in ({'at_utc': (datetime.now(timezone.utc)-timedelta(seconds=121)).isoformat()},
                        {'at_utc': (datetime.now(timezone.utc)+timedelta(seconds=4)).isoformat()},
                        {'debug_mode_enabled': False}, {'historical_restoration_receipt': {}},
                        {'observed_accessibility_text': ''}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.readiness.require_ui(self.observation(**changes))

    def test_truecolor_exception_does_not_exempt_variants_or_other_conflicts(self):
        policy = json.loads((BASE / 'truecolor_operating_policy.json').read_text())
        names = ['MSI.True Color.exe', 'msi.true color.EXE', 'TrueColor.exe',
                 'Lively.exe', 'NVIDIA Overlay.exe', 'RTSS.exe', 'python.exe']
        result = self.readiness.classify_background_apps(
            [{'Name': name, 'ProcessId': i} for i, name in enumerate(names)], policy)
        self.assertEqual([p['ProcessId'] for p in result['permitted_background_apps']], [0, 1])
        self.assertEqual([p['ProcessId'] for p in result['isolation_conflicts']], [2, 3, 4, 5])
        self.assertFalse(result['truecolor_presence']['GPU_context_allowance'])
        self.assertFalse(result['truecolor_presence']['absence_claimed'])

    def test_source_helpers_are_preserved(self):
        import hashlib
        receipt = json.loads((BASE / 'launch_helper_derivation.json').read_text())
        for record in receipt['files']:
            self.assertEqual(hashlib.sha256((ROOT / record['source']).read_bytes()).hexdigest(), record['source_sha256'])
        self.assertEqual((BASE / 'truecolor_operating_policy.json').read_bytes(),
                         (ROOT / 'data/outputs/ball_tracking/fresh_game_diagnostic_v0_1/launch_v0_1/truecolor_operating_policy.json').read_bytes())


class DeadlineTests(unittest.TestCase):
    def test_hard_deadline_exits_if_not_finished(self):
        launcher = module('run_supervised')
        class Finished:
            def wait(self, seconds):
                self.seconds = seconds
                return False
        finished, calls = Finished(), []
        launcher.hard_deadline(finished, -1, calls.append)
        self.assertEqual(finished.seconds, 0)
        self.assertEqual(calls, [124])

    def test_completed_guard_does_not_exit(self):
        launcher = module('run_supervised')
        class Finished:
            def wait(self, seconds):
                return True
        calls = []
        launcher.hard_deadline(Finished(), 0, calls.append)
        self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
