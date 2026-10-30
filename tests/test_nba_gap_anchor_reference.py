"""Source transport, control preservation and honest draft references."""
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from src.ball_tracking import nba_gap_anchor_reference as reference
from src.ball_tracking import nba_temporal_gap_continuous as continuous
from src.ball_tracking import nba_wasb_diagnostic as d
from tests.test_nba_temporal_gap_continuous import produced_context, resources
from tests.test_nba_hard_example_diagnostic import label


def unknown_annotation(index):
    return {"frame_index": index, "annotation_status": "labeled", "visibility": "indeterminate",
        "absence_reason": None, "game_ball_identity_certainty": "ambiguous", "geometry": None,
        "localization_eligible": False, "difficulty_tags": [], "notes": "Source evidence does not establish the ball center."}


def write_json(root, name, value):
    path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2)+"\n", encoding="utf-8")
    return d.binding(root, path)


def source_fixture(root):
    """Saved producer-shaped records with real PNGs and independently built clocks."""
    repository = Path(__file__).resolve().parents[1]
    names = ("nba_gap_anchor_reference.py", "annotations.py", "nba_annotations.py",
             "nba_temporal_gap_continuous_review.py", "nba_wasb_diagnostic.py", "wasb_development_observation.py")
    for name in names:
        target = root / "src/ball_tracking" / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((repository / "src/ball_tracking" / name).read_bytes())
    target = root / "tests/test_nba_gap_anchor_reference.py"; target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(Path(__file__).read_bytes())
    sources = []
    for kind in ("nba", "nfhs"):
        cid = "nba_source" if kind == "nba" else "possession_fixture"
        video_path = root / f"data/clips/{cid}.mp4"; video_path.parent.mkdir(parents=True, exist_ok=True)
        video_path.write_bytes(b"Synthetic source identity for " + cid.encode())
        video = {"path": video_path.relative_to(root).as_posix(), "sha256": d.digest(video_path),
                 "width_px": 64, "height_px": 40, "frame_count": 90}
        if kind == "nfhs":
            video["fps"] = 25.0
        native = []; frames = []
        for index in range(90):
            if kind == "nba":
                buffer = io.BytesIO(); image = Image.new("RGB", (64, 40), (index, 30, 70)); image.save(buffer, "PNG")
                png = root / f"data/outputs/original/{cid}/source_{index:06d}.png"; png.parent.mkdir(parents=True, exist_ok=True)
                png.write_bytes(buffer.getvalue())
                entry = {"source_frame_index": index, "source_pts_ticks": index*1500,
                    "png": {**d.binding(root, png), "rgb_sha256": hashlib.sha256(image.tobytes()).hexdigest()}}
            else:
                entry = {"source_frame_index": index, "source_pts_ticks": index*3600,
                         "container_pts_ticks": 3600+index*3600, "duration_ticks": 3600}
            native.append(entry)
            protected = kind == "nfhs" and index >= 80
            row = {"candidate_id": cid, "source_frame_index": index, "source_pts_ticks": entry["source_pts_ticks"],
                   "decision": "withheld" if protected else "preserved_original", "baseline_center_xy_px": None if protected else [20, 20]}
            if not protected:
                row["source_frame"] = entry
            if kind == "nfhs":
                row["container_pts_ticks"] = entry["container_pts_ticks"]
            frames.append(row)
        gaps = []
        for number, width in enumerate((1, 1, 1, 2, 2)):
            lo = 10+15*number; hi = lo+width-1
            for index in range(lo, hi+1):
                frames[index]["baseline_center_xy_px"] = None; frames[index]["decision"] = "filled_saved_candidate"
            gaps.append({"gap_id": f"{cid}:{lo}-{hi}", "source_frame_range_inclusive": [lo, hi],
                "anchors": [{"source_frame_index": lo-1}, {"source_frame_index": hi+1}],
                "reason": "all_frames_have_unambiguous_saved_candidates"})
        source = {"candidate_id": cid, "kind": kind, "analysis_group": "synthetic_development", "source_video": video,
            "source_end_exclusive_pts_ticks": 90*(1500 if kind == "nba" else 3600),
            "time_origin": "native_container" if kind == "nba" else "clip_first_frame", "frames": frames,
            "protected_ranges": [] if kind == "nba" else [[80, 89]],
            "segments": [{"range_inclusive": [0, 89 if kind == "nba" else 79], "gaps": gaps}]}
        if kind == "nba":
            source["source_manifest"] = write_json(root, "data/outputs/nba_manifest.json", {
                "candidate_id": cid, "source_video": video, "time_base": "1/90000", "frames": native,
                "source_end_exclusive_pts_ticks": 90*1500})
        else:
            source["possession"] = {"possession_id": cid, "source_video": video,
                                    "visible_segments": [[0, 79]], "protected_ranges": [[80, 89]]}
            packet = write_json(root, "data/outputs/packets.json", {
                "streams": [{"width": 64, "height": 40, "nb_frames": "90", "time_base": "1/90000"}],
                "packets": [{"pts": f["container_pts_ticks"], "duration": 3600} for f in native]})
            source["native_timestamps"] = write_json(root, "data/outputs/timing.json", {
                "schema_version": "nfhs_container_native_timestamps/v0.1", "status": "verified", "candidate_id": cid,
                "source_video": video, "actual_source_binding": d.binding(root, video_path), "time_base": "1/90000",
                "time_origin": "clip_first_frame", "container_time_origin_ticks": 3600, "original_time_base": "1/90000",
                "packet_probe": packet, "frames": native, "source_end_exclusive_pts_ticks": 90*3600,
                "container_end_exclusive_pts_ticks": 91*3600})
        sources.append(source)
    selection = {"schema_version": continuous.SCHEMA, "sources": sources}
    selection_binding = write_json(root, "data/outputs/selection.json", selection)
    rows = []
    for source, indices in ((sources[0], range(54, 58)), (sources[1], range(9, 12))):
        for index in indices:
            rows.append({"continuous_source_id": source["candidate_id"], "candidate_id": "historical_short_window",
                "source_frame_index": index, "source_frame": source["frames"][index]["source_frame"],
                "source_video": source["source_video"], "annotation": label(index, (20, 20)),
                "baseline": {"outcome": "matched"}, "selected": {"outcome": "matched"}})
    report_binding = write_json(root, "data/outputs/report.json", {"status": "completed", "selection": selection_binding, "frames": rows})
    plan = root / "docs/plan.md"; plan.parent.mkdir(parents=True, exist_ok=True); plan.write_text("Synthetic approved scope", encoding="utf-8")
    plan_binding = d.binding(root, plan)
    approval = write_json(root, "configs/review.json", {"schema_version": "nba_gap_anchor_reference_approval/v0.1",
        "status": "approved", "approved_by": "Ryan", "user_statement": "Move forward chat", "plan": plan_binding, "totals": reference.TOTALS})
    scope = {"schema_version": reference.SCOPE_SCHEMA, "status": "approved", "plan": plan_binding, "approval": approval,
        "selection": selection_binding, "report": report_binding, "totals": reference.TOTALS,
        "groups": reference.derive_groups(selection), "output_root": "data/outputs/reference",
        "implementation": reference.implementation_bindings(root), "focused_tests": d.binding(root, target)}
    write_json(root, "configs/scope.json", scope)
    return scope


