"""Pure reading of saved U/F/C/S memberships; no file or scientific execution.

Callers supply the permitted parsed bodies. Only target breakdown rows and
identity/provenance fields are interpreted. Other embedded scientific fields
participate in the published digest check but are not followed or interpreted.
"""
from __future__ import annotations

import hashlib
import json

MAX_TEXT_BYTES = 64 * 1024
POOL_SCHEMA = "ball_crop_candidate_retention_pool/v0.1"
AUDIT_SCHEMA = "ball_crop_retention_independent_publication_recovery_audit/v0.1"
EXTRACT_SCHEMA = "ball_crop_retention_error_breakdown_pool_extract/v0.1"
SUMMARY_SCHEMA = "ball_crop_retention_post_review_error_breakdown/v0.1"
SCORING_COMMIT = "f36237247191e726ad7e81bdc6651f9340a9063d"
SCORING_SPEC = "4b1f9f3c75ee53eb1358bcb49981118269694ec39adb5a312ae325f8ee273bbf"
SELECTION_COMMIT = "0a7f5bc69be948b8c4e2c630c84c4ccdefb5dc41"
SELECTION_SPEC = "e481d645e946f285c655d721563172c4cb8c2f124214840b8c8d8ae5cfb752fd"
AUDIT_COMMIT = "a89cd40838b066c1d2fe3cb1f257dda10e80a3bb"
PURPOSES = ("representative_evaluation", "challenge_evaluation")
INPUT_KEYS = dict(zip(PURPOSES, ("representative_pool", "challenge_pool")))
ARMS = tuple("history_edge_" + a + "_cost_" + b for a in ("tight", "wide") for b in ("tight", "wide"))
ARM_NAMES = dict(zip(ARMS, ("TT", "TW", "WT", "WW")))
RADII = (5.0, 10.0, 15.0, 20.0, 30.0)
THRESHOLDS = (.01, .20, .35)
POLICIES = ("cap20", "all")
PARTS = ("U_no_candidate_at_export_floor", "F_confidence_filter_loss",
         "C_candidate_cap_loss", "S_path_choice_loss")
OTHER_LISTS = ("false_observations_on_eligible_frames", "hidden_alarm_frames")
KEY_FIELDS = ("arm", "radius_px", "confidence_threshold", "retention_policy")
WINDOWS = tuple({"window_id": f"possession_{p:03d}_frames_{first:04d}_{last:04d}_{purpose}_development_v0_2",
                 "possession_id": f"possession_{p:03d}", "purpose": purpose,
                 "start_frame_index": first, "end_frame_index": last, "authority_index": i}
                for i, (p, first, last, purpose) in enumerate(((1, 50, 74, PURPOSES[0]), (1, 200, 224, PURPOSES[1]),
                    (2, 250, 274, PURPOSES[0]), (2, 25, 49, PURPOSES[1]), (3, 300, 324, PURPOSES[0]), (3, 150, 174, PURPOSES[1]))))
DECISIONS = ("selected_method", "selected_operating_point", "quality_gate")
WINDOW_AUTHORITY = "../../../../../../../configs/ball_tracking/proposals/rfdetr_medium_crop_candidate_retention_v0_1.json"
PROPOSAL_REFERENCE = "../../../../../../../docs/ball_crop_candidate_retention_error_breakdown_proposal.md"


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _digest(value):
    # Stream canonical encoding rather than constructing a second large pool.
    digest = hashlib.sha256()
    encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    for piece in encoder.iterencode(value):
        digest.update(piece.encode("utf-8"))
    return digest.hexdigest()


def _published(value, schema):
    _require(type(value) is dict and value.get("schema_version") == schema, "Unsupported saved schema")
    _require(value.get("content_sha256") == _digest({k: v for k, v in value.items() if k != "content_sha256"}),
             "Published content digest differs")
    _require(all(k in value and value[k] is None for k in DECISIONS), "Saved decisions must remain explicitly null")


def _audit(audit):
    _published(audit, AUDIT_SCHEMA)
    _require(audit.get("status") == "passed" and audit.get("execution_code_commit") == AUDIT_COMMIT
             and audit.get("original_evaluation_commit") == SCORING_COMMIT
             and audit.get("original_evaluation_spec_sha256") == SCORING_SPEC
             and audit.get("original_selection_commit") == SELECTION_COMMIT
             and audit.get("original_selection_spec_sha256") == SELECTION_SPEC,
             "Passed audit source/scoring provenance differs")
    pools = audit.get("pool_audits")
    _require(type(pools) is list and len(pools) == 2 and {p["purpose"] for p in pools} == set(PURPOSES),
             "Audit does not preserve both pools")
    reviews = audit.get("review_audits")
    _require(type(reviews) is list and len(reviews) == 6
             and {r["window_id"] for r in reviews} == {w["window_id"] for w in WINDOWS},
             "Audit window identities differ")


