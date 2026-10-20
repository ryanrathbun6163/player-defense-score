"""Producer-derived transport, pruning, label boundary and recovery checks."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from src.ball_tracking import nba_temporal_gap_continuous as continuous
from src.ball_tracking import nba_temporal_gap_selection as selector
from src.ball_tracking import nba_temporal_gap_continuous_review as review
from src.ball_tracking import nba_action_observation as action
from src.ball_tracking import nba_wasb_diagnostic as d
from src.ball_tracking import wasb_development_observation as nfhs
from tests.test_nba_hard_example_diagnostic import label
from tests.test_nba_temporal_gap_selection import geometry


def produced_context(root, count=14):
    """Raw maps produce real streamed means, actual components and saved rows."""
    source_video = {"path": "source.mp4", "sha256": "a" * 64, "width_px": 512, "height_px": 288, "frame_count": count}
    ticks = [0]
    for i in range(count): ticks.append(ticks[-1] + (1530 if i % 2 == 0 else 1440))
    frames = [{"source_frame_index": i, "source_pts_ticks": ticks[i], "png": {"path": f"fixture_{i}.png"}}
              for i in range(count)]
    manifest = {"candidate_id": "synthetic", "source_video": source_video, "time_base": "1/90000", "frames": frames,
                "source_end_exclusive_pts_ticks": ticks[-1]}
    arrays = {i: np.zeros((3, 288, 512), np.float32) for i in range(count - 2)}
    anchors = {1: [50, 50], 3: [52, 50], count - 2: [61, 50]}
    for index in range(count):
        starts = continuous.saved.needed_starts([index], [0, count - 1])
        point = anchors.get(index, [49 + index, 50])
        for start in starts:
            if index in anchors or start == starts[0]:
                arrays[start][index - start, point[1], point[0]] = .8 if index in anchors else .6
    observations = [action.select_observation(frame,
        continuous.metrics.reconstruct_mean([(s, arrays[s][frame["source_frame_index"] - s])
            for s in continuous.saved.needed_starts([frame["source_frame_index"]], [0, count - 1])]),
        len(continuous.saved.needed_starts([frame["source_frame_index"]], [0, count - 1])), manifest,
        {"kind": "development", "source_frame_range_inclusive": [0, count - 1]}) for frame in frames]
    # The first/last complete-triplet-only frame can emit .6; make them genuine edge gaps.
    for index in (0, count - 1):
        for start in continuous.saved.needed_starts([index], [0, count - 1]): arrays[start][index-start].fill(0)
        observations[index] = action.select_observation(frames[index], np.zeros((288, 512), np.float32), 1, manifest,
            {"kind": "development", "source_frame_range_inclusive": [0, count - 1]})
    d.write_once(root / "manifest.json", manifest)
    manifest_binding = d.binding(root, root / "manifest.json")
    records = [{"first_source_frame_index": i, "cache": {"path": f"triplet_{i}.npz"}} for i in arrays]
    producer = {"candidate_id": "synthetic", "input_manifest": manifest_binding, "checkpoint": {"sha256": d.EXPANDED_SHA},
                "inference": d.POLICY, "frames": observations, "triplet_caches": records}
    d.write_once(root / "observations.json", producer)
    segment = {"segment_id": "synthetic:0-13", "range_inclusive": [0, count-1],
               "observations": d.binding(root, root / "observations.json")}
    source = {"candidate_id": "synthetic", "kind": "nba", "analysis_group": "sac_training_fit",
              "source_video": source_video, "source_manifest": manifest_binding, "protected_ranges": [],
              "source_end_exclusive_pts_ticks": ticks[-1], "segments": [segment]}
    context = continuous.load_segment(root, source, segment)
    reads = []
    def cache_reader(_root, _context, start):
        reads.append(start)
        return arrays[start], {"start": start, "cache": {"path": f"fixture_triplet_{start}"}}
    return context, arrays, reads, cache_reader


def resources():
    return {"cache_reads": [], "peak_triplet_arrays": 0}


class ContinuousGapTests(unittest.TestCase):
    def test_actual_producer_loader_and_component_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); context, _, _, _ = produced_context(root)
            self.assertEqual(len(context["observations"]), 14)
            row = context["observations"][2]
            bad = copy.deepcopy(row); bad["temporal_contributions"] = 1
            with self.assertRaisesRegex(ValueError, "contributor context"):
                continuous.normalize_observation(bad, context["frames"][2], [0, 13], "nba")
            bad = copy.deepcopy(context["observations"][1]); bad["native_score"] += 1
            with self.assertRaisesRegex(ValueError, "selected-component"):
                continuous.normalize_observation(bad, context["frames"][1], [0, 13], "nba")

    def test_pruned_reads_and_frozen_selector_equal_full_contributor_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); context, _, reads, provider = produced_context(root)
            pruned = continuous.select_segment(root, context, resources(), cache_reader=provider)
            self.assertEqual(reads, [0, 1, 2])
            reads.clear()
            full = continuous.select_segment(root, context, resources(), cache_reader=provider, prune=False)
            self.assertEqual(reads, list(range(12)))
            self.assertEqual(pruned["gaps"], full["gaps"])
            for before, after in zip(pruned["frames"], full["frames"]):
                for key in ("decision", "selected_center_xy_px", "reason", "selected_provenance_id", "selected_component"):
                    self.assertEqual(before[key], after[key])
            self.assertEqual(pruned["frames"][2]["decision"], "filled_saved_candidate")
            self.assertEqual(pruned["frames"][2]["selected_center_xy_px"], [51.0, 50.0])
            self.assertEqual(pruned["frames"][2]["selected_provenance_id"], ["old", "synthetic", 2, "contributor", 0, 2, 0])

    def test_pruning_inclusive_native_boundary_edges_speed_and_invalid_anchors(self):
        rows = [geometry(1, 0, [100, 100]), geometry(2, 3600, None), geometry(3, 7200, None), geometry(4, 10800, [160, 100])]
        self.assertEqual(continuous.potentially_fillable_indices(rows), {2, 3})
        changed = copy.deepcopy(rows); changed[-1]["source_pts_ticks"] = 10801
        self.assertEqual(continuous.potentially_fillable_indices(changed), set())
        changed = copy.deepcopy(rows); changed[-1]["baseline_center_xy_px"] = [160.00001, 100]
        self.assertEqual(continuous.potentially_fillable_indices(changed), set())
        changed = copy.deepcopy(rows); changed[0]["baseline_center_xy_px"] = [-1, 100]
        self.assertEqual(continuous.potentially_fillable_indices(changed), set())
        self.assertEqual(continuous.potentially_fillable_indices(rows[1:]), set())
        self.assertEqual(continuous.potentially_fillable_indices(rows[:-1]), set())

    def test_missing_cache_fails_without_fallback_or_model(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); context, _, _, _ = produced_context(root)
            with self.assertRaisesRegex(ValueError, "corrupt completed cache"):
                continuous.select_segment(root, context, resources(),
                    cache_reader=lambda *args: (_ for _ in ()).throw(ValueError("corrupt completed cache")))

    def test_emitted_source_passes_actual_renderer_consumer(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); context, _, _, provider = produced_context(root)
            segment = continuous.select_segment(root, context, resources(), cache_reader=provider)
            emitted = {**context["source"], "segments": [segment], "frames": segment["frames"]}
            timeline = review.validate_source(root, emitted)
            self.assertEqual(len(timeline), 14)
            self.assertEqual(timeline[2]["decision"], "filled_saved_candidate")
            self.assertEqual(timeline[-1]["source_pts_ticks"], context["frames"][-1]["source_pts_ticks"])

    def test_nfhs_actual_producer_size_bytes_and_per_cache_identity_transport(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = {"path": "source.mp4", "sha256": "a"*64, "width_px": 512, "height_px": 288}
            identity = {"weights": {"sha256": d.EXPANDED_SHA}, "source_video": source,
                        "segment": [10, 12], "inference": {"heatmap_threshold": .3}}
            d.write_once(root / "inference_identity.json", identity)
            (root / "triplet_000010.npz").write_bytes(b"producer-fixture")
            d.write_once(root / "triplet_000010.json", {"fixture": True})
            record = {"input_frame_indices": [10, 11, 12], "cache": nfhs.binding(root, root / "triplet_000010.npz"),
                "receipt": nfhs.binding(root, root / "triplet_000010.json"), "original_identity": nfhs.binding(root, root / "inference_identity.json"),
                "origin": "observation_cache"}
            context = {"cache_records": {10: record}, "source": {"kind": "nfhs", "source_video": source}, "manifest": {},
                       "producer": {"identity": identity}, "segment": {"range_inclusive": [10, 12]}}
            with patch.object(continuous.saved, "load_cache", return_value=("values", {"format": "nfhs_original"})) as loader:
                values, provenance = continuous.read_contributor(root, context, 10)
            descriptor = loader.call_args.args[1]
            self.assertEqual(descriptor["cache"], d.binding(root, root / "triplet_000010.npz"))
            self.assertEqual(loader.call_args.kwargs["nfhs_identity"]["inference"]["heatmap_threshold"], .3)
            self.assertEqual(provenance["original_producer_record"], record)
            self.assertEqual(values, "values")

    def test_nfhs_native_origin_protected_band_and_actual_timeline_consumer(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "source.mp4").write_bytes(b"synthetic-source-binding-only")
            source_binding = d.binding(root, root / "source.mp4")
            video = {"path": "source.mp4", "sha256": source_binding["sha256"], "width_px": 512, "height_px": 288,
                     "fps": 25.0, "frame_count": 7}
            possession = {"possession_id": "synthetic_nfhs", "source_video": video,
                          "visible_segments": [[0, 2], [4, 6]], "protected_ranges": [[3, 3]]}
            identity = {"weights": {"sha256": d.EXPANDED_SHA}, "source_video": video}
            produced = []
            source_segments = []
            for lo, hi in possession["visible_segments"]:
                means = np.zeros((3, 288, 512), np.float32)
                result = {"segment": [lo, hi], "identity": identity,
                    "frames": nfhs.observed_frames(means, [1, 1, 1], lo, video, .3),
                    "triplets": [{"input_frame_indices": [lo, lo+1, hi], "cache": {"path": "never-opened.npz"}}]}
                produced.append(result)
                path = root / f"segment_{lo}.json"; d.write_once(path, result)
                source_segments.append({"segment_id": f"synthetic_nfhs:{lo}-{hi}", "range_inclusive": [lo, hi],
                                        "observations": d.binding(root, path)})
            timeline = {"source_video": video, "protected_ranges": [[3, 3]],
                        "frames": nfhs.make_timeline(possession, produced, [])}
            d.write_once(root / "timeline.json", timeline)
            probe = {"streams": [{"width": 512, "height": 288, "nb_frames": "7", "time_base": "1/12800"}],
                     "packets": [{"pts": (i+1)*512, "duration": 512} for i in range(7)]}
            d.write_once(root / "packets.json", probe)
            timing = {"schema_version": "nfhs_container_native_timestamps/v0.1", "status": "verified",
                      "candidate_id": "synthetic_nfhs", "actual_source_binding": source_binding,
                      "packet_probe": d.binding(root, root / "packets.json"), "original_time_base": "1/12800",
                      "source_end_exclusive_pts_ticks": 7*3600, "container_end_exclusive_pts_ticks": 8*3600,
                      "time_base": "1/90000", "time_origin": "clip_first_frame", "source_video": video,
                      "container_time_origin_ticks": 3600, "frames": [
                        {"source_frame_index": i, "source_pts_ticks": i*3600, "container_pts_ticks": (i+1)*3600, "duration_ticks": 3600}
                        for i in range(7)]}
            d.write_once(root / "timing.json", timing)
            source = {"candidate_id": "synthetic_nfhs", "kind": "nfhs", "source_video": video, "possession": possession,
                      "analysis_group": "nfhs_development", "source_end_exclusive_pts_ticks": 7*3600,
                      "protected_ranges": [[3, 3]], "segments": source_segments,
                      "timeline_observations": d.binding(root, root / "timeline.json"),
                      "native_timestamps": d.binding(root, root / "timing.json")}
            scope = {"sources": [source], "totals": {"processed_frames": 6, "segments": 2, "timeline_frames": 7}}
            accounting = resources()
            selection = continuous.select_sources(root, scope, accounting)
            self.assertEqual(accounting["cache_reads"], [])
            self.assertEqual(len(selection["frames"]), 6)
            emitted = selection["sources"][0]
            rendered_timeline = review.validate_source(root, emitted)
            self.assertTrue(rendered_timeline[3]["source_pixels_withheld"])
            self.assertEqual(emitted["frames"][0]["source_pts_ticks"], 0)
            self.assertEqual(emitted["frames"][0]["container_pts_ticks"], 3600)
            self.assertEqual(emitted["frames"][3]["container_pts_ticks"], 14400)
            # All missing runs stop at their permitted segment edge, never bridge the protected slot.
            self.assertEqual([s["gaps"][0]["reason"] for s in emitted["segments"]], ["window_edge_gap"]*2)

    def test_actual_emitted_nfhs_cache_loads_without_receipt_repair(self):
        for threshold in (.3,):
            with self.subTest(threshold=threshold), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                video = {"path": "source.mp4", "sha256": "a"*64, "width_px": 512, "height_px": 288}
                identity = {"weights": {"sha256": d.EXPANDED_SHA}, "source_video": video,
                            "segment": [10, 12], "inference": {"heatmap_threshold": threshold}}
                d.write_once(root / "inference_identity.json", identity)
                values = np.zeros((3, 288, 512), np.float32)
                metadata = {"input_frame_indices": [10, 11, 12], "output_frame_indices": [10, 11, 12],
                    "inference_seconds": .01, "inference_identity_sha256": nfhs.canonical(identity),
                    "transform": nfhs.transform_metadata(512, 288), "cuda_peak_allocated_bytes": 0}
                cache, receipt = root / "triplet_000010.npz", root / "triplet_000010.json"
                nfhs.write_npz_once(cache, heatmaps=values, metadata_json=np.array(json.dumps(metadata, sort_keys=True)))
                _, emitted = nfhs.read_bound_triplet(root, cache, receipt, 10, identity, video)
                record = {**emitted, "input_frame_indices": [10, 11, 12], "origin": "observation_cache",
                          "original_identity": nfhs.binding(root, root / "inference_identity.json")}
                before = receipt.read_bytes()
                context = {"source": {"kind": "nfhs", "source_video": video}, "manifest": {}, "cache_records": {10: record},
                           "producer": {"identity": identity}, "segment": {"range_inclusive": [10, 12]}}
                actual, provenance = continuous.read_contributor(root, context, 10)
                self.assertTrue(np.array_equal(actual, values))
                self.assertEqual(provenance["historical_producer_threshold"], threshold)
                self.assertEqual(receipt.read_bytes(), before)
                receipt.unlink()
                with self.assertRaises((ValueError, FileNotFoundError)):
                    continuous.read_contributor(root, context, 10)
                self.assertFalse(receipt.exists())

    def test_imported_nfhs_model_only_identity_joins_the_actual_producer_window(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            video = {"path": "source.mp4", "sha256": "a"*64, "width_px": 512, "height_px": 288,
                     "fps": 25.0, "frame_count": 25}
            possession = {"possession_id": "synthetic_nfhs", "source_video": video, "visible_segments": [[0, 24]]}
            window = {"window_id": "original_window", "possession_id": "synthetic_nfhs", "source_video": video,
                      "start_frame_index": 10, "end_frame_index": 12}
            old = {"checkpoint": {"path": "weights.pth", "sha256": d.EXPANDED_SHA},
                   "training_completion": {"path": "training.json", "sha256": "b"*64}, "upstream_commit": "synthetic",
                   "output_root": "data/outputs/prior", "windows": [window], "inference": nfhs.OLD_POLICY}
            model = nfhs.model_identity(old, {"python": "synthetic"})
            # This is the actual original producer's model-only identity shape.
            identity = {**model, "experiment_config_sha256": nfhs.canonical(old), "inference": nfhs.OLD_POLICY}
            self.assertNotIn("source_video", identity)
            folder_path = root / old["output_root"] / window["window_id"]
            d.write_once(folder_path / "inference_identity.json", identity)
            d.write_once(root / "old_experiment.json", old)
            config = {"possessions": [possession], "cached_experiment": nfhs.binding(root, root / "old_experiment.json")}
            d.write_once(root / continuous.NFHS_CONFIG, config)
            values = np.zeros((3, 288, 512), np.float32)
            metadata = {"input_frame_indices": [10, 11, 12], "output_frame_indices": [10, 11, 12],
                "inference_seconds": .01, "inference_identity_sha256": nfhs.canonical(identity),
                "transform": nfhs.transform_metadata(512, 288), "cuda_peak_allocated_bytes": 0}
            cache, receipt = folder_path / "triplet_000010.npz", folder_path / "triplet_000010.json"
            nfhs.write_npz_once(cache, heatmaps=values, metadata_json=np.array(json.dumps(metadata, sort_keys=True)))
            _, emitted = nfhs.read_bound_triplet(root, cache, receipt, 10, identity, video)
            # Derive the import via cache_index, the same code that produced real records.
            plan = nfhs.cache_index(root, config, old, model)["synthetic_nfhs", 10]
            record = {**emitted, "input_frame_indices": [10, 11, 12], "origin": "prior_development_cache",
                      "original_identity": plan["identity_binding"]}
            context = {"source": {"kind": "nfhs", "candidate_id": "synthetic_nfhs", "source_video": video,
                                   "possession": possession}, "manifest": {}, "cache_records": {10: record},
                       "producer": {"identity": {**model, "source_video": video, "segment": [0, 24], "inference": nfhs.POLICY}},
                       "segment": {"range_inclusive": [0, 24]}}
            actual, provenance = continuous.read_contributor(root, context, 10)
            self.assertTrue(np.array_equal(actual, values))
            self.assertEqual(provenance["historical_producer_threshold"], .5)
            self.assertEqual(provenance["original_source_authority"]["window_id"], "original_window")
            changed = copy.deepcopy(context); changed["source"]["source_video"]["sha256"] = "wrong"
            with self.assertRaisesRegex(ValueError, "source/window/protected-boundary"):
                continuous.read_contributor(root, changed, 10)
            changed = copy.deepcopy(context); changed["source"]["possession"]["visible_segments"] = [[0, 11]]
            with self.assertRaisesRegex(ValueError, "source/window/protected-boundary"):
                continuous.read_contributor(root, changed, 10)

    def test_labels_not_opened_without_persisted_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(continuous.saved, "read_bound") as reader:
                with self.assertRaises(FileNotFoundError):
                    continuous.score_saved_selection(root, {}, {}, {"path": "missing_selection.json", "sha256": "none", "bytes": 0})
                reader.assert_not_called()

    def test_resume_requires_the_original_pre_scoring_receipt_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); output = root / "data/outputs/synthetic"
            path = output / "attempts/original/selection.json"
            bindings = {"scope": {"sha256": "scope"}, "selector": {"sha256": "frozen"}}
            selection = {"schema_version": continuous.SCHEMA, "policy": selector.POLICY,
                         "bindings": bindings, "labels_used": False, "frames": [{"selected_center_xy_px": [1, 2]}]}
            d.write_once(path, selection)
            original = d.binding(root, path)
            d.write_once(path.with_name("selection_ready.json"), {"selection": original, "bindings": bindings, "labels_loaded": False})
            loaded, binding = continuous.load_resumable_selection(root, output, original["path"], bindings)
            self.assertEqual(loaded, selection); self.assertEqual(binding, original)
            # A newly computed hash must not bless accidental edits made after scoring.
            changed = copy.deepcopy(selection); changed["frames"][0]["selected_center_xy_px"] = [99, 99]
            path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "pre-scoring receipt"):
                continuous.load_resumable_selection(root, output, original["path"], bindings)

    def test_saved_selection_is_checked_before_label_load_and_scores_producer_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); context, _, _, provider = produced_context(root)
            segment = continuous.select_segment(root, context, resources(), cache_reader=provider)
            chosen = [segment["frames"][i] for i in (1, 2, 3)]
            prior_rows = []
            for decision in chosen:
                annotation = label(decision["source_frame_index"], (49+decision["source_frame_index"], 50))
                row = {"window_id": "short-window", "candidate_id": "synthetic", "source_frame_index": decision["source_frame_index"],
                    "source_frame": decision["source_frame"], "source_video": decision["source_video"], "analysis_group": "sac_training_fit",
                    "cohort": "synthetic", "is_control": False, "annotation": annotation, "eligibility": "eligible", "decision": decision,
                    "old": {"pool": {"contributor_planes": [None]*decision["original_observation"]["temporal_contributions"]}}}
                row["baseline"] = selector.score_point(row, decision["baseline_center_xy_px"], decision["original_observation"]["candidates"])
                row["selected"] = selector.score_point(row, decision["selected_center_xy_px"], [r["component"] for r in decision["candidate_pool"]["records"]])
                row["changed"] = decision["decision"] == "filled_saved_candidate"
                prior_rows.append(row)
            d.write_once(root / "prior.json", {"status": "completed", "frames": prior_rows})
            selection = {"frames": segment["frames"]}; d.write_once(root / "selection.json", selection)
            scope = {"totals": {"scored_frames": 3}, "accepted_gap_report": d.binding(root, root / "prior.json")}
            binding = d.binding(root, root / "selection.json")
            rows, retention, changes = continuous.score_saved_selection(root, scope, selection, binding)
            self.assertEqual([r["baseline"]["outcome"] for r in rows], ["matched", "missing", "matched"])
            self.assertEqual([r["selected"]["outcome"] for r in rows], ["matched"]*3)
            self.assertTrue(retention[0]["retained_exact_coordinate"])
            self.assertEqual(changes, [])
            (root / "selection.json").write_text("{}", encoding="utf-8")
            with patch.object(continuous.saved, "read_bound") as reader:
                with self.assertRaisesRegex(ValueError, "persisted unchanged"):
                    continuous.score_saved_selection(root, scope, selection, binding)
                reader.assert_not_called()


if __name__ == "__main__": unittest.main()
