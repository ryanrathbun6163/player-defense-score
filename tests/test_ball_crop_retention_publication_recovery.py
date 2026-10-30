"""Fabricated publication-recovery evidence; never open real saved outputs.

Fixtures live in an ignored temporary tree. Production science is not selected,
scored, rendered or decoded by these tests.
"""
import copy
from contextlib import ExitStack
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import cv2
import numpy as np

from src.ball_tracking import crop_retention_experiment as original
from src.ball_tracking import crop_retention_publication_recovery as recovery
from src.ball_tracking import crop_retention_review as review
from src.ball_tracking import crop_retention_resources as resources
from src.ball_tracking import prepare_detection_visual_review as zoom
from src.ball_tracking.development_experiments import canonical_sha256, read_json, sha256_file
from test_ball_crop_retention_recovery import binding, write_json
from test_ball_crop_retention_render_recovery import (
    SyntheticRenderRecovery, forbid_scientific_work,
)
from test_ball_crop_retention_review import context_fixture


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION_COMMIT = "d" * 40
PUBLICATION_SPEC = "e" * 64


def fabricated_bundle(root):
    """Render invented pixels only to create a small, genuine PNG/MP4 fixture.

Callers patch tile dimensions before using this helper. Recovery tests prohibit
all render entry points after this fixture has been created.
"""
    context, experiment, evaluation, _, _, observations, reports, _ = context_fixture(root)
    context.update(commit=recovery.RENDER_COMMIT, spec_sha256=recovery.RENDER_SPEC)
    # The final frame has an explicitly missing graph output, not a placeholder
    # coordinate. Its saved FN is deliberately retained without re-scoring.
    for arm in review.ARMS:
        observation, report = observations[arm, "all"], reports[arm, "all"]
        frame = observation["frames"][-1]
        frame["emitted_candidate_indices"] = []
        frame["decision_reason"] = "empty_hypothesis"
        frame["ranking"]["winner"] = {"endpoint": None, "score": 0.0, "path": []}
        report["frame_results"][-1].update(
            input_detection_count=0, accepted_detection_count=0, matched_candidate_index=None,
            false_positive_count=0, false_negative_count=1, matched_center_error_px=None,
            matched_effective_center_error_px=None)
        report["observations_content_sha256"] = canonical_sha256(observation)
    for key, observation in observations.items():
        for row in observation["frames"]:
            row["output_state"] = "tentative_observation" if row["emitted_candidate_indices"] else "no_accepted_observation"
        reports[key]["observations_content_sha256"] = canonical_sha256(observation)
    with patch.object(original, "load_saved_control", side_effect=experiment.load_saved_control):
        prepared = review.prepare_window(root, context, "synthetic_development_window",
            observation_loader=lambda r, c, u: experiment.load_new_observations(r, c, u),
            score_loader=lambda r, c, w: evaluation.load_window_score(r, c, w))
        target = root / review.OUTPUT_ROOT / "review/windows" / prepared.window["window_id"]
        with patch.object(review, "render_frame", side_effect=semantic_frame):
            review.render_prepared_window(root, prepared, target)
    manifest = read_json(target / "manifest.json")
    snapshot = {"window_id": prepared.window["window_id"], "manifest": binding(root, target / "manifest.json"),
                "assets": [binding(root, target / a["path"]) for a in manifest["assets"]],
                "asset_count": 301, "status": "new_snapshot_unreceipted_not_accepted",
                "successful_render_attempt_id": None,
                "failed_render_attempt_id": recovery.FAILED_RENDER,
                "historical_success_binding_verified": False}
    return context, prepared, target, snapshot


def semantic_frame(source, annotation, frame, observations, reports):
    """Invented pixels with the production panel/focus metadata contract."""
    comparison = np.zeros((review.TILE_HEIGHT * 4, review.TILE_WIDTH * 3, 3), np.uint8)
    width = source.shape[1]
    sidebar = max(520, min(720, round(width * .34)))
    native = {key: np.zeros((source.shape[0] + review.NATIVE_HEADER, width + sidebar, 3), np.uint8)
              for key in review.VIEW_KEYS}
    closeups = np.zeros((4 * zoom.ZOOM_PANEL_HEIGHT_PX, zoom.ZOOM_PANEL_WIDTH_PX, 3), np.uint8)
    focus, kind = zoom._focus_point(annotation, frame,
        [zoom.DetectionReviewView("synthetic", .01, 10, "descriptive")], width, source.shape[0])
    x, y = map(round, focus)
    half = zoom.ZOOM_HALF_SIZE_PX
    regions = [{"arm": arm, "focus_type": kind, "focus_xy_px": list(focus),
                "requested_source_crop_xyxy_px": [x-half, y-half, x+half+1, y+half+1],
                "zoom_factor": zoom.ZOOM_FACTOR, "raw_unmarked_view_included": True} for arm in review.ARMS]
    return comparison, native, closeups, regions


class TemporaryRoot(unittest.TestCase):
    def setUp(self):
        parent = ROOT / "data/outputs/t/publication_tests"
        parent.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="p_", dir=parent)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()