def _role(confidence, policy):
    return "saved" if policy == "cap20" else "new_distinct" if confidence == .01 else "structural_equivalence_not_executed"


def _layout():
    return [(arm, radius, confidence, policy) for arm in ARMS for radius in RADII
            for confidence in THRESHOLDS for policy in POLICIES]


def _indices(value, window, label):
    _require(type(value) is list and all(type(i) is int for i in value), "Non-integer saved membership: " + label)
    _require(value == sorted(set(value)) and all(window["start_frame_index"] <= i <= window["end_frame_index"] for i in value),
             "Unsorted, duplicate or out-of-window membership: " + label)


def _validate_memberships(row, window):
    parts = row.get("parts")
    _require(type(parts) is dict and set(parts) == set(PARTS), "Saved loss categories are incomplete")
    seen = set()
    lengths = []
    for key in PARTS:
        values = parts[key]
        _indices(values, window, key)
        _require(seen.isdisjoint(values), "Saved U/F/C/S memberships overlap")
        seen.update(values)
        lengths.append(len(values))
    total = row.get("total_missed_eligible_frames")
    _require(type(total) is int and total >= 0 and sum(lengths) == total,
             "Saved loss memberships do not reconcile to the saved missed total")
    for key in OTHER_LISTS:
        _indices(row.get(key), window, key)
    hidden = set(row["hidden_alarm_frames"])
    _require(hidden.isdisjoint(seen) and hidden.isdisjoint(row["false_observations_on_eligible_frames"]),
             "Hidden alarms overlap eligible-frame evidence")
    _require(set(row["false_observations_on_eligible_frames"]) <= seen,
             "Single-output eligible false observations must also be saved misses")
    _require(row.get("candidate_burden_is_tracker_accuracy") is False
             and row.get("semantic_training_labels_created") is False, "Saved semantic limits differ")


def _source(source_map, output_pointer, input_key, pointer, identity, operation="copied"):
    source_map.append({"output_pointer": output_pointer, "input": input_key, "json_pointer": pointer,
                       "window_identity_pointer": identity, "operation": operation})


