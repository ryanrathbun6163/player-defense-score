"""Review transports actual producer records and independently checks image panels."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import uuid

import numpy as np
from PIL import Image

from src.ball_tracking import nba_ball_distractor_reference_review as render
from src.ball_tracking import nba_wasb_diagnostic as d
from tests.test_nba_ball_distractor_reference import prepared_fixture
from tests.test_nba_wasb_diagnostic import FFBIN


class BallDistractorReferenceReviewTests(unittest.TestCase):
    def setUp(self):
        repository = Path(__file__).resolve().parents[1]
        self.root = repository/"data/outputs/t/ball_distractor_reference_review_tests"/uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.fixture = prepared_fixture(self.root)
        for name in ("nba_ball_distractor_reference_review.py", "nba_annotations.py", "nba_action_review.py", "nba_wasb_diagnostic.py"):
            path = self.root/"src/ball_tracking"/name
            path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes((repository/"src/ball_tracking"/name).read_bytes())
        self.preparation_path = self.fixture["preparation_path"]
        prepared = self.fixture["preparation"]
        rows = []
        for index,blank in enumerate(prepared["new_review_rows"]):
            classification = "unresolved" if blank["center_xy_px"] is None or index%3 == 0 else "ball" if index%3 == 1 else "other_object"
            rows.append({"row_id":blank["row_id"],"classification":classification,
                "subtype":"head" if classification == "other_object" else None,"center_xy_px":blank["center_xy_px"],
                "physical_object_instance_id":None if classification == "unresolved" else f"synthetic_object:{index}",
                "episode_id":None if classification == "unresolved" else f"synthetic_episode:{index//3}",
                "rationale":"Synthetic renderer test judgment, not a source annotation.","duplicate_of_row_id":None})
        self.proposal = {"schema_version":"nba_ball_distractor_reference_proposal/v0.1",
            "preparation":d.binding(self.root,self.preparation_path),"authorship":{"kind":"synthetic_test"},"human_review":"pending","rows":rows,
            "reused_grouping":[{"candidate_key":c["accepted_candidate"]["candidate_key"],"physical_object_instance_id":None,
                "episode_id":None,"rationale":"Synthetic grouping supplement."} for c in prepared["reused_controls"]]}
        self.proposal_path = self.root/"data/outputs/proposal.json"
        self.write_proposal()

    def write_proposal(self):
        self.proposal_path.write_text(json.dumps(self.proposal,indent=2)+"\n",encoding="utf-8")

    def data(self, labeled=True):
        prep,proposal = render.inputs(self.root,self.preparation_path,self.proposal_path if labeled else None)
        groups = render.source_groups(prep,proposal)
        return prep,proposal,groups,render.records(groups)

    def test_producer_transport_census_native_clocks_points_and_no_source_outcomes(self):
        prep,proposal,groups,rows = self.data()
        self.assertEqual((len(groups),len(rows),sum(len(g["rows"]) for g in groups)),(3,15,10))
        expected = {c["candidate_group_id"]:c for c in prep["candidates"]}
        seen = []
        for group in groups:
            source_frames = [f for f in prep["frames"] if f["group_id"] == group["group_id"]]
            self.assertEqual(group["frames"],source_frames)
            for candidate in group["rows"]:
                seen.append(candidate["row_id"])
                if candidate["row_id"] in expected:
                    self.assertEqual(candidate["center_xy_px"],expected[candidate["row_id"]]["center_xy_px"])
                self.assertFalse({"components","native_score","old_geometric_outcome","emitted_in_saved_selection"} & candidate.keys())
        self.assertEqual(set(seen),{r["row_id"] for r in proposal["rows"]})
        for row in rows:
            self.assertEqual(row["source_pts_ticks"],row["source_frame"]["source_pts_ticks"])
            self.assertTrue(all(c["label"] is None for c in row["rows"]) if not row["target"] else all(c["label"] is not None for c in row["rows"]))
        self.assertEqual(sum(r["duration_ticks"] for r in rows),3*288000)
        _,_,blank,_ = self.data(False)
        self.assertTrue(all(c["label"] is None for g in blank for c in g["rows"]))

    def test_proposal_rejects_changed_candidate_missing_rows_and_reused_order(self):
        original = copy.deepcopy(self.proposal)
        self.proposal["rows"][0]["center_xy_px"][0] += 1; self.write_proposal()
        with self.assertRaisesRegex(ValueError,"center changed"):
            self.data()
        self.proposal = copy.deepcopy(original); self.proposal["rows"].pop(); self.write_proposal()
        with self.assertRaisesRegex(ValueError,"census/order"):
            self.data()
        self.proposal = copy.deepcopy(original); self.proposal["reused_grouping"].reverse(); self.write_proposal()
        with self.assertRaisesRegex(ValueError,"Reused grouping"):
            self.data()
        self.proposal = copy.deepcopy(original); self.proposal["rows"][-1]["classification"] = "other_object"; self.write_proposal()
        with self.assertRaisesRegex(ValueError,"Unavailable contrast"):
            self.data()

    def test_source_sheets_have_exact_unmarked_five_frame_crops_and_resume_bindings(self):
        prep,_,groups,_ = self.data(False)
        args = self.root,self.preparation_path,"data/outputs/source_sheets"
        result = render.build_source_sheets(*args)
        self.assertEqual(len(result["stills"]),3)
        manifest = d.read_json(self.root/result["artifacts"]["manifest"]["path"])
        self.assertFalse(manifest["object_classes_displayed"])
        self.assertFalse(manifest["markers_displayed"])
        self.assertFalse(manifest["model_scores_displayed"])
        self.assertFalse(manifest["geometric_outcomes_displayed"])
        groups_by_id = {g["group_id"]:g for g in groups}
        for still in result["stills"]:
            group = groups_by_id[still["group_id"]]
            with Image.open(self.root/still["image"]["path"]) as sheet:
                for candidate in still["crop_records"]:
                    cx,cy = candidate["center_xy_px"]
                    box = [int(np.floor(cx))-96,int(np.floor(cy))-96,int(np.floor(cx))+96,int(np.floor(cy))+96]
                    self.assertEqual(candidate["crop_xyxy_px"],box)
                    for frame,placement in zip(group["frames"],candidate["sheet_crop_boxes"],strict=True):
                        with Image.open(self.root/frame["raw_png"]["path"]) as source:
                            expected = source.crop(box).resize((224,224),Image.Resampling.NEAREST)
                            self.assertEqual(sheet.crop(placement).tobytes(),expected.tobytes())
        anchors = [c for s in result["stills"] for c in s["crop_records"] if c["center_kind"] == "distance_anchor"]
        self.assertEqual(len(anchors),1)
        with patch.object(render,"source_sheet",side_effect=AssertionError("resume must not rerender")):
            self.assertEqual(render.build_source_sheets(*args),result)
        path = self.root/result["stills"][0]["image"]["path"]; path.write_bytes(path.read_bytes()+b"tamper")
        with self.assertRaisesRegex(ValueError,"Bound file changed"):
            render.build_source_sheets(*args)

    def test_paired_crops_target_markers_class_keys_and_unknown_contrast(self):
        _,_,groups,rows = self.data()
        target = next(r for r in rows if r["target"] and any(c["center_xy_px"] is None for c in r["rows"]))
        image = render.source_image(self.root,target,target["source_frame"])
        canvas,markers = render.render_frame(image,target,len(groups))
        self.assertEqual(len(markers),2*sum(c["center_xy_px"] is not None for c in target["rows"]))
        pixels = np.asarray(canvas).copy(); render.verify_pixels(pixels,canvas,markers,target)
        for j,candidate in enumerate(target["rows"]):
            if candidate["center_xy_px"] is None:
                continue
            x = 10+318*j
            expected = image.crop(render.crop_box(candidate["center_xy_px"])).resize((144,144),Image.Resampling.NEAREST)
            self.assertEqual(canvas.crop((x,580,x+144,724)).tobytes(),expected.tobytes())
        altered = copy.deepcopy(target); altered["rows"][0]["label"]["classification"] = "other_object"
        self.assertNotEqual(render.key_bits(target),render.key_bits(altered))
        orange = np.all(pixels == render.ORANGE,axis=2); pixels[orange] = [15,20,29]
        with self.assertRaisesRegex(ValueError,"marker"):
            render.verify_pixels(pixels,canvas,markers,target)
        for context in (rows[0],rows[-1]):
            _,context_markers = render.render_frame(render.source_image(self.root,context,context["source_frame"]),context,len(groups))
            self.assertEqual(context_markers,[])

    def test_partial_source_attempt_preserved_and_final_hold_required(self):
        _,_,_,rows = self.data()
        total = sum(r["duration_ticks"] for r in rows)
        probe = {"streams":[{"width":1280,"height":960,"time_base":"1/90000","nb_frames":len(rows),"duration_ts":total}],
            "frames":[{"best_effort_timestamp":r["review_pts_ticks"],"duration":r["duration_ticks"]} for r in rows]}
        self.assertEqual(render.verify_probe(probe,rows),total)
        probe["frames"][-1]["duration"] = 18000
        with self.assertRaisesRegex(ValueError,"timing"):
            render.verify_probe(probe,rows)
        with patch.object(render,"source_sheet",side_effect=RuntimeError("synthetic interruption")):
            with self.assertRaisesRegex(RuntimeError,"synthetic interruption"):
                render.build_source_sheets(self.root,self.preparation_path,"data/outputs/interrupted")
        attempts = list((self.root/"data/outputs/interrupted/attempts").iterdir())
        self.assertEqual(len(attempts),1)
        self.assertEqual(d.read_json(attempts[0]/"failed.json")["error"],"synthetic interruption")
        self.assertFalse((self.root/"data/outputs/interrupted/completion.json").exists())

    @unittest.skipUnless((FFBIN/"ffmpeg.exe").is_file(),"FFmpeg required")
    def test_complete_actual_encode_decodes_context_targets_final_and_reuses_exact_package(self):
        prep,proposal,groups,rows = self.data()
        args = self.root,self.preparation_path,self.proposal_path,"data/outputs/media",str(FFBIN/"ffmpeg.exe")
        result = render.render(*args)
        verification = d.read_json(self.root/result["artifacts"]["verification"]["path"])
        self.assertEqual((verification["decoded_frames"],verification["target_frames"],verification["new_review_rows"],verification["context_finals"]),(15,3,10,3))
        self.assertEqual(verification["duration_ticks"],864000)
        self.assertEqual(len(result["stills"]),6)
        self.assertTrue(verification["all_frame_keys_pixels_and_markers_verified"])
        guide = (self.root/result["artifacts"]["guide"]["path"]).read_text(encoding="utf-8")
        self.assertIn("Existing accepted26: grouping supplement only",guide)
        for row in proposal["rows"]:
            self.assertIn(row["row_id"],guide)
        final = rows[-1]
        canvas,markers = render.render_frame(render.source_image(self.root,final,final["source_frame"]),final,len(groups))
        with Image.open(self.root/result["artifacts"]["actual_final"]["path"]) as saved:
            render.verify_pixels(np.asarray(saved),canvas,markers,final)
        with patch.object(render,"source_image",side_effect=AssertionError("resume must not rerender")):
            self.assertEqual(render.render(*args),result)


if __name__ == "__main__":
    unittest.main()
