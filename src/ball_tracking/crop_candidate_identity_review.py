"""One owned byte-verification attempt before Ryan's eight-frame identity review.

Historical scientific bodies remain opaque to the parent. Completed authority,
monitor modules are reused without overrides or mutation. No pixels are decoded.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

from . import crop_retention_output_presence as predecessor
from . import crop_retention_monitor as monitor
from . import crop_retention_resources as resources
from .development_experiments import canonical_sha256, read_json, safe_path

legacy = predecessor.legacy
_require = legacy._require
verify_binding = legacy.verify_binding
file_binding = legacy.file_binding
_absent = legacy._absent
_stat_metadata = legacy._stat_metadata
BudgetJournal = resources.BudgetJournal
ID = "rfdetr_medium_crop_candidate_identity_review_v0_1"
MANIFEST_PATH = "configs/ball_tracking/crop_retention_experiments/" + ID + ".json"
APPROVAL_PATH = "configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_identity_review_approval_v0_1.json"
PROPOSAL_PATH = "docs/ball_crop_candidate_identity_review_proposal.md"
PROPOSAL_SHA = "4f3ae4ce372599e10b8768611ccccd8cab61ede09de28a90be20da6251a395da"
SCOPE_PATH = "configs/ball_tracking/proposals/" + ID + ".json"
SCOPE_SHA = "e767f943291464609c1567439910a0f092d9d63943da5932d4ba53cd8c9a7c49"
IMPLEMENTATION_DIR = "data/outputs/t/ci_impl_efeefd58f680"
CERTIFICATE_PATH = IMPLEMENTATION_DIR + "/implementation_validation.json"
POST_COMMIT_PATH = IMPLEMENTATION_DIR + "/post_commit_execution_checkpoint.json"
FROZEN_HISTORY_PATH = IMPLEMENTATION_DIR + "/frozen_history.json"
FROZEN_HISTORY_SHA = "d536ae6f1615c59c89664918c5b983a9e8a01d28237959a6328000c722d96b78"
PREDECESSOR_COMPLETION_PATH = predecessor.IMPLEMENTATION_DIR + "/output_presence_completion_efeefd58f680.json"
BASE_COMMIT = "efeefd58f6801ffe5de106a48f8dad1e835b9647"
OUTPUT_ROOT = predecessor.OUTPUT_ROOT
OUTPUT_DIR = "review/candidate_identity_review_v0_1"
OUTPUT_NAMES = ("verification.json", "pending_review.json", "review_guide.md", "provenance.json")
OUTPUTS = [OUTPUT_DIR + "/" + name for name in OUTPUT_NAMES]
UNIT_KEY = "post-review-candidate-identity:verify:"
PREFIX_COUNT = 3121
PREFIX_ATTEMPTS = 60
PREFIX_TIP = "7a990a3fd2b86502dd6245d6d08d2d17c75abe4534bad8d6cc323aa9c43ba701"
PREDECESSOR_ATTEMPT = "395c3038fe7440a1b59912df476c3dd7"
PREDECESSOR_RESULT_SHA = "00ef943fdac730dedba1fe779f32ed5c1a61663cd915e52352eee25cd57ebbb5"
USED_SECONDS = 3362.7889999999825
MAX_UNIT_SECONDS = 120
MAX_GUIDE_BYTES = 65536
HASH_CHUNK_BYTES = 1024 * 1024
KNOWN_FAILURES = predecessor.KNOWN_FAILURES
FRAMES = (300, 301, 302, 304, 308, 319, 320, 324)
WINDOW_ID = "possession_003_frames_0300_0324_representative_evaluation_development_v0_2"
ROLES = ("unmarked_source", "native_tt_cap20_overlay")
SETTING = {"arm": "history_edge_tight_cost_tight", "policy": "cap20", "confidence_threshold": .01,
           "localization_radius_source_px": 10.0, "native_view": "view_0"}
# Copied from the approved metadata scope; never discover scientific inputs.
SCIENTIFIC_INPUTS = [
  {
    "frame_index": 300,
    "unmarked_source": {
      "path": "data/outputs/ball_tracking/crop_motion_factorial/rfdetr_medium_crop_motion_factorial_v0_1/review/9a2a78ec54725d766a7179680fd698a2/possession_003_frames_0300_0324_representative_evaluation_development_v0_2/confidence_0.2/unmarked_source/frame_000300.png",
      "sha256": "83f66dd364e17e786bc9332d1a6680dafff755d2d3a000b198c29358fb60885a"
    },
    "native_tt_cap20_overlay": {
      "path": "data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/review/windows/possession_003_frames_0300_0324_representative_evaluation_development_v0_2/view_0/frame_000300.png",
      "sha256": "dbd73c0a853c125e285d464488318de4058e2fa8e34d564a61cccf6e3313ead1",
      "size_bytes": 3131375
    }
  },
  {
    "frame_index": 301,
    "unmarked_source": {
      "path": "data/outputs/ball_tracking/crop_motion_factorial/rfdetr_medium_crop_motion_factorial_v0_1/review/9a2a78ec54725d766a7179680fd698a2/possession_003_frames_0300_0324_representative_evaluation_development_v0_2/confidence_0.2/unmarked_source/frame_000301.png",
      "sha256": "58204cc756cced65d25e50143418ddca5418cb70a431394a303172e98ef2b88b"
    },
    "native_tt_cap20_overlay": {
      "path": "data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/review/windows/possession_003_frames_0300_0324_representative_evaluation_development_v0_2/view_0/frame_000301.png",
      "sha256": "1f526b2959b4387123a11c62b6654cca918cde68aa825f47686d7b3cfe56017a",
      "size_bytes": 3045831
    }
  },
  {
    "frame_index": 302,
    "unmarked_source": {
      "path": "data/outputs/ball_tracking/crop_motion_factorial/rfdetr_medium_crop_motion_factorial_v0_1/review/9a2a78ec54725d766a7179680fd698a2/possession_003_frames_0300_0324_representative_evaluation_development_v0_2/confidence_0.2/unmarked_source/frame_000302.png",
      "sha256": "7f3a3aa7f6968b0fe7bf7d26969f2592554beba868ddd99f756599db6319ff54"
    },
    "native_tt_cap20_overlay": {
      "path": "data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/review/windows/possession_003_frames_0300_0324_representative_evaluation_development_v0_2/view_0/frame_000302.png",
      "sha256": "a9cda0c820bd2e3ad4d4deb8ba4032007e0c639bf7738ccb30f86bc3ceeec67b",
      "size_bytes": 3090512
    }
  },
  {
    "frame_index": 304,
    "unmarked_source": {
      "path": "data/outputs/ball_tracking/crop_motion_factorial/rfdetr_medium_crop_motion_factorial_v0_1/review/9a2a78ec54725d766a7179680fd698a2/possession_003_frames_0300_0324_representative_evaluation_development_v0_2/confidence_0.2/unmarked_source/frame_000304.png",
      "sha256": "4073903b152ef4883ad21e02d6da3cac47bf3827cad08dbf596d90b7a39308d3"
    },
    "native_tt_cap20_overlay": {
      "path": "data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/review/windows/possession_003_frames_0300_0324_representative_evaluation_development_v0_2/view_0/frame_000304.png",
      "sha256": "4145004f13ed4641f8daeae0d8fbcf9a8d2191b6d8ce9c909f9c0b6bdf8c18a8",
      "size_bytes": 3059573
    }
  },
  {
    "frame_index": 308,
    "unmarked_source": {
      "path": "data/outputs/ball_tracking/crop_motion_factorial/rfdetr_medium_crop_motion_factorial_v0_1/review/9a2a78ec54725d766a7179680fd698a2/possession_003_frames_0300_0324_representative_evaluation_development_v0_2/confidence_0.2/unmarked_source/frame_000308.png",
      "sha256": "b20cf1b540e13429fca1fbf2e75642cc8decb4e54bf5811f88ffe6ff637def9e"
    },
    "native_tt_cap20_overlay": {
      "path": "data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/review/windows/possession_003_frames_0300_0324_representative_evaluation_development_v0_2/view_0/frame_000308.png",
      "sha256": "e5a10f63f7f32b1c39ffbd4de09acc8e708f44136cb185a8e0f80b4760657fa9",
      "size_bytes": 3074979
    }
  },
  {
    "frame_index": 319,
    "unmarked_source": {
      "path": "data/outputs/ball_tracking/crop_motion_factorial/rfdetr_medium_crop_motion_factorial_v0_1/review/9a2a78ec54725d766a7179680fd698a2/possession_003_frames_0300_0324_representative_evaluation_development_v0_2/confidence_0.2/unmarked_source/frame_000319.png",
      "sha256": "0fbdb28bafec5b4add46c5712aef20d0c14fe00f3718d0f4fc491bcecd5f79a9"
    },
    "native_tt_cap20_overlay": {
      "path": "data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/review/windows/possession_003_frames_0300_0324_representative_evaluation_development_v0_2/view_0/frame_000319.png",
      "sha256": "2205ac3773c3ddc056a3a1ceb56e00722a6d2c8ab5d698d04d48f8cbedbc6787",
      "size_bytes": 3072188
    }
  },
  {
    "frame_index": 320,
    "unmarked_source": {
      "path": "data/outputs/ball_tracking/crop_motion_factorial/rfdetr_medium_crop_motion_factorial_v0_1/review/9a2a78ec54725d766a7179680fd698a2/possession_003_frames_0300_0324_representative_evaluation_development_v0_2/confidence_0.2/unmarked_source/frame_000320.png",
      "sha256": "674943028e1bdbb5ab340ace5d564c419803c266509cda4735fcf1a6f06a78b1"
    },
    "native_tt_cap20_overlay": {
      "path": "data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/review/windows/possession_003_frames_0300_0324_representative_evaluation_development_v0_2/view_0/frame_000320.png",
      "sha256": "430488219092c68efe391fc841bc354776e37bccd973528dc784f218782df274",
      "size_bytes": 3091241
    }
  },
  {
    "frame_index": 324,
    "unmarked_source": {
      "path": "data/outputs/ball_tracking/crop_motion_factorial/rfdetr_medium_crop_motion_factorial_v0_1/review/9a2a78ec54725d766a7179680fd698a2/possession_003_frames_0300_0324_representative_evaluation_development_v0_2/confidence_0.2/unmarked_source/frame_000324.png",
      "sha256": "b6f9bb4b83a6a3f39ee5963b895226d4d3f9f4578eeac2d9e75b20b9d1d47874"
    },
    "native_tt_cap20_overlay": {
      "path": "data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/review/windows/possession_003_frames_0300_0324_representative_evaluation_development_v0_2/view_0/frame_000324.png",
      "sha256": "45e392c62b972fcaa773c7b99eae00b058afe58b836a2c331b5ba9d5468f385f",
      "size_bytes": 3120588
    }
  }
]
AUTHORITY_PATHS = {"proposal": PROPOSAL_PATH, "scope": SCOPE_PATH, "authorization": APPROVAL_PATH,
                   "frozen_history": FROZEN_HISTORY_PATH, "predecessor_manifest": predecessor.MANIFEST_PATH,
                   "predecessor_completion": PREDECESSOR_COMPLETION_PATH}
AUTHORITY_FIELDS = tuple(AUTHORITY_PATHS)
MANIFEST_FIELDS = {"schema_version", "study_id", "output_root", "output_dir", "permitted_stages", "unit_key",
                   "maximum_unit_seconds", "maximum_guide_bytes", "scientific_inputs", *AUTHORITY_FIELDS,
                   "implementation_validation", "post_commit_checkpoint", "selected_method", "selected_operating_point", "quality_gate"}
MONITOR_EVIDENCE = {*predecessor.MONITOR_EVIDENCE,
                    *(predecessor.IMPLEMENTATION_DIR + "/" + name for name in
                      ("validate.py", "check_helper_race.py", "helper_race_check_01.json"))}
SEMANTIC_SOURCES = ("src/ball_tracking/crop_retention_review.py",
                    "src/ball_tracking/prepare_detection_visual_review.py")
CHECKS = {"input_hash_unchanged": True, "source_authority_unchanged": True,
          "preserved_metadata_and_receipts_unchanged": True, "output_integrity_verified": True,
          "only_sixteen_declared_pngs_read": True, "png_bytes_verified_without_decode": True,
          "no_inference_scoring_selection_media_or_semantic_labels": True,
          "new_budget_distinct_from_consumed_attempts": True, "validated_monitor_used": True,
          "clean_post_commit_checkpoint_verified": True}
_scan_record = predecessor._scan_record
_successful_completion = predecessor._successful_completion
VERIFICATION_SCHEMA = "ball_crop_candidate_identity_review_verification/v0.1"
LEDGER_SCHEMA = "ball_crop_candidate_identity_review_ledger/v0.1"

def _pair(value):
    _require(type(value) is dict and set(value) == {"path", "sha256"}
             and type(value["path"]) is str and type(value["sha256"]) is str
             and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]), "Invalid exact metadata binding")
    return value


def _read_bound(root, binding, limit=32 * 1024 * 1024):
    """Only callers' fixed administrative paths may reach this bounded reader."""
    _pair(binding)
    allowed = {*AUTHORITY_PATHS.values(), CERTIFICATE_PATH,
               OUTPUT_ROOT + "/attempts/" + PREDECESSOR_ATTEMPT + ".result.json"}
    receipt = re.fullmatch(re.escape(OUTPUT_ROOT) + r"/attempts/[0-9a-f]{32}\.result\.json", binding["path"])
    _require(binding["path"] in allowed or receipt is not None,
             "Administrative reader cannot follow scientific or undeclared pointers")
    path = safe_path(root, binding["path"])
    before = _stat_metadata(path)
    _require(before["size_bytes"] <= limit, "Administrative receipt exceeds its byte bound")
    with path.open("rb") as stream:
        payload = stream.read(limit + 1)
    _require(len(payload) <= limit and _stat_metadata(path) == before
             and hashlib.sha256(payload).hexdigest() == binding["sha256"],
             "Administrative receipt changed or differs from its binding")
    return json.loads(payload)


