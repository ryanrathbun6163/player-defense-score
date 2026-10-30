"""Artificial-fixture orchestration; the real-data entry point stays disabled.

No file readers, detector imports, scientific journal or release path exist here.
The approved first stage can exercise an in-memory, hash-bound protocol. A later
reviewed release must supply exact real input/output inventories and ownership
before real execution can be implemented. Synthetic tags are provenance, not a
security claim that arbitrary caller-supplied bytes depict artificial content.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import re

from .annotations import BallAnnotationSet
from .detections import BallDetectionRun
from .development_experiments import require_digest
from . import crop_cross_detector_corroboration as selector
from . import crop_cross_detector_corroboration_evaluation as evaluation

ID = "rfdetr_yolo_crop_corroboration_v0_1"
PHASES = ("selection", "evaluation", "review", "complete", "failed")
ROLES = {
    "selection": frozenset(("rf_candidates", "yolo_candidates")),
    "evaluation": frozenset(("annotations", "saved_controls")),
    "review": frozenset(("source_png",)),
    "complete": frozenset(), "failed": frozenset(),
}
MAX_RETURN_BYTES = 512 * 1024
MAX_OUTPUT_BYTES = 4 * 1024**3


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _name(value):
    _require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_./-]+", value)
             and not value.startswith(("/", "."))
             and all(p not in ("", ".", "..") for p in value.split("/")),
             "Expected a declared relative artifact name")
    return value


def _json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")


def _binding(name, payload):
    return {"path": name, "size_bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest()}


@dataclass(frozen=True)
class FixtureArtifact:
    """Immutable artificial input bytes with one explicit role and binding."""

    name: str
    role: str
    payload: bytes
    sha256: str

    def __post_init__(self):
        _name(self.name)
        _require(self.role in set().union(*ROLES.values()), "Unknown fixture role")
        _require(type(self.payload) is bytes, "Fixture payload must be immutable bytes")
        require_digest(self.sha256, "fixture digest", 64)
        _require(hashlib.sha256(self.payload).hexdigest() == self.sha256,
                 "Fixture input digest differs")

    @classmethod
    def from_json(cls, name, role, value):
        raw = _json_bytes(value)
        return cls(name, role, raw, hashlib.sha256(raw).hexdigest())


class OutputSink:
    """Create-only in-memory artificial outputs with exact name/size bounds."""

    def __init__(self, limits, maximum_bytes=MAX_OUTPUT_BYTES):
        _require(isinstance(limits, dict) and limits, "Exact output limits required")
        for name, limit in limits.items():
            _name(name)
            _require(type(limit) is int and 0 < limit <= MAX_OUTPUT_BYTES,
                     "Invalid per-output bound")
        _require(type(maximum_bytes) is int and 0 < maximum_bytes <= MAX_OUTPUT_BYTES,
                 "Invalid aggregate output bound")
        self._limits = dict(limits)
        self._payloads = {}
        self._maximum = maximum_bytes
        self._closed = False

    def write(self, name, payload):
        _name(name)
        _require(not self._closed and name in self._limits, "Output is closed or undeclared")
        _require(name not in self._payloads, "Create-only output already exists")
        _require(type(payload) is bytes and len(payload) <= self._limits[name],
                 "Output exceeds its declared bound")
        _require(sum(map(len, self._payloads.values())) + len(payload) <= self._maximum,
                 "Aggregate output allowance exceeded")
        self._payloads[name] = payload
        return _binding(name, payload)

    def json(self, name, value):
        return self.write(name, _json_bytes(value))

    def verify(self, binding):
        _require(isinstance(binding, dict) and set(binding) == {"path", "size_bytes", "sha256"},
                 "Exact output binding required")
        name = _name(binding["path"])
        _require(name in self._payloads and _binding(name, self._payloads[name]) == binding,
                 "Sealed output bytes differ")

    def decode(self, binding):
        self.verify(binding)
        return json.loads(self._payloads[binding["path"]])

    def complete(self):
        _require(not self._closed and set(self._payloads) == set(self._limits),
                 "Incomplete or already closed artificial output inventory")
        self._closed = True
        return [_binding(n, self._payloads[n]) for n in sorted(self._payloads)]


class PhaseAccess:
    """Role allowlists; no implicit filesystem/network/provenance-pointer reads."""

    def __init__(self, artifacts, window_ids, *, fixture_id):
        _require(isinstance(fixture_id, str) and fixture_id.startswith("synthetic:"),
                 "Explicit artificial fixture provenance required")
        _require(isinstance(window_ids, (tuple, list)) and len(window_ids) == 6
                 and len(set(window_ids)) == 6, "Exactly six distinct windows required")
        for ident in window_ids:
            _name(ident)
            _require("/" not in ident, "Window ID cannot be an artifact path")
        rows = list(artifacts)
        _require(all(isinstance(a, FixtureArtifact) for a in rows)
                 and len({a.name for a in rows}) == len(rows), "Duplicate or invalid fixture inputs")
        self._inputs = {a.name: a for a in rows}
        self._window_ids = tuple(window_ids)
        self._frozen = None
        self._sink = None
        self._phase = "selection"
        self.fixture_id = fixture_id
        self.access_log = []

    @property
    def phase(self):
        return self._phase

    def _verify_frozen(self):
        if self._frozen is not None:
            for binding in self._frozen:
                self._sink.verify(binding)

    def read(self, name):
        _name(name)
        _require(name in self._inputs, "Undeclared fixture input")
        value = self._inputs[name]
        _require(value.role in ROLES[self._phase], "Input role forbidden in this phase")
        self._verify_frozen()
        _require(hashlib.sha256(value.payload).hexdigest() == value.sha256,
                 "Bound fixture bytes changed")
        self.access_log.append({"phase": self._phase, "name": name, "role": value.role})
        return value.payload

    def json(self, name):
        # Embedded paths remain inert JSON values.
        return json.loads(self.read(name))

    def freeze(self, bindings, sink):
        _require(self._phase == "selection" and isinstance(sink, OutputSink),
                 "Selection can freeze exactly once")
        expected = {f"selection/{w}/observations.json" for w in self._window_ids}
        _require(isinstance(bindings, list) and len(bindings) == 6
                 and {b["path"] for b in bindings} == expected,
                 "All six exact selections must freeze before evaluation")
        for binding in bindings:
            sink.verify(binding)
        self._frozen, self._sink = deepcopy(bindings), sink
        self._phase = "evaluation"

    def begin_review(self):
        _require(self._phase == "evaluation", "Review follows evaluation only")
        self._verify_frozen()
        self._phase = "review"

    def close(self):
        _require(self._phase in ("evaluation", "review"), "Unfinished or closed fixture phase")
        self._verify_frozen()
        self._phase = "complete"

    def fail(self):
        self._phase = "failed"


def _windows(windows):
    _require(isinstance(windows, (tuple, list)) and len(windows) == 6,
             "The artificial protocol requires six complete windows")
    _require(len({w["window_id"] for w in windows}) == 6, "Duplicate window")
    _require(Counter(w["purpose"] for w in windows) ==
             Counter({p: 3 for p in evaluation.POOLS}), "Exactly three windows per separate pool")
    for w in windows:
        _name(w["window_id"])
        _require(w["window_id"].startswith("synthetic_") and "/" not in w["window_id"],
                 "Artificial protocol requires synthetic window IDs")
        start, end = w["start_frame_index"], w["end_frame_index"]
        _require(type(start) is int and type(end) is int and start >= 0 and end - start == 24,
                 "Each window must contain exactly 25 source frames")


def run_synthetic_comparison(windows, access, sink, commit, *, render=None, progress=None):
    """Exercise six-window phase ordering with caller-supplied artificial bytes.

    Inputs are named rf/<id>, yolo/<id>, labels/<id>, controls/<id>.
    Controls contain observations, reports, observation_references and
    report_references keyed by the three saved arm names. They are copied and
    bound, never selected or scored anew. Optional render receives keyword
    window/run/labels/observations_by_arm/reports_by_arm/access/sink.
    No real-file loader or scientific dispatcher is available in this stage.
    """
    _windows(windows)
    require_digest(commit, "artificial implementation commit", 40)
    _require(isinstance(access, PhaseAccess) and isinstance(sink, OutputSink)
             and access.phase == "selection"
             and tuple(w["window_id"] for w in windows) == access._window_ids,
             "Owned artificial access and output context required")
    runs, observations, frozen, comparisons, review_data = {}, {}, [], [], []
    try:
        for window in windows:
            ident = window["window_id"]
            rf = BallDetectionRun.from_mapping(access.json("rf/" + ident))
            yolo = BallDetectionRun.from_mapping(access.json("yolo/" + ident))
            _require(rf.source_video.to_dict() == window["source_video"]
                     and rf.possession_id == window["possession_id"]
                     and rf.window.to_dict() == {"start_frame_index": window["start_frame_index"],
                                                 "end_frame_index": window["end_frame_index"]},
                     "Candidate run differs from declared window")
            obs = selector.select_candidates(rf, yolo, commit, progress=progress)
            observations[ident], runs[ident] = obs, (rf, yolo)
            frozen.append(sink.json(f"selection/{ident}/observations.json", obs))
        access.freeze(frozen, sink)
        for window in windows:
            ident = window["window_id"]
            rf, yolo = runs[ident]
            labels = BallAnnotationSet.from_mapping(access.json("labels/" + ident))
            controls = access.json("controls/" + ident)
            original_controls = _json_bytes(controls)
            arms = tuple(evaluation.CONTROLS)
            _require(set(controls) == {"observations", "reports", "observation_references", "report_references"}
                     and all(set(controls[k]) == set(arms) for k in controls),
                     "Exactly three bound saved controls required")
            obs_by_arm, reports = {}, {}
            for arm in arms:
                obs_by_arm[arm] = evaluation.verify_saved_observations(
                    {"observations": controls["observations"][arm]},
                    controls["observation_references"][arm], rf)
                reports[arm] = evaluation.verify_saved_report(
                    controls["reports"][arm], controls["report_references"][arm],
                    obs_by_arm[arm], rf, labels)
            obs_by_arm[selector.ARM] = observations[ident]
            reports[selector.ARM] = evaluation.evaluate_selection(
                labels, rf, observations[ident], commit, yolo_run=yolo)
            _require(_json_bytes(controls) == original_controls, "Saved controls were changed")
            comparison = evaluation.compare_window(window, reports[selector.ARM],
                {a: reports[a] for a in arms}, obs_by_arm)
            comparisons.append(comparison)
            sink.json(f"evaluation/{ident}.json", {"new_report": reports[selector.ARM],
                                                 "comparison": comparison})
            review_data.append((window, rf, labels, obs_by_arm, reports))
        pools = [evaluation.aggregate_pool([c for c in comparisons if c["purpose"] == p], p)
                 for p in evaluation.POOLS]
        for pool in pools:
            sink.json(f"evaluation/{pool['purpose']}.json", pool)
        if render is not None:
            access.begin_review()
            for window, rf, labels, obs_by_arm, reports in review_data:
                render(window=window, run=rf, labels=labels,
                       observations_by_arm={a: obs_by_arm[a] for a in (evaluation.TOP, selector.ARM)},
                       reports_by_arm={a: reports[a] for a in (evaluation.TOP, selector.ARM)},
                       access=access, sink=sink)
        summary = {"schema_version": "ball_crop_corroboration_artificial_completion/v0.1",
                   "fixture_id": access.fixture_id, "artificial_only": True,
                   "window_ids": [w["window_id"] for w in windows],
                   "selection_bindings": frozen,
                   "interpretation": evaluation.development_interpretation(pools),
                   "review_rendered": render is not None,
                   "scientific_execution": False, "journal_events": 0,
                   "selected_method": None, "selected_operating_point": None, "quality_gate": None}
        _require(len(_json_bytes(summary)) <= MAX_RETURN_BYTES, "Bounded fixture return exceeded")
        access.close()
        sink.json("summary.json", summary)
        artifacts = sink.complete()
        result = {"summary": summary, "artifacts": artifacts,
                  "access_log": deepcopy(access.access_log)}
        _require(len(_json_bytes(result)) <= MAX_RETURN_BYTES,
                 "Bounded complete fixture return exceeded")
        return result
    except BaseException:
        access.fail()
        raise


def run_study(*args, **kwargs):
    """Unconditionally refuse real execution before opening even a manifest."""
    raise PermissionError("Real corroboration execution is not released: an exact separately "
                          "approved inventory, clean implementation certificate, consumed-attempt "
                          "protection and new release receipt are required. Stage 1 is artificial only.")


def main(argv=None):
    # Do not interpret a path, environment flag or synthetic token as a release.
    return run_study(argv=argv)


if __name__ == "__main__":
    main()
