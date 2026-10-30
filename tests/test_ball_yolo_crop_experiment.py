"""Synthetic-only crop geometry, guarded inventory and resumable inference."""
import copy
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from src.ball_tracking import yolo11x_adapter as adapter
from src.ball_tracking import yolo_crop_candidates as candidates
from src.ball_tracking import yolo_crop_experiment as experiment
from src.ball_tracking.annotations import SourceVideo
from src.ball_tracking.development_experiments import canonical_sha256, read_json, sha256_file
from src.ball_tracking.detections import ModelProvenance
from src.ball_tracking.temporal_experiment import file_binding, spec_digest
from src.ball_tracking.tiled_candidates import crop_views

COMMIT = "a" * 40


def model():
    return ModelProvenance(adapter.MODEL_NAME, "ultralytics", adapter.PACKAGE_VERSION,
        adapter.WEIGHTS_IDENTIFIER, adapter.WEIGHTS_SHA256, COMMIT, "cuda:0 | synthetic", "float32",
        640, 640, adapter.RESIZE_MODE, False, 37, "sports ball", .01, adapter.POSTPROCESSING)


def prediction(rows=None, attempts=1, forwards=None):
    rows = rows if rows is not None else [(100., 100., 110., 110., .8), (30., 30., 40., 40., .009)]
    returned = [{"postprocessor_index": i, "bbox_xyxy_px": list(r[:4]), "confidence": r[4], "source_class_id": 32}
                for i, r in enumerate(rows)]
    ordered = sorted([r for r in returned if r["confidence"] >= .01],
                     key=lambda r: (-r["confidence"], r["bbox_xyxy_px"], r["postprocessor_index"]))
    exported, source = [], []
    for i, r in enumerate(ordered):
        x1, y1, x2, y2 = r["bbox_xyxy_px"]
        exported.append({"candidate_index": i, "class_id": 37, "class_name": "sports ball", "confidence": r["confidence"],
                         "bbox_xyxy_px": r["bbox_xyxy_px"], "center_xy_px": [(x1+x2)/2, (y1+y2)/2]})
        source.append({"candidate_index": i, "postprocessor_index": r["postprocessor_index"]})
    return {"candidates": exported, "postprocessing": {"source_class_id": 32, "returned_candidates": returned,
            "exported_candidate_sources": source, "cap_saturated": len(returned) == 300,
            "input_transform": copy.deepcopy(adapter.INPUT_TRANSFORM)},
            "forward_accounting": {"synthetic_forwards": 2, "project_attempts": attempts,
                "project_forwards": attempts if forwards is None else forwards, "this_project_attempt_forwards": 1,
                "preparation_complete": True}}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def fixture(root):
    """Six approved-shaped synthetic windows, no real evidence or annotation reads."""
    windows, inventory = [], []
    for i, (pid, lo, hi) in enumerate(experiment.APPROVED_WINDOWS):
        purpose = "representative_evaluation" if i % 2 == 0 else "challenge_evaluation"
        w = {"window_id": f"{pid}_synthetic_{lo}_{hi}", "purpose": purpose, "possession_id": pid,
             "source_video": {"path": f"data/clips/{pid}.mp4", "sha256": "b"*64, "width_px": 1920,
                              "height_px": 1080, "fps": 25., "frame_count": 500},
             "start_frame_index": lo, "end_frame_index": hi, "annotation_set_id": f"{pid}_synthetic_{lo}",
             "detection_run_id": f"{pid}_synthetic_{lo}"}
        windows.append(w)
        for f in range(lo, hi+1):
            path = root / "data/outputs/ball_tracking/synthetic" / w["window_id"] / "unmarked_source" / f"frame_{f:06d}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"synthetic-bound-png-{f}".encode())
            inventory.append({"window_id": w["window_id"], "frame_index": f, "source_png": file_binding(root, path)})
    docs = {}
    for key in ("design_document", "prior_results"):
        path = root / "docs" / (key + ".md")
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text("synthetic evidence", encoding="utf-8")
        docs[key] = file_binding(root, path)
    runtime_path = root / "data/outputs/ball_tracking/yolo11x_runtime/runtime.json"
    runtime = {"weights": {"path": "data/outputs/ball_tracking/yolo11x_runtime/yolo11x.pt", "sha256": adapter.WEIGHTS_SHA256}}
    write(runtime_path, runtime)
    p = {"schema_version": "ball_detector_challenger_proposal/v0.1", "proposal_id": experiment.EXPERIMENT_ID,
         "windows": windows, "crop_views": crop_views(), "sealed_holdouts": experiment.SEALED,
         "proposed_output_root": experiment.OUTPUT_ROOT, "original_embargo_paths": [f"data/outputs/embargo_{i}.json" for i in range(9)],
         "inference_source_frames": inventory, "model": {"model_name": adapter.MODEL_NAME,
             "package_version": adapter.PACKAGE_VERSION, "publisher_expected_weights_sha256": adapter.WEIGHTS_SHA256},
         "prior_visual_review": {"path": "configs/ball_tracking/reviews/synthetic_prior.json", "sha256": "c"*64}, **docs}
    proposal_path = root / "configs/ball_tracking/proposals/synthetic_yolo.json"
    write(proposal_path, p)
    m = {"schema_version": "ball_yolo_crop_experiment/v0.1", "experiment_id": experiment.EXPERIMENT_ID,
         "proposal": file_binding(root, proposal_path), "authorization": None, "runtime": file_binding(root, runtime_path),
         "output_root": experiment.OUTPUT_ROOT, "selected_operating_point": None, "quality_gate": None}
    approval = {"schema_version": "ball_yolo_crop_experiment_approval/v0.1", "experiment_spec_sha256": spec_digest(m),
                "proposal": m["proposal"], "approved_by": "ryan", "statement": "synthetic test approval",
                "recorded_at_utc": "synthetic", "timestamp_semantics": "synthetic", "scope": "six_development_windows_four_fixed_crops_three_selectors",
                "git_mutations_authorized": False}
    approval_path = root / "configs/ball_tracking/reviews/synthetic_yolo.json"
    write(approval_path, approval); m["authorization"] = file_binding(root, approval_path)
    manifest_path = root / "configs/ball_tracking/yolo_crop_experiments/synthetic.json"
    write(manifest_path, m)
    inputs = [{"window": w, "source_frames": [r for r in inventory if r["window_id"] == w["window_id"]],
               "runtime_record": runtime, "weights_path": root / runtime["weights"]["path"], "model": model()} for w in windows]
    return manifest_path, m, p, inputs


