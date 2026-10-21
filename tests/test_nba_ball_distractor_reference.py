"""Actual candidate producer transport, native pixels and blank reference integrity."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from src.ball_tracking import nba_ball_distractor_reference as reference
from src.ball_tracking import nba_candidate_preservation as pools
from src.ball_tracking import nba_gap_anchor_reference as source_reference
from src.ball_tracking import nba_wasb_diagnostic as d
from tests.test_nba_appearance_reference import scope_fixture as appearance_fixture
from tests.test_nba_gap_anchor_reference import write_json


def scope_fixture(root):
    prior = appearance_fixture(root)
    repository = Path(__file__).resolve().parents[1]
    (root / "src/ball_tracking/nba_ball_distractor_reference.py").write_bytes(
        (repository / "src/ball_tracking/nba_ball_distractor_reference.py").read_bytes())
    selection = d.read_json(root / prior["selection"]["path"])
    targets, blocks = [], {}
    for spec in prior["targets"]:
        cid, index = spec["continuous_source_id"], spec["source_frame_index"]
        role = "fit" if spec["role"] == "fit_eligible" else "check"
        targets.append({"target_id": f"{cid}:{index}", "continuous_source_id": cid, "source_frame_index": index,
            "source_pts_ticks": selection["sources"][0 if cid == "nba_source" else 1]["frames"][index]["source_pts_ticks"],
            "role": role, "block_id": spec["block_id"], "block_range_inclusive": [0, 79],
            "context_range_inclusive": [index-2, index+2], "segment_id": cid+":0-79"})
        blocks[spec["block_id"]] = {"source": cid, "role": role, "range_inclusive": [0, 79], "candidate_quota": 0}
    grid = write_json(root, "data/outputs/design/grid.json", {"targets": targets})
    sources = {s["candidate_id"]: s for s in selection["sources"]}
    candidates, target_bindings = [], []
    for target in targets:
        cid, index = target["continuous_source_id"], target["source_frame_index"]
        source = sources[cid]; original = source["frames"][index]
        plane = np.zeros((288, 512), np.float32); plane[40, 400] = .8
        # Real mean-component producer from appearance_fixture, and real retained
        # contributor producer here. No consumer-only invented component shape.
        pool = pools.build_pool("old", cid, index, original["original_observation"], [(index-1, 1, plane)], (64, 40))
        groups = []
        for number, group in enumerate(pool["coordinate_groups"]):
            records = [pool["records"][i] for i in group["record_indices"]]
            groups.append({**group, "candidate_group_id": f"{cid}:{index}:coordinate:{number}",
                "provenance_ids": [r["provenance_id"] for r in records],
                "provenance_kinds": sorted({r["provenance_id"][3] for r in records}),
                "emitted_in_saved_selection": number == 0, "existing_object_label": None, "in_source_bounds": True})
        record = {"grid": grid, "target": target, "source_video": source["source_video"], "source_frame": original["source_frame"],
            "original_mean_reproduced_exactly": True, "original_observation": original["original_observation"],
            "pool": pool, "candidate_groups": groups}
        binding = write_json(root, f"data/outputs/design/{cid}_{index}.json", record); target_bindings.append(binding)
        for group in groups:
            candidates.append({**target, **{k: group[k] for k in ("candidate_group_id", "center_xy_px", "provenance_ids", "provenance_kinds", "emitted_in_saved_selection")},
                "pool_record_indices": group["record_indices"], "components": [pool["records"][i]["component"] for i in group["record_indices"]],
                "target_record": binding, "source_video": source["source_video"], "source_frame": original["source_frame"],
                "object_classification": None, "physical_object_instance_id": None})
            blocks[target["block_id"]]["candidate_quota"] += 1
    completed = write_json(root, "data/outputs/design/completed.json", {"grid": grid, "target_records": target_bindings})
    registry = write_json(root, "data/outputs/design/registry.json", {"grid": grid, "full_pool_completion": completed, "candidate_records": candidates})
    candidate = candidates[-1]; slot = {k: candidate[k] for k in ("continuous_source_id", "source_frame_index", "source_pts_ticks", "block_id",
        "block_range_inclusive", "context_range_inclusive", "source_video", "source_frame", "target_record")}
    slot.update({"slot_id": "contrast:nfhs:30:head", "role": "fit_only_contrast", "domain": "nfhs", "requested_subtype": "head",
        "replacement_allowed": False, "object_center_xy_px": None, "object_classification": None, "physical_object_instance_id": None,
        "anchor_kind": "saved_selected_emission", "distance_anchor_points_xy_px": [[20, 20]]})
    contrasts = write_json(root, "data/outputs/design/contrasts.json", {"candidate_registry": registry, "slots": [slot]})
    accepted_candidates = [{"candidate_key": f"old:{i}", "continuous_source_id": "nba_source", "source_frame_index": 60,
        "role": "excluded_check", "center_xy_px": [20+i, 20]} for i in range(2)]
    accepted_rows = [{"candidate_key": "old:0", "classification": "ball", "subtype": None, "rationale": "Accepted source review."},
                     {"candidate_key": "old:1", "classification": "unresolved", "subtype": None, "rationale": "Accepted uncertainty."}]
    accepted = write_json(root, "data/outputs/accepted.json", {"status": "human_accepted_assisted_reference",
        "frames": [{"continuous_source_id": "nba_source", "source_frame_index": 60}], "candidates": accepted_candidates, "rows": accepted_rows})
    nfhs = d.read_json(root / prior["fit_authority"]["path"])["nfhs_training_config"]
    plan = write_json(root, "docs/plan.json", {"purpose": "Synthetic bounded source preparation"})
    proposal = {"schema_version": reference.PROPOSAL_SCHEMA, "plan": plan, "source_blocks": blocks,
        "design_evidence": {"grid": grid, "full_pool_reconstruction": completed, "candidate_registry": registry, "contrast_slots": contrasts},
        "authorities": {"selection": prior["selection"], "accepted_appearance": accepted, "old_34_regression_preparation": prior["regression_preparation"],
                        "nba_fit_authority": prior["fit_authority"], "nfhs_fit_authority": nfhs},
        "new_label_budget": {"candidate_fit": 3, "candidate_excluded_check": 6, "source_authored_fit_contrast_slots": 1,
            "total_attempted_maximum": 10, "unique_target_frames": 3, "unique_context_frames": 15, "context_radius_frames": 2, "replacements_allowed": False}}
    proposal_binding = write_json(root, "configs/proposal.json", proposal)
    approval = {"schema_version": reference.APPROVAL_SCHEMA, "status": "approved", "approved_by": "Ryan", "label_preparation_authorized": True,
                "proposal": proposal_binding, "plan": plan, "design_evidence": proposal["design_evidence"]}
    write_json(root, "configs/approval.json", approval)
    return {"proposal_path": root / "configs/proposal.json", "approval_path": root / "configs/approval.json", "proposal": proposal,
            "approval": approval, "output": root / "data/outputs/reference"}


def prepared_fixture(root):
    fixture = scope_fixture(root); requests = []
    def decoder(_root, possession, segment):
        source_reference.nfhs.guard_segment(possession, segment); requests.append(segment)
        for index in range(segment[0], segment[1]+1):
            yield index, np.full((40, 64, 3), index, np.uint8)
    with patch.object(source_reference.nfhs, "decode_segment", decoder):
        preparation = reference.prepare(root, fixture["proposal_path"], fixture["approval_path"], fixture["output"])
    return {**fixture, "preparation": preparation, "preparation_path": fixture["output"] / "preparation.json", "decode_requests": requests}


class BallDistractorReferenceTests(unittest.TestCase):
    def test_actual_mean_contributor_transport_and_native_source_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); fixture = prepared_fixture(root); prep = fixture["preparation"]
            self.assertEqual(prep["totals"]["new_review_rows"], 10)
            self.assertEqual(fixture["decode_requests"], [[28, 32]])
            self.assertEqual(prep["resources"]["existing_png_reads"], 10)
            self.assertEqual(prep["resources"]["nfhs_decoded_frames"], 5)
            self.assertEqual({p for c in prep["candidates"] for p in c["provenance_kinds"]}, {"mean", "contributor"})
            self.assertTrue(all(r["classification"] is None and r["physical_object_instance_id"] is None for r in prep["new_review_rows"]))
            self.assertIsNone(prep["new_review_rows"][-1]["center_xy_px"])
            self.assertEqual(prep["frames"][-1]["container_pts_ticks"], 33*3600)
            self.assertEqual(reference.load_ready_preparation(root, fixture["preparation_path"]), prep)
            with patch.object(source_reference, "extract_frames", side_effect=AssertionError("must not extract")):
                self.assertEqual(reference.prepare(root, fixture["proposal_path"], fixture["approval_path"], fixture["output"]), prep)

    def test_controls_remain_exact_and_new_metadata_is_frozen_before_pixels(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); fixture = prepared_fixture(root)
            frozen = d.read_json(fixture["output"] / "metadata.json")
            accepted = d.read_json(root / fixture["proposal"]["authorities"]["accepted_appearance"]["path"])
            self.assertEqual([r["accepted_row"] for r in frozen["reused_controls"]], accepted["rows"])
            self.assertEqual([r["accepted_candidate"] for r in frozen["reused_controls"]], accepted["candidates"])
            self.assertTrue(all(r["physical_object_instance_id"] is None for r in frozen["reused_controls"]))
            self.assertEqual(frozen["pixel_reads"], 0)
            self.assertFalse(any("raw_png" in f for f in frozen["frames"]))

    def test_provenance_roles_approval_and_excluded_context_fail_before_pixels(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); fixture = scope_fixture(root)
            for kind in ("approval", "role", "excluded", "provenance"):
                proposal, approval = copy.deepcopy(fixture["proposal"]), copy.deepcopy(fixture["approval"])
                if kind == "approval":
                    approval["status"] = "pending"
                elif kind == "role":
                    proposal["source_blocks"]["nba_source_block"]["role"] = "fit"
                elif kind == "excluded":
                    proposal["authorities"]["old_34_regression_preparation"] = write_json(root, "data/outputs/bad_regression.json", {
                        "frames": [{"continuous_source_id": "nba_source", "source_frame_index": 5}]})
                else:
                    binding = proposal["design_evidence"]["candidate_registry"]
                    registry = d.read_json(root / binding["path"]); registry["candidate_records"][0]["center_xy_px"][0] += 1
                    new = write_json(root, "data/outputs/bad_registry.json", registry)
                    contrasts = d.read_json(root / proposal["design_evidence"]["contrast_slots"]["path"])
                    contrasts["candidate_registry"] = new
                    proposal["design_evidence"]["candidate_registry"] = new
                    proposal["design_evidence"]["contrast_slots"] = write_json(root, "data/outputs/bad_contrasts.json", contrasts)
                    approval["design_evidence"] = proposal["design_evidence"]
                binding = write_json(root, "configs/mutated.json", proposal); approval["proposal"] = binding
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    reference.census(root, proposal, approval, binding)

    def test_source_failure_is_preserved_and_readiness_and_png_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); fixture = scope_fixture(root)
            video = root / "data/clips/possession_fixture.mp4"; original = video.read_bytes(); video.write_bytes(b"changed")
            with patch.object(source_reference, "extract_frames") as extract:
                with self.assertRaisesRegex(ValueError, "source video bytes"):
                    reference.prepare(root, fixture["proposal_path"], fixture["approval_path"], fixture["output"])
                extract.assert_not_called()
            self.assertEqual(len(list(fixture["output"].glob("attempts/*/failed.json"))), 1)
            self.assertFalse((fixture["output"] / "preparation_ready.json").exists())
            video.write_bytes(original)
            def decoder(_root, possession, segment):
                source_reference.nfhs.guard_segment(possession, segment)
                for index in range(segment[0], segment[1]+1):
                    yield index, np.full((40, 64, 3), index, np.uint8)
            with patch.object(source_reference.nfhs, "decode_segment", decoder):
                prep = reference.prepare(root, fixture["proposal_path"], fixture["approval_path"], fixture["output"])
            path = fixture["output"] / "preparation.json"; png = root / prep["frames"][0]["raw_png"]["path"]
            original = png.read_bytes(); png.write_bytes(original+b"changed")
            with self.assertRaisesRegex(ValueError, "PNG hash"):
                reference.load_ready_preparation(root, path)
            png.write_bytes(original); prep["new_review_rows"][0]["classification"] = "ball"
            write_json(root, path.relative_to(root).as_posix(), prep)
            with self.assertRaisesRegex(ValueError, "changed after freeze"):
                reference.load_ready_preparation(root, path)


if __name__ == "__main__":
    unittest.main()