def _spec_sha256(manifest):
    return canonical_sha256({key: value for key, value in manifest.items()
                             if key != "implementation_validation"})


def _input_rows(inputs):
    """Flatten only the fixed sixteen bindings, retaining frame and viewing order."""
    _require(inputs == SCIENTIFIC_INPUTS, "Only the sixteen approved image bindings are permitted")
    _require(type(inputs) is list and len(inputs) == len(FRAMES)
             and tuple(row["frame_index"] for row in inputs) == FRAMES, "Review frame order changed")
    result = []
    for row in inputs:
        _require(set(row) == {"frame_index", *ROLES}, "Unexpected image row fields")
        for role in ROLES:
            binding = row[role]
            _require(type(binding) is dict and set(binding) in ({"path", "sha256"}, {"path", "sha256", "size_bytes"}),
                     "Unexpected image binding fields")
            _pair({key: binding[key] for key in ("path", "sha256")})
            if "size_bytes" in binding:
                _require(type(binding["size_bytes"]) is int and binding["size_bytes"] > 0, "Invalid expected PNG size")
            result.append({"frame_index": row["frame_index"], "role": role, "expected": deepcopy(binding)})
    _require(len({row["expected"]["path"] for row in result}) == 16, "Repeated image binding")
    return result


def _validate_scope(scope):
    _require(type(scope) is dict and scope["schema_version"] == "ball_crop_candidate_identity_review_scope/v0.1"
             and scope["status"] == "proposed_not_authorized" and scope["prepared_at_commit"] == BASE_COMMIT
             and scope["proposal_path"] == PROPOSAL_PATH and scope["window_id"] == WINDOW_ID
             and scope["setting"] == SETTING and scope["scientific_inputs"] == SCIENTIFIC_INPUTS,
             "Frozen identity-review scope differs")
    _input_rows(scope["scientific_inputs"])
    _require(scope["selection_source"]["frame_indices"] == list(FRAMES)
             and scope["selection_source"]["source_row_pointer"] == "/pools/0/rows/16"
             and scope["selection_source"]["field"] == "present_nonmatching_current_output",
             "Fixed reviewed membership selection changed")
    worker = scope["proposed_worker"]
    _require(worker["unit"] == UNIT_KEY and worker["maximum_attempts"] == 1
             and worker["maximum_charged_seconds"] == MAX_UNIT_SECONDS
             and worker["output_root"] == OUTPUT_ROOT + "/" + OUTPUT_DIR, "Worker scope changed")
    human = scope["human_review"]
    _require(human["reviewer"] == "Ryan" and human["sequence"] == list(ROLES)
             and human["identity_choices"] == ["ball", "another_object", "uncertain"]
             and human["ball_center_choices"] == ["plausible", "clearly_displaced", "cannot_judge"]
             and human["other_identity_center_value"] == "not_applicable"
             and human["initial_row_status"] == "pending"
             and human["source_first_not_blind"] is True and human["parent_pixel_inspection_authorized"] is False
             and human["preserve_localization_outcome"] is True,
             "Human review instructions or parent access changed")
    _require(all(scope[key] is None for key in ("selected_method", "selected_operating_point", "quality_gate")),
             "This case study cannot select a method or quality gate")
    return scope


