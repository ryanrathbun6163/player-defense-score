"""Accepted difficult-scene transport using the actual source/review producers.

Source identities and native PTS come from the captured authorized action-input
fixture. Preparation/package keys match the committed October 19 hard-example
record. Only encoding is stubbed; these tests make no MP4 playback claim.
"""
import copy
import json
import sys
import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.ball_tracking.nba_hard_example_reference import load_accepted_references, publish_reference
from src.ball_tracking.prepare_nba_assisted_review import binding, prepare_review
from tests import test_nba_hard_example_assets as assets
from tests.test_nba_annotations import observed


def build_fixture(test):
    fixture = assets.NBAHardExampleAssetTests()
    fixture.setUp()
    test.addCleanup(fixture.doCleanups)
    root = fixture.root
    windows = []
    for name, start, stop in (("first_window", 0, 2), ("second_window", 2, 4)):
        frames = fixture.manifest["frames"][start:stop]
        end = (fixture.manifest["frames"][stop]["source_pts_ticks"] if stop < 4
               else fixture.manifest["source_end_exclusive_pts_ticks"])
        window = copy.deepcopy(fixture.proposal["windows"][0])
        window.update(window_id=name, frames=len(frames),
                      source_frame_range_inclusive=[frames[0]["source_frame_index"], frames[-1]["source_frame_index"]],
                      source_pts_ticks_inclusive=[frames[0]["source_pts_ticks"], frames[-1]["source_pts_ticks"]],
                      source_end_exclusive_pts_ticks=end,
                      native_duration_seconds=(end - frames[0]["source_pts_ticks"]) / 90000)
        windows.append(window)
    fixture.proposal["windows"] = windows
    fixture.proposal["totals"]["new_proposed_label_frames"] = 4
    fixture.bind_proposal()
    packages, accepted_packages, originals, proposals = [], [], [], []
    for offset, window in enumerate(windows):
        original = copy.deepcopy(fixture.doc)
        original["annotation_set_id"] = window["window_id"] + "_hard_example_v0_1"
        original["frames"] = copy.deepcopy(fixture.manifest["frames"][offset * 2:offset * 2 + 2])
        original["annotations"] = [fixture.unlabeled(f["source_frame_index"]) for f in original["frames"]]
        original_path = root / (window["window_id"] + "_draft.json")
        original_path.write_text(json.dumps(original), encoding="utf-8")
        original_binding = binding(original_path, root)
        rows = [observed(f["source_frame_index"]) for f in original["frames"]]
        # Preserve a genuinely unscored row and uncertain point in accepted output.
        if offset == 1:
            rows[0].update(visibility="not_visible", absence_reason="occluded",
                           geometry=None, localization_eligible=False)
            rows[1]["geometry"]["uncertainty_radius_px"] = 2.0
        proposal = {
            "schema_version": "nba_assisted_annotation_proposal/v0.1",
            "candidate_id": original["candidate_id"],
            "source_annotation_binding": {k: original_binding[k] for k in ("path", "sha256")},
            "origin": {"kind": "assistant_visual_proposal", "actor_id": "codex_test",
                       "method": "direct_visual_inspection_of_native_rgb_pngs", "detector_predictions_used": False,
                       "interpolation_used": False, "created_at_utc": "2026-10-20T03:00:00+00:00"},
            "annotations": rows,
            "review_priority": [{"frame_index": rows[-1]["frame_index"], "reason": "Synthetic final-frame review"}],
            "frame_inspections": [{"frame_index": f["source_frame_index"], "source_png_sha256": f["png"]["sha256"],
                                   "evidence_paths": [f["png"]["path"]], "notes": "Synthetic source image"}
                                  for f in original["frames"]],
            "human_review": {"status": "pending", "reviewer_id": None, "reviewed_at_utc": None},
        }
        proposed_path = root / (window["window_id"] + "_proposal.json")
        proposed_path.write_text(json.dumps(proposal), encoding="utf-8")
        def synthetic_encoder(command, **kwargs):
            Path(command[-1]).write_bytes(b"synthetic review bytes; not encoded media")
            return SimpleNamespace(returncode=0)
        output = root / "data/outputs/reviews" / window["window_id"]
        with patch("src.ball_tracking.prepare_nba_assisted_review.subprocess.run", side_effect=synthetic_encoder):
            receipt = prepare_review(root, original_path, proposed_path, output, sys.executable)
        directory = output / original["candidate_id"]
        bound = lambda name: binding(directory / name, root)
        package = {k: original[k] for k in ("candidate_id", "game_id", "approved_role")}
        package.update(window_id=window["window_id"], source_frame_range_inclusive=window["source_frame_range_inclusive"],
                       counts=receipt["counts"], source_draft=original_binding, proposal=bound("proposal.json"),
                       review_manifest=bound("review_manifest.json"), review_video=bound("review.mp4"),
                       preparation_receipt=bound("preparation_receipt.json"),
                       actual_final_frame_inspected=rows[-1]["frame_index"],
                       review_priority_frames=[rows[-1]["frame_index"]], human_label_acceptance="pending")
        accepted_package = {key: copy.deepcopy(package[key]) for key in
                            ("window_id", "candidate_id", "game_id", "approved_role", "source_frame_range_inclusive",
                             "proposal", "review_manifest", "review_video")}
        accepted_package.update(original_annotations=original_binding, review_receipt=package["preparation_receipt"],
                                frame_count=len(rows), actual_final_frame_in_presented_review=rows[-1]["frame_index"],
                                priority_frame_indices=package["review_priority_frames"])
        packages.append(package)
        accepted_packages.append(accepted_package)
        originals.append(original)
        proposals.append(proposal)
    all_rows = [row for p in proposals for row in p["annotations"]]
    prepared = {"schema_version": "nba_hard_example_reference_preparation/v0.1",
                "status": "prepared_pending_human_label_acceptance", "packages": packages,
                "scope_approval": fixture.bind("approval.json"), "scope_proposal": fixture.bind("proposal.json"),
                "totals": {"frames": 4, "eligible_proposed_centers": 3, "null_geometry": 1,
                           "visibility": dict(Counter(row["visibility"] for row in all_rows))}}
    fixture.write("preparation.json", prepared)
    acceptance = {
        "schema_version": "nba_hard_example_label_acceptance/v0.1", "status": "accepted", "reviewer_id": "Ryan",
        "reviewed_at_utc": "2026-10-20T04:00:00+00:00", "user_statement": "Synthetic human acceptance fixture only.",
        "review_method": "human_visual_acceptance_of_assisted_proposals", "annotation_origin": "assistant_visual_proposal",
        "scope": "Synthetic saved-output diagnostic only", "preparation_record": fixture.bind("preparation.json"),
        "scope_approval": fixture.bind("approval.json"), "packages": accepted_packages,
        "limits": {"independent_human_annotation": False, "training_authorized": False,
                   "new_inference_authorized": False, "independent_test_set": False,
                   "full_possession_or_phase_acceptance": False, "saved_output_scoring_authorized": True}}
    fixture.write("acceptance.json", acceptance)
    return fixture, acceptance, originals, proposals


class HardExampleReferenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture, self.acceptance, self.originals, self.proposals = build_fixture(self)
        self.root = self.fixture.root
        self.path = self.root / "acceptance.json"

    def save(self):
        self.fixture.write("acceptance.json", self.acceptance)

    def test_same_candidate_windows_preserve_native_rows_unknowns_and_ai_origin(self):
        original_read = Path.read_bytes
        before = [(self.root / p["original_annotations"]["path"]).read_bytes() for p in self.acceptance["packages"]]
        def guarded_read(path):
            self.assertNotEqual(path.resolve(), self.fixture.source_path.resolve())
            return original_read(path)
        with patch.object(Path, "read_bytes", guarded_read):
            references = load_accepted_references(self.path, self.root, verify_images=True)
        self.assertEqual([r["window_id"] for r in references], ["first_window", "second_window"])
        self.assertEqual(len({r["candidate_id"] for r in references}), 1)
        for record, original, proposal in zip(references, self.originals, self.proposals):
            self.assertEqual(record["frames"], original["frames"])
            self.assertEqual(record["annotations"], proposal["annotations"])
            self.assertEqual(record["origin"], proposal["origin"])
            self.assertEqual(record["human_review"]["status"], "accepted")
            self.assertFalse(record["human_review"]["independent_human_annotation"])
            self.assertEqual(record["bindings"]["source_verification"],
                             self.fixture.manifest["preparation"]["identity"]["window"]["source_verification"])
        self.assertIsNone(references[1]["annotations"][0]["geometry"])
        self.assertEqual(references[1]["annotations"][1]["geometry"]["uncertainty_radius_px"], 2.0)
        self.assertEqual(before, [(self.root / p["original_annotations"]["path"]).read_bytes()
                                  for p in self.acceptance["packages"]])
        for package in self.acceptance["packages"]:
            self.assertEqual(json.loads((self.root / package["proposal"]["path"]).read_bytes())["human_review"]["status"], "pending")

    def test_bound_preparation_scope_and_presented_artifacts_cannot_change(self):
        refs = [self.acceptance[key] for key in ("preparation_record", "scope_approval")]
        refs += [self.acceptance["packages"][0][key] for key in
                 ("proposal", "original_annotations", "review_manifest", "review_video", "review_receipt")]
        for ref in refs:
            path = self.root / ref["path"]
            raw = path.read_bytes()
            path.write_bytes(raw + b" ")
            try:
                with self.subTest(path=ref["path"]), self.assertRaisesRegex(ValueError, "Hash mismatch"):
                    load_accepted_references(self.path, self.root)
            finally:
                path.write_bytes(raw)

    def test_window_inventory_final_priority_role_and_limits_fail_closed(self):
        initial = copy.deepcopy(self.acceptance)
        changes = [lambda a: a["packages"].append(copy.deepcopy(a["packages"][0])),
                   lambda a: a["packages"].pop(),
                   lambda a: a["packages"][0].update(window_id="another_window"),
                   lambda a: a["packages"][0].update(frame_count=1),
                   lambda a: a["packages"][0].update(actual_final_frame_in_presented_review=11000),
                   lambda a: a["packages"][0].update(priority_frame_indices=[]),
                   lambda a: a["packages"][0].update(approved_role="training"),
                   lambda a: a["limits"].update(independent_human_annotation=True),
                   lambda a: a["limits"].update(training_authorized=True),
                   lambda a: a["limits"].update(saved_output_scoring_authorized=False),
                   lambda a: a.update(status="pending")]
        for mutate in changes:
            self.acceptance = copy.deepcopy(initial)
            mutate(self.acceptance)
            self.save()
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                load_accepted_references(self.path, self.root)

    def test_rebound_manifest_checks_native_pts_geometry_exceptions_and_counts(self):
        package = self.acceptance["packages"][0]
        manifest_path = self.root / package["review_manifest"]["path"]
        manifest = json.loads(manifest_path.read_bytes())
        prep_path = self.root / self.acceptance["preparation_record"]["path"]
        prep = json.loads(prep_path.read_bytes())
        changes = [(lambda m: m["frames"][0].update(source_pts_ticks=1), "mapping differs"),
                   (lambda m: m["frames"][0]["render_geometry"].update(point_source_pixels=[1, 1]), "geometry differs"),
                   (lambda m: m["frames"][0].update(exceptions=["incorrect"]), "exception flags differ"),
                   (lambda m: m["counts"].update(with_point=0), "counts differ"),
                   (lambda m: m["video"].update(final_frame_hold_seconds=0), "final-frame convention differs")]
        for mutate, message in changes:
            changed = copy.deepcopy(manifest)
            mutate(changed)
            manifest_path.write_text(json.dumps(changed), encoding="utf-8")
            package["review_manifest"] = binding(manifest_path, self.root)
            prep["packages"][0]["review_manifest"] = package["review_manifest"]
            prep_path.write_text(json.dumps(prep), encoding="utf-8")
            self.acceptance["preparation_record"] = binding(prep_path, self.root)
            self.save()
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                load_accepted_references(self.path, self.root)

    def test_receipt_counts_and_source_stat_still_authoritative(self):
        prep_path = self.root / self.acceptance["preparation_record"]["path"]
        original = prep_path.read_bytes()
        prep = json.loads(original)
        prep["totals"]["null_geometry"] = 0
        prep_path.write_text(json.dumps(prep), encoding="utf-8")
        self.acceptance["preparation_record"] = binding(prep_path, self.root)
        self.save()
        with self.assertRaisesRegex(ValueError, "Preparation totals differ"):
            load_accepted_references(self.path, self.root)
        prep_path.write_bytes(original)
        self.acceptance["preparation_record"] = binding(prep_path, self.root)
        self.save()
        self.fixture.source_path.write_bytes(b"changed source")
        with self.assertRaisesRegex(ValueError, "Parent source stat changed"):
            load_accepted_references(self.path, self.root)

    def test_publication_separate_and_refuses_overwrite_and_escape(self):
        output = self.root / "data/outputs/accepted/reference.json"
        result = publish_reference(self.path, output, self.root)
        self.assertEqual(result["verification"]["native_pngs_verified"], 4)
        self.assertEqual(result["verification"]["original_video_bytes_read"], 0)
        self.assertEqual(json.loads(output.read_bytes()), result)
        original = output.read_bytes()
        with self.assertRaisesRegex(ValueError, "Existing reference preserved"):
            publish_reference(self.path, output, self.root)
        self.assertEqual(output.read_bytes(), original)
        with self.assertRaisesRegex(ValueError, "under data/outputs"):
            publish_reference(self.path, self.root / "bad.json", self.root)
        self.acceptance["packages"][0]["review_video"]["path"] = "../outside.mp4"
        self.save()
        with self.assertRaisesRegex(ValueError, "relative path"):
            load_accepted_references(self.path, self.root)


if __name__ == "__main__":
    unittest.main()
