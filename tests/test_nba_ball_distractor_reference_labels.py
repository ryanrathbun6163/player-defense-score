"""Producer-derived draft labels, physical grouping and provisional scientific gates."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from src.ball_tracking import nba_ball_distractor_reference as reference
from src.ball_tracking import nba_ball_distractor_reference_labels as labels
from src.ball_tracking import nba_gap_anchor_reference as source_reference
from src.ball_tracking import nba_wasb_diagnostic as d
from tests.test_nba_ball_distractor_reference import scope_fixture
from tests.test_nba_gap_anchor_reference import write_json


def labeled_fixture(root):
    fixture = scope_fixture(root); repository = Path(__file__).resolve().parents[1]
    module = root / "src/ball_tracking/nba_ball_distractor_reference_labels.py"
    module.write_bytes((repository / "src/ball_tracking/nba_ball_distractor_reference_labels.py").read_bytes())
    # The actual approved scientific gate schema is the source of this fixture.
    approved = json.loads((repository / "configs/ball_tracking/proposals/nba_ball_distractor_verifier_v0_1.json").read_text())
    fixture["proposal"]["pre_fit_adequacy"] = approved["pre_fit_adequacy"]
    binding = write_json(root, "configs/proposal.json", fixture["proposal"])
    fixture["approval"]["proposal"] = binding
    write_json(root, "configs/approval.json", fixture["approval"])
    def decoder(_root, possession, segment):
        source_reference.nfhs.guard_segment(possession, segment)
        for index in range(segment[0], segment[1]+1):
            yield index, np.full((40, 64, 3), index, np.uint8)
    with patch.object(source_reference.nfhs, "decode_segment", decoder):
        prep = reference.prepare(root, fixture["proposal_path"], fixture["approval_path"], fixture["output"])
    rows = []
    for candidate in prep["candidates"]:
        number = int(candidate["candidate_group_id"].split(":")[-1])
        classification = "ball" if number == 0 else "other_object"
        subtype = None if number == 0 else ("head" if number == 1 else "clothing")
        rows.append({"row_id": candidate["candidate_group_id"], "center_xy_px": candidate["center_xy_px"],
            "classification": classification, "subtype": subtype,
            "physical_object_instance_id": candidate["target_id"]+f":object{number}",
            "episode_id": candidate["block_id"]+f":object{number}", "rationale": "Synthetic visible source judgment.",
            "duplicate_of_row_id": None})
    candidate = prep["candidates"][-2]; slot = prep["contrast_slots"][0]
    rows.append({"row_id": slot["slot_id"], "center_xy_px": [30, 10], "classification": "other_object", "subtype": "head",
        "physical_object_instance_id": candidate["target_id"]+":object1", "episode_id": candidate["block_id"]+":object1",
        "rationale": "Source-authored head is already the candidate object.", "duplicate_of_row_id": candidate["candidate_group_id"],
        "object_extent_xyxy_px": [25, 5, 35, 15]})
    documents = [{"human_review": "pending", "authorship": {"annotator_id": "AI fixture", "method": "source_first_ai", "not_blind": True}, "rows": rows}]
    old = {"accepted_reference": fixture["proposal"]["authorities"]["accepted_appearance"], "accepted_classes_changed": False,
        "authorship": {"annotator_id": "AI fixture", "method": "grouping_existing_accepted_labels", "not_blind": True}, "rows": []}
    for control in prep["reused_controls"]:
        candidate, label, block = (control[k] for k in ("accepted_candidate", "accepted_row", "historical_block"))
        resolved = label["classification"] != "unresolved"
        old["rows"].append({"candidate_key": candidate["candidate_key"], "accepted_classification_unchanged": label["classification"],
            "block_id": block["block_id"], "role": block["role"], "physical_object_instance_id": "old_ball" if resolved else None,
            "episode_id": "old_ball_episode" if resolved else None, "rationale": "Accepted labels unchanged; group only."})
    annotations = write_json(root, "data/outputs/annotations.json", documents[0])
    grouping = write_json(root, "data/outputs/grouping.json", old)
    return {**fixture, "preparation": prep, "preparation_path": fixture["output"] / "preparation.json", "documents": documents,
            "reused": old, "annotations_path": root / annotations["path"], "grouping_path": root / grouping["path"]}


class BallDistractorReferenceLabelsTests(unittest.TestCase):
    def test_actual_preparation_merge_retains_controls_unknowns_and_excludes_duplicate_contrast(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); fixture = labeled_fixture(root)
            output = root / "data/outputs/merged"
            result = labels.merge(root, fixture["preparation_path"], [fixture["annotations_path"]], fixture["grouping_path"], output)
            prep, loaded = labels.load_proposal(root, output / "proposal.json")
            self.assertEqual(loaded, result); self.assertEqual(prep, fixture["preparation"])
            self.assertEqual(len(result["rows"]), 10); self.assertEqual(result["reused_grouping"], fixture["reused"]["rows"])
            self.assertEqual(len(result["physical_groups"]), 10)  # nine new objects + one old; contrast is a duplicate.
            report = result["provisional_adequacy"]
            self.assertEqual(report["unknown_rows_unscored"], 1)
            self.assertEqual(report["supplemental_duplicate_rows_excluded"], 1)
            self.assertFalse(report["fit_authorized"]); self.assertFalse(report["feature_extraction_authorized"])
            self.assertIn("fit_groups", report["failed_gates"])
            self.assertIn("fit_contributor_classes", report["failed_gates"])
            self.assertEqual(report["resolved_group_counts"]["fit"]["nfhs"], {"ball": 1, "other_object": 2})

    def test_aliases_count_once_and_conflicting_classes_or_episodes_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = labeled_fixture(Path(folder))
            documents = copy.deepcopy(fixture["documents"])
            first, second = documents[0]["rows"][:2]
            second.update({"classification": first["classification"], "subtype": first["subtype"],
                           "physical_object_instance_id": first["physical_object_instance_id"], "episode_id": first["episode_id"]})
            result = labels.build(fixture["preparation"], fixture["proposal"], documents, fixture["reused"])
            self.assertEqual(len(result["physical_groups"]), 9)
            second["classification"] = "other_object"; second["subtype"] = "head"
            with self.assertRaisesRegex(ValueError, "Conflicting resolved"):
                labels.build(fixture["preparation"], fixture["proposal"], documents, fixture["reused"])
            second.update({"classification": "ball", "subtype": None, "episode_id": "different_episode"})
            with self.assertRaisesRegex(ValueError, "Conflicting resolved"):
                labels.build(fixture["preparation"], fixture["proposal"], documents, fixture["reused"])

    def test_fixed_points_contrast_domain_unknown_and_existing_classes_are_strict(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = labeled_fixture(Path(folder))
            for kind in ("point", "role", "contrast_bounds", "contrast_type", "unknown_group", "accepted_label", "duplicate", "incomplete"):
                documents, reused = copy.deepcopy(fixture["documents"]), copy.deepcopy(fixture["reused"])
                row = documents[0]["rows"][0]; contrast = documents[0]["rows"][-1]
                if kind == "point": row["center_xy_px"][0] += 1
                elif kind == "role": row["role"] = "fit"
                elif kind == "contrast_bounds": contrast["center_xy_px"] = [64, 10]
                elif kind == "contrast_type": contrast["subtype"] = "clothing"
                elif kind == "unknown_group": row["classification"] = "unresolved"
                elif kind == "accepted_label": reused["rows"][0]["accepted_classification_unchanged"] = "other_object"
                elif kind == "duplicate": contrast["duplicate_of_row_id"] = row["row_id"]
                else: documents[0]["rows"].pop()
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    labels.build(fixture["preparation"], fixture["proposal"], documents, reused)

    def test_unknown_contrast_is_not_promoted_and_seal_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); fixture = labeled_fixture(root)
            contrast = fixture["documents"][0]["rows"][-1]
            contrast.update({"classification": "unresolved", "subtype": None, "center_xy_px": None,
                "physical_object_instance_id": None, "episode_id": None, "duplicate_of_row_id": None, "object_extent_xyxy_px": None})
            write_json(root, "data/outputs/annotations.json", fixture["documents"][0])
            output = root / "data/outputs/merged"
            result = labels.merge(root, fixture["preparation_path"], [fixture["annotations_path"]], fixture["grouping_path"], output)
            self.assertEqual(result["provisional_adequacy"]["unknown_rows_unscored"], 2)
            self.assertEqual(result["provisional_adequacy"]["supplemental_duplicate_rows_excluded"], 0)
            self.assertEqual(result["rows"][-1]["classification"], "unresolved")
            result["human_review"] = "accepted"
            write_json(root, "data/outputs/merged/proposal.json", result)
            with self.assertRaisesRegex(ValueError, "changed or falsely accepted"):
                labels.load_proposal(root, output / "proposal.json")


if __name__ == "__main__":
    unittest.main()