def _validate_manifest(manifest):
    _require(type(manifest) is dict and set(manifest) == MANIFEST_FIELDS
             and manifest["schema_version"] == "ball_crop_candidate_identity_review_experiment/v0.1"
             and manifest["study_id"] == ID and manifest["output_root"] == OUTPUT_ROOT
             and manifest["output_dir"] == OUTPUT_DIR and manifest["permitted_stages"] == ["verify"]
             and manifest["unit_key"] == UNIT_KEY and manifest["maximum_unit_seconds"] == MAX_UNIT_SECONDS
             and manifest["maximum_guide_bytes"] == MAX_GUIDE_BYTES
             and manifest["scientific_inputs"] == SCIENTIFIC_INPUTS
             and manifest["post_commit_checkpoint"] == POST_COMMIT_PATH, "Unsupported candidate-identity scope")
    _require(all(manifest[k] is None for k in ("selected_method", "selected_operating_point", "quality_gate")),
             "Candidate-identity cannot choose a method or quality gate")
    for key, path in AUTHORITY_PATHS.items():
        _require(_pair(manifest[key])["path"] == path, "Unexpected authority path: " + key)
    _require(manifest["proposal"] == {"path": PROPOSAL_PATH, "sha256": PROPOSAL_SHA}
             and manifest["scope"] == {"path": SCOPE_PATH, "sha256": SCOPE_SHA}
             and manifest["frozen_history"] == {"path": FROZEN_HISTORY_PATH, "sha256": FROZEN_HISTORY_SHA},
             "Exact approved proposal, scope and completed prefix are required")
    _require(_pair(manifest["implementation_validation"])["path"] == CERTIFICATE_PATH,
             "Unexpected current validation certificate")


def _validate_implementation(root, manifest):
    certificate = _read_bound(root, manifest["implementation_validation"])
    _require(certificate["schema_version"] == "ball_crop_candidate_identity_review_implementation_validation/v0.1",
             "Unsupported candidate-identity validation certificate")
    for key in ("focused_tests_passed", "full_suite_passed", "independent_static_review_passed",
                "integrity_tests_passed", "monitor_design_check_passed"):
        _require(certificate.get(key) is True, "Candidate-identity implementation validation is incomplete: " + key)
    _require(certificate["manifest_spec_sha256"] == _spec_sha256(manifest)
             and certificate["authority_sha256"] == {key: manifest[key]["sha256"] for key in AUTHORITY_FIELDS},
             "Candidate-identity validation is bound to different authority/specification")
    required = {path.relative_to(root).as_posix() for folder in ("src", "tests")
                for path in (root / folder).rglob("*.py")} | {"requirements.txt"}
    rows = certificate["source_bindings"]
    legacy._unique_bindings(rows)
    _require({row["path"] for row in rows} == required, "Current validation must cover the complete current source inventory")
    for row in rows:
        verify_binding(root, row)
        legacy.original._git(root, "ls-files", "--error-unmatch", "--", row["path"])
    evidence = certificate["evidence_bindings"]
    legacy._unique_bindings(evidence)
    _require(bool(evidence), "Validation evidence is missing")
    for row in evidence:
        _require(row["path"] in MONITOR_EVIDENCE or row["path"].startswith(IMPLEMENTATION_DIR + "/"),
                 "Validation evidence points outside the approved administrative directories")
        safe_path(root, row["path"])
        verify_binding(root, row)
    return certificate


def _post_commit_checkpoint(root, manifest, commit):
    """An absent release gate is a hard stop before history/root scans or dispatch."""
    path = safe_path(root, POST_COMMIT_PATH)
    _require(path.is_file(), "The post-commit execution checkpoint is absent; execution remains blocked")
    checkpoint = monitor._read_record(path)
    _require(checkpoint["schema_version"] == "ball_crop_candidate_identity_review_execution_checkpoint/v0.1"
             and type(commit) is str and re.fullmatch(r"[0-9a-f]{40}", commit) and commit != BASE_COMMIT
             and checkpoint["head"] == commit and checkpoint["branch"] == "codex/ball-detector-baseline"
             and checkpoint["manifest"] == file_binding(root, root / MANIFEST_PATH)
             and checkpoint["implementation_validation"] == manifest["implementation_validation"]
             and checkpoint["manifest_spec_sha256"] == _spec_sha256(manifest)
             and checkpoint["preserved_prefix_tip_sha256"] == PREFIX_TIP,
             "Post-commit checkpoint does not bind this exact execution")
    for key in ("execution_authorized", "clean", "index_empty", "validated_sources_unchanged"):
        _require(checkpoint.get(key) is True, "Post-commit execution prerequisite is missing: " + key)
    _require(subprocess.run(["git", "merge-base", "--is-ancestor", BASE_COMMIT, commit], cwd=root).returncode == 0,
             "Candidate-identity must descend from the completed output-presence commit")
    return checkpoint


