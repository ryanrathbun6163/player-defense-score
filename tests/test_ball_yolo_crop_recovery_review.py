"""Synthetic mixed-inference provenance, independent images and immutable review."""
import copy
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from src.ball_tracking import yolo_crop_recovery_review as review
from src.ball_tracking.development_experiments import canonical_sha256, read_json, sha256_file
from src.ball_tracking.yolo_crop_candidates import experiment_grid
from test_ball_yolo_crop_review import (ROOT, one_frame, saved_fixture, prepared_fixture as old_prepared_fixture,
                                       fast_frame as old_fast_frame, write_json)
from test_ball_temporal_association import fixture

COMMIT = "a" * 40


def unit(window, frame, ordinal, old=False):
    view = review.crop_views()[ordinal]
    ident = f"{window['window_id']}_{frame}_{ordinal}"
    return {"window_id": window["window_id"], "possession_id": window.get("possession_id", "synthetic_possession"),
        "frame_index": frame, "view_id": view["view_id"], "view_ordinal": ordinal,
        "actual_inference_commit": review.ORIGINAL_COMMIT if old else COMMIT,
        **{k: {"path": f"data/outputs/synthetic/{ident}_{k}.json", "sha256": canonical_sha256([ident, k])}
           for k in review.UNIT_BINDINGS}}


def provenance(window, units):
    return {"window_id": window["window_id"], "assembly_code_commit": COMMIT, "model_code_commit_role": review.ROLE,
        "inference_units": units, "inference_inventory_sha256": canonical_sha256(units),
        "actual_inference_commits": sorted({u["actual_inference_commit"] for u in units})}


def prepared_fixture(root, window_count=6):
    proposal, _ = saved_fixture(root, window_count=window_count)
    prepared = old_prepared_fixture(root, proposal)
    all_pv, total = [], 0
    for item in prepared.windows:
        units = []
        for f in item["run"].frames:
            for ordinal in range(4):
                units.append(unit(item["window"], f.frame_index, ordinal, total < 175))
                total += 1
        pv = provenance(item["window"], units)
        item["inference_provenance"] = pv
        all_pv.append(pv)
    prepared.header.update({"schema_version": "ball_yolo_crop_visual_review/v0.2", "renderer_code_commit": COMMIT,
        "assembly_code_commit": COMMIT, "model_code_commit_role": review.ROLE,
        "native_header_px": review.NATIVE_HEADER, "reused_native_header_px": review.original.NATIVE_HEADER,
        "window_inference_provenance": all_pv})
    return prepared


def fast_frame(*args, inference_units, assembly_commit, renderer_commit):
    assert len(inference_units) == 4 and all(u["frame_index"] == args[2].frame_index for u in inference_units)
    assert assembly_commit == renderer_commit == COMMIT
    return old_fast_frame(*args)


