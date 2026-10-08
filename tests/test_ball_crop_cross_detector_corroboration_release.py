"""Artificial-file release tests; no real evidence or model calls.

Every generated file lives beneath tempfile's supervised TEMP root. Repository
reads are restricted to the frozen administrative scope and proposal prose.
The bounded Windows smoke launches only an artificial ownership probe.
"""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
import copy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.ball_tracking import crop_cross_detector_corroboration_release as release
from src.ball_tracking import crop_cross_detector_corroboration_evaluation as scoring
from src.ball_tracking import crop_cross_detector_corroboration as selector
from src.ball_tracking import crop_cross_detector_corroboration_review as review
from src.ball_tracking import crop_retention_resources as resources
from src.ball_tracking import tiled_candidates as tiled
from src.ball_tracking import yolo_crop_candidates as yolo_candidates
from src.ball_tracking import yolo_crop_recovery as yolo_recovery
from src.ball_tracking import yolo11x_adapter as yolo_adapter
from src.ball_tracking.development_experiments import canonical_sha256
from test_ball_crop_cross_detector_corroboration_evaluation import fixture, control_reference
from test_ball_crop_retention_experiment import candidate_fixture
from test_ball_tiled_comparison import crop_result
from test_ball_crop_retention_error_breakdown import limits as artificial_limits

ROOT = Path(__file__).resolve().parents[1]
SCOPE_PATH = "configs/ball_tracking/proposals/rfdetr_yolo_crop_corroboration_release_v0_1.json"
COMMIT = "d" * 40


