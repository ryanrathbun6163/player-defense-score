"""Changed reference-clock contracts and unchanged arithmetic, entirely on CPU."""
import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys
import unittest

from src.ball_tracking import candidate_quality_cable_reference_diagnostic as diagnostic
from src.ball_tracking import candidate_quality_cable_diagnostic as prior

ROOT = Path(__file__).resolve().parents[1]


class CandidateQualityCableReferenceDiagnosticTests(unittest.TestCase):
    def readiness(self, now, changed=False):
        return dict(at_utc=now.isoformat(), driver_version="617.42",
                    gpu_uuid="GPU-f26f32f8-e85b-0d38-651e-d5c54097525b",
                    power_limit_W=250,
                    ram_configured_mt_s=[5200, 5200], isolation_conflicts=[], existing_gpu_workers=[],
                    debug_mode_enabled=True, debug_mode_state_basis="ui_observed",
                    configuration_changes=["NVIDIA Debug Mode"] if changed else [],
                    unexpected_setting_changes=[], settings_changed=changed,
                    fresh_launch_checks_passed=True)

    def test_metadata_import_and_separate_attempt_identity(self):
        code = "import sys;from src.ball_tracking import candidate_quality_cable_reference_diagnostic;assert 'torch' not in sys.modules"
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotEqual(diagnostic.OUTPUT, prior.OUTPUT)
        self.assertNotEqual(diagnostic.MODULE, prior.MODULE)
        self.assertEqual(diagnostic.MAX_TOTAL_SECONDS, 600)
        self.assertEqual(diagnostic.CLEANUP_RESERVE_SECONDS, 30)
        self.assertEqual(diagnostic.REMAINING_PILOT_SECONDS, 2287)

    def test_historical_off_observation_is_preserved_separately_from_planned_on(self):
        actual = diagnostic.read(ROOT / prior.OUTPUT / "intervention_record.json")
        prior.validate_intervention_record(actual)
        diagnostic.validate_historical_intervention_record(actual)
        self.assertFalse(actual["current_debug_mode_enabled"])
        choice = dict(planned_debug_mode_enabled=True, actual_setting_changed=False,
                      user_allows_configuration_selection=True, workload_launch_authorized=False)
        diagnostic.validate_configuration_choice(choice)
        with self.assertRaises(ValueError): diagnostic.validate_configuration_choice(actual)
        with self.assertRaises(ValueError): diagnostic.validate_execution_approval(choice, {})
        for key in choice:
            with self.subTest(key=key), self.assertRaises(ValueError):
                diagnostic.validate_configuration_choice(dict(choice, **{key: not choice[key]}))

    def test_exact_execution_permission_allows_only_reference_clock_setting(self):
        link = dict(path="prepared/execution_freeze.json", bytes=1, sha256="test-only")
        approval = dict(run_approved=True, execution_freeze=link, max_total_seconds=600,
                        automatic_retry=False, diagnostic_intervention="previously_user_changed_native_Corsair_cable_path",
                        debug_mode_enabled=True, settings_change_authorized=True,
                        allowed_setting_changes=["NVIDIA Debug Mode"], approval_text="test-only explicit execution approval")
        diagnostic.validate_execution_approval(approval, link)
        for change in ({"run_approved": False}, {"debug_mode_enabled": False}, {"settings_change_authorized": False},
                       {"allowed_setting_changes": []}, {"allowed_setting_changes": ["NVIDIA Debug Mode", "Power limit"]},
                       {"automatic_retry": True}, {"max_total_seconds": 601}, {"approval_text": ""}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                diagnostic.validate_execution_approval(dict(approval, **change), link)
        freeze = dict(schema_version="candidate_quality_cable_reference_diagnostic/v0.2",
                      max_total_seconds=600, cleanup_reserve_seconds=30, remaining_pilot_seconds=2287,
                      first_fit_only="leave_chi_out", start_step=748, end_step=2244, max_updates=1496,
                      scoring=False, debug_mode_enabled=True, agent_settings_change=False,
                      diagnostic_intervention="previously_user_changed_native_Corsair_cable_path")
        diagnostic.validate_freeze(freeze)
        with self.assertRaises(ValueError): diagnostic.validate_freeze(dict(freeze, debug_mode_enabled=False))
        with self.assertRaises(ValueError): diagnostic.validate_freeze(dict(freeze, agent_settings_change=True))

    def test_fresh_readiness_accepts_only_observed_on_and_recorded_allowed_change(self):
        now = datetime(2026, 10, 29, 22, 0, tzinfo=timezone.utc)
        ready = self.readiness(now)
        diagnostic.validate_launch_readiness(ready, now)
        diagnostic.validate_launch_readiness(self.readiness(now, changed=True), now)
        diagnostic.validate_launch_readiness(dict(ready, debug_mode_state_basis="user_reported"), now)
        invalid = ({"debug_mode_enabled": False}, {"debug_mode_state_basis": "planned"},
                   {"configuration_changes": ["NVIDIA Debug Mode"], "settings_changed": False},
                   {"configuration_changes": [], "settings_changed": True},
                   {"configuration_changes": ["Power limit"], "settings_changed": True},
                   {"unexpected_setting_changes": ["GPU clocks"]},
                   {"at_utc": (now-timedelta(seconds=121)).isoformat()},
                   {"at_utc": (now+timedelta(seconds=3)).isoformat()},
                   {"at_utc": now.replace(tzinfo=None).isoformat()},
                   {"driver_version": "616.56"}, {"gpu_uuid": "other"},
                   {"power_limit_W": 200},
                   {"ram_configured_mt_s": [6000, 6000]}, {"isolation_conflicts": ["Lively"]},
                   {"existing_gpu_workers": [123]}, {"fresh_launch_checks_passed": False})
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(ValueError):
                diagnostic.validate_launch_readiness(dict(ready, **change), now)
        for missing in ready:
            changed = dict(ready); del changed[missing]
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                diagnostic.validate_launch_readiness(changed, now)

    def test_training_batch_arithmetic_and_endpoints_are_identical_to_off_preparation(self):
        def parts(module):
            tree = ast.parse(Path(module.__file__).read_text())
            run = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run")
            batch = next(node for node in ast.walk(run) if isinstance(node, ast.For)
                         and isinstance(node.target, ast.Name) and node.target.id == "batch")
            epoch = next(node for node in ast.walk(run) if isinstance(node, ast.For)
                         and isinstance(node.target, ast.Name) and node.target.id == "epoch")
            return ast.dump(batch, include_attributes=False), ast.dump(epoch.iter, include_attributes=False)
        self.assertEqual(parts(diagnostic), parts(prior))
        self.assertEqual((diagnostic.START_STEP, diagnostic.END_STEP, diagnostic.MAX_UPDATES), (748, 2244, 1496))
        self.assertEqual(diagnostic.accounting(dict.fromkeys(diagnostic.recovery.RECOVERED_COUNTERS, 0))["cumulative_physical_lower_bound"],
                         prior.accounting(dict.fromkeys(prior.recovery.RECOVERED_COUNTERS, 0))["cumulative_physical_lower_bound"])


if __name__ == "__main__":
    unittest.main()
