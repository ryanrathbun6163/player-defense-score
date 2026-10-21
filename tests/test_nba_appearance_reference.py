"""Producer-derived appearance census, authority boundaries and label transport."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from src.ball_tracking import nba_appearance_reference as appearance
from src.ball_tracking import nba_action_observation as action
from src.ball_tracking import nba_gap_anchor_reference as source_reference
from src.ball_tracking import nba_temporal_gap_continuous as continuous
from src.ball_tracking import nba_wasb_diagnostic as d
from tests.test_nba_gap_anchor_reference import source_fixture, write_json
from tests.test_nba_temporal_gap_continuous import produced_context, resources


def scope_fixture(root):
    old = source_fixture(root)
    repository = Path(__file__).resolve().parents[1]
    (root / "src/ball_tracking/nba_appearance_reference.py").write_bytes(
        (repository / "src/ball_tracking/nba_appearance_reference.py").read_bytes())
    selection = d.read_json(root / old["selection"]["path"])
    targets = []
    for source, indices, role in ((selection["sources"][0], (5, 20), "excluded_check"),
                                  (selection["sources"][1], (30,), "fit_eligible")):
        cid = source["candidate_id"]
        for index in indices:
            # Actual producing code converts a weighted native heatmap into
            # source-pixel components. No consumer-shaped candidate fixture.
            heatmap = np.zeros((288, 512), np.float32)
            heatmap[100, 100:102] = [.4, .8]
            heatmap[180, 300] = .7
            frame = source["frames"][index]
            source_frame = {**frame["source_frame"], "png": {"path": "unused_nfhs.png"}}
            if source["kind"] == "nba":
                source_frame = frame["source_frame"]
            observed = action.select_observation(source_frame, heatmap, 3,
                {"source_video": source["source_video"], "time_base": "1/90000"},
                {"kind": "live_action", "source_frame_range_inclusive": [0, 79]})
            if source["kind"] == "nfhs":
                observed["frame_index"] = index
            frame["original_observation"] = observed
            targets.append({"target_id": f"{cid}_{index}", "block_id": cid + "_block",
                "continuous_source_id": cid, "source_frame_index": index, "role": role,
                "complete_block_range_inclusive": [0, 79]})
    selection_binding = write_json(root, "data/outputs/appearance_selection.json", selection)
    nfhs = selection["sources"][1]
    nfhs_binding = write_json(root, "configs/fit_nfhs.json", {"training_blocks": [{
        "possession_id": nfhs["candidate_id"], "start_frame_index": 0, "end_frame_index": 79,
        "source_video": nfhs["source_video"]}]})
    fit_binding = write_json(root, "configs/fit.json", {"nba_training_windows": [], "nfhs_training_config": nfhs_binding})
    regression = write_json(root, "data/outputs/regression.json", {"schema_version": source_reference.SCHEMA,
        "status": "source_preparation_complete", "frames": [{"continuous_source_id": "nba_source", "source_frame_index": 60}]})
    scope = {"schema_version": appearance.SCOPE_SCHEMA, "status": "approved", "selection": selection_binding,
        "regression_preparation": regression, "fit_authority": fit_binding, "context_radius_frames": 2,
        "source_roles": {"nba_source": "excluded_check", "possession_fixture": "fit_eligible"},
        "targets": targets, "expected_totals": {"targets": 3, "candidates": 6, "context_frames": 15}}
    write_json(root, "configs/appearance_scope.json", scope)
    return scope


def prepared_fixture(root):
    scope = scope_fixture(root)
    appearance.freeze(root, "configs/appearance_scope.json", "data/outputs/appearance")
    requests = []
    def decoder(_root, possession, segment):
        source_reference.nfhs.guard_segment(possession, segment)
        requests.append(segment)
        for index in range(segment[0], segment[1]+1):
            yield index, np.full((40, 64, 3), index, np.uint8)
    with patch.object(source_reference.nfhs, "decode_segment", decoder):
        prep = appearance.prepare(root, "data/outputs/appearance/metadata.json")
    path = root / "data/outputs/appearance/preparation.json"
    proposal = {"schema_version": appearance.PROPOSAL_SCHEMA, "preparation": d.binding(root, path),
        "authorship": {"annotator_id": "AI synthetic fixture", "method": "source_first_ai", "not_blind": True},
        "human_review": "pending", "rows": [{"candidate_key": c["candidate_key"], "classification": "unresolved",
            "subtype": None, "rationale": "Synthetic source provides no basketball identity."} for c in prep["candidates"]]}
    proposed_path = root / "data/outputs/appearance/proposal.json"
    write_json(root, proposed_path.relative_to(root).as_posix(), proposal)
    return {"scope": scope, "preparation": prep, "preparation_path": path,
            "proposal": proposal, "proposal_path": proposed_path, "decode_requests": requests}


class AppearanceReferenceTests(unittest.TestCase):
    def test_actual_candidate_producer_freeze_extract_resume_and_proposal_transport(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); fixture = prepared_fixture(root); prep = fixture["preparation"]
            self.assertEqual(prep["totals"], {"targets": 3, "candidates": 6, "context_frames": 15})
            self.assertEqual(fixture["decode_requests"], [[28, 32]])
            frozen = d.read_json(root / "data/outputs/appearance/metadata.json")
            self.assertEqual(frozen["pixel_reads"], 0)
            self.assertFalse(any("raw_png" in f for f in frozen["frames"]))
            selection = d.read_json(root / fixture["scope"]["selection"]["path"])
            original = selection["sources"][0]["frames"][5]["original_observation"]["candidates"]
            self.assertEqual([c["component"] for c in prep["candidates"][:2]], original)
            self.assertEqual(prep["candidates"][0]["provenance_id"], ["old", "nba_source", 5, "mean", None, None, 0])
            self.assertNotEqual(prep["candidates"][0]["center_xy_px"][0], 100 * 64 / 512)
            self.assertEqual(prep["frames"][-1]["container_pts_ticks"], 33*3600)
            with patch.object(source_reference.nfhs, "decode_segment", side_effect=AssertionError("must not decode")):
                self.assertEqual(appearance.prepare(root, "data/outputs/appearance/metadata.json"), prep)
            loaded, proposed = appearance.validate_proposal(root, fixture["proposal_path"])
            self.assertEqual(loaded, prep); self.assertEqual(proposed, fixture["proposal"])

    def test_actual_continuous_emitted_original_candidate_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); context, _, _, reader = produced_context(root)
            segment = continuous.select_segment(root, context, resources(), cache_reader=reader)
            source = {**context["source"], "segments": [segment], "frames": segment["frames"], "time_origin": "native_container"}
            selection = write_json(root, "data/outputs/selection.json", {"schema_version": continuous.SCHEMA, "sources": [source]})
            nfhs = write_json(root, "configs/nfhs.json", {"training_blocks": []})
            fit = write_json(root, "configs/fit.json", {"nba_training_windows": [], "nfhs_training_config": nfhs})
            reg = write_json(root, "data/outputs/reg.json", {"schema_version": source_reference.SCHEMA,
                "status": "source_preparation_complete", "frames": []})
            scope = {"schema_version": appearance.SCOPE_SCHEMA, "status": "approved", "selection": selection,
                "fit_authority": fit, "regression_preparation": reg, "context_radius_frames": 2,
                "source_roles": {"synthetic": "excluded_check"}, "targets": [{"target_id": "actual3", "block_id": "actual",
                    "continuous_source_id": "synthetic", "source_frame_index": 3, "role": "excluded_check",
                    "complete_block_range_inclusive": [0, 13]}]}
            frozen, _ = appearance.census(root, scope)
            original = segment["frames"][3]["original_observation"]["candidates"]
            self.assertEqual([c["component"] for c in frozen["candidates"]], original)
            self.assertEqual(frozen["frames"][2]["source_frame"], segment["frames"][3]["source_frame"])

    def test_protected_block_regression_role_and_clock_exclusions_before_pixels(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); scope = scope_fixture(root)
            mutations = []
            value = copy.deepcopy(scope); value["targets"][0]["source_frame_index"] = 1; mutations.append(value)
            value = copy.deepcopy(scope); value["targets"][0]["source_frame_index"] = 60; mutations.append(value)
            value = copy.deepcopy(scope); value["targets"][1]["source_frame_index"] = 7; mutations.append(value)
            value = copy.deepcopy(scope); value["targets"][2]["complete_block_range_inclusive"] = [0, 89]; value["targets"][2]["source_frame_index"] = 80; mutations.append(value)
            value = copy.deepcopy(scope); value["targets"][0]["role"] = "fit_eligible"; mutations.append(value)
            value = copy.deepcopy(scope); value["source_roles"]["nba_source"] = "fit_eligible"
            for t in value["targets"][:2]: t["role"] = "fit_eligible"
            mutations.append(value)
            with patch.object(source_reference, "extract_frames", side_effect=AssertionError("must not extract")):
                for value in mutations:
                    with self.subTest(value=value["targets"]), self.assertRaises(ValueError):
                        appearance.census(root, value)
            selected = d.read_json(root / scope["selection"]["path"])
            selected["sources"][0]["frames"][5]["original_observation"]["source_pts_ticks"] += 1
            scope["selection"] = write_json(root, "data/outputs/altered.json", selected)
            with self.assertRaisesRegex(ValueError, "clock"):
                appearance.census(root, scope)

    def test_exact_label_census_unknowns_and_no_fabricated_geometry(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); fixture = prepared_fixture(root)
            original = fixture["proposal"]
            for change in ("omit", "duplicate", "geometry", "accept", "wrong_class", "blank", "subtype"):
                value = copy.deepcopy(original)
                if change == "omit": value["rows"].pop()
                elif change == "duplicate": value["rows"][-1] = value["rows"][0]
                elif change == "geometry": value["rows"][0]["center_xy_px"] = [1, 2]
                elif change == "accept": value["human_review"] = "accepted"
                elif change == "wrong_class": value["rows"][0]["classification"] = "negative_from_distance"
                elif change == "blank": value["rows"][0]["rationale"] = " "
                else: value["rows"][0]["subtype"] = "head"
                path = root / f"data/outputs/{change}.json"; write_json(root, path.relative_to(root).as_posix(), value)
                with self.subTest(change=change), self.assertRaises(ValueError): appearance.validate_proposal(root, path)
            value = copy.deepcopy(original); value["rows"][0].update(classification="other_object", subtype="head")
            write_json(root, "data/outputs/other.json", value)
            appearance.validate_proposal(root, "data/outputs/other.json")

    def test_changed_nfhs_video_fails_before_decode_and_preserves_failed_attempt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); scope_fixture(root)
            appearance.freeze(root, "configs/appearance_scope.json", "data/outputs/appearance")
            (root / "data/clips/possession_fixture.mp4").write_bytes(b"changed source")
            with patch.object(source_reference.nfhs, "decode_segment", side_effect=AssertionError("must not decode")):
                with self.assertRaisesRegex(ValueError, "video bytes changed"):
                    appearance.prepare(root, "data/outputs/appearance/metadata.json")
            self.assertEqual(len(list((root / "data/outputs/appearance/attempts").glob("*/failed.json"))), 1)
            self.assertFalse((root / "data/outputs/appearance/preparation_ready.json").exists())


if __name__ == "__main__":
    unittest.main()
