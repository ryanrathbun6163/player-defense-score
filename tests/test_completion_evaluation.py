"""CPU transport checks using the actual observation/scoring/completion producers."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from src.ball_tracking import completion_evaluation as evaluation
from src.ball_tracking import completion_comparison_render as rendering
from src.ball_tracking.annotations import FrameAnnotation
from src.ball_tracking.completion_evaluation_package import _baseline, normalize_block
from src.ball_tracking.completion_training_runtime import binding, atomic_write_once
from src.ball_tracking.nba_action_observation import select_observation, stream_means
from src.ball_tracking.wasb_experiment import canonical


REPO = Path(__file__).resolve().parents[1]


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def block(self, pid="possession_001", domain="nfhs", n=4):
        source = {"width_px": 64, "height_px": 36, "frame_count": n + 1, "sha256": "synthetic-source"}
        frames = []
        for index in range(n):
            path = self.root / f"{pid}_{index}.png"
            rgb = np.full((36, 64, 3), index + 30, dtype=np.uint8)
            Image.fromarray(rgb).save(path)
            raw = {"frame_index": index, "annotation_status": "labeled", "visibility": "fully_visible",
                "absence_reason": None, "game_ball_identity_certainty": "certain",
                "geometry": {"center_xy_px": [20, 12], "source": "observed_complete_ball_center", "uncertainty_radius_px": 2},
                "localization_eligible": True, "difficulty_tags": [], "notes": "Synthetic producer fixture."}
            annotation = FrameAnnotation.from_mapping(raw, index, type("Bounds", (), source)()).to_dict()
            frames.append({"source_frame_index": index, "source_pts_ticks": (index + 1) * 512,
                "duration_ticks": 512, "state": "permitted", "block_id": pid + ":block",
                "reference_role": evaluation.ROLE, "annotation": annotation,
                "png": {**binding(self.root, path), "rgb_sha256": hashlib.sha256(rgb.tobytes()).hexdigest()}})
        block = {"block_id": pid + ":block", "domain": domain, "game_id": pid, "possession_id": pid,
            "role": evaluation.ROLE, "source_video": source, "time_base": "1/12800", "frames": frames,
            "protected_ranges": [[n, n]]}
        for frame, mean, count in stream_means(frames, lambda selected: self.heatmaps()):
            original = select_observation(frame, mean, count, block, {"kind": "synthetic"})
            # Exercise the historical NFHS producer layout, which has no native
            # transport fields; NBA originals retain those fields.
            if domain == "nfhs":
                original = {k: original[k] for k in ("state", "center_xy_px", "native_score", "candidates", "selected_candidate_index")}
                original.update(frame_index=frame["source_frame_index"], contribution_count=count)
            frame["baseline_observation"] = _baseline(original)
        return normalize_block(block)

    @staticmethod
    def heatmaps(wrong=False):
        maps = np.zeros((3, 288, 512), dtype=np.float32)
        maps[:, 240 if wrong else 96, 400 if wrong else 160] = .8
        return maps

    def observed(self, block, wrong=False):
        return [select_observation(f, mean, count, block, {"kind": "synthetic"})
                for f, mean, count in stream_means(block["frames"], lambda frames: self.heatmaps(wrong))]

    def package(self, wrong=False):
        blocks = [self.block(f"possession_00{i}") for i in range(1, 4)]
        timelines = []
        for block in blocks:
            n = len(block["frames"])
            timelines.append({"possession_id": block["possession_id"], "source_video": block["source_video"],
                "time_base": block["time_base"], "protected_ranges": [[n, n]],
                "frames": deepcopy(block["frames"]) + [{"source_frame_index": n, "source_pts_ticks": (n + 1) * 512,
                    "duration_ticks": 512, "state": "withheld", "block_id": None}]})
        package = {"schema_version": "completion_evaluation_package/v0.1", "execution_ready": True,
            "inference_blocks": blocks, "curated_timelines": timelines,
            "selected_method": {"checkpoint": {"path": "synthetic.pth", "sha256": "synthetic"},
                "training_result": {"path": "synthetic-result.json", "sha256": "synthetic"},
                "selection": {"selected_epoch": 0, "epoch_zero_selected": True}},
            "regression_cohorts": [{"cohort_id": "test", "source_id": "possession_001", "frame_indices": list(range(4)),
                                    "regression_screen": True, "role": "checkpoint_selection_development"}]}
        records = {b["block_id"]: {"block_sha256": canonical(b), "observations": self.observed(b, wrong)} for b in blocks}
        return package, records

    def test_historical_baseline_native_transport_and_original_preservation(self):
        for domain in ("nfhs", "nba"):
            block = self.block(domain=domain)
            original = deepcopy(block)
            rows = evaluation.baseline_observations(block)
            self.assertEqual(block, original)
            evaluation.validate_observations(block, rows)
            self.assertEqual([r["temporal_contributions"] for r in rows], [1, 2, 2, 1])
            self.assertEqual(rows[0]["source_pts_ticks"], 512)
            self.assertEqual(rows[0]["original_baseline_record"], block["frames"][0]["baseline_observation"]["original_record"])
            changed = deepcopy(block)
            changed["frames"][0]["baseline_observation"]["center_xy_px"] = [1, 1]
            with self.assertRaisesRegex(ValueError, "changed original"):
                evaluation.baseline_observations(changed)

    def test_bounded_native_loader_actual_stream_producer_and_mean_transport(self):
        block = self.block(n=5)
        class FakeAdapter:
            def predict_triplet(inner, rgb):
                self.assertEqual([int(image[0, 0, 0]) for image in rgb], list(range(int(rgb[0][0, 0, 0]), int(rgb[0][0, 0, 0]) + 3)))
                return {"heatmaps": self.heatmaps()}
        rows, receipt = evaluation.infer_block(self.root, block, FakeAdapter(), self.root / "means.npy")
        self.assertEqual(receipt["model_calls"], 3)
        self.assertEqual(receipt["native_png_decodes"], 5)
        self.assertEqual(receipt["maximum_cached_native_images"], 3)
        means = np.load(self.root / "means.npy", allow_pickle=False)
        self.assertEqual(means.shape, (5, 288, 512))
        self.assertEqual(rows[0]["mean_heatmap_sha256"], hashlib.sha256(means[0].tobytes()).hexdigest())
        self.assertEqual([r["center_xy_px"] for r in rows], [[20., 12.]] * 5)

    def test_protected_access_rejected_before_file_read_and_rgb_hash_checked(self):
        block = self.block()
        loader = evaluation.NativeImages(self.root, block)
        protected = {"state": "withheld", "source_frame_index": 4}
        with patch.object(evaluation, "bound_path", side_effect=AssertionError("No file read")):
            with self.assertRaisesRegex(ValueError, "Protected image"):
                loader.get(protected)
            with self.assertRaisesRegex(ValueError, "Protected index"):
                loader.get({**protected, "state": "permitted"})
        block["frames"][0]["png"]["rgb_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "RGB hash"):
            loader.get(block["frames"][0])

    def test_inference_failure_is_preserved_as_failure_not_missing(self):
        class BrokenAdapter:
            def predict_triplet(self, images):
                raise RuntimeError("synthetic execution failure")
        with self.assertRaisesRegex(RuntimeError, "execution failure"):
            evaluation.infer_block(self.root, self.block(), BrokenAdapter(), self.root / "failed_means.npy")
        self.assertTrue((self.root / "failed_means.npy").is_file())

    def test_actual_score_json_renderer_transport_and_pending_object_review(self):
        package, records = self.package()
        package_binding = {"path": "synthetic-package.json", "sha256": "synthetic"}
        result = evaluation.score_package(package, records, package_binding)
        result = json.loads(json.dumps(result, allow_nan=False))
        rendering.validate_evaluation(package, result, package_binding)
        for timeline, comparison in zip(package["curated_timelines"], result["curated_comparisons"], strict=True):
            rendering.validate_timeline(timeline, comparison)
            summary = comparison["selected_metrics"]["summary"]
            self.assertEqual((summary["matched"], summary["withheld"]), (4, 1))
            self.assertEqual(summary["wrong_objects"]["gate"]["status"], "inconclusive")
        self.assertEqual(result["prospective_regression_status"], "pass")
        self.assertFalse(result["full_clip_pass_claimed"])
        self.assertFalse(result["conditional_resolution_fit_authorized_by_report"])

    def test_regression_census_and_individual_lost_points(self):
        package, records = self.package(wrong=True)
        result = evaluation.score_package(package, records, {})
        cohort = result["regression_cohorts"][0]
        self.assertEqual(result["prospective_regression_status"], "fail")
        self.assertEqual((cohort["baseline"]["matched"], cohort["selected"]["wrong"]), (4, 4))
        self.assertEqual(sum(r["lost_match"] for r in cohort["changed_frames"]), 4)

    def test_stale_timing_context_binding_and_failed_observations_rejected(self):
        mutations = [lambda rows: rows[0].update(source_pts_ticks=0),
                     lambda rows: rows[0].update(temporal_contributions=3),
                     lambda rows: rows[0].update(inference_status="failed"),
                     lambda rows: rows[0].update(source_png={}),
                     lambda rows: rows.pop()]
        block = self.block()
        for mutate in mutations:
            rows = self.observed(block)
            mutate(rows)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                evaluation.validate_observations(block, rows)
        package, records = self.package()
        records[package["inference_blocks"][0]["block_id"]]["block_sha256"] = "stale"
        with self.assertRaisesRegex(ValueError, "block identity"):
            evaluation.score_package(package, records, {})

    def test_real_nfhs_config_string_path_reaches_adapter_constructor(self):
        # Consume the actual frozen recipe/config representation; constructor is
        # mocked so this transport check never loads weights or touches CUDA.
        package = {"selected_method": {"checkpoint": {"path": "synthetic.pth", "sha256": "synthetic"}}}
        recipe = json.loads((REPO / evaluation.PRIMARY_RECIPE).read_text())
        config = json.loads((REPO / recipe["nfhs_training_config"]["path"]).read_text())
        with patch.object(evaluation, "bound_path", side_effect=lambda root, value: Path(root) / value["path"]), \
             patch("src.ball_tracking.wasb_adapted_adapter.AdaptedWasbAdapter") as constructor:
            evaluation.make_adapter(REPO, package)
        self.assertEqual(constructor.call_args.args[0], REPO / config["upstream_source"])
        self.assertEqual(constructor.call_args.kwargs["device"], "cuda")

    def test_execution_identity_binds_frozen_and_additive_dependencies(self):
        recipe = json.loads((REPO / evaluation.PRIMARY_RECIPE).read_text())
        with patch.object(evaluation, "runtime_versions", return_value=recipe["runtime"]):
            identity = evaluation.execution_identity(REPO, {"synthetic": True})
        self.assertEqual(len(identity["frozen_dependencies"]), 25)
        self.assertEqual(len(identity["comparison_dependencies"]), 4)
        self.assertEqual({Path(b["path"]).stem for b in identity["comparison_dependencies"]},
                         {"completion_evaluation", "completion_evaluation_package", "completion_scoring", "completion_comparison_render"})
        with patch.object(evaluation, "runtime_versions", return_value={}):
            with self.assertRaisesRegex(ValueError, "runtime versions"):
                evaluation.execution_identity(REPO, {})

    def test_epoch_zero_reuses_saved_records_and_failed_attempt_resumes(self):
        package, _ = self.package()
        package["selected_method"]["checkpoint"]["sha256"] = evaluation.BASELINE_SHA
        identity = {"implementation": {"path": "synthetic.py", "sha256": "synthetic"}, "synthetic": True}
        output = self.root / "data/outputs/evaluation"
        with patch.object(evaluation, "prepare_selected_package", side_effect=lambda *args: deepcopy(package)), \
             patch.object(evaluation, "execution_identity", return_value=identity), \
             patch.object(evaluation, "make_adapter", side_effect=AssertionError("Epoch zero must not load a model")):
            with patch.object(evaluation, "score_package", side_effect=ValueError("synthetic scoring delivery failure")):
                with self.assertRaisesRegex(ValueError, "delivery failure"):
                    evaluation.execute(self.root, output_folder="data/outputs/evaluation")
            failed = list((output / "attempts").glob("*/failed.json"))
            self.assertEqual(len(failed), 1)
            old_failure = failed[0].read_bytes()
            blocks_before = {p: p.read_bytes() for p in (output / "blocks").glob("*/completed.json")}
            self.assertEqual(len(blocks_before), 3)
            result = evaluation.execute(self.root, output_folder="data/outputs/evaluation", resume=True)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(failed[0].read_bytes(), old_failure)
            self.assertTrue(all(p.read_bytes() == value for p, value in blocks_before.items()))
            replay = evaluation.execute(self.root, output_folder="data/outputs/evaluation", resume=True)
            self.assertEqual(result, replay)
            with self.assertRaisesRegex(ValueError, "explicit --resume"):
                evaluation.execute(self.root, output_folder="data/outputs/evaluation")

    def test_later_render_publication_preserves_completion_and_reuses_review(self):
        output = self.root / "data/outputs/evaluation"
        output.mkdir(parents=True)
        atomic_write_once(output / "evaluation.json", {"package": {"path": "package.json"}})
        completed = {"identity": {"synthetic": True}, "review": None,
                     "evaluation": binding(self.root, output / "evaluation.json")}
        atomic_write_once(output / "completed.json", completed)
        original = (output / "completed.json").read_bytes()
        calls = []
        def fake_render(root, package, evaluation_binding, folder):
            calls.append(folder)
            path = Path(root) / folder
            path.mkdir()
            (path / "index.html").write_text("synthetic review")
            atomic_write_once(path / "summary.json", {"synthetic": True})
            return {"index": binding(root, path / "index.html"), "summary": binding(root, path / "summary.json")}
        with patch.object(rendering, "render_comparison", side_effect=fake_render):
            first = evaluation.ensure_review(self.root, output, completed)
            second = evaluation.ensure_review(self.root, output, completed)
        self.assertEqual(len(calls), 1)
        self.assertEqual(first, second)
        self.assertIsNotNone(first["review"])
        self.assertEqual((output / "completed.json").read_bytes(), original)

    def completed_producer_fixture(self):
        """Use the frozen runner's actual completion and validation producers.

        Five synthetic zero-draw epochs exercise result transport only. A CPU
        model emits synthetic heatmaps. Resource/RNG/GPU setup is mocked, and
        no actual fitting, accepted reference use or campaign execution occurs.
        """
        import torch
        from src.ball_tracking import completion_training as producer
        blocks = [self.block(f"possession_00{i}", n=3) for i in range(1, 4)] + [self.block("nba_synthetic", domain="nba", n=3)]
        for block in blocks:
            block["role"] = "checkpoint_validation"
        package = {"training_blocks": [], "training_triplets": [], "validation_blocks": blocks}
        schedule = {"epochs": [{"epoch": e, "batches": []} for e in range(1, 21)]}
        atomic_write_once(self.root / "package.json", package)
        atomic_write_once(self.root / "schedule.json", schedule)
        cp = self.root / "initial.pth"
        torch.save({"model_state_dict": {"weight": torch.tensor([0.])}}, cp)
        recipe = {"schema_version": "ball_completion_primary_recipe/v0.1", "status": "frozen_before_model_execution",
            "protected_evaluation_authorized": False, "package": binding(self.root, self.root / "package.json"),
            "sampling_schedule": binding(self.root, self.root / "schedule.json"), "initialization": {"checkpoint": binding(self.root, cp)},
            "cache_root": "data/outputs/synthetic-cache"}
        atomic_write_once(self.root / evaluation.PRIMARY_RECIPE, recipe)
        identity = {"recipe": binding(self.root, self.root / evaluation.PRIMARY_RECIPE),
                    "package_sha256": canonical(package), "schedule_sha256": canonical(schedule)}
        class FakeStore:
            def __init__(self, *args): pass
            def prepare(self): return {"elapsed_seconds": 0, "synthetic": True}
            def inputs(self, *args): return torch.zeros((9, 288, 512))
            def close(self): pass
        class FakeModel:
            def state_dict(self): return {"weight": torch.tensor([0.])}
            def eval(self): return self
            def __call__(self, inputs): return {0: torch.full((1, 3, 288, 512), -20.)}
        output = self.root / "data/outputs/synthetic-fit"
        with patch.object(producer, "resources", return_value={"synthetic_cpu": True}), \
             patch.object(producer.runtime, "FrameStore", FakeStore), \
             patch.object(producer.adaptation, "initialize", return_value=(FakeModel(), torch.device("cpu"), None, {})), \
             patch.object(producer.training, "freeze_batch_norm", return_value={}), \
             patch.object(producer.training, "assert_batch_norm_unchanged"), \
             patch.object(producer.training, "rng_state", return_value={}), \
             patch.object(producer.training, "restore_rng"), \
             patch.object(producer, "state_payload", return_value={"synthetic_cpu_state": True}), \
             patch.object(torch.cuda, "is_available", side_effect=AssertionError("CUDA check prohibited")):
            producer._execute_locked(self.root, recipe, package, schedule, {}, identity, output, False)
        return (output / "completed.json").relative_to(self.root).as_posix()

    def test_actual_completed_result_producer_consumed_without_model_loading(self):
        path = self.completed_producer_fixture()
        selected, audit = evaluation.audit_completed_result(self.root, path)
        self.assertEqual(audit["completed_epochs"], 5)
        self.assertEqual(audit["validation_reports_checked"], 6)
        self.assertTrue(selected["selection"]["epoch_zero_selected"])
        self.assertFalse(audit["model_loaded"])
        result = json.loads((self.root / path).read_text())
        result["final_checkpoint"] = {"path": "wrong"}
        (self.root / path).write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError, "Final checkpoint"):
            evaluation.audit_completed_result(self.root, path)


if __name__ == "__main__":
    unittest.main()
