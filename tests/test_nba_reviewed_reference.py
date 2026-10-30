"""Acceptance transport uses the actual draft and assisted-review producers."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.ball_tracking.nba_reviewed_reference import load_accepted_references, publish_reference
from src.ball_tracking.prepare_nba_assisted_review import binding, prepare_review
from tests.test_nba_annotations import build_fixture, observed


def build_accepted_fixture(root):
    """Return acceptance path/data, original and proposal; synthetic review bytes only.

    Record shapes follow the captured October 18 preparation/acceptance records.
    The real review producer emits manifests/receipts/images. Only its encoder is
    replaced: this fixture tests transport and makes no encoded-media claim.
    """
    root = Path(root)
    draft_path, original = build_fixture(root)
    original_binding = {key: value for key, value in binding(draft_path, root).items() if key != "bytes"}
    frames = original["frames"]
    proposal = {
        "schema_version": "nba_assisted_annotation_proposal/v0.1", "candidate_id": original["candidate_id"],
        "source_annotation_binding": original_binding,
        "origin": {"kind": "assistant_visual_proposal", "actor_id": "codex_test",
                   "method": "direct_visual_inspection_of_native_rgb_pngs", "detector_predictions_used": False,
                   "interpolation_used": False, "created_at_utc": "2026-10-18T00:00:00+00:00"},
        "annotations": [observed(f["source_frame_index"]) for f in frames],
        "review_priority": [{"frame_index": frames[-1]["source_frame_index"], "reason": "Synthetic final-frame review"}],
        "frame_inspections": [{"frame_index": f["source_frame_index"], "source_png_sha256": f["png"]["sha256"],
                               "evidence_paths": [f["png"]["path"]], "notes": "Synthetic fixture image"} for f in frames],
        "human_review": {"status": "pending", "reviewer_id": None, "reviewed_at_utc": None},
    }
    proposed_path = root / "assisted.json"
    proposed_path.write_text(json.dumps(proposal), encoding="utf-8")
    def synthetic_encoder(command, **kwargs):
        Path(command[-1]).write_bytes(b"synthetic review bytes; not an encoded-media test")
        return SimpleNamespace(returncode=0)
    out = root / "data/outputs/reviews"
    with patch("src.ball_tracking.prepare_nba_assisted_review.subprocess.run", side_effect=synthetic_encoder):
        receipt = prepare_review(root, draft_path, proposed_path, out, sys.executable)
    directory = out / original["candidate_id"]
    bound = lambda name: binding(directory / name, root)
    package = {
        "candidate_id": original["candidate_id"], "counts": receipt["counts"], "origin": proposal["origin"],
        "proposal": bound("proposal.json"), "original_draft": original_binding,
        "review_receipt": bound("preparation_receipt.json"), "review_video": bound("review.mp4"),
        "priority_frame_indices": [662], "original_draft_revision": 0, "original_draft_all_rows_unlabeled": True,
    }
    prepared = {"schema_version": "nba_assisted_annotation_pilot_preparation/v0.1",
                "status": "prepared_pending_human_review", "totals": {"source_frames": 3}, "packages": [package]}
    prepared_path = root / "preparation.json"
    prepared_path.write_text(json.dumps(prepared), encoding="utf-8")
    accepted = {
        "schema_version": "nba_assisted_label_acceptance/v0.1", "status": "accepted", "reviewer_id": "Fixture human",
        "reviewed_at_utc": "2026-10-18T01:00:00+00:00", "review_date_local": "2026-10-18", "timezone": "UTC",
        "user_statement": "Synthetic acceptance fixture; no real human annotation.",
        "review_method": "human_visual_acceptance_of_assisted_proposals", "annotation_origin": "assistant_visual_proposal",
        "scope": "Synthetic transport test only", "preparation_record": binding(prepared_path, root),
        "packages": [{**{key: original[key] for key in ("candidate_id", "game_id", "approved_role")},
                      "proposal": bound("proposal.json"), "original_annotations": original_binding,
                      "review_manifest": bound("review_manifest.json"), "review_video": bound("review.mp4"),
                      "frame_count": 3, "source_frame_range_inclusive": [660, 662],
                      "actual_final_frame_in_presented_review": 662, "priority_frame_indices": [662]}],
        "limits": {"independent_human_annotation": False, "training_authorized": False,
                   "new_diagnostic_recipe_approved": False, "independent_test_set": False,
                   "full_possession_or_phase_acceptance": False, "motion_human_reviews_still_pending": 3},
    }
    acceptance_path = root / "acceptance.json"
    acceptance_path.write_text(json.dumps(accepted), encoding="utf-8")
    return acceptance_path, accepted, original, proposal


class ReviewedReferenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="nba_reviewed_reference_")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path, self.acceptance, self.original, self.proposal = build_accepted_fixture(self.root)

    def save_acceptance(self):
        self.path.write_text(json.dumps(self.acceptance), encoding="utf-8")

    def test_actual_producers_preserve_rows_native_ticks_origin_and_inputs(self):
        draft = self.root / "draft.json"
        proposal = self.root / self.acceptance["packages"][0]["proposal"]["path"]
        before = [draft.read_bytes(), proposal.read_bytes()]
        original_read = Path.read_bytes
        def no_original_video_read(path):
            self.assertNotEqual(path.resolve(), (self.root / "source.mp4").resolve())
            return original_read(path)
        with patch.object(Path, "read_bytes", no_original_video_read):
            rows = load_accepted_references(self.path, self.root, verify_images=True)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["frames"], self.original["frames"])
        self.assertEqual(row["annotations"], self.proposal["annotations"])
        self.assertEqual(row["origin"], self.proposal["origin"])
        self.assertEqual(row["human_review"]["status"], "accepted")
        self.assertFalse(row["human_review"]["independent_human_annotation"])
        self.assertEqual([f["source_pts_ticks"] for f in row["frames"]], [996362, 997802, 999332])
        self.assertEqual([draft.read_bytes(), proposal.read_bytes()], before)
        self.assertEqual(json.loads(proposal.read_bytes())["human_review"]["status"], "pending")

    def test_changed_bound_files_fail_before_reference_publication(self):
        refs = list(self.acceptance["packages"][0][key] for key in
                    ("proposal", "original_annotations", "review_manifest", "review_video"))
        refs.append(self.acceptance["preparation_record"])
        for ref in refs:
            path = self.root / ref["path"]
            raw = path.read_bytes()
            path.write_bytes(raw + b" ")
            try:
                with self.subTest(path=ref["path"]), self.assertRaisesRegex(ValueError, "Hash mismatch"):
                    load_accepted_references(self.path, self.root)
            finally:
                path.write_bytes(raw)

    def test_acceptance_cannot_change_role_inventory_final_frame_or_review_scope(self):
        for field, value in (("approved_role", "independent_test"), ("game_id", "wrong_game"),
                             ("frame_count", 2), ("actual_final_frame_in_presented_review", 661),
                             ("priority_frame_indices", [660])):
            original = copy.deepcopy(self.acceptance)
            self.acceptance["packages"][0][field] = value
            self.save_acceptance()
            with self.subTest(field=field), self.assertRaises(ValueError):
                load_accepted_references(self.path, self.root)
            self.acceptance = original
        self.acceptance["limits"]["independent_human_annotation"] = True
        self.save_acceptance()
        with self.assertRaisesRegex(ValueError, "Unsupported acceptance scope"):
            load_accepted_references(self.path, self.root)

    def test_hash_rebound_manifest_cannot_change_native_ticks_or_geometry(self):
        ref = self.acceptance["packages"][0]["review_manifest"]
        path = self.root / ref["path"]
        manifest = json.loads(path.read_bytes())
        for mutation in ("ticks", "geometry"):
            changed = copy.deepcopy(manifest)
            if mutation == "ticks":
                changed["frames"][1]["source_pts_ticks"] += 1
            else:
                changed["frames"][1]["render_geometry"]["point_source_pixels"][0] += 1
            path.write_text(json.dumps(changed), encoding="utf-8")
            self.acceptance["packages"][0]["review_manifest"] = binding(path, self.root)
            self.save_acceptance()
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, "mapping differs|geometry differs"):
                load_accepted_references(self.path, self.root)

    def test_preparation_binding_duplicates_and_original_stat_remain_authoritative(self):
        prep_path = self.root / self.acceptance["preparation_record"]["path"]
        original = prep_path.read_bytes()
        prep = json.loads(original)
        prep["packages"][0]["proposal"]["sha256"] = "0" * 64
        prep_path.write_text(json.dumps(prep), encoding="utf-8")
        self.acceptance["preparation_record"] = binding(prep_path, self.root)
        self.save_acceptance()
        with self.assertRaisesRegex(ValueError, "Preparation/acceptance binding differs"):
            load_accepted_references(self.path, self.root)
        prep_path.write_bytes(original)
        self.acceptance["preparation_record"] = binding(prep_path, self.root)
        self.acceptance["packages"].append(copy.deepcopy(self.acceptance["packages"][0]))
        self.save_acceptance()
        with self.assertRaisesRegex(ValueError, "package inventory differs"):
            load_accepted_references(self.path, self.root)
        self.acceptance["packages"].pop()
        self.save_acceptance()
        (self.root / "source.mp4").write_bytes(b"changed source; never decoded")
        with self.assertRaisesRegex(ValueError, "source stat changed"):
            load_accepted_references(self.path, self.root, verify_images=False)

    def test_publication_is_separate_refuses_overwrite_and_rejects_path_escape(self):
        output = self.root / "data/outputs/reviewed/reference.json"
        result = publish_reference(self.path, output, self.root)
        self.assertEqual(result["verification"]["native_pngs_verified"], 3)
        self.assertEqual(json.loads(output.read_bytes()), result)
        prior = output.read_bytes()
        with self.assertRaisesRegex(ValueError, "Existing reference preserved"):
            publish_reference(self.path, output, self.root)
        self.assertEqual(output.read_bytes(), prior)
        self.acceptance["packages"][0]["review_video"]["path"] = "../outside.mp4"
        self.save_acceptance()
        with self.assertRaisesRegex(ValueError, "relative path"):
            load_accepted_references(self.path, self.root)


if __name__ == "__main__":
    unittest.main()