def encoded(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")) + "\n").encode()


def stat_metadata(path):
    value = path.stat()
    return dict(size_bytes=value.st_size, mtime_ns=value.st_mtime_ns,
                device=value.st_dev, inode=value.st_ino)


def put(root, name, payload):
    """Bind only bytes constructed by this test under its temporary root."""
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload if isinstance(payload, bytes) else encoded(payload))
    raw = path.read_bytes()
    return dict(path=name, size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def administrative_scope():
    return json.loads((ROOT / SCOPE_PATH).read_text(encoding="utf-8"))


def release_fixture(root):
    """190 tiny inputs and a full 342-file output contract, without old runs."""
    scope = administrative_scope()
    scope.update(artificial_only=True, fixture_id="synthetic:release-contract", status="artificial_fixture",
                 windows=[], existing_scientific_files=[], saved_controls=[], saved_reports=[], saved_mean_references=[])
    scope["outputs"]["directory"] = "data/outputs/synthetic_corroboration"
    scope["outputs"]["files"] = []
    records, runs, old_reports, source_rows = scope["existing_scientific_files"], {}, {}, []
    pools = {purpose: {"old": [], "mean": []} for purpose in scoring.POOLS}
    pending = []

    def record(name, role, phase, value, **metadata):
        binding = put(root, name, value)
        records.append({**binding, "role": role, "first_allowed_phase": phase,
                        "preparation_metadata": stat_metadata(root / name), **metadata})
        return binding

    def output(name, role, maximum=4 * 1024 * 1024):
        scope["outputs"]["files"].append(dict(path=name, role=role, maximum_bytes=maximum))

    for index in range(6):
        start = (50, 200, 250, 25, 300, 150)[index]
        labels, rf, yolo, observations, reports, window = fixture(
            count=25, start=start, purpose=scoring.POOLS[index % 2],
            possession=f"possession_{index // 2 + 1:03d}", hidden=tuple(range(15, 20)) if index == 5 else ())
        ident = f"synthetic_window_{index}"
        window.update(window_id=ident, annotation_set_id=labels.annotation_set_id)
        runs[ident] = {"rfdetr": rf, "yolo": yolo}
        # Small artificial stand-ins exercise access/binding. Pure adapters get
        # separate genuine-format tests below; no production loader is mocked in.
        for name, role, detector in (("rf", "rf_candidates", "rfdetr"), ("yolo", "yolo_candidates", "yolo")):
            binding = record(f"data/synthetic/{name}_{index}.json", role, "selection",
                             {"artificial": True, "detector": detector, "window_id": ident,
                              "header": {"assembly_code_commit": COMMIT, "actual_inference_commits": ["c" * 40, "e" * 40],
                                         "model_code_commit_role": yolo_recovery.ROLE,
                                         "inference_units": [{"artificial_only": True, "actual_inference_commit": "c" * 40}]}}, window_id=ident)
            window["crop_candidates" if detector == "rfdetr" else "yolo_candidates"] = binding
        record(f"data/synthetic/labels_{index}.json", "reviewed_annotations", "evaluation",
               labels.to_dict(), window_id=ident)
        scope["windows"].append(window)
        old_reports[ident] = copy.deepcopy(reports)
        for arm in scoring.CONTROLS:
            role = "saved_mean_observations" if arm == scoring.MEAN else "saved_control_observations"
            binding = record(f"data/synthetic/{index}_{arm}.json", role, "evaluation",
                             {"observations": observations[arm], "inert_pointer": "data/clips/forbidden.mp4"}, window_id=ident)
            ref = control_reference(observations[arm], reports[arm])
            if arm != scoring.MEAN:
                scope["saved_controls"].append({**ref, "file": binding, "window_id": ident,
                                                "purpose": window["purpose"], "possession_id": window["possession_id"]})
                offset = len(pools[window["purpose"]]["old"])
                pools[window["purpose"]]["old"].append(reports[arm])
                pending.append((ident, window["purpose"], arm, ref, binding, offset))
            else:
                offset = len(pools[window["purpose"]]["mean"])
                pools[window["purpose"]]["mean"].append(reports[arm])
                pending.append((ident, window["purpose"], arm, ref, binding, offset))
        # One shared tiny image per frame; generated bytes, never video pixels.
        import cv2
        import numpy as np
        okay, png = cv2.imencode(".png", np.zeros((90, 160, 3), np.uint8))
        if not okay:
            raise AssertionError("Artificial PNG encoding failed")
        for frame in range(start, start + 25):
            binding = record(f"data/synthetic/png/{index}/{frame}.png", "source_png", "review", png.tobytes(),
                             window_id=ident, frame_index=frame)
            source_rows.append({"window_id": ident, "frame_index": frame, "source_png": binding})
            for panel in ("saved_top_one", "new_corroborated"):
                output(f"review/{ident}/native/{panel}/frame_{frame:06d}.png", "native_review_overlay")
        output(f"selection/{ident}/observations.json", "new_selection_and_linear_candidate_audit")
        output(f"evaluation/{ident}.json", "new_report_copied_three_controls_and_comparison")
        output(f"review/{ident}/comparison.mp4", "new_synchronized_video")
        output(f"review/{ident}/first.png", "first_frame_composite")
        output(f"review/{ident}/last.png", "last_frame_composite")
        output(f"review/{ident}/review_index.json", "new_review_index")
    bound_pools = {}
    for purpose, groups in pools.items():
        for name, reports in groups.items():
            field = "evaluation_reports" if name == "old" else "new_evaluation_reports"
            role = "saved_scoring_pool" if name == "old" else "saved_mean_scoring_pool"
            bound_pools[purpose, name] = record(f"data/synthetic/{purpose}_{name}.json", role, "evaluation",
                                               {field: reports, "unrelated": {"must_not_analyze": "artificial ignored report"}}, purpose=purpose)
        output(f"evaluation/{purpose}.json", "separate_pool_comparison")
    for ident, purpose, arm, ref, obs_binding, offset in pending:
        if arm == scoring.MEAN:
            pool = bound_pools[purpose, "mean"]
            scope["saved_mean_references"].append({"window_id": ident, "purpose": purpose, "arm": arm,
                "observations_file": obs_binding["path"], "observations_json_pointer": "/observations",
                "report_file": pool["path"], "report_json_pointer": f"/new_evaluation_reports/{offset}",
                "original_selection_commit": ref["original_selection_commit"],
                "original_evaluation_commit": ref["original_evaluation_commit"],
                "expected_config": ref["config"], "expected_localization_radius_px": 10.0})
        else:
            pool = bound_pools[purpose, "old"]
            scope["saved_reports"].append({**ref, "window_id": ident, "purpose": purpose,
                "source": {**pool, "json_pointer": f"/evaluation_reports/{offset}"},
                "observations_file": obs_binding})
    for name, role in (("manifest.json", "all_six_selection_freeze"), ("provenance.json", "declared_access_and_artifact_provenance"),
                       ("summary.json", "bounded_scientific_summary"), ("summary.md", "human_readable_outcome")):
        output(name, role)
    scope["outputs"]["count"] = len(scope["outputs"]["files"])
    scope["outputs"]["sum_of_individual_file_maxima_bytes"] = sum(row["maximum_bytes"] for row in scope["outputs"]["files"])
    scope["existing_scientific_file_count"] = len(records)
    scope["existing_scientific_input_bytes_at_preparation"] = sum(row["size_bytes"] for row in records)
    scope["input_role_counts"] = dict(Counter(row["role"] for row in records))
    scope["input_phase_counts"] = dict(Counter(row["first_allowed_phase"] for row in records))
    return scope, runs, old_reports, source_rows


def fake_render(window, run, labels, observations_by_arm, reports_by_arm, *, read_source, write_bytes, open_video, verify_video):
    """Lightweight renderer double verifies all 25 authorized reads and paths."""
    prefix = f"review/{window['window_id']}"
    frames = list(range(window["start_frame_index"], window["end_frame_index"] + 1))
    for frame in frames:
        pixels = read_source(frame)
        if pixels.shape != (run.source_video.height_px, run.source_video.width_px, 3):
            raise AssertionError("Artificial source shape differs")
        for panel in ("saved_top_one", "new_corroborated"):
            write_bytes(f"{prefix}/native/{panel}/frame_{frame:06d}.png", f"artificial-overlay-{frame}-{panel}".encode())
    write_bytes(prefix + "/first.png", b"artificial-first")
    write_bytes(prefix + "/last.png", b"artificial-last")
    write_bytes(prefix + "/comparison.mp4", b"artificial-video-placeholder-never-decoded")
    index = {"window_id": window["window_id"], "frame_count": 25, "frame_indices": frames,
             "final_frame_index": frames[-1], "human_final_frame_review": "pending", "native_overlay_count": 50}
    binding = write_bytes(prefix + "/review_index.json", encoded(index))
    return {"index": index, "index_binding": binding}


def yolo_format_fixture(root):
    """Genuine saved v0.2 shape composed from invented detections, no inference."""
    window, rf, _, _ = candidate_fixture(root)
    model = replace(rf.model_provenance, model_name=yolo_adapter.MODEL_NAME, package_name="ultralytics",
                    package_version=yolo_adapter.PACKAGE_VERSION, code_commit=COMMIT,
                    input_width_px=640, input_height_px=640, resize_mode=yolo_adapter.RESIZE_MODE,
                    weights_identifier=yolo_adapter.WEIGHTS_IDENTIFIER, weights_sha256=yolo_adapter.WEIGHTS_SHA256,
                    precision="float32", device="cuda:0 | artificial metadata only", tiling_enabled=False,
                    postprocessing_description=yolo_adapter.POSTPROCESSING)
    sources, units, frames = [], [], []
    for index in range(25):
        source = {"path": f"data/synthetic/source_{index}.png", "sha256": "a" * 64}
        sources.append({"window_id": window["window_id"], "frame_index": index, "source_png": source})
        views = []
        for ordinal, view in enumerate(tiled.crop_views()):
            # Same source box represented twice across overlapping crops;
            # duplicate global candidates and original per-crop mapping remain.
            points = [(800., 100., .8)] if ordinal == 0 else [(32., 100., .8)] if ordinal == 1 else []
            candidates = crop_result(view, points)["candidates"]
            prediction = {"candidates": candidates, "postprocessing": {
                "source_class_id": 32,
                "returned_candidates": [{"postprocessor_index": number, "bbox_xyxy_px": candidate["bbox_xyxy_px"],
                                          "confidence": candidate["confidence"], "source_class_id": 32}
                                         for number, candidate in enumerate(candidates)],
                "exported_candidate_sources": [{"candidate_index": number, "postprocessor_index": number}
                                                for number in range(len(candidates))],
                "cap_saturated": False, "input_transform": yolo_adapter.INPUT_TRANSFORM},
                "forward_accounting": {"synthetic_forwards": 1, "project_attempts": 1, "project_forwards": 1,
                                       "this_project_attempt_forwards": 1, "preparation_complete": True}}
            views.append({"view": view, "prediction": prediction, "elapsed_seconds": .001,
                          "cuda_peak_allocated_bytes": 128, "attempt_id": f"artificial_{index}_{ordinal}"})
            units.append({**yolo_recovery.unit(window, index, view),
                          "actual_inference_commit": "c" * 40 if index < 10 else "e" * 40,
                          "checkpoint": {"path": f"data/synthetic/inert_{index}_{ordinal}.json", "sha256": "b" * 64}})
        frames.append(yolo_candidates.make_frame(index, source, views, rf.source_video, model))
    header = {"window": copy.deepcopy(window), "per_view_model_provenance": model.to_dict(),
              "source_frames": sources, "crop_views": tiled.crop_views(), "inference_units": units,
              "inference_inventory_sha256": canonical_sha256(units), "actual_inference_commits": ["c" * 40, "e" * 40],
              "assembly_code_commit": COMMIT, "model_code_commit_role": yolo_recovery.ROLE,
              "selected_operating_point": None, "quality_gate": None}
    payload = {"schema_version": yolo_recovery.CANDIDATE_SCHEMA, "header": header, "frames": frames,
               "content_sha256": canonical_sha256({"header": header, "frames": frames})}
    expected = yolo_recovery.candidate_run(payload)
    window["yolo_candidates"] = {"path": "data/synthetic/yolo.json", "sha256": "f" * 64}
    return window, expected, payload


class TemporaryRoot(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="corroboration_release_")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()


class FilePhaseTests(TemporaryRoot):
    def setUp(self):
        super().setUp()
        self.scope, self.runs, self.reports, _ = release_fixture(self.root)

    def access(self):
        return release.PhaseAccess(self.root, self.scope, artificial=True)

    def sink(self):
        return release.OutputSink(self.root, self.scope)

    def freeze(self, access, sink):
        bindings = [sink.json(f"selection/{window['window_id']}/observations.json", {"artificial": window["window_id"]})
                    for window in self.scope["windows"]]
        access.freeze(bindings, sink)
        return bindings

    def test_exact_190_input_12_28_150_and_342_output_contract(self):
        release.validate_scope(self.scope, production=False)
        self.assertEqual(self.scope["existing_scientific_file_count"], 190)
        self.assertEqual(self.scope["input_phase_counts"], {"selection": 12, "evaluation": 28, "review": 150})
        self.assertEqual(self.scope["outputs"]["count"], 342)
        for key in ("existing_scientific_files",):
            altered = copy.deepcopy(self.scope)
            altered[key].pop()
            with self.assertRaises(ValueError):
                release.validate_scope(altered, production=False)

    def test_labels_saved_controls_and_pixels_closed_before_full_freeze(self):
        access = self.access()
        for row in self.scope["existing_scientific_files"]:
            if row["first_allowed_phase"] != "selection":
                with patch.object(Path, "open", side_effect=AssertionError("premature body open")), self.assertRaises(ValueError):
                    access.read(row["path"])
        with self.assertRaises(ValueError):
            access.read("data/clips/forbidden.mp4")
        first = next(row for row in self.scope["existing_scientific_files"] if row["role"] == "rf_candidates")
        self.assertTrue(access.json(first["path"])["artificial"])

    def test_five_duplicate_or_changed_selections_never_unlock_labels(self):
        access, sink = self.access(), self.sink()
        bindings = [sink.json(f"selection/{window['window_id']}/observations.json", {"artificial": index})
                    for index, window in enumerate(self.scope["windows"])]
        for wrong in (bindings[:5], [bindings[0]] * 6, [{**binding, "sha256": "0" * 64} for binding in bindings]):
            with self.assertRaises(ValueError):
                access.freeze(wrong, sink)
            self.assertEqual(access.phase, "selection")
        access.freeze(bindings, sink)
        label = next(row for row in self.scope["existing_scientific_files"] if row["role"] == "reviewed_annotations")
        self.assertEqual(access.json(label["path"])["review"]["status"], "reviewed")
        with self.assertRaises(ValueError):
            access.freeze(bindings, sink)

    def test_every_later_read_rechecks_all_frozen_selections(self):
        access, sink = self.access(), self.sink()
        bindings = self.freeze(access, sink)
        # Publication bindings are repository-relative, as are receipt bindings.
        (self.root / bindings[-1]["path"]).write_bytes(b"tampered-sixth-selection")
        label = next(row for row in self.scope["existing_scientific_files"] if row["role"] == "reviewed_annotations")
        with self.assertRaises(ValueError):
            access.read(label["path"])
        with self.assertRaises(ValueError):
            access.begin_review(sink)

    def test_hash_size_and_filesystem_metadata_changes_fail_closed(self):
        row = self.scope["existing_scientific_files"][0]
        original = (self.root / row["path"]).read_bytes()
        access = self.access()
        (self.root / row["path"]).write_bytes(b"x" * len(original))
        with self.assertRaises(ValueError):
            access.read(row["path"])
        (self.root / row["path"]).write_bytes(original + b" ")
        with self.assertRaises(ValueError):
            access.read(row["path"])
        (self.root / row["path"]).write_bytes(original)
        self.scope["existing_scientific_files"][0]["preparation_metadata"]["inode"] += 1
        with self.assertRaises(ValueError):
            self.access().read(row["path"])

    def test_paths_reject_traversal_absolute_case_alias_ads_and_windows_devices(self):
        for path in ("../escape", "data/../escape", "/absolute", "C:/escape", "data\\escape", "data/file:stream", "data/CON", "data/a."):
            changed = copy.deepcopy(self.scope)
            changed["existing_scientific_files"][0]["path"] = path
            with self.subTest(path=path), self.assertRaises(ValueError):
                release.validate_scope(changed, production=False)
        changed = copy.deepcopy(self.scope)
        changed["existing_scientific_files"][1]["path"] = changed["existing_scientific_files"][0]["path"].upper()
        with self.assertRaises(ValueError):
            release.validate_scope(changed, production=False)

    def test_output_create_only_caps_and_exact_completion_no_extras(self):
        sink = self.sink()
        binding = sink.write("summary.md", b"artificial")
        self.assertEqual(binding["size_bytes"], 10)
        for name, raw in (("summary.md", b"changed"), ("undeclared.txt", b"x"), ("../escape", b"x")):
            with self.assertRaises((ValueError, FileExistsError)):
                sink.write(name, raw)
        with self.assertRaises(ValueError):
            sink.complete()
        for row in self.scope["outputs"]["files"]:
            if row["path"] != "summary.md":
                sink.write(row["path"], b"x")
        result = sink.complete()
        bindings = result[0] if isinstance(result, tuple) else result
        self.assertEqual(len(bindings), 342)
        with self.assertRaises((ValueError, FileExistsError)):
            self.sink()

    def test_output_per_file_bound_is_not_silently_truncated(self):
        scope = copy.deepcopy(self.scope)
        next(row for row in scope["outputs"]["files"] if row["path"] == "summary.md")["maximum_bytes"] = 3
        sink = release.OutputSink(self.root, scope)
        with self.assertRaises(ValueError):
            sink.write("summary.md", b"four")
        self.assertFalse((self.root / scope["outputs"]["directory"] / "summary.md").exists())

    def test_owned_video_publishes_25_frames_and_removes_only_verified_temporary(self):
        import numpy as np
        sink = self.sink()
        relative = f"review/{self.scope['windows'][0]['window_id']}/comparison.mp4"
        size = (review.TILE_WIDTH * 3, review.TILE_HEIGHT)
        writer = sink.open_video(relative, 5.0, size)
        pixels = np.zeros((size[1], size[0], 3), np.uint8)
        for _ in range(25):
            writer.write(pixels)
        writer.release()
        binding = sink.verify_video(relative, 25, 5.0, size)
        self.assertGreater(binding["size_bytes"], 0)
        self.assertTrue((self.root / binding["path"]).is_file())
        self.assertEqual(sink.videos, {})
        self.assertFalse((sink.folder / "tmp").exists())
        sink.verify(binding)

    def test_incomplete_generated_video_retains_failed_temporary_and_never_publishes(self):
        import numpy as np
        sink = self.sink()
        relative = f"review/{self.scope['windows'][0]['window_id']}/comparison.mp4"
        size = (review.TILE_WIDTH * 3, review.TILE_HEIGHT)
        writer = sink.open_video(relative, 5.0, size)
        pixels = np.zeros((size[1], size[0], 3), np.uint8)
        for _ in range(24):
            writer.write(pixels)
        writer.release()
        with self.assertRaisesRegex(ValueError, "final frame"):
            sink.verify_video(relative, 25, 5.0, size)
        self.assertNotIn(relative, sink.bindings)
        self.assertFalse((sink.folder / relative).exists())
        self.assertEqual(len(list((sink.folder / "tmp").glob("*.mp4"))), 1)
        sink.close_writers()


class AdapterTests(TemporaryRoot):
    def test_rf_saved_tiled_projection_preserves_indices_duplicates_and_extra_yolo_binding(self):
        window, expected, payload, _ = candidate_fixture(self.root)
        window["yolo_candidates"] = {"path": "data/synthetic/inert_yolo.json", "sha256": "f" * 64}
        with patch.object(Path, "open", side_effect=AssertionError("adapter must remain pure")):
            actual = release.candidate_run(payload, window, "rfdetr")
        self.assertEqual(actual.to_dict(), expected.to_dict())
        self.assertEqual(len(actual.frames[0].detections), 21)
        self.assertEqual(actual.frames[0].detections[20].candidate_index, 20)

    def test_rf_local_global_mapping_tampering_fails_even_when_resealed(self):
        window, _, payload, _ = candidate_fixture(self.root)
        payload["frames"][0]["candidates"][0]["view_ordinal"] = 1
        payload["content_sha256"] = canonical_sha256({"header": payload["header"], "frames": payload["frames"]})
        with self.assertRaises(ValueError):
            release.candidate_run(payload, window, "rfdetr")

    def test_yolo_recovery_keeps_actual_inference_inventory_separate_from_assembly(self):
        window, expected, payload = yolo_format_fixture(self.root)
        preserved = copy.deepcopy(payload)
        with patch.object(yolo_recovery, "load_candidate_run", side_effect=AssertionError("forbidden loader")), \
                patch.object(yolo_recovery, "_load_units", side_effect=AssertionError("forbidden checkpoint loader")), \
                patch.object(yolo_recovery, "_load_ledger", side_effect=AssertionError("forbidden journal loader")), \
                patch.object(yolo_adapter.YOLO11xAdapter, "__init__", side_effect=AssertionError("model construction")), \
                patch.object(Path, "open", side_effect=AssertionError("adapter body open")):
            actual = release.candidate_run(payload, window, "yolo")
        self.assertEqual(actual.to_dict(), expected.to_dict())
        self.assertEqual(payload, preserved)
        self.assertEqual(actual.model_provenance.code_commit, COMMIT)
        self.assertEqual({unit["actual_inference_commit"] for unit in payload["header"]["inference_units"]}, {"c" * 40, "e" * 40})
        self.assertEqual([candidate.center_xy_px for candidate in actual.frames[0].detections], [(800., 100.), (800., 100.)])

    def test_yolo_resealed_wrong_inventory_and_source_are_refused(self):
        window, _, payload = yolo_format_fixture(self.root)
        for mutation in (lambda value: value["header"].update(actual_inference_commits=[COMMIT]),
                         lambda value: value["header"]["window"]["source_video"].update(sha256="0" * 64),
                         lambda value: value["header"]["inference_units"].pop(),
                         lambda value: value["header"].update(model_code_commit_role="actual_inference_for_all")):
            changed = copy.deepcopy(payload)
            mutation(changed)
            changed["header"]["inference_inventory_sha256"] = canonical_sha256(changed["header"]["inference_units"])
            changed["content_sha256"] = canonical_sha256({"header": changed["header"], "frames": changed["frames"]})
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                release.candidate_run(changed, window, "yolo")


class WholeComparisonTests(TemporaryRoot):
    def setUp(self):
        super().setUp()
        self.scope, self.runs, self.reports, _ = release_fixture(self.root)

    def adapters(self, payload, window, detector):
        self.assertEqual(payload["window_id"], window["window_id"])
        self.assertEqual(payload["detector"], detector)
        return self.runs[window["window_id"]][detector]

    def test_full_file_protocol_freezes_six_then_scores_new_only_preserving_all_controls(self):
        originals = {row["path"]: (self.root / row["path"]).read_bytes() for row in self.scope["existing_scientific_files"]}
        from src.ball_tracking import crop_motion_factorial as old_selector
        from src.ball_tracking import crop_motion_evaluation as old_evaluator
        from src.ball_tracking import crop_path_confidence_mean as old_mean
        with ExitStack() as stack:
            stack.enter_context(patch.object(release, "candidate_run", side_effect=self.adapters))
            stack.enter_context(patch.object(old_selector, "rank_candidates", side_effect=AssertionError("old selector rerun")))
            stack.enter_context(patch.object(old_selector, "validate_observations", side_effect=AssertionError("old validator rerun")))
            stack.enter_context(patch.object(old_evaluator, "_evaluate_validated", side_effect=AssertionError("old evaluator rerun")))
            stack.enter_context(patch.object(old_mean, "iter_ranked_frames", side_effect=AssertionError("old mean selector rerun")))
            new_score = stack.enter_context(patch.object(scoring, "evaluate_selection", wraps=scoring.evaluate_selection))
            selected = stack.enter_context(patch.object(selector, "select_candidates", wraps=selector.select_candidates))
            result = release.run_artificial(self.root, self.scope, COMMIT, render=fake_render)
        self.assertEqual((selected.call_count, new_score.call_count), (6, 6))
        self.assertLessEqual(len(encoded(result)), 1024 * 1024)
        self.assertLessEqual(len(encoded(release.parent_return(result))), 512 * 1024)
        self.assertLessEqual(len(encoded(result["summary"])), 131072)
        output_root = self.root / self.scope["outputs"]["directory"]
        self.assertEqual({path.relative_to(output_root).as_posix() for path in output_root.rglob("*") if path.is_file()},
                         {row["path"] for row in self.scope["outputs"]["files"]})
        for path, original in originals.items():
            self.assertEqual((self.root / path).read_bytes(), original)
        for window in self.scope["windows"]:
            evaluated = json.loads((output_root / f"evaluation/{window['window_id']}.json").read_text())
            expected = {arm: self.reports[window["window_id"]][arm] for arm in scoring.CONTROLS}
            self.assertEqual(evaluated["saved_reports"], expected)
            self.assertEqual(len(evaluated["saved_reports"][scoring.MEAN]["config"]), 5)
            index = json.loads((output_root / f"review/{window['window_id']}/review_index.json").read_text())
            self.assertEqual(index["frame_count"], 25)
            self.assertEqual(index["final_frame_index"], window["end_frame_index"])
        provenance = json.loads((output_root / "provenance.json").read_text())
        self.assertEqual([row["phase"] for row in provenance["scientific_access_log"]],
                         ["selection"] * 12 + ["evaluation"] * 28 + ["review"] * 150)
        self.assertEqual(provenance["saved_control_replays"], 0)
        for window in self.scope["windows"]:
            header = json.loads(originals[window["yolo_candidates"]["path"]])["header"]
            self.assertEqual(provenance["source_origins"][window["window_id"]]["yolo_original_header"], header)

    def test_sixth_selection_failure_never_opens_labels_saved_scores_or_pixels(self):
        original_select = selector.select_candidates
        calls, opened = [], []

        def fail_sixth(*args, **kwargs):
            calls.append(1)
            if len(calls) == 6:
                raise RuntimeError("artificial sixth-selection failure")
            return original_select(*args, **kwargs)

        original_read = release.PhaseAccess.read

        def observe_read(access, path):
            opened.append(path)
            return original_read(access, path)

        with patch.object(release, "candidate_run", side_effect=self.adapters), \
                patch.object(release.PhaseAccess, "read", new=observe_read), \
                patch.object(selector, "select_candidates", side_effect=fail_sixth), \
                patch.object(scoring, "evaluate_selection", side_effect=AssertionError("premature scoring")):
            with self.assertRaisesRegex(RuntimeError, "sixth-selection"):
                release.run_artificial(self.root, self.scope, COMMIT, render=fake_render)
        allowed = {row["path"] for row in self.scope["existing_scientific_files"] if row["first_allowed_phase"] == "selection"}
        self.assertTrue(set(opened) <= allowed)
        self.assertEqual(len(opened), 12)
        self.assertFalse((self.root / self.scope["outputs"]["directory"] / "summary.json").exists())

    def test_changed_saved_control_after_freeze_fails_before_new_evaluation_or_media(self):
        target = next(row for row in self.scope["existing_scientific_files"] if row["role"] == "saved_control_observations")
        original_freeze = release.PhaseAccess.freeze

        def mutate_after_freeze(access, bindings, sink):
            result = original_freeze(access, bindings, sink)
            (self.root / target["path"]).write_bytes(b"tampered-after-selection")
            return result

        with patch.object(release, "candidate_run", side_effect=self.adapters), \
                patch.object(release.PhaseAccess, "freeze", new=mutate_after_freeze), \
                patch.object(scoring, "evaluate_selection", side_effect=AssertionError("tampered old control scored")):
            with self.assertRaises(ValueError):
                release.run_artificial(self.root, self.scope, COMMIT, render=fake_render)
        output_root = self.root / self.scope["outputs"]["directory"]
        self.assertEqual(len(list((output_root / "selection").rglob("observations.json"))), 6)
        self.assertFalse((output_root / "review").exists())


def artificial_prefix(scope):
    """Invent the declared accounting shape; never read the real journal."""
    history = scope["preserved_history"]
    failures = list(history["historic_failure_ids"])
    ids = failures + [f"{index + 100:032x}" for index in range(59)]
    events = []
    used = 0.0
    for number, ident in enumerate(ids):
        elapsed = 50.0 if number < 62 else history["consumed_seconds"] - used
        used += elapsed
        events.append({"kind": "started", "attempt_id": ident, "unit_key": f"artificial_old_{number}",
                       "selection_unit": False, "reserved_seconds": 1200.0})
        for sample in range(50 if number < 62 else 104):
            events.append({"kind": "sample", "attempt_id": ident, "elapsed_seconds": elapsed * sample / 110})
        events.append({"kind": "finished", "attempt_id": ident, "elapsed_seconds": elapsed,
                       "success": ident not in failures, "worker_result": None})
    for index, event in enumerate(events):
        event["sha256"] = f"{index + 1:064x}"
    events[-1]["sha256"] = history["resource_tip"]
    return events


class HistoryBoundaryTests(TemporaryRoot):
    def journal(self, events=None):
        scope = administrative_scope()
        journal = release.CorroborationJournal.__new__(release.CorroborationJournal)
        journal.root, journal.folder = self.root, self.root / "resource_events"
        journal.scope = scope
        journal.events = artificial_prefix(scope) if events is None else events
        journal.limits = artificial_limits()
        journal.baseline_bytes = 0
        for event in journal.events:
            if event["kind"] in ("started", "finished"):
                suffix = "reservation" if event["kind"] == "started" else "completion"
                put(self.root, f"attempts/{event['attempt_id']}.{suffix}.json", {"event_sha256": event["sha256"]})
        return journal, scope

    def test_exact_preserved_prefix_and_consumed_balance_are_not_reset(self):
        journal, scope = self.journal()
        release.verify_history(journal, scope, phase="before")
        self.assertEqual(len(journal.events), 3330)
        self.assertEqual(len(journal._attempts()), 63)
        self.assertEqual(sum(event["success"] is True for event in journal.events if event["kind"] == "finished"), 59)
        self.assertAlmostEqual(journal.consumed(), 3547.523999999985, places=8)

    def test_one_reservation_preserves_prefix_and_consumed_attempt_cannot_retry(self):
        journal, scope = self.journal()
        original = copy.deepcopy(journal.events)
        unit = scope["proposed_scientific_unit"]["key"]
        ident, reserved = journal.reserve(unit, False)
        self.assertEqual(reserved, 1200)
        self.assertEqual(journal.events[:-1], original)
        self.assertEqual(json.loads((self.root / "attempts" / f"{ident}.reservation.json").read_text()),
                         {"event_sha256": journal.events[-1]["sha256"]})
        with self.assertRaises((ValueError, resources.ResourceLimitError)):
            journal.reserve(unit, False)

    def test_wrong_tip_wrong_count_changed_budget_and_unexplained_suffix_refused(self):
        for mutate in (lambda rows: rows[-1].update(sha256="0" * 64),
                       lambda rows: rows.pop(),
                       lambda rows: rows[-1].update(elapsed_seconds=1.0),
                       lambda rows: rows.append({"kind": "started", "attempt_id": "a" * 32,
                                                  "unit_key": "unexplained", "selection_unit": False, "reserved_seconds": 1.0})):
            journal, scope = self.journal()
            mutate(journal.events)
            with self.subTest(mutate=mutate), self.assertRaises((ValueError, resources.ResourceLimitError)):
                release.verify_history(journal, scope, phase="before")

    def test_unknown_or_selection_unit_cannot_reserve_scientific_time(self):
        for key, flag in (("unknown", False), ("cross-detector-corroboration:study:", True)):
            journal, _ = self.journal()
            with self.subTest(key=key, flag=flag), self.assertRaises((ValueError, resources.ResourceLimitError)):
                journal.reserve(key, flag)
            self.assertEqual(len(journal.events), 3330)

    def test_orphan_attempt_evidence_prevents_reinitializing_history(self):
        scope = administrative_scope()
        put(self.root, "attempts/" + "a" * 32 + ".reservation.json", {"event_sha256": "f" * 64})
        with self.assertRaises(resources.ResourceLimitError):
            release.CorroborationJournal(self.root, artificial_limits(), scope=scope)


def artificial_manifest():
    return {"schema_version": "ball_crop_corroboration_release_manifest/v0.1", "study_id": release.ID,
            "scope": {"path": release.SCOPE_PATH, "sha256": release.SCOPE_SHA},
            "proposal": {"path": release.PROPOSAL_PATH, "sha256": release.PROPOSAL_SHA},
            "execution_approval": {"path": release.APPROVAL_PATH, "sha256": "e" * 64},
            "implementation_validation": {"path": release.CERTIFICATE_PATH, "sha256": "e" * 64},
            "frozen_history": {"path": release.HISTORY_PATH, "sha256": "e" * 64},
            "post_commit_checkpoint": release.CHECKPOINT_PATH,
            "selected_method": None, "selected_operating_point": None, "quality_gate": None}


def certificate_fixture(root):
    """Invent 187 tiny source files and linked validation receipts in TEMP."""
    scope, manifest = administrative_scope(), artificial_manifest()
    manifest["scope"] = put(root, release.SCOPE_PATH, (ROOT / release.SCOPE_PATH).read_bytes())
    manifest["proposal"] = put(root, release.PROPOSAL_PATH, (ROOT / release.PROPOSAL_PATH).read_bytes())
    implementation_files = ["src/ball_tracking/crop_cross_detector_corroboration_release.py",
                            "tests/test_ball_crop_cross_detector_corroboration_release.py"]
    bindings = [put(root, f"src/artificial/source_{index:03d}.py", b"" if index == 0 else b"# Artificial source certificate fixture.\n") for index in range(179)]
    bindings += [put(root, f"tests/artificial/test_{index:03d}.py", b"# Artificial test source.\n") for index in range(5)]
    bindings += [put(root, name, b"# Artificial release source; never executed.\n") for name in implementation_files]
    bindings.append(put(root, "requirements.txt", b"# Artificial requirements.\n"))
    helper = put(root, release.ADMIN_ROOT + "/validate.py", b"# Artificial supervisor; never executed.\n")
    absolute_helper = {**helper, "path": str(root / helper["path"])}
    absolute_bindings = [{**binding, "path": str(root / binding["path"])} for binding in bindings]
    scope["preserved_worktree_bindings"] = [put(root, f"docs/artificial/preserved_{index:02d}.txt", b"Artificial preserved bytes.\n") for index in range(16)]
    preserved = scope["preserved_worktree_bindings"] + [manifest["scope"], manifest["proposal"]]
    approval_payload = {
        "schema_version": "ball_crop_cross_detector_corroboration_release_implementation_approval/v0.1",
        "status": "approved_release_implementation_and_artificial_validation_only", "head": release.BASE_COMMIT,
        "proposal_bindings": [manifest["scope"], manifest["proposal"]], "implementation_files": implementation_files,
        "preserved_worktree_bindings": preserved, "artificial_validation_budget_seconds": 4200,
        "maximum_focused_seconds": 600, "maximum_full_seconds": 3600,
        "prior_validation_consumed_seconds_preserved": ["2164.2970000000005", "2295.467999999999"],
        "implementation_authorized": True, "artificial_validation_authorized": True,
        "scientific_body_access_authorized": False, "scientific_execution_authorized": False,
        "administrative_scientific_journal_replay_authorized": False, "new_media_presentation_authorized": False,
        "runtime_manifest_or_execution_approval_creation_authorized": False, "release_checkpoint_authorized": False,
        "stage_authorized": False, "commit_authorized": False, "push_authorized": False,
        "pr_authorized": False, "merge_authorized": False}
    approval = put(root, release.ADMIN_ROOT + "/approval.json", approval_payload)
    base = {"success": True, "returncode": 0, "failure": None, "owned_cleanup_verified": True,
            "cleanup_errors": [], "validator": absolute_helper, "validator_after": absolute_helper,
            "source_bindings": absolute_bindings, "source_bindings_after": absolute_bindings,
            "approval": approval, "approval_after": approval, "preservation_error": None,
            "preserved_worktree_bindings_before": preserved, "preserved_worktree_bindings_after": preserved,
            "baseline_test_count": 1167, "failed_count": 0, "error_count": 0, "expected_focused_test_count": 3}
    focused = {**base, "test_count": 3, "passed_count": 3, "skipped_count": 0, "elapsed_seconds": 2.0, "previously_consumed_seconds": 0.0}
    full = {**base, "test_count": 1170, "passed_count": 1169, "skipped_count": 1, "elapsed_seconds": 3.0, "previously_consumed_seconds": 2.0}
    certificate = {"schema_version": "ball_crop_cross_detector_corroboration_release_implementation/v0.1",
                   "scope": manifest["scope"], "stage1_validation": scope["stage1_validation"],
                   "source_bindings": absolute_bindings,
                   "focused_result": put(root, release.ADMIN_ROOT + "/focused_01_result.json", focused),
                   "full_result": put(root, release.ADMIN_ROOT + "/full_01_result.json", full), "approval": approval}
    certificate["validation_results"] = [certificate["focused_result"], certificate["full_result"]]
    for kind in ("focused", "full"):
        put(root, release.ADMIN_ROOT + f"/{kind}_01_started.json", {"artificial_only": True})
    manifest["implementation_validation"] = put(root, release.CERTIFICATE_PATH, certificate)
    return scope, manifest, certificate, bindings


def extended_certificate_fixture(root):
    """Invent four consumed checks and an explicit additive grant, all in TEMP."""
    scope, manifest, certificate, _ = certificate_fixture(root)
    templates = {kind: json.loads((root / certificate[kind + "_result"]["path"]).read_text())
                 for kind in ("focused", "full")}
    consumed, prior = 0.0, []
    for name, elapsed, success in (("focused_01", 20.0, False), ("focused_02", 25.0, True),
                                   ("full_01", 2075.594000000001, False), ("focused_03", 25.0, True)):
        kind = name.split("_")[0]
        receipt = {**templates[kind], "success": success, "returncode": 0 if success else 1,
                   "failure": None if success else "Artificial preserved failed attempt",
                   "elapsed_seconds": elapsed, "previously_consumed_seconds": consumed}
        prior.append(put(root, release.ADMIN_ROOT + f"/{name}_result.json", receipt))
        put(root, release.ADMIN_ROOT + f"/{name}_started.json", {"artificial_only": True})
        consumed += elapsed
    proposal = put(root, release.ADMIN_ROOT + "/correction_and_validation_extension_proposal.json",
                   {"artificial_only": True, "additional_seconds": 600})
    grant = {
        "schema_version": "ball_crop_corroboration_release_validation_extension_approval/v0.1",
        "status": "approved_additive_artificial_validation_allowance", "approved_by": "Ryan",
        "user_statement": "Artificial approval fixture only.", "proposal": proposal,
        "implementation_approval": certificate["approval"], "scope": certificate["scope"],
        "base_budget_seconds": 4200, "additional_seconds": 600, "cumulative_budget_seconds": 4800,
        "consumed_seconds_at_approval": consumed, "prior_validation_results": prior,
        "maximum_focused_seconds": 600, "maximum_full_seconds": 3600,
        "resource_limits_unchanged": {"sampled_memory_bytes": 8 * 1024**3, "minimum_free_disk_bytes": 50 * 1024**3,
                                      "counted_validation_output_bytes": 4 * 1024**3},
        "implementation_files": ["src/ball_tracking/crop_cross_detector_corroboration_release.py",
                                 "tests/test_ball_crop_cross_detector_corroboration_release.py"],
        "prior_validation_consumed_seconds_preserved": ["2164.2970000000005", "2295.467999999999"],
        "fresh_allowance_or_budget_reset": False, "scientific_execution_authorized": False,
        "scientific_body_access_authorized": False, "real_resource_journal_access_authorized": False,
        "new_media_presentation_authorized": False, "runtime_execution_authority_creation_authorized": False,
        "git_mutations_authorized": False}
    grant_binding = put(root, release.ADMIN_ROOT + "/validation_extension_approval.json", grant)
    for kind, name, elapsed in (("focused", "focused_04", 10.0), ("full", "full_02", 2300.0)):
        receipt = {**templates[kind], "elapsed_seconds": elapsed, "previously_consumed_seconds": consumed,
                   "validation_extension": grant_binding, "validation_extension_after": grant_binding,
                   "cumulative_validation_budget_seconds": 4800}
        certificate[kind + "_result"] = put(root, release.ADMIN_ROOT + f"/{name}_result.json", receipt)
        put(root, release.ADMIN_ROOT + f"/{name}_started.json", {"artificial_only": True})
        consumed += elapsed
    certificate["validation_extension"] = grant_binding
    certificate["validation_results"] = prior + [certificate["focused_result"], certificate["full_result"]]
    manifest["implementation_validation"] = put(root, release.CERTIFICATE_PATH, certificate)
    return scope, manifest, certificate, grant


class PreservationMetadataTests(TemporaryRoot):
    def context(self):
        base = release.OUTPUT_ROOT
        names = [base + "/old.bin", base + "/audit/previous/final.png"]
        for name in names:
            put(self.root, name, b"artificial preserved evidence")
        external = []
        for index in range(18):
            row = put(self.root, f"data/synthetic/external_review_{index:02d}.json", {"artificial_only": True})
            external.append({"path": row["path"], **stat_metadata(self.root / row["path"])})
        (self.root / base / "sealed/empty").mkdir(parents=True)
        directories = [base, base + "/audit", base + "/audit/previous", base + "/sealed", base + "/sealed/empty"]
        absent = [f"data/synthetic/embargo_{index}.json" for index in range(9)]
        return {"root": self.root,
                "history": {"preserved_files": [{"path": name, **stat_metadata(self.root / name)} for name in names],
                            "preserved_directories": directories, "external_preserved_files": external,
                            "protection": {"sealed_holdouts_metadata_only": [{"window_id": f"synthetic_holdout_{index}"} for index in range(3)],
                                           "preserved_absent_paths": absent}},
                "scope": {"preserved_history": {"resource_event_count": 3330},
                          "prediction_embargoes": absent,
                          "outputs": {"files": [{"path": "summary.json", "maximum_bytes": 1024}]}}}

    def append_owned(self, attempt, *, complete=False):
        base = release.OUTPUT_ROOT
        suffixes = (".reservation.json", ".monitoring_policy.json", ".log", ".start")
        if complete:
            suffixes += (".completion.json", ".result.json")
        for suffix in suffixes:
            put(self.root, base + "/attempts/" + attempt + suffix, b"artificial administrative record")
        put(self.root, base + "/resource_events/00003330.json", b"artificial resource suffix")

    def test_inventory_is_complete_and_metadata_only_including_empty_directories(self):
        context = self.context()
        with patch.object(Path, "open", side_effect=AssertionError("preserved scientific body read")):
            release._preserved(context)
            for rows in ([], context["history"]["preserved_files"][:1]):
                partial = copy.deepcopy(context)
                partial["history"]["preserved_files"] = rows
                with self.subTest(rows=len(rows)), self.assertRaises(ValueError):
                    release._preserved(partial)
            partial = copy.deepcopy(context)
            partial["history"]["preserved_directories"] = partial["history"]["preserved_directories"][:-1]
            with self.assertRaises(ValueError):
                release._preserved(partial)
        put(self.root, release.OUTPUT_ROOT + "/unlisted_old_evidence.bin", b"artificial unlisted evidence")
        with self.assertRaises(ValueError):
            release._preserved(context)

    def test_old_metadata_change_is_rejected_in_every_phase(self):
        context = self.context()
        put(self.root, context["history"]["preserved_files"][1]["path"], b"changed artificial final frame")
        for phase in ("before", "worker", "completed"):
            with self.subTest(phase=phase), patch.object(Path, "open", side_effect=AssertionError("old body read")), self.assertRaises(ValueError):
                release._preserved(context, phase, None if phase == "before" else "a" * 32)

    def test_worker_allows_only_its_exact_attempt_and_contiguous_suffix(self):
        context = self.context()
        attempt = "a" * 32
        self.append_owned(attempt)
        put(self.root, release.OUTPUT_ROOT + "/supervisor.lock", b"artificial live-owner metadata")
        with patch.object(Path, "open", side_effect=AssertionError("worker preservation read")):
            release._preserved(context, "worker", attempt)
        put(self.root, release.OUTPUT_ROOT + "/attempts/" + "b" * 32 + ".result.json", b"unrelated attempt")
        with self.assertRaises(ValueError):
            release._preserved(context, "worker", attempt)

    def test_completion_requires_full_outputs_and_refuses_undeclared_additions(self):
        context = self.context()
        attempt = "a" * 32
        self.append_owned(attempt, complete=True)
        with self.assertRaises(ValueError):
            release._preserved(context, "completed", attempt)
        put(self.root, release.OUTPUT_DIR + "/summary.json", b"artificial complete summary")
        with patch.object(Path, "open", side_effect=AssertionError("completed preservation body read")):
            release._preserved(context, "completed", attempt)
        put(self.root, release.OUTPUT_DIR + "/unapproved.json", b"extra output")
        with self.assertRaises(ValueError):
            release._preserved(context, "completed", attempt)

    def test_new_resource_suffix_cannot_skip_a_consumed_event_index(self):
        context = self.context()
        attempt = "a" * 32
        self.append_owned(attempt)
        put(self.root, release.OUTPUT_ROOT + "/resource_events/00003332.json", b"artificial skipped index")
        with self.assertRaisesRegex(ValueError, "Noncontiguous"):
            release._preserved(context, "worker", attempt)

    def test_external_review_metadata_and_prediction_embargoes_remain_closed(self):
        context = self.context()
        for phase in ("before", "worker", "completed"):
            modified = copy.deepcopy(context)
            modified["history"]["external_preserved_files"][0]["size_bytes"] += 1
            with self.subTest(phase=phase), patch.object(Path, "open", side_effect=AssertionError("external review body read")), self.assertRaises(ValueError):
                release._preserved(modified, phase, None if phase == "before" else "a" * 32)
        put(self.root, context["scope"]["prediction_embargoes"][0], b"artificial forbidden prediction")
        with self.assertRaisesRegex(ValueError, "Protected absent"):
            release._preserved(context)

    def test_frozen_history_retains_pinned_external_reviews_and_all_636_mean_artifacts(self):
        context = self.context()
        old = {**copy.deepcopy(context["history"]), "schema_version": "ball_crop_path_confidence_mean_frozen_history/v0.1",
               "human_review_bindings": [{"path": "data/synthetic/review_approval.json", "sha256": "a" * 64, "size_bytes": 1}],
               "administrative_attempt_bindings": [
                   {"path": "data/synthetic/representative.result.json", "sha256": "d" * 64, "size_bytes": 120078},
                   {"path": "data/synthetic/representative.reservation.json", "sha256": "e" * 64, "size_bytes": 1}]}
        mean_rows = [{"path": release.OUTPUT_ROOT + f"/audit/mean/artificial_{index:03d}.png",
                      "size_bytes": 1, "mtime_ns": 1, "device": 1, "inode": index + 100} for index in range(636)]
        mean = {"artifact_metadata": mean_rows, "artifacts": [{"path": row["path"], "size_bytes": 1, "sha256": "b" * 64} for row in mean_rows]}
        frozen = copy.deepcopy(context["history"])
        frozen["preserved_files"] += mean_rows
        binding = {"path": release.MEAN_RESULT, "sha256": "c" * 64, "size_bytes": 1}
        scope = {"administrative_binding_sources": [binding]}
        opened = []

        def read_admin(root, bound, **kwargs):
            opened.append(bound)
            if bound == release.PRIOR_HISTORY:
                return encoded(old)
            if bound == binding:
                return encoded(mean)
            if bound == old["human_review_bindings"][0]:
                return b"{}"
            if bound == old["administrative_attempt_bindings"][0]:
                self.assertEqual(kwargs["maximum"], release.MAX_RECEIPT_BYTES)
                return b"{}"
            raise AssertionError("Undeclared historical body read")

        with patch.object(release, "_read_bound", side_effect=read_admin), patch.object(Path, "open", side_effect=AssertionError("scientific body read")):
            release._history_authority(self.root, frozen, scope)
            self.assertEqual(opened, [release.PRIOR_HISTORY, binding, old["human_review_bindings"][0],
                                      old["administrative_attempt_bindings"][0]])
            for field in ("external_preserved_files", "preserved_files"):
                altered = copy.deepcopy(frozen)
                altered[field] = altered[field][:-1]
                with self.subTest(field=field), self.assertRaises(ValueError):
                    release._history_authority(self.root, altered, scope)


class AuthorityAndTransportTests(TemporaryRoot):
    def test_absent_future_release_refuses_before_dispatch_or_scientific_access(self):
        with patch.object(release.monitor, "run_supervised", side_effect=AssertionError("production launch")), \
                patch.object(release, "_read_bound", side_effect=AssertionError("unauthorized body read")), \
                patch.object(release, "_git", side_effect=AssertionError("unnecessary Git invocation")):
            with self.assertRaises(PermissionError):
                release.run_study(self.root)

    def test_runtime_manifest_cannot_change_study_scope_or_assert_a_selected_method(self):
        manifest = artificial_manifest()
        release._validate_manifest(manifest)
        for change in ({"study_id": "another-study"}, {"selected_method": "corroborated"},
                       {"scope": {"path": release.SCOPE_PATH, "sha256": "0" * 64}},
                       {"post_commit_checkpoint": "data/synthetic/fake.json"}, {"force": True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                release._validate_manifest({**manifest, **change})

    def test_oversized_runtime_manifest_is_refused_before_opening_its_body(self):
        put(self.root, release.MANIFEST_PATH, b" " * (1024**2 + 1))
        with patch.object(Path, "open", side_effect=AssertionError("oversized manifest body read")), \
                patch.object(release, "_git", side_effect=AssertionError("oversized manifest reached Git")), \
                self.assertRaises(ValueError):
            release._metadata(self.root)

    def _admin_gate(self, dirty=False, committed=True):
        scope, manifest = administrative_scope(), artificial_manifest()
        put(self.root, release.MANIFEST_PATH, manifest)
        approval = {"schema_version": "ball_crop_corroboration_execution_approval/v0.1", "study_id": release.ID,
                    "approved_by": "Ryan", "scope": manifest["scope"], "proposal": manifest["proposal"],
                    "scientific_execution_authorized": True, "administrative_history_verification_authorized": True,
                    "new_verified_media_presentation_authorized": True, "release_checkpoint_authorized": True,
                    "user_statement": "Artificial authorization fixture only."}

        def read_admin(root, binding, **kwargs):
            if binding["path"] == release.SCOPE_PATH:
                return encoded(scope)
            if binding["path"] == release.PROPOSAL_PATH:
                return b"Artificial prose fixture."
            if binding["path"] == release.APPROVAL_PATH:
                return encoded(approval)
            raise AssertionError("Dirty/uncommitted release reached later body access")

        def git(root, *args):
            if args[0] == "status":
                return "?? src/new_release.py" if dirty else ""
            if args[:2] == ("rev-parse", "HEAD"):
                return COMMIT
            if args[0] == "branch":
                return "codex/artificial-release"
            if args[0] == "merge-base":
                return ""
            if args[0] == "ls-files":
                return args[-1] if committed else ""
            raise AssertionError(f"Unexpected Git inspection {args}")
        return read_admin, git

    def test_dirty_and_uncommitted_release_checkpoints_fail_before_science(self):
        for dirty, committed in ((True, True), (False, False)):
            reader, git = self._admin_gate(dirty, committed)
            with patch.object(release, "_read_bound", side_effect=reader), patch.object(release, "_git", side_effect=git), \
                    patch.object(release, "_certificate", side_effect=AssertionError("must stop before certificate")), \
                    self.subTest(dirty=dirty, committed=committed), self.assertRaises(ValueError):
                release._metadata(self.root)

    def test_clean_checkpoint_requires_every_certified_source_and_preserved_path_tracked(self):
        scope = administrative_scope()
        sources = [{"path": f"src/artificial_{index:03d}.py", "sha256": "a" * 64, "size_bytes": 1} for index in range(187)]
        names = {row["path"] for row in sources + scope["preserved_worktree_bindings"]}
        names.update((release.MANIFEST_PATH, release.APPROVAL_PATH, release.SCOPE_PATH, release.PROPOSAL_PATH))
        for missing in (sources[90]["path"], scope["preserved_worktree_bindings"][0]["path"]):
            reader, original_git = self._admin_gate()

            def git(root, *args):
                return "\n".join(sorted(names - {missing})) if args == ("ls-files",) else original_git(root, *args)

            with patch.object(release, "_read_bound", side_effect=reader), patch.object(release, "_git", side_effect=git), \
                    patch.object(release, "_certificate", return_value={"source_bindings": sources}), \
                    patch.object(release, "_require_tracked", wraps=release._require_tracked) as required, \
                    self.subTest(missing=missing), self.assertRaisesRegex(ValueError, "All tested source"):
                release._metadata(self.root)
            self.assertEqual(set(required.call_args.args[1]), names)

    def test_worker_gate_blocks_before_manifest_history_and_source_access(self):
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(resources, "wait_for_supervisor", side_effect=AssertionError("unowned gate wait")), \
                patch.object(release, "_metadata", side_effect=AssertionError("unowned metadata access")), \
                self.assertRaises(ValueError):
            release._worker(self.root)

    def test_validated_worker_paths_wait_for_start_gate_before_requiring_ownership(self):
        order = []
        with patch.object(release, "_owned_paths", side_effect=lambda *_: order.append("exact_paths")), \
                patch.object(resources, "wait_for_supervisor", side_effect=lambda: order.append("wait_for_gate")), \
                patch.object(release, "_ownership", side_effect=lambda *_: order.append("ownership")), \
                patch.object(release, "_metadata", side_effect=RuntimeError("artificial stop before authority")):
            with self.assertRaisesRegex(RuntimeError, "artificial stop"):
                release._worker(self.root)
        self.assertEqual(order, ["exact_paths", "wait_for_gate", "ownership"])

    def test_owned_worker_wires_running_preservation_on_both_sides_of_comparison(self):
        attempt, order = "a" * 32, []
        receipt = self.root / release.OUTPUT_ROOT / "attempts" / (attempt + ".result.json")
        receipt.parent.mkdir(parents=True)
        context = {"root": self.root, "scope": {"artificial_orchestration_only": True}, "limits": {},
                   "output_root": self.root / release.OUTPUT_ROOT, "commit": COMMIT,
                   "manifest_binding": {"path": release.MANIFEST_PATH, "sha256": "a" * 64}}
        journal = SimpleNamespace(_attempts=lambda: {attempt: {"start": {"reserved_seconds": 1200}}})
        access, sink = object(), object()
        worker_result = {"artificial_orchestration_only": True, "attempt_id": attempt}

        def metadata(*_):
            order.append("authority")
            return context

        def preserved(observed, phase="before", attempt_id=None):
            self.assertIs(observed, context)
            self.assertEqual((phase, attempt_id), ("worker", attempt))
            self.assertFalse(receipt.exists())
            order.append("worker_preservation")

        def comparison(scope, observed_access, observed_sink, commit, *, progress):
            self.assertIs(scope, context["scope"])
            self.assertIs(observed_access, access)
            self.assertIs(observed_sink, sink)
            self.assertEqual(commit, COMMIT)
            order.append("comparison")
            progress()
            return worker_result

        with patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": attempt}, clear=True), \
                patch.object(release, "_owned_paths", side_effect=lambda *_: order.append("exact_paths")), \
                patch.object(resources, "wait_for_supervisor", side_effect=lambda: order.append("wait_for_gate")), \
                patch.object(release, "_ownership", side_effect=lambda *_: order.append("ownership")), \
                patch.object(release, "_metadata", side_effect=metadata), \
                patch.object(resources, "BudgetJournal", return_value=journal), \
                patch.object(release, "verify_history", side_effect=lambda *args: order.append(("history", args[2], args[3]))), \
                patch.object(release, "_preserved", side_effect=preserved), \
                patch.object(release, "PhaseAccess", return_value=access), \
                patch.object(release, "OutputSink", return_value=sink), \
                patch.object(release, "run_comparison", side_effect=comparison), \
                patch.object(release.monitor, "run_supervised", side_effect=AssertionError("unapproved production launch")):
            result = release._worker(self.root)
        self.assertEqual(result, {"worker_result_written": True, "attempt_id": attempt})
        self.assertEqual(json.loads(receipt.read_text()), worker_result)
        self.assertEqual(order, ["exact_paths", "wait_for_gate", "ownership", "authority",
                                 ("history", "worker", attempt), "worker_preservation", "comparison", "ownership",
                                 "authority", ("history", "worker", attempt), "worker_preservation"])

    def test_worker_identity_cannot_use_another_result_path_or_dead_supervisor(self):
        ident = "a" * 32
        base = self.root / release.OUTPUT_ROOT / "attempts" / ident
        base.parent.mkdir(parents=True)
        Path(str(base) + ".start").write_bytes(b"owned-test-start")
        put(self.root, release.OUTPUT_ROOT + "/supervisor.lock", {"pid": os.getppid(), "token": "artificial"})
        environment = {"BALL_RETENTION_ATTEMPT_ID": ident, "BALL_RETENTION_START_GATE": str(base) + ".start",
                       "BALL_RETENTION_RESULT_PATH": str(base) + ".result.json",
                       "BALL_RETENTION_PARENT_PID": str(os.getppid())}
        with patch.dict(os.environ, {**environment, "BALL_RETENTION_RESULT_PATH": str(base) + ".wrong.json"}, clear=True), self.assertRaises(ValueError):
            release._ownership(self.root, ident)
        with patch.dict(os.environ, environment, clear=True), patch.object(resources, "_alive", return_value=False), self.assertRaises(ValueError):
            release._ownership(self.root, ident)

    def ownership_fixture(self, *, released=True):
        attempt, supervisor = "a" * 32, 32123
        base = self.root / release.OUTPUT_ROOT / "attempts" / attempt
        base.parent.mkdir(parents=True)
        if released:
            Path(str(base) + ".start").write_bytes(b"artificial released gate")
        put(self.root, release.OUTPUT_ROOT + "/supervisor.lock", {"pid": supervisor, "token": "artificial"})
        environment = {"BALL_RETENTION_ATTEMPT_ID": attempt, "BALL_RETENTION_START_GATE": str(base) + ".start",
                       "BALL_RETENTION_RESULT_PATH": str(base) + ".result.json", "BALL_RETENTION_PARENT_PID": str(supervisor)}
        return attempt, supervisor, base, environment

    def test_redirected_worker_accepts_live_injected_supervisor_when_immediate_parent_differs(self):
        attempt, supervisor, _, environment = self.ownership_fixture()
        with patch.dict(os.environ, environment, clear=True), patch.object(os, "getppid", return_value=supervisor + 1), \
                patch.object(resources, "_alive", return_value=True) as alive, \
                patch.object(release, "_metadata", side_effect=AssertionError("ownership entered metadata")):
            release._ownership(self.root, attempt)
        alive.assert_called_once_with(supervisor)

    def test_worker_rejects_missing_malformed_or_mismatched_injected_supervisor(self):
        attempt, supervisor, _, environment = self.ownership_fixture()
        for value in (None, "", "0", "-1", "abc", "1.5", "+32123", " 32123", "032123", str(supervisor + 1)):
            altered = dict(environment)
            if value is None:
                altered.pop("BALL_RETENTION_PARENT_PID")
            else:
                altered["BALL_RETENTION_PARENT_PID"] = value
            with self.subTest(parent=value), patch.dict(os.environ, altered, clear=True), \
                    patch.object(resources, "_alive", return_value=True), self.assertRaises(ValueError):
                release._ownership(self.root, attempt)

    def test_worker_rejects_unreleased_gate_and_wrong_exact_gate_with_live_owner(self):
        attempt, _, base, environment = self.ownership_fixture(released=False)
        with patch.dict(os.environ, environment, clear=True), patch.object(resources, "_alive", return_value=True), self.assertRaises(ValueError):
            release._ownership(self.root, attempt)
        wrong_gate = Path(str(base) + ".wrong.start")
        wrong_gate.write_bytes(b"artificial unrelated released gate")
        with patch.dict(os.environ, {**environment, "BALL_RETENTION_START_GATE": str(wrong_gate)}, clear=True), \
                patch.object(resources, "_alive", return_value=True), self.assertRaises(ValueError):
            release._ownership(self.root, attempt)

    @unittest.skipUnless(os.name == "nt", "Windows virtual-environment owned launch")
    def test_windows_virtualenv_owned_ownership_smoke_records_topology_and_cleanup(self):
        started = time.monotonic()
        python = ROOT / ".venv" / "Scripts" / "python.exe"
        self.assertTrue(python.is_file(), "The actual repository virtual-environment launcher is required")
        attempt = "a" * 32
        base = self.root / release.OUTPUT_ROOT / "attempts" / attempt
        base.parent.mkdir(parents=True)
        gate, result_path = Path(str(base) + ".start"), Path(str(base) + ".result.json")
        put(self.root, release.OUTPUT_ROOT + "/supervisor.lock", {"pid": os.getpid(), "token": "artificial-smoke"})
        environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "BALL_RETENTION_ATTEMPT_ID": attempt,
                       "BALL_RETENTION_PARENT_PID": str(os.getpid()), "BALL_RETENTION_START_GATE": str(gate),
                       "BALL_RETENTION_RESULT_PATH": str(result_path)}
        # This child calls only the ownership entry checks. Metadata, budget
        # journals and scientific access are explicit failure sentinels.
        code = """import json, os, sys, time
from pathlib import Path
from src.ball_tracking import crop_cross_detector_corroboration_release as release
from src.ball_tracking import crop_retention_resources as resources
def forbidden(*args, **kwargs):
    raise AssertionError('ownership smoke crossed into metadata, journal or science')
release._metadata = forbidden
resources.BudgetJournal = forbidden
release.PhaseAccess = forbidden
root = Path(sys.argv[1]).resolve()
attempt = os.environ['BALL_RETENTION_ATTEMPT_ID']
release._owned_paths(root, attempt)
resources.wait_for_supervisor()
release._ownership(root, attempt)
lock = json.loads((root / release.OUTPUT_ROOT / 'supervisor.lock').read_text())
record = {'worker_pid': os.getpid(), 'worker_ppid': os.getppid(),
          'injected_supervisor_pid': int(os.environ['BALL_RETENTION_PARENT_PID']),
          'lock_pid': lock['pid'], 'stopped_before_metadata_journal_science': True}
resources._write_new(Path(os.environ['BALL_RETENTION_RESULT_PATH']), record)
# Stay in the owned Job until the test verifies membership and terminates it.
deadline = time.monotonic() + 20
while time.monotonic() < deadline:
    time.sleep(.025)
raise RuntimeError('ownership smoke parent did not clean up its child')
"""
        process, job, value, owned, cleanup_verified = None, None, None, [], False
        log_path = self.root / "ownership-smoke.log"
        try:
            with log_path.open("xb") as log:
                process, job = release.monitor._spawn_owned(
                    [str(python), "-B", "-u", "-c", code, str(self.root)],
                    commit_limit_bytes=512 * 1024**2, cwd=ROOT, env=environment,
                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
                gate.touch(exist_ok=False)
                deadline = started + 24.0
                while not result_path.is_file() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(.025)
                self.assertTrue(result_path.is_file(), "Owned virtual-environment probe did not complete its ownership check")
                with result_path.open("rb") as stream:
                    raw = stream.read(16385)
                self.assertLessEqual(len(raw), 16384)
                value = json.loads(raw)
                owned = sorted(job.pids())
                self.assertIn(value["worker_pid"], owned)
                self.assertIn(process.pid, owned)
                self.assertEqual(value["injected_supervisor_pid"], os.getpid())
                self.assertEqual(value["lock_pid"], os.getpid())
                self.assertTrue(value["stopped_before_metadata_journal_science"])
                if value["worker_pid"] != process.pid:
                    self.assertEqual(value["worker_ppid"], process.pid)
        finally:
            if process is not None or job is not None:
                # The unchanged helper kills the full Job, verifies empty
                # membership and process exit within one second, then closes it.
                release.monitor._terminate(process, job)
                cleanup_verified = process is not None and process.poll() is not None
                if value is not None:
                    cleanup_verified = cleanup_verified and not resources._alive(value["worker_pid"])
                self.assertTrue(cleanup_verified, "Owned smoke cleanup did not verify")
        self.assertLess(time.monotonic() - started, 30.0)
        audit = {**value, "launcher_pid": process.pid, "python_path": str(python), "artificial_root": str(self.root),
                 "owned_pids_before_cleanup": owned, "cleanup_verified": cleanup_verified,
                 "immediate_parent_differs_from_injected": value["worker_ppid"] != value["injected_supervisor_pid"],
                 "elapsed_seconds": round(time.monotonic() - started, 6)}
        print("PDS_OWNERSHIP_SMOKE " + json.dumps(audit, sort_keys=True, separators=(",", ":")), flush=True)

    def test_complete_source_certificate_passes_and_changed_source_bytes_fail(self):
        scope, manifest, certificate, bindings = certificate_fixture(self.root)
        self.assertEqual(bindings[0]["size_bytes"], 0)
        self.assertEqual(bindings[0]["sha256"], hashlib.sha256(b"").hexdigest())
        self.assertEqual(release._certificate(self.root, manifest, scope), certificate)
        (self.root / bindings[0]["path"]).write_bytes(b"# Formerly empty source changed after testing.\n")
        with self.assertRaises(ValueError):
            release._certificate(self.root, manifest, scope)

    def test_certificate_rejects_false_counts_cleanup_or_retested_source_linkage(self):
        scope, manifest, certificate, _ = certificate_fixture(self.root)
        original = json.loads((self.root / certificate["full_result"]["path"]).read_text())
        for change in ({"passed_count": 1168}, {"owned_cleanup_verified": False},
                       {"source_bindings_after": []}, {"previously_consumed_seconds": 0.0},
                       {"elapsed_seconds": 4201.0}, {"approval_after": {**certificate["approval"], "sha256": "0" * 64}},
                       {"preservation_error": "preserved bytes changed"}, {"preserved_worktree_bindings_before": []},
                       {"preserved_worktree_bindings_after": original["preserved_worktree_bindings_after"][:-1]}):
            modified = {**original, **change}
            certificate["full_result"] = put(self.root, certificate["full_result"]["path"], modified)
            certificate["validation_results"] = [certificate["focused_result"], certificate["full_result"]]
            manifest["implementation_validation"] = put(self.root, release.CERTIFICATE_PATH, certificate)
            with self.subTest(change=change), self.assertRaises(ValueError):
                release._certificate(self.root, manifest, scope)

    def test_certificate_requires_all_187_source_paths_and_all_18_preserved_bytes(self):
        scope, manifest, certificate, _ = certificate_fixture(self.root)
        missing = copy.deepcopy(certificate)
        missing["source_bindings"] = missing["source_bindings"][:-1]
        manifest["implementation_validation"] = put(self.root, release.CERTIFICATE_PATH, missing)
        with self.assertRaises(ValueError):
            release._certificate(self.root, manifest, scope)
        manifest["implementation_validation"] = put(self.root, release.CERTIFICATE_PATH, certificate)
        put(self.root, scope["preserved_worktree_bindings"][7]["path"], b"preserved bytes altered")
        with self.assertRaises(ValueError):
            release._certificate(self.root, manifest, scope)

    def test_resealed_approval_cannot_expand_implementation_authority_or_erase_prior_budgets(self):
        scope, manifest, certificate, _ = certificate_fixture(self.root)
        approval = json.loads((self.root / certificate["approval"]["path"]).read_text())
        receipts = {kind: json.loads((self.root / certificate[kind + "_result"]["path"]).read_text()) for kind in ("focused", "full")}
        for change in ({"scientific_execution_authorized": True}, {"commit_authorized": True},
                       {"artificial_validation_budget_seconds": 4201},
                       {"prior_validation_consumed_seconds_preserved": ["0", "0"]},
                       {"preserved_worktree_bindings": approval["preserved_worktree_bindings"][:-1]}):
            candidate = copy.deepcopy(certificate)
            candidate["approval"] = put(self.root, candidate["approval"]["path"], {**approval, **change})
            for kind in ("focused", "full"):
                receipt = {**receipts[kind], "approval": candidate["approval"], "approval_after": candidate["approval"]}
                candidate[kind + "_result"] = put(self.root, candidate[kind + "_result"]["path"], receipt)
            candidate["validation_results"] = [candidate["focused_result"], candidate["full_result"]]
            manifest["implementation_validation"] = put(self.root, release.CERTIFICATE_PATH, candidate)
            with self.subTest(change=change), self.assertRaises(ValueError):
                release._certificate(self.root, manifest, scope)

    def test_certificate_charges_failed_validation_before_successful_rechecks(self):
        scope, manifest, certificate, _ = certificate_fixture(self.root)
        failed = put(self.root, release.ADMIN_ROOT + "/focused_00_result.json",
                     {"success": False, "elapsed_seconds": 7.0, "previously_consumed_seconds": 0.0})
        put(self.root, release.ADMIN_ROOT + "/focused_00_started.json", {"artificial_only": True})
        for kind, previous in (("focused", 7.0), ("full", 9.0)):
            receipt = json.loads((self.root / certificate[kind + "_result"]["path"]).read_text())
            receipt["previously_consumed_seconds"] = previous
            certificate[kind + "_result"] = put(self.root, certificate[kind + "_result"]["path"], receipt)
        certificate["validation_results"] = [failed, certificate["focused_result"], certificate["full_result"]]
        manifest["implementation_validation"] = put(self.root, release.CERTIFICATE_PATH, certificate)
        self.assertEqual(release._certificate(self.root, manifest, scope), certificate)
        certificate["validation_results"] = certificate["validation_results"][1:]
        manifest["implementation_validation"] = put(self.root, release.CERTIFICATE_PATH, certificate)
        with self.assertRaises(ValueError):
            release._certificate(self.root, manifest, scope)

    def test_certificate_cannot_adopt_unfinished_validation_or_ignore_new_result(self):
        scope, manifest, certificate, _ = certificate_fixture(self.root)
        put(self.root, release.ADMIN_ROOT + "/focused_02_started.json", {"artificial_only": True})
        with self.assertRaises(ValueError):
            release._certificate(self.root, manifest, scope)
        put(self.root, release.ADMIN_ROOT + "/focused_02_result.json",
            {"success": False, "elapsed_seconds": 1.0, "previously_consumed_seconds": 5.0})
        with self.assertRaises(ValueError):
            release._certificate(self.root, manifest, scope)

    def test_missing_or_forged_additive_grant_cannot_extend_the_original_budget(self):
        scope, manifest, certificate, _ = extended_certificate_fixture(self.root)
        grant_binding = certificate["validation_extension"]
        with patch.object(release, "VALIDATION_EXTENSION_BINDING", grant_binding):
            release._certificate(self.root, manifest, scope)
            for extension in (None, {**grant_binding, "sha256": "0" * 64},
                              {**grant_binding, "path": release.ADMIN_ROOT + "/unapproved_extension.json"}):
                altered = copy.deepcopy(certificate)
                if extension is None:
                    altered.pop("validation_extension")
                else:
                    altered["validation_extension"] = extension
                manifest["implementation_validation"] = put(self.root, release.CERTIFICATE_PATH, altered)
                with self.subTest(extension=extension), self.assertRaises(ValueError):
                    release._certificate(self.root, manifest, scope)

    def test_additive_grant_retains_failed_consumption_and_links_both_latest_receipts(self):
        scope, manifest, certificate, grant = extended_certificate_fixture(self.root)
        grant_binding = certificate["validation_extension"]
        originals = {kind: json.loads((self.root / certificate[kind + "_result"]["path"]).read_text())
                     for kind in ("focused", "full")}
        prior = [json.loads((self.root / row["path"]).read_text()) for row in grant["prior_validation_results"]]
        self.assertEqual(len(prior), 4)
        self.assertEqual(sum(row["success"] is False for row in prior), 2)
        self.assertAlmostEqual(sum(row["elapsed_seconds"] for row in prior), 2145.594000000001)
        self.assertGreater(originals["full"]["previously_consumed_seconds"] + originals["full"]["elapsed_seconds"], 4200)
        with patch.object(release, "VALIDATION_EXTENSION_BINDING", grant_binding):
            self.assertEqual(release._certificate(self.root, manifest, scope), certificate)
            missing_prior = copy.deepcopy(certificate)
            missing_prior["validation_results"] = missing_prior["validation_results"][1:]
            manifest["implementation_validation"] = put(self.root, release.CERTIFICATE_PATH, missing_prior)
            with self.assertRaises(ValueError):
                release._certificate(self.root, manifest, scope)
            for kind, change in (("focused", {"validation_extension_after": None}),
                                 ("full", {"validation_extension": {**grant_binding, "sha256": "0" * 64}}),
                                 ("full", {"validation_extension_after": {**grant_binding, "sha256": "0" * 64}}),
                                 ("full", {"cumulative_validation_budget_seconds": 4200}),
                                 ("full", {"previously_consumed_seconds": 0.0}),
                                 ("full", {"elapsed_seconds": 2660.0})):
                altered = copy.deepcopy(certificate)
                for reset_kind in ("focused", "full"):
                    receipt = {**originals[reset_kind], **(change if reset_kind == kind else {})}
                    altered[reset_kind + "_result"] = put(self.root, altered[reset_kind + "_result"]["path"], receipt)
                altered["validation_results"] = grant["prior_validation_results"] + [altered["focused_result"], altered["full_result"]]
                manifest["implementation_validation"] = put(self.root, release.CERTIFICATE_PATH, altered)
                with self.subTest(kind=kind, change=change), self.assertRaises(ValueError):
                    release._certificate(self.root, manifest, scope)

    def test_entire_parent_return_is_bounded_including_artifacts(self):
        result = {"schema_version": "artificial", "study_id": release.ID, "attempt_id": None,
                  "unit_key": release.UNIT_KEY, "commit": COMMIT, "scope_content_sha256": "e" * 64,
                  "summary": {}, "artifacts": [], "scientific_input_count": 190, "artificial_only": True}
        self.assertLess(len(encoded(release.parent_return(result))), release.MAX_RETURN_BYTES)
        result["artifacts"] = [{"path": "x" * release.MAX_RETURN_BYTES}]
        with self.assertRaises(ValueError):
            release.parent_return(result)

    def test_oversized_worker_receipt_fails_before_any_artifact_metadata_access(self):
        with patch.object(release, "_stat", side_effect=AssertionError("oversized receipt touched files")), \
                self.assertRaises(ValueError):
            release.validate_return({"artificial_padding": "x" * release.MAX_RECEIPT_BYTES}, {}, "a" * 32)

    def test_parent_summary_must_match_published_summary_hash_and_size_without_body_reads(self):
        scope, _, _, _ = release_fixture(self.root)
        directory = scope["outputs"]["directory"]
        comparisons = []
        for index, window in enumerate(scope["windows"]):
            _, _, _, observations, reports, _ = fixture(count=25, start=window["start_frame_index"],
                purpose=window["purpose"], possession=window["possession_id"],
                hidden=tuple(range(15, 20)) if index == 5 else ())
            comparisons.append(scoring.compare_window(window, reports[scoring.ARM],
                {arm: reports[arm] for arm in scoring.CONTROLS}, observations))
        pools = [scoring.aggregate_pool([row for row in comparisons if row["purpose"] == purpose], purpose) for purpose in scoring.POOLS]
        artifacts = {row["path"]: put(self.root, directory + "/" + row["path"], b"artificial")
                     for row in scope["outputs"]["files"] if row["path"] != "summary.json"}
        reviews = [{"window_id": window["window_id"], "index_binding": artifacts[f"review/{window['window_id']}/review_index.json"],
                    "clip": directory + f"/review/{window['window_id']}/comparison.mp4", "frame_count": 25, "fps": 5,
                    "first_frame_index": window["start_frame_index"], "final_frame_index": window["end_frame_index"], "human_review": "pending"}
                   for window in scope["windows"]]
        summary = release._compact_summary(comparisons, pools, reviews, False)
        artifacts["summary.json"] = put(self.root, directory + "/summary.json", summary)
        result = {"schema_version": "ball_crop_corroboration_worker_result/v0.1", "study_id": release.ID,
                  "attempt_id": "a" * 32, "unit_key": release.UNIT_KEY, "commit": COMMIT,
                  "scope_content_sha256": canonical_sha256(scope), "summary": summary, "scientific_input_count": 190,
                  "scientific_access_log": [{"path": row["path"], "role": row["role"], "phase": phase}
                                            for phase in ("selection", "evaluation", "review")
                                            for row in scope["existing_scientific_files"] if row["first_allowed_phase"] == phase],
                  "artificial_only": False, "artifacts": list(artifacts.values()),
                  "artifact_metadata": [{"path": binding["path"], **stat_metadata(self.root / binding["path"])} for binding in artifacts.values()],
                  "selection_bindings": [artifacts[f"selection/{window['window_id']}/observations.json"] for window in scope["windows"]]}
        context = {"root": self.root, "scope": scope, "commit": COMMIT}
        with patch.object(release, "OUTPUT_DIR", directory), patch.object(release, "_preserved"), \
                patch.object(release, "_read_bound", side_effect=AssertionError("parent body read")), \
                patch.object(Path, "open", side_effect=AssertionError("parent body read")):
            release.validate_return(result, context, "a" * 32)
            changed = copy.deepcopy(result)
            changed["summary"]["interpretation"]["label"] = "unpublished-same-length-or-longer-outcome"
            with self.assertRaises(ValueError):
                release.validate_return(changed, context, "a" * 32)
            changed = copy.deepcopy(result)
            changed["summary"]["unpublished_extra"] = "also forbidden"
            with self.assertRaises(ValueError):
                release.validate_return(changed, context, "a" * 32)

    def test_reparse_ancestor_is_rejected_without_opening_bound_body(self):
        target = self.root / "data" / "synthetic"
        target.mkdir(parents=True)
        put(self.root, "data/synthetic/input.json", {"artificial": True})
        original_lstat = Path.lstat

        def reparse(path):
            observed = original_lstat(path)
            if path == target:
                return SimpleNamespace(st_mode=observed.st_mode, st_file_attributes=0x400)
            return observed

        with patch.object(Path, "lstat", new=reparse), patch.object(Path, "open", side_effect=AssertionError("reparse body open")), self.assertRaises(ValueError):
            release._safe(self.root, "data/synthetic/input.json")


def retry_scope_fixture():
    """Read only the approved planning metadata, never its embedded bodies."""
    return json.loads((ROOT / release.RETRY_SCOPE_PATH).read_text(encoding="utf-8"))


def retry_journal_fixture(root):
    """Invent the failed startup on top of the existing artificial prefix."""
    scope, retry = administrative_scope(), retry_scope_fixture()
    events = artificial_prefix(scope)
    predecessor = release.RETRY_PREDECESSOR
    events += [
        {"kind": "started", "attempt_id": predecessor, "unit_key": release.UNIT_KEY,
         "selection_unit": False, "reserved_seconds": 1200.0, "sha256": "a" * 64},
        {"kind": "sample", "attempt_id": predecessor, "elapsed_seconds": 0.25, "sha256": "b" * 64},
        {"kind": "sample", "attempt_id": predecessor, "elapsed_seconds": 0.5, "sha256": "c" * 64},
        {"kind": "finished", "attempt_id": predecessor, "elapsed_seconds": 1.125,
         "charged_elapsed_seconds": 1.125, "success": False, "failure": "Worker has no live owning supervisor",
         "sha256": retry["retry_design"]["exact_starting_history"]["tip"]}]
    approval = {"artificial_only": True, "user_statement": "Synthetic fixture, never production authority."}
    context = {"root": root, "scope": scope, "retry": retry, "retry_approval": approval,
               "retry_approval_binding": put(root, release.RETRY_APPROVAL_PATH, approval)}
    journal = release.CorroborationRetryJournal.__new__(release.CorroborationRetryJournal)
    journal.root, journal.folder = root, root / "resource_events"
    journal.scope, journal.context, journal.events = scope, context, events
    journal.limits, journal.baseline_bytes = artificial_limits(), release.RETRY_BASELINE_BYTES
    for event in events:
        if event["kind"] in ("started", "finished"):
            suffix = "reservation" if event["kind"] == "started" else "completion"
            put(root, f"attempts/{event['attempt_id']}.{suffix}.json", {"event_sha256": event["sha256"]})
    return journal, context


def retry_receipt_snapshots(root, record, stem):
    for key, rows, infix in (("helper_snapshots", record["helper_bindings"], "_helper_"),
                             ("implementation_snapshots", [row for row in record["source_bindings"]
                                                            if row["path"] in release.RETRY_CHANGED_FILES], "_")):
        record[key] = [put(root, release.RETRY_ADMIN_ROOT + "/" + stem + infix + Path(row["path"]).name,
                           (root / row["path"]).read_bytes()) for row in rows]


def retry_certificate_fixture(root):
    """All historical/current certificate bodies are invented beneath TEMP."""
    scope, _, original_certificate, source_rows = certificate_fixture(root)
    retry = retry_scope_fixture()
    evidence = retry["evidence_reuse"]
    original_binding = put(root, release.CERTIFICATE_PATH, original_certificate)
    before = copy.deepcopy(source_rows)
    old_protected = before + [put(root, f"docs/artificial/ancestor_{i:02d}.txt", b"Artificial preserved ancestor.\n")
                              for i in range(12)]
    old_helper_root = "data/outputs/t/artificial_shutdown"
    old_helpers = [put(root, old_helper_root + "/" + name, ("# Artificial " + name + "\n").encode())
                   for name in ("validate.py", "finalize_validation.py", "lifecycle.py", "test_lifecycle.py")]
    shutdown = {"schema_version": "ball_crop_shutdown_implementation_validation/v0.1",
                "status": "artificial_validation_passed_runtime_authority_unchanged",
                "focused_counts": evidence["accepted_focused_counts"], "full_counts": evidence["accepted_full_counts"],
                "cumulative_validation_seconds": 9589.048999999992,
                "source_bindings": before, "preserved_worktree_bindings": old_protected}
    shutdown_binding = put(root, old_helper_root + "/implementation_validation.json", shutdown)
    for row in evidence["consumption_records"]:
        name = row["binding"]["path"]
        row["binding"] = put(root, name, {key: row[key] for key in
            ("success", "failure", "phase", "elapsed_seconds", "previously_consumed_seconds", "cumulative_seconds")})
    evidence["original_runtime_package"] = [original_binding if row["path"] == release.CERTIFICATE_PATH else row
                                             for row in evidence["original_runtime_package"]]
    evidence["accepted_shutdown_certificate"] = shutdown_binding
    evidence["old_helper_bindings"] = old_helpers
    retry_proposal = put(root, release.RETRY_PROPOSAL_PATH, b"Artificial integration proposal; no production authority.\n")
    retry_binding = put(root, release.RETRY_SCOPE_PATH, retry)
    ancestors = [original_binding, shutdown_binding]
    current = [put(root, row["path"], b"# Changed artificial integration source.\n")
               if row["path"] in release.RETRY_CHANGED_FILES else row for row in before]
    protected = [row for row in old_protected if row["path"] not in release.RETRY_CHANGED_FILES] + [retry_binding, retry_proposal]
    helpers = [put(root, release.RETRY_ADMIN_ROOT + "/" + Path(row["path"]).name,
                   (root / row["path"]).read_bytes()) for row in old_helpers]
    approval = {
        "schema_version": "ball_crop_corroboration_retry_integration_implementation_approval/v0.1",
        "status": "approved_implementation_and_bounded_artificial_validation", "approved_by": "Ryan",
        "user_statement": "Artificial approval fixture only; not authorization for repository work.",
        "head": release.RETRY_BASE_COMMIT, "implementation_files": sorted(release.RETRY_CHANGED_FILES),
        "scope_binding": retry_binding, "proposal_binding": retry_proposal,
        "ancestor_source_bindings": before, "ancestor_certificates": ancestors,
        "ancestor_protected_bindings": old_protected, "prior_consumption_records": evidence["consumption_records"],
        "previously_consumed_seconds": 9589.048999999992, "prior_cap_seconds": 10200,
        "additional_seconds": 2800, "maximum_new_phase_seconds": 2800, "cumulative_validation_budget_seconds": 13000,
        "maximum_focused_invocations": 3, "maximum_focused_seconds": 300,
        "maximum_full_invocations": 1, "maximum_full_seconds": 2500, "closed_remainder_reusable": False,
        "maximum_sampled_memory_bytes": 8 * 1024**3, "maximum_new_output_bytes": 4 * 1024**3,
        "minimum_free_disk_bytes": 50 * 1024**3, "maximum_natural_shutdown_seconds": 1,
        "maximum_forced_cleanup_seconds": 1,
        "prior_validation_consumed_seconds_preserved": ["2164.2970000000005", "2295.467999999999"],
        **{key: True for key in ("implementation_authorized", "repository_source_edits_authorized",
                                "ignored_validator_implementation_authorized", "artificial_validation_authorized")},
        **{key: False for key in ("scientific_body_access_authorized", "scientific_execution_authorized",
                                 "real_resource_journal_replay_authorized", "runtime_authority_or_certificate_replacement_authorized")}}
    approval_binding = put(root, release.RETRY_ADMIN_ROOT + "/approval.json", approval)
    focused_ids = [f"test_ball_crop_cross_detector_corroboration_release.Artificial.test_{i:03d}" for i in range(54)]
    ignored_ids = [f"test_lifecycle.Artificial.test_{i:03d}" for i in range(17)]
    full_ids = sorted(focused_ids + [f"test_artificial.Other.test_{i:04d}" for i in range(1167)])
    inventory = {"schema_version": "ball_crop_corroboration_retry_test_inventory/v0.1", "source_bindings": current,
                 "helper_bindings": helpers, "focused_repository_ids": focused_ids,
                 "ignored_lifecycle_ids": ignored_ids, "full_repository_ids": full_ids}
    inventory_binding = put(root, release.RETRY_ADMIN_ROOT + "/test_inventory.json", inventory)
    counts = {"repository_focused_test_count": 54, "ignored_lifecycle_test_count": 17, "full_test_count": 1221}
    base = {"success": True, "returncode": 0, "failure": None, "driver_exception": None,
            "owned_cleanup_verified": True, "cleanup_errors": [], "final_accounting_error": None,
            "preservation_error": None, "failed_count": 0, "error_count": 0,
            "source_bindings": current, "source_bindings_after": current,
            "helper_bindings": helpers, "helper_bindings_after": helpers,
            "approval": approval_binding, "approval_after": approval_binding,
            "validation_extension": approval_binding, "validation_extension_after": approval_binding,
            "preserved_worktree_bindings_before": protected, "preserved_worktree_bindings_after": protected,
            "cumulative_validation_budget_seconds": 13000, "test_inventory": inventory_binding, "test_counts": counts,
            "peak_rss_bytes": 100, "peak_observed_output_bytes": 100,
            "minimum_free_bytes": 51 * 1024**3, "publication_reserve_bytes": release.monitor.FINAL_RESERVE,
            "shutdown": {"natural_shutdown_success": True, "failure": None, "final_membership": [],
                         "owned_cleanup_verified": True, "cleanup_errors": [], "elapsed_seconds": 0,
                         "natural_shutdown_limit_seconds": 1, "telemetry": {"identity_observation_budget": {
                             "maximum_incident_seconds": .05, "maximum_total_seconds": .25,
                             "failed": False, "consumed_seconds": 0}}}, **counts}
    prior = 9589.048999999992
    focused = {**base, "phase": "focused", "test_count": 71, "passed_count": 71, "skipped_count": 0,
               "elapsed_seconds": 2.0, "previously_consumed_seconds": prior, "timeout_seconds": 300}
    full = {**base, "phase": "full", "test_count": 1221, "passed_count": 1220, "skipped_count": 1,
            "elapsed_seconds": 3.0, "previously_consumed_seconds": prior + 2.0, "timeout_seconds": 2500}
    retry_receipt_snapshots(root, focused, "focused_01")
    retry_receipt_snapshots(root, full, "full_01")
    focused_binding = put(root, release.RETRY_ADMIN_ROOT + "/focused_01_result.json", focused)
    full_binding = put(root, release.RETRY_ADMIN_ROOT + "/full_01_result.json", full)
    for kind in ("focused", "full"):
        put(root, release.RETRY_ADMIN_ROOT + f"/{kind}_01_started.json", {"artificial_only": True})
    cert = {"schema_version": "ball_crop_corroboration_retry_integration_validation/v0.1",
            "status": "artificial_validation_passed_runtime_authority_unchanged", "scope": retry_binding,
            "proposal": retry_proposal, "approval": approval_binding, "ancestor_certificates": ancestors,
            "source_bindings": current, "preserved_worktree_bindings": protected, "helper_bindings": helpers,
            "focused_result": focused_binding, "full_result": full_binding,
            "validation_results": [row["binding"] for row in evidence["consumption_records"]] + [focused_binding, full_binding],
            "test_inventory": inventory_binding, "test_counts": counts,
            "cumulative_validation_seconds": prior + 5.0, "cumulative_validation_cap_seconds": 13000,
            "new_phase_seconds": 5.0, "new_focused_validation_seconds": 2.0, "new_full_invocation_count": 1}
    manifest = {"integration_scope": retry_binding, "integration_proposal": retry_proposal,
                "implementation_validation": put(root, release.RETRY_CERTIFICATE_PATH, cert)}
    return scope, manifest, cert


class RetryCertificateTests(TemporaryRoot):
    def verify(self, scope, manifest, cert):
        manifest["implementation_validation"] = put(self.root, release.RETRY_CERTIFICATE_PATH, cert)
        return release._retry_certificate(self.root, manifest, scope)

    def test_new_certificate_accepts_changed_two_files_without_retesting_historical_bytes(self):
        scope, manifest, cert = retry_certificate_fixture(self.root)
        with patch.object(release, "_certificate", side_effect=AssertionError("historical current-byte verifier reused")):
            self.assertEqual(self.verify(scope, manifest, cert), cert)
        self.assertEqual(len(cert["source_bindings"]), 187)
        self.assertEqual(len(cert["validation_results"]), 17)
        self.assertEqual(cert["new_phase_seconds"], 5)
        self.assertGreater(cert["cumulative_validation_seconds"], 9589)

    def test_retry_certificate_refuses_original_schema_missing_ancestor_or_historical_receipt(self):
        scope, manifest, cert = retry_certificate_fixture(self.root)
        for change in ({"schema_version": "ball_crop_cross_detector_corroboration_release_implementation/v0.1"},
                       {"ancestor_certificates": cert["ancestor_certificates"][:-1]},
                       {"validation_results": cert["validation_results"][1:]},
                       {"cumulative_validation_seconds": 5.0}, {"new_phase_seconds": 2801}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.verify(scope, manifest, {**cert, **change})

    def test_retry_certificate_rejects_extra_omitted_or_resealed_out_of_scope_source(self):
        scope, manifest, cert = retry_certificate_fixture(self.root)
        omitted = copy.deepcopy(cert)
        omitted["source_bindings"].pop()
        with self.assertRaises(ValueError):
            self.verify(scope, manifest, omitted)
        extra = put(self.root, "src/artificial/unapproved_extra.py", b"# Unapproved additional source.\n")
        with self.assertRaises(ValueError):
            self.verify(scope, manifest, cert)
        (self.root / extra["path"]).unlink()
        changed = copy.deepcopy(cert)
        row = next(row for row in changed["source_bindings"] if row["path"].startswith("src/artificial/"))
        row.update(put(self.root, row["path"], b"# Out-of-scope change resealed in current certificate.\n"))
        with self.assertRaises(ValueError):
            self.verify(scope, manifest, changed)

    def test_retry_certificate_rejects_changed_ancestor_or_missing_protected_binding(self):
        scope, manifest, cert = retry_certificate_fixture(self.root)
        missing = {**cert, "preserved_worktree_bindings": cert["preserved_worktree_bindings"][:-1]}
        with self.assertRaises(ValueError):
            self.verify(scope, manifest, missing)
        put(self.root, cert["ancestor_certificates"][1]["path"], {"forged_ancestor": True})
        with self.assertRaises(ValueError):
            self.verify(scope, manifest, cert)

    def test_retry_certificate_count_inventory_keeps_ignored_focus_out_of_full_suite(self):
        scope, manifest, cert = retry_certificate_fixture(self.root)
        wrong = copy.deepcopy(cert)
        wrong["test_counts"]["full_test_count"] = 1167 + 71
        with self.assertRaises(ValueError):
            self.verify(scope, manifest, wrong)
        inventory = json.loads((self.root / cert["test_inventory"]["path"]).read_text())
        inventory["full_repository_ids"] += inventory["ignored_lifecycle_ids"]
        wrong = copy.deepcopy(cert)
        wrong["test_inventory"] = put(self.root, cert["test_inventory"]["path"], inventory)
        with self.assertRaises(ValueError):
            self.verify(scope, manifest, wrong)

    def test_retry_certificate_refuses_unfinished_or_extra_validation_invocation(self):
        scope, manifest, cert = retry_certificate_fixture(self.root)
        put(self.root, release.RETRY_ADMIN_ROOT + "/focused_02_started.json", {"artificial_only": True})
        with self.assertRaises(ValueError):
            self.verify(scope, manifest, cert)
        put(self.root, release.RETRY_ADMIN_ROOT + "/focused_02_result.json", {"success": False})
        with self.assertRaises(ValueError):
            self.verify(scope, manifest, cert)

    def test_retry_certificate_refuses_changed_receipt_bytes_cleanup_counts_or_source_inventory(self):
        scope, manifest, cert = retry_certificate_fixture(self.root)
        full = json.loads((self.root / cert["full_result"]["path"]).read_text())
        for change in ({"owned_cleanup_verified": False}, {"source_bindings_after": []},
                       {"helper_bindings_after": []}, {"passed_count": 1237},
                       {"elapsed_seconds": 2501}, {"previously_consumed_seconds": 0.0},
                       {"preservation_error": "Artificial changed preservation"}):
            altered = copy.deepcopy(cert)
            altered["full_result"] = put(self.root, cert["full_result"]["path"], {**full, **change})
            altered["validation_results"][-1] = altered["full_result"]
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.verify(scope, manifest, altered)

    def test_retry_certificate_resealed_approval_cannot_reset_or_expand_validation(self):
        scope, manifest, cert = retry_certificate_fixture(self.root)
        approval = json.loads((self.root / cert["approval"]["path"]).read_text())
        for change in ({"previously_consumed_seconds": 0.0}, {"maximum_focused_seconds": 301},
                       {"closed_remainder_reusable": True}, {"maximum_full_invocations": 2},
                       {"prior_consumption_records": approval["prior_consumption_records"][:-1]},
                       {"scientific_execution_authorized": True}):
            altered = copy.deepcopy(cert)
            altered["approval"] = put(self.root, cert["approval"]["path"], {**approval, **change})
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.verify(scope, manifest, altered)

    def test_retry_certificate_charges_failed_focus_before_final_source_validation(self):
        scope, manifest, cert = retry_certificate_fixture(self.root)
        focused = json.loads((self.root / cert["focused_result"]["path"]).read_text())
        full = json.loads((self.root / cert["full_result"]["path"]).read_text())
        old_total = 9589.048999999992
        failed = {**focused, "success": False, "returncode": 1, "failure": "Artificial failed focus",
                  "elapsed_seconds": .75}
        failed_binding = put(self.root, cert["focused_result"]["path"], failed)
        focused["previously_consumed_seconds"] += .75
        full["previously_consumed_seconds"] += .75
        retry_receipt_snapshots(self.root, focused, "focused_02")
        cert["focused_result"] = put(self.root, release.RETRY_ADMIN_ROOT + "/focused_02_result.json", focused)
        put(self.root, release.RETRY_ADMIN_ROOT + "/focused_02_started.json", {"artificial_only": True})
        cert["full_result"] = put(self.root, cert["full_result"]["path"], full)
        cert["validation_results"] = cert["validation_results"][:15] + [failed_binding, cert["focused_result"], cert["full_result"]]
        cert.update(cumulative_validation_seconds=old_total + 5.75, new_phase_seconds=5.75,
                    new_focused_validation_seconds=2.75)
        self.assertEqual(self.verify(scope, manifest, cert), cert)
        cert["validation_results"].remove(failed_binding)
        with self.assertRaises(ValueError):
            self.verify(scope, manifest, cert)


class RetryHistoryTests(TemporaryRoot):
    def test_failed_prefix_charge_and_one_same_unit_reservation_are_preserved(self):
        journal, context = retry_journal_fixture(self.root)
        original = copy.deepcopy(journal.events)
        release.verify_retry_history(journal, context)
        self.assertEqual(len(original), 3334)
        self.assertEqual(journal.consumed(release.UNIT_KEY), 1.125)
        attempt, reserved = journal.reserve(release.UNIT_KEY, False)
        self.assertEqual(reserved, 1198.875)
        self.assertEqual(journal.events[:-1], original)
        self.assertEqual(journal.consumed(release.UNIT_KEY), 1200.0)
        self.assertAlmostEqual(journal.consumed(), 4747.523999999985)
        start = journal.events[-1]
        self.assertEqual(start["predecessor_attempt_id"], release.RETRY_PREDECESSOR)
        self.assertEqual(start["retry_approval"], context["retry_approval_binding"])
        self.assertEqual(start["original_scientific_scope"], {"path": release.SCOPE_PATH, "sha256": release.SCOPE_SHA})
        self.assertEqual(json.loads((self.root / f"attempts/{attempt}.reservation.json").read_text()),
                         {"event_sha256": start["sha256"]})
        release.verify_retry_history(journal, context, "worker", attempt)
        with self.assertRaises(ValueError):
            journal.reserve(release.UNIT_KEY, False)

    def test_retry_completion_accepts_one_contiguous_owned_suffix_only(self):
        journal, context = retry_journal_fixture(self.root)
        attempt, _ = journal.reserve(release.UNIT_KEY, False)
        with self.assertRaises(ValueError):
            release.verify_retry_history(journal, context, "completed", attempt)
        journal.append("sample", attempt_id=attempt, elapsed_seconds=0.5)
        journal.append("finished", attempt_id=attempt, elapsed_seconds=2.0, charged_elapsed_seconds=2.0,
                       time_budget_seconds=1198.875, success=True)
        release.verify_retry_history(journal, context, "completed", attempt)
        self.assertEqual(journal.consumed(release.UNIT_KEY), 3.125)
        self.assertAlmostEqual(journal.consumed(), 3550.648999999985)
        with self.assertRaises(ValueError):
            release.verify_retry_history(journal, context, "worker", attempt)
        with self.assertRaises(ValueError):
            journal.reserve(release.UNIT_KEY, False)
        journal.events[-1]["time_budget_seconds"] = 1200
        with self.assertRaises(ValueError):
            release.verify_retry_history(journal, context, "completed", attempt)

    def test_retry_refuses_changed_count_tip_failure_charge_and_successful_predecessor(self):
        changes = (
            lambda rows: rows.pop(),
            lambda rows: rows[-1].update(sha256="0" * 64),
            lambda rows: rows[3329].update(sha256="0" * 64),
            lambda rows: rows[-1].update(elapsed_seconds=1.0),
            lambda rows: rows[-1].update(charged_elapsed_seconds=0),
            lambda rows: rows[-1].update(success=True),
            lambda rows: rows[-1].update(failure="different failure"),
            lambda rows: rows[-4].update(unit_key="renamed-study"),
            lambda rows: rows[-4].update(selection_unit=True),
        )
        for mutate in changes:
            journal, context = retry_journal_fixture(self.root)
            mutate(journal.events)
            with self.subTest(mutation=mutate), self.assertRaises((ValueError, resources.ResourceLimitError)):
                release.verify_retry_history(journal, context)

    def test_retry_rejects_changed_or_missing_predecessor_seals(self):
        for suffix in ("reservation", "completion"):
            journal, context = retry_journal_fixture(self.root)
            name = f"attempts/{release.RETRY_PREDECESSOR}.{suffix}.json"
            put(self.root, name, {"event_sha256": "0" * 64})
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                release.verify_retry_history(journal, context)

    def test_retry_refuses_wrong_authority_unit_ceiling_and_predecessor_on_new_reservation(self):
        journal, context = retry_journal_fixture(self.root)
        attempt, _ = journal.reserve(release.UNIT_KEY, False)
        original = copy.deepcopy(journal.events[-1])
        for change in ({"retry_approval": {**context["retry_approval_binding"], "sha256": "0" * 64}},
                       {"predecessor_attempt_id": "b" * 32}, {"reserved_seconds": 1200},
                       {"reserved_seconds": 1.0}, {"unit_key": "renamed-study"}, {"selection_unit": True},
                       {"original_scientific_scope": {"path": release.SCOPE_PATH, "sha256": "0" * 64}}):
            journal.events[-1] = {**original, **change}
            with self.subTest(change=change), self.assertRaises((ValueError, resources.ResourceLimitError)):
                release.verify_retry_history(journal, context, "worker", attempt)

    def test_retry_refuses_open_unrelated_suffix_and_third_attempt(self):
        journal, context = retry_journal_fixture(self.root)
        attempt, _ = journal.reserve(release.UNIT_KEY, False)
        with self.assertRaises(ValueError):
            release.verify_retry_history(journal, context, "before")
        journal.append("started", attempt_id="b" * 32, unit_key=release.UNIT_KEY,
                       selection_unit=False, reserved_seconds=1.0)
        with self.assertRaises(ValueError):
            release.verify_retry_history(journal, context, "worker", attempt)
        with self.assertRaises(ValueError):
            release.verify_retry_history(journal, context, "worker", "b" * 32)

    def test_failed_retry_retains_charge_and_never_becomes_another_retry(self):
        journal, context = retry_journal_fixture(self.root)
        attempt, _ = journal.reserve(release.UNIT_KEY, False)
        journal.append("finished", attempt_id=attempt, elapsed_seconds=3.0, success=False,
                       failure="Artificial failed retry")
        self.assertEqual(journal.consumed(release.UNIT_KEY), 4.125)
        with self.assertRaises(ValueError):
            release.verify_retry_history(journal, context, "completed", attempt)
        with self.assertRaises(ValueError):
            journal.reserve(release.UNIT_KEY, False)

    def test_retry_refuses_changed_global_budget_existing_output_or_unknown_unit(self):
        journal, context = retry_journal_fixture(self.root)
        journal.limits["maximum_cumulative_seconds"] = 14401
        with self.assertRaises(ValueError):
            release.verify_retry_history(journal, context)
        journal.limits["maximum_cumulative_seconds"] = 14400
        for unit, selected in (("renamed-study", False), (release.UNIT_KEY, True)):
            with self.subTest(unit=unit, selected=selected), self.assertRaises(ValueError):
                journal.reserve(unit, selected)
        (self.root / release.OUTPUT_DIR).mkdir(parents=True)
        with self.assertRaises(ValueError):
            journal.reserve(release.UNIT_KEY, False)
        self.assertEqual(len(journal.events), 3334)

    def test_retry_rechecks_bound_approval_before_reserving_under_supervisor_lock(self):
        journal, context = retry_journal_fixture(self.root)
        put(self.root, release.RETRY_APPROVAL_PATH, {"changed_after_parent_verification": True})
        with self.assertRaises(ValueError):
            journal.reserve(release.UNIT_KEY, False)
        self.assertEqual(len(journal.events), 3334)

    def test_retry_constructor_rejects_orphan_evidence_without_replaying_real_journal(self):
        _, context = retry_journal_fixture(self.root)
        with self.assertRaises(resources.ResourceLimitError):
            release.CorroborationRetryJournal(self.root, artificial_limits(), context=context)

    def test_retry_output_allowance_keeps_original_baseline_and_charges_failed_startup_files(self):
        journal, context = retry_journal_fixture(self.root)
        context["history"] = {"preserved_files": [{"size_bytes": 9999999999} for _ in range(6917)]}
        self.assertEqual(release._context_baseline(context), 8875168842)
        attempt, _ = journal.reserve(release.UNIT_KEY, False)
        boundary = 8875168842 + release.MAX_NEW_BYTES - release.monitor.FINAL_RESERVE
        journal.append("sample", attempt_id=attempt, elapsed_seconds=.25, output_bytes=boundary)
        with self.assertRaises(resources.ResourceLimitError):
            journal.append("sample", attempt_id=attempt, elapsed_seconds=.5, output_bytes=boundary + 1)
        self.assertEqual(journal.events[-1]["output_bytes"], boundary + 1)
        end = journal.append("finished", attempt_id=attempt, elapsed_seconds=1.0, success=True,
                             final_accounting_output_bound_bytes=8875168842 + release.MAX_NEW_BYTES + 1)
        self.assertFalse(end["success"])

    def test_retry_preservation_suffix_starts_after_3334_and_never_reuses_failed_startup_indices(self):
        context = PreservationMetadataTests.context(self)
        context["retry"] = retry_scope_fixture()
        context["history"]["preserved_history"] = {"resource_event_count": 3334}
        attempt = "a" * 32
        PreservationMetadataTests.append_owned(self, attempt)
        old_name = release.OUTPUT_ROOT + "/resource_events/00003330.json"
        new_name = release.OUTPUT_ROOT + "/resource_events/00003334.json"
        (self.root / old_name).unlink()
        put(self.root, new_name, b"artificial retry reservation event")
        with patch.object(Path, "open", side_effect=AssertionError("preserved body read")):
            release._preserved(context, "worker", attempt)
        put(self.root, old_name, b"attempt to reuse the old startup event index")
        with patch.object(Path, "open", side_effect=AssertionError("preserved body read")), \
                self.assertRaisesRegex(ValueError, "Noncontiguous"):
            release._preserved(context, "worker", attempt)


class RetryAuthorityTests(TemporaryRoot):
    def manifest(self):
        retry = retry_scope_fixture()
        old = {row["path"]: row for row in retry["evidence_reuse"]["original_runtime_package"]}
        return {"schema_version": "ball_crop_corroboration_retry_release_manifest/v0.1", "study_id": release.ID,
                "scope": old[release.SCOPE_PATH],
                "proposal": {"path": release.PROPOSAL_PATH, "sha256": release.PROPOSAL_SHA},
                "execution_approval": old[release.APPROVAL_PATH],
                "integration_scope": {"path": release.RETRY_SCOPE_PATH, "sha256": release.RETRY_SCOPE_SHA},
                "integration_proposal": retry["proposal"],
                "retry_approval": {"path": release.RETRY_APPROVAL_PATH, "sha256": "d" * 64},
                "implementation_validation": {"path": release.RETRY_CERTIFICATE_PATH, "sha256": "e" * 64},
                "frozen_history": {"path": release.RETRY_HISTORY_PATH, "sha256": "f" * 64},
                "post_commit_checkpoint": release.RETRY_CHECKPOINT_PATH,
                "selected_method": None, "selected_operating_point": None, "quality_gate": None}

    def admin_gate(self, *, dirty=False, committed=True, media_authorized=True):
        manifest, retry, scope = self.manifest(), retry_scope_fixture(), administrative_scope()
        put(self.root, release.RETRY_MANIFEST_PATH, manifest)
        original = artificial_manifest()
        original.update({key: manifest[key] for key in ("scope", "proposal", "execution_approval")})
        original_approval = {"study_id": release.ID, "scope": manifest["scope"], "proposal": manifest["proposal"],
                             "scientific_execution_authorized": True}
        approval = {"schema_version": "ball_crop_corroboration_retry_execution_approval/v0.1",
                    "study_id": release.ID, "approved_by": "Ryan", "user_statement": "Artificial retry gate fixture only.",
                    "scope": manifest["scope"], "original_execution_approval": manifest["execution_approval"],
                    "integration_scope": manifest["integration_scope"], "integration_proposal": manifest["integration_proposal"],
                    "implementation_validation": manifest["implementation_validation"],
                    "failed_attempt_audit": retry["evidence_reuse"]["failed_attempt_audit"],
                    "predecessor_attempt_id": release.RETRY_PREDECESSOR, "unit_key": release.UNIT_KEY,
                    "maximum_attempts": 1, "maximum_retry_seconds": 1198.875, "fresh_budget": False,
                    **{key: True for key in ("scientific_execution_authorized", "administrative_history_verification_authorized",
                                             "release_checkpoint_authorized", "new_verified_media_presentation_authorized")}}
        approval["new_verified_media_presentation_authorized"] = media_authorized
        bodies = {release.RETRY_SCOPE_PATH: encoded(retry), release.RETRY_PROPOSAL_PATH: b"Artificial proposal.",
                  release.MANIFEST_PATH: encoded(original), release.SCOPE_PATH: encoded(scope),
                  release.PROPOSAL_PATH: b"Artificial original proposal.", release.APPROVAL_PATH: encoded(original_approval),
                  release.RETRY_APPROVAL_PATH: encoded(approval)}

        def read_admin(root, binding, **kwargs):
            if binding["path"] not in bodies:
                raise AssertionError("Retry checkpoint reached an unauthorized later body")
            return bodies[binding["path"]]

        def git(root, *args):
            if args[0] == "status":
                return "?? src/uncommitted_retry.py" if dirty else ""
            if args[:2] == ("rev-parse", "HEAD"):
                return COMMIT
            if args[0] == "branch":
                return "codex/ball-detector-baseline"
            if args[0] == "merge-base":
                return ""
            if args[0] == "ls-files":
                return args[-1] if committed else ""
            raise AssertionError(f"Unexpected Git inspection {args}")

        return manifest, read_admin, git

    def test_retry_dirty_or_uncommitted_authority_fails_before_certificate_or_science(self):
        for dirty, committed in ((True, True), (False, False)):
            _, reader, git = self.admin_gate(dirty=dirty, committed=committed)
            with patch.object(release, "_read_bound", side_effect=reader), patch.object(release, "_git", side_effect=git), \
                    patch.object(release, "_retry_certificate", side_effect=AssertionError("dirty authority reached certificate")), \
                    self.subTest(dirty=dirty, committed=committed), self.assertRaises(ValueError):
                release._metadata(self.root, release.RETRY_MANIFEST_PATH)

    def test_retry_requires_certified_source_and_preserved_paths_to_be_tracked(self):
        _, reader, original_git = self.admin_gate()
        sources = [{"path": f"src/artificial_{i:03d}.py", "sha256": "a" * 64, "size_bytes": 1} for i in range(187)]
        preserved = [{"path": "docs/artificial_review.md", "sha256": "b" * 64, "size_bytes": 1}]
        authorities = {release.RETRY_MANIFEST_PATH, release.RETRY_APPROVAL_PATH, release.RETRY_SCOPE_PATH,
                       release.RETRY_PROPOSAL_PATH, release.MANIFEST_PATH, release.APPROVAL_PATH,
                       release.SCOPE_PATH, release.PROPOSAL_PATH}
        names = {row["path"] for row in sources + preserved} | authorities
        for missing in (sources[90]["path"], preserved[0]["path"]):
            def git(root, *args):
                return "\n".join(sorted(names - {missing})) if args == ("ls-files",) else original_git(root, *args)

            with patch.object(release, "_read_bound", side_effect=reader), patch.object(release, "_git", side_effect=git), \
                    patch.object(release, "_retry_certificate", return_value={"source_bindings": sources,
                                                                            "preserved_worktree_bindings": preserved}), \
                    self.subTest(missing=missing), self.assertRaisesRegex(ValueError, "All tested source"):
                release._metadata(self.root, release.RETRY_MANIFEST_PATH)

    def test_retry_stale_checkpoint_fails_before_frozen_history_or_scientific_metadata(self):
        # Scientific approval remains valid when later media presentation is
        # explicitly unapproved; execution must reach the checkpoint gate.
        manifest, reader, git = self.admin_gate(media_authorized=False)
        checkpoint = {"schema_version": "ball_crop_corroboration_retry_post_commit_checkpoint/v0.1", "commit": COMMIT,
                      "clean": True, "manifest": release._binding(release.RETRY_MANIFEST_PATH, encoded(manifest)),
                      "predecessor_attempt_id": release.RETRY_PREDECESSOR, "original_baseline_bytes": 8875168842,
                      **{key: manifest[key] for key in ("retry_approval", "implementation_validation", "scope",
                                                       "integration_scope", "frozen_history")}}
        for change in ({"commit": "a" * 40}, {"clean": False}, {"original_baseline_bytes": 9999999999},
                       {"predecessor_attempt_id": "b" * 32}, {"manifest": {"path": release.MANIFEST_PATH}}):
            with patch.object(release, "_read_bound", side_effect=reader), patch.object(release, "_git", side_effect=git), \
                    patch.object(release, "_retry_certificate", return_value={"source_bindings": [], "preserved_worktree_bindings": []}), \
                    patch.object(release, "_require_tracked"), \
                    patch.object(release.monitor, "_read_record", return_value={**checkpoint, **change}), \
                    patch.object(release, "_retry_history_authority", side_effect=AssertionError("stale checkpoint reached later history")), \
                    self.subTest(change=change), self.assertRaisesRegex(ValueError, "stale actual clean retry checkpoint"):
                release._metadata(self.root, release.RETRY_MANIFEST_PATH)

    def test_retry_manifest_is_a_separate_exact_version_without_generic_retry_switch(self):
        manifest = self.manifest()
        self.assertEqual(release._retry_manifest(manifest), manifest)
        with self.assertRaises(ValueError):
            release._validate_manifest(manifest)
        with self.assertRaises(ValueError):
            release._retry_manifest(artificial_manifest())
        for change in ({"schema_version": "ball_crop_corroboration_release_manifest/v0.1"},
                       {"study_id": release.ID + "_new"}, {"force": True}, {"selected_method": "corroborated"},
                       {"integration_scope": {"path": release.RETRY_SCOPE_PATH, "sha256": "0" * 64}},
                       {"implementation_validation": {"path": release.CERTIFICATE_PATH, "sha256": "e" * 64}},
                       {"post_commit_checkpoint": release.CHECKPOINT_PATH}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                release._retry_manifest({**manifest, **change})

    def test_retry_metadata_dispatch_is_allowlisted_and_absent_authority_stops_early(self):
        with patch.object(release, "_read_bound", side_effect=AssertionError("unauthorized body access")), \
                patch.object(release, "_git", side_effect=AssertionError("unauthorized Git check")), \
                patch.object(resources, "BudgetJournal", side_effect=AssertionError("unauthorized journal")), \
                patch.object(release.monitor, "run_supervised", side_effect=AssertionError("unauthorized dispatch")):
            with self.assertRaises(PermissionError):
                release.run_study(self.root, release.RETRY_MANIFEST_PATH)
            for manifest in ("configs/arbitrary_retry.json", "../escape.json", release.RETRY_MANIFEST_PATH + ".copy"):
                with self.subTest(manifest=manifest), self.assertRaises(ValueError):
                    release.run_study(self.root, manifest)

    def test_history_dispatch_retains_old_guard_and_uses_retry_only_for_explicit_context(self):
        journal, scope = object(), {"artificial": True}
        context = {"scope": scope}
        with patch.object(release, "verify_history") as original, \
                patch.object(release, "verify_retry_history") as retry:
            release._verify_context_history(journal, context, "worker", "a" * 32)
            original.assert_called_once_with(journal, scope, "worker", "a" * 32)
            retry.assert_not_called()
            context["retry"] = retry_scope_fixture()
            release._verify_context_history(journal, context, "completed", "b" * 32)
            retry.assert_called_once_with(journal, context, "completed", "b" * 32)
            self.assertEqual(original.call_count, 1)

    def test_retry_worker_carries_same_manifest_to_both_authority_checks(self):
        attempt = "a" * 32
        receipt = self.root / release.OUTPUT_ROOT / "attempts" / (attempt + ".result.json")
        receipt.parent.mkdir(parents=True)
        context = {"root": self.root, "scope": {}, "limits": {}, "retry": retry_scope_fixture(),
                   "output_root": self.root / release.OUTPUT_ROOT, "commit": COMMIT,
                   "manifest_path": release.RETRY_MANIFEST_PATH,
                   "manifest_binding": {"path": release.RETRY_MANIFEST_PATH, "sha256": "a" * 64}}
        journal = SimpleNamespace(_attempts=lambda: {attempt: {"start": {"reserved_seconds": 1198.875}}})
        result = {"artificial_orchestration_only": True, "attempt_id": attempt}
        with patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": attempt}, clear=True), \
                patch.object(release, "_owned_paths"), patch.object(resources, "wait_for_supervisor"), \
                patch.object(release, "_ownership"), patch.object(release, "_metadata", return_value=context) as metadata, \
                patch.object(resources, "BudgetJournal", return_value=journal), \
                patch.object(release, "_verify_context_history") as history, patch.object(release, "_preserved"), \
                patch.object(release, "PhaseAccess"), patch.object(release, "OutputSink"), \
                patch.object(release, "run_comparison", return_value=result), \
                patch.object(release.monitor, "run_supervised", side_effect=AssertionError("production launch")):
            release._worker(self.root, release.RETRY_MANIFEST_PATH)
        self.assertEqual([call.args for call in metadata.call_args_list],
                         [(self.root, release.RETRY_MANIFEST_PATH)] * 2)
        self.assertEqual([call.args for call in history.call_args_list],
                         [(journal, context, "worker", attempt)] * 2)
        self.assertEqual(json.loads(receipt.read_text()), result)

    def test_retry_supervisor_command_and_completion_keep_selected_manifest_and_original_baseline(self):
        attempt = "b" * 32
        event = {"success": True, "attempt_id": attempt, "final_accounting_output_bound_bytes": 8875168843,
                 "worker_result": {"path": f"attempts/{attempt}.result.json", "sha256": "e" * 64, "size_bytes": 2}}
        context = {"root": self.root, "scope": {}, "retry": retry_scope_fixture(), "limits": {}, "policy": {},
                   "output_root": self.root / release.OUTPUT_ROOT, "commit": COMMIT,
                   "manifest_path": release.RETRY_MANIFEST_PATH,
                   "manifest_binding": {"path": release.RETRY_MANIFEST_PATH, "sha256": "a" * 64},
                   "history": {"preserved_files": [{"size_bytes": 9999999999}]}}
        journal = SimpleNamespace(_attempts=lambda: {attempt: {"finished": event}})
        called = []

        def supervised(output, unit, command, limits, **kwargs):
            called.append(command)
            self.assertEqual(unit, release.UNIT_KEY)
            self.assertFalse(kwargs["selection_unit"])
            self.assertTrue(kwargs["require_result"])
            kwargs["journal_factory"](output, limits)
            return event

        with patch.object(release, "_metadata", return_value=context) as metadata, \
                patch.object(release, "_preserved"), patch.object(resources, "BudgetJournal", return_value=journal), \
                patch.object(release, "_verify_context_history") as history, \
                patch.object(release, "CorroborationRetryJournal") as retry_journal, \
                patch.object(release, "CorroborationJournal", side_effect=AssertionError("old journal route")), \
                patch.object(release.monitor, "run_supervised", side_effect=supervised), \
                patch.object(release, "_successful_event") as completion, \
                patch.object(release, "_read_bound", return_value=b"{}"), \
                patch.object(release, "validate_return", return_value={"artificial_only": True}):
            release.run_study(self.root, release.RETRY_MANIFEST_PATH)
        self.assertEqual(len(called), 1)
        self.assertEqual(called[0][called[0].index("--manifest") + 1], release.RETRY_MANIFEST_PATH)
        self.assertEqual([call.args for call in metadata.call_args_list], [(self.root, release.RETRY_MANIFEST_PATH)] * 2)
        retry_journal.assert_called_once_with(context["output_root"], context["limits"], context=context)
        completion.assert_called_once_with(event, context, 8875168842)
        self.assertEqual(history.call_args_list[-1].args, (journal, context, "completed", attempt))


if __name__ == "__main__":
    unittest.main()
