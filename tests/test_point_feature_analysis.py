"""Synthetic producer/consumer and independent arithmetic checks; no inference."""
from copy import deepcopy
from types import SimpleNamespace
import unittest

import numpy as np

from src.ball_tracking import candidate_response_analysis as response
from src.ball_tracking import point_feature_analysis as analysis
from src.ball_tracking import point_feature_inference as producer


def vector(x, y=0):
    result = np.zeros(384, dtype=np.float32)
    result[:2] = x, y
    return result


def candidate(index, cls, point, *, match=True, selected=False, padded=False, native=True):
    return {"id": index, "native": native, "mass": 2.0, "in_bounds": True,
            "match": match, "is_native_selected": selected,
            "geometry_status": "padded_source_crop" if padded else "complete_source_crop",
            "features": {"cls": cls, "point": point, "peak": .5}}


def frame(candidates, *, category="eligible", native_correct=False, index=1, stress=None):
    return {"block_id": "synthetic", "frame": index, "reference_category": category,
            "native_correct": native_correct, "native_outcome": "matched" if native_correct else "missing",
            "candidates": candidates, "stress": {"emitted": stress is not None,
                "geometry_status": "complete_source_crop" if stress is not None else "missing_selection",
                "features": {"cls": stress, "point": stress, "peak": stress}, "tags": ["gain"]}}


