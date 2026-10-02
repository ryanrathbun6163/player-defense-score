"""Synthetic recovery scoring: exact saved controls and mixed inference origins."""
import copy
import tempfile
import unittest
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import numpy as np

from src.ball_tracking import yolo_crop_candidates as selectors
from src.ball_tracking import yolo_crop_evaluation as original_evaluation
from src.ball_tracking import yolo_crop_experiment as original_experiment
from src.ball_tracking import yolo_crop_recovery as recovery
from src.ball_tracking import yolo_crop_recovery_evaluation as evaluation
from src.ball_tracking.development_experiments import canonical_sha256, read_json, sha256_file
from src.ball_tracking.temporal_association import RADII, THRESHOLDS
from src.ball_tracking.temporal_experiment import file_binding
from test_ball_detection_visual_review import write_json
import test_ball_yolo_crop_evaluation as original_fixture

COMMIT = "f" * 40
PURPOSES = original_fixture.PURPOSES


class SavedSyntheticAdapter:
    """Return fabricated fixture predictions with an auditable attempt counter."""
    def __init__(self, predictions, *, fail_at=None):
        self.predictions, self.fail_at, self.calls = predictions, fail_at, 0
        self.cuda_peak_allocated_bytes = 128
        self._accounting = {"synthetic_forwards": 0, "project_attempts": 0,
                            "project_forwards": 0, "preparation_complete": False}

    @property
    def accounting(self):
        return dict(self._accounting)

    def prepare(self):
        self._accounting.update(synthetic_forwards=2, preparation_complete=True)

    def predict_frame(self, pixels):
        assert pixels.shape == (648, 1152, 3) and pixels.dtype == np.uint8
        self.calls += 1
        self._accounting.update(project_attempts=self.calls, project_forwards=self.calls)
        if self.calls == self.fail_at:
            raise RuntimeError("synthetic interrupted crop")
        value = copy.deepcopy(self.predictions[self.calls-1])
        value["forward_accounting"] = {**self.accounting, "this_project_attempt_forwards": 1}
        return value