class SyntheticPublicationRecovery(SyntheticRenderRecovery):
    """Frozen 50-attempt history with five receipted and one failed publication.

Window manifests here are deliberately tiny invented records. Tests of bundle
content validation use a separate complete fabricated bundle fixture.
"""

    def __init__(self, root):
        super().__init__(root)
        self.render_context = copy.deepcopy(self.context)
        self.render_context.update(commit=recovery.RENDER_COMMIT, spec_sha256=recovery.RENDER_SPEC)
        self.context.update(commit=PUBLICATION_COMMIT, spec_sha256=PUBLICATION_SPEC,
                            render_context=self.render_context)
        self.add_frozen_render("preflight", "verify")
        self.add_frozen_render("preflight", "render")
        self.window_records = []
        for index, window in enumerate(self.proposal["windows"]):
            target = self.output / "review/windows" / window["window_id"] / "manifest.json"
            write_json(target, {"synthetic": "Immutable window snapshot", "window_id": window["window_id"]})
            frozen = binding(root, target)
            if index < 5:
                record = self.add_frozen_render("render", window["window_id"], [frozen])
            else:
                record = self.add_frozen_render("render", window["window_id"], success=False,
                                                attempt_id=recovery.FAILED_RENDER)
            self.window_records.append({"window_id": window["window_id"], "manifest": frozen,
                "assets": [], "asset_count": 301,
                "successful_render_attempt_id": record["attempt_id"] if index < 5 else None,
                "failed_render_attempt_id": record["attempt_id"] if index == 5 else None,
                "status": "receipted_manifest_and_asset_hashes_verified" if index < 5
                          else "new_snapshot_unreceipted_not_accepted",
                "historical_success_binding_verified": index < 5})
        preservation = self.output / "audit/synthetic_publication_preservation.json"
        self.preservation = {"review_windows": self.window_records, "verified_bindings": [],
                             "sixth_window_adopted": False, "comparison_complete": False,
            "preserved_old_evidence": {"completed_selection_manifests": self.interruption["completed_selection_manifests"],
                "completed_trace_bindings": self.interruption["completed_trace_bindings"],
                "completed_scoring_artifacts": self.interruption["completed_scoring_artifacts"],
                "partial_review_files": self.interruption["partial_review_files"],
                "failed_scoring_partial": self.failure["partial"], "failed_scoring_log": self.failure["log"],
                "failed_render_log": self.interruption["failed_render_log"]},
            "preserved_input_bindings": [w["crop_candidates"] for w in self.proposal["windows"]],
            "absent_finalization_artifacts": [(self.output / name).relative_to(root).as_posix()
                                             for name in recovery.OUTPUTS.values()]}
        write_json(preservation, self.preservation)
        self.preservation_binding = binding(root, preservation)
        self.add_frozen_render("publication-diagnosis", "", [self.preservation_binding])
        rows = []
        for identifier, attempt in self.journal._attempts().items():
            finish = attempt["finished"]
            result = finish["worker_result"]
            rows.append({"attempt_id": identifier, "unit_key": attempt["start"]["unit_key"],
                "success": finish["success"], "completion_event_sha256": finish["sha256"],
                "reservation": binding(root, self.output / "attempts" / (identifier + ".reservation.json")),
                "completion": binding(root, self.output / "attempts" / (identifier + ".completion.json")),
                "worker_result": binding(root, self.output / result["path"]) if result else None})
        self.publication_checkpoint = {"journal_prefix": {"events": self.event_bindings(),
                "chain_tip_sha256": self.journal.events[-1]["sha256"], "attempts": rows},
            "completed_attempts": 50, "successful_attempts": 47, "failed_attempts": 3,
            "cumulative_active_seconds": self.journal.consumed(),
            "remaining_cumulative_seconds": 14400-self.journal.consumed(),
            "review_windows": self.window_records, "preservation_audit": self.preservation_binding}
        self.context.update(checkpoint=self.publication_checkpoint, preservation=self.preservation)
        checkpoint_path = self.output / "audit/synthetic_publication_checkpoint.json"
        write_json(checkpoint_path, self.publication_checkpoint)
        self.context["manifest"] = {"output_root": original.OUTPUT_ROOT,
                                    "preservation_audit": self.preservation_binding,
                                    "resource_checkpoint": binding(root, checkpoint_path)}

    def patch_scope(self):
        stack = ExitStack()
        values = {"PREFIX_COUNT": len(self.publication_checkpoint["journal_prefix"]["events"]),
                  "PREFIX_TIP": self.publication_checkpoint["journal_prefix"]["chain_tip_sha256"],
                  "KNOWN_FAILURES": {r["attempt_id"] for r in self.publication_checkpoint["journal_prefix"]["attempts"]
                                     if not r["success"]},
                  "SIXTH_WINDOW": self.proposal["windows"][-1]["window_id"],
                  "SIXTH_MANIFEST_SHA": self.window_records[-1]["manifest"]["sha256"]}
        for name, value in values.items():
            stack.enter_context(patch.object(recovery, name, value))
        return stack

    def add_frozen_render(self, stage, key, artifacts=None, *, success=True, attempt_id=None):
        with ExitStack() as stack:
            if attempt_id is not None:
                stack.enter_context(patch.object(resources.uuid, "uuid4", return_value=SimpleNamespace(hex=attempt_id)))
            return self.add_render_attempt(stage, key, artifacts, success=success,
                                           commit=recovery.RENDER_COMMIT, spec=recovery.RENDER_SPEC)

    def add_publication_attempt(self, stage, key="", artifacts=None, *, success=True,
                                commit=PUBLICATION_COMMIT, spec=PUBLICATION_SPEC):
        attempt, remaining = self.journal.reserve("publication-recovery:" + stage + ":" + key, False)
        append = self.journal.append
        def with_budget(kind, **details):
            if kind == "finished":
                details["time_budget_seconds"] = remaining
            return append(kind, **details)
        with patch.object(self.journal, "append", side_effect=with_budget):
            return self.finish_attempt(attempt, stage, artifacts or [], stage=stage, key=key,
                                       success=success, commit=commit, spec=spec)


