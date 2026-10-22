"""Boundaries and native timing for the campaign's pending source references."""
import copy
import json
import tempfile
from pathlib import Path
import unittest
import numpy as np

from src.ball_tracking.completion_references import (
    accepted_campaign_reference, accepted_inventory, binding, guard_range,
    presentation_timeline, read_json, render_frame,
)


class CompletionReferenceTests(unittest.TestCase):
    def setUp(self):
        self.config = {"possession_id": "possession_003", "range_inclusive": [0, 119],
                       "training_eligible": False, "checkpoint_selection_eligible": False,
                       "human_acceptance": "pending", "role": "post_selection_evaluation_only"}
        self.possession = {"source_video": {"frame_count": 500},
                           "protected_ranges": [[225, 299]], "visible_segments": [[0, 224], [300, 499]]}

    def test_reject_protected_and_existing_reference_before_decode(self):
        self.assertEqual(guard_range(self.config, self.possession, {}), list(range(120)))
        with self.assertRaisesRegex(ValueError, "accepted"):
            guard_range(self.config, self.possession, {("possession_003", 19): {}})
        self.config["range_inclusive"] = [224, 300]
        with self.assertRaisesRegex(ValueError, "protected"):
            guard_range(self.config, self.possession, {})

    def test_role_and_acceptance_cannot_change_in_renderer(self):
        for key, value in (("training_eligible", True), ("checkpoint_selection_eligible", True),
                           ("human_acceptance", "accepted")):
            changed = {**self.config, key: value}
            with self.assertRaisesRegex(ValueError, "pending evaluation-only"):
                guard_range(changed, self.possession, {})

    def test_native_pts_sorted_and_origin_preserved(self):
        # Actual H.264 packets can arrive in decode order, with a nonzero PTS origin.
        probe = {"streams": [{"time_base": "1/12800"}],
                 "packets": [{"pts": 1536, "duration": 512}, {"pts": 512, "duration": 512},
                             {"pts": 1024, "duration": 512}]}
        rows = presentation_timeline(probe, 3)
        self.assertEqual([r["native_pts_ticks"] for r in rows], [512, 1024, 1536])
        self.assertEqual([r["clip_relative_seconds"] for r in rows], [0, .04, .08])
        self.assertEqual(rows[0]["native_pts_seconds"], .04)
        probe["packets"][0]["pts"] = 2048
        with self.assertRaisesRegex(ValueError, "Non-contiguous"):
            presentation_timeline(probe, 3)

    def test_binding_accepts_relative_paths(self):
        # Regression: the CLI initially rendered a video then failed to bind a relative path.
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            path = Path(directory) / "sample.txt"
            path.write_text("source", encoding="utf-8")
            relative = path.relative_to(Path.cwd())
            self.assertEqual(binding(Path.cwd(), relative), binding(Path.cwd(), path))

    def test_overlay_uses_actual_source_dimensions(self):
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        item = {"source_frame_index": 10, "native_pts_ticks": 5120, "native_time_base": "1/12800",
                "annotation": {"visibility": "partially_visible",
                               "geometry": {"center_xy_px": [500, 300], "uncertainty_radius_px": 8}}}
        result = render_frame(frame, item, 120, "new_source", 119)
        self.assertEqual(result[225, 375].tolist(), [0, 255, 255])
        self.assertEqual(result[150, 250].tolist(), [0, 0, 0])