def _metadata(root, manifest_path, require_clean=True):
    root = Path(root).resolve()
    path = Path(manifest_path).absolute()
    _require(path == root / MANIFEST_PATH, "Unexpected candidate-identity manifest path")
    commit = legacy.original._clean_checkpoint(root) if require_clean else legacy.original._git(root, "rev-parse", "HEAD")
    manifest = read_json(safe_path(root, MANIFEST_PATH))
    _validate_manifest(manifest)
    checkpoint = _post_commit_checkpoint(root, manifest, commit) if require_clean else None
    for key in AUTHORITY_FIELDS:
        verify_binding(root, manifest[key])
    scope = _validate_scope(_read_bound(root, manifest["scope"]))
    approval = _read_bound(root, manifest["authorization"])
    _require(approval["schema_version"] == "ball_crop_candidate_identity_review_approval/v0.1"
             and approval["approved_by"].lower() == "ryan" and approval["proposal"] == manifest["proposal"]
             and approval["scope"] == manifest["scope"]
             and approval["reviewer"] == "Ryan" and approval["human_review_requires_successful_byte_verification"] is True
             and approval["maximum_new_attempts"] == 1 and approval["maximum_unit_seconds"] == MAX_UNIT_SECONDS
             and approval["approved_operations"] == ["verify_png_byte_bindings", "prepare_pending_human_review"],
             "Exact candidate-identity approval is required")
    for key in ("implementation_authorized", "focused_validation_authorized", "full_regression_authorized",
                "conditional_execution_authorized", "separate_clean_commit_required", "responsive_monitor_policy_adopted",
                "human_review_authorized"):
        _require(approval.get(key) is True, "Missing authorization: " + key)
    for key in ("parent_scientific_body_access_authorized", "automatic_scientific_retry_authorized",
                "parent_pixel_inspection_authorized", "new_model_inference_authorized", "scoring_authorized",
                "rendering_authorized", "git_mutations_authorized"):
        _require(approval.get(key) is False, "Approval expands scope: " + key)
    # Historical metadata only; never invoke any consumed predecessor runner.
    historical = predecessor._metadata(root, root / predecessor.MANIFEST_PATH, False)
    history = _read_bound(root, manifest["frozen_history"])
    _require(history["schema_version"] == "ball_crop_candidate_identity_review_frozen_history/v0.1"
             and history["head"] == BASE_COMMIT and history["prefix_count"] == PREFIX_COUNT
             and history["prefix_tip_sha256"] == PREFIX_TIP and history["prefix_attempts"] == PREFIX_ATTEMPTS
             and history["prefix_successes"] == 56 and set(history["known_failures"]) == KNOWN_FAILURES
             and history["limits"] == historical["limits"] and history["scientific_bodies_read_or_hashed"] is False
             and math.isclose(history["consumed_seconds"], USED_SECONDS, abs_tol=1e-7, rel_tol=0),
             "Wrong completed-history preservation authority")
    prior = _read_bound(root, manifest["predecessor_completion"])
    _require(prior["schema_version"] == "player_defense_score_output_presence_completion/v0.1"
             and prior["success"] is True and prior["execution_commit"] == BASE_COMMIT
             and prior["attempt_id"] == PREDECESSOR_ATTEMPT and prior["completion_event_chain_sha256"] == PREFIX_TIP
             and prior["authorized_output_presence_attempts_remaining"] == 0
             and prior["authorized_prior_recovery_attempts_remaining"] == 0
             and prior["worker_result_binding_from_verified_return"] == {
                 "path": OUTPUT_ROOT + "/attempts/" + PREDECESSOR_ATTEMPT + ".result.json", "sha256": PREDECESSOR_RESULT_SHA},
             "The consumed successful output-presence attempt is required")
    _require({key: prior["summary_transport"][key] for key in ("path", "sha256")} ==
             {key: scope["selection_source"][key] for key in ("path", "sha256")},
             "Selection pointer differs from the predecessor's verified transport")
    certificate = _validate_implementation(root, manifest) if require_clean else None
    if require_clean:
        for name in (MANIFEST_PATH, *AUTHORITY_PATHS.values()):
            if not name.startswith("data/"):
                legacy.original._git(root, "ls-files", "--error-unmatch", "--", name)
        for name in SEMANTIC_SOURCES:
            _require(legacy.original._git(root, "rev-parse", BASE_COMMIT + ":" + name)
                     == legacy.original._git(root, "rev-parse", commit + ":" + name),
                     "Historical candidate-identity semantics changed: " + name)
    _require(subprocess.run(["git", "check-ignore", "-q", "--", OUTPUT_ROOT + "/" + OUTPUTS[0]], cwd=root).returncode == 0,
             "Study outputs must remain ignored")
    return {"root": root, "manifest_path": path, "manifest": manifest, "commit": commit,
            "spec_sha256": _spec_sha256(manifest), "output_root": safe_path(root, OUTPUT_ROOT),
            "limits": historical["limits"], "history": history, "scope": scope, "certificate": certificate,
            "policy": monitor.monitoring_policy(historical["limits"], .25), "checkpoint": checkpoint}


def _remaining_seconds(journal):
    return min(MAX_UNIT_SECONDS - journal.consumed(UNIT_KEY),
               journal.limits["maximum_cumulative_seconds"] - journal.consumed())


def _closed_prefix(journal):
    _require(len(journal.events) >= PREFIX_COUNT and journal.events[PREFIX_COUNT - 1]["sha256"] == PREFIX_TIP,
             "Exact completed 3121-event prefix is required")
    old_starts, _ = predecessor._closed_prefix(journal)
    frozen = journal.events[:PREFIX_COUNT]
    starts = {e["attempt_id"]: e for e in frozen if e["kind"] == "started"}
    ends = {e["attempt_id"]: e for e in frozen if e["kind"] == "finished"}
    _require(len(starts) == len(ends) == PREFIX_ATTEMPTS and set(starts) == set(ends)
             and set(starts) - set(old_starts) == {PREDECESSOR_ATTEMPT}
             and {aid for aid, e in ends.items() if not e["success"]} == KNOWN_FAILURES
             and sum(e["success"] is True for e in ends.values()) == 56
             and starts[PREDECESSOR_ATTEMPT]["unit_key"] == predecessor.UNIT_KEY
             and frozen[-1] == ends[PREDECESSOR_ATTEMPT]
             and math.isclose(sum(e["elapsed_seconds"] for e in ends.values()), USED_SECONDS, abs_tol=1e-7, rel_tol=0),
             "Completed output-presence history or budgets changed")
    policy = monitor.monitoring_policy(journal.limits, .25)
    _successful_completion(ends[PREDECESSOR_ATTEMPT], {"limits": journal.limits, "policy": policy},
                           starts[PREDECESSOR_ATTEMPT]["reserved_seconds"])
    _require(ends[PREDECESSOR_ATTEMPT]["worker_result"] == {
        "path": "attempts/" + PREDECESSOR_ATTEMPT + ".result.json", "sha256": PREDECESSOR_RESULT_SHA},
        "Successful precursor receipt changed")
    return starts, ends


