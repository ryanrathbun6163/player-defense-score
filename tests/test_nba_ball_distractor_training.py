"""Transport checks for the provisional fit, independent of optimizer fixtures."""
import copy
import unittest

import numpy as np

from src.ball_tracking import nba_appearance_feature_screen as screen
from src.ball_tracking import nba_ball_distractor_training as training


class TrainingTransportTests(unittest.TestCase):
    def test_raw_record_round_trip_and_tampering(self):
        raw = np.linspace(-2, 3, 384, dtype=np.float32)
        record = {"raw_cls_float32": raw.tolist(), "raw_cls_sha256": screen._hash_array(raw),
                  "normalized_float64_sha256": screen._hash_array(screen.normalize_feature(raw))}
        np.testing.assert_array_equal(training.validate_raw(record), raw)
        bad = copy.deepcopy(record); bad["raw_cls_float32"][0] += 1
        with self.assertRaises(ValueError):
            training.validate_raw(bad)
        bad = copy.deepcopy(record); bad["normalized_float64_sha256"] = "0"*64
        with self.assertRaises(ValueError):
            training.validate_raw(bad)

    def test_crop_identity_matches_real_preprocessor(self):
        from PIL import Image
        pixels = np.arange(90*100*3, dtype=np.uint8).reshape(90,100,3)
        image = Image.fromarray(pixels)
        for center in ([40.9,50.2],[-.2,80.9],[40.1,50.9]):
            key = training.crop_key("source",5,center)
            crop,_,_ = screen.crop_and_preprocess(image,center)
            self.assertEqual(crop.tobytes(), image.crop((key[2],key[3],key[2]+64,key[3]+64)).tobytes())
        self.assertEqual(training.crop_key("source",5,[40.9,50.2]),training.crop_key("source",5,[40.1,50.9]))

    def test_unknowns_never_become_correct_rejections_and_ties_fail(self):
        rows = [{"row_id": "unknown", "role":"check", "classification":"unresolved"},
                {"row_id":"ball", "role":"check", "classification":"ball"},
                {"row_id":"other", "role":"check", "classification":"other_object"}]
        report = training.reference_summary(rows,{"unknown":-2.,"ball":0.,"other":-1.})
        check = {r["classification"]:r for r in report if r["role"] == "check"}
        self.assertIsNone(check["unresolved"]["correct"])
        self.assertEqual(check["ball"]["correct"],0)
        self.assertEqual(check["ball"]["ties"],1)
        self.assertEqual(check["other_object"]["correct"],1)


if __name__ == "__main__":
    unittest.main()
