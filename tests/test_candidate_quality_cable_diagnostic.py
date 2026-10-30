"""CPU-only checks for scope, producer transport, timing and arithmetic preservation."""
import ast
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from src.ball_tracking import candidate_quality_cable_diagnostic as diagnostic
from src.ball_tracking import candidate_quality_post_driver_resume as recovery
from src.ball_tracking import gpu_supervision

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / recovery.OUTPUT


class CandidateQualityCableDiagnosticTests(unittest.TestCase):
    def test_metadata_import_does_not_load_torch(self):
        result = subprocess.run([sys.executable, "-B", "-c",
            "import sys;from src.ball_tracking import candidate_quality_cable_diagnostic;assert 'torch' not in sys.modules"],
            cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_budget_uses_actual_captured_policy_start_including_startup(self):
        policy = json.loads((HISTORICAL / "monitoring/attempt_003/policy.json").read_text())
        start = datetime.fromisoformat(policy["created_at_utc"])
        fresh = diagnostic.remaining_wall_seconds(policy, start)
        self.assertEqual(fresh["stop_wait_seconds"], 570)
        after_startup = diagnostic.remaining_wall_seconds(policy, start+timedelta(seconds=120))
        self.assertEqual(after_startup["stop_wait_seconds"], 450)
        self.assertEqual(after_startup["remaining_original_pilot_seconds_before_diagnostic"], 2287)
        self.assertEqual(after_startup["absolute_budget_deadline_utc"], (start+timedelta(seconds=600)).isoformat())
        for seconds in (-3, 570, 600, 2946):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                diagnostic.remaining_wall_seconds(policy, start+timedelta(seconds=seconds))

    def test_policy_transport_from_actual_supervisor_producer(self):
        rows = [json.loads(line) for line in (HISTORICAL / "monitoring/attempt_003/telemetry.jsonl").read_text().splitlines()]
        sample = next(row for row in rows if "values" in row)
        class NoProcess:
            def __init__(self, command, cwd, log): self.pid = 1
            def active(self): return 0
            def wait_launcher(self): pass
            def exit_code(self): return 0
            def close(self): pass
        with tempfile.TemporaryDirectory(dir=ROOT / "data/outputs/t", prefix="clock_policy_test_") as folder:
            monitor = Path(folder) / "monitor"
            args = ["--run", "--monitor", diagnostic.MONITOR]
            with patch.object(gpu_supervision, "OwnedJob", NoProcess), patch.object(gpu_supervision, "sample", return_value=sample):
                result = gpu_supervision.supervise(ROOT, monitor, diagnostic.MODULE, args, sys.executable)
            self.assertEqual(result["returncode"], 0)
            policy = json.loads((monitor / "policy.json").read_text())
            diagnostic.validate_policy(policy)
            self.assertIn(diagnostic.MODULE, policy["command"][4])
            for change in ({"module": recovery.MODULE}, {"sample_seconds": 5}, {"automatic_retry": True},
                           {"arguments": ["--run"]}, {"temperature_stop_C": 90}):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    diagnostic.validate_policy(dict(policy, **change))

    def test_first_fit_endpoint_and_replay_counts_match_actual_records(self):
        audit = json.loads((HISTORICAL / recovery.PREPARATION / "checkpoint_audit.json").read_text())
        manifest = json.loads((HISTORICAL / "preparation/fits/leave_chi_out/manifest.json").read_text())
        journal = [json.loads(line) for line in (HISTORICAL / "attempt_003/journal.jsonl").read_text().splitlines()]
        returned = [row for row in journal if row["event"] == "train_return"]
        self.assertEqual(audit["logical_fit_steps"], diagnostic.START_STEP)
        self.assertEqual(manifest["fitting_candidates"], 11954)
        self.assertEqual((11954+31)//32*4, diagnostic.MAX_UPDATES)
        self.assertEqual(len(returned), diagnostic.PRIOR_RETURNED_OVERLAP)
        self.assertEqual(max(row["step"] for row in returned), 1763)
        counters = dict.fromkeys(recovery.RECOVERED_COUNTERS, 0)
        counters.update(training_forwards_attempted=1496, training_forwards_returned=1496,
                        optimizer_updates=1496, training_candidate_presentations=47816)
        result = diagnostic.accounting(counters)
        self.assertEqual(result["logical_replay_branch"]["optimizer_updates"], 2244)
        self.assertEqual(result["updates_replaying_attempt003"], 1015)
        self.assertEqual(result["updates_beyond_attempt003_last_returned"], 481)
        self.assertEqual(result["cumulative_physical_lower_bound"]["optimizer_updates"], 4082)
        for change in ({"optimizer_updates": 1497}, {"scoring_forwards_attempted": 1}, {"parity_forwards_attempted": 1}):
            with self.subTest(change=change), self.assertRaises(ValueError): diagnostic.accounting(dict(counters, **change))

    def test_training_arithmetic_ast_matches_frozen_producer(self):
        def training_body(module):
            tree = ast.parse(Path(module.__file__).read_text())
            run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run")
            batch = next(n for n in ast.walk(run) if isinstance(n, ast.For)
                         and isinstance(n.target, ast.Name) and n.target.id == "batch")
            start = next(i for i,n in enumerate(batch.body) if isinstance(n, ast.Assign)
                         and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "losses")
            end = next(i for i,n in enumerate(batch.body) if isinstance(n, ast.For)
                       and isinstance(n.target, ast.Tuple) and any(isinstance(x,ast.Name) and x.id == "row" for x in n.target.elts))
            nodes = [n for n in batch.body[start:end+1]
                     if not (isinstance(n, ast.If) and isinstance(n.test, ast.Name) and n.test.id == "first_batch")]
            return ast.dump(ast.Module(body=nodes, type_ignores=[]), include_attributes=False)
        self.assertEqual(training_body(diagnostic), training_body(recovery))
        tree = ast.parse(Path(diagnostic.__file__).read_text())
        run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run")
        attributes = {n.attr for n in ast.walk(run) if isinstance(n, ast.Attribute)}
        self.assertNotIn("forward_with_features", attributes)
        self.assertNotIn("inference_mode", attributes)
        self.assertNotIn("eval", attributes)
        epoch_loop = next(n for n in ast.walk(run) if isinstance(n, ast.For)
                          and isinstance(n.target, ast.Name) and n.target.id == "epoch")
        self.assertEqual(ast.dump(epoch_loop.iter), ast.dump(ast.parse("range(3, 7)", mode="eval").body))

    def test_approval_and_scope_are_specific_and_cannot_expand(self):
        proposal = json.loads((ROOT / "data/outputs/t/reference_clock_test_proposal_v0_1/proposal.json").read_text())
        freeze = {"schema_version": "candidate_quality_cable_diagnostic/v0.1",
            "max_total_seconds": proposal["max_total_seconds"], "cleanup_reserve_seconds": proposal["cleanup_reserve_seconds"],
            "remaining_pilot_seconds": diagnostic.REMAINING_PILOT_SECONDS, "first_fit_only": proposal["workload"]["fit"],
            "start_step": proposal["workload"]["starting_logical_step"], "end_step": proposal["workload"]["ending_logical_step"],
            "max_updates": proposal["workload"]["max_physical_updates"], "scoring": proposal["workload"]["scoring"],
            "debug_mode_enabled": False, "agent_settings_change": False,
            "diagnostic_intervention": "previously_user_changed_native_Corsair_cable_path"}
        diagnostic.validate_freeze(freeze)
        for change in ({"max_total_seconds": 2287}, {"first_fit_only": "all_nba"}, {"scoring": True}, {"max_updates": 1497}):
            with self.subTest(change=change), self.assertRaises(ValueError): diagnostic.validate_freeze(dict(freeze, **change))
        link = {"path": "new/execution_freeze.json", "bytes": 1, "sha256": "fixed"}
        approval = dict(run_approved=True, execution_freeze=link, max_total_seconds=600,
                        automatic_retry=False, diagnostic_intervention="previously_user_changed_native_Corsair_cable_path",
                        debug_mode_enabled=False, settings_change_authorized=False,
                        approval_text="explicit diagnostic approval")
        diagnostic.validate_execution_approval(approval, link)
        for change in ({"run_approved": False}, {"max_total_seconds": 601}, {"automatic_retry": True}, {"approval_text": ""},
                       {"debug_mode_enabled": True}, {"settings_change_authorized": True},
                       {"diagnostic_intervention": "NVIDIA Debug Mode off -> on"}):
            with self.subTest(change=change), self.assertRaises(ValueError): diagnostic.validate_execution_approval(dict(approval, **change), link)

    def test_actual_interruption_producers_preserve_partial_forward_and_debit(self):
        failed = diagnostic.read(HISTORICAL / "attempt_004/failed.json")
        launcher = diagnostic.read(ROOT / "data/outputs/t/training_retry_2026-10-29_v0_1/launcher_finished.json")
        budget = diagnostic.read(ROOT / "data/outputs/t/reference_clock_test_v0_1/post_reboot_preservation_budget.json")
        diagnostic.validate_previous_accounting(failed, launcher, budget)
        zero = dict.fromkeys(recovery.RECOVERED_COUNTERS, 0)
        result = diagnostic.accounting(zero)
        source = failed["accounting"]["cumulative_physical_lower_bound"]
        for key, actual in result["prior_durable_physical_lower_bound"].items():
            self.assertEqual(actual, source[key])
        self.assertEqual(result["attempt004_returned_forward_without_optimizer_update"], 1)
        self.assertEqual(result["prior_scientific_unsaved_updates_by_attempt"]["attempt_004"], 82)
        for changed in (dict(launcher, charged_elapsed_seconds=0), dict(launcher, event_remaining_owned_processes=1)):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                diagnostic.validate_previous_accounting(failed, changed, budget)
        with self.assertRaises(ValueError):
            diagnostic.validate_previous_accounting(failed, launcher, dict(budget, remaining_original_pilot_seconds=3600))

    def test_reported_intervention_is_not_launch_readiness_or_permission(self):
        reported = dict(cable_change_user_reported=True, current_debug_mode_enabled=False,
                        debug_mode_state_basis="user_reported", debug_mode_setting_changed_by_agent=False)
        diagnostic.validate_intervention_record(reported)
        with self.assertRaises(ValueError): diagnostic.validate_launch_readiness(reported)
        with self.assertRaises(ValueError): diagnostic.validate_execution_approval(reported, {})
        for change in ({"current_debug_mode_enabled": True}, {"debug_mode_setting_changed_by_agent": True},
                       {"debug_mode_state_basis": "independently_verified"}, {"cable_change_user_reported": False}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                diagnostic.validate_intervention_record(dict(reported, **change))
        now = datetime(2026, 10, 29, 22, 0, tzinfo=timezone.utc)
        ready = dict(at_utc=now.isoformat(), driver_version="617.42",
                     gpu_uuid="GPU-f26f32f8-e85b-0d38-651e-d5c54097525b",
                     ram_configured_mt_s=[5200, 5200], isolation_conflicts=[], existing_gpu_workers=[],
                     debug_mode_enabled=False, debug_mode_state_basis="user_reported",
                     settings_changed=False, fresh_launch_checks_passed=True)
        diagnostic.validate_launch_readiness(ready, now)
        diagnostic.validate_launch_readiness(dict(ready, debug_mode_state_basis="ui_observed"), now)
        for change in ({"debug_mode_enabled": True}, {"settings_changed": True}, {"fresh_launch_checks_passed": False}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                diagnostic.validate_launch_readiness(dict(ready, **change), now)

    def test_launch_readiness_rejects_stale_missing_and_changed_environment(self):
        now = datetime(2026, 10, 29, 22, 0, tzinfo=timezone.utc)
        ready = dict(at_utc=(now-timedelta(seconds=120)).isoformat(), driver_version="617.42",
                     gpu_uuid="GPU-f26f32f8-e85b-0d38-651e-d5c54097525b",
                     ram_configured_mt_s=[5200, 5200], isolation_conflicts=[], existing_gpu_workers=[],
                     debug_mode_enabled=False, debug_mode_state_basis="user_reported",
                     settings_changed=False, fresh_launch_checks_passed=True)
        diagnostic.validate_launch_readiness(ready, now)
        invalid_changes = (
            {"at_utc": (now-timedelta(seconds=120.001)).isoformat()},
            {"at_utc": (now+timedelta(seconds=3)).isoformat()},
            {"at_utc": now.replace(tzinfo=None).isoformat()},
            {"at_utc": now.astimezone(timezone(timedelta(hours=-7))).isoformat()},
            {"at_utc": None}, {"at_utc": "invalid"},
            {"driver_version": "616.56"}, {"gpu_uuid": "other-device"},
            {"ram_configured_mt_s": [6000, 6000]}, {"ram_configured_mt_s": [5200]},
            {"isolation_conflicts": ["Lively"]}, {"existing_gpu_workers": [1234]},
            {"debug_mode_state_basis": "inferred_after_reboot"})
        for change in invalid_changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                diagnostic.validate_launch_readiness(dict(ready, **change), now)
        for missing in ready:
            changed = dict(ready); del changed[missing]
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                diagnostic.validate_launch_readiness(changed, now)

    def test_output_attempt_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "data/outputs/t", prefix="clock_destination_test_") as folder:
            root = Path(folder); (root / diagnostic.OUTPUT).mkdir(parents=True)
            first = diagnostic.make_attempt_directory(root)
            (first / "sentinel").write_bytes(b"preserve")
            with self.assertRaises(FileExistsError): diagnostic.make_attempt_directory(root)
            self.assertEqual((first / "sentinel").read_bytes(), b"preserve")


if __name__ == "__main__":
    unittest.main()