def prepared_fixture(root):
    """Call the real preparation producer; only video decoding is synthetic."""
    scope = source_fixture(root); requests = []
    def decoder(_root, possession, segment):
        reference.nfhs.guard_segment(possession, segment); requests.append(segment)
        for index in range(segment[0], segment[1]+1):
            yield index, np.full((40, 64, 3), index, dtype=np.uint8)
    with patch.object(reference.nfhs, "decode_segment", decoder):
        ready = reference.prepare(root, "configs/scope.json")
    path = root / ready["preparation"]["path"]; preparation = d.read_json(path)
    proposal = {"schema_version": reference.PROPOSAL_SCHEMA, "preparation": ready["preparation"], "status": "draft",
        "authorship": {"annotator_id": "AI test fixture", "method": "source_first_ai", "not_blind": True}, "human_review": "pending",
        "new_annotations": [{"continuous_source_id": f["continuous_source_id"], "source_frame_index": f["source_frame_index"],
                             "annotation": unknown_annotation(f["source_frame_index"])} for f in preparation["frames"] if f["reference_origin"] == "new"],
        "existing_controls": [{"continuous_source_id": f["continuous_source_id"], "source_frame_index": f["source_frame_index"],
                               "existing_reference": f["existing_reference"]} for f in preparation["frames"] if f["reference_origin"] == "existing"]}
    write_json(root, "data/outputs/proposal.json", proposal)
    return {"scope": scope, "preparation": preparation, "preparation_path": path,
            "proposal": proposal, "proposal_path": root / "data/outputs/proposal.json", "decode_requests": requests}


