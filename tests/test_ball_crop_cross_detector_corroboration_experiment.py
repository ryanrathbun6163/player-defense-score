"""Artificial phase and publication checks; no project scientific inputs."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

from src.ball_tracking import crop_cross_detector_corroboration_experiment as study


def protocol():
    names = ["synthetic_" + str(i) for i in range(6)]
    values = [study.FixtureArtifact.from_json("input/" + role, role,
              {"role": role, "inert_pointer": "data/clips/not_permitted.mp4"})
              for role in ("rf_candidates", "yolo_candidates", "annotations", "saved_controls", "source_png")]
    access = study.PhaseAccess(values, names, fixture_id="synthetic:protocol")
    limits = {f"selection/{n}/observations.json": 1024 for n in names}
    limits["summary.json"] = 1024
    sink = study.OutputSink(limits, maximum_bytes=8192)
    bindings = [sink.json(f"selection/{n}/observations.json", {"window": n}) for n in names]
    return access, sink, bindings


class PhaseBoundaryTests(unittest.TestCase):
    def test_real_entrypoints_refuse_before_any_file_access_even_with_fake_release(self):
        with patch("builtins.open", side_effect=AssertionError("no read")), \
             patch.object(Path, "read_bytes", side_effect=AssertionError("no body")), \
             patch.object(Path, "exists", side_effect=AssertionError("no metadata")):
            for call in (lambda: study.run_study("data/outputs/science.json", approved=True),
                         lambda: study.run_study(dry_run=True, synthetic=True),
                         lambda: study.main(["--release", "invented.json"])):
                with self.assertRaisesRegex(PermissionError, "separately approved inventory"):
                    call()

    def test_only_declared_role_is_read_and_embedded_pointer_stays_inert(self):
        access, _, _ = protocol()
        self.assertEqual(access.json("input/rf_candidates")["inert_pointer"], "data/clips/not_permitted.mp4")
        for name in ("input/annotations", "input/saved_controls", "input/source_png", "data/clips/not_permitted.mp4"):
            with self.assertRaises(ValueError):
                access.read(name)
        self.assertEqual(len(access.access_log), 1)

    def test_all_six_unique_exact_outputs_required_before_evaluation(self):
        access, sink, bindings = protocol()
        for invalid in (bindings[:5], [bindings[0]] * 6, [dict(b, sha256="0" * 64) for b in bindings]):
            with self.assertRaises(ValueError):
                access.freeze(invalid, sink)
            self.assertEqual(access.phase, "selection")
        access.freeze(bindings, sink)
        self.assertEqual(access.json("input/annotations")["role"], "annotations")
        with self.assertRaises(ValueError):
            access.read("input/source_png")
        with self.assertRaises(ValueError):
            access.read("input/rf_candidates")
        with self.assertRaises(ValueError):
            access.freeze(bindings, sink)

    def test_modified_selection_is_detected_before_later_input_access(self):
        access, sink, bindings = protocol()
        access.freeze(bindings, sink)
        sink._payloads[bindings[0]["path"]] = b"tampered"
        with self.assertRaisesRegex(ValueError, "Sealed output"):
            access.read("input/annotations")
        with self.assertRaises(ValueError):
            access.begin_review()
        self.assertEqual(access.access_log, [])

    def test_freeze_copies_bindings_and_review_cannot_reopen_scoring_inputs(self):
        access, sink, bindings = protocol()
        access.freeze(bindings, sink)
        bindings[0]["sha256"] = "0" * 64
        access.begin_review()
        self.assertEqual(access.json("input/source_png")["role"], "source_png")
        with self.assertRaises(ValueError):
            access.read("input/saved_controls")
        access.close()
        with self.assertRaises(ValueError):
            access.read("input/source_png")
        with self.assertRaises(ValueError):
            access.begin_review()

    def test_failure_permanently_closes_access_without_adopting_partial_outputs(self):
        access, sink, bindings = protocol()
        access.fail()
        for action in (lambda: access.read("input/rf_candidates"),
                       lambda: access.freeze(bindings, sink), access.close):
            with self.assertRaises(ValueError):
                action()
        self.assertEqual(access.phase, "failed")


class OutputAndFixtureTests(unittest.TestCase):
    def test_create_only_exact_names_and_per_file_aggregate_bounds(self):
        sink = study.OutputSink({"a.json": 8, "b.json": 8}, maximum_bytes=10)
        binding = sink.write("a.json", b"123456")
        self.assertEqual(binding["size_bytes"], 6)
        for name, data in (("a.json", b"x"), ("unknown", b"x"), ("b.json", b"x" * 9), ("b.json", b"x" * 5)):
            with self.assertRaises(ValueError):
                sink.write(name, data)
        with self.assertRaises(ValueError):
            sink.complete()
        sink.write("b.json", b"1234")
        self.assertEqual(len(sink.complete()), 2)
        with self.assertRaises(ValueError):
            sink.complete()

    def test_paths_cannot_escape_or_alias_declared_names(self):
        for name in ("../a", "a/../b", "./a", "a//b", "a/", "/a", "C:/a", "a\\b"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                study.OutputSink({name: 1})
        for maximum in (0, True, study.MAX_OUTPUT_BYTES + 1):
            with self.assertRaises(ValueError):
                study.OutputSink({"a": 1}, maximum_bytes=maximum)

    def test_input_digest_duplicate_roles_and_artificial_provenance(self):
        artifact = study.FixtureArtifact.from_json("candidate/a", "rf_candidates", {"synthetic": True})
        names = [str(i) for i in range(6)]
        with self.assertRaisesRegex(ValueError, "digest"):
            study.FixtureArtifact("candidate/a", "rf_candidates", artifact.payload, "0" * 64)
        with self.assertRaises(ValueError):
            study.FixtureArtifact("candidate/a", "rf_candidates", bytearray(b"{}"), hashlib.sha256(b"{}").hexdigest())
        with self.assertRaises(ValueError):
            study.PhaseAccess([artifact, artifact], names, fixture_id="synthetic:test")
        with self.assertRaises(ValueError):
            study.PhaseAccess([artifact], names, fixture_id="real:test")

    def test_missing_window_invalid_pool_and_short_window_refused(self):
        windows = [{"window_id": "synthetic_" + str(i), "purpose": study.evaluation.POOLS[i % 2],
                    "start_frame_index": 0, "end_frame_index": 24} for i in range(6)]
        study._windows(windows)
        for changed in (windows[:5], [windows[0]] * 6):
            with self.assertRaises(ValueError):
                study._windows(changed)
        for key, value in (("purpose", "test_holdout"), ("end_frame_index", 23),
                           ("start_frame_index", True), ("window_id", "actual_project_window")):
            altered = deepcopy(windows)
            altered[0][key] = value
            with self.assertRaises(ValueError):
                study._windows(altered)


def comparison_fixture():
    from test_ball_crop_cross_detector_corroboration_evaluation import fixture, control_reference
    windows, inputs, limits = [], [], {}
    for index in range(6):
        labels, rf, yolo, observations, reports, window = fixture(
            count=25, start=index * 30, purpose=study.evaluation.POOLS[index % 2],
            possession="possession_" + f"{index // 2 + 1:03d}", hidden=(15, 16, 17, 18, 19) if index == 5 else ())
        ident = "synthetic_window_" + str(index)
        window["window_id"] = ident
        windows.append(window)
        controls = {"observations": {}, "reports": {}, "observation_references": {}, "report_references": {}}
        for arm in study.evaluation.CONTROLS:
            controls["observations"][arm], controls["reports"][arm] = observations[arm], reports[arm]
            ref = control_reference(observations[arm], reports[arm])
            controls["observation_references"][arm] = ref
            controls["report_references"][arm] = ref
        for prefix, role, value in (("rf/", "rf_candidates", rf.to_dict()),
                                    ("yolo/", "yolo_candidates", yolo.to_dict()),
                                    ("labels/", "annotations", labels.to_dict()),
                                    ("controls/", "saved_controls", controls),
                                    ("image/", "source_png", {"artificial": True})):
            inputs.append(study.FixtureArtifact.from_json(prefix + ident, role, value))
        limits[f"selection/{ident}/observations.json"] = 1024 * 1024
        limits[f"evaluation/{ident}.json"] = 1024 * 1024
    for purpose in study.evaluation.POOLS:
        limits[f"evaluation/{purpose}.json"] = 2 * 1024 * 1024
    limits["summary.json"] = study.MAX_RETURN_BYTES
    return windows, inputs, limits


class ArtificialIntegrationTests(unittest.TestCase):
    def test_six_selections_seal_before_six_new_evaluations_and_review(self):
        windows, inputs, limits = comparison_fixture()
        for window in windows:
            limits[f"review/{window['window_id']}/synthetic.json"] = 1024
        access = study.PhaseAccess(inputs, [w["window_id"] for w in windows], fixture_id="synthetic:integration")
        sink = study.OutputSink(limits)
        rendered = []

        def render(**kwargs):
            ident = kwargs["window"]["window_id"]
            self.assertEqual(kwargs["access"].phase, "review")
            self.assertEqual(set(kwargs["observations_by_arm"]), {study.evaluation.TOP, study.selector.ARM})
            self.assertTrue(kwargs["access"].json("image/" + ident)["artificial"])
            kwargs["sink"].json(f"review/{ident}/synthetic.json", {"artificial_only": True})
            rendered.append(ident)

        before = [(a.name, a.payload, a.sha256) for a in inputs]
        with patch.object(study.selector, "select_candidates", wraps=study.selector.select_candidates) as selected, \
             patch.object(study.evaluation, "evaluate_detections", wraps=study.evaluation.evaluate_detections) as evaluated:
            result = study.run_synthetic_comparison(windows, access, sink, "d" * 40, render=render)
        self.assertEqual(selected.call_count, 6)
        self.assertEqual(evaluated.call_count, 6)
        self.assertEqual(access.phase, "complete")
        self.assertEqual(rendered, [w["window_id"] for w in windows])
        self.assertEqual([(a.name, a.payload, a.sha256) for a in inputs], before)
        phases = [row["phase"] for row in result["access_log"]]
        self.assertEqual(phases, ["selection"] * 12 + ["evaluation"] * 12 + ["review"] * 6)
        self.assertEqual(result["summary"]["journal_events"], 0)
        self.assertFalse(result["summary"]["scientific_execution"])
        self.assertLessEqual(len(study._json_bytes(result)), study.MAX_RETURN_BYTES)
        self.assertEqual(len(result["artifacts"]), len(limits))

    def test_invalid_sixth_window_never_reads_labels_controls_or_pixels(self):
        windows, inputs, limits = comparison_fixture()
        name = "yolo/" + windows[-1]["window_id"]
        row = next(a for a in inputs if a.name == name)
        value = study.json.loads(row.payload)
        value["source_video"]["sha256"] = "1" * 64
        # A valid outer binding cannot disguise an invalid/mismatched source contract.
        inputs[inputs.index(row)] = study.FixtureArtifact.from_json(row.name, row.role, value)
        access = study.PhaseAccess(inputs, [w["window_id"] for w in windows], fixture_id="synthetic:invalid")
        sink = study.OutputSink(limits)
        with self.assertRaises(ValueError):
            study.run_synthetic_comparison(windows, access, sink, "d" * 40)
        self.assertEqual(access.phase, "failed")
        self.assertTrue(all(row["phase"] == "selection" for row in access.access_log))
        self.assertNotIn("summary.json", sink._payloads)

    def test_oversized_complete_return_cannot_be_reported_successfully(self):
        windows, inputs, limits = comparison_fixture()
        access = study.PhaseAccess(inputs, [w["window_id"] for w in windows], fixture_id="synthetic:return")
        sink = study.OutputSink(limits)
        original = sink.complete

        def large_inventory():
            return original() + [{"path": "a" * (study.MAX_RETURN_BYTES + 1)}]

        with patch.object(sink, "complete", side_effect=large_inventory), self.assertRaisesRegex(ValueError, "complete fixture return"):
            study.run_synthetic_comparison(windows, access, sink, "d" * 40)
        self.assertEqual(access.phase, "failed")


if __name__ == "__main__":
    unittest.main()