class PointAnalysisTests(unittest.TestCase):
    def test_actual_producer_witness_and_weighted_raw_tokens_before_normalization(self):
        seq = np.zeros((1, 257, 384), np.float32)
        seq[0, 0] = vector(3, 4)
        seq[0, producer.TOKEN_INDICES] = np.stack([vector(8), vector(0, 2), vector(4), vector(0, 6)])
        witness = producer.extract_witnesses(SimpleNamespace(last_hidden_state=seq, pooler_output=seq[:, 0]))
        queries = []
        for identity, weights in (("a", [.25, .25, .25, .25]), ("b", [0, 0, 0, 1])):
            queries.append({"query_id": identity, "input_id": "input", "geometry": {
                "status": "padded_source_crop", "tokens": [{"sequence_index": int(i), "weight": w}
                    for i, w in zip(producer.TOKEN_INDICES, weights)]}})
        item = {"input_id": "input", "query_ids": ["a", "b"]}
        record = {"status": "completed", "input": item, "same_pass_CLS_exact": True,
            "sequence_shape": [1, 257, 384], "sequence_indices": [120, 121, 136, 137],
            "CLS_float32_sha256": producer.sha(witness["cls"].tobytes()), "CLS_unknown_reason": None,
            "point_unknown_reasons": {}}
        result = analysis.reconstruct(record, item, queries, witness)
        np.testing.assert_allclose(result["a"]["cls"][:2], [.6, .8], atol=1e-15)
        np.testing.assert_allclose(result["a"]["point"][:2], [3/np.sqrt(13), 2/np.sqrt(13)], atol=1e-15)
        np.testing.assert_array_equal(result["b"]["point"][:2], [0, 1])
        self.assertNotEqual(result["a"]["point"][0], 1/np.sqrt(2))  # Per-token L2 would incorrectly yield this.
        wrong = deepcopy(queries); wrong[0]["geometry"]["tokens"][0]["sequence_index"] = 119
        with self.assertRaises(ValueError): analysis.reconstruct(record, item, wrong, witness)
        wrong = deepcopy(record); wrong["CLS_float32_sha256"] = "0"*64
        with self.assertRaises(ValueError): analysis.reconstruct(wrong, item, queries, witness)
        zero = deepcopy(witness); zero["tokens"][:] = 0
        unavailable = deepcopy(record); unavailable["point_unknown_reasons"] = {q["query_id"]: "zero_norm_descriptor" for q in queries}
        self.assertIsNone(analysis.reconstruct(unavailable, item, queries, zero)["a"]["point"])
        with self.assertRaises(ValueError): analysis.reconstruct(record, item, queries, zero)

    def test_cosine_margin_independent_known_vectors_and_unknown_bank(self):
        bank = {"b": vector(1).astype(float), "o": vector(0, 1).astype(float)}
        labels = {"b": "ball", "o": "other_object"}
        query = vector(3, 4).astype(float)/5
        result = analysis.cosine_margin(query, bank, labels)
        self.assertAlmostEqual(result["margin"], -.2)
        self.assertEqual(result["best_ball_ids"], ["b"])
        unknown = analysis.cosine_margin(query, {**bank, "o": None}, labels)
        self.assertIsNone(unknown["margin"])
        self.assertEqual(unknown["reason"], "bank_descriptor_unavailable")
        self.assertEqual(unknown["unknown_bank_ids"], ["o"])
        self.assertIsNone(analysis.cosine_margin(None, bank, labels, unknown_reason="zero_norm_descriptor")["margin"])

    def test_bank_excluded_and_representation_matched_unknown_propagation(self):
        queries = []
        for identity, label in (("b", "ball"), ("o", "other_object")):
            queries.append({"query_id": identity, "input_id": identity, "cohort": "historical", "block_id": "sac",
                "source_frame_index": 1, "source_role": "reference_bank", "geometry": {"status": "complete_source_crop"},
                "historical_case": {"original_source_role": "fit_eligible", "semantic_label_status": "human_accepted_assisted_appearance",
                                    "accepted_appearance": {"classification": label}}})
        queries.append({"query_id": "q", "input_id": "q", "cohort": "HOU_main", "block_id": "hou",
                        "source_frame_index": 2, "geometry": {"status": "padded_source_crop", "padded_native_pixels": 64}})
        vectors = {"b": {"cls": vector(1), "point": vector(0, 1)},
                   "o": {"cls": vector(0, 1), "point": None},
                   "q": {"cls": vector(1), "point": vector(0, 1), "unknown_reasons": {"cls": None, "point": None}}}
        rows = analysis.margins_for_queries(queries, vectors, ["b", "o"], {"b": "ball", "o": "other_object"})
        self.assertEqual(rows["b"]["readouts"]["cls"]["status"], "excluded_bank_query")
        self.assertEqual(rows["q"]["readouts"]["cls"]["margin"], 1)
        self.assertIsNone(rows["q"]["readouts"]["point"]["margin"])
        self.assertEqual(rows["q"]["geometry_status"], "padded_source_crop")

    def test_paired_rank_ties_unknowns_and_native_only_mass(self):
        f = frame([candidate(0, .4, .8, selected=True), candidate(1, .6, .8, match=False, native=False)])
        cls = response.rank_frame(f, "cls"); point = response.rank_frame(f, "point")
        self.assertEqual(point["status_among_available_features"], "tied_first")
        self.assertEqual(response.compare_ranks([point], [cls])["fewer_strictly_higher_misses"], 1)
        self.assertNotIn("strict_first_gain_over_baseline", response.compare_ranks([point], [cls]))
        self.assertEqual(response.rank_frame(f, "native_mass")["candidate_count"], 1)
        f["candidates"][1]["features"]["point"] = None
        self.assertEqual(response.compare_ranks([response.rank_frame(f, "point")], [cls]),
                         {"not_comparable_incomplete_features": 1})

    def test_global_bounds_and_padding_strata_keep_scores_and_unknowns(self):
        rows = [frame([candidate(0, .2, .2, selected=True)], native_correct=True, stress=.2),
                frame([candidate(0, .5, .5, selected=True, padded=True)], native_correct=True, index=2, stress=.5),
                frame([candidate(0, .2, .2, match=False, padded=True), candidate(1, None, None, match=False)], category="certain_hidden", index=3),
                frame([candidate(0, 999, 999, match=False)], category="uncertain_hidden", index=4)]
        shared = {n: response.thresholds(rows, n) for n in analysis.FEATURES}
        self.assertEqual(shared["point"]["maximum_observed_certain_hidden"], .2)
        self.assertEqual(shared["point"]["minimum_observed_native_correct"], .2)
        report = analysis.summarize(rows, shared)
        p = report["features"]["point"]
        self.assertEqual(p["reject_all_observed_hidden_bound"]["original_native_correct_points"], {"rejected": 1, "retained": 1})
        self.assertEqual(p["retain_all_observed_native_correct_bound"]["certain_hidden"]["candidates_unknown"], 1)
        padded = p["padding_strata"]["padded_source_crop"]["bounds"]
        self.assertEqual(padded["retain_all_observed_native_correct"]["counts"]["hidden_candidates:retained"], 1)
        self.assertEqual(padded["reject_all_observed_hidden"]["same_shared_HOU_cutoff"], .2)
        self.assertEqual(padded["retain_all_observed_native_correct"]["counts"]["native_correct:retained"], 1)

    def test_point_query_identity_transport_rejects_pts_and_candidate_changes(self):
        base = {"block_id": "synthetic", "source_frame_index": 1, "source_pts_ticks": 123,
                "time_base": "1/60000", "source_png": {"path": "image.png"},
                "native_selected_candidate_index": 0, "source_video": {"width_px": 1280, "height_px": 720},
                "source_role": "checkpoint_validation", "geometry": {"status": "complete_source_crop"}}
        cand = {"candidate_index": 0, "center_x": 30.5, "center_y": 20.5}
        observation = {"center_xy_px": [30.5, 20.5]}
        mq = {**deepcopy(base), "query_id": "main", "cohort": "HOU_main", "center_xy_px": [30.5, 20.5], "candidate": cand}
        sq = {**deepcopy(base), "query_id": "stress", "cohort": "HOU_stress", "center_xy_px": [30.5, 20.5], "observation": observation}
        source = {**base, "main_candidates": [{"candidate": cand}], "expanded_weak_selection": {"observation": observation}}
        score = {k: {"readouts": {n: {"margin": .3} for n in analysis.READOUTS}} for k in ("main", "stress")}
        f = frame([candidate(0, 0, 0, selected=True)], native_correct=True, stress=.5); f["_reference"] = [40.5, 20.5]
        result = analysis.add_margins(deepcopy(f), source, [mq], sq, score, {"source_video": base["source_video"]})
        self.assertEqual(result["candidates"][0]["localization_distance_px"], 10)
        changed = deepcopy(mq); changed["source_pts_ticks"] += 1
        with self.assertRaises(ValueError): analysis.add_margins(deepcopy(f), source, [changed], sq, score, {"source_video": base["source_video"]})
        changed = deepcopy(mq); changed["candidate"]["center_x"] += 1
        with self.assertRaises(ValueError): analysis.add_margins(deepcopy(f), source, [changed], sq, score, {"source_video": base["source_video"]})

    def test_historical_roles_and_same_frame_pairs_do_not_promote_AI_labels(self):
        queries, scores = [], {}
        for identity, role, accepted, ai, margin in (("b", "resolved_check", "ball", None, -.2),
                ("o", "resolved_check", "other_object", None, -.3), ("a", "exposed_regression", None, "ball", -.4),
                ("bank", "reference_bank", "ball", None, None)):
            case = {"semantic_label_status": "human_accepted_assisted_appearance" if accepted else "prior_AI_only"}
            if accepted: case["accepted_appearance"] = {"classification": accepted}
            if ai: case["prior_ai_assessment"] = {"assessment": ai}
            queries.append({"query_id": identity, "cohort": "historical", "source_id": "source", "source_frame_index": 1,
                            "source_role": role, "historical_case": case})
            scores[identity] = {"query_id": identity, "readouts": {n: {"margin": margin} for n in analysis.READOUTS}}
        result = analysis.historical_summary(queries, scores, {"queries": []})
        self.assertEqual(result["roles"]["reference_bank"]["readouts"]["cls"], {"excluded_bank_query": 1})
        self.assertEqual(result["roles"]["resolved_check"]["readouts"]["cls"], {"other_class_preferred": 1, "accepted_class_preferred": 1})
        self.assertFalse(result["roles"]["exposed_regression"]["semantic_accuracy_claim"])
        self.assertEqual(len(result["accepted_same_frame_pairs"]), 1)
        self.assertEqual(result["accepted_same_frame_pairs"][0]["readouts"]["point"]["ordering"], "ball_above")


if __name__ == "__main__":
    unittest.main()
