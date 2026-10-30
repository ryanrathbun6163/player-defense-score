"""Accepted-reference transport and unchanged saved-coordinate metric checks."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from src.ball_tracking import nba_gap_anchor_reference_evaluation as evaluation
from src.ball_tracking import nba_gap_anchor_reference as preparation
from src.ball_tracking import nba_temporal_gap_continuous as continuous
from src.ball_tracking import nba_temporal_gap_selection as selector
from src.ball_tracking import nba_wasb_diagnostic as d
from tests.test_nba_gap_anchor_reference import source_fixture, write_json, unknown_annotation
from tests.test_nba_hard_example_diagnostic import label


def accepted_fixture(root):
    """Prepare real emitted records; derive seven scores with continuous producer."""
    scope = source_fixture(root); repository = Path(__file__).resolve().parents[1]
    for name in ("nba_gap_anchor_reference_evaluation.py", "nba_temporal_gap_selection.py", "nba_candidate_preservation.py"):
        (root / "src/ball_tracking" / name).write_bytes((repository / "src/ball_tracking" / name).read_bytes())
    selection = preparation.read_bound(root, scope["selection"])
    previous = preparation.read_bound(root, scope["report"])
    decisions = {}
    for source in selection["sources"]:
        for row in source["frames"]:
            if row["decision"] == "withheld":
                continue
            component = {"center_x": 20, "center_y": 20}
            row.update(source_video=source["source_video"], selected_center_xy_px=[20, 20],
                original_observation={"temporal_contributions": 3,
                                      "candidates": [component] if row["baseline_center_xy_px"] is not None else []},
                candidate_pool={"records": [{"component": component}]}, candidate_pool_scope="synthetic_saved_pool", segment_id="synthetic_segment")
            decisions[source["candidate_id"], row["source_frame_index"]] = row
    selection["frames"] = list(decisions.values())
    selection_binding = write_json(root, "data/outputs/selection.json", selection)
    prior_rows = []
    for old in previous["frames"]:
        decision = decisions[old["continuous_source_id"], old["source_frame_index"]]
        row = {**old, "window_id": "historical_window", "analysis_group": "synthetic_development", "cohort": "test",
               "is_control": True, "eligibility": "eligible", "decision": decision,
               "old": {"pool": {"contributor_planes": [None]*3}}}
        row["baseline"] = selector.score_point(row, decision["baseline_center_xy_px"], decision["original_observation"]["candidates"])
        row["selected"] = selector.score_point(row, decision["selected_center_xy_px"], [r["component"] for r in decision["candidate_pool"]["records"]])
        row["changed"] = decision["baseline_center_xy_px"] != decision["selected_center_xy_px"]
        prior_rows.append(row)
    prior_binding = write_json(root, "data/outputs/prior.json", {"status": "completed", "frames": prior_rows})
    actual_rows, _, _ = continuous.score_saved_selection(root,
        {"accepted_gap_report": prior_binding, "totals": {"scored_frames": 7}}, selection, selection_binding)
    report_binding = write_json(root, "data/outputs/report.json", {"status": "completed", "selection": selection_binding, "frames": actual_rows})
    scope["selection"] = selection_binding; scope["report"] = report_binding
    write_json(root, "configs/scope.json", scope)
    def decoder(_root, possession, segment):
        preparation.nfhs.guard_segment(possession, segment)
        for index in range(segment[0], segment[1]+1):
            yield index, np.full((40, 64, 3), index, dtype=np.uint8)
    with patch.object(preparation.nfhs, "decode_segment", decoder):
        ready = preparation.prepare(root, "configs/scope.json")
    prepared = d.read_json(root / ready["preparation"]["path"])
    new = []
    for frame in prepared["frames"]:
        if frame["reference_origin"] != "new":
            continue
        cid, index = preparation.key(frame)
        unknown = (cid == "nba_source" and index in (9, 10, 11)) or (cid == "possession_fixture" and index in (55, 56))
        annotation = unknown_annotation(index) if unknown else label(index, (20, 20))
        # Independent exact radius and just-outside cases, both real source rows.
        if cid == "nba_source" and index in (24, 25):
            annotation = label(index, (30 if index == 24 else 30.000001, 20))
            annotation["geometry"]["uncertainty_radius_px"] = 20
        new.append({"continuous_source_id": cid, "source_frame_index": index, "annotation": annotation})
    proposal = {"schema_version": preparation.PROPOSAL_SCHEMA, "preparation": ready["preparation"], "status": "draft",
        "authorship": {"annotator_id": "AI test fixture", "method": "source_first_ai", "not_blind": True}, "human_review": "pending",
        "new_annotations": new, "existing_controls": [{"continuous_source_id": r["continuous_source_id"],
            "source_frame_index": r["source_frame_index"], "existing_reference": r["existing_reference"]}
            for r in prepared["frames"] if r["reference_origin"] == "existing"]}
    proposal_binding = write_json(root, "data/outputs/proposal.json", proposal)
    seal = write_json(root, "data/outputs/seal.json", {"schema_version": "nba_gap_anchor_reference_proposal_seal/v0.1",
        "proposal": proposal_binding, "preparation": ready["preparation"], "new_targets": 27, "reused_controls": 7,
        "created_at_utc": "2026-10-21T09:00:00+00:00"})
    video = root / "data/outputs/review.mp4"; video.write_bytes(b"Already verified synthetic media")
    guide = root / "data/outputs/review.html"; guide.write_text("Already delivered synthetic guide", encoding="utf-8")
    media = write_json(root, "data/outputs/media_completion.json", {"status": "completed",
        "identity": {"proposal": proposal_binding, "preparation": ready["preparation"]},
        "artifacts": {"video": d.binding(root, video), "guide": d.binding(root, guide)}})
    result = write_json(root, "configs/preparation_result.json", {"status": "references_prepared_pending_human_acceptance",
        "preparation": ready["preparation"], "proposal": proposal_binding, "proposal_seal": seal, "media": {"completion": media}})
    acceptance = {"schema_version": evaluation.ACCEPTANCE_SCHEMA, "status": "accepted", "annotation_origin": "assistant_visual_proposal",
        "review_method": "human_visual_acceptance_of_assisted_proposals", "reviewer_id": "Ryan",
        "reviewed_at_utc": "2026-10-21T10:00:00+00:00", "user_statement": "ok great chat they have been reviewed. move forward",
        "preparation_result": result, "preparation": ready["preparation"], "proposal": proposal_binding, "proposal_seal": seal,
        "review_completion": media, "review_video": d.binding(root, video), "review_guide": d.binding(root, guide),
        "accepted_new_references": 27, "reused_controls_unchanged": 7, "evaluation_authorized": True, "evaluation_radius_px": 10,
        "semantic_object_adjudication": "not_separately_reported"}
    write_json(root, "configs/acceptance.json", acceptance)
    return {"acceptance_path": root / "configs/acceptance.json", "proposal": proposal, "prepared": prepared,
            "selection": selection, "original_rows": actual_rows, "reference_path": root / "data/outputs/accepted.json",
            "report_path": root / "data/outputs/evaluation.json"}


class GapAnchorEvaluationTests(unittest.TestCase):
    def test_publish_then_score_metadata_only_keeps_new_and_controls_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); fixture = accepted_fixture(root)
            original_digest = d.digest
            def metadata_only_digest(path):
                self.assertNotIn(Path(path).suffix.lower(), (".png", ".mp4"))
                return original_digest(path)
            with patch.object(d, "digest", metadata_only_digest), patch.object(preparation.nba, "read_verified_png", side_effect=AssertionError("pixels prohibited")), patch.object(preparation.nfhs, "decode_segment", side_effect=AssertionError("decoding prohibited")):
                accepted = evaluation.publish_reference(root, fixture["acceptance_path"], fixture["reference_path"])
                report = evaluation.evaluate(root, fixture["reference_path"], fixture["report_path"])
            self.assertEqual(accepted["new_annotations"], fixture["proposal"]["new_annotations"])
            self.assertEqual(accepted["existing_controls"], fixture["proposal"]["existing_controls"])
            self.assertEqual(accepted["authorship"], fixture["proposal"]["authorship"])
            self.assertEqual(accepted["totals"], {"new_references": 27, "reused_controls": 7, "new_geometry": 22, "new_unknown": 5})
            self.assertEqual(report["summary"]["new_references_only"]["frames"], 27)
            self.assertEqual(len(report["reused_controls"]), 7)
            self.assertTrue(all(r["original_scores_reproduced_exactly"] for r in report["reused_controls"]))
            self.assertEqual([r["existing_reference"]["row"] for r in report["reused_controls"]], fixture["original_rows"])
            self.assertEqual(report["summary"]["new_references_only"]["selected"]["unscored"], 5)
            self.assertTrue(all(r["emitted_point_present"] for r in report["summary"]["unscored_new_frames"]))
            self.assertEqual(d.read_json(root / "data/outputs/proposal.json")["human_review"], "pending")
            by_key = {preparation.key(r): r for r in report["new_frames"]}
            self.assertEqual(by_key["nba_source", 24]["selected"]["outcome"], "matched")
            self.assertEqual(by_key["nba_source", 24]["selected"]["raw_center_error_px"], 10)
            self.assertEqual(by_key["nba_source", 25]["selected"]["outcome"], "wrong")
            self.assertEqual(by_key["nba_source", 25]["selected"]["uncertainty_adjusted_error_px"], 0)

    def test_publication_and_scoring_are_write_once_and_tampering_is_not_rebound(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); f = accepted_fixture(root)
            accepted = evaluation.publish_reference(root, f["acceptance_path"], f["reference_path"])
            before = f["reference_path"].read_bytes()
            evaluation.publish_reference(root, f["acceptance_path"], f["reference_path"])
            self.assertEqual(f["reference_path"].read_bytes(), before)
            accepted["new_annotations"][0]["annotation"]["notes"] = "silently edited after acceptance"
            f["reference_path"].write_text(json.dumps(accepted), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Published accepted reference differs"):
                evaluation.evaluate(root, f["reference_path"], f["report_path"])
            self.assertFalse(f["report_path"].exists())

    def test_control_source_and_original_outcome_corruption_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); f = accepted_fixture(root)
            accepted = evaluation.publish_reference(root, f["acceptance_path"], f["reference_path"])
            changed = copy.deepcopy(f["selection"])
            chosen = next(r for r in changed["frames"] if r["candidate_id"] == "possession_fixture" and r["source_frame_index"] == 10)
            chosen["source_video"] = {**chosen["source_video"], "sha256": "0"*64}
            with self.assertRaisesRegex(ValueError, "source or native PTS"):
                evaluation.score_reference_rows(accepted, f["prepared"], changed)
            changed = copy.deepcopy(accepted)
            changed["existing_controls"][0]["existing_reference"]["row"]["selected"]["outcome"] = "wrong"
            with self.assertRaisesRegex(ValueError, "control outcomes/errors"):
                evaluation.score_reference_rows(changed, f["prepared"], f["selection"])

    def test_unresolved_object_identity_does_not_change_existing_geometric_metric(self):
        row = {"source_frame_index": 1, "source_frame": {"source_pts_ticks": 3600},
               "source_video": {"width_px": 64, "height_px": 40}, "annotation": label(1, (63, 20)),
               "old": {"pool": {"contributor_planes": [None]*3}}, "object_assessment": "unresolved"}
        self.assertEqual(selector.score_point(row, [63, 20], [{"center_x": 63, "center_y": 20}])["outcome"], "matched")
        self.assertEqual(selector.score_point(row, [64, 20], [{"center_x": 64, "center_y": 20}])["outcome"], "wrong")
        row["annotation"] = unknown_annotation(1)
        score = selector.score_point(row, [63, 20], [{"center_x": 63, "center_y": 20}])
        self.assertEqual(score["outcome"], "unscored")
        self.assertIsNone(score["raw_center_error_px"])
        self.assertFalse(score["raw_candidate_available"])


if __name__ == "__main__":
    unittest.main()