class PublicationDispatchTests(TemporaryRoot):
    def test_selector_scoring_rendering_and_helper_stages_are_not_dispatchable(self):
        forbidden = ("select", "score", "score-final", "render", "completion-audit",
                     "presentation", "unknown")
        for stage in forbidden:
            with self.subTest(stage=stage), patch.object(recovery, "_metadata",
                    side_effect=AssertionError("Forbidden stage opened authority")):
                with self.assertRaises(ValueError):
                    recovery.run_recovery(self.root, self.root / "unused.json", stage=stage)
            with self.subTest(worker=stage), patch.object(recovery, "wait_for_supervisor",
                    side_effect=AssertionError("Forbidden worker reached supervisor")):
                with self.assertRaises(ValueError):
                    recovery._worker(self.root, self.root / "unused.json", stage, "")

    def test_dry_run_is_metadata_only_and_never_opens_saved_science(self):
        with patch.object(recovery, "_metadata", return_value={"spec_sha256": PUBLICATION_SPEC}) as metadata, \
                patch.object(recovery, "load_context", side_effect=AssertionError("Unsupervised saved data")), \
                patch.object(recovery, "run_supervised", side_effect=AssertionError("Dry-run worker")):
            result = recovery.run_recovery(self.root, self.root / "unused.json", dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertFalse(metadata.call_args.args[2])

    def test_dirty_tree_and_nonempty_index_fail_before_authority_reads(self):
        for dirty, index in ((" M source.py", ""), ("", "source.py")):
            def git(root, *args):
                return {("branch", "--show-current"): "codex/ball-detector-baseline",
                        ("status", "--porcelain=v1"): dirty,
                        ("diff", "--cached", "--name-only"): index}[args]
            with self.subTest(dirty=dirty, index=index), patch.object(original, "_git", side_effect=git), \
                    patch.object(recovery, "read_json", side_effect=AssertionError("Authority read before clean gate")):
                with self.assertRaises(ValueError):
                    recovery._metadata(self.root, self.root / "manifest.json", True)

    def context(self):
        return {"commit": PUBLICATION_COMMIT, "spec_sha256": PUBLICATION_SPEC,
                "output_root": self.root / original.OUTPUT_ROOT,
                "proposal": {"windows": [{"window_id": "w" + str(i)} for i in range(6)],
                             "resource_limits": {"maximum_cumulative_seconds": 14400}}}

    def test_recovery_dispatch_has_only_preflight_acceptance_and_finalization(self):
        context = self.context()
        with ExitStack() as stack:
            forbid_scientific_work(stack)
            stack.enter_context(patch.object(review, "render_window", side_effect=AssertionError("Renderer replay")))
            stack.enter_context(patch.object(review, "render_prepared_window", side_effect=AssertionError("Renderer replay")))
            stack.enter_context(patch.object(recovery, "_metadata", return_value=context))
            dispatch = stack.enter_context(patch.object(recovery, "run_supervised", return_value={"success": True}))
            result = recovery.run_recovery(self.root, self.root / "manifest.json", stage="recover")
        keys = [call.args[1] for call in dispatch.call_args_list]
        self.assertEqual(len(keys), 5)
        self.assertEqual([key.split(":")[1] for key in keys], ["preflight", "accept", "review-final", "completion-audit", "presentation"])
        self.assertTrue(all(call.args[0] == context["output_root"] for call in dispatch.call_args_list))
        self.assertTrue(all(call.kwargs["selection_unit"] is False for call in dispatch.call_args_list))
        self.assertTrue(all(call.kwargs["require_result"] is True for call in dispatch.call_args_list))
        self.assertTrue(all(call.kwargs["cwd"] == self.root for call in dispatch.call_args_list))
        self.assertFalse(result["selection_executed"])
        self.assertFalse(result["scoring_executed"])

    def test_failure_stops_dispatch_without_retry_or_finalization(self):
        for fail_at in range(5):
            outcomes = [{"success": True}] * fail_at + [resources.ResourceLimitError("synthetic resource abort")]
            with self.subTest(fail_at=fail_at), patch.object(recovery, "_metadata", return_value=self.context()), \
                    patch.object(recovery, "run_supervised", side_effect=outcomes) as dispatch:
                with self.assertRaisesRegex(resources.ResourceLimitError, "synthetic resource abort"):
                    recovery.run_recovery(self.root, self.root / "manifest.json", stage="recover")
            self.assertEqual(dispatch.call_count, fail_at + 1)

    def test_supervisor_gate_precedes_loading_any_saved_output(self):
        with patch.object(recovery, "wait_for_supervisor", side_effect=RuntimeError("no supervisor")), \
                patch.object(recovery, "load_context", side_effect=AssertionError("Saved outputs loaded before gate")):
            with self.assertRaisesRegex(RuntimeError, "no supervisor"):
                recovery._worker(self.root, self.root / "manifest.json", "verify", "")


class PublicationHistoryTests(TemporaryRoot):
    def setUp(self):
        super().setUp()
        self.data = SyntheticPublicationRecovery(self.root)
        self.scope = self.data.patch_scope()
        self.addCleanup(self.scope.close)

    def test_frozen_fifty_attempt_prefix_preserves_all_three_failures_and_budget(self):
        d = self.data
        with ExitStack() as stack:
            forbid_scientific_work(stack)
            journal = recovery.verify_history(self.root, d.context)
        self.assertEqual(len(journal._attempts()), 50)
        self.assertEqual(sum(a["finished"]["success"] is False for a in journal._attempts().values()), 3)
        self.assertAlmostEqual(journal.consumed(), d.publication_checkpoint["cumulative_active_seconds"])
        _, remaining = journal.reserve("publication-recovery:preflight:recover", False)
        self.assertAlmostEqual(remaining, d.publication_checkpoint["remaining_cumulative_seconds"])
        self.assertTrue(d.partial.exists())

    def test_missing_or_changed_prefix_event_and_seals_reject_recovery(self):
        d = self.data
        prefix = d.publication_checkpoint["journal_prefix"]
        targets = [self.root / prefix["events"][3]["path"],
                   self.root / prefix["attempts"][-1]["reservation"]["path"],
                   self.root / prefix["attempts"][-1]["completion"]["path"]]
        for target in targets:
            before = target.read_bytes()
            for changed in (None, before + b" "):
                try:
                    if changed is None:
                        target.unlink()
                    else:
                        target.write_bytes(changed)
                    with self.subTest(path=target.name, missing=changed is None), \
                            self.assertRaises((ValueError, RuntimeError, FileNotFoundError)):
                        recovery.verify_history(self.root, d.context)
                finally:
                    target.write_bytes(before)

    def test_shortened_or_duplicate_frozen_attempt_inventory_is_rejected(self):
        d = self.data
        original_rows = d.publication_checkpoint["journal_prefix"]["attempts"]
        for changed in (original_rows[:-1], original_rows[:-1] + [original_rows[0]]):
            d.publication_checkpoint["journal_prefix"]["attempts"] = changed
            try:
                with self.subTest(count=len(changed)), self.assertRaises((ValueError, RuntimeError)):
                    recovery.verify_history(self.root, d.context)
            finally:
                d.publication_checkpoint["journal_prefix"]["attempts"] = original_rows

    def test_new_failure_cannot_be_added_to_known_failure_allowlist(self):
        d = self.data
        d.add_publication_attempt("accept", success=False)
        with self.assertRaises((ValueError, RuntimeError)):
            recovery.verify_history(self.root, d.context)

    def test_unfinished_attempt_requires_its_exact_active_supervisor_identity(self):
        d = self.data
        active, _ = d.journal.reserve("publication-recovery:preflight:recover", False)
        with patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": "not-the-active-attempt"}):
            with self.assertRaises((ValueError, RuntimeError)):
                recovery.verify_history(self.root, d.context)
        with patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": active}):
            self.assertEqual(len(recovery.verify_history(self.root, d.context)._attempts()), 51)

    def test_new_success_requires_new_commit_spec_and_unchanged_receipt_seals(self):
        d = self.data
        row = d.add_publication_attempt("preflight", "recover")
        recovery.completed_records(self.root, d.context)
        for field, old in (("commit", recovery.RENDER_COMMIT), ("spec_sha256", recovery.RENDER_SPEC)):
            with self.subTest(field=field), self.assertRaises((ValueError, RuntimeError)):
                recovery.completed_records(self.root, {**d.context, field: old})
        seal = self.root / row["completion"]["path"]
        seal.unlink()
        with self.assertRaises((ValueError, RuntimeError, FileNotFoundError)):
            recovery.completed_records(self.root, d.context)

    def test_unknown_scoring_or_render_success_cannot_authorize_output(self):
        for stage in ("score", "score-final", "render"):
            with self.subTest(stage=stage):
                # Every suffix failure is permanent, so isolate each invented
                # ledger instead of resetting its resource history.
                root = self.root / stage
                root.mkdir()
                d = SyntheticPublicationRecovery(root)
                d.add_publication_attempt(stage, "w5", [d.window_records[-1]["manifest"]])
                with d.patch_scope(), self.assertRaisesRegex(ValueError, "roles are forbidden"):
                    recovery.completed_records(root, d.context)

    def test_sixth_published_manifest_alone_is_not_an_acceptance_receipt(self):
        d = self.data
        self.assertTrue((self.root / d.window_records[-1]["manifest"]["path"]).is_file())
        self.assertNotIn("accept", recovery.completed_records(self.root, d.context))

    def rewrite_suffix(self, events):
        """Re-seal invented events to exercise semantics past hash checks."""
        d = self.data
        prefix = d.publication_checkpoint["journal_prefix"]["events"]
        previous = d.publication_checkpoint["journal_prefix"]["chain_tip_sha256"]
        for index, event in enumerate(events, len(prefix)):
            event = {k: v for k, v in event.items() if k != "sha256"}
            event["previous_sha256"] = previous
            event["sha256"] = canonical_sha256(event)
            previous = event["sha256"]
            write_json(d.output / "resource_events" / f"{index:08d}.json", event)
            if event["kind"] in ("started", "finished"):
                suffix = ".reservation.json" if event["kind"] == "started" else ".completion.json"
                write_json(d.output / "attempts" / (event["attempt_id"] + suffix), {"event_sha256": event["sha256"]})

    def test_success_cannot_hide_resource_overshoot_accounting_error_or_changed_budget(self):
        d = self.data
        d.add_publication_attempt("preflight", "recover")
        frozen = copy.deepcopy(d.journal.events[len(d.publication_checkpoint["journal_prefix"]["events"]):])
        cases = (("time_overshoot_seconds", .01), ("memory_overshoot_bytes", 1),
                 ("output_overshoot_bytes", 1), ("maximum_monitor_interval_seconds", 1.01),
                 ("final_accounting_error", "synthetic incomplete accounting"),
                 ("peak_worker_memory_bytes", d.limits["maximum_worker_memory_bytes"] + 1),
                 ("maximum_output_bytes", d.limits["maximum_total_new_output_bytes"] + 1),
                 ("final_accounting_output_bound_bytes", d.limits["maximum_total_new_output_bytes"] + 1),
                 ("minimum_free_disk_bytes", d.limits["minimum_free_disk_bytes"] - 1),
                 ("time_budget_seconds", frozen[-1]["time_budget_seconds"] + 1))
        for field, value in cases:
            altered = copy.deepcopy(frozen)
            altered[-1][field] = value
            self.rewrite_suffix(altered)
            try:
                with self.subTest(field=field), self.assertRaises(ValueError):
                    recovery.verify_history(self.root, d.context)
            finally:
                self.rewrite_suffix(frozen)

    def test_completion_cannot_borrow_another_attempts_success_receipt(self):
        d = self.data
        d.add_publication_attempt("preflight", "recover")
        events = copy.deepcopy(d.journal.events[len(d.publication_checkpoint["journal_prefix"]["events"]):])
        events[-1]["worker_result"] = copy.deepcopy(d.journal.events[len(d.publication_checkpoint["journal_prefix"]["events"]) - 1]["worker_result"])
        self.rewrite_suffix(events)
        with self.assertRaisesRegex(ValueError, "own worker receipt"):
            recovery.verify_history(self.root, d.context)

    def test_reservation_cannot_reset_consumed_time_even_with_matching_completion(self):
        d = self.data
        d.add_publication_attempt("preflight", "recover")
        events = copy.deepcopy(d.journal.events[len(d.publication_checkpoint["journal_prefix"]["events"]):])
        events[0]["reserved_seconds"] += 1
        events[-1]["time_budget_seconds"] += 1
        self.rewrite_suffix(events)
        with self.assertRaisesRegex(ValueError, "remaining allowance"):
            recovery.verify_history(self.root, d.context)

    def test_second_worker_cannot_start_before_first_worker_finishes(self):
        d = self.data
        first, _ = d.journal.reserve("publication-recovery:verify:", False)
        # Append directly to represent a forged overlapping reservation. The
        # real supervisor refuses a second worker while one is active.
        second = "f" * 32
        event = d.journal.append("started", attempt_id=second, unit_key="publication-recovery:verify:",
                                 selection_unit=False, reserved_seconds=1)
        write_json(d.output / "attempts" / (second + ".reservation.json"), {"event_sha256": event["sha256"]})
        with patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": first}), self.assertRaises(ValueError):
            recovery.verify_history(self.root, d.context)


class PublicationBundleTests(TemporaryRoot):
    def setUp(self):
        super().setUp()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(review, "TILE_WIDTH", 96))
        self.stack.enter_context(patch.object(review, "TILE_HEIGHT", 64))
        old, self.prepared, self.folder, self.snapshot = fabricated_bundle(self.root)
        self.context = {**old, "root": self.root, "output_root": self.root / original.OUTPUT_ROOT,
                        "render_context": old, "commit": PUBLICATION_COMMIT, "spec_sha256": PUBLICATION_SPEC,
                        "preservation": {"review_windows": [self.snapshot]}}
        self.stack.enter_context(patch.object(review, "prepare_window", return_value=self.prepared))
        self.stack.enter_context(patch.object(review, "render_window", side_effect=AssertionError("Renderer replay")))
        self.stack.enter_context(patch.object(review, "render_prepared_window", side_effect=AssertionError("Renderer replay")))
        forbid_scientific_work(self.stack)

    def validate(self, **kwargs):
        return recovery.validate_bundle(self.root, self.context, self.prepared.window["window_id"], **kwargs)

    def change_manifest(self, change):
        path = self.folder / "manifest.json"
        value = read_json(path)
        change(value)
        write_json(path, value)
        self.snapshot["manifest"] = binding(self.root, path)
        self.snapshot["assets"] = [binding(self.root, self.folder / b["path"]) for b in value["assets"]]

    def test_all_300_pngs_and_all_25_video_frames_decode_without_replaying_science(self):
        before = [binding(self.root, p) for p in self.folder.rglob("*") if p.is_file()]
        value, validation = self.validate()
        self.assertEqual(validation["pngs_decoded"], 300)
        self.assertEqual(validation["video"]["decoded_frames"], 25)
        self.assertEqual(validation["video"]["fps"], 5.0)
        self.assertEqual(validation["final_source_frame"], 24)
        self.assertEqual(value["header"]["renderer_code_commit"], recovery.RENDER_COMMIT)
        self.assertEqual(value["header"]["experiment_spec_sha256"], recovery.RENDER_SPEC)
        self.assertNotEqual(value["header"]["renderer_code_commit"], self.context["commit"])
        for arm in review.ARMS:
            self.assertEqual(self.prepared.observations[arm, "all"]["frames"][-1]["emitted_candidate_indices"], [])
            self.assertIsNone(self.prepared.reports[arm, "all"]["frame_results"][-1]["matched_candidate_index"])
            self.assertEqual(self.prepared.reports[arm, "all"]["frame_results"][-1]["false_negative_count"], 1)
        self.assertEqual(before, [binding(self.root, p) for p in self.folder.rglob("*") if p.is_file()])

    def test_missing_final_png_or_changed_intermediate_png_is_rejected(self):
        for relative, content in (("comparison/frame_000024.png", None), ("view_2/frame_000010.png", b"changed")):
            target = self.folder / relative
            before = target.read_bytes()
            try:
                if content is None:
                    target.unlink()
                else:
                    target.write_bytes(content)
                with self.subTest(relative=relative), self.assertRaises((ValueError, FileNotFoundError)):
                    self.validate()
            finally:
                target.write_bytes(before)

    def test_self_consistent_manifest_cannot_hide_an_undecodable_png(self):
        target = self.folder / "view_2/frame_000010.png"
        target.write_bytes(b"A fabricated file which is not an encoded PNG")
        def mutate(value):
            next(b for b in value["assets"] if b["path"] == "view_2/frame_000010.png")["sha256"] = sha256_file(target)
        self.change_manifest(mutate)
        with self.assertRaisesRegex(ValueError, "decode"):
            self.validate()

    def test_header_role_floor_radius_and_pair_order_cannot_be_reinterpreted(self):
        original_value = read_json(self.folder / "manifest.json")
        mutations = (lambda v: v["header"].update(renderer_code_commit=PUBLICATION_COMMIT),
                     lambda v: v["header"].update(confidence_threshold=.20),
                     lambda v: v["header"].update(radius_px=5),
                     lambda v: v["header"]["layout"]["motion_rows"].reverse())
        for change in mutations:
            write_json(self.folder / "manifest.json", original_value)
            self.change_manifest(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.validate()

    def test_final_frame_and_frame_order_must_remain_exact(self):
        original_value = read_json(self.folder / "manifest.json")
        for change in (lambda v: v.update(final_frame=23), lambda v: v["frame_evidence"].reverse()):
            write_json(self.folder / "manifest.json", original_value)
            self.change_manifest(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.validate()

    def test_independent_video_decode_rejects_short_wrong_fps_and_wrong_dimensions(self):
        class Capture:
            def __init__(self, count, fps, shape):
                self.count, self.fps, self.shape = count, fps, shape
            def isOpened(self):
                return True
            def get(self, prop):
                return self.fps
            def read(self):
                self.count -= 1
                return (True, np.zeros(self.shape, np.uint8)) if self.count >= 0 else (False, None)
            def release(self):
                pass
        for count, fps, shape in ((24, 5, (256, 288, 3)), (25, 6, (256, 288, 3)), (25, 5, (255, 288, 3))):
            with self.subTest(count=count, fps=fps, shape=shape), \
                    patch.object(cv2, "VideoCapture", return_value=Capture(count, fps, shape)), \
                    self.assertRaises(ValueError):
                self.validate()

    def test_finalization_validation_reads_immutable_bundle_without_new_decode(self):
        with patch.object(review, "_read_png", side_effect=AssertionError("Unexpected finalizer decode")), \
                patch.object(review, "_verify_video", side_effect=AssertionError("Unexpected finalizer decode")):
            _, validation = self.validate(decode=False)
        self.assertEqual(validation["pngs_decoded"], 0)
        self.assertIsNone(validation["video"])

    def test_closeup_arm_focus_and_raw_region_semantics_are_validated(self):
        original_value = read_json(self.folder / "manifest.json")
        changes = (lambda v: v["frame_evidence"][-1]["closeup_regions"].reverse(),
                   lambda v: v["frame_evidence"][-1]["closeup_regions"][0].update(focus_type="invented_truth"),
                   lambda v: v["frame_evidence"][-1]["closeup_regions"][0].update(raw_unmarked_view_included=False),
                   lambda v: v["frame_evidence"][-1]["closeup_regions"][0].update(requested_source_crop_xyxy_px=[0, 0, 1, 1]))
        for change in changes:
            write_json(self.folder / "manifest.json", original_value)
            self.change_manifest(change)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "closeup"):
                self.validate(decode=False)

    def test_missing_graph_output_keeps_null_errors_and_explicit_missing_state(self):
        key = review.ARMS[0], "all"
        obs = self.prepared.observations[key]["frames"][-1]
        report = self.prepared.reports[key]["frame_results"][-1]
        for row, field, altered in ((obs, "output_state", "tentative_observation"),
                                    (obs, "decision_reason", "current_endpoint"),
                                    (report, "matched_center_error_px", 0.0),
                                    (report, "matched_effective_center_error_px", 0.0),
                                    (report, "false_negative_count", 0)):
            before = row[field]
            row[field] = altered
            try:
                with self.subTest(field=field), self.assertRaises(ValueError):
                    self.validate(decode=False)
            finally:
                row[field] = before

    def test_self_consistent_declared_png_dimensions_cannot_change_display_geometry(self):
        def mutate(value):
            asset = next(b for b in value["assets"] if b["path"] == "view_2/frame_000010.png")
            asset["width_px"] -= 1
        self.change_manifest(mutate)
        with self.assertRaisesRegex(ValueError, "geometry"):
            self.validate(decode=False)


class PublicationCertificateTests(TemporaryRoot):
    def test_certificate_requires_all_sources_helpers_authorities_and_validation_flags(self):
        source = self.root / "src/module.py"
        source.parent.mkdir()
        source.write_text("# fabricated source\n", encoding="utf-8")
        requirements = self.root / "requirements.txt"
        requirements.write_text("# fabricated dependencies\n", encoding="utf-8")
        helpers = []
        for name in (*recovery.HELPERS.values(), "audit/independent_render_recovery_audit.py"):
            path = self.root / original.OUTPUT_ROOT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# fabricated helper\n", encoding="utf-8")
            helpers.append(binding(self.root, path))
        authorities = ("publication_proposal", "preservation_audit", "resource_checkpoint", "rendering_manifest", "authorization")
        manifest = {name: {"sha256": str(i) * 64} for i, name in enumerate(authorities)}
        certificate = {"focused_tests_passed": True, "full_suite_passed": True,
            "independent_static_review_passed": True, "publication_failure_boundary_tests_passed": True,
            "source_bindings": [binding(self.root, source), binding(self.root, requirements)],
            "helper_bindings": helpers, "evidence_bindings": [],
            **{name + "_sha256": manifest[name]["sha256"] for name in authorities}}
        path = self.root / "certificate.json"
        def publish(value):
            write_json(path, value)
            manifest["implementation_validation"] = binding(self.root, path)
        publish(certificate)
        with patch.object(original, "_git", return_value=""):
            recovery._validate_implementation(self.root, manifest)
            changes = [(name, False) for name in ("focused_tests_passed", "full_suite_passed",
                "independent_static_review_passed", "publication_failure_boundary_tests_passed")]
            changes += [("helper_bindings", helpers[:-1]), ("source_bindings", []),
                        ("publication_proposal_sha256", "f" * 64)]
            for field, value in changes:
                publish({**certificate, field: value})
                with self.subTest(field=field), self.assertRaises(ValueError):
                    recovery._validate_implementation(self.root, manifest)
            publish(certificate)
            source.write_text("# changed source\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                recovery._validate_implementation(self.root, manifest)


class PublicationAcceptanceTests(TemporaryRoot):
    def setUp(self):
        super().setUp()
        self.data = SyntheticPublicationRecovery(self.root)
        self.scope = self.data.patch_scope()
        self.addCleanup(self.scope.close)
        self.validation = {"pngs_decoded": 300, "video": {"decoded_frames": 25, "fps": 5.0,
                           "dimensions_px": [review.TILE_WIDTH * 3, review.TILE_HEIGHT * 4],
                           "first_source_frame": 0, "last_source_frame": 24},
                           "final_source_frame": 24}

    def publish_acceptance(self):
        with patch.object(recovery, "validate_bundle", return_value=({}, self.validation)):
            return recovery.accept_publication(self.root, self.data.context)

    def receipt_acceptance(self):
        path = self.data.output / recovery.OUTPUTS["accept"]
        return self.data.add_publication_attempt("accept", artifacts=[binding(self.root, path)])

    def test_acceptance_keeps_render_failure_and_separate_validation_provenance(self):
        d = self.data
        frozen_failure = copy.deepcopy(d.journal._attempts()[recovery.FAILED_RENDER])
        value = self.publish_acceptance()
        self.assertEqual(value["original_renderer_commit"], recovery.RENDER_COMMIT)
        self.assertEqual(value["original_renderer_spec_sha256"], recovery.RENDER_SPEC)
        self.assertEqual(value["validation_commit"], PUBLICATION_COMMIT)
        self.assertEqual(value["validation_spec_sha256"], PUBLICATION_SPEC)
        self.assertEqual(value["original_failed_render_attempt_id"], recovery.FAILED_RENDER)
        self.assertEqual(value["human_visual_review"], "pending")
        self.assertEqual(frozen_failure, d.journal._attempts()[recovery.FAILED_RENDER])
        self.assertIsNone(frozen_failure["finished"]["worker_result"])
        self.assertFalse((d.output / "attempts" / (recovery.FAILED_RENDER + ".result.json")).exists())
        with self.assertRaisesRegex(ValueError, "successful acceptance"):
            recovery._acceptance(self.root, d.context, recovery.completed_records(self.root, d.context))
        self.receipt_acceptance()
        records = recovery.completed_records(self.root, d.context)
        self.assertEqual(recovery._acceptance(self.root, d.context, records), value)
        path = d.output / recovery.OUTPUTS["accept"]
        before = path.read_bytes()
        altered = copy.deepcopy(value)
        altered["validation"]["final_source_frame"] = 23
        altered["content_sha256"] = canonical_sha256({k: v for k, v in altered.items() if k != "content_sha256"})
        write_json(path, altered)
        try:
            with self.assertRaisesRegex(ValueError, "validated content"):
                recovery._acceptance(self.root, d.context, records)
        finally:
            path.write_bytes(before)
        self.receipt_acceptance()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            recovery.completed_records(self.root, d.context)

    def test_published_acceptance_without_success_cannot_finalize_or_be_overwritten(self):
        d = self.data
        self.publish_acceptance()
        acceptance = d.output / recovery.OUTPUTS["accept"]
        before = acceptance.read_bytes()
        with self.assertRaisesRegex(ValueError, "successful acceptance"):
            recovery.finalize_review(self.root, d.context)
        self.assertFalse((d.output / recovery.OUTPUTS["review-final"]).exists())
        with self.assertRaisesRegex(ValueError, "Create-only"):
            self.publish_acceptance()
        self.assertEqual(acceptance.read_bytes(), before)
        d.add_publication_attempt("accept", success=False)
        with self.assertRaisesRegex(ValueError, "failure"):
            recovery.completed_records(self.root, d.context)

    def test_finalization_binds_five_original_successes_and_the_new_sixth_acceptance(self):
        d = self.data
        before = [binding(self.root, self.root / r["manifest"]["path"]) for r in d.window_records]
        self.publish_acceptance()
        record = self.receipt_acceptance()
        with patch.object(recovery, "validate_bundle", return_value=({}, {})) as validate:
            result = recovery.finalize_review(self.root, d.context)
        self.assertEqual([call.args[2] for call in validate.call_args_list], ["w" + str(i) for i in range(6)])
        self.assertTrue(all(call.kwargs == {"decode": False} for call in validate.call_args_list))
        self.assertEqual(result["schema_version"], "ball_crop_candidate_retention_review/v0.2")
        self.assertEqual(result["original_renderer_commit"], recovery.RENDER_COMMIT)
        self.assertEqual(result["code_commit"], PUBLICATION_COMMIT)
        self.assertEqual(result["acceptance_worker_result"], record["worker_result"])
        self.assertEqual(result["previous_motion_and_yolo_review"], "complete_no_repeat")
        self.assertEqual(result["human_visual_review"], "pending_six_new_floor_clips_only")
        self.assertTrue(all(result[k] is None for k in ("selected_method", "selected_operating_point", "quality_gate")))
        self.assertEqual(before, [binding(self.root, self.root / r["manifest"]["path"]) for r in d.window_records])
        with self.assertRaisesRegex(ValueError, "Create-only"):
            recovery.finalize_review(self.root, d.context)

    def test_out_of_order_success_receipt_is_rejected(self):
        d = self.data
        target = d.output / recovery.OUTPUTS["review-final"]
        write_json(target, {"synthetic": "finalization without prior acceptance"})
        d.add_publication_attempt("review-final", artifacts=[binding(self.root, target)])
        with self.assertRaisesRegex(ValueError, "prerequisite|out-of-order"):
            recovery.completed_records(self.root, d.context)

    def test_receipt_only_helper_cannot_bless_scientific_output(self):
        d = self.data
        self.publish_acceptance()
        self.receipt_acceptance()
        final = d.output / recovery.OUTPUTS["review-final"]
        write_json(final, {"synthetic": "receipt-only order fixture"})
        d.add_publication_attempt("review-final", artifacts=[binding(self.root, final)])
        d.add_publication_attempt("completion-audit", artifacts=[d.score_bindings[0]])
        with self.assertRaisesRegex(ValueError, "unapproved artifacts"):
            recovery.completed_records(self.root, d.context)

    def test_worker_rejects_mismatched_active_stage_before_any_acceptance(self):
        d = self.data
        attempt, _ = d.journal.reserve("publication-recovery:preflight:recover", False)
        d.context["_journal"] = d.journal
        with patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": attempt}), \
                patch.object(recovery, "wait_for_supervisor"), \
                patch.object(recovery, "load_context", return_value=d.context), \
                patch.object(recovery, "accept_publication", side_effect=AssertionError("Mismatched worker published")):
            with self.assertRaisesRegex(ValueError, "reservation"):
                recovery._worker(self.root, self.root / "manifest.json", "accept", "")

    def test_changed_old_input_after_publication_prevents_success_receipt(self):
        d = self.data
        attempt, _ = d.journal.reserve("publication-recovery:accept:", False)
        d.context["_journal"] = d.journal
        result_path = d.output / "attempts" / (attempt + ".result.json")
        original_selection = self.root / d.selections[0]["manifest"]["path"]
        def validate(*args, **kwargs):
            original_selection.write_bytes(original_selection.read_bytes() + b"changed during validation")
            return {}, self.validation
        with patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": attempt, "BALL_RETENTION_RESULT_PATH": str(result_path)}), \
                patch.object(recovery, "wait_for_supervisor"), \
                patch.object(recovery, "load_context", return_value=d.context), \
                patch.object(recovery, "validate_bundle", side_effect=validate):
            with self.assertRaises(ValueError):
                recovery._worker(self.root, self.root / "manifest.json", "accept", "")
        self.assertTrue((d.output / recovery.OUTPUTS["accept"]).exists())
        self.assertFalse(result_path.exists())
        d.finish_attempt(attempt, "accept", [], success=False, commit=PUBLICATION_COMMIT, spec=PUBLICATION_SPEC)
        with self.assertRaisesRegex(ValueError, "failure"):
            recovery.verify_history(self.root, d.context)

    def test_all_preserved_scientific_roles_are_rechecked_without_parsing_them(self):
        d = self.data
        targets = [d.selections[0]["manifest"], d.selections[0]["traces"][0], d.score_bindings[0],
                   d.score_bindings[-1], d.failure["partial"], d.failure["log"],
                   d.interruption["partial_review_files"][0], d.interruption["failed_render_log"],
                   d.proposal["windows"][0]["crop_candidates"]]
        with patch.object(recovery, "read_json", side_effect=AssertionError("Preservation hashes parsed science")):
            recovery._verify_preserved_inputs(self.root, d.context)
            for item in targets:
                path = self.root / item["path"]
                before = path.read_bytes()
                path.write_bytes(before + b"changed")
                try:
                    with self.subTest(path=item["path"]), self.assertRaises(ValueError):
                        recovery._verify_preserved_inputs(self.root, d.context)
                finally:
                    path.write_bytes(before)

    def test_exact_sixth_snapshot_is_the_only_eligible_acceptance_target(self):
        d = self.data
        snapshot = d.preservation["review_windows"][-1]
        for field, changed in (("window_id", "w4"), ("failed_render_attempt_id", "f" * 32),
                               ("historical_success_binding_verified", True)):
            before = snapshot[field]
            snapshot[field] = changed
            try:
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, "Wrong acceptance target"):
                    self.publish_acceptance()
                self.assertFalse((d.output / recovery.OUTPUTS["accept"]).exists())
            finally:
                snapshot[field] = before


if __name__ == "__main__":
    unittest.main()