class AcceptedCampaignReferenceTests(unittest.TestCase):
    """Consumer checks derived from the actual human-accepted batch01 producer.

    These metadata-only integration tests run when its ignored publication is
    present. They never decode footage or modify the authoritative evidence.
    """

    @classmethod
    def setUpClass(cls):
        cls.repository = Path(__file__).resolve().parents[1]
        cls.receipt_relative = "configs/ball_tracking/reviews/ball_completion_reference_batch_01_acceptance_v0_1.json"
        cls.real_receipt = read_json(cls.repository / cls.receipt_relative)
        cls.publication_relative = cls.real_receipt["accepted_reference"]["path"]
        publication_path = cls.repository / cls.publication_relative
        if not publication_path.is_file():
            raise unittest.SkipTest("Actual accepted batch01 publication is not available in this checkout")
        if binding(cls.repository, publication_path) != cls.real_receipt["accepted_reference"]:
            raise AssertionError("Authoritative captured publication does not match its acceptance receipt")
        cls.real_publication = read_json(publication_path)
        cls.old_config = read_json(cls.repository / "configs/ball_tracking/completion_campaign/reference_batch_01_v0_1.json")
        cls.source_contract = read_json(cls.repository / cls.old_config["source_contract"])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        # Copy the producer's exact bound evidence, not a consumer-shaped fixture.
        for key in ("proposal", "review_manifest"):
            source = self.repository / self.real_publication[key]["path"]
            target = self.root / self.real_publication[key]["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())

    def write_fixture(self, publication=None, receipt=None):
        publication = copy.deepcopy(self.real_publication if publication is None else publication)
        receipt = copy.deepcopy(self.real_receipt if receipt is None else receipt)
        path = self.root / self.publication_relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(publication), encoding="utf-8")
        entry = binding(self.root, path)
        receipt["accepted_reference"] = copy.deepcopy(entry)
        receipt_path = self.root / self.receipt_relative
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        entry["acceptance_receipt"] = binding(self.root, receipt_path)
        return entry

    def consume(self, entry):
        return accepted_campaign_reference(self.root, entry, self.source_contract["possessions"])

    def test_actual_publication_preserves_120_rows_and_old_config_replay(self):
        old, _ = accepted_inventory(self.repository, self.old_config)
        self.assertEqual(len(old), 320)
        new_config = copy.deepcopy(self.old_config)
        new_config["additional_accepted_references"] = [{
            **self.real_receipt["accepted_reference"],
            "acceptance_receipt": binding(self.repository, self.repository / self.receipt_relative),
        }]
        new, preserved = accepted_inventory(self.repository, new_config)
        self.assertEqual(len(new), 440)
        self.assertTrue(all(new[key] == row for key, row in old.items()))
        self.assertTrue(all(new[("possession_003", row["frame_index"])] == row
                            for row in self.real_publication["annotations"]))
        self.assertIn(self.real_receipt["accepted_reference"], preserved)
        self.assertIn(binding(self.repository, self.repository / self.receipt_relative), preserved)
        possession = next(p for p in self.source_contract["possessions"] if p["possession_id"] == "possession_003")
        self.assertEqual(len(guard_range(self.old_config, possession, old)), 120)
        with self.assertRaisesRegex(ValueError, "relabel an accepted reference"):
            guard_range(new_config, possession, new)

    def test_publication_or_receipt_byte_mutation_is_rejected(self):
        for which in ("publication", "receipt"):
            with self.subTest(which=which):
                entry = self.write_fixture()
                path = self.publication_relative if which == "publication" else self.receipt_relative
                with (self.root / path).open("a", encoding="utf-8") as handle:
                    handle.write(" ")
                with self.assertRaisesRegex(ValueError, "binding changed"):
                    self.consume(entry)

    def test_accepted_status_authorship_roles_and_receipt_links_are_enforced(self):
        changes = [
            ("publication", "status", "assistant_proposal_pending_human_acceptance", "human acceptance"),
            ("receipt", "status", "pending", "human acceptance"),
            ("publication", "annotation_origin", "human_annotation", "authorship"),
            ("publication", "training_eligible", True, "evaluation-only"),
            ("receipt", "checkpoint_selection_eligible", True, "evaluation-only"),
            ("receipt", "protected_evaluation_authorized", True, "evaluation-only"),
            ("receipt", "model_output_acceptance", True, "evaluation-only"),
            ("publication", "acceptance_receipt_path", "wrong_receipt.json", "links disagree"),
            ("receipt", "batch_id", "another_batch", "links disagree"),
        ]
        for target, key, value, message in changes:
            with self.subTest(target=target, key=key):
                publication, receipt = copy.deepcopy(self.real_publication), copy.deepcopy(self.real_receipt)
                (publication if target == "publication" else receipt)[key] = value
                with self.assertRaisesRegex(ValueError, message):
                    self.consume(self.write_fixture(publication, receipt))
        entry = self.write_fixture()
        del entry["acceptance_receipt"]
        with self.assertRaisesRegex(ValueError, "bound acceptance receipt"):
            self.consume(entry)

    def test_rehashed_annotation_or_native_frame_cannot_diverge_from_review(self):
        for target in ("annotations", "frames"):
            publication = copy.deepcopy(self.real_publication)
            if target == "annotations":
                publication[target][0]["geometry"]["center_xy_px"][0] += 1
            else:
                publication[target][0]["native_pts_ticks"] += 1
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "reviewed proposal/media records"):
                self.consume(self.write_fixture(publication))

    def test_conflicting_existing_row_rejected_identical_row_deduplicated(self):
        entry = self.write_fixture()
        directory = self.root / "legacy"
        directory.mkdir()
        row = copy.deepcopy(self.real_publication["annotations"][0])
        legacy = {"review": {"status": "reviewed"}, "possession_id": "possession_003", "annotations": [row]}
        legacy_path = directory / "accepted.json"
        legacy_path.write_text(json.dumps(legacy), encoding="utf-8")
        gap_path = self.root / "gap.json"
        gap_path.write_text(json.dumps({"status": "human_accepted_assisted_reference", "new_annotations": []}), encoding="utf-8")
        contract_path = self.root / "contract.json"
        contract_path.write_text(json.dumps(self.source_contract), encoding="utf-8")
        config = {"accepted_curated_directory": "legacy", "accepted_gap_reference": binding(self.root, gap_path),
                  "source_contract": "contract.json", "additional_accepted_references": [entry]}
        accepted, _ = accepted_inventory(self.root, config)
        self.assertEqual(len(accepted), 120)
        legacy["annotations"][0]["geometry"]["center_xy_px"][0] += 1
        legacy_path.write_text(json.dumps(legacy), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Conflicting accepted campaign row"):
            accepted_inventory(self.root, config)


if __name__ == "__main__":
    unittest.main()