class IdentityJournal(BudgetJournal):
    """One new 120-second role, never a renewal of either consumed diagnostic."""
    def reserve(self, unit_key, selection_unit):
        _require(unit_key == UNIT_KEY and selection_unit is False, "Unknown candidate-identity reservation")
        _require(len(self.events) == PREFIX_COUNT, "Study cannot retry or adopt a suffix")
        _closed_prefix(self)
        _require(all(a["finished"] is not None for a in self._attempts().values()), "An attempt is still active")
        remaining = _remaining_seconds(self)
        _require(remaining > 0, "Candidate-identity budget is exhausted")
        aid = uuid.uuid4().hex
        self.append("started", attempt_id=aid, unit_key=UNIT_KEY, selection_unit=False, reserved_seconds=remaining)
        resources._write_new(self.root / "attempts" / (aid + ".reservation.json"), {"event_sha256": self.events[-1]["sha256"]})
        return aid, remaining


def verify_history(root, context, phase="before"):
    _require(phase in ("before", "worker", "completed"), "Unknown study history phase")
    root, output = Path(root).resolve(), context["output_root"]
    history = context["history"]
    journal = BudgetJournal(output, context["limits"])
    starts, ends = _closed_prefix(journal)
    _require(history["prior_output_presence_completion"] == ends[PREDECESSOR_ATTEMPT], "Preserved completion changed")
    rows = history["raw_event_bindings"]
    legacy._unique_bindings(rows)
    _require(len(rows) == PREFIX_COUNT, "Incomplete frozen raw history")
    for index, b in enumerate(rows):
        _require(b["path"] == OUTPUT_ROOT + f"/resource_events/{index:08d}.json", "Noncontiguous prefix binding")
        verify_binding(root, b)
    seals = history["administrative_attempt_bindings"]
    legacy._unique_bindings(seals)
    expected = {OUTPUT_ROOT + "/attempts/" + aid + suffix for aid in starts
                for suffix in (".reservation.json", ".completion.json")}
    expected |= {OUTPUT_ROOT + "/attempts/" + aid + ".result.json" for aid in starts if ends[aid]["success"]}
    _require({b["path"] for b in seals} == expected, "Administrative receipt inventory changed")
    for b in seals:
        verify_binding(root, b)
    for aid in starts:
        for suffix, event in ((".reservation.json", starts[aid]), (".completion.json", ends[aid])):
            _require(read_json(safe_path(root, OUTPUT_ROOT + "/attempts/" + aid + suffix)) == {"event_sha256": event["sha256"]},
                     "Preserved attempt seal changed")
        if ends[aid]["success"]:
            receipt = next(b for b in seals if b["path"] == OUTPUT_ROOT + "/attempts/" + aid + ".result.json")
            _require(ends[aid]["worker_result"] == {"path": "attempts/" + aid + ".result.json", "sha256": receipt["sha256"]},
                     "Preserved successful receipt identity changed")
        else:
            _require(ends[aid]["worker_result"] is None, "Failed attempt acquired a result")
            _absent(output / "attempts" / (aid + ".result.json"))
    suffix = journal.events[PREFIX_COUNT:]
    attempts = journal._attempts()
    new = {aid: value for aid, value in attempts.items() if aid not in starts}
    if phase == "before":
        _require(not suffix and not new and all(row["finished"] is not None for row in attempts.values()),
                 "Candidate-identity requires the untouched completed prefix; no retry or unknown suffix")
        return journal
    _require(len(new) == 1 and suffix and suffix[0]["kind"] == "started", "Exactly one owned candidate-identity attempt is required")
    aid, attempt = next(iter(new.items()))
    start, end = attempt["start"], attempt["finished"]
    expected_seconds = min(MAX_UNIT_SECONDS, context["limits"]["maximum_cumulative_seconds"] - USED_SECONDS)
    _require(start["unit_key"] == UNIT_KEY and start["selection_unit"] is False
             and math.isclose(start["reserved_seconds"], expected_seconds, rel_tol=0, abs_tol=1e-7)
             and all(event["attempt_id"] == aid for event in suffix)
             and sum(event["kind"] == "started" for event in suffix) == 1,
             "Unknown candidate-identity role or renewed reservation")
    _require(read_json(safe_path(root, OUTPUT_ROOT + "/attempts/" + aid + ".reservation.json")) == {"event_sha256": start["sha256"]},
             "Candidate-identity reservation seal changed")
    policy_sha = resources._digest(context["policy"])
    policy_path = OUTPUT_ROOT + "/attempts/" + aid + ".monitoring_policy.json"
    _require(monitor._read_record(safe_path(root, policy_path)) == {"policy": context["policy"], "sha256": policy_sha},
             "Monitor policy differs from the adopted responsive policy")
    samples = [event for event in suffix if event["kind"] == "sample"]
    latest = None
    for sample in samples:
        _require(sample["monitoring_policy_sha256"] == policy_sha
                 and all(type(sample[key]) is int and sample[key] >= 0
                         for key in ("memory_bytes", "scanner_memory_bytes", "free_disk_bytes"))
                 and type(sample["elapsed_seconds"]) in (int, float) and math.isfinite(sample["elapsed_seconds"])
                 and 0 <= sample["elapsed_seconds"] <= start["reserved_seconds"]
                 and sample["scanner_memory_bytes"] <= sample["memory_bytes"] <= context["policy"]["maximum_combined_rss_bytes"]
                 and sample["free_disk_bytes"] >= context["policy"]["effective_minimum_free_disk_bytes"],
                 "Candidate-identity sample violated safety or policy bounds")
        scan = sample["scan"]
        if scan is None:
            _require(latest is None and sample["output_bytes"] is None, "Missing scan cannot replace a completed measurement")
        else:
            _scan_record(scan, policy_sha)
            _require(sample["output_bytes"] == scan["output_bytes"] <= context["policy"]["maximum_output_bytes"],
                     "Resource sample differs from complete accounting")
            if latest is not None:
                _require(scan == latest or scan["requested_at"] >= latest["completed_at"], "Accounting results moved backwards or overlapped")
            latest = scan
    if phase == "worker":
        _require(aid == os.environ.get("BALL_RETENTION_ATTEMPT_ID") and end is None
                 and all(event["kind"] in ("started", "sample") for event in suffix), "Worker does not own the sole active reservation")
    else:
        _require(end is not None and suffix[-1] == end, "Incomplete or failed candidate-identity attempt cannot release a review")
        _successful_completion(end, context, start["reserved_seconds"])
        counts = [sample["output_bytes"] for sample in samples if sample["output_bytes"] is not None]
        _require(samples and counts and end["monitor_samples"] == len(samples)
                 and end["peak_worker_memory_bytes"] >= max(sample["memory_bytes"] for sample in samples)
                 and end["maximum_output_bytes"] >= max(counts)
                 and end["minimum_free_disk_bytes"] <= min(sample["free_disk_bytes"] for sample in samples)
                 and end["worker_result"]["path"] == "attempts/" + aid + ".result.json"
                 and end["monitoring_policy_path"] == "attempts/" + aid + ".monitoring_policy.json",
                 "Completed candidate-identity attempt understates its evidence or names another receipt")
        _require(read_json(safe_path(root, OUTPUT_ROOT + "/attempts/" + aid + ".completion.json")) == {"event_sha256": end["sha256"]},
                 "Candidate-identity completion seal changed")
    return journal


