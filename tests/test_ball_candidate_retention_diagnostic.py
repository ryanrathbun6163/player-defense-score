"""Synthetic checks for the bounded, saved-evidence mechanism ledger.

These fixtures are invented JSON and byte strings. They never access basketball
pixels, real labels, model inference, selectors, evaluators, or renderers.
"""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.ball_tracking import candidate_retention_diagnostic as diagnostic


def write_json(root, relative, document):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
    return {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def annotation(*, uncertainty=2.0, eligible=True, visibility="partially_visible"):
    return {
        "localization_eligible": eligible,
        "visibility": visibility,
        "geometry": {
            "center_xy_px": [10.0, 20.0],
            "source": "amodal_estimate",
            "uncertainty_radius_px": uncertainty,
        },
    }


def approval_fixture(root):
    design = root / "docs/design.md"
    design.parent.mkdir(parents=True)
    design.write_text("Synthetic bounded saved-evidence design.\n", encoding="utf-8")
    design_binding = {"path": "docs/design.md", "sha256": hashlib.sha256(design.read_bytes()).hexdigest()}
    proposal = {
        "schema_version": "candidate_retention_localization_diagnostic_proposal/v0.1",
        "proposal_id": "saved_candidate_retention_localization_diagnostic_v0_1",
        "design_document": design_binding,
    }
    proposal_binding = write_json(root, "configs/proposal.json", proposal)
    approval = {
        "schema_version": "ball_candidate_retention_localization_approval/v0.1",
        "proposal": proposal_binding,
        "design_document": design_binding,
        "approved_by": "synthetic_reviewer",
        "statement": "Approve only this synthetic saved-evidence diagnostic.",
        "diagnostic_implementation_authorized": True,
        "diagnostic_execution_authorized": True,
        "new_tracking_experiment_authorized": False,
        "training_authorized": False,
        "git_mutations_authorized": False,
        "selected_method": None,
        "selected_operating_point": None,
        "quality_gate": None,
    }
    return root / proposal_binding["path"], proposal, approval


def scope_fixture():
    """Invent the full frozen cardinalities without reading any real evidence."""
    frames = []
    for index in range(32):
        frame_id = "synthetic_{:03d}".format(index)
        role = "persistent_miss" if index < 20 else "positive_control" if index < 27 else "hidden_control"
        frame = {
            "id": frame_id,
            "cohort_role": role,
            "possession_id": "synthetic_possession",
            "purpose": "representative_evaluation",
            "window_id": "synthetic_window",
            "frame_index": index,
            "candidates": [],
            "display_outcomes": [{"detector": "RF" if family < 9 else "YOLO", "arm": str(family), "confidence_threshold": confidence}
                                 for family in range(10) for confidence in (.20, .35)],
        }
        indices = [("RF", 0)] + ([("RF", 1)] if index < 24 else []) + ([("YOLO", 0)] if index < 26 else [])
        for detector, candidate_index in indices:
            frame["candidates"].append({
                "id": "{}_{}_{}".format(frame_id, detector, candidate_index),
                "detector": detector,
                "input_candidates": {"sha256": ("a" if detector == "RF" else "b") * 64},
                "detection": {"candidate_index": candidate_index},
            })
        frames.append(frame)
    fields = ("id", "cohort_role", "possession_id", "purpose", "frame_index", "window_id")
    proposal = {"scope": {
        "frame_count": 32,
        "candidate_count": 82,
        "display_outcome_count": 640,
        "saved_cap_record_count": 15,
        "frames": [{key: frame[key] for key in fields} for frame in frames],
        "candidate_ids": [candidate["id"] for frame in frames for candidate in frame["candidates"]],
        "cohort_counts": {"persistent_miss": 20, "positive_control": 7, "hidden_control": 5},
        "candidate_counts_by_detector": {"RF": 56, "YOLO": 26},
    }}
    inspection = {"frames": frames}
    cap = {"records": [{"frame_id": frame["id"]} for frame in frames[:15]]}
    return proposal, inspection, cap


def assembly_fixture(root, *, cap_content_valid=True):
    """Two invented frames with real JSON bindings and mixed inference provenance."""
    view = {"view_id": "synthetic_crop", "ordinal": 0, "xyxy_half_open_px": [0, 0, 80, 80]}
    raw_by_detector = {}
    bindings = {}
    for detector in ("RF", "YOLO"):
        raw_frames = []
        inventory = []
        for frame_index in (7, 8):
            indices = [2, *range(3, 22), 99] if detector == "RF" else [99]
            items, locals_ = [], []
            for local_index, index in enumerate(indices):
                center = [13.0, 24.0] if detector == "RF" and index == 99 else [50.0, 60.0] if detector == "RF" else [10.0, 20.0]
                confidence = .02 if index == 99 and detector == "RF" else .9 if index in (2, 99) else .1
                detection = {"candidate_index": index, "center_xy_px": center, "confidence": confidence,
                             "bbox_xyxy_px": [center[0] - 1, center[1] - 1, center[0] + 1, center[1] + 1]}
                local = {**detection, "candidate_index": local_index}
                items.append({"detection": detection, "view_ordinal": 0, "local_candidate_index": local_index})
                locals_.append(local)
            crop_view = {"view": view, "candidates": locals_} if detector == "RF" else {"view": view, "prediction": {"candidates": locals_}}
            raw_frames.append({"frame_index": frame_index, "candidates": items, "views": [crop_view]})
            inventory.append({"frame_index": frame_index, "view_ordinal": 0,
                              "actual_inference_commit": ("b" if frame_index == 7 else "c") * 40})
        raw = {"header": {"per_view_model_provenance": {"code_commit": "a" * 40},
                          "inference_units": inventory}, "frames": raw_frames}
        raw["content_sha256"] = diagnostic.canonical_sha256(raw)
        raw_by_detector[detector] = raw
        bindings[detector] = write_json(root, "inputs/{}_candidates.json".format(detector), raw)

    annotations = [dict(annotation(uncertainty=9.0), frame_index=7),
                   {"frame_index": 8, "localization_eligible": False, "visibility": "not_visible", "geometry": None}]
    annotation_binding = write_json(root, "inputs/annotations.json", {"annotations": annotations})
    frames = []
    for offset, frame_index in enumerate((7, 8)):
        frame = {"id": "synthetic_{:03d}".format(frame_index), "frame_index": frame_index,
                 "window_id": "synthetic_window", "possession_id": "synthetic_possession",
                 "purpose": "representative_evaluation", "cohort_role": "positive_control" if frame_index == 7 else "hidden_control",
                 "annotation": annotations[offset], "annotation_binding": annotation_binding,
                 "candidates": [], "display_outcomes": [], "saved_floor_outcomes": {}}
        for detector in ("RF", "YOLO"):
            raw = raw_by_detector[detector]
            source_frame = raw["frames"][offset]
            for position, item in enumerate(source_frame["candidates"]):
                if item["detection"]["candidate_index"] not in (2, 99):
                    continue
                index = item["detection"]["candidate_index"]
                unit = raw["header"]["inference_units"][offset] if detector == "YOLO" else None
                local_candidates = source_frame["views"][0]["candidates"] if detector == "RF" else source_frame["views"][0]["prediction"]["candidates"]
                frame["candidates"].append({
                    "id": "{}_{}_{}".format(frame["id"], detector, index), "detector": detector,
                    "detection": item["detection"], "input_candidates": bindings[detector],
                    "source_candidate_pointer": "/frames/{}/candidates/{}".format(offset, position),
                    "crop_provenance": {"view": view,
                                        "local_candidate": local_candidates[item["local_candidate_index"]],
                                        "actual_inference_commit": unit["actual_inference_commit"] if unit else "a" * 40,
                                        "inference_unit": unit},
                    "new_identity_label": None,
                })
        frames.append(frame)

    reports = []
    cap_binding = None
    for detector in ("RF", "YOLO"):
        raw = raw_by_detector[detector]
        for confidence in (.01, .20, .35):
            variant = "{}_{}".format(detector, confidence)
            config = {"confidence_threshold": confidence, "candidate_cap": 20 if confidence == .01 else None,
                      "arm": "crop_top_twenty" if confidence == .01 else "crop_top_one"}
            traces = []
            for offset, frame in enumerate(frames):
                decisions = []
                for item in raw["frames"][offset]["candidates"]:
                    index = item["detection"]["candidate_index"]
                    if confidence == .01:
                        disposition = "outside_top_twenty" if detector == "RF" and index == 99 else "emitted"
                    else:
                        disposition = "below_threshold" if item["detection"]["confidence"] < confidence else "emitted"
                    decisions.append({"candidate_index": index, "disposition": disposition})
                traces.append({"frame_index": frame["frame_index"], "candidate_decisions": decisions,
                               "emitted_candidate_indices": [d["candidate_index"] for d in decisions if d["disposition"] == "emitted"]})
            observations = {"config": config, "variant_id": variant, "possession_id": "synthetic_possession",
                            "input_candidate_content_sha256": diagnostic.canonical_sha256(raw), "frames": traces}
            selector = {"observations": observations, "input_crop_file": bindings[detector], "crop_content_sha256": raw["content_sha256"]}
            selector_binding = write_json(root, "inputs/synthetic_window/{}.json".format(variant), selector)
            if detector == "RF" and confidence == .01:
                cap_binding = selector_binding
            results = []
            for offset, frame in enumerate(frames):
                matched = 99 if detector == "YOLO" and offset == 0 else None
                results.append({"frame_index": frame["frame_index"], "matched_candidate_index": matched,
                                "accepted_detection_count": len(traces[offset]["emitted_candidate_indices"]),
                                "matched_center_error_px": 0.0 if matched is not None else None,
                                "matched_effective_center_error_px": 0.0 if matched is not None else None,
                                "false_positive_count": len(traces[offset]["emitted_candidate_indices"]) - int(matched is not None),
                                "false_negative_count": int(offset == 0 and matched is None),
                                "duplicate_false_positive_count": 0,
                                "non_visible_false_alarm_count": int(offset == 1),
                                "scoring_status": "localization_eligible" if offset == 0 else "non_visible_negative"})
            report = {"possession_id": "synthetic_possession", "selection_purpose": "representative_evaluation",
                      "localization_radius_px": 10, "config": config, "variant_id": variant,
                      "observations_content_sha256": diagnostic.canonical_sha256(observations),
                      "input_candidate_content_sha256": diagnostic.canonical_sha256(raw), "frame_results": results}
            if confidence == .01 and detector == "RF" and not cap_content_valid:
                report["observations_content_sha256"] = "0" * 64
            report_index = len(reports)
            reports.append(report)
            for offset, frame in enumerate(frames):
                if confidence != .01:
                    frame["display_outcomes"].append({
                        "detector": detector, "arm": "crop_top_one", "confidence_threshold": confidence,
                        "emitted_candidate_indices": traces[offset]["emitted_candidate_indices"],
                        "saved_outcome": "matched" if results[offset]["matched_candidate_index"] is not None else "hidden_alarm" if offset == 1 else "unmatched",
                        "false_negative_cause": None,
                        "report_source": {"json_pointer": "/evaluation_reports/{}/frame_results/{}".format(report_index, offset)},
                        "observations_source": {**selector_binding, "json_pointer": "/observations/frames/{}".format(offset)},
                    })

        # Both report families preserve original indices, never output positions.
        floor_results = [{"frame_index": f["frame_index"], "matched_candidate_index": 99 if i == 0 else None,
                          "matched_center_error_px": 5.0 if detector == "RF" and i == 0 else 0.0 if i == 0 else None}
                         for i, f in enumerate(frames)]
        floor_index = len(reports)
        reports.append({"possession_id": "synthetic_possession", "selection_purpose": "representative_evaluation",
                        "localization_radius_px": 10, "config": {"confidence_threshold": .01}, "frame_results": floor_results})
        for offset, frame in enumerate(frames):
            frame["saved_floor_outcomes"][detector] = {"saved_frame_result": floor_results[offset],
                "source": {"json_pointer": "/evaluation_reports/{}/frame_results/{}".format(floor_index, offset)}}

    aggregate = {"evaluation_reports": reports, "saved_control_outputs": [cap_binding]}
    report_binding = write_json(root, "inputs/reports.json", aggregate)
    for frame in frames:
        for outcome in frame["display_outcomes"]:
            outcome["report_source"].update(report_binding)
        for outcome in frame["saved_floor_outcomes"].values():
            outcome["source"].update(report_binding)
    cap = {"records": [{"frame_id": frames[0]["id"], "raw_floor_match_candidate_index": 99,
                        "saved_top_twenty_frame_result": reports[0]["frame_results"][0],
                        "source": {**report_binding, "json_pointer": "/evaluation_reports/0/frame_results/0"}}]}
    findings = write_json(root, "inputs/findings.json", {"synthetic_observation": "Identity remains unresolved."})
    inspection = {"frames": frames}
    by_name = {"inspection.json": write_json(root, "inputs/inspection.json", inspection), "findings.md": findings}
    return inspection, cap, diagnostic._Evidence(root), by_name, {"assets": []}


class EvidenceBindingTests(unittest.TestCase):
    def test_json_pointers_resolve_exact_nested_values_and_escaped_keys(self):
        document = {"a/b": {"~key": [None, {"candidate_index": 99}]}}
        self.assertIs(diagnostic.resolve_pointer(document, ""), document)
        self.assertIsNone(diagnostic.resolve_pointer(document, "/a~1b/~0key/0"))
        self.assertEqual(
            diagnostic.resolve_pointer(document, "/a~1b/~0key/1/candidate_index"), 99
        )

    def test_invalid_or_shifted_pointer_is_not_silently_resolved(self):
        document = {"frames": [{"candidate_index": 99}]}
        for pointer in ("frames/0", "/frames/1", "/frames/-1", "/frames/nope", "/missing"):
            with self.subTest(pointer=pointer), self.assertRaises(diagnostic.DiagnosticError):
                diagnostic.resolve_pointer(document, pointer)

    def test_content_binding_rejects_changed_bytes_even_if_json_means_the_same(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binding = write_json(root, "evidence.json", {"candidate_index": 99})
            self.assertEqual(diagnostic.verify_binding(root, binding), root / "evidence.json")
            with (root / "evidence.json").open("a", encoding="utf-8") as stream:
                stream.write("\n")
            with self.assertRaises(diagnostic.DiagnosticError):
                diagnostic.verify_binding(root, binding)

    def test_missing_input_and_escape_from_evidence_root_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workspace"
            root.mkdir()
            outside = Path(temporary) / "outside.json"
            outside.write_bytes(b"{}")
            digest = hashlib.sha256(b"{}").hexdigest()
            for relative in ("missing.json", "../outside.json"):
                with self.subTest(path=relative), self.assertRaises(diagnostic.DiagnosticError):
                    diagnostic.verify_binding(root, {"path": relative, "sha256": digest})

    def test_content_digest_is_order_independent_but_preserves_null_and_numeric_values(self):
        a = {"matched_error": None, "center": [4.0, 8.0]}
        b = {"center": [4.0, 8.0], "matched_error": None}
        self.assertEqual(diagnostic.canonical_sha256(a), diagnostic.canonical_sha256(b))
        changed = {"center": [4.0, 8.0], "matched_error": 0.0}
        self.assertNotEqual(diagnostic.canonical_sha256(a), diagnostic.canonical_sha256(changed))


class ParallelMechanismTests(unittest.TestCase):
    def test_confidence_and_cap_losses_remain_separate_settings(self):
        # One proposal can be lost to confidence at .20/.35 and to the cap at
        # .01. These are three setting records, not three independent frames.
        saved = [(.20, "below_threshold"), (.35, "below_threshold"), (.01, "outside_top_twenty")]
        actual = [(threshold, diagnostic.retention_state(state)) for threshold, state in saved]
        self.assertEqual(actual, [(.20, "confidence_rejected"), (.35, "confidence_rejected"), (.01, "saved_cap_rejected")])
        self.assertEqual(diagnostic.retention_state("outside_selector_cap"), "saved_cap_rejected")
        self.assertEqual(diagnostic.retention_state("eligible_not_emitted"), "retained_but_not_emitted")
        self.assertEqual(diagnostic.retention_state("emitted"), "emitted")

    def test_unverified_observation_content_cannot_establish_cap_membership(self):
        self.assertEqual(
            diagnostic.retention_state("outside_top_twenty", content_verified=False), "unknown"
        )
        self.assertEqual(diagnostic.retention_state("emitted", content_verified=False), "unknown")

    def test_top_one_selector_rejection_is_a_choice_loss_not_top_twenty_preprocessing(self):
        self.assertEqual(
            diagnostic.retention_state("outside_selector_cap", arm="yolo_top_one"),
            "retained_but_not_emitted",
        )
        self.assertEqual(
            diagnostic.retention_state("outside_selector_cap", arm="crop_top_twenty"),
            "saved_cap_rejected",
        )

    def test_ball_region_hypothesis_can_have_nonzero_distance_without_identity_certification(self):
        candidate = {
            "center_xy_px": [13.0, 24.0],
            "agent_observation": "Synthetic ball-region hypothesis, identity unresolved",
            "certified_candidate_identity": None,
            "training_eligible": False,
            "matched_error_px": None,
        }
        before = copy.deepcopy(candidate)
        reference = annotation()
        result = diagnostic.reference_residual(candidate, reference)
        self.assertEqual((result["dx"], result["dy"], result["reference_distance_px"]), (3.0, 4.0, 5.0))
        self.assertEqual(result["reference_geometry"], reference["geometry"])
        self.assertEqual(candidate, before)
        self.assertIsNone(candidate["certified_candidate_identity"])
        self.assertIsNone(candidate["matched_error_px"])
        self.assertFalse(candidate["training_eligible"])

    def test_amodal_uncertainty_is_preserved_without_reducing_raw_distance(self):
        candidate = {"center_xy_px": [13.0, 24.0]}
        low = diagnostic.reference_residual(candidate, annotation(uncertainty=1.0))
        high = diagnostic.reference_residual(candidate, annotation(uncertainty=30.0))
        self.assertEqual(low["reference_distance_px"], 5.0)
        self.assertEqual(high["reference_distance_px"], 5.0)
        self.assertEqual(high["reference_geometry"]["uncertainty_radius_px"], 30.0)

    def test_hidden_and_ineligible_frames_have_null_residuals(self):
        hidden = {"localization_eligible": False, "visibility": "not_visible", "geometry": None}
        for reference in (hidden, annotation(eligible=False)):
            with self.subTest(reference=reference):
                result = diagnostic.reference_residual({"center_xy_px": [13.0, 24.0]}, reference)
                for key in ("dx", "dy", "reference_distance_px"):
                    self.assertIsNone(result[key])
                self.assertTrue(result["reason"])

    def test_candidate_keys_keep_detector_and_file_namespaces(self):
        frame = {"window_id": "synthetic_window", "frame_index": 7}
        rf = {"input_candidates": {"sha256": "a" * 64}, "detector": "RF", "detection": {"candidate_index": 0}}
        yolo = {**rf, "detector": "YOLO"}
        other_file = {**rf, "input_candidates": {"sha256": "b" * 64}}
        self.assertEqual(diagnostic.candidate_key(frame, rf), ("a" * 64, "RF", "synthetic_window", 7, 0))
        self.assertEqual(len({diagnostic.candidate_key(frame, value) for value in (rf, yolo, other_file)}), 3)


class MappingAndScopeTests(unittest.TestCase):
    def test_original_index_is_verified_from_candidate_mapping_not_list_position(self):
        frame = {"window_id": "synthetic_window", "frame_index": 7}
        detection = {"candidate_index": 99, "center_xy_px": [13.0, 24.0], "confidence": .03}
        candidate = {
            "id": "synthetic_RF_99",
            "detector": "RF",
            "input_candidates": {"sha256": "a" * 64},
            "source_candidate_pointer": "/frames/0/candidates/0",
            "detection": detection,
        }
        raw = {"frames": [{"frame_index": 7, "candidates": [{"detection": copy.deepcopy(detection)}]}]}
        diagnostic.verify_candidate_mapping(frame, candidate, raw)
        self.assertEqual(diagnostic.candidate_key(frame, candidate)[-1], 99)
        wrong_index = copy.deepcopy(candidate)
        wrong_index["detection"]["candidate_index"] = 0
        with self.assertRaises(diagnostic.DiagnosticError):
            diagnostic.verify_candidate_mapping(frame, wrong_index, raw)
        wrong_frame = copy.deepcopy(raw)
        wrong_frame["frames"][0]["frame_index"] = 8
        with self.assertRaises(diagnostic.DiagnosticError):
            diagnostic.verify_candidate_mapping(frame, candidate, wrong_frame)

    def test_exact_fixed_scope_accepts_full_synthetic_cardinalities(self):
        diagnostic.validate_scope(*scope_fixture())

    def test_missing_extra_and_duplicate_records_fail_fixed_scope(self):
        for scenario in ("frame", "candidate", "display", "cap", "duplicate_frame", "duplicate_candidate", "duplicate_cap"):
            proposal, inspection, cap = scope_fixture()
            if scenario == "frame":
                inspection["frames"].pop()
            elif scenario == "candidate":
                inspection["frames"][0]["candidates"].pop()
            elif scenario == "display":
                inspection["frames"][0]["display_outcomes"].append({"unexpected": True})
            elif scenario == "cap":
                cap["records"].pop()
            elif scenario == "duplicate_frame":
                inspection["frames"][1] = copy.deepcopy(inspection["frames"][0])
            elif scenario == "duplicate_candidate":
                inspection["frames"][0]["candidates"][1] = copy.deepcopy(inspection["frames"][0]["candidates"][0])
            else:
                cap["records"][1] = copy.deepcopy(cap["records"][0])
            with self.subTest(scenario=scenario), self.assertRaises(diagnostic.DiagnosticError):
                diagnostic.validate_scope(proposal, inspection, cap)

    def test_changing_declared_counts_cannot_expand_the_approved_scope(self):
        for field in ("frame_count", "candidate_count", "display_outcome_count", "saved_cap_record_count"):
            proposal, inspection, cap = scope_fixture()
            proposal["scope"][field] += 1
            with self.subTest(field=field), self.assertRaises(diagnostic.DiagnosticError):
                diagnostic.validate_scope(proposal, inspection, cap)


class SyntheticAssemblyTests(unittest.TestCase):
    def test_actual_saved_evidence_join_preserves_namespaces_nulls_and_inference_commits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = assembly_fixture(root)
            frames = diagnostic.build_ledger_frames(*fixture)
            visible, hidden = frames
            by_identity = {(c["saved_candidate"]["detector"], c["saved_candidate"]["detection"]["candidate_index"]): c
                           for c in visible["candidates"]}
            weak = by_identity[("RF", 99)]
            yolo = by_identity[("YOLO", 99)]
            self.assertNotEqual(weak["identity_key"], yolo["identity_key"])
            self.assertTrue(weak["retention"]["saved_floor_selected_match"])
            self.assertEqual([s["state"] for s in weak["retention"]["display_settings"]], ["confidence_rejected", "confidence_rejected"])
            self.assertEqual(weak["retention"]["top_twenty_at_0_01"]["membership"], "saved_cap_rejected")
            self.assertEqual(weak["localization"]["reference_distance_px"], 5.0)
            self.assertEqual(weak["localization"]["reference_geometry"]["uncertainty_radius_px"], 9.0)
            self.assertIsNone(weak["identity"]["certified_candidate_identity"])
            self.assertFalse(weak["identity"]["training_eligible"])
            self.assertEqual(weak["saved_candidate"]["crop_provenance"]["actual_inference_commit"], "a" * 40)
            self.assertEqual(yolo["saved_candidate"]["crop_provenance"]["actual_inference_commit"], "b" * 40)
            hidden_yolo = next(c for c in hidden["candidates"] if c["saved_candidate"]["detector"] == "YOLO")
            self.assertEqual(hidden_yolo["saved_candidate"]["crop_provenance"]["actual_inference_commit"], "c" * 40)
            for candidate in hidden["candidates"]:
                self.assertIsNone(candidate["localization"]["reference_distance_px"])
            rf_display = visible["display_outcomes"][0]
            self.assertIsNone(rf_display["saved_frame_result"]["matched_center_error_px"])
            yolo_display = next(o for o in visible["display_outcomes"] if o["saved_display_outcome"]["detector"] == "YOLO")
            self.assertEqual(yolo_display["saved_frame_result"]["matched_candidate_index"], 99)
            self.assertEqual(yolo_display["saved_display_outcome"]["emitted_candidate_indices"], [99])
            self.assertGreater(len(fixture[2].pointers), 20)
            fixture[2].preserve()

    def test_actual_ledger_writer_round_trips_saved_evidence_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = assembly_fixture(root)
            ledger = {"frames": diagnostic.build_ledger_frames(*fixture)}
            output_root = "data/outputs/ball_tracking/candidate_retention_localization_diagnostic"
            target = diagnostic.create_output_directory(root, root / output_root / "synthetic_v1", output_root)
            diagnostic.write_ledger_files(target, ledger)
            saved = (target / "case_ledger.json").read_bytes()
            self.assertEqual(json.loads(saved), ledger)
            self.assertTrue((target / "summary.md").is_file())
            with self.assertRaises((diagnostic.DiagnosticError, FileExistsError)):
                diagnostic.write_ledger_files(target, {"frames": []})
            self.assertEqual((target / "case_ledger.json").read_bytes(), saved)
            fixture[2].preserve()

    def test_required_report_byte_tampering_stops_assembly(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = assembly_fixture(root)
            path = root / fixture[0]["frames"][0]["display_outcomes"][0]["report_source"]["path"]
            path.write_bytes(path.read_bytes() + b" ")
            with self.assertRaisesRegex(diagnostic.DiagnosticError, "SHA-256 mismatch"):
                diagnostic.build_ledger_frames(*fixture)

    def test_rebound_selector_still_must_match_saved_content_and_original_namespace(self):
        for scenario in ("observation_content", "candidate_namespace"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                fixture = assembly_fixture(root)
                inspection, _, _, by_name, _ = fixture
                source = inspection["frames"][0]["display_outcomes"][0]["observations_source"]
                wrapper = json.loads((root / source["path"]).read_text(encoding="utf-8"))
                if scenario == "observation_content":
                    wrapper["observations"]["frames"][0]["candidate_decisions"][-1]["candidate_index"] = 123
                else:
                    wrapper["input_crop_file"] = inspection["frames"][0]["candidates"][-1]["input_candidates"]
                new_binding = write_json(root, source["path"], wrapper)
                for frame in inspection["frames"]:
                    for outcome in frame["display_outcomes"]:
                        if outcome["observations_source"]["path"] == source["path"]:
                            outcome["observations_source"].update(new_binding)
                by_name["inspection.json"] = write_json(root, "inputs/inspection.json", inspection)
                with self.assertRaises(diagnostic.DiagnosticError):
                    diagnostic.build_ledger_frames(*fixture)

    def test_saved_pointer_payload_and_outcome_cannot_drift(self):
        for scenario in ("reference", "display_outcome"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                fixture = assembly_fixture(root)
                inspection, _, _, by_name, _ = fixture
                if scenario == "reference":
                    inspection["frames"][0]["annotation"]["geometry"]["center_xy_px"][0] += 1
                else:
                    inspection["frames"][0]["display_outcomes"][0]["saved_outcome"] = "matched"
                by_name["inspection.json"] = write_json(root, "inputs/inspection.json", inspection)
                with self.assertRaises(diagnostic.DiagnosticError):
                    diagnostic.build_ledger_frames(*fixture)

    def test_absent_optional_cap_selector_stays_unknown_without_changing_saved_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = assembly_fixture(root)
            (root / "inputs/synthetic_window/RF_0.01.json").unlink()
            saved = copy.deepcopy(fixture[1]["records"][0])
            frames = diagnostic.build_ledger_frames(*fixture)
            detail = frames[0]["cap_record"]
            self.assertEqual(detail["saved_record"], saved)
            self.assertEqual(detail["resolved_membership"]["membership"], "unknown")
            self.assertFalse(detail["resolved_membership"]["content_contract_verified"])
            self.assertTrue(detail["resolved_membership"]["reason"])

    def test_contradictory_cap_content_is_rejected_instead_of_claiming_unknown(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = assembly_fixture(Path(temporary), cap_content_valid=False)
            with self.assertRaisesRegex(diagnostic.DiagnosticError, "content contract mismatch"):
                diagnostic.build_ledger_frames(*fixture)


class OutputGuardTests(unittest.TestCase):
    def test_output_directory_is_create_only_and_preserves_existing_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            relative = "data/outputs/ball_tracking/candidate_retention_localization_diagnostic"
            destination = root / relative / "synthetic_v1"
            actual = diagnostic.create_output_directory(root, destination, relative)
            self.assertEqual(actual, destination)
            sentinel = destination / "existing.json"
            sentinel.write_bytes(b'{"reviewed":true}')
            with self.assertRaises((diagnostic.DiagnosticError, FileExistsError)):
                diagnostic.create_output_directory(root, destination, relative)
            self.assertEqual(sentinel.read_bytes(), b'{"reviewed":true}')
            self.assertEqual(list(destination.iterdir()), [sentinel])

    def test_output_cannot_replace_root_or_escape_declared_output_tree(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            relative = "data/outputs/ball_tracking/candidate_retention_localization_diagnostic"
            for destination in (root / relative, root / "other", root / relative / ".." / "escaped"):
                with self.subTest(destination=destination), self.assertRaises(diagnostic.DiagnosticError):
                    diagnostic.create_output_directory(root, destination, relative)


class ApprovalGuardTests(unittest.TestCase):
    def test_bounded_diagnostic_requires_both_explicit_authorizations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, proposal, approval = approval_fixture(root)
            diagnostic.verify_approval(root, path, proposal, approval)
            for field in ("diagnostic_implementation_authorized", "diagnostic_execution_authorized"):
                for value in (False, None, "true", 1):
                    changed = {**approval, field: value}
                    with self.subTest(field=field, value=value), self.assertRaises(diagnostic.DiagnosticError):
                        diagnostic.verify_approval(root, path, proposal, changed)

    def test_approval_does_not_authorize_training_experiment_or_git(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, proposal, approval = approval_fixture(root)
            for field in ("new_tracking_experiment_authorized", "training_authorized", "git_mutations_authorized"):
                with self.subTest(field=field), self.assertRaises(diagnostic.DiagnosticError):
                    diagnostic.verify_approval(root, path, proposal, {**approval, field: True})

    def test_approval_bound_to_exact_proposal_and_design_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, proposal, approval = approval_fixture(root)
            for field in ("proposal", "design_document"):
                changed = copy.deepcopy(approval)
                changed[field]["sha256"] = "0" * 64
                with self.subTest(field=field), self.assertRaises(diagnostic.DiagnosticError):
                    diagnostic.verify_approval(root, path, proposal, changed)
            design = root / approval["design_document"]["path"]
            design.write_text("Changed design.\n", encoding="utf-8")
            with self.assertRaises(diagnostic.DiagnosticError):
                diagnostic.verify_approval(root, path, proposal, approval)


if __name__ == "__main__":
    unittest.main()
