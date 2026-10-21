"""Metadata transport from the authorized, completed appearance review records.

These tests use the actual captured preparation/review JSON, never regenerate
source images or review media. A checkout without that local evidence skips
this explicitly identified captured-record integration suite.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.ball_tracking import nba_appearance_reference_acceptance as acceptance
from src.ball_tracking import nba_appearance_reference as preparation
from src.ball_tracking import nba_wasb_diagnostic as d

ROOT = Path(__file__).resolve().parents[1]
CAPTURED = ROOT / "configs/ball_tracking/reviews/nba_appearance_reference_acceptance_v0_1.json"


class CapturedRecords:
    """Rebind copies of producer-emitted JSON for isolated corruption checks."""
    def __init__(self, directory):
        self.directory = directory
        self.acceptance = d.read_json(CAPTURED)
        self.result = d.read_json(d.bound(ROOT, self.acceptance["preparation_result"]))
        self.proposal = d.read_json(d.bound(ROOT, self.acceptance["proposal"]))
        self.seal = d.read_json(d.bound(ROOT, self.acceptance["proposal_seal"]))
        self.media = d.read_json(d.bound(ROOT, self.acceptance["review_completion"]))
        self.manifest = d.read_json(d.bound(ROOT, self.media["artifacts"]["manifest"]))
        self.verification = d.read_json(d.bound(ROOT, self.media["artifacts"]["verification"]))
        self.prepared = d.read_json(d.bound(ROOT, self.acceptance["preparation"]))

    def write(self, name, document):
        path = self.directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        return d.binding(ROOT, path)

    def save(self):
        proposal = self.write("proposal.json", self.proposal)
        self.seal["proposal"] = proposal
        seal = self.write("seal.json", self.seal)
        self.media["identity"]["proposal"] = proposal
        self.manifest["identity"] = copy.deepcopy(self.media["identity"])
        self.media["artifacts"]["manifest"] = self.write("manifest.json", self.manifest)
        self.media["artifacts"]["verification"] = self.write("verification.json", self.verification)
        media = self.write("media.json", self.media)
        self.result["appearance_proposals"].update(proposal=proposal, seal=seal)
        self.result["media"].update(completion=media, artifacts=copy.deepcopy(self.media["artifacts"]))
        result = self.write("result.json", self.result)
        self.acceptance.update(preparation_result=result, proposal=proposal, proposal_seal=seal, review_completion=media)
        self.write("acceptance.json", self.acceptance)
        return self.directory / "acceptance.json"


@unittest.skipUnless(
    CAPTURED.is_file()
    and (ROOT / "data/outputs/ball_tracking/nba/appearance_reference_v0_1/preparation/preparation.json").is_file()
    and (ROOT / "data/outputs/ball_tracking/nba/appearance_reference_v0_1/review/completion.json").is_file(),
    "Requires authorized local captured appearance acceptance/review JSON")
class AppearanceAcceptanceTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / "data/outputs/t"
        parent.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="appearance_acceptance_test_", dir=parent)
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def fixture(self, name="inputs"):
        return CapturedRecords(self.directory / name)

    def test_actual_captured_records_publish_metadata_only_and_resume_exactly(self):
        f = self.fixture(); path = f.save(); output = self.directory / "accepted"
        prior = {p: p.read_bytes() for p in (path, f.directory / "proposal.json", f.directory / "seal.json", f.directory / "media.json")}
        digest = d.digest
        def metadata_only(path):
            path = Path(path)
            self.assertNotIn(path.suffix.lower(), (".npy", ".npz"))
            if path.suffix.lower() in (".png", ".mp4"):
                self.assertTrue(path.is_relative_to(ROOT / "data/outputs/ball_tracking/nba/appearance_reference_v0_1/review"))
            return digest(path)
        with patch.object(d, "digest", metadata_only), \
             patch.object(preparation.source_reference, "extract_frames", side_effect=AssertionError("No source decoding")), \
             patch.object(preparation.source_reference, "verify_raw_png", side_effect=AssertionError("No image inspection")):
            completed = acceptance.publish(ROOT, path, output)
            before = (output / "accepted_reference.json").read_bytes()
            resumed = acceptance.publish(ROOT, path, output)
        self.assertEqual(resumed, completed)
        self.assertEqual((output / "accepted_reference.json").read_bytes(), before)
        self.assertEqual(len(list((output / "attempts").iterdir())), 1)
        reference = d.read_json(output / "accepted_reference.json")
        for key in ("sources", "groups", "frames", "targets", "candidates", "totals"):
            self.assertEqual(reference[key], f.prepared[key])
        self.assertEqual(reference["rows"], f.proposal["rows"])
        self.assertEqual(reference["authorship"], f.proposal["authorship"])
        self.assertEqual(reference["proposal_seal_evidence"], f.seal)
        self.assertEqual(reference["counts"], {"ball": 10, "other_object": 10, "unresolved": 6})
        self.assertEqual(reference["source_roles"], f.result["census"]["source_roles"])
        self.assertEqual(reference["prior_evidence"], f.result["preserved"])
        self.assertEqual(reference["human_review"]["user_statement"], "I accept the proposals. Move forward chat")
        self.assertFalse(reference["limits"]["unresolved_used_as_negatives"])
        self.assertFalse(reference["limits"]["automatic_model_adoption"])
        self.assertEqual(reference["proposal_seal_evidence"]["disagreement"]["published"], "unresolved")
        self.assertTrue(all(p.read_bytes() == original for p, original in prior.items()))
        self.assertEqual(completed["resources"], {"source_pixel_reads": 0, "source_pixel_decodes": 0,
            "model_calls": 0, "candidate_array_reads": 0, "geometric_scores_computed": 0,
            **reference["review_artifact_byte_verification"]})
        self.assertEqual(reference["review_artifact_byte_verification"]["reviewed_artifact_files_hashed"], 33)

    def test_label_census_geometry_authorship_and_unknown_semantics_rejected(self):
        mutations = [
            ("missing", lambda f: f.proposal["rows"].pop(), "candidate label census"),
            ("geometry", lambda f: f.proposal["rows"][0].update(center_xy_px=[1, 2]), "geometry is not permitted"),
            ("author", lambda f: f.proposal["authorship"].update(not_blind=False), "AI authorship"),
            ("unknown", lambda f: next(r for r in f.proposal["rows"] if r["classification"] == "unresolved").update(subtype="head"), "Only confirmed"),
        ]
        for name, mutate, message in mutations:
            with self.subTest(name=name):
                f = self.fixture(name); mutate(f); path = f.save(); output = self.directory / (name + "_output")
                with self.assertRaisesRegex(ValueError, message):
                    acceptance.publish(ROOT, path, output)
                self.assertFalse((output / "accepted_reference.json").exists())
                failures = list((output / "attempts").glob("*/failed.json"))
                self.assertEqual(len(failures), 1)
                self.assertEqual(d.read_json(failures[0])["status"], "failed_preserved")

    def test_roles_counts_seal_and_reviewed_label_join_rejected(self):
        mutations = [
            ("role", lambda f: f.acceptance["source_roles"].update(sas_det_q1_c02="fit_eligible"), "source roles"),
            ("counts", lambda f: f.acceptance["accepted_counts"].update(ball=11), "class counts"),
            ("seal", lambda f: f.seal.update(preparation={"path": "wrong.json"}), "differs from its seal"),
            ("label", lambda f: f.manifest["frames"][2]["candidates"][0]["label"].update(classification="ball"), "candidate or label join"),
            ("frame", lambda f: f.manifest["frames"][0].update(source_frame_index=941), "source frame"),
            ("final", lambda f: f.media["stills"].pop(), "final-frame evidence"),
        ]
        for name, mutate, message in mutations:
            with self.subTest(name=name):
                f = self.fixture(name); mutate(f); path = f.save()
                with self.assertRaisesRegex(ValueError, message):
                    acceptance.publish(ROOT, path, self.directory / (name + "_output"))

    def test_publication_tampering_and_different_acceptance_cannot_be_rebound(self):
        f = self.fixture(); path = f.save(); output = self.directory / "accepted"
        completed = acceptance.publish(ROOT, path, output)
        f.acceptance["user_statement"] += " Changed after publication."
        f.write("acceptance.json", f.acceptance)
        with self.assertRaisesRegex(ValueError, "publication identity differs"):
            acceptance.publish(ROOT, path, output)
        f.acceptance["user_statement"] = "I accept the proposals. Move forward chat"
        f.write("acceptance.json", f.acceptance)
        reference_path = ROOT / completed["accepted_reference"]["path"]
        reference = d.read_json(reference_path); reference["rows"][0]["classification"] = "ball"
        reference_path.write_text(json.dumps(reference), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Bound file changed"):
            acceptance.publish(ROOT, path, output)

    def test_interrupted_publication_preserves_failure_and_resumes_without_overwrite(self):
        f = self.fixture(); path = f.save(); output = self.directory / "accepted"
        write_once = d.write_once
        def fail_completion(path, value):
            if Path(path) == output / "completion.json":
                raise OSError("simulated interruption after accepted artifact")
            return write_once(path, value)
        with patch.object(d, "write_once", fail_completion), self.assertRaisesRegex(OSError, "simulated interruption"):
            acceptance.publish(ROOT, path, output)
        original = (output / "accepted_reference.json").read_bytes()
        failures = list((output / "attempts").glob("*/failed.json"))
        self.assertEqual(len(failures), 1)
        failed_before = failures[0].read_bytes()
        complete = acceptance.publish(ROOT, path, output)
        self.assertEqual(complete["status"], "completed")
        self.assertEqual((output / "accepted_reference.json").read_bytes(), original)
        self.assertEqual(failures[0].read_bytes(), failed_before)
        self.assertEqual(len(list((output / "attempts").iterdir())), 2)

    def test_same_length_review_media_mutation_is_rejected_without_decoding(self):
        f = self.fixture(); original = f.media["artifacts"]["video"]
        changed = bytearray((ROOT / original["path"]).read_bytes())
        changed[-1] ^= 1
        video = self.directory / "same_length_changed.mp4"; video.write_bytes(changed)
        self.assertEqual(video.stat().st_size, original["bytes"])
        f.media["artifacts"]["video"] = {**original, "path": video.relative_to(ROOT).as_posix()}
        path = f.save()
        with self.assertRaisesRegex(ValueError, "Bound file changed"):
            acceptance.publish(ROOT, path, self.directory / "accepted")
        self.assertFalse((self.directory / "accepted/accepted_reference.json").exists())


if __name__ == "__main__":
    unittest.main()