def scoring_fixture(root):
    """Build genuine recovery receipts from synthetic data only, before poisoning stages."""
    from test_ball_yolo_crop_recovery import bind_partial
    with patch.object(original_fixture, "COMMIT", recovery.ORIGINAL_COMMIT):
        old_path, old_m, p, old_model = original_fixture.synthetic_setup(root)
    p.update(crop_views=recovery.crop_views(), sealed_holdouts=original_experiment.SEALED)
    (root/"docs").mkdir(exist_ok=True)
    predictions = []
    for w in p["windows"]:
        value = read_json(original_experiment.candidate_path(root, w))
        predictions.extend(view["prediction"] for frame in value["frames"] for view in frame["views"])
        # These temporary fixture files have no receipts yet. The injected old
        # runner below creates the authentic partial run and its immutable ledger.
        original_experiment.candidate_path(root, w).unlink()
        for config in selectors.experiment_grid():
            original_experiment.output_path(root, w, config).unlink()
    for source in p["inference_source_frames"]:
        target = root / source["source_png"]["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f"synthetic-source-{source['window_id']}-{source['frame_index']}".encode())
        source["source_png"] = file_binding(root, target)
    inputs = [{"window": w, "model": old_model, "weights_path": root/"synthetic.pt",
               "runtime_record": {"synthetic_only": True},
               "source_frames": [s for s in p["inference_source_frames"] if s["window_id"] == w["window_id"]]}
              for w in p["windows"]]
    pixels = np.zeros((1080, 1920, 3), np.uint8)
    with patch.object(original_experiment, "preflight", return_value=(old_m, p, inputs, recovery.ORIGINAL_COMMIT)), \
            patch.object(original_experiment, "unchanged"):
        for sequence, fail_at in ((predictions, 176), (predictions[175:], 1)):
            adapter = SavedSyntheticAdapter(sequence, fail_at=fail_at)
            try:
                original_experiment.run_experiment(root, old_path, adapter_factory=lambda *_: adapter,
                                                   png_reader=lambda *_: pixels)
            except RuntimeError as error:
                if str(error) != "synthetic interrupted crop":
                    raise
            else:
                raise AssertionError("Expected synthetic interruption")
    path, manifest, proposal, recovered_inputs = bind_partial(root, old_path, old_m, p, inputs, commit=COMMIT)
    original_bytes = {binding["path"]: (root/binding["path"]).read_bytes()
                      for binding in recovery.preserved_bindings(recovered_inputs[0]["recovery"])}
    adapter = SavedSyntheticAdapter(predictions[175:])
    with patch.object(recovery, "preflight", return_value=(manifest, proposal, recovered_inputs, COMMIT)), \
            patch.object(recovery, "unchanged"):
        inference = recovery.run_experiment(root, path, adapter_factory=lambda *_: adapter, png_reader=lambda *_: pixels)
    if adapter.calls != 425:
        raise AssertionError("Synthetic recovery must execute exactly the missing 425 units")
    return path, manifest, proposal, recovered_inputs, original_bytes, inference


class RecoveryScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.path, cls.m, cls.p, cls.inputs, cls.original_bytes, cls.inference = scoring_fixture(cls.root)
        cls.stack = ExitStack()
        cls.addClassCleanup(cls.stack.close)
        cls.stack.enter_context(patch.object(recovery, "preflight", return_value=(cls.m, cls.p, cls.inputs, COMMIT)))
        cls.stack.enter_context(patch.object(recovery, "unchanged"))
        original_fixture.forbid_legacy(cls.stack)
        cls.stack.enter_context(patch.object(recovery, "observations", side_effect=AssertionError("reselected during scoring")))
        cls.saved_bytes = {b["path"]: (cls.root/b["path"]).read_bytes()
                           for b in [*cls.p["saved_control_outputs"], *cls.p["saved_control_scoring_reports"]]}
        evidence_snapshots = []
        load_evidence = evaluation._load_evidence

        def capture_evidence(*args):
            value = load_evidence(*args)
            evidence_snapshots.append(value)
            return value

        with patch.object(evaluation, "_load_evidence", side_effect=capture_evidence), \
                patch.object(original_evaluation, "evaluate_detections", wraps=original_evaluation.evaluate_detections) as scorer:
            cls.summary = evaluation.score_experiment(cls.root, cls.path)
            cls.score_calls = scorer.call_count
        cls.pools = {purpose: read_json(evaluation._pool_path(cls.root, purpose)) for purpose in PURPOSES}
        cls.saved = {purpose: {"evaluation_reports": pool["evaluation_reports"][:405],
                               "aggregate_results": pool["aggregate_results"][:135]}
                     for purpose, pool in cls.pools.items()}
        cls.evidence = evidence_snapshots[-1]

    def test_exact_new_and_reused_counts_complete_grid_and_final_frames(self):
        self.assertEqual(self.score_calls, 810)
        self.assertEqual(self.summary["per_window_reports"], 1620)
        self.assertEqual(self.summary["new_per_window_reports"], 810)
        self.assertEqual(self.summary["reused_per_window_reports"], 810)
        self.assertEqual(self.summary["aggregate_cells_per_pool"], 270)
        self.assertEqual(self.summary["saved_controls_rescored"], 0)
        self.assertEqual(self.summary["saved_controls_reranked"], 0)
        for purpose, pool in self.pools.items():
            self.assertEqual(len(pool["evaluation_reports"]), 810)
            self.assertEqual(len(pool["aggregate_results"]), 270)
            self.assertEqual(len(pool["paired_differences"]), 405)
            self.assertEqual(len(pool["loss_decomposition"]), 810)
            self.assertEqual(len(pool["aggregate_paired_differences"]), 135)
            self.assertEqual({r["config"]["confidence_threshold"] for r in pool["evaluation_reports"]}, set(THRESHOLDS))
            self.assertEqual({r["localization_radius_px"] for r in pool["evaluation_reports"]}, set(RADII))
            for report in pool["evaluation_reports"]:
                self.assertEqual(len(report["frame_results"]), 25)
                self.assertEqual(report["frame_results"][-1]["frame_index"], report["window"]["end_frame_index"])
                self.assertEqual(report["selection_purpose"], purpose)

    def test_175_old_425_new_actual_origins_survive_reports_and_aggregates(self):
        units = [u for evidence in self.evidence.values() for u in evidence[3]["header"]["inference_units"]]
        self.assertEqual(Counter(u["actual_inference_commit"] for u in units), {recovery.ORIGINAL_COMMIT: 175, COMMIT: 425})
        self.assertEqual(len({(u["window_id"], u["frame_index"], u["view_id"]) for u in units}), 600)
        for pool in self.pools.values():
            self.assertEqual(pool["assembly_code_commit"], COMMIT)
            self.assertEqual(pool["evaluation_code_commit"], COMMIT)
            self.assertEqual(pool["model_code_commit_role"], evaluation.MODEL_COMMIT_ROLE)
            for report in pool["evaluation_reports"][405:]:
                window = next(w for w in self.p["windows"] if w["possession_id"] == report["possession_id"] and w["purpose"] == pool["purpose"])
                observations = self.evidence[window["window_id"]][2][report["variant_id"]]
                self.assertEqual(evaluation.provenance_binding(report), evaluation.provenance_binding(observations))
                self.assertNotIn("detector_code_commit", report)
                self.assertEqual(report["ranking_code_commit"], COMMIT)
                self.assertEqual(report["evaluator_code_commit"], COMMIT)
            for aggregate in pool["aggregate_results"][135:]:
                self.assertEqual(len(aggregate["inference_inventory_bindings"]), 3)
                self.assertEqual(aggregate["assembly_code_commit"], COMMIT)
        second = self.evidence[self.p["windows"][1]["window_id"]][3]["header"]
        self.assertEqual(Counter(u["actual_inference_commit"] for u in second["inference_units"]),
                         {recovery.ORIGINAL_COMMIT: 75, COMMIT: 25})

    def test_all_original_bytes_and_rf_reports_are_preserved(self):
        for path, content in {**self.original_bytes, **self.saved_bytes}.items():
            self.assertEqual((self.root/path).read_bytes(), content)
        for purpose, pool in self.pools.items():
            self.assertEqual(pool["evaluation_reports"][:405], self.saved[purpose]["evaluation_reports"])
            self.assertEqual(pool["aggregate_results"][:135], self.saved[purpose]["aggregate_results"])
            self.assertEqual({r["evaluator_code_commit"] for r in pool["evaluation_reports"][:405]},
                             {original_experiment.PRIOR_COMMIT})

    def test_first_window_semantics_match_original_despite_new_assembly(self):
        window = self.p["windows"][0]
        old_payload = read_json(original_experiment.candidate_path(self.root, window))
        labels, run, observations, new_payload = self.evidence[window["window_id"]]
        self.assertEqual(old_payload["frames"], new_payload["frames"])
        old_run = selectors.candidate_run(old_payload)
        for config in selectors.experiment_grid():
            old_obs = read_json(original_experiment.output_path(self.root, window, config))["observations"]
            self.assertEqual(old_obs["frames"], observations[config.variant_id]["frames"])
        # Independent generic metric computation on the preserved first-window
        # observations is synthetic fixture evidence, not a production old rerun.
        old_obs = read_json(original_experiment.output_path(self.root, window, selectors.experiment_grid()[0]))["observations"]
        report = original_evaluation._evaluate_validated(labels, old_run, old_obs, 10, recovery.ORIGINAL_COMMIT)
        new_report = next(r for r in self.pools[window["purpose"]]["evaluation_reports"][405:]
                          if r["variant_id"] == old_obs["variant_id"] and r["possession_id"] == window["possession_id"] and r["localization_radius_px"] == 10)
        for key in ("metrics", "frame_results", "temporal_metrics"):
            self.assertEqual(report[key], new_report[key])
        self.assertEqual(old_run.model_provenance.code_commit, recovery.ORIGINAL_COMMIT)
        self.assertEqual(run.model_provenance.code_commit, COMMIT)

    def test_resume_and_saved_review_load_never_score_or_select(self):
        before = [sha256_file(self.root/b["path"]) for b in self.summary["reports"]]
        with patch.object(original_evaluation, "evaluate_detections", side_effect=AssertionError("scored on resume")):
            self.assertEqual(evaluation.score_experiment(self.root, self.path), self.summary)
            self.assertEqual(evaluation.load_scoring_pools(self.root, self.m, self.p, COMMIT, inputs=self.inputs), self.pools)
        self.assertEqual(before, [sha256_file(self.root/b["path"]) for b in self.summary["reports"]])

    def test_partial_resume_scores_only_missing_pool(self):
        target = evaluation._pool_path(self.root, PURPOSES[1])
        before = target.read_bytes()
        target.unlink()
        try:
            with patch.object(original_evaluation, "evaluate_detections", wraps=original_evaluation.evaluate_detections) as scorer:
                self.assertEqual(evaluation.score_experiment(self.root, self.path), self.summary)
            self.assertEqual(scorer.call_count, 405)
            self.assertEqual(target.read_bytes(), before)
        finally:
            target.write_bytes(before)

    def test_rebound_score_aggregate_and_pool_provenance_tampering_rejected(self):
        # Check persisted-content validation independently of expensive source
        # loading; self.evidence was verified by the genuine recovery loaders.
        mutations = [
            lambda v: v["evaluation_reports"][405].update(inference_inventory_sha256="0"*64),
            lambda v: v["evaluation_reports"][405].update(actual_inference_commits=[COMMIT]),
            lambda v: v["evaluation_reports"][405].update(assembly_code_commit=recovery.ORIGINAL_COMMIT),
            lambda v: v["evaluation_reports"][405].update(model_code_commit_role="actual_inference"),
            lambda v: v["evaluation_reports"][405].update(detector_code_commit=COMMIT),
            lambda v: v["evaluation_reports"][405]["input_candidate_file"].update(sha256="0"*64),
            lambda v: v["aggregate_results"][135].update(actual_inference_commits=[COMMIT]),
            lambda v: v["aggregate_results"][135]["inference_inventory_bindings"][0].update(inference_inventory_sha256="0"*64),
            lambda v: v["aggregate_results"][135].update(model_code_commit_role="actual_inference"),
            lambda v: v.update(actual_inference_commits=[COMMIT]),
            lambda v: v.update(model_code_commit_role="actual_inference"),
            lambda v: v["inference_inventory_bindings"][0].update(inference_inventory_sha256="0"*64),
        ]
        for mutate in mutations:
            value = copy.deepcopy(self.pools[PURPOSES[0]])
            mutate(value)
            value["content_sha256"] = original_evaluation._pool_digest(value)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                evaluation._validate_pool(value, self.m, self.p, PURPOSES[0], COMMIT, self.saved[PURPOSES[0]], self.evidence)

    def test_changed_original_control_blocks_missing_pool_before_scoring(self):
        control = self.root/self.p["saved_control_outputs"][0]["path"]
        second = evaluation._pool_path(self.root, PURPOSES[1])
        control_bytes, pool_bytes = control.read_bytes(), second.read_bytes()
        control.write_bytes(control_bytes + b" ")
        second.unlink()
        try:
            with patch.object(original_evaluation, "evaluate_detections", side_effect=AssertionError("scored before control validation")):
                with self.assertRaises(ValueError):
                    evaluation.score_experiment(self.root, self.path)
            self.assertFalse(second.exists())
        finally:
            control.write_bytes(control_bytes)
            second.write_bytes(pool_bytes)

    def test_rebound_existing_pool_blocks_missing_pool_before_scoring(self):
        first, second = [evaluation._pool_path(self.root, p) for p in PURPOSES]
        first_bytes, second_bytes = first.read_bytes(), second.read_bytes()
        value = read_json(first)
        value["evaluation_reports"][405]["inference_inventory_sha256"] = "0"*64
        value["content_sha256"] = original_evaluation._pool_digest(value)
        write_json(first, value)
        second.unlink()
        try:
            with patch.object(original_evaluation, "evaluate_detections", side_effect=AssertionError("scored before saved pool validation")):
                with self.assertRaises(ValueError):
                    evaluation.score_experiment(self.root, self.path)
            self.assertFalse(second.exists())
        finally:
            first.write_bytes(first_bytes)
            second.write_bytes(second_bytes)

    def test_rebound_candidate_origin_and_selector_role_rejected_by_saved_loaders(self):
        window, item = self.p["windows"][1], self.inputs[1]
        labels, run, observations, payload = self.evidence[window["window_id"]]
        target = recovery.candidate_path(self.root, window)
        before = target.read_bytes()
        changed = copy.deepcopy(payload)
        changed["header"]["inference_units"][0]["actual_inference_commit"] = COMMIT
        changed["header"]["inference_inventory_sha256"] = canonical_sha256(changed["header"]["inference_units"])
        changed["content_sha256"] = canonical_sha256({k: changed[k] for k in ("header", "frames")})
        write_json(target, changed)
        try:
            with self.assertRaises(ValueError):
                recovery.load_candidate_run(self.root, self.m, self.p, window, COMMIT, model=item["model"])
        finally:
            target.write_bytes(before)
        config = selectors.experiment_grid()[0]
        target = recovery.output_path(self.root, window, config)
        before = target.read_bytes()
        changed = read_json(target)
        changed["observations"]["model_code_commit_role"] = "actual_inference_for_all_units"
        changed["observations_content_sha256"] = canonical_sha256(changed["observations"])
        write_json(target, changed)
        try:
            with self.assertRaises(ValueError):
                recovery.load_observations(self.root, self.m, self.p, window, run, payload["content_sha256"],
                                           config, COMMIT, rederive=False)
        finally:
            target.write_bytes(before)

    def test_actual_review_preparation_joins_all_frames_and_mixed_origins(self):
        import cv2
        from src.ball_tracking import yolo_crop_recovery_review as review
        with patch.object(review.original, "load_reused_assets", return_value=[]), \
                patch.object(original_evaluation, "evaluate_detections", side_effect=AssertionError("review scored")), \
                patch.object(evaluation, "score_experiment", side_effect=AssertionError("review scored")), \
                patch.object(cv2, "VideoCapture", side_effect=AssertionError("review decoded video")):
            prepared = review._prepare_review(self.root, self.path)
        self.assertEqual(len(prepared.windows), 6)
        self.assertEqual(prepared.header["actual_inference_commit_counts"], {recovery.ORIGINAL_COMMIT: 175, COMMIT: 425})
        self.assertEqual(prepared.header["confidence_views"], [.2, .35])
        for row in prepared.windows:
            self.assertEqual(len(row["run"].frames), 25)
            self.assertEqual(len(row["reports"]), 12)
            for key, report in row["reports"].items():
                self.assertEqual(report["observations_content_sha256"], canonical_sha256(row["observations"][key]))
                self.assertEqual(report["frame_results"][-1]["frame_index"], row["window"]["end_frame_index"])
        mixed = prepared.windows[1]["inference_provenance"]["inference_units"]
        frame_218 = [u for u in mixed if u["frame_index"] == 218]
        self.assertEqual([u["actual_inference_commit"] for u in frame_218], [recovery.ORIGINAL_COMMIT]*3+[COMMIT])


if __name__ == "__main__":
    unittest.main()
