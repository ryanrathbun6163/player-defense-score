"""Focused native-timestamp, provenance and draft-save contract checks."""

import copy
import hashlib
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from src.ball_tracking import nba_annotations as nba


# Captured producer records from the approved SAC source-only frame_map.jsonl,
# October 18, 2026. These are metadata, not annotation truth or image fixtures.
# In particular, PTS steps are 1440 then 1530 ticks, not a constant nominal fps.
PRODUCER_ROWS = [
    {"clip_frame_index": 660, "source_frame_index": 660, "source_pts_ticks": 996362,
     "clip_pts_ticks": 993392, "time_base": "1/90000"},
    {"clip_frame_index": 661, "source_frame_index": 661, "source_pts_ticks": 997802,
     "clip_pts_ticks": 994832, "time_base": "1/90000"},
    {"clip_frame_index": 662, "source_frame_index": 662, "source_pts_ticks": 999332,
     "clip_pts_ticks": 996362, "time_base": "1/90000"},
]


def unlabeled(index):
    return {"frame_index": index, "annotation_status": "unlabeled", "visibility": None,
            "absence_reason": None, "game_ball_identity_certainty": None, "geometry": None,
            "localization_eligible": False, "difficulty_tags": [], "notes": None}


def observed(index):
    return {"frame_index": index, "annotation_status": "labeled", "visibility": "fully_visible",
            "absence_reason": None, "game_ball_identity_certainty": "certain",
            "geometry": {"center_xy_px": [3.0, 2.0], "source": "observed_complete_ball_center",
                         "uncertainty_radius_px": 1.0},
            "localization_eligible": True, "difficulty_tags": [], "notes": None}


class NBAAnnotationFixture:
    """Synthetic RGB/source bytes with captured native producer metadata."""

    def __init__(self, root):
        self.root = Path(root)
        self.path = self.root / "draft.json"
        self.source = self.root / "source.mp4"
        self.source.write_bytes(b"synthetic metadata-only source placeholder; never decoded")
        source_sha = hashlib.sha256(self.source.read_bytes()).hexdigest()
        source_stat = self.source.stat()
        stat = {"bytes": source_stat.st_size, "mtime_ns": source_stat.st_mtime_ns}
        self.audit = {"sha256": source_sha, "source_stat_after": stat}
        self.write_json("audit.json", self.audit)
        self.map_path = self.root / "frame_map.jsonl"
        self.map_path.write_text("".join(json.dumps(row) + "\n" for row in PRODUCER_ROWS), encoding="utf-8")
        frame_map = {**self.binding("frame_map.jsonl"), "bytes": self.map_path.stat().st_size}
        self.doc = {
            "schema_version": nba.SCHEMA_VERSION,
            "annotation_set_id": "sac_mem_native_contract_fixture",
            "candidate_id": "sac_mem_q1_c01", "game_id": "0022500829",
            "approved_role": "future_training_candidate_pool",
            "approval": {"path": "approval.json", "sha256": "0" * 64},
            "source_video": {"path": "source.mp4", "sha256": source_sha,
                             "width_px": 8, "height_px": 6, "frame_count": 357233},
            "time_base": "1/90000", "coordinate_system": dict(nba.COORDINATE_SYSTEM),
            "frames": [], "annotations": [unlabeled(row["source_frame_index"]) for row in PRODUCER_ROWS],
            "revision": 0, "created_at_utc": "2026-10-18T00:00:00+00:00",
            "updated_at_utc": "2026-10-18T00:00:00+00:00",
            "review": {"status": "draft", "annotator_id": None, "reviewer_id": None, "reviewed_at_utc": None},
        }
        for i, row in enumerate(PRODUCER_ROWS):
            image = Image.new("RGB", (8, 6), (i * 40, 30, 60))
            name = f"source_{row['source_frame_index']:06d}.png"
            image.save(self.root / name)
            self.doc["frames"].append({
                "source_frame_index": row["source_frame_index"], "source_pts_ticks": row["source_pts_ticks"],
                "png": {**self.binding(name), "rgb_sha256": hashlib.sha256(image.tobytes()).hexdigest()},
            })
        self.proposal = {
            "schema_version": "nba_development_selection_proposal/v0.1",
            "game_roles": [{"game_id": self.doc["game_id"], "proposed_role": self.doc["approved_role"]}],
            "candidates": [{"candidate_id": self.doc["candidate_id"], "game_id": self.doc["game_id"],
                            "parent_source_sha256": source_sha, "frame_map": frame_map}],
            "proposed_annotation_pilot": [{"candidate_id": self.doc["candidate_id"], "source_frame_range_inclusive": [660, 662],
                                           "source_pts_ticks_inclusive": [996362, 999332], "time_base": "1/90000", "frame_count": 3}],
        }
        self.write_json("proposal.json", self.proposal)
        self.approval = {
            "schema_version": "nba_development_selection_approval/v0.1", "status": "approved",
            "approved_by": "Fixture human", "approval_statement": "Fixture approval, not a real label or review.",
            "proposal": self.binding("proposal.json"),
            "game_roles": [{"game_id": self.doc["game_id"], "approved_role": self.doc["approved_role"]}],
            "annotation_pilots": [{
                **{field: copy.deepcopy(self.doc[field]) for field in ("annotation_set_id", "candidate_id", "game_id", "approved_role", "source_video", "time_base")},
                "source_frame_range_inclusive": [660, 662], "source_pts_ticks_inclusive": [996362, 999332],
                "frame_map": frame_map,
                "source_verification": {"audit": self.binding("audit.json"), "hash_field": "sha256",
                                        "stat_field": "source_stat_after", "source_stat": stat},
            }],
        }
        self.rebind_approval()

    def binding(self, name):
        return {"path": name, "sha256": hashlib.sha256((self.root / name).read_bytes()).hexdigest()}

    def write_json(self, name, value):
        (self.root / name).write_text(json.dumps(value), encoding="utf-8")

    def rebind_approval(self):
        self.write_json("approval.json", self.approval)
        self.doc["approval"] = self.binding("approval.json")


