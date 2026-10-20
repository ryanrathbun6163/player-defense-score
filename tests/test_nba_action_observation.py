"""Native action observations consume actual synthetic diagnostic producer caches.

No existing development cache, source recording or actual model is read. The
earlier producer runs on its accepted-reference fixture and fake adapter before
the action consumer imports those emitted records.
"""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import numpy as np
from PIL import Image

from src.ball_tracking import nba_action_observation as action
from src.ball_tracking import nba_wasb_diagnostic as d
from src.ball_tracking.nba_reviewed_reference import publish_reference
from src.ball_tracking.wasb_experiment import merge_heatmaps
from tests import test_nba_wasb_diagnostic as producer_fixture

FakeAdapter = producer_fixture.FakeAdapter


APPROVED_WINDOW_FIELDS = {
    "candidate_id", "game_id", "approved_role", "source_frame_range_inclusive",
    "source_pts_ticks_inclusive", "source_end_exclusive_pts_ticks", "time_base",
    "frames", "timeline_duration_seconds", "maximum_complete_triplets",
    "planned_prior_triplet_imports", "maximum_new_model_calls",
}


class StreamingAndSelectionTests(unittest.TestCase):
    def test_streamed_float32_means_match_producer_bit_for_bit_at_all_endpoints(self):
        rng = np.random.default_rng(473)
        for length in (3, 5):
            frames = [{"source_frame_index": i} for i in range(100, 100 + length)]
            triplets = {i: rng.random((3, 288, 512), dtype=np.float32)
                        for i in range(100, 100 + length - 2)}
            expected, counts = merge_heatmaps(triplets, 100, 99 + length)
            seen = []
            def provide(rows):
                first = rows[0]["source_frame_index"]
                seen.append(first)
                return triplets[first]
            actual = list(action.stream_means(frames, provide))
            with self.subTest(length=length):
                self.assertEqual(seen, sorted(triplets))
                self.assertEqual([row[2] for row in actual], counts)
                self.assertEqual([row[0] for row in actual], frames)
                for (_, mean, _), target in zip(actual, expected):
                    self.assertEqual(mean.dtype, np.float32)
                    self.assertEqual(mean.tobytes(), target.tobytes())

    def test_short_segments_withhold_without_calling_provider(self):
        for length in (1, 2):
            frames = [{"source_frame_index": i} for i in range(length)]
            provider = Mock(side_effect=AssertionError("Incomplete triplet inferred"))
            self.assertEqual(list(action.stream_means(frames, provider)),
                             [(frame, None, 0) for frame in frames])
            provider.assert_not_called()

    def test_strict_threshold_and_stable_component_mass_tie(self):
        manifest = {"source_video": {"width_px": 512, "height_px": 288}, "time_base": "1/90000"}
        frame = {"source_frame_index": 10, "source_pts_ticks": 90000,
                 "png": {"path": "synthetic.png", "sha256": "0" * 64}}
        segment = {"kind": "live_action"}
        mean = np.zeros((288, 512), np.float32)
        mean[50, 50] = np.float32(.3)
        at_threshold = action.select_observation(frame, mean, 1, manifest, segment)
        self.assertEqual(at_threshold["state"], "missing")
        self.assertEqual(at_threshold["candidates"], [])
        mean[70, 70] = np.nextafter(np.float32(.3), np.float32(1))
        above_threshold = action.select_observation(frame, mean, 1, manifest, segment)
        self.assertEqual(len(above_threshold["candidates"]), 1)
        mean.fill(0)
        mean[80, 80] = .75
        mean[180, 180] = .75
        tied = action.select_observation(frame, mean, 1, manifest, segment)
        self.assertEqual(len(tied["candidates"]), 2)
        self.assertEqual(tied["candidates"][0]["native_score"], tied["candidates"][1]["native_score"])
        self.assertEqual(tied["selected_candidate_index"], 0)
        self.assertEqual(tied["center_xy_px"], [80.0, 80.0])

    def test_equal_state_same_kind_segments_keep_distinct_native_time_intervals(self):
        manifest = {"source_video": {"width_px": 512, "height_px": 288},
                    "time_base": "1/90000", "source_end_exclusive_pts_ticks": 95940}
        segments = [{"kind": "live_action", "source_frame_range_inclusive": [10, 11]},
                    {"kind": "live_action", "source_frame_range_inclusive": [12, 13]}]
        frames = [{"source_frame_index": i, "source_pts_ticks": pts,
                   "png": {"path": f"synthetic_{i}.png", "sha256": "0" * 64}}
                  for i, pts in zip(range(10, 14), (90000, 91440, 92970, 94410))]
        observations = [action.select_observation(frame, None, 0, manifest, segments[offset // 2])
                        for offset, frame in enumerate(frames)]
        summary = action.summarize(manifest, {"frames": observations, "triplet_caches": []})
        intervals = summary["state_intervals"]
        self.assertEqual(len(intervals), 2)
        self.assertEqual([row["state"] for row in intervals], ["withheld", "withheld"])
        self.assertEqual([row["segment_kind"] for row in intervals], ["live_action", "live_action"])
        self.assertEqual([row["segment_source_frame_range_inclusive"] for row in intervals], [[10, 11], [12, 13]])
        self.assertEqual([row["frames"] for row in intervals], [2, 2])
        self.assertEqual([row["first_source_pts_ticks"] for row in intervals], [90000, 92970])
        self.assertEqual([row["end_exclusive_pts_ticks"] for row in intervals], [92970, 95940])
        self.assertEqual([row["duration_seconds"] for row in intervals], [.033, .033])


class ActionObservationTests(unittest.TestCase):
    def setUp(self):
        # Reuse the actual earlier test producer setup without inheriting its
        # tests or rerunning the earlier diagnostic suite.
        producer_fixture.NBADiagnosticTests.setUp(self)
        self.old_output = self.output
        self.old_result, self.old_adapter = producer_fixture.NBADiagnosticTests.run_fake(self, render=False)
        self.assertEqual(len(self.old_adapter.calls), 1)
        self.old_observations = d.read_json(self.old_output / self.reference["candidate_id"] / "observations.json")
        self.published = self.root / "data/outputs/published.json"
        publish_reference(self.acceptance, self.published, self.root)
        self.action_output = self.root / "data/outputs/action"
        self.manifest = self.make_manifest()
        self.window = {
            **{k: self.manifest[k] for k in ("candidate_id", "game_id", "approved_role", "time_base")},
            "source_frame_range_inclusive": [658, 664],
            "source_pts_ticks_inclusive": [993392, 1002302],
            "source_end_exclusive_pts_ticks": 1003742,
            "frames": 7, "timeline_duration_seconds": 10350 / 90000,
            "maximum_complete_triplets": 5, "planned_prior_triplet_imports": 1,
            "maximum_new_model_calls": 4,
            "source_video": self.reference["source_video"],
            "unapproved_metadata_field": "Proposal-only supporting metadata, deliberately absent from approval projection",
        }
        self.proposal_path, self.action_approval_path = self.make_scope()
        self.context = action.load_context(self.root, self.proposal_path, self.action_approval_path)
        self.manifest_path = self.action_output / "inputs" / self.reference["candidate_id"] / "manifest.json"
        d.write_once(self.manifest_path, self.manifest)
        self.segments = [{"source_frame_range_inclusive": [658, 664], "kind": "live_action"}]
        self.scene_path = self.root / "scene.json"
        self.save_scene(self.segments)
        self.context["scene_binding"] = d.binding(self.root, self.scene_path)

    def make_manifest(self):
        rows = {r["source_frame_index"]: copy.deepcopy(r) for r in self.reference["frames"]}
        # New synthetic RGB PNGs follow the native PNG producer's emitted record
        # fields. The existing pilot rows are reused verbatim from that producer.
        for index, pts, red in ((658, 993392, 150), (659, 994832, 170),
                                (663, 1000772, 190), (664, 1002302, 210)):
            image = Image.new("RGB", (8, 6), (red, 30, 60))
            path = self.root / f"action_{index:06d}.png"
            image.save(path)
            rows[index] = {"source_frame_index": index, "source_pts_ticks": pts,
                           "png": {"path": path.name, "sha256": d.digest(path),
                                   "rgb_sha256": hashlib.sha256(image.tobytes()).hexdigest()}}
        return {**{k: self.reference[k] for k in
                   ("candidate_id", "game_id", "approved_role", "source_video", "time_base")},
                "frames": [rows[i] for i in sorted(rows)], "source_end_exclusive_pts_ticks": 1003742}

    def make_scope(self):
        accepted = self.root / "model_accepted.json"
        d.write_once(accepted, {"status": "accepted", "fixture_only": True})
        prior_result = self.root / "pilot_result.json"
        d.write_once(prior_result, {
            "evidence": [d.binding(self.root, p) for p in (
                self.old_output / "run_identity.json",
                self.old_output / self.reference["candidate_id"] / "observations.json")],
            "reference": d.binding(self.root, self.published),
        })
        recipe = {
            "checkpoint_sha256": d.EXPANDED_SHA,
            "prior_diagnostic_config": d.binding(self.root, self.config_path),
            "native_input_spacing_ms": [16, 17], "strict_heatmap_threshold": .3,
            "selection": "largest_component_mass_then_stable_candidate_index",
            "aggregation": "mean_aligned_complete_triplets", "triplet_stride": 1, "dtype": "float32",
            **{key: False for key in ("training", "threshold_search", "motion_selector", "interpolation",
                                      "padding", "resampling", "external_model_context")},
        }
        self.action_proposal = {
            "proposal_id": "synthetic_action", "windows": [self.window],
            "totals": {"frames": 7, "maximum_complete_triplets": 5,
                       "planned_prior_triplet_imports": 1, "maximum_new_model_calls": 4},
            "authority": {"completed_pilot_result": d.binding(self.root, prior_result),
                          "accepted_pilot_model_outputs": d.binding(self.root, accepted)},
            "model_recipe": recipe, "source_and_scene_policy": {"fixture_only": True},
            "cache_and_memory_policy": {"fixture_only": True},
            "outputs": {"root": self.action_output.relative_to(self.root).as_posix()},
            "validation_before_real_run": ["synthetic fixture"], "resource_estimate": {"fixture_only": True},
        }
        proposal_path = self.root / "action_proposal.json"
        d.write_once(proposal_path, self.action_proposal)
        self.action_approval = {
            "schema_version": "nba_wasb_action_observation_approval/v0.1", "status": "approved",
            "approved_by": "Ryan", "approved_at_utc": "2026-10-20T01:10:40+00:00",
            "proposal": d.binding(self.root, proposal_path),
            "scope": {"proposal_id": "synthetic_action", "implement": True, "validate": True,
                      "execute_one_resumable_run": True,
                      "windows": [{k: self.window[k] for k in APPROVED_WINDOW_FIELDS}],
                      **{k: copy.deepcopy(self.action_proposal[k]) for k in
                         ("totals", "model_recipe", "source_and_scene_policy", "cache_and_memory_policy",
                          "outputs", "validation_before_real_run", "resource_estimate")}},
        }
        approval_path = self.root / "action_approval.json"
        d.write_once(approval_path, self.action_approval)
        return proposal_path, approval_path

    def save_scene(self, segments):
        scene = {"status": "ai_source_continuity_reviewed", "proposal": self.context["proposal_binding"],
                 "windows": [{"candidate_id": self.manifest["candidate_id"],
                              "input_manifest": d.binding(self.root, self.manifest_path), "segments": segments}]}
        self.scene_path.write_text(json.dumps(scene), encoding="utf-8")

    def infer(self, adapter=None, segments=None):
        adapter = adapter or FakeAdapter()
        result = action.infer_action(self.root, self.manifest, segments or self.segments,
                                     self.context, lambda: adapter)
        return result, adapter

    def old_snapshot(self):
        return {p.relative_to(self.old_output).as_posix(): p.read_bytes()
                for p in self.old_output.rglob("*") if p.is_file()}

    def test_actual_producer_cache_import_extended_context_and_no_old_reinference(self):
        before = self.old_snapshot()
        action.validate_manifest(self.manifest, self.window, self.reference)
        result, adapter = self.infer()
        self.assertEqual(len(adapter.calls), 4)
        self.assertNotIn([0, 40, 80], [[int(image[0, 0, 0]) for image in rows] for rows in adapter.calls])
        self.assertEqual([f["temporal_contributions"] for f in result["frames"]], [1, 2, 3, 3, 3, 2, 1])
        self.assertEqual([f["source_pts_ticks"] for f in result["frames"]],
                         [993392, 994832, 996362, 997802, 999332, 1000772, 1002302])
        imports = [r for r in result["triplet_caches"] if r["origin"] == "prior_pilot_import"]
        self.assertEqual(len(imports), 1)
        prior_receipt = d.read_json(self.old_output / self.reference["candidate_id"] / "triplets/triplet_000660.json")
        self.assertEqual(imports[0]["original_identity_sha256"], d.canonical(prior_receipt["identity"]))
        self.assertEqual(imports[0]["original_started_record"], prior_receipt["started_record"])
        self.assertEqual(imports[0]["attempt_id"], prior_receipt["attempt_id"])
        self.assertEqual(self.old_snapshot(), before)
        self.assertEqual(result["model_output_human_review"], "pending")
        self.assertFalse(result["annotations_present"])
        self.assertNotIn("annotations", result)
        summary = action.summarize(self.manifest, result)
        self.assertEqual((summary["imported_prior_triplets"], summary["action_triplets"]), (1, 4))
        self.assertEqual(summary["semantics"], "unlabeled availability, not accuracy")
        factory = Mock(side_effect=AssertionError("Completed action or pilot input reinferred"))
        resumed = action.infer_action(self.root, self.manifest, self.segments, self.context, factory)
        self.assertEqual(resumed, result)
        factory.assert_not_called()

    def test_corrupt_old_cache_or_missing_receipt_refuses_without_old_repair_or_model(self):
        folder = self.old_output / self.reference["candidate_id"] / "triplets"
        old_segment = [{"source_frame_range_inclusive": [660, 662], "kind": "live_action"}]
        factory = Mock(side_effect=AssertionError("Invalid old cache reinferred"))
        for mode in ("corrupt_cache", "missing_receipt"):
            path = folder / ("triplet_000660.npz" if mode == "corrupt_cache" else "triplet_000660.json")
            raw = path.read_bytes()
            if mode == "corrupt_cache": path.write_bytes(raw + b"corruption")
            else: path.unlink()
            try:
                with self.subTest(mode=mode), self.assertRaises(ValueError):
                    action.infer_action(self.root, self.manifest, old_segment, self.context, factory)
                if mode == "corrupt_cache": self.assertEqual(path.read_bytes(), raw + b"corruption")
                else: self.assertFalse(path.exists())
            finally:
                path.write_bytes(raw)
        factory.assert_not_called()

    def test_producer_five_frame_pilot_interior_stays_identical_and_mismatch_refuses(self):
        larger_reference = copy.deepcopy(self.reference)
        larger_reference["frames"] = self.manifest["frames"][1:-1]
        larger_prior_output = self.root / "data/outputs/five_frame_producer"
        old_adapter = FakeAdapter()
        old_observations = d.infer_reference(self.root, larger_reference, self.config,
                                             self.context["old_plan"], larger_prior_output,
                                             lambda: old_adapter)
        self.assertEqual(len(old_adapter.calls), 3)
        context = copy.deepcopy(self.context)
        context["references"] = [larger_reference]
        context["old_observations"] = {larger_reference["candidate_id"]: old_observations}
        adapter = FakeAdapter()
        result = action.infer_action(self.root, self.manifest, self.segments, context, lambda: adapter)
        self.assertEqual(len(adapter.calls), 2)
        comparison = result["pilot_context_comparison"]
        self.assertEqual(comparison["unchanged_context_frames_verified_identical"], [661])
        self.assertEqual([r["source_frame_index"] for r in comparison["changed_context_frames"]],
                         [659, 660, 662, 663])
        self.assertFalse(comparison["original_score_recomputed"])
        old_observations["frames"][2]["center_xy_px"][0] += 1
        factory = Mock(side_effect=AssertionError("Completed cached context reinferred"))
        with self.assertRaisesRegex(ValueError, "Unchanged pilot context produced different"):
            action.infer_action(self.root, self.manifest, self.segments, context, factory)
        factory.assert_not_called()

    def test_failure_and_resume_preserve_attempts_and_completed_new_cache(self):
        class FailsOnSecond(FakeAdapter):
            def predict_triplet(self, images):
                result = super().predict_triplet(images)
                if len(self.calls) == 2:
                    raise RuntimeError("synthetic second action call failure")
                return result
        failed_adapter = FailsOnSecond()
        with self.assertRaisesRegex(RuntimeError, "second action call"):
            self.infer(failed_adapter)
        folder = self.action_output / self.reference["candidate_id"] / "triplets"
        retained = {p: p.read_bytes() for p in folder.rglob("*") if p.is_file()}
        self.assertEqual(len(list(folder.glob("triplet_*.npz"))), 1)
        self.assertEqual(len(list(folder.glob("attempts/*_failed.json"))), 1)
        result, resumed = self.infer()
        self.assertEqual(len(resumed.calls), 3)
        self.assertEqual(len(result["triplet_caches"]), 5)
        for path, raw in retained.items(): self.assertEqual(path.read_bytes(), raw)
        accounting = d.call_accounting(self.action_output)
        self.assertEqual(accounting["model_call_starts"], 5)
        self.assertEqual(accounting["completed_unique_triplets"], 4)
        self.assertEqual(accounting["failed_attempts"], 1)
        self.assertEqual(accounting["started_without_completed_or_failed_record"], [])

    def test_reviewed_boundaries_withhold_short_segments_and_never_cross(self):
        segments = [{"source_frame_range_inclusive": [658, 659], "kind": "cutaway"},
                    {"source_frame_range_inclusive": [660, 662], "kind": "live_action"},
                    {"source_frame_range_inclusive": [663, 664], "kind": "replay"}]
        self.save_scene(segments)
        loaded = action.load_scenes(self.root, self.scene_path, self.context, [self.manifest])
        self.context["scene_binding"] = d.binding(self.root, self.scene_path)
        factory = Mock(side_effect=AssertionError("Triplet crossed scene boundary"))
        result = action.infer_action(self.root, self.manifest, loaded[self.manifest["candidate_id"]], self.context, factory)
        self.assertEqual([r["first_source_frame_index"] for r in result["triplet_caches"]], [660])
        self.assertEqual([f["state"] for f in result["frames"]],
                         ["withheld", "withheld", "observed", "observed", "observed", "withheld", "withheld"])
        self.assertEqual([f["temporal_contributions"] for f in result["frames"]], [0, 0, 1, 1, 1, 0, 0])
        summary = action.summarize(self.manifest, result)
        self.assertEqual((summary["observed"], summary["missing"], summary["withheld"]), (3, 0, 4))
        self.assertAlmostEqual(sum(row["duration_seconds"] for row in summary["state_intervals"]), 10350 / 90000)
        factory.assert_not_called()
        self.save_scene(segments[:-1])
        with self.assertRaisesRegex(ValueError, "cover every frame"):
            action.load_scenes(self.root, self.scene_path, self.context, [self.manifest])

    def test_manifest_rejects_changed_native_cadence_pilot_rows_and_annotations(self):
        for mode in ("cadence", "pilot", "annotations"):
            changed = copy.deepcopy(self.manifest)
            if mode == "cadence": changed["frames"][1]["source_pts_ticks"] += 1
            elif mode == "pilot": changed["frames"][2]["png"]["path"] = "wrong.png"
            else: changed["annotations"] = []
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                action.validate_manifest(changed, self.window, self.reference)

    def test_load_prepared_consumes_producer_authority_without_png_decode_and_rejects_tamper(self):
        from src.ball_tracking import nba_action_inputs as inputs
        context = copy.deepcopy(self.context)
        context["output"] = self.root / "data/outputs/load_prepared"
        context["proposal"]["windows"][0].update(reused_native_png_frames=3, new_native_png_frames=4)
        context["proposal"]["outputs"]["root"] = context["output"].relative_to(self.root).as_posix()
        proposal_path = self.root / "prepared_proposal.json"
        d.write_once(proposal_path, context["proposal"])
        context["proposal_binding"] = d.binding(self.root, proposal_path)
        approval = copy.deepcopy(self.action_approval)
        approval["proposal"] = context["proposal_binding"]
        approval["scope"]["outputs"] = copy.deepcopy(context["proposal"]["outputs"])
        approval_path = self.root / "prepared_approval.json"
        d.write_once(approval_path, approval)
        context["approval"] = d.binding(self.root, approval_path)
        rows = [{k: frame[k] for k in ("source_frame_index", "source_pts_ticks")}
                for frame in self.manifest["frames"]]
        source_rows = (self.root / "source.mp4", rows, self.manifest["source_end_exclusive_pts_ticks"])
        indexed = {frame["source_frame_index"]: frame for frame in self.manifest["frames"]}

        def synthetic_extraction(root, window, selected, end_pts, directory, identity, ffmpeg):
            frames = [indexed[row["source_frame_index"]] for row in selected]
            d.write_once(directory / "completion.json", {"status": "complete", "identity": identity,
                                                         "frames": frames, "fixture_only": True})
            return frames

        # Exercise the actual input-manifest/identity producer. Only extraction
        # and original-source audit lookup are replaced with tiny synthetic data.
        with patch.object(inputs, "_source_rows", return_value=source_rows), \
             patch.object(inputs, "_extract_range", side_effect=synthetic_extraction):
            prepared = inputs.prepare_inputs(self.root, context["proposal"], context["approval"],
                                             context["references"], context["output"] / "inputs", "unused")
        manifest_path = context["output"] / "inputs" / self.manifest["candidate_id"] / "manifest.json"
        original_manifest = manifest_path.read_bytes()
        range_path = self.root / prepared[0]["preparation"]["range_completions"][0]["path"]
        original_range = range_path.read_bytes()
        with patch.object(inputs, "_source_rows", return_value=source_rows) as audit, \
             patch.object(d.nba, "read_verified_png", side_effect=AssertionError("Prepared PNG reread")), \
             patch.object(inputs.subprocess, "run", side_effect=AssertionError("Prepared source redecode")), \
             patch.object(Image, "open", side_effect=AssertionError("Prepared PNG redecode")):
            self.assertEqual(action.load_prepared(self.root, context), prepared)
            audit.assert_called_once_with(self.root, context["proposal"]["windows"][0])
            changed = copy.deepcopy(prepared[0])
            changed["preparation"]["identity"]["approval"]["sha256"] = "0" * 64
            manifest_path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Prepared input authority changed"):
                action.load_prepared(self.root, context)
            manifest_path.write_bytes(original_manifest)
            range_path.write_bytes(original_range + b"changed completion")
            with self.assertRaisesRegex(ValueError, "Bound file changed"):
                action.load_prepared(self.root, context)
            self.assertEqual(range_path.read_bytes(), original_range + b"changed completion")
            self.assertEqual(audit.call_count, 3)

    def test_exact_approval_projection_accepted_but_scope_and_recipe_changes_rejected(self):
        self.assertEqual(set(self.action_approval["scope"]["windows"][0]), APPROVED_WINDOW_FIELDS)
        self.assertNotEqual(self.action_approval["scope"]["windows"], self.action_proposal["windows"])
        context = action.load_context(self.root, self.proposal_path, self.action_approval_path)
        self.assertEqual(context["proposal_binding"], self.action_approval["proposal"])
        original_proposal = self.proposal_path.read_bytes()
        original_approval = self.action_approval_path.read_bytes()
        for mode in ("binding", "status", "window", "total", "cadence", "training"):
            proposal = copy.deepcopy(self.action_proposal)
            approval = copy.deepcopy(self.action_approval)
            if mode == "binding": approval["proposal"]["sha256"] = "0" * 64
            elif mode == "status": approval["status"] = "pending"
            elif mode == "window": approval["scope"]["windows"][0]["source_frame_range_inclusive"][0] -= 1
            elif mode == "total": approval["scope"]["totals"]["maximum_new_model_calls"] += 1
            else:
                key, value = ("native_input_spacing_ms", [40]) if mode == "cadence" else ("training", True)
                proposal["model_recipe"][key] = value
                approval["scope"]["model_recipe"][key] = value
                self.proposal_path.write_text(json.dumps(proposal), encoding="utf-8")
                approval["proposal"] = d.binding(self.root, self.proposal_path)
            self.action_approval_path.write_text(json.dumps(approval), encoding="utf-8")
            try:
                with self.subTest(mode=mode), self.assertRaises(ValueError):
                    action.load_context(self.root, self.proposal_path, self.action_approval_path)
            finally:
                self.proposal_path.write_bytes(original_proposal)
                self.action_approval_path.write_bytes(original_approval)


if __name__ == "__main__":
    unittest.main()