def extract_pool(pool: dict, audit: dict) -> dict:
    """Copy exactly 24 target rows from one supplied pool, using saved block IDs."""
    try:
        _audit(audit)
        _published(pool, POOL_SCHEMA)
        purpose = pool["purpose"]
        _require(purpose in PURPOSES and pool.get("code_commit") == SCORING_COMMIT
                 and pool.get("experiment_spec_sha256") == SCORING_SPEC,
                 "Saved pool purpose/scoring provenance differs")
        _require(pool.get("semantic_training_labels_created") is False and pool.get("independent_trials_claimed") is False,
                 "Saved pool interpretation limits differ")
        windows = {w["window_id"]: w for w in WINDOWS if w["purpose"] == purpose}
        measurements = pool.get("retention_measurements")
        _require(type(measurements) is list and len(measurements) == 3
                 and {m["window_id"] for m in measurements} == set(windows),
                 "Three distinct authority-matched measurement window IDs are required")
        rows = pool.get("loss_decomposition")
        _require(type(rows) is list and len(rows) == 360, "Exactly three complete 120-row blocks are required")
        input_key = INPUT_KEYS[purpose]
        result = {"schema_version": EXTRACT_SCHEMA, "purpose": purpose, "source_input": input_key,
                  "source_content_sha256": pool["content_sha256"], "audit_content_sha256": audit["content_sha256"],
                  "scoring_commit": pool["code_commit"], "scoring_spec_sha256": pool["experiment_spec_sha256"],
                  "audit_execution_commit": audit["execution_code_commit"], "rows": [], "source_map": []}
        source_map = result["source_map"]
        for key, source, pointer in (("purpose", input_key, "/purpose"), ("source_content_sha256", input_key, "/content_sha256"),
                                    ("audit_content_sha256", "audit", "/content_sha256"),
                                    ("scoring_commit", input_key, "/code_commit"),
                                    ("scoring_spec_sha256", input_key, "/experiment_spec_sha256"),
                                    ("audit_execution_commit", "audit", "/execution_code_commit")):
            _source(source_map, "/" + key, source, pointer, None)
        for block, measurement in enumerate(measurements):
            window = windows[measurement["window_id"]]
            identity = f"/retention_measurements/{block}/window_id"
            for offset, expected in enumerate(_layout()):
                index = block * 120 + offset
                row = rows[index]
                _require(type(row) is dict and tuple(row.get(k) for k in KEY_FIELDS) == expected
                         and all(type(row[k]) in (int, float) for k in ("radius_px", "confidence_threshold"))
                         and row.get("selection_execution_role") == _role(expected[2], expected[3]),
                         "Saved breakdown key order or execution role differs")
                if expected[1:3] != (10.0, .01):
                    continue
                _validate_memberships(row, window)
                target = "/rows/" + str(len(result["rows"]))
                base = f"/loss_decomposition/{index}"
                copied = {"window_id": measurement["window_id"], "purpose": purpose,
                          "possession_id": window["possession_id"], "start_frame_index": window["start_frame_index"],
                          "end_frame_index": window["end_frame_index"], "source_row_pointer": base,
                          "window_identity_pointer": identity}
                _source(source_map, target + "/window_id", input_key, identity, identity)
                _source(source_map, target + "/purpose", input_key, "/purpose", identity)
                for key in ("possession_id", "start_frame_index", "end_frame_index"):
                    _source(source_map, target + "/" + key, "window_authority", f"/windows/{window['authority_index']}/{key}", identity)
                for key in (*KEY_FIELDS, "selection_execution_role", "total_missed_eligible_frames"):
                    copied[key] = row[key]
                    _source(source_map, target + "/" + key, input_key, base + "/" + key, identity)
                copied["parts"], copied["membership_counts"] = {}, {}
                for key in PARTS:
                    copied["parts"][key] = list(row["parts"][key])
                    copied["membership_counts"][key] = len(row["parts"][key])
                    pointer = base + "/parts/" + key
                    _source(source_map, target + "/parts/" + key, input_key, pointer, identity)
                    _source(source_map, target + "/membership_counts/" + key, input_key, pointer, identity, "list_length")
                for key in OTHER_LISTS:
                    copied[key] = list(row[key])
                    copied["membership_counts"][key] = len(row[key])
                    _source(source_map, target + "/" + key, input_key, base + "/" + key, identity)
                    _source(source_map, target + "/membership_counts/" + key, input_key, base + "/" + key, identity, "list_length")
                result["rows"].append(copied)
        _require(len(result["rows"]) == 24, "Target extraction is incomplete")
        result["extraction_content_sha256"] = _digest(result)
        return result
    except (KeyError, TypeError, IndexError, AttributeError) as error:
        raise ValueError("Missing or unsupported saved breakdown relationship") from error