def _input_metadata(root, inputs, rows):
    expected = {row["expected"]["path"]: row["expected"] for row in _input_rows(inputs)}
    _require(type(rows) is list and len(rows) == 16 and {row["path"] for row in rows} == set(expected),
             "Frozen metadata must cover exactly sixteen scientific inputs")
    result = {}
    for row in rows:
        _require(set(row) == {"path", "size_bytes", "mtime_ns", "device", "inode"}
                 and all(type(row[key]) is int and row[key] >= 0 for key in row if key != "path"),
                 "Invalid frozen image metadata")
        actual = _stat_metadata(safe_path(root, row["path"]))
        _require(actual == {key: row[key] for key in row if key != "path"}
                 and actual["size_bytes"] > 0, "Scientific input metadata changed: " + row["path"])
        if "size_bytes" in expected[row["path"]]:
            _require(actual["size_bytes"] == expected[row["path"]]["size_bytes"], "Expected image size changed")
        result[row["path"]] = actual
    return result


def _preserved_metadata(root, context, phase="before", allow_outputs=False):
    """Only lstat/traversal of scientific paths; never open/hash their bodies."""
    _require(phase in ("before", "worker", "completed"), "Unknown preservation phase")
    root, output = Path(root).resolve(), context["output_root"]
    history = context["history"]
    _input_metadata(root, SCIENTIFIC_INPUTS, history["scientific_input_metadata"])
    rows = history["preserved_files"]
    old_files = {row["path"] for row in rows}
    old_dirs = set(history["preserved_directories"])
    _require(len(old_files) == len(rows) and len(old_dirs) == len(history["preserved_directories"]), "Repeated preservation metadata")
    for row in rows:
        _require(_stat_metadata(safe_path(root, row["path"], OUTPUT_ROOT)) ==
                 {key: row[key] for key in ("size_bytes", "mtime_ns", "device", "inode")},
                 "Preserved evidence metadata changed: " + row["path"])
    for name in old_dirs:
        path = safe_path(root, name) if name == OUTPUT_ROOT else safe_path(root, name, OUTPUT_ROOT)
        _require(path.is_dir(), "Preserved directory disappeared")
    legacy._protected_metadata(root, context["history"]["protection"])
    aid = os.environ.get("BALL_RETENTION_ATTEMPT_ID") if phase == "worker" else context.get("completed_attempt_id")
    for name in history["preserved_absent_paths"]:
        if phase != "before" and name == OUTPUT_ROOT + "/supervisor.lock":
            continue
        if allow_outputs and name == OUTPUT_ROOT + "/" + OUTPUT_DIR:
            continue
        _absent(safe_path(root, name))
    if phase == "before":
        _require(aid is None, "Before phase cannot adopt an attempt")
    else:
        _require(type(aid) is str and re.fullmatch(r"[0-9a-f]{32}", aid), "Invalid candidate-identity attempt identity")
    if phase == "worker":
        owner = monitor._read_record(output / "supervisor.lock")
        _require(owner["pid"] == int(os.environ["BALL_RETENTION_PARENT_PID"]), "Worker supervisor ownership changed")
    elif phase == "completed":
        _absent(output / "supervisor.lock")
    destination = output / OUTPUT_DIR
    if not allow_outputs:
        _absent(destination)
    permitted_files = {OUTPUT_ROOT + "/" + path for path in OUTPUTS} if allow_outputs else set()
    permitted_dirs = {OUTPUT_ROOT + "/" + OUTPUT_DIR} if allow_outputs else set()
    if aid:
        base = OUTPUT_ROOT + "/attempts/" + aid
        permitted_files |= {base + suffix for suffix in (".reservation.json", ".completion.json", ".log", ".start",
                                                            ".result.json", ".monitoring_policy.json")}
        permitted_dirs |= {base + ".temp", base + ".monitor"}
    if phase == "worker":
        permitted_files.add(OUTPUT_ROOT + "/supervisor.lock")

    def dynamic(name):
        if phase == "before":
            return False
        relative = name.removeprefix(OUTPUT_ROOT + "/resource_events/")
        event = re.fullmatch(r"(\d{8})\.json", relative)
        if event is None and phase == "worker":
            event = re.fullmatch(r"\.pending_(\d{8})\.json_[0-9a-f]{32}", relative)
        if name.startswith(OUTPUT_ROOT + "/resource_events/") and event:
            return int(event[1]) >= PREFIX_COUNT
        prefix = OUTPUT_ROOT + "/attempts/" + aid + ".monitor/"
        if name.startswith(prefix):
            leaf = name[len(prefix):]
            if leaf == "owned.start" or re.fullmatch(r"\d{6}\.(request|response)\.json", leaf):
                return True
            return phase == "worker" and re.fullmatch(r"\.pending_\d{6}\.(request|response)\.json_[0-9a-f]{32}", leaf) is not None
        return False

    def fail(error):
        raise error

    for folder, directories, files in os.walk(output, onerror=fail):
        for name in directories:
            relative = (Path(folder) / name).relative_to(root).as_posix()
            safe_path(root, relative)
            _require(relative in old_dirs | permitted_dirs, "Unexpected evidence directory: " + relative)
        for name in files:
            relative = (Path(folder) / name).relative_to(root).as_posix()
            safe_path(root, relative)
            _require(relative in old_files | permitted_files or dynamic(relative), "Unexpected evidence file: " + relative)


def _run_bounded_supervised(context, command):
    return monitor.run_supervised(context["output_root"], UNIT_KEY, command, context["limits"],
                                  cwd=context["root"], selection_unit=False, poll_seconds=.25,
                                  require_result=True, journal_factory=IdentityJournal)


def _verify_image_bytes(root, inputs, expected_metadata):
    """Hash only the declared PNG bytes in an owned worker; never decode pixels."""
    _require(bool(os.environ.get("BALL_RETENTION_ATTEMPT_ID")), "Scientific access requires an owned worker")
    root = Path(root).resolve()
    frozen = _input_metadata(root, inputs, expected_metadata)
    records, stopped = [], False
    for row in _input_rows(inputs):
        record = {**row, "actual": None, "metadata_before": None, "metadata_after": None,
                  "success": False, "error": None}
        if stopped:
            record["error"] = "not_attempted_after_prior_failure"
            records.append(record)
            continue
        try:
            binding = row["expected"]
            path = safe_path(root, binding["path"])
            before = _stat_metadata(path)
            record["metadata_before"] = before
            _require(before == frozen[binding["path"]], "Image metadata changed before hashing")
            digest, size = hashlib.sha256(), 0
            with path.open("rb") as stream:
                while size <= before["size_bytes"]:
                    chunk = stream.read(min(HASH_CHUNK_BYTES, before["size_bytes"] + 1 - size))
                    if not chunk:
                        break
                    digest.update(chunk)
                    size += len(chunk)
            record["actual"] = {"path": binding["path"], "size_bytes": size, "sha256": digest.hexdigest()}
            after = _stat_metadata(safe_path(root, binding["path"]))
            record["metadata_after"] = after
            _require(before == after and size == before["size_bytes"], "Image changed during hashing")
            _require(digest.hexdigest() == binding["sha256"], "Image hash differs from its approved binding")
            record["success"] = True
        except (OSError, ValueError) as error:
            record["error"] = (type(error).__name__ + ": " + str(error))[:500]
            stopped = True
        records.append(record)
    return {"schema_version": VERIFICATION_SCHEMA, "success": not stopped,
            "pixels_decoded": False, "images": records}


