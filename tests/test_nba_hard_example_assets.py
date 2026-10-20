"""Hard-example draft transport against captured action-input producer metadata.

The frame indices/native PTS below were captured from the authorized DET
nba_action_inputs/v0.1 manifest on October 19, 2026 (manifest SHA-256
f40c5217cbcaa6f74b1b825b303a1b13572d84c735fc0083ca980dc9768d7b6e).
PNG bytes are synthetic; tests never depend on ignored NBA media. Producer
frame keys, preparation identity, and source-verification fields follow the
actual prepare_inputs output independently of this consumer's validation.
"""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from src.ball_tracking import nba_annotations as nba


CAPTURED_NATIVE_ROWS = [
    (11000, 16520372), (11001, 16521812),
    (11002, 16523342), (11003, 16524872),
]


class NBAHardExampleAssetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="nba_hard_example_assets_")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source_path = self.root / "source.mp4"
        self.source_path.write_bytes(b"synthetic source placeholder: never decoded or reread")
        source = {"path": "source.mp4", "sha256": hashlib.sha256(self.source_path.read_bytes()).hexdigest(),
                  "width_px": 8, "height_px": 6, "frame_count": 12000}
        stat = self.source_path.stat()
        source_stat = {"bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}
        self.write("audit.json", {"full_file_sha256": source["sha256"], "target_stat_after": source_stat})
        frames = []
        for index, pts in CAPTURED_NATIVE_ROWS:
            image = Image.new("RGB", (8, 6), (index % 255, 25, 80))
            name = f"source_{index:06d}.png"
            image.save(self.root / name)
            frames.append({"source_frame_index": index, "source_pts_ticks": pts,
                           "png": {"path": name, "sha256": self.bind(name)["sha256"],
                                   "rgb_sha256": hashlib.sha256(image.tobytes()).hexdigest()}})
        self.manifest = {
            "schema_version": "nba_action_inputs/v0.1", "candidate_id": "sas_det_q1_c02",
            "game_id": "0022500828", "approved_role": "target_case_development",
            "source_video": source, "time_base": "1/90000",
            "source_frame_range_inclusive": [11000, 11003],
            "source_pts_ticks_inclusive": [16520372, 16524872],
            "source_end_exclusive_pts_ticks": 16526312, "frames": frames,
        }
        original = {k: copy.deepcopy(v) for k, v in self.manifest.items()
                    if k not in {"schema_version", "frames"}}
        original["source_verification"] = {
            "audit": self.bind("audit.json", size=False), "hash_field": "full_file_sha256",
            "stat_field": "target_stat_after", "source_stat": source_stat,
        }
        self.manifest["preparation"] = {"identity": {"window": original}, "source_hash_recomputed": False,
                                        "annotations_created": 0}
        self.write("manifest.json", self.manifest)
        window = {
            "window_id": "det_distractor_long_gap", "candidate_id": "sas_det_q1_c02",
            "game_id": "0022500828", "approved_game_role": "target_case_development",
            "source_frame_range_inclusive": [11000, 11002], "frames": 3,
            "source_pts_ticks_inclusive": [16520372, 16523342],
            "source_end_exclusive_pts_ticks": 16524872, "time_base": "1/90000",
            "native_duration_seconds": 0.05, "input_manifest": self.bind("manifest.json"),
        }
        self.proposal = {
            "schema_version": "nba_hard_example_reference_proposal/v0.1",
            "proposal_id": "nba_hard_example_reference_v0_1", "status": "design_only_awaiting_scope_approval",
            "runnable": False, "windows": [window], "approval_scope_requested": "Synthetic draft only, human acceptance before scoring.",
            "totals": {"new_proposed_label_frames": 3, "new_model_calls": 0, "training_runs": 0,
                       "raw_game_video_decodes": 0},
            "boundaries": {"protected_holdouts_unchanged": True, "original_nfhs_finish_line_unchanged": True,
                           "no_new_training_threshold_search_motion_selector_interpolation_or_model_inference": True},
            "label_contract": {"human_acceptance_required_before_reference_publication_or_scoring": True},
        }
        self.approval = {
            "schema_version": "nba_hard_example_reference_approval/v0.1", "status": "approved",
            "reviewer_id": "Ryan", "user_statement": "Synthetic approval fixture; not actual human review.",
            "recorded_at_utc": "2026-10-20T02:24:03+00:00", "source_commit": "b" * 40,
            "human_label_acceptance_required_before_publication_or_scoring": True,
            "new_model_inference_or_training_authorized": False,
        }
        self.doc = {
            "schema_version": "nba_ball_annotations/v0.1",
            "annotation_set_id": "det_distractor_long_gap_hard_example_v0_1",
            "candidate_id": "sas_det_q1_c02", "game_id": "0022500828",
            "approved_role": "target_case_development", "source_video": copy.deepcopy(source),
            "time_base": "1/90000", "coordinate_system": copy.deepcopy(nba.COORDINATE_SYSTEM),
            "frames": copy.deepcopy(frames[:3]), "annotations": [self.unlabeled(i) for i, _ in CAPTURED_NATIVE_ROWS[:3]],
            "revision": 0, "created_at_utc": "2026-10-20T02:24:03+00:00", "updated_at_utc": "2026-10-20T02:24:03+00:00",
            "review": {"status": "draft", "annotator_id": None, "reviewer_id": None, "reviewed_at_utc": None},
        }
        self.bind_proposal()

    @staticmethod
    def unlabeled(index):
        return {"frame_index": index, "annotation_status": "unlabeled", "visibility": None,
                "absence_reason": None, "game_ball_identity_certainty": None, "geometry": None,
                "localization_eligible": False, "difficulty_tags": [], "notes": None}

    def write(self, name, value):
        (self.root / name).write_text(json.dumps(value), encoding="utf-8")

    def bind(self, name, size=True):
        raw = (self.root / name).read_bytes()
        value = {"path": name, "sha256": hashlib.sha256(raw).hexdigest()}
        if size:
            value["bytes"] = len(raw)
        return value

    def bind_approval(self):
        self.write("approval.json", self.approval)
        self.doc["approval"] = self.bind("approval.json", size=False)

    def bind_proposal(self):
        self.write("proposal.json", self.proposal)
        self.approval.update(proposal=self.bind("proposal.json"),
                             approved_scope=self.proposal["approval_scope_requested"],
                             totals=copy.deepcopy(self.proposal["totals"]),
                             preserved_boundaries=copy.deepcopy(self.proposal["boundaries"]),
                             windows=[{k: copy.deepcopy(w[k]) for k in (
                                 "window_id", "candidate_id", "game_id", "source_frame_range_inclusive", "frames")}
                                 for w in self.proposal["windows"]])
        self.bind_approval()

    def verify(self, doc=None, images=False):
        return nba.verify_annotation_assets(self.doc if doc is None else doc, self.root, verify_images=images)

    def test_captured_native_transport_and_actual_pngs_without_source_reads(self):
        real_read = Path.read_bytes
        def guarded_read(path):
            self.assertNotEqual(path.resolve(), self.source_path.resolve(), "Source video was reread")
            return real_read(path)
        with patch.object(Path, "read_bytes", guarded_read):
            result = self.verify(images=True)
        self.assertEqual(result["frames_verified"], 3)
        self.assertEqual(result["full_source_bytes_read"], 0)
        self.assertEqual(result["human_label_review"], "pending")
        self.assertEqual(result["window_id"], "det_distractor_long_gap")
        self.assertEqual([r["source_pts_ticks"] for r in self.doc["frames"]], [16520372, 16521812, 16523342])

    def test_subset_additional_frames_and_wrong_annotation_window_rejected(self):
        for mode in ("subset", "additional", "wrong_id"):
            with self.subTest(mode=mode):
                changed = copy.deepcopy(self.doc)
                if mode == "subset":
                    changed["frames"] = changed["frames"][:-1]
                    changed["annotations"] = changed["annotations"][:-1]
                elif mode == "additional":
                    changed["frames"].append(copy.deepcopy(self.manifest["frames"][-1]))
                    changed["annotations"].append(self.unlabeled(11003))
                else:
                    changed["annotation_set_id"] = "wrong_hard_example_v0_1"
                with self.assertRaises(nba.AnnotationValidationError):
                    self.verify(changed)

    def test_source_candidate_game_role_and_all_frame_binding_fields_are_checked(self):
        changes = [lambda d: d.update(approved_role="future_training_candidate_pool"),
                   lambda d: d.update(candidate_id="different_candidate"),
                   lambda d: d.update(game_id="0022500829"),
                   lambda d: d["source_video"].update(sha256="0" * 64),
                   lambda d: d["frames"][1].update(source_pts_ticks=16521813),
                   lambda d: d["frames"][1]["png"].update(path="another.png"),
                   lambda d: d["frames"][1]["png"].update(sha256="0" * 64),
                   lambda d: d["frames"][1]["png"].update(rgb_sha256="0" * 64)]
        for mutate in changes:
            with self.subTest(mutate=mutate):
                changed = copy.deepcopy(self.doc)
                mutate(changed)
                with self.assertRaises(nba.AnnotationValidationError):
                    self.verify(changed)

    def test_approval_fields_cannot_expand_or_change_bound_scope(self):
        original = copy.deepcopy(self.approval)
        changes = [lambda a: a.update(status="pending"), lambda a: a.update(reviewer_id="Other"),
                   lambda a: a.update(user_statement=""), lambda a: a.update(approved_scope="Also fit Detroit"),
                   lambda a: a.update(new_model_inference_or_training_authorized=True),
                   lambda a: a.update(human_label_acceptance_required_before_publication_or_scoring=False),
                   lambda a: a["windows"][0].update(frames=2),
                   lambda a: a["windows"][0].update(approved_role="training"),
                   lambda a: a["windows"].append(copy.deepcopy(a["windows"][0])),
                   lambda a: a["totals"].update(new_proposed_label_frames=4),
                   lambda a: a["preserved_boundaries"].update(protected_holdouts_unchanged=False),
                   lambda a: a.update(unbound_override=True)]
        for mutate in changes:
            with self.subTest(mutate=mutate):
                self.approval = copy.deepcopy(original)
                mutate(self.approval)
                self.bind_approval()
                with self.assertRaises(nba.AnnotationValidationError):
                    self.verify()

    def test_sized_proposal_and_manifest_bindings_fail_closed(self):
        self.approval["proposal"]["bytes"] += 1
        self.bind_approval()
        with self.assertRaisesRegex(nba.AnnotationValidationError, "Size mismatch"):
            self.verify()
        self.bind_proposal()
        self.proposal["windows"][0]["input_manifest"]["bytes"] += 1
        self.bind_proposal()
        with self.assertRaisesRegex(nba.AnnotationValidationError, "Size mismatch"):
            self.verify()
        self.proposal["windows"][0]["input_manifest"] = self.bind("manifest.json")
        self.bind_proposal()
        self.manifest["frames"][1]["source_pts_ticks"] += 1
        self.write("manifest.json", self.manifest)
        with self.assertRaisesRegex(nba.AnnotationValidationError, "Hash mismatch"):
            self.verify()

    def test_proposed_native_end_boundary_duration_and_count_are_independent(self):
        original = copy.deepcopy(self.proposal)
        for key, value in (("source_end_exclusive_pts_ticks", 16524873),
                           ("native_duration_seconds", 0.051), ("frames", 4),
                           ("source_pts_ticks_inclusive", [16520372, 16523343])):
            with self.subTest(field=key):
                self.proposal = copy.deepcopy(original)
                self.proposal["windows"][0][key] = value
                self.bind_proposal()
                with self.assertRaises(nba.AnnotationValidationError):
                    self.verify()

    def test_proposal_schema_and_scientific_boundaries_cannot_be_reinterpreted(self):
        original = copy.deepcopy(self.proposal)
        changes = [lambda p: p.update(schema_version="nba_action_inputs/v0.1"),
                   lambda p: p.update(runnable=True),
                   lambda p: p["totals"].update(training_runs=1),
                   lambda p: p["boundaries"].update(protected_holdouts_unchanged=False),
                   lambda p: p["label_contract"].update(human_acceptance_required_before_reference_publication_or_scoring=False),
                   lambda p: p["windows"][0]["input_manifest"].pop("bytes"),
                   lambda p: p["windows"][0].update(frames="3")]
        for mutate in changes:
            with self.subTest(mutate=mutate):
                self.proposal = copy.deepcopy(original)
                mutate(self.proposal)
                self.bind_proposal()
                with self.assertRaises(nba.AnnotationValidationError):
                    self.verify()

    def test_source_audit_stat_and_producer_identity_remain_enforced(self):
        self.manifest["preparation"]["identity"]["window"]["approved_role"] = "future_training_candidate_pool"
        self.write("manifest.json", self.manifest)
        self.proposal["windows"][0]["input_manifest"] = self.bind("manifest.json")
        self.bind_proposal()
        with self.assertRaisesRegex(nba.AnnotationValidationError, "Producer identity"):
            self.verify()
        self.manifest["preparation"]["identity"]["window"]["approved_role"] = "target_case_development"
        self.write("manifest.json", self.manifest)
        self.proposal["windows"][0]["input_manifest"] = self.bind("manifest.json")
        self.bind_proposal()
        self.source_path.write_bytes(b"changed source")
        with self.assertRaisesRegex(nba.AnnotationValidationError, "Parent source stat changed"):
            self.verify()

    def test_original_png_bytes_are_checked_after_manifest_transport(self):
        frame = self.doc["frames"][0]
        (self.root / frame["png"]["path"]).write_bytes(b"altered PNG")
        self.assertEqual(self.verify()["frames_verified"], 0)
        with self.assertRaisesRegex(nba.AnnotationValidationError, "PNG hash mismatch"):
            self.verify(images=True)


if __name__ == "__main__":
    unittest.main()