def _validate_extract(value):
    fields = {"schema_version", "purpose", "source_input", "source_content_sha256", "audit_content_sha256",
              "scoring_commit", "scoring_spec_sha256", "audit_execution_commit", "rows", "source_map", "extraction_content_sha256"}
    _require(type(value) is dict and set(value) == fields and value.get("schema_version") == EXTRACT_SCHEMA
             and value.get("extraction_content_sha256") == _digest({k: v for k, v in value.items() if k != "extraction_content_sha256"}),
             "Copied pool extraction is invalid or changed")
    purpose = value["purpose"]
    _require(purpose in PURPOSES and value["source_input"] == INPUT_KEYS[purpose]
             and value["scoring_commit"] == SCORING_COMMIT and value["scoring_spec_sha256"] == SCORING_SPEC
             and value["audit_execution_commit"] == AUDIT_COMMIT, "Copied pool provenance differs")
    _require(all(type(value[k]) is str and len(value[k]) == 64 and all(c in "0123456789abcdef" for c in value[k])
                 for k in ("source_content_sha256", "audit_content_sha256")), "Invalid copied source digest")
    rows = value["rows"]
    windows = {w["window_id"]: w for w in WINDOWS if w["purpose"] == purpose}
    _require(type(rows) is list and len(rows) == 24
             and {(r["window_id"], r["arm"], r["retention_policy"]) for r in rows}
                 == {(wid, arm, policy) for wid in windows for arm in ARMS for policy in POLICIES},
             "Copied window/settings inventory differs")
    input_key = INPUT_KEYS[purpose]
    expected_map = []
    for key, source, pointer in (("purpose", input_key, "/purpose"), ("source_content_sha256", input_key, "/content_sha256"),
                                ("audit_content_sha256", "audit", "/content_sha256"), ("scoring_commit", input_key, "/code_commit"),
                                ("scoring_spec_sha256", input_key, "/experiment_spec_sha256"),
                                ("audit_execution_commit", "audit", "/execution_code_commit")):
        _source(expected_map, "/" + key, source, pointer, None)
    row_fields = {"window_id", "purpose", "possession_id", "start_frame_index", "end_frame_index", "source_row_pointer",
                  "window_identity_pointer", *KEY_FIELDS, "selection_execution_role", "total_missed_eligible_frames",
                  "parts", "membership_counts", *OTHER_LISTS}
    for i, row in enumerate(rows):
        _require(set(row) == row_fields, "Unexpected copied row payload")
        window = windows[row["window_id"]]
        block, arm_index, policy_index = i // 8, (i % 8) // 2, i % 2
        base = f"/loss_decomposition/{block * 120 + arm_index * 30 + 6 + policy_index}"
        identity = f"/retention_measurements/{block}/window_id"
        _require(row["window_id"] == rows[block * 8]["window_id"] and row["arm"] == ARMS[arm_index]
                 and row["retention_policy"] == POLICIES[policy_index]
                 and row["source_row_pointer"] == base and row["window_identity_pointer"] == identity,
                 "Copied block mapping or source pointers differ")
        _require(row["purpose"] == purpose and all(row[k] == window[k] for k in ("possession_id", "start_frame_index", "end_frame_index"))
                 and row["radius_px"] == 10.0 and row["confidence_threshold"] == .01
                 and row["selection_execution_role"] == _role(.01, row["retention_policy"]), "Copied target labels differ")
        _validate_memberships({**row, "candidate_burden_is_tracker_accuracy": False, "semantic_training_labels_created": False}, window)
        _require(type(row["membership_counts"]) is dict and all(type(v) is int for v in row["membership_counts"].values())
                 and row["membership_counts"] == {**{k: len(row["parts"][k]) for k in PARTS}, **{k: len(row[k]) for k in OTHER_LISTS}},
                 "Copied membership cardinalities differ")
        target = f"/rows/{i}"
        _source(expected_map, target + "/window_id", input_key, identity, identity)
        _source(expected_map, target + "/purpose", input_key, "/purpose", identity)
        for key in ("possession_id", "start_frame_index", "end_frame_index"):
            _source(expected_map, target + "/" + key, "window_authority", f"/windows/{window['authority_index']}/{key}", identity)
        for key in (*KEY_FIELDS, "selection_execution_role", "total_missed_eligible_frames"):
            _source(expected_map, target + "/" + key, input_key, base + "/" + key, identity)
        for key in PARTS:
            pointer = base + "/parts/" + key
            _source(expected_map, target + "/parts/" + key, input_key, pointer, identity)
            _source(expected_map, target + "/membership_counts/" + key, input_key, pointer, identity, "list_length")
        for key in OTHER_LISTS:
            _source(expected_map, target + "/" + key, input_key, base + "/" + key, identity)
            _source(expected_map, target + "/membership_counts/" + key, input_key, base + "/" + key, identity, "list_length")
    _require(value["source_map"] == expected_map, "Copied source map differs from exact saved row/window relationships")


def _members(row, key, part=False):
    indices = row["parts"][key] if part else row[key]
    return str(row["membership_counts"][key]) + ": " + (", ".join(map(str, indices)) if indices else "none")