def _validate_verification(value, inputs, expected_metadata):
    _require(type(value) is dict and set(value) == {"schema_version", "success", "pixels_decoded", "images"}
             and value["schema_version"] == VERIFICATION_SCHEMA and value["success"] is True
             and value["pixels_decoded"] is False, "Image verification did not succeed without decoding")
    expected_rows = _input_rows(inputs)
    rows = value["images"]
    frozen = {row["path"]: {key: row[key] for key in row if key != "path"} for row in expected_metadata}
    _require(type(rows) is list and len(rows) == 16 and len(frozen) == 16, "Incomplete image verification receipt")
    for row, expected in zip(rows, expected_rows):
        _require(set(row) == {"frame_index", "role", "expected", "actual", "metadata_before", "metadata_after", "success", "error"}
                 and {key: row[key] for key in expected} == expected and row["success"] is True and row["error"] is None,
                 "Image receipt identity or success changed")
        binding = expected["expected"]
        _require(row["actual"] == {"path": binding["path"], "sha256": binding["sha256"],
                                  "size_bytes": frozen[binding["path"]]["size_bytes"]}
                 and row["metadata_before"] == row["metadata_after"] == frozen[binding["path"]],
                 "Image receipt does not verify the exact frozen bytes")
    return value


def _pending_ledger(scope):
    """Prepare questions only. No identity or center judgment is supplied by code."""
    _validate_scope(scope)
    return {"schema_version": LEDGER_SCHEMA, "scope": {"path": SCOPE_PATH, "sha256": SCOPE_SHA},
            "window_id": WINDOW_ID, "setting": deepcopy(SETTING), "required_reviewer": "Ryan",
            "source_first_not_blind": True, "selection_source": deepcopy(scope["selection_source"]),
            "rows": [{"frame_index": row["frame_index"],
                      "image_bindings": {role: deepcopy(row[role]) for role in ROLES},
                      "prior_localization_outcome": "present_nonmatching_current_output",
                      "status": "pending", "reviewer": None, "actual_response": None, "recorded_at_utc": None,
                      "emitted_candidate_index": None, "candidate_identity": None,
                      "ball_center": None, "note": None} for row in scope["scientific_inputs"]],
            "selected_method": None, "selected_operating_point": None, "quality_gate": None}


def _review_guide(root, scope):
    _validate_scope(scope)
    lines = ["# P003 eight-frame candidate identity review", "",
             "All eight decisions are pending. Ryan supplies the judgments; the assistant does not inspect pixels.",
             "For each frame open the unmarked source first, then the TT/cap20 overlay. This is not blind or independent review.",
             "The overlay already contains reference geometry and localization outcomes. Its header names the emitted #candidate_index; amber alt # markers are not emissions.",
             "Record identity: ball / another object / uncertain. If ball, record center: plausible / clearly displaced / cannot judge; otherwise not applicable.",
             "An unreadable candidate index remains null. If markings or pixels are insufficient, retain uncertainty; do not add frames, crops, video or new renderings.",
             "The prior raw 10-source-pixel localization result remains unchanged. These correlated selected failures establish neither frequency nor cause, method rank, tracking quality or generalization.",
             "Use only these sixteen images. Ordinary viewer display and zoom are permitted. Do not reopen scientific manifests, observations, candidates, annotations, reports or videos.",
             "Record the actual response, reviewer and receipt time; preserve corrections as new records. Completed package approval supplies no frame-specific answer.", ""]
    for row in scope["scientific_inputs"]:
        frame = row["frame_index"]
        lines.extend([f"## Frame {frame} — pending", ""])
        for role in ROLES:
            path = (Path(root).resolve() / row[role]["path"]).as_posix()
            label = "1. Unmarked source" if role == ROLES[0] else "2. TT/cap20 overlay"
            lines.append(f"- [{label}](<{path}>)")
        lines.append("")
    text = "\n".join(lines)
    _require(0 < len(text.encode("utf-8")) <= MAX_GUIDE_BYTES, "Review guide exceeds its transport bound")
    return text


def _worker(root, manifest_path):
    resources.wait_for_supervisor()
    root = Path(root).resolve()
    context = _metadata(root, manifest_path, True)
    journal = verify_history(root, context, "worker")
    aid = os.environ["BALL_RETENTION_ATTEMPT_ID"]
    result_path = safe_path(root, OUTPUT_ROOT + "/attempts/" + aid + ".result.json")
    _require(Path(os.environ["BALL_RETENTION_RESULT_PATH"]).resolve() == result_path, "Worker receipt is outside its reservation")
    _absent(result_path)
    _preserved_metadata(root, context, "worker")
    verification = _verify_image_bytes(root, SCIENTIFIC_INPUTS, context["history"]["scientific_input_metadata"])
    destination = safe_path(root, OUTPUT_ROOT + "/" + OUTPUT_DIR)
    _absent(destination)
    destination.mkdir()
    verification_bytes = legacy._json_bytes(verification)
    _require(len(verification_bytes) <= monitor.WORKER_RECEIPT_LIMIT, "Verification evidence exceeds its bound")
    legacy._write_new(destination / "verification.json", verification_bytes)
    # A mismatch remains durable failed evidence and must never release images.
    _validate_verification(verification, SCIENTIFIC_INPUTS, context["history"]["scientific_input_metadata"])
    ledger = _pending_ledger(context["scope"])
    guide = _review_guide(root, context["scope"])
    ledger_bytes, guide_bytes = legacy._json_bytes(ledger), guide.encode("utf-8")
    _require(len(ledger_bytes) <= monitor.WORKER_RECEIPT_LIMIT, "Pending ledger exceeds its bound")
    legacy._write_new(destination / "pending_review.json", ledger_bytes)
    legacy._write_new(destination / "review_guide.md", guide_bytes)
    provenance = {"schema_version": "ball_crop_candidate_identity_review_provenance/v0.1",
                  "study_id": ID, "unit_key": UNIT_KEY, "attempt_id": aid, "commit": context["commit"],
                  "spec_sha256": context["spec_sha256"], "authority_bindings": {k: context["manifest"][k] for k in AUTHORITY_FIELDS},
                  "implementation_validation": context["manifest"]["implementation_validation"],
                  "post_commit_checkpoint": file_binding(root, root / POST_COMMIT_PATH),
                  "source_bindings": context["certificate"]["source_bindings"], "scientific_inputs": SCIENTIFIC_INPUTS,
                  "preserved_prefix_count": PREFIX_COUNT, "preserved_prefix_tip_sha256": PREFIX_TIP,
                  "active_reservation_sha256": journal._attempts()[aid]["start"]["sha256"],
                  "monitoring_policy_sha256": resources._digest(context["policy"]), "checks": CHECKS,
                  "review_bindings": [file_binding(root, destination / name) for name in OUTPUT_NAMES[:3]],
                  "acceptance": "Requires successful sealed completion and preservation; every human judgment remains pending."}
    provenance_bytes = legacy._json_bytes(provenance)
    _require(len(provenance_bytes) <= monitor.WORKER_RECEIPT_LIMIT, "Provenance exceeds its bound")
    legacy._write_new(destination / "provenance.json", provenance_bytes)
    authored = dict(zip(OUTPUT_NAMES, (verification_bytes, ledger_bytes, guide_bytes, provenance_bytes)))
    _require(all((destination / name).read_bytes() == raw for name, raw in authored.items()), "Authored administrative output differs")
    end = _metadata(root, manifest_path, True)
    _require(end["commit"] == context["commit"] and end["spec_sha256"] == context["spec_sha256"], "Authority changed during worker execution")
    verify_history(root, end, "worker")
    _preserved_metadata(root, end, "worker", allow_outputs=True)
    artifacts = [file_binding(root, destination / name) for name in OUTPUT_NAMES]
    _require(all(b["sha256"] == hashlib.sha256(authored[Path(b["path"]).name]).hexdigest() for b in artifacts), "Authored artifact changed")
    result = {"schema_version": "ball_crop_candidate_identity_review_worker_result/v0.1",
              "stage": "verify", "unit_key": UNIT_KEY, "attempt_id": aid, "commit": context["commit"],
              "spec_sha256": context["spec_sha256"], "artifacts": artifacts,
              "artifact_metadata": [{"path": b["path"], **_stat_metadata(root / b["path"])} for b in artifacts],
              "scientific_inputs": SCIENTIFIC_INPUTS, "checks": CHECKS,
              "verification": verification, "pending_review": ledger,
              "guide_payload": {"text": guide, "size_bytes": len(guide_bytes), "sha256": hashlib.sha256(guide_bytes).hexdigest()}}
    payload = legacy._json_bytes(result)
    _require(len(payload) <= monitor.WORKER_RECEIPT_LIMIT, "Worker receipt exceeds interface bound")
    legacy._write_new(result_path, payload)
    _require(result_path.read_bytes() == payload, "Worker receipt differs")
    return {"worker_result_written": True, "attempt_id": aid, "completion_pending": True}