def build_fixture(root):
    """Create an actual initialized draft for editor producer/consumer tests."""
    fixture = NBAAnnotationFixture(root)
    nba.initialize_annotations(fixture.path, fixture.doc)
    return fixture.path, fixture.doc


class NBAAnnotationsTests(unittest.TestCase, NBAAnnotationFixture):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="nba_annotation_contract_")
        self.addCleanup(self.temporary.cleanup)
        NBAAnnotationFixture.__init__(self, Path(self.temporary.name))

    def initialized(self):
        nba.initialize_annotations(self.path, self.doc)
        return nba.load_annotation_snapshot(self.path)

    def test_captured_native_ticks_and_real_asset_transport(self):
        result = nba.verify_annotation_assets(self.doc, self.root)
        self.assertEqual(result["frames_verified"], 3)
        self.assertEqual(result["full_source_bytes_read"], 0)
        loaded, digest = self.initialized()
        self.assertEqual(loaded["frames"], self.doc["frames"])
        self.assertEqual(digest, nba.document_sha256(self.path))
        self.assertIsNone(loaded["review"]["annotator_id"])
        self.assertTrue(all(row == unlabeled(row["frame_index"]) for row in loaded["annotations"]))
        self.assertEqual(nba.read_verified_png(self.doc["frames"][0], self.doc["source_video"], self.root),
                         (self.root / self.doc["frames"][0]["png"]["path"]).read_bytes())

    def test_exact_frame_map_rejects_interior_tick_change(self):
        self.doc["frames"][1]["source_pts_ticks"] += 1
        nba.validate_annotations(self.doc)  # Still monotonic with unchanged approved endpoints.
        with self.assertRaisesRegex(nba.AnnotationValidationError, "approved producer frame map"):
            nba.verify_annotation_assets(self.doc, self.root)

    def test_producer_relative_pts_and_hash_binding_are_enforced(self):
        rows = copy.deepcopy(PRODUCER_ROWS)
        rows[1]["clip_pts_ticks"] += 1
        self.map_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        with self.assertRaisesRegex(nba.AnnotationValidationError, "Hash mismatch"):
            nba.verify_annotation_assets(self.doc, self.root)
        binding = {**self.binding("frame_map.jsonl"), "bytes": self.map_path.stat().st_size}
        self.proposal["candidates"][0]["frame_map"] = binding
        self.write_json("proposal.json", self.proposal)
        self.approval["proposal"] = self.binding("proposal.json")
        self.approval["annotation_pilots"][0]["frame_map"] = binding
        self.rebind_approval()
        with self.assertRaisesRegex(nba.AnnotationValidationError, "relative PTS"):
            nba.verify_annotation_assets(self.doc, self.root)

    def test_approval_cannot_silently_change_proposed_role_or_range(self):
        for field, value in (("approved_role", "target_case_development"), ("source_pts_ticks_inclusive", [996362, 999333])):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.doc)
                if field == "approved_role":
                    changed[field] = value
                else:
                    changed["frames"][-1]["source_pts_ticks"] += 1
                with self.assertRaises(nba.AnnotationValidationError):
                    nba.verify_annotation_assets(changed, self.root)
        self.proposal["proposed_annotation_pilot"][0]["source_pts_ticks_inclusive"][1] += 1
        self.write_json("proposal.json", self.proposal)
        self.approval["proposal"] = self.binding("proposal.json")
        self.rebind_approval()
        with self.assertRaisesRegex(nba.AnnotationValidationError, "differs from proposed pilot"):
            nba.verify_annotation_assets(self.doc, self.root)

    def test_source_audit_stat_and_producer_specific_keys(self):
        self.audit = {"full_file_sha256": self.audit["sha256"], "target_stat_after": self.audit["source_stat_after"]}
        self.write_json("audit.json", self.audit)
        verification = self.approval["annotation_pilots"][0]["source_verification"]
        verification.update(audit=self.binding("audit.json"), hash_field="full_file_sha256", stat_field="target_stat_after")
        self.rebind_approval()
        self.assertEqual(nba.verify_annotation_assets(self.doc, self.root, verify_images=False)["frames_verified"], 0)
        self.source.write_bytes(b"changed source")
        with self.assertRaisesRegex(nba.AnnotationValidationError, "source stat changed"):
            nba.verify_annotation_assets(self.doc, self.root, verify_images=False)

    def test_png_bytes_rgb_and_dimensions_fail_closed(self):
        frame = self.doc["frames"][0]
        frame["png"]["rgb_sha256"] = "0" * 64
        with self.assertRaisesRegex(nba.AnnotationValidationError, "RGB hash mismatch"):
            nba.read_verified_png(frame, self.doc["source_video"], self.root)
        frame["png"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(nba.AnnotationValidationError, "PNG hash mismatch"):
            nba.read_verified_png(frame, self.doc["source_video"], self.root)
        frame["png"]["sha256"] = self.binding(frame["png"]["path"])["sha256"]
        self.doc["source_video"]["width_px"] += 1
        with self.assertRaisesRegex(nba.AnnotationValidationError, "dimensions"):
            nba.read_verified_png(frame, self.doc["source_video"], self.root)

    def test_schema_rejects_review_fabrication_and_non_native_mapping(self):
        mutations = [
            lambda d: d.update(fps=25),
            lambda d: d.update(time_base="1/25"),
            lambda d: d["frames"][1].update(source_frame_index=663),
            lambda d: d["frames"][1].update(source_pts_ticks=d["frames"][0]["source_pts_ticks"]),
            lambda d: d["frames"][0]["png"].update(path="../outside.png"),
            lambda d: d["frames"][0]["png"].update(path="review.jpg"),
            lambda d: d["review"].update(status="reviewed", reviewer_id="Someone"),
            lambda d: d["annotations"].__setitem__(0, observed(660)),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                changed = copy.deepcopy(self.doc)
                mutate(changed)
                with self.assertRaises(nba.AnnotationValidationError):
                    nba.validate_annotations(changed)

    def test_existing_frame_semantics_preserve_hidden_and_indeterminate_rules(self):
        self.doc["review"]["annotator_id"] = "Fixture annotator"
        row = observed(660)
        row.update(visibility="not_visible", absence_reason="occluded")
        self.doc["annotations"][0] = row
        with self.assertRaisesRegex(nba.AnnotationValidationError, "forbids geometry"):
            nba.validate_annotations(self.doc)
        row.update(geometry=None, localization_eligible=False)
        nba.validate_annotations(self.doc)
        row.update(visibility="indeterminate", absence_reason=None, game_ball_identity_certainty="ambiguous")
        with self.assertRaisesRegex(nba.AnnotationValidationError, "requires notes"):
            nba.validate_annotations(self.doc)
        row["notes"] = "Cannot identify game ball in this synthetic example"
        nba.validate_annotations(self.doc)

    def test_atomic_save_preserves_snapshot_and_immutable_mapping(self):
        original, digest = self.initialized()
        original_bytes = self.path.read_bytes()
        labels = copy.deepcopy(original["annotations"])
        labels[0] = observed(660)
        saved = nba.save_annotations(self.path, labels, expected_revision=0, expected_sha256=digest, annotator_id="Actual UI name")
        self.assertEqual(saved["revision"], 1)
        self.assertEqual(saved["review"]["annotator_id"], "Actual UI name")
        self.assertEqual(saved["review"]["status"], "draft")
        for key in ("frames", "source_video", "approval", "game_id", "candidate_id", "approved_role"):
            self.assertEqual(saved[key], original[key])
        snapshots = list((self.root / "draft.history").glob("*.json"))
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].read_bytes(), original_bytes)
        with self.assertRaises(nba.AnnotationConflictError):
            nba.save_annotations(self.path, labels, expected_revision=0, expected_sha256=digest, annotator_id="Actual UI name")
        with self.assertRaises(nba.AnnotationConflictError):
            nba.save_annotations(self.path, labels, expected_revision=1, expected_sha256=nba.document_sha256(self.path), annotator_id="Different name")

    def test_concurrent_stale_writers_have_one_winner(self):
        doc, digest = self.initialized()
        def save():
            try:
                nba.save_annotations(self.path, doc["annotations"], expected_revision=0, expected_sha256=digest, annotator_id="Fixture annotator")
                return "saved"
            except nba.AnnotationConflictError:
                return "conflict"
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: save(), range(2)))
        self.assertEqual(sorted(outcomes), ["conflict", "saved"])
        self.assertEqual(nba.load_annotations(self.path)["revision"], 1)

    def test_failed_replace_keeps_original_and_prior_snapshot(self):
        doc, digest = self.initialized()
        original = self.path.read_bytes()
        with patch.object(nba.os, "replace", side_effect=OSError("simulated write failure")):
            with self.assertRaisesRegex(OSError, "simulated"):
                nba.save_annotations(self.path, doc["annotations"], expected_revision=0, expected_sha256=digest, annotator_id="Fixture annotator")
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(next((self.root / "draft.history").glob("*.json")).read_bytes(), original)
        self.assertFalse(self.path.with_name("draft.json.lock").exists())
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_initialization_and_json_parsing_do_not_fabricate_work(self):
        self.initialized()
        with self.assertRaises(nba.AnnotationConflictError):
            nba.initialize_annotations(self.path, self.doc)
        changed = copy.deepcopy(self.doc)
        changed["review"]["annotator_id"] = "Ryan"
        with self.assertRaisesRegex(nba.AnnotationValidationError, "null annotator"):
            nba.initialize_annotations(self.root / "second.json", changed)
        self.path.write_text('{"schema_version":"x","schema_version":"y"}', encoding="utf-8")
        with self.assertRaisesRegex(nba.AnnotationValidationError, "Duplicate"):
            nba.load_annotations(self.path)


if __name__ == "__main__":
    unittest.main()
