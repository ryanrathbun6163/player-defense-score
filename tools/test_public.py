"""Run the portable, standard-library-only checks included in a public clone.

This explicit subset exercises synthetic/metadata contracts, not model accuracy.
Private footage, trained weights, local execution receipts and GPU libraries are
not required. The full research suite remains available through unittest.
"""
from pathlib import Path
import os
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]

# Some research test modules mix portable fixtures with private integration
# checks. Select the public classes/methods explicitly instead of silently
# skipping missing assets or importing every research test during discovery.
TEST_TARGETS = (
    "test_pipeline_foundation",
    "test_ball_annotation_foundation.BallAnnotationValidationTests",
    "test_ball_annotation_foundation.BallDetectionRunValidationTests",
    "test_ball_annotation_foundation.BallDetectionEvaluationTests",
    "test_ball_point_evaluation",
    "test_saved_score_failure_data",
    "test_saved_score_failure_analysis",
    "test_saved_score_failure_study",
    "test_candidate_acceptance_data",
    "test_candidate_acceptance_evaluation",
    "test_candidate_proposal_coverage_analysis",
    "test_candidate_producer_transfer_analysis",
    "test_fresh_game_analysis",
    "test_dual_view_context_analysis.GatesAndTransport",
    "test_dual_view_context_recovery_analysis",
    "test_dual_view_context_recovery_supervision.RecoveryDeadlineTests.test_exact_prior_debit_and_total_cap",
    "test_dual_view_context_recovery_supervision.RecoveryDeadlineTests.test_supervisor_created_later_cannot_reset_deadline",
    "test_dual_view_context_recovery_supervision.RecoveryDeadlineTests.test_wall_clock_change_cannot_extend_deadline",
    "test_dual_view_context_recovery_supervision.RecoveryDeadlineTests.test_stale_30minute_policy_or_inconsistent_contract_is_rejected",
    "test_dual_view_context_recovery_supervision.RecoveryDeadlineTests.test_ready_handshake_rejects_old_timings_even_when_status_is_ready",
    "test_dual_view_context_recovery_supervision.RecoveryDeadlineTests.test_unclean_prior_cleanup_or_changed_debit_rejected",
)


def main():
    if sys.version_info < (3, 11):
        print("Public checks require Python 3.11 or newer.", file=sys.stderr)
        return 2
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONNOUSERSITE"] = "1"
    if not sys.flags.no_site:
        # Excluding site-packages makes accidental numerical/model dependencies
        # fail on the maintainer's machine as they would in a clean public clone.
        return subprocess.run(
            [sys.executable, "-B", "-S", str(Path(__file__).resolve())],
            cwd=ROOT, check=False,
        ).returncode

    os.chdir(ROOT)
    sys.path[:0] = [str(ROOT / "tests"), str(ROOT)]
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name in TEST_TARGETS:
        selected = loader.loadTestsFromName(name)
        if not selected.countTestCases():
            print(f"Public target contains no tests: {name}", file=sys.stderr)
            return 2
        suite.addTests(selected)
    if loader.errors:
        print("\n".join(loader.errors), file=sys.stderr)
        return 2
    print(f"Public CPU checks: {suite.countTestCases()} tests; site-packages disabled.", flush=True)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.skipped:
        print("Public checks must run without skipped tests.", file=sys.stderr)
    return 0 if result.wasSuccessful() and not result.skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