class RecoveryReviewProvenanceTests(unittest.TestCase):
    def test_exact_175_425_partition_and_no_relabeling(self):
        with tempfile.TemporaryDirectory() as temporary:
            prepared = prepared_fixture(Path(temporary))
            provenances = prepared.header["window_inference_provenance"]
            units = [u for pv in provenances for u in pv["inference_units"]]
            recovery = {"completed_crop_units_reuse_without_inference": units[:175],
                        "missing_crop_units_only_allowed_new_inference": units[175:]}
            review._check_partition(provenances, recovery, COMMIT)
            for scenario in ("old_commit", "old_binding", "new_commit", "missing", "scope"):
                changed, contract = copy.deepcopy(provenances), copy.deepcopy(recovery)
                if scenario == "old_commit": changed[0]["inference_units"][0]["actual_inference_commit"] = COMMIT
                elif scenario == "old_binding": changed[0]["inference_units"][0]["checkpoint"]["sha256"] = "0" * 64
                elif scenario == "new_commit": changed[-1]["inference_units"][-1]["actual_inference_commit"] = review.ORIGINAL_COMMIT
                elif scenario == "missing": contract["missing_crop_units_only_allowed_new_inference"].pop()
                else: changed[-1]["inference_units"][-1]["frame_index"] = 99
                with self.subTest(scenario=scenario), self.assertRaises(ValueError): review._check_partition(changed, contract, COMMIT)

    def test_window_identity_inventory_digest_and_actual_commit_role(self):
        w = {"window_id": "synthetic", "possession_id": "P", "start_frame_index": 0, "end_frame_index": 0}
        h = {**provenance(w, [unit(w, 0, i, i < 2) for i in range(4)]), "per_view_model_provenance": {"code_commit": COMMIT}}
        self.assertEqual(review._window_provenance(h, w, COMMIT)["inference_units"], h["inference_units"])
        for scenario in ("digest", "order", "duplicate", "role", "unknown_commit", "commits", "possession", "boolean", "receipt"):
            changed = copy.deepcopy(h)
            if scenario == "digest": changed["inference_inventory_sha256"] = "0"*64
            elif scenario == "order": changed["inference_units"].reverse()
            elif scenario == "duplicate": changed["inference_units"][1] = changed["inference_units"][0]
            elif scenario == "role": changed["model_code_commit_role"] = "actual_inference"
            elif scenario == "unknown_commit": changed["inference_units"][0]["actual_inference_commit"] = "b"*40
            elif scenario == "commits": changed["actual_inference_commits"] = [COMMIT]
            elif scenario == "possession": changed["inference_units"][0]["possession_id"] = "other"
            elif scenario == "boolean": changed["inference_units"][0]["view_ordinal"] = False
            else: changed["inference_units"][0]["attempt_start"]["sha256"] = "not-a-digest"
            if scenario != "digest": changed["inference_inventory_sha256"] = canonical_sha256(changed["inference_units"])
            with self.subTest(scenario=scenario), self.assertRaises(ValueError): review._window_provenance(changed, w, COMMIT)

    def test_scores_require_inventory_binding_and_separate_assembly_selection_evaluation(self):
        _, run = fixture([[(100, 100, .8)]])
        run = replace(run, model_provenance=replace(run.model_provenance, code_commit=COMMIT))
        config = experiment_grid()[0]
        pv = {"inference_inventory_sha256": "b"*64, "actual_inference_commits": [review.ORIGINAL_COMMIT, COMMIT],
              "assembly_code_commit": COMMIT, "model_code_commit_role": review.ROLE}
        binding = {"path": "data/outputs/candidates.json", "sha256": "c"*64}
        obs = {"schema_version": "ball_yolo_crop_observations/v0.2", "frames": [{"frame_index": 0}],
               **pv, "input_candidate_file": binding, "ranking_code_commit": COMMIT}
        report = {"schema_version": "ball_yolo_crop_evaluation/v0.2", "possession_id": run.possession_id,
            "variant_id": config.variant_id, "localization_radius_px": 10.0, "config": asdict(config),
            "source_video": run.source_video.to_dict(), "window": run.window.to_dict(),
            "observations_content_sha256": canonical_sha256(obs), "frame_results": [{"frame_index": 0}],
            **pv, "input_candidate_file": binding, "ranking_code_commit": COMMIT, "evaluator_code_commit": COMMIT,
            "input_model_provenance": run.model_provenance.to_dict(), "input_candidate_content_sha256": canonical_sha256(run.to_dict())}
        pool = {"evaluation_reports": [report]}
        self.assertEqual(review._report(pool, run, config, obs, pv, binding, COMMIT), report)
        for key, bad in (("inference_inventory_sha256", "d"*64), ("model_code_commit_role", "inference"),
                         ("input_candidate_file", {**binding, "sha256": "d"*64}),
                         ("detector_code_commit", COMMIT), ("ranking_code_commit", "d"*40),
                         ("evaluator_code_commit", "d"*40), ("assembly_code_commit", "d"*40)):
            changed = copy.deepcopy(report); changed[key] = bad
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "provenance"):
                review._report({"evaluation_reports": [changed]}, run, config, obs, pv, binding, COMMIT)


class RecoveryReviewFrameTests(unittest.TestCase):
    def test_visible_mixed_commit_labels_and_unchanged_old_source_pixels(self):
        from src.ball_tracking import prepare_detection_visual_review as helper
        annotation, frame, source, observations, reports, natives = one_frame()
        w = {"window_id": "synthetic", "possession_id": "P"}
        units = [unit(w, 0, i, i < 2) for i in range(4)]
        before = {k: v.copy() for k, v in natives.items()}
        with patch.object(helper, "_put_fitted_text", wraps=helper._put_fitted_text) as text:
            comparison, new, closeups, focus = review.render_frame(source, annotation, frame, observations, reports, natives, .2,
                inference_units=units, assembly_commit=COMMIT, renderer_commit=COMMIT)
        self.assertEqual(comparison.shape, (1566, 2400, 3))
        self.assertTrue(all(p.shape[0] == 1080+180 for p in new))
        self.assertTrue(all(np.array_equal(natives[k], before[k]) for k in natives))
        rendered = [c.args[1] for c in text.call_args_list]
        self.assertTrue(any("tl=116e3ed9cb41" in s and "bl=aaaaaaaaaaaa" in s for s in rendered))
        self.assertTrue(any("ModelProvenance.code_commit is assembly-view provenance only" in s for s in rendered))
        self.assertEqual(len(focus), 3)
        x1, y1, x2, y2 = focus[0]["requested_source_crop_xyxy_px"]
        expected = np.repeat(np.repeat(source[y1:y2, x1:x2], 4, axis=0), 4, axis=1)
        actual = closeups[helper.ZOOM_PANEL_HEADER_PX:helper.ZOOM_PANEL_HEIGHT_PX, :expected.shape[1]]
        self.assertTrue(np.array_equal(actual[1:-1, 1:-1], expected[1:-1, 1:-1]))
        target = ROOT / "data/outputs/ball_tracking/yolo_crop_recovery_implementation_validation"
        target.mkdir(parents=True, exist_ok=True)
        for name, pixels in (("comparison", comparison), ("closeups", closeups), ("native", new[0])):
            self.assertTrue(cv2.imwrite(str(target/f"synthetic_mixed_v1_{name}.png"), pixels))
        changed = copy.deepcopy(units); changed[0]["frame_index"] = 1
        with self.assertRaisesRegex(ValueError, "synchronized"):
            review.render_frame(source, annotation, frame, observations, reports, natives, .2,
                inference_units=changed, assembly_commit=COMMIT, renderer_commit=COMMIT)


