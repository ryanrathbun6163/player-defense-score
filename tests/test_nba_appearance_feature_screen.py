"""Fixed-screen math plus actual captured registry and emitted-cache transport."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

import numpy as np
from PIL import Image

from src.ball_tracking import nba_appearance_feature_screen as screen
from src.ball_tracking import nba_appearance_feature_screen_review as review
from src.ball_tracking import nba_wasb_diagnostic as d

REPOSITORY = Path(__file__).resolve().parents[1]
CAPTURE = REPOSITORY/"data/outputs/ball_tracking/nba/appearance_reference_v0_1/feature_screen_scope.json"
HAS_CAPTURE = CAPTURE.is_file()


def captured_items():
    return d.read_json(CAPTURE)["items"]


def vector(label):
    value=np.zeros(384,np.float32);value[0 if label=="ball" else 1]=1
    return value


class StubModel:
    """No pretrained model; deterministic two-coordinate synthetic descriptor."""
    def __init__(self,fail_on=None):self.calls=0;self.fail_on=fail_on
    def __call__(self,pixel_values,return_dict):
        import torch
        self.calls+=1
        if self.calls==self.fail_on:raise RuntimeError("synthetic model interruption")
        assert return_dict and torch.is_inference_mode_enabled()
        result=vector("ball" if float(pixel_values[0,0].mean())>0 else "other_object")
        return SimpleNamespace(pooler_output=torch.from_numpy(result[None,:]),last_hidden_state=torch.zeros((1,257,384)))


def tiny_emitted_fixture():
    root=REPOSITORY/"data/outputs/t/appearance_feature_screen_tests"/uuid.uuid4().hex
    root.mkdir(parents=True)
    source=captured_items()
    selected=[next(r for r in source if r["screen_role"]=="reference_bank" and r["accepted_appearance"]["classification"]==label) for label in ("ball","other_object")]
    selected += [next(r for r in source if r["screen_role"]==role) for role in ("resolved_check","unresolved_audit","exposed_regression")]
    items=copy.deepcopy(selected)
    for i,item in enumerate(items):
        # Retain captured case IDs, source dimensions, saved points, native PTS,
        # labels and provenance. Only pixel authority is an explicit synthetic PNG.
        label=item.get("accepted_appearance",{}).get("classification")
        image=Image.new("RGB",(item["source_video"]["width_px"],item["source_video"]["height_px"]),(220,30,80) if label=="ball" else (20,160,80))
        path=root/f"data/outputs/source_{i}.png";path.parent.mkdir(parents=True,exist_ok=True);image.save(path)
        item["raw_png"]={**d.binding(root,path),"rgb_sha256":hashlib.sha256(image.tobytes()).hexdigest()}
    for name in ("approval.json","config.json","weights.stub"):(root/name).write_text("{}",encoding="utf-8")
    for name in ("nba_appearance_feature_screen_review.py","nba_action_review.py"):
        dest=root/"src/ball_tracking"/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((REPOSITORY/"src/ball_tracking"/name).read_bytes())
    protocol={"fixture_only":True,"output_root":"data/outputs/screen","source_pngs":[r["raw_png"] for r in items],
              "config":d.binding(root,root/"config.json"),"weights":d.binding(root,root/"weights.stub")}
    return root,protocol,items


class AppearanceFeatureScreenTests(unittest.TestCase):
    def test_crop_floor_black_padding_and_normalization_known_pixels(self):
        image=Image.new("RGB",(96,96),(255,128,0))
        native,model,pixels=screen.crop_and_preprocess(image,[48.999,48.001])
        self.assertEqual((native.size,model.size,pixels.shape,pixels.dtype),((64,64),(224,224),(3,224,224),np.dtype("float32")))
        expected=(np.array([1,128/255,0],np.float32)-np.array([.485,.456,.406],np.float32))/np.array([.229,.224,.225],np.float32)
        np.testing.assert_array_equal(pixels[:,100,100],expected)
        small=Image.new("RGB",(4,3),(9,17,33))
        edge,_,_=screen.crop_and_preprocess(small,[0.9,0.9])
        self.assertEqual(edge.getpixel((31,32)),(0,0,0));self.assertEqual(edge.getpixel((32,32)),(9,17,33))
        self.assertEqual(edge.getpixel((35,34)),(9,17,33));self.assertEqual(edge.getpixel((36,34)),(0,0,0))
        ramp=np.zeros((96,96,3),np.uint8);ramp[:,:,0]=np.arange(96,dtype=np.uint8)
        native,model,_=screen.crop_and_preprocess(Image.fromarray(ramp),[48.99,48.1])
        self.assertEqual(native.getpixel((0,0))[0],16);self.assertEqual(native.getpixel((63,63))[0],79)
        independently=Image.fromarray(ramp).crop((16,16,80,80)).resize((256,256),Image.Resampling.BICUBIC).crop((16,16,240,240))
        self.assertEqual(model.tobytes(),independently.tobytes())

    def test_cls_is_pooler_only_and_float64_norm_rejects_invalid(self):
        raw=np.arange(1,385,dtype=np.float32)
        extracted=screen.extract_cls(SimpleNamespace(pooler_output=raw[None,:],last_hidden_state=np.full((1,257,384),999,np.float32)))
        np.testing.assert_array_equal(extracted,raw)
        normalized=screen.normalize_feature(raw)
        self.assertEqual(normalized.dtype,np.float64)
        np.testing.assert_array_equal(normalized,raw.astype(np.float64)/np.linalg.norm(raw.astype(np.float64)))
        for bad in (np.zeros(384,np.float32),np.full(384,np.nan),np.full(384,np.inf),np.ones(383)):
            with self.subTest(shape=bad.shape),self.assertRaises(ValueError):screen.normalize_feature(bad)
        for output in (SimpleNamespace(last_hidden_state=raw),SimpleNamespace(pooler_output=raw[None,:].astype(np.float64)),SimpleNamespace(pooler_output=raw)):
            with self.assertRaises(ValueError):screen.extract_cls(output)

    @unittest.skipUnless(HAS_CAPTURE,"Authorized local captured registry required")
    def test_actual_captured_registry_source_and_provenance_authority(self):
        registry=d.read_json(CAPTURE)
        proposal=d.read_json(REPOSITORY/"configs/ball_tracking/proposals/nba_appearance_feature_screen_v0_1.json")
        accepted=d.read_json(REPOSITORY/proposal["accepted_reference"]["path"])
        result=screen.validate_registry(REPOSITORY,registry,proposal,accepted)
        self.assertEqual(result,registry["items"]);self.assertEqual(len(result),60)
        self.assertEqual(len({(r["continuous_source_id"],r["source_frame_index"]) for r in result}),49)
        old=[r for r in result if r["screen_role"]=="exposed_regression"]
        self.assertEqual(sum(r["saved_provenance_id"][3]=="contributor" for r in old),14)
        for field in ("saved_center_xy_px","saved_provenance_id","source_pts_ticks"):
            changed=copy.deepcopy(registry);row=changed["items"][26]
            if field=="saved_center_xy_px":row[field][0]+=.1
            elif field=="saved_provenance_id":row[field][3]="changed"
            else:row[field]+=1
            with self.subTest(field=field),self.assertRaises(ValueError):screen.validate_registry(REPOSITORY,changed,proposal,accepted)

    @unittest.skipUnless(HAS_CAPTURE,"Authorized local captured registry required")
    def test_all_class_max_ties_gates_and_unknowns_on_captured_inventory(self):
        items=captured_items();features={}
        for row in items:
            label=row.get("accepted_appearance",{}).get("classification",row.get("prior_ai_assessment",{}).get("assessment"))
            features[row["case_id"]]=vector(label)
        report=screen.retrieve(features,items);summary=report["summary"]
        self.assertEqual((len(report["queries"]),summary["similarity_count"]),(50,500))
        self.assertEqual(summary["accepted_checks"]["correct"],10);self.assertTrue(summary["main_gate"]["passed"])
        self.assertEqual(summary["unknowns_unscored"],6);self.assertTrue(summary["clean_screen"])
        self.assertEqual(summary["qualitative_regression"]["unresolved_unscored"],8)
        for query in report["queries"]:
            self.assertEqual(len(query["nearest_ball_case_ids"]),4);self.assertEqual(len(query["nearest_other_case_ids"]),6)
            if query["screen_role"]!="resolved_check":self.assertIsNone(query["accepted_check_outcome"])
        check=next(r for r in items if r["screen_role"]=="resolved_check" and r["accepted_appearance"]["classification"]=="ball")
        features[check["case_id"]]=vector("other_object")
        failed=screen.retrieve(features,items);self.assertFalse(failed["summary"]["main_gate"]["passed"])
        self.assertEqual(failed["summary"]["accepted_checks"]["incorrect"],1)
        features[check["case_id"]]=vector("ball")+vector("other_object")
        tied=screen.retrieve(features,items);self.assertEqual(tied["summary"]["accepted_checks"]["ties"],1)
        self.assertFalse(tied["summary"]["main_gate"]["passed"])
        features[check["case_id"]]=vector("ball")
        head=next(r for r in items if r["screen_role"]=="exposed_regression" and r["source_frame_index"]==1420)
        features[head["case_id"]]=vector("ball")
        adverse=screen.retrieve(features,items)
        self.assertTrue(adverse["summary"]["main_gate"]["passed"]);self.assertFalse(adverse["summary"]["clean_screen"])
        self.assertEqual(adverse["summary"]["challenges"]["sac_wrong_head"]["adverse_case_ids"],[head["case_id"]])

    @unittest.skipUnless(HAS_CAPTURE,"Authorized local captured registry required")
    def test_real_cache_emitter_failure_resume_and_tamper_without_real_model(self):
        root,protocol,items=tiny_emitted_fixture();args=(root,"approval.json","data/outputs/screen","weights.stub")
        failed_model=StubModel(fail_on=3)
        with patch.object(screen,"load_inputs",return_value=(protocol,items)),patch.object(screen,"load_model",return_value=failed_model):
            with self.assertRaisesRegex(RuntimeError,"synthetic model interruption"):screen.run(*args)
        failure=list((root/"data/outputs/screen/attempts").glob("*/failed.json"))
        self.assertEqual(len(failure),1);self.assertEqual(d.read_json(failure[0])["resources"]["model_calls"],3)
        resumed=StubModel()
        with patch.object(screen,"load_inputs",return_value=(protocol,items)),patch.object(screen,"load_model",return_value=resumed):completion=screen.run(*args)
        self.assertEqual(resumed.calls,3);self.assertEqual(completion["resources"]["cached_features_reused"],2)
        with patch.object(screen,"load_inputs",return_value=(protocol,items)),patch.object(screen,"load_model",side_effect=AssertionError("no reload")):
            self.assertEqual(screen.run(*args),completion)
        first=root/completion["features"][0]["feature"]["path"];data=d.read_json(first);data["raw_cls_float32"][0]+=.125
        first.write_text(json.dumps(data),encoding="utf-8")
        with patch.object(screen,"load_inputs",return_value=(protocol,items)),patch.object(screen,"load_model",side_effect=AssertionError("no reload")):
            with self.assertRaisesRegex(ValueError,"descriptor"):screen.run(*args)
        self.assertFalse((root/"data/outputs/screen/.run.lock").exists())

    @unittest.skipUnless(HAS_CAPTURE,"Authorized local captured registry required")
    def test_review_consumes_actual_emitted_records_all_queries_pixels_and_resume(self):
        root,protocol,items=tiny_emitted_fixture()
        with patch.object(screen,"load_inputs",return_value=(protocol,items)),patch.object(screen,"load_model",return_value=StubModel()):
            completion=screen.run(root,"approval.json","data/outputs/screen","weights.stub")
        result=review.build_review(root,"data/outputs/screen/completion.json","data/outputs/review")
        self.assertEqual(result["query_count"],3);self.assertEqual(len(result["sheets"]),1)
        manifest=d.read_json(root/result["artifacts"]["manifest"]["path"])
        self.assertEqual(manifest["actual_final_case_id"],items[-1]["case_id"])
        sheet_path=root/result["sheets"][0]["image"]["path"]
        with Image.open(sheet_path) as sheet:
            for i,entry in enumerate(completion["features"][2:]):
                with Image.open(root/entry["crop64"]["path"]) as crop:
                    expected=crop.resize((224,224),Image.Resampling.NEAREST)
                actual=sheet.crop((30,130+340*i+66,254,130+340*i+290))
                self.assertEqual(actual.tobytes(),expected.tobytes())
        guide=(root/result["artifacts"]["guide"]["path"]).read_text(encoding="utf-8")
        self.assertIn("Prior AI disagreement",guide);self.assertIn("not newly accepted classification truth",guide)
        with patch.object(review,"row_image",side_effect=AssertionError("no rerender")):
            self.assertEqual(review.build_review(root,"data/outputs/screen/completion.json","data/outputs/review"),result)
        sheet_path.write_bytes(sheet_path.read_bytes()+b"tamper")
        with self.assertRaisesRegex(ValueError,"Bound file changed"):
            review.build_review(root,"data/outputs/screen/completion.json","data/outputs/review")


if __name__=="__main__":unittest.main()
