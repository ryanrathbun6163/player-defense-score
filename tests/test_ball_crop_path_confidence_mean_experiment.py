"""Artificial-only one-attempt, phase access, create-only and receipt boundaries."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.ball_tracking import crop_path_confidence_mean_experiment as study
from src.ball_tracking import crop_retention_resources as resources
from test_ball_crop_retention_error_breakdown import limits, write_json
import test_ball_crop_saved_decision_contrast as contrast_fixtures
import test_ball_crop_retention_output_presence as presence_fixtures
from test_ball_crop_retention_experiment import candidate_fixture
from test_ball_crop_path_confidence_mean_evaluation import fixture as evaluation_fixture
from src.ball_tracking import crop_path_confidence_mean_evaluation as evaluation


def invented_prefix():
    events = contrast_fixtures.invented_prefix()
    aid = study.PREDECESSOR_ATTEMPT
    def append(kind, **details):
        events.append({"kind": kind, "attempt_id": aid, "sha256": f"{len(events) + 1:064x}", **details})
    append("started", unit_key=study.predecessor.UNIT_KEY, selection_unit=False, reserved_seconds=120.)
    for index in range(47):
        append("sample", elapsed_seconds=index / 2)
    event = presence_fixtures.completion_event(seconds=42.078, reservation=120.)
    event.update(worker_result={"path": "attempts/" + aid + ".result.json", "sha256": study.PREDECESSOR_RESULT_SHA}, monitor_samples=47)
    append("finished", **event)
    events[-1]["sha256"] = study.PREFIX_TIP
    return events


def invented_manifest():
    result = {"schema_version": "ball_crop_path_confidence_mean_experiment/v0.1", "study_id": study.ID,
        "output_root": study.OUTPUT_ROOT, "output_dir": study.OUTPUT_DIR, "permitted_stages": ["study"],
        "unit_key": study.UNIT_KEY, "maximum_unit_seconds": 1200,
        **{k: {"path": p, "sha256": "f" * 64} for k, p in study.AUTHORITY_PATHS.items()},
        "implementation_validation": {"path": study.CERTIFICATE_PATH, "sha256": "e" * 64},
        "post_commit_checkpoint": study.POST_COMMIT_PATH, "selected_method": None, "selected_operating_point": None, "quality_gate": None}
    for key, digest in (("proposal", study.PROPOSAL_SHA), ("scope", study.SCOPE_SHA),
                        ("authorization", study.APPROVAL_SHA), ("frozen_history", study.FROZEN_HISTORY_SHA)):
        result[key]["sha256"] = digest
    return result


class TemporaryRoot(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="mean_")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()


class MeanBudgetTests(TemporaryRoot):
    def journal(self, events=None, approved=None):
        value = study.MeanJournal.__new__(study.MeanJournal)
        value.root, value.folder = self.root, self.root / "resource_events"
        value.events = invented_prefix() if events is None else events
        value.limits = limits() if approved is None else approved
        value.baseline_bytes = 0
        return value

    def test_preserves_3221_events_62_closed_58_success_and_four_failures(self):
        journal = self.journal()
        self.assertEqual(len(journal.events), 3221)
        starts, ends = study._closed_prefix(journal)
        self.assertEqual(len(starts), 62)
        self.assertEqual(sum(e["success"] is True for e in ends.values()), 58)
        self.assertEqual({a for a, e in ends.items() if not e["success"]}, study.KNOWN_FAILURES)
        self.assertAlmostEqual(journal.consumed(), study.USED_SECONDS, places=7)

    def test_one_new_1200_second_reservation_preserves_prefix_and_refuses_retry(self):
        journal = self.journal()
        original = copy.deepcopy(journal.events)
        aid, seconds = journal.reserve(study.UNIT_KEY, False)
        self.assertEqual(seconds, 1200)
        self.assertEqual(journal.events[:-1], original)
        self.assertEqual(json.loads((self.root / "attempts" / (aid + ".reservation.json")).read_text()),
                         {"event_sha256": journal.events[-1]["sha256"]})
        with self.assertRaisesRegex(ValueError, "cannot retry"):
            journal.reserve(study.UNIT_KEY, False)

    def test_prior_role_and_selection_reservations_rejected(self):
        for key, selection in ((study.predecessor.UNIT_KEY, False), (study.UNIT_KEY, True), ("unknown", False)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.journal().reserve(key, selection)

    def test_remaining_cumulative_balance_is_not_reset(self):
        approved = limits()
        approved["maximum_cumulative_seconds"] = study.USED_SECONDS + 3
        _, seconds = self.journal(approved=approved).reserve(study.UNIT_KEY, False)
        self.assertAlmostEqual(seconds, 3, places=7)
        approved["maximum_cumulative_seconds"] = study.USED_SECONDS
        with self.assertRaises(ValueError):
            self.journal(approved=approved).reserve(study.UNIT_KEY, False)

    def test_tip_budget_success_and_receipt_mutations_refused(self):
        for mutate in (lambda es: es[-1].update(sha256="0" * 64),
                       lambda es: es[-1].update(elapsed_seconds=1),
                       lambda es: es[-1].update(success=False),
                       lambda es: es[-1]["worker_result"].update(sha256="0" * 64),
                       lambda es: es[-49].update(unit_key="old-role"),
                       lambda es: es.append({"kind": "started", "attempt_id": "a" * 32, "reserved_seconds": 1, "unit_key": "x"})):
            events = invented_prefix()
            mutate(events)
            with self.assertRaises((ValueError, resources.ResourceLimitError)):
                self.journal(events).reserve(study.UNIT_KEY, False)

    def test_additive_bytes_include_administration_and_keep_violating_sample(self):
        journal = self.journal()
        journal.baseline_bytes = 1000
        journal.append("sample", output_bytes=1000 + study.MAX_NEW_BYTES - study.monitor.FINAL_RESERVE)
        count = len(journal.events)
        with self.assertRaises(resources.ResourceLimitError):
            journal.append("sample", output_bytes=1001 + study.MAX_NEW_BYTES - study.monitor.FINAL_RESERVE)
        self.assertEqual(len(journal.events), count + 1)
        self.assertEqual(journal.events[-1]["output_bytes"], 1001 + study.MAX_NEW_BYTES - study.monitor.FINAL_RESERVE)

    def test_final_new_byte_overflow_seals_failure_instead_of_losing_attempt(self):
        journal = self.journal()
        aid, _ = journal.reserve(study.UNIT_KEY, False)
        result = journal.append("finished", attempt_id=aid, elapsed_seconds=1, success=True,
                                failure=None, final_accounting_output_bound_bytes=study.MAX_NEW_BYTES + 1)
        self.assertIs(result["success"], False)
        self.assertTrue((self.root / "attempts" / (aid + ".completion.json")).is_file())


class ReleaseBoundaryTests(TemporaryRoot):
    def test_manifest_rejects_expanded_scope_and_false_authority(self):
        manifest = invented_manifest()
        study._validate_manifest(manifest)
        for change in ({"permitted_stages": ["select"]}, {"maximum_unit_seconds": 1201},
                       {"selected_method": "mean"}, {"output_dir": "overwrite"}, {"unit_key": study.predecessor.UNIT_KEY},
                       {"authorization": {"path": study.APPROVAL_PATH, "sha256": "0" * 64}},
                       {"frozen_history": {"path": study.FROZEN_HISTORY_PATH, "sha256": "0" * 64}}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                study._validate_manifest({**manifest, **change})

    def test_dirty_checkpoint_stops_before_reading_manifest_or_science(self):
        with patch.object(study.original, "_clean_checkpoint", side_effect=ValueError("dirty")), \
             patch.object(study, "read_json", side_effect=AssertionError("must not read")):
            with self.assertRaisesRegex(ValueError, "dirty"):
                study._metadata(self.root, self.root / study.MANIFEST_PATH)

    def test_missing_release_stops_before_authority_reads(self):
        write_json(self.root / study.MANIFEST_PATH, invented_manifest())
        with patch.object(study.original, "_clean_checkpoint", return_value="e" * 40), \
             patch.object(study, "verify_binding", side_effect=AssertionError("must not read authority")):
            with self.assertRaisesRegex(ValueError, "checkpoint absent"):
                study._metadata(self.root, self.root / study.MANIFEST_PATH)

    def test_admin_reader_rejects_scientific_and_embedded_paths_before_open(self):
        for name in ("data/outputs/science.json", "configs/ball_tracking/annotations/truth.json", "data/clips/source.mp4"):
            with patch.object(Path, "open", side_effect=AssertionError("must not open")), self.assertRaises(ValueError):
                study._read_bound(self.root, {"path": name, "sha256": "f" * 64})

    def test_bounded_admin_reader_checks_digest_and_size(self):
        path = self.root / study.CERTIFICATE_PATH
        write_json(path, {"invented": True})
        binding = study.file_binding(self.root, path)
        self.assertEqual(study._read_bound(self.root, binding), {"invented": True})
        for wrong, cap in (({**binding, "sha256": "0" * 64}, 1000), (binding, 1)):
            with self.assertRaises(ValueError):
                study._read_bound(self.root, wrong, cap)

    def test_dry_run_never_dispatches_or_reads_science(self):
        context = {"spec_sha256": "f" * 64}
        with patch.object(study, "_metadata", return_value=context), patch.object(study, "verify_history") as history, \
             patch.object(study, "_preserved_metadata") as preservation, \
             patch.object(study, "_run_bounded_supervised", side_effect=AssertionError("dispatch")):
            result = study.run_study(self.root, self.root / study.MANIFEST_PATH, True)
        self.assertIs(result["scientific_inputs_verified"], False)
        history.assert_called_once_with(self.root, context, "before")
        preservation.assert_called_once_with(self.root, context, "before")


class PhaseAndPublicationTests(TemporaryRoot):
    def fixture(self):
        rows, metadata = [], []
        for role in ("candidate_run", "saved_control_observations", "reviewed_annotations", "saved_scoring_pool", "source_png"):
            path = self.root / "data" / (role + ".json")
            write_json(path, {"role": role, "evil_pointer": "data/clips/forbidden.mp4"})
            binding = study.file_binding(self.root, path)
            stat = study._stat_metadata(path)
            rows.append({**binding, "role": role, "size_bytes": stat["size_bytes"]})
            metadata.append({"path": binding["path"], **stat})
        windows = [{"window_id": str(i)} for i in range(6)]
        files = [{"path": f"selection/{i}/observations.json", "maximum_bytes": 1024} for i in range(6)]
        files += [{"path": "summary.json", "maximum_bytes": 1024}]
        scope = {"windows": windows, "existing_scientific_files": rows, "outputs": {"files": files}}
        context = {"current_attempt_id": "a" * 32, "scope": scope, "history": {"scientific_input_metadata": metadata}}
        (self.root / study.OUTPUT_ROOT / "audit").mkdir(parents=True)
        return context, {r["role"]: r["path"] for r in rows}

    def test_no_worker_no_access(self):
        context, _ = self.fixture()
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(ValueError, "owned reservation"):
            study.PhaseAccess(self.root, context)

    def test_phase_rejects_labels_controls_pool_and_pixels_before_any_open(self):
        context, names = self.fixture()
        with patch.dict(os.environ, BALL_RETENTION_ATTEMPT_ID="a" * 32):
            access = study.PhaseAccess(self.root, context)
            self.assertEqual(access.json(names["candidate_run"])["role"], "candidate_run")
            for role in ("saved_control_observations", "reviewed_annotations", "saved_scoring_pool", "source_png"):
                with patch.object(Path, "open", side_effect=AssertionError("premature open")), self.assertRaises(ValueError):
                    access.read(names[role])
            with self.assertRaises(ValueError):
                access.read("data/clips/forbidden.mp4")

    def test_all_six_exact_outputs_must_freeze_before_scoring_and_cannot_revise(self):
        context, names = self.fixture()
        with patch.dict(os.environ, BALL_RETENTION_ATTEMPT_ID="a" * 32):
            access, sink = study.PhaseAccess(self.root, context), study.OutputSink(self.root, context["scope"])
            bindings = [sink.json(f"selection/{i}/observations.json", {"i": i}) for i in range(6)]
            for invalid in (bindings[:5], [bindings[0]] * 6):
                with self.assertRaises(ValueError):
                    access.freeze(invalid, sink)
            access.freeze(bindings, sink)
            self.assertEqual(access.json(names["reviewed_annotations"])["role"], "reviewed_annotations")
            self.assertEqual(access.json(names["saved_scoring_pool"])["role"], "saved_scoring_pool")
            with self.assertRaises(ValueError):
                access.read(names["source_png"])
            with self.assertRaises(ValueError):
                sink.json("selection/0/observations.json", {"changed": True})
            access.render(sink)
            self.assertTrue(access.read(names["source_png"]))
            with self.assertRaises(ValueError):
                access.json(names["saved_scoring_pool"])

    def test_wrong_scientific_digest_and_ownership_change_refused(self):
        context, names = self.fixture()
        context["scope"]["existing_scientific_files"][0]["sha256"] = "0" * 64
        with patch.dict(os.environ, BALL_RETENTION_ATTEMPT_ID="a" * 32):
            access = study.PhaseAccess(self.root, context)
            with self.assertRaisesRegex(ValueError, "bytes differ"):
                access.json(names["candidate_run"])
            os.environ["BALL_RETENTION_ATTEMPT_ID"] = "b" * 32
            with self.assertRaisesRegex(ValueError, "ownership"):
                access.read(names["candidate_run"])

    def test_create_only_declared_bounds_and_full_inventory(self):
        context, _ = self.fixture()
        sink = study.OutputSink(self.root, context["scope"])
        for name, raw in (("undeclared.json", b"{}"), ("../escape.json", b"{}"), ("summary.json", b"a" * 1025)):
            with self.assertRaises(ValueError):
                sink.write(name, raw)
        for i in range(6):
            sink.json(f"selection/{i}/observations.json", {"i": i})
        with self.assertRaises(ValueError):
            sink.complete()
        sink.json("summary.json", {"done": True})
        bindings, metadata = sink.complete()
        self.assertEqual(len(bindings), 7)
        self.assertEqual(len(metadata), 7)
        with self.assertRaises(ValueError):
            sink.json("summary.json", {})
        with self.assertRaises((ValueError, FileExistsError)):
            study.OutputSink(self.root, context["scope"])

    def test_changed_publication_is_rejected_before_phase_transition(self):
        context, _ = self.fixture()
        with patch.dict(os.environ, BALL_RETENTION_ATTEMPT_ID="a" * 32):
            access, sink = study.PhaseAccess(self.root, context), study.OutputSink(self.root, context["scope"])
            bindings = [sink.json(f"selection/{i}/observations.json", {"i": i}) for i in range(6)]
            (self.root / bindings[0]["path"]).write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                access.freeze(bindings, sink)
            self.assertEqual(access.phase, "selection")

    def test_candidate_conversion_matches_original_namespace_without_selector(self):
        window, expected, value, _ = candidate_fixture(self.root)
        with patch.object(study.original, "_candidate_input", side_effect=AssertionError("old reader")):
            actual = study.candidate_run(value, window)
        self.assertEqual(actual.to_dict(), expected.to_dict())
        value["frames"][0]["candidates"][0]["detection"]["confidence"] = .2
        with self.assertRaises(ValueError):
            study.candidate_run(value, window)


class ReturnedAccountingTests(unittest.TestCase):
    def fixture(self):
        windows, comparisons = [], []
        for i in range(6):
            purpose = evaluation.POOLS[i % 2]
            hidden = tuple(range(15, 20)) if i == 5 else ()
            start = 150 if i == 5 else 300 if i == 4 else 0
            _, _, observations, reports, window = evaluation_fixture(count=25, start=start, purpose=purpose, hidden=hidden)
            window["window_id"] = evaluation.DIAGNOSTIC_WINDOW if i == 4 else "artificial_" + str(i)
            window["possession_id"] = "possession_003" if i >= 4 else "possession_001"
            if i == 4:
                diagnostic_observations = observations
            windows.append(window)
            comparisons.append(evaluation.compare_window(window, reports[evaluation.ARM],
                {a: reports[a] for a in (evaluation.TT, evaluation.TOP)}, observations))
        pools = [evaluation.aggregate_pool([w for w in comparisons if w["purpose"] == p], p) for p in evaluation.POOLS]
        human = [{"frame_index": f, "emitted_candidate_index": None, "status": "reviewed", "reviewer": "Ryan"}
                 for f in evaluation.DIAGNOSTIC_FRAMES]
        # The historical reviewed TT diagnostic has one emission on every row.
        # The generic fixture omits offset2; preserve equal artificial arms here.
        for arm in evaluation.ARMS:
            item = diagnostic_observations[arm]["frames"][2]
            item.update(emitted_candidate_indices=[0], decision_reason="current_endpoint")
            if item["ranking"] is not None:
                item["ranking"]["winner"].update(endpoint=[302, 0], path=[[302, 0]], node_count=1, score=.8, endpoint_confidence=.8)
        # Keep source accounting for that diagnostic emission consistent.
        comparison = comparisons[4]
        for arm in evaluation.ARMS:
            row = comparison["summaries"][arm]
            row["frame_indices"]["missing"].remove(302)
            row["frame_indices"]["matched"].append(302)
            row["frame_indices"]["matched"].sort()
            row["counts"]["missing"] -= 1
            row["counts"]["matched"] += 1
            row["missed_eligible_count"] -= 1
            fake = {"frame_results": [{"frame_index": f, "accepted_detection_count": 1,
                     "matched_candidate_index": None if f == 301 else 0, "scoring_status": "localization_eligible"}
                     for f in range(300, 325)]}
            comparison["temporal_metrics"][arm] = evaluation.temporal_metrics(fake)
            comparison["path_metrics"][arm] = evaluation.path_metrics(diagnostic_observations[arm])
        for control in (evaluation.TT, evaluation.TOP):
            table = comparison["paired_transitions"][control]["eligible"]
            table["missing"]["missing"] = {"count": 0, "frame_indices": []}
            table["matched"]["matched"]["frame_indices"].append(302)
            table["matched"]["matched"]["frame_indices"].sort()
            table["matched"]["matched"]["count"] += 1
        pools = [evaluation.aggregate_pool([w for w in comparisons if w["purpose"] == p], p) for p in evaluation.POOLS]
        diagnostic = evaluation.diagnostic_rows(evaluation.DIAGNOSTIC_WINDOW, diagnostic_observations, human)
        reviews = []
        for w in windows:
            base = study.OUTPUT_ROOT + "/" + study.OUTPUT_DIR + "/review/" + w["window_id"]
            reviews.append({"window_id": w["window_id"], "clip": base + "/comparison.mp4",
                            "index_binding": {"path": base + "/review_index.json", "sha256": "f" * 64},
                            "first_frame_index": w["start_frame_index"], "last_frame_index": w["end_frame_index"],
                            "frame_count": 25, "fps": 5, "human_review": "pending"})
        summary = {"windows": comparisons, "pools": pools, "interpretation": evaluation.development_interpretation(pools),
                   "fixed_diagnostic": diagnostic, "reviews": reviews,
                   "selected_method": None, "selected_operating_point": None, "quality_gate": None}
        context = {"scope": {"windows": windows}, "human_ledger": {"rows": human}}
        return summary, context

    def test_bounded_return_reconciles_accounting_without_any_file_read(self):
        summary, context = self.fixture()
        with patch.object(Path, "open", side_effect=AssertionError("parent body access")):
            study.validate_bounded_summary(summary, context)
        self.assertLess(len(study._json_bytes(summary)), study.MAX_RETURN_BYTES)

    def test_count_transition_runs_human_identity_and_pixel_pointer_mutations_rejected(self):
        for mutate in (
            lambda s: s["windows"][0]["summaries"][evaluation.ARM]["counts"].update(matched=99),
            lambda s: s["windows"][0]["paired_transitions"][evaluation.TT]["eligible"]["matched"]["matched"].update(count=999),
            lambda s: s["windows"][0]["temporal_metrics"][evaluation.ARM].update(longest_correct_run=99),
            lambda s: s["pools"][0]["totals"][evaluation.TT]["counts"].update(missing=0),
            lambda s: s["fixed_diagnostic"][0]["saved_tt"]["original_human_record"].update(emitted_candidate_index=7),
            lambda s: s["fixed_diagnostic"][0]["new_mean"].update(semantic_identity="ball"),
            lambda s: s["fixed_diagnostic"][0]["new_mean"].pop("observation"),
            lambda s: s["fixed_diagnostic"][0]["new_mean"]["observation"].update(emitted_candidate_indices=[99]),
            lambda s: s["windows"][0]["changed_emission_frames"][evaluation.TT].append(0),
            lambda s: s["windows"][0]["path_metrics"][evaluation.ARM]["path_node_counts"].update({"0": 0, "1": 25}),
            lambda s: s["reviews"][0].update(clip="data/clips/source.mp4"),
            lambda s: s["reviews"][0].update(last_frame_index=23),
            lambda s: s.update(selected_method="mean"),
        ):
            summary, context = self.fixture()
            mutate(summary)
            with self.assertRaises((ValueError, KeyError)):
                study.validate_bounded_summary(summary, context)

    def test_review_index_transport_must_equal_its_verified_artifact_binding(self):
        summary, context = self.fixture()
        names = [r["index_binding"]["path"].removeprefix(study.OUTPUT_ROOT + "/" + study.OUTPUT_DIR + "/")
                 for r in summary["reviews"]]
        names += ["summary.json", "summary.md"]
        names += [f"artificial/{i}.json" for i in range(636 - len(names))]
        context.update(commit="c" * 40, spec_sha256="s" * 64)
        context["scope"]["outputs"] = {"files": [{"path": n, "maximum_bytes": study.MAX_RETURN_BYTES} for n in names]}
        full = [study.OUTPUT_ROOT + "/" + study.OUTPUT_DIR + "/" + n for n in names]
        artifacts = [{"path": name, "sha256": "f" * 64} for name in full]
        stats = {name: {"size_bytes": 10, "mtime_ns": 1, "device": 1, "inode": i} for i, name in enumerate(full)}
        result = {"schema_version": "ball_crop_path_confidence_mean_worker_result/v0.1", "stage": "study",
                  "unit_key": study.UNIT_KEY, "attempt_id": "a" * 32, "commit": context["commit"],
                  "spec_sha256": context["spec_sha256"], "artifacts": artifacts,
                  "artifact_metadata": [], "checks": study.CHECKS, "summary": summary,
                  "summary_text": study._summary_text(summary), "scientific_input_count": 176}
        def bind_transport():
            for name, raw in (("summary.json", study._json_bytes(summary)), ("summary.md", result["summary_text"].encode())):
                target = study.OUTPUT_ROOT + "/" + study.OUTPUT_DIR + "/" + name
                next(b for b in artifacts if b["path"] == target)["sha256"] = hashlib.sha256(raw).hexdigest()
                stats[target]["size_bytes"] = len(raw)
            result["artifact_metadata"] = [{"path": name, **stats[name]} for name in full]
        bind_transport()
        with tempfile.TemporaryDirectory(prefix="mean_receipt_") as temporary:
            root = Path(temporary).resolve()
            def stat(path):
                return stats[path.relative_to(root).as_posix()]
            with patch.object(study, "_stat_metadata", side_effect=stat), \
                 patch.object(Path, "open", side_effect=AssertionError("parent artifact body read")):
                study.validate_return(result, root, context, "a" * 32)
                summary["reviews"][0]["index_binding"]["sha256"] = "0" * 64
                bind_transport()
                with self.assertRaisesRegex(ValueError, "Review index binding differs"):
                    study.validate_return(result, root, context, "a" * 32)

    def test_return_cannot_omit_window_or_drop_to_partial_scope(self):
        summary, context = self.fixture()
        summary["windows"].pop()
        with self.assertRaises(ValueError):
            study.validate_bounded_summary(summary, context)


if __name__ == "__main__":
    unittest.main()