class FakeAdapter:
    def __init__(self, *, fail_at=None):
        self._account = {"synthetic_forwards": 0, "project_attempts": 0, "project_forwards": 0, "preparation_complete": False}
        self.fail_at, self.calls, self.prepares = fail_at, 0, 0
        self.cuda_peak_allocated_bytes = 1234

    @property
    def accounting(self):
        return dict(self._account)

    def prepare(self):
        self.prepares += 1
        self._account.update(synthetic_forwards=2, preparation_complete=True)

    def predict_frame(self, rgb):
        assert self._account["preparation_complete"] and rgb.shape == (648, 1152, 3) and rgb.dtype == np.uint8
        self.calls += 1
        self._account["project_attempts"] += 1
        self._account["project_forwards"] += 1
        if self.fail_at == self.calls:
            raise RuntimeError("synthetic failed project attempt")
        return prediction(attempts=self.calls)


class CandidateTests(unittest.TestCase):
    def test_crop_mapping_global_ties_and_duplicate_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); _, m, p, inputs = fixture(root)
            w = p["windows"][0]; source = SourceVideo.from_mapping(w["source_video"])
            # Two equal-score crops describe the same source box; both survive.
            boxes = [(800., 450., 810., 460., .8), (32., 450., 42., 460., .8),
                     (800., 18., 810., 28., .8), (32., 18., 42., 28., .8)]
            records = [{"view": v, "prediction": prediction([box]), "elapsed_seconds": .01,
                        "cuda_peak_allocated_bytes": 1, "attempt_id": f"synthetic_{i}"}
                       for i, (v, box) in enumerate(zip(crop_views(), boxes))]
            frame = candidates.make_frame(50, inputs[0]["source_frames"][0]["source_png"], records, source, model())
            self.assertEqual([r["detection"]["bbox_xyxy_px"] for r in frame["candidates"]], [[800., 450., 810., 460.]]*4)
            self.assertEqual([r["view_ordinal"] for r in frame["candidates"]], [0,1,2,3])
            self.assertEqual([r["local_candidate_index"] for r in frame["candidates"]], [0]*4)
            self.assertEqual([r["detection"]["candidate_index"] for r in frame["candidates"]], list(range(4)))

    def test_simple_selectors_inclusive_ties_caps_empty_and_label_exclusion(self):
        from test_ball_crop_ranking import run_fixture
        _, run = run_fixture([[(100+i, 100, .2) for i in range(25)], []])
        self.assertEqual(len(candidates.experiment_grid()), 27)
        for arm, count in zip(candidates.ARMS, [25, 1, 20]):
            obs = candidates.select_candidates(run, candidates.SelectorConfig(arm, .2), COMMIT)
            self.assertEqual(obs["frames"][0]["emitted_candidate_indices"], list(range(count)))
            self.assertEqual(obs["frames"][1]["emitted_candidate_indices"], [])
            self.assertIsNone(obs["frames"][0]["ranking"])
            self.assertEqual(candidates.validate_observations(obs, run).arm, arm)
            self.assertEqual(candidates.validate_saved_structure(obs, run).arm, arm)
            changed = copy.deepcopy(obs); changed["labels"] = []
            with self.assertRaises(ValueError): candidates.validate_observations(changed, run)
            with self.assertRaises(ValueError): candidates.validate_saved_structure(changed, run)
            for bad_indices in ([999], [0, 0], [True]):
                changed = copy.deepcopy(obs); changed['frames'][0]['emitted_candidate_indices'] = bad_indices
                with self.assertRaises(ValueError): candidates.validate_saved_structure(changed, run)
        for bad in (True, .201):
            with self.assertRaises(ValueError): candidates.SelectorConfig(candidates.ARMS[0], bad)