class RecoveryReviewBundleTests(unittest.TestCase):
    def test_new_subtree_complete_final_frames_resume_and_per_frame_provenance_tamper(self):
        from src.ball_tracking import yolo11x_adapter, yolo_crop_recovery as recovery
        from src.ball_tracking import yolo_crop_recovery_evaluation as scoring
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepared = prepared_fixture(root)
            before = {r["path"]: sha256_file(root/r["path"]) for r in prepared.header["reused_assets"]}
            capture_real, decoded = cv2.VideoCapture, []
            def capture(path):
                self.assertTrue(Path(path).is_relative_to(root/review.OUTPUT_ROOT))
                self.assertEqual(Path(path).name, "comparison_slow.mp4")
                decoded.append(path)
                return capture_real(path)
            with patch.object(review, "_prepare_review", return_value=prepared), patch.object(review, "render_frame", side_effect=fast_frame), \
                    patch.object(review, "TILE_WIDTH", 32), patch.object(review, "TILE_HEIGHT", 32), \
                    patch.object(cv2, "VideoCapture", side_effect=capture), \
                    patch.object(review.original, "render_experiment", side_effect=AssertionError("old renderer forbidden")), \
                    patch.object(recovery.original, "create_adapter", side_effect=AssertionError("model factory forbidden")), \
                    patch.object(yolo11x_adapter, "YOLO11xAdapter", side_effect=AssertionError("model constructor forbidden")), \
                    patch.object(recovery.original, "read_source_png", side_effect=AssertionError("inference reader forbidden")), \
                    patch.object(recovery.simple, "select_candidates", side_effect=AssertionError("selection forbidden")), \
                    patch.object(scoring, "score_experiment", side_effect=AssertionError("new scoring forbidden")), \
                    patch.object(scoring.original, "score_experiment", side_effect=AssertionError("old scoring forbidden")):
                result = review.render_experiment(root, root/"synthetic_manifest.json")
                self.assertEqual(result["assets"], 1512); self.assertEqual(result["reused_native_assets"], 1200)
                self.assertEqual(len(decoded), 12)
                bundle = Path(result["bundle"]); manifest = read_json(bundle/"manifest.json")
                self.assertEqual(len(manifest["frame_evidence"]), 300)
                self.assertEqual(sum(r["path"].endswith(".png") for r in manifest["assets"]), 1500)
                self.assertEqual(sum(r["path"].endswith(".mp4") for r in manifest["assets"]), 12)
                self.assertEqual(len([r for r in manifest["frame_evidence"] if r["frame_index"] == 24]), 12)
                self.assertTrue(review.render_experiment(root, root/"synthetic_manifest.json")["reused"])
                self.assertEqual(len(decoded), 12)
                self.assertEqual(before, {p: sha256_file(root/p) for p in before})
                for scenario in ("unit", "assembly", "render", "inventory", "source"):
                    changed = copy.deepcopy(manifest); row = changed["frame_evidence"][0]
                    if scenario == "unit": row["inference_units"][0]["actual_inference_commit"] = COMMIT
                    elif scenario == "assembly": row["assembly_code_commit"] = "b"*40
                    elif scenario == "render": row["renderer_code_commit"] = "b"*40
                    elif scenario == "inventory": row["inference_inventory_sha256"] = "b"*64
                    else: row["source_png"] = changed["frame_evidence"][1]["source_png"]
                    write_json(bundle/"manifest.json", changed)
                    with self.subTest(scenario=scenario), self.assertRaises(ValueError): review.render_experiment(root, root/"synthetic_manifest.json")
                write_json(bundle/"manifest.json", manifest)
                final = bundle/"synthetic_window_5/confidence_0.35/closeups/frame_000024.png"
                content = final.read_bytes(); final.unlink()
                with self.assertRaisesRegex(ValueError, "final frames"): review.validate_review_bundle(root,bundle,prepared.header)
                final.write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "asset hash"): review.validate_review_bundle(root,bundle,prepared.header)
                final.write_bytes(content)

    def test_changed_input_before_publication_leaves_no_completed_bundle(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); prepared = prepared_fixture(root, window_count=1)
            prepared.verify.side_effect = ValueError("changed recovery binding")
            with patch.object(review, "_prepare_review", return_value=prepared), patch.object(review, "render_frame", side_effect=fast_frame), \
                    patch.object(review, "TILE_WIDTH", 32), patch.object(review, "TILE_HEIGHT", 32):
                with self.assertRaisesRegex(ValueError, "changed recovery binding"):
                    review.render_experiment(root, root/"synthetic_manifest.json")
            self.assertFalse(list((root/review.OUTPUT_ROOT/"review").iterdir()))


if __name__ == "__main__":
    unittest.main()