def _completed_result(root, context, event):
    root = Path(root).resolve()
    journal = verify_history(root, context, "completed")
    _require(journal.events[-1] == event, "Supervisor completion differs from its persisted event")
    aid = event["attempt_id"]
    context = {**context, "completed_attempt_id": aid}
    _preserved_metadata(root, context, "completed", allow_outputs=True)
    binding = {"path": OUTPUT_ROOT + "/" + event["worker_result"]["path"], "sha256": event["worker_result"]["sha256"]}
    _require(binding["path"] == OUTPUT_ROOT + "/attempts/" + aid + ".result.json", "Wrong candidate-identity receipt path")
    result = _read_bound(root, binding, monitor.WORKER_RECEIPT_LIMIT)
    _require(set(result) == {"schema_version", "stage", "unit_key", "attempt_id", "commit", "spec_sha256",
                             "artifacts", "artifact_metadata", "scientific_inputs", "checks", "verification", "pending_review", "guide_payload"}
             and result["schema_version"] == "ball_crop_candidate_identity_review_worker_result/v0.1"
             and result["stage"] == "verify" and result["unit_key"] == UNIT_KEY and result["attempt_id"] == aid
             and result["commit"] == context["commit"] and result["spec_sha256"] == context["spec_sha256"]
             and result["scientific_inputs"] == SCIENTIFIC_INPUTS and result["checks"] == CHECKS
             and all(type(value) is bool for value in result["checks"].values()),
             "Candidate-identity worker receipt does not certify this exact execution")
    _validate_verification(result["verification"], SCIENTIFIC_INPUTS, context["history"]["scientific_input_metadata"])
    _require(result["pending_review"] == _pending_ledger(context["scope"]), "Pending ledger contains invented or altered answers")
    expected = {OUTPUT_ROOT + "/" + path for path in OUTPUTS}
    legacy._unique_bindings(result["artifacts"])
    _require(len(result["artifacts"]) == len(OUTPUTS) and {row["path"] for row in result["artifacts"]} == expected,
             "Candidate-identity artifact identities changed")
    rows = result["artifact_metadata"]
    _require(type(rows) is list and len(rows) == len(OUTPUTS) and {row["path"] for row in rows} == expected, "Incomplete artifact metadata")
    for row in rows:
        _require(set(row) == {"path", "size_bytes", "mtime_ns", "device", "inode"}
                 and _stat_metadata(safe_path(root, row["path"])) == {key: row[key] for key in row if key != "path"},
                 "Administrative artifact metadata changed after worker verification")
    payload = result["guide_payload"]
    _require(type(payload) is dict and set(payload) == {"text", "size_bytes", "sha256"}
             and type(payload["text"]) is str and type(payload["size_bytes"]) is int
             and payload["text"] == _review_guide(root, context["scope"]), "Review guide or transport changed")
    guide_bytes = payload["text"].encode("utf-8")
    bodies = {"verification.json": legacy._json_bytes(result["verification"]),
              "pending_review.json": legacy._json_bytes(result["pending_review"]), "review_guide.md": guide_bytes}
    for name, raw in bodies.items():
        path = OUTPUT_ROOT + "/" + OUTPUT_DIR + "/" + name
        _require(next(row["sha256"] for row in result["artifacts"] if row["path"] == path) == hashlib.sha256(raw).hexdigest()
                 and next(row["size_bytes"] for row in rows if row["path"] == path) == len(raw),
                 "Returned administrative transport differs from its artifact")
    _require(0 < len(guide_bytes) <= MAX_GUIDE_BYTES and len(guide_bytes) == payload["size_bytes"]
             and hashlib.sha256(guide_bytes).hexdigest() == payload["sha256"], "Invalid review guide transport")
    # Only transport and metadata are inspected by the parent; no PNG body reads.
    return {"stage": "verify", "successful_workers": 1, "commit": context["commit"],
            "worker_result": binding, "completion_event_sha256": event["sha256"], "artifacts": result["artifacts"],
            "verification": result["verification"], "pending_review": result["pending_review"], "review_guide": payload["text"],
            "human_review_pending": True, "new_model_calls": 0, "scoring_executed": False, "media_decoded": False,
            "parent_pixel_inspection_authorized": False,
            "selected_method": None, "selected_operating_point": None, "quality_gate": None}


def run_identity_review(root, manifest_path, dry_run=False):
    # Even dry-run requires the real post-commit gate. Tests use fabricated metadata.
    context = _metadata(root, manifest_path, True)
    verify_history(root, context, "before")
    _preserved_metadata(root, context, "before")
    if dry_run:
        return {"dry_run": True, "metadata_only": True, "scientific_inputs_verified": False,
                "spec_sha256": context["spec_sha256"], "post_commit_checkpoint_verified": True}
    command = [sys.executable, "-B", "-m", "src.ball_tracking.crop_candidate_identity_review",
               "--manifest", str(context["manifest_path"]), "--repository-root", str(context["root"]), "--worker"]
    event = _run_bounded_supervised(context, command)
    end_context = _metadata(root, manifest_path, True)
    _require(end_context["commit"] == context["commit"] and end_context["spec_sha256"] == context["spec_sha256"],
             "Candidate-identity authority changed before parent review release")
    return _completed_result(root, end_context, event)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--stage", choices=("verify",), default="verify")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    _require(not (args.worker and args.dry_run), "An owned worker cannot use dry-run authority")
    root = args.repository_root.resolve()
    manifest = root / args.manifest
    result = _worker(root, manifest) if args.worker else run_identity_review(root, manifest, args.dry_run)
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