class ManifestTests(unittest.TestCase):
    def test_preflight_uses_only_bound_inventory_metadata_and_never_labels_or_media(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path, m, p, inputs = fixture(root)
            actual_read = experiment.read_json
            opened = []
            def checked_read(target):
                self.assertNotIn("annotations", Path(target).parts)
                opened.append(Path(target))
                return actual_read(target)
            with patch.object(experiment, "EXPECTED_PROPOSAL_SHA", m["proposal"]["sha256"]), \
                    patch.object(experiment, "git", return_value=COMMIT), \
                    patch.object(experiment, "inspect_runtime", return_value=(inputs[0]["weights_path"], model())), \
                    patch.object(experiment.subprocess, "run", return_value=SimpleNamespace(returncode=0)), \
                    patch.object(experiment, "read_json", side_effect=checked_read), \
                    patch.object(experiment, "create_adapter", side_effect=AssertionError("no model")), \
                    patch.object(experiment, "read_source_png", side_effect=AssertionError("no pixels")):
                result = experiment.run_experiment(root, path, dry_run=True)
                self.assertEqual(result["unique_project_crop_units"], 600)
                self.assertEqual(result["selector_outputs"], 162)
                self.assertFalse((root / experiment.OUTPUT_ROOT).exists())
                png = root / p["inference_source_frames"][0]["source_png"]["path"]
                png.write_bytes(b"changed source")
                with self.assertRaises(ValueError): experiment.preflight(root, path, require_clean=False)
            self.assertEqual(len(set(opened)), 4)

    def test_changed_proposal_authorization_and_embargo_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path, m, p, inputs = fixture(root)
            with patch.object(experiment, "EXPECTED_PROPOSAL_SHA", m["proposal"]["sha256"]):
                self.assertEqual(experiment.load_manifest(root, path)[0], m)
                blocked = root / p["original_embargo_paths"][0]
                blocked.parent.mkdir(parents=True, exist_ok=True); blocked.write_bytes(b"forbidden")
                with self.assertRaisesRegex(ValueError, "embargo"): experiment.load_manifest(root, path)
                blocked.unlink()
                value = copy.deepcopy(m); value["runtime"]["sha256"] = "0"*64
                write(path, value)
                with self.assertRaisesRegex(ValueError, "authorization"): experiment.load_manifest(root, path)


class InferenceTests(unittest.TestCase):
    def test_failed_synthetic_preparation_is_recorded_before_any_project_pixels(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,m,p,inputs=fixture(root)
            fake=FakeAdapter()
            def failure():
                fake._account['synthetic_forwards']=1
                raise RuntimeError('synthetic warmup failed')
            fake.prepare=failure
            with patch.object(experiment,'preflight',return_value=(m,p,inputs,COMMIT)),patch.object(experiment,'unchanged'):
                with self.assertRaisesRegex(RuntimeError,'synthetic warmup failed'):
                    experiment.run_experiment(root,path,adapter_factory=lambda *args:fake,
                        png_reader=Mock(side_effect=AssertionError('project pixels before preparation')))
            starts, results=experiment._validate_preparations(root,m,COMMIT)
            self.assertEqual(len(starts),1)
            self.assertEqual(next(iter(results.values()))['status'],'failed')
            self.assertEqual(next(iter(results.values()))['accounting_after']['synthetic_forwards'],1)
            self.assertFalse((root/experiment.OUTPUT_ROOT/'attempts').exists())

    def test_native_png_reader_preserves_geometry_and_rgb_channels(self):
        import cv2
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'data/outputs/ball_tracking/synthetic/unmarked_source/frame_000050.png'
            path.parent.mkdir(parents=True)
            bgr=np.zeros((1080,1920,3),np.uint8)
            bgr[432,768]=[11,22,33];bgr[1079,1919]=[44,55,66]
            self.assertTrue(cv2.imwrite(str(path),bgr))
            record={'source_png':file_binding(root,path)}
            with patch.object(cv2,'imread',side_effect=AssertionError('separate file reread')):
                rgb=experiment.read_source_png(root,record)
            self.assertEqual(rgb[432,768].tolist(),[33,22,11])
            self.assertEqual(rgb[1079,1919].tolist(),[66,55,44])
            self.assertEqual(rgb.shape,(1080,1920,3))
            path.write_bytes(b'changed after initial binding')
            with patch.object(cv2,'imdecode',side_effect=AssertionError('decode before verified bytes')):
                with self.assertRaisesRegex(ValueError,'bytes changed before decode'):
                    experiment.read_source_png(root,record)

    def test_six_windows_600_units_retry_resume_and_162_selectors_no_old_pipeline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path, m, p, inputs = fixture(root)
            failed, resumed = FakeAdapter(fail_at=3), FakeAdapter()
            reader = Mock(return_value=np.zeros((1080,1920,3), np.uint8))
            factory = Mock(side_effect=[failed, resumed])
            with patch.object(experiment, "preflight", return_value=(m,p,inputs,COMMIT)), \
                    patch.object(experiment, "unchanged"), \
                    patch("src.ball_tracking.tiled_experiment.run_experiment", side_effect=AssertionError("old runner")), \
                    patch("src.ball_tracking.crop_motion_factorial.rank_candidates", side_effect=AssertionError("old selector")):
                with self.assertRaisesRegex(RuntimeError, "failed project"):
                    experiment.run_experiment(root,path,adapter_factory=factory,png_reader=reader)
                self.assertEqual(len(list((root / experiment.OUTPUT_ROOT).glob("*/views/*.json"))), 2)
                done = experiment.run_experiment(root,path,adapter_factory=factory,png_reader=reader)
                self.assertEqual(done["unique_completed_crop_units"], 600)
                self.assertEqual(done["created_crop_checkpoints"], 598)
                self.assertEqual(done["total_recorded_project_attempts"], 601)
                self.assertEqual(done["failed_attempt_records"], 1)
                self.assertEqual(done["unfinished_attempt_records"], 0)
                self.assertEqual(done["predictor_preparations"], 2)
                self.assertEqual(done["recorded_synthetic_forwards"], 4)
                self.assertFalse(done["unfinished_accounting_is_unknown"])
                self.assertEqual((failed.prepares,resumed.prepares,failed.calls,resumed.calls),(1,1,3,598))
                files = list((root / experiment.OUTPUT_ROOT).rglob("*.json"))
                before = {str(f): sha256_file(f) for f in files}
                copies = reader.call_count
                again = experiment.run_experiment(root,path,adapter_factory=Mock(side_effect=AssertionError("resume constructed model")),png_reader=reader)
                self.assertEqual(again["created_crop_checkpoints"],0)
                self.assertEqual(reader.call_count,copies)
                self.assertEqual(before,{str(f):sha256_file(f) for f in files})
                selectors = [f for w in p['windows'] for f in (root / experiment.OUTPUT_ROOT / w['window_id']).glob("*.json") if f.name!='candidates.json']
                self.assertEqual(len(selectors),162)
                record = read_json(selectors[-1]);self.assertEqual(len(record['observations']['frames']),25)
                self.assertEqual(record['observations']['frames'][-1]['frame_index'],p['windows'][-1]['end_frame_index'])
                # A corrupted cached record must fail before a new factory or pixel read.
                crop = next((root / experiment.OUTPUT_ROOT).glob("*/views/*.json"))
                value=read_json(crop);value['source_png']['sha256']='f'*64;write(crop,value)
                with self.assertRaises(ValueError):
                    experiment.run_experiment(root,path,adapter_factory=Mock(side_effect=AssertionError("model before cache validation")),png_reader=Mock(side_effect=AssertionError("pixels")))

    def test_wrong_success_forward_accounting_never_publishes_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,m,p,inputs=fixture(root)
            fake=FakeAdapter()
            original=fake.predict_frame
            def invalid(rgb):
                value=original(rgb);fake._account['synthetic_forwards']+=1;return value
            fake.predict_frame=invalid
            with patch.object(experiment,'preflight',return_value=(m,p,inputs,COMMIT)),patch.object(experiment,'unchanged'):
                with self.assertRaisesRegex(ValueError,'Exactly one project'):
                    experiment.run_experiment(root,path,adapter_factory=lambda *args:fake,png_reader=lambda *args:np.zeros((1080,1920,3),np.uint8))
            self.assertEqual(list((root/experiment.OUTPUT_ROOT).glob('*/views/*.json')),[])


if __name__ == '__main__':
    unittest.main()