def build_summary(pool_results: list[dict]) -> tuple[dict, str]:
    """Present both complete copied pools, without computing pool statistics."""
    try:
        _require(type(pool_results) is list and len(pool_results) == 2
                 and {p["purpose"] for p in pool_results} == set(PURPOSES), "Both separate copied pools are required")
        for value in pool_results:
            _validate_extract(value)
        _require(pool_results[0]["audit_content_sha256"] == pool_results[1]["audit_content_sha256"], "Copied pools use different audits")
        # Copy only the small extraction, preventing the caller from attaching
        # raw fields to a returned object by retaining shared mutable references.
        pools = json.loads(json.dumps(sorted(pool_results, key=lambda p: PURPOSES.index(p["purpose"])), allow_nan=False))
        source_map = [{**entry, "output_pointer": f"/pools/{pi}" + entry["output_pointer"]}
                      for pi, pool in enumerate(pools) for entry in pool["source_map"]]
        limitations = [
            "Counts label saved list memberships for each row; they are not newly evaluated metrics or independent trials.",
            "The ordered U/F/C/S categories are disjoint within a row. False observations can overlap eligible misses and must not be added to them. Hidden alarms remain separate.",
            "No saved nearby candidate does not prove the ball was absent from the pixels. Path-choice loss can include missing output and does not certify a wrong-object emission.",
            "Object identity and center placement remain unresolved. Localization matches are not semantic identity labels, and candidate burden is not tracker accuracy.",
            "The [five hidden frames from one episode](" + PROPOSAL_REFERENCE + "#exact-extraction-and-interpretation) cannot establish robust hidden-ball performance.",
            "Non-target .20/.35 all-policy rows are reused structural-equivalence records, not newly executed uncapped trials; they were inspected only to validate saved layout and role.",
            "No pool totals, rates, rankings, cross-window/category unions, training split, method choice, operating point or quality gate are created.",
            "All prior clip reviews remain complete. No images, raw candidates, annotations, observations, paths or models were consulted by this pure formatter.",
        ]
        questions = ["Which saved loss category should a separately specified future study investigate, while distinguishing missing output from wrong-object or center-placement errors?",
                     "What independent evidence would resolve those distinctions without changing the sealed holdouts?"]
        result = {"schema_version": SUMMARY_SCHEMA, "pools": pools, "source_map": source_map,
                  "selected_method": None, "selected_operating_point": None, "quality_gate": None,
                  "membership_count_basis": "Length of each saved frame-index list within its own row only",
                  "new_scientific_aggregation": False, "new_experiment_authorized": False,
                  "limitations": limitations, "unresolved_questions": questions,
                  "checks": {"published_digests_and_provenance_validated": True, "saved_window_block_mapping_validated": True,
                             "complete_target_rows_preserved": True, "saved_memberships_reconciled": True,
                             "new_scoring_selection_or_media": False}}
        text = ["# Where the saved candidate-retention misses occur", "",
                "This is a reading of the completed ball-tracking comparison. The player-coordinate foundation is complete; possession understanding, matchup inference and defensive scoring remain later work.", "",
                "Each table preserves the same confidence and radius, all frozen settings and both cap policies. Each list cell reads **membership count: saved source-frame indices**. The saved missed total is copied, not re-evaluated. The row's source link identifies both its breakdown entry and its saved window mapping.", "",
                "- **U:** no saved candidate center met the radius at the export floor.",
                "- **F:** a nearby floor candidate was removed by confidence filtering.",
                "- **C:** a confidence-qualified nearby candidate was removed by the cap.",
                "- **S:** a retained nearby candidate did not become a matching final output; this can include missing output.", ""]
        for pool in pools:
            purpose = pool["purpose"]
            reference = "../../evaluation/" + purpose + ".json"
            text += ["## " + purpose.replace("_evaluation", "").capitalize() + " pool", ""]
            for window_id in dict.fromkeys(row["window_id"] for row in pool["rows"]):
                selected = [row for row in pool["rows"] if row["window_id"] == window_id]
                first = selected[0]
                identity = reference + "#" + first["window_identity_pointer"]
                source = reference + "#" + first["source_row_pointer"]
                text += ["### [" + window_id + "](" + identity + ")", "",
                         "Confidence [" + str(first["confidence_threshold"]) + "](" + source + "/confidence_threshold), radius [" + str(first["radius_px"]) + " source-image pixels](" + source + "/radius_px). This display radius is not a quality gate.", "",
                         "| Setting | Policy / original execution role | U memberships | F memberships | C memberships | S memberships | Saved missed total | Eligible false-observation memberships | Hidden-alarm memberships | Sources |",
                         "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
                for row in selected:
                    pointer = reference + "#" + row["source_row_pointer"]
                    identity = reference + "#" + row["window_identity_pointer"]
                    text.append("| " + " | ".join([ARM_NAMES[row["arm"]], row["retention_policy"] + " / " + row["selection_execution_role"],
                        *(_members(row, k, True) for k in PARTS), str(row["total_missed_eligible_frames"]),
                        *(_members(row, k) for k in OTHER_LISTS), "[saved row](" + pointer + "); [window mapping](" + identity + ")"]) + " |")
                text.append("")
        text += ["## Limits and unresolved questions", "", *["- " + line for line in limitations], "", *["- " + line for line in questions], ""]
        markdown = "\n".join(text)
        _require(len(markdown.encode("utf-8")) <= MAX_TEXT_BYTES, "Complete readable breakdown exceeds 64 KiB; no rows were truncated")
        return result, markdown
    except (KeyError, TypeError, IndexError, AttributeError) as error:
        raise ValueError("Missing or unsupported copied breakdown relationship") from error