class GapAnchorReferenceTests(unittest.TestCase):
    def test_preparation_freezes_native_frames_and_controls_then_resumes_without_decode(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); fixture = prepared_fixture(root); prep = fixture["preparation"]
            self.assertEqual(len(prep["frames"]), 74)
            self.assertEqual(len(fixture["decode_requests"]), 5)
            self.assertEqual(prep["resources"]["nfhs_decoded_frames"], 37)
            self.assertFalse(prep["new_labels_created"])
            self.assertTrue(all("annotation" not in f for f in prep["frames"]))
            controls = [f for f in prep["frames"] if f["reference_origin"] == "existing"]
            self.assertEqual(len(controls), 7)
            self.assertTrue(any(f["continuous_source_id"] != f["existing_reference"]["row"]["candidate_id"] for f in controls))
            with patch.object(reference.nfhs, "decode_segment", side_effect=AssertionError("must not re-decode")):
                ready = reference.prepare(root, "configs/scope.json")
            self.assertEqual(ready["preparation"], fixture["proposal"]["preparation"])
            loaded, _ = reference.validate_proposal(root, fixture["proposal_path"])
            self.assertEqual(loaded, prep)

    def test_proposal_rejects_changed_controls_context_labels_and_false_acceptance(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); fixture = prepared_fixture(root)
            for change in ("control", "context", "accepted", "unknown_geometry"):
                proposal = copy.deepcopy(fixture["proposal"])
                if change == "control":
                    proposal["existing_controls"][0]["existing_reference"]["row"]["annotation"]["notes"] = "changed"
                elif change == "context":
                    proposal["new_annotations"][0]["source_frame_index"] -= 2
                elif change == "accepted":
                    proposal["human_review"] = "accepted"
                else:
                    proposal["new_annotations"][0]["annotation"]["geometry"] = {
                        "center_xy_px": [20, 20], "source": "human_amodal_estimate", "uncertainty_radius_px": 2}
                write_json(root, "data/outputs/bad_proposal.json", proposal)
                with self.subTest(change=change), self.assertRaises(ValueError):
                    reference.validate_proposal(root, root / "data/outputs/bad_proposal.json")

    def test_tampered_preparation_and_png_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); fixture = prepared_fixture(root)
            raw_path = root / fixture["preparation"]["frames"][0]["raw_png"]["path"]
            original = raw_path.read_bytes(); raw_path.write_bytes(original+b"tampered")
            with self.assertRaisesRegex(ValueError, "PNG hash"):
                reference.load_ready_preparation(root, fixture["preparation_path"])
            raw_path.write_bytes(original)
            altered = copy.deepcopy(fixture["preparation"]); altered["frames"][0]["source_pts_ticks"] += 1
            fixture["preparation_path"].write_text(json.dumps(altered), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source freeze"):
                reference.load_ready_preparation(root, fixture["preparation_path"])

    def test_protected_context_and_source_changes_fail_before_extraction(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); scope = source_fixture(root)
            selection = reference.read_bound(root, scope["selection"]); report = reference.read_bound(root, scope["report"])
            source = selection["sources"][1]
            source["protected_ranges"] = [[72, 89]]
            with self.assertRaisesRegex(ValueError, "protected"):
                reference.census(selection, report, scope["groups"])
            (root / selection["sources"][0]["source_video"]["path"]).write_bytes(b"changed")
            with patch.object(reference, "extract_frames") as extract:
                with self.assertRaisesRegex(ValueError, "Source video bytes"):
                    reference.prepare(root, "configs/scope.json")
                extract.assert_not_called()

    def test_failed_decode_is_preserved_and_no_preparation_is_published(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source_fixture(root)
            with patch.object(reference.nfhs, "decode_segment", side_effect=ValueError("synthetic decoding failure")):
                with self.assertRaisesRegex(ValueError, "synthetic decoding"):
                    reference.prepare(root, "configs/scope.json")
            output = root / "data/outputs/reference"
            failures = list(output.glob("attempts/*/failed.json"))
            self.assertEqual(len(failures), 1)
            self.assertEqual(d.read_json(failures[0])["resources"]["existing_png_reads"], 37)
            self.assertFalse((output / "preparation.json").exists())
            self.assertFalse((output / "preparation_ready.json").exists())

    def test_actual_continuous_producer_and_report_join(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); context, _, _, reader = produced_context(root)
            segment = continuous.select_segment(root, context, resources(), cache_reader=reader)
            source = {**context["source"], "segments": [segment], "frames": segment["frames"], "time_origin": "native_container"}
            # Keep the actual emitted filled gap and its neighboring source records.
            groups = reference.derive_groups({"sources": [source]})
            self.assertEqual(len(groups), 1)
            # The producer fixture's first gap at frame2 lacks the proposed two-frame lead-in;
            # shift its source indices consistently, leaving all emitted field contracts intact.
            for frame in source["frames"]:
                frame["source_frame_index"] += 1; frame["source_frame"]["source_frame_index"] += 1
            segment["range_inclusive"] = [1, 14]
            # Use an interior seven-frame batch from the same emitted producer; the gap
            # is frame3 and its first context frame0 needs one real-shaped preceding row.
            first = copy.deepcopy(source["frames"][0]); first["source_frame_index"] = 0
            first["source_frame"]["source_frame_index"] = 0; source["frames"].insert(0, first)
            segment["range_inclusive"] = [0, 14]
            filled = next(g for g in segment["gaps"] if g["reason"] == "all_frames_have_unambiguous_saved_candidates")
            filled["source_frame_range_inclusive"] = [3, 3]
            for anchor in filled["anchors"]:
                anchor["source_frame_index"] += 1
            groups = reference.derive_groups({"sources": [source]})
            rows = []
            for frame in source["frames"]:
                if frame["source_frame_index"] in (2, 3, 4):
                    rows.append({"continuous_source_id": "synthetic", "source_frame_index": frame["source_frame_index"],
                        "source_frame": frame["source_frame"], "source_video": source["source_video"],
                        "annotation": label(frame["source_frame_index"], (50, 50))})
            with patch.object(reference, "TOTALS", {"groups": 1, "target_frames": 3, "context_frames": 7,
                                                   "new_references": 0, "reused_references": 3}):
                frames = reference.census({"sources": [source]}, {"frames": rows}, groups)
            self.assertEqual([f["role"] for f in frames], ["context_only", "context_only", "anchor", "fill", "anchor", "context_only", "context_only"])
            self.assertEqual([f["existing_reference"]["row"] for f in frames if f["reference_origin"] == "existing"], rows)


if __name__ == "__main__":
    unittest.main()
