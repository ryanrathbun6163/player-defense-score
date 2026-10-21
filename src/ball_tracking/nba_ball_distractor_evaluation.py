"""Complete the fixed saved-emission comparison without retraining or tuning."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from . import nba_appearance_feature_screen as screen
from . import nba_ball_distractor_classifier as classifier
from . import nba_ball_distractor_emission_features as emission
from . import nba_ball_distractor_training as training
from . import nba_wasb_diagnostic as d

OUTPUT = "data/outputs/ball_tracking/nba/ball_distractor_training_v0_1"
PROPOSAL = "configs/ball_tracking/proposals/nba_ball_distractor_verifier_v0_1.json"


def _completed_phase(root, phase):
    """Verify immutable completed evidence without redoing scientific work."""
    output = root/OUTPUT
    path = output/("emission_completion.json" if phase == "features" else "evaluation_completion.json")
    if not path.exists():
        return None
    checked = set()

    def verify(binding):
        identity = binding["path"],binding["sha256"],binding.get("bytes")
        if identity not in checked:
            d.bound(root,binding); checked.add(identity)
        return root/binding["path"]

    def read(binding):
        return d.read_json(verify(binding))

    finished = d.read_json(path)
    d.require(finished["status"] == "completed", "Existing phase did not complete")
    training_completion = d.read_json(output/"completion.json")
    fit = read(training_completion["fit"])
    d.require(fit["status"] == "converged_fit" and fit["optimizer_calls"] == 1, "A valid single fit is required")
    protocol = read(training_completion["protocol"])
    for binding in protocol["implementation"]:
        verify(binding)
    for name in ("model","config","weights","proposed_labels"):
        verify(protocol[name])
    d.require(screen._runtime() == protocol["runtime"], "Frozen runtime changed")
    approval = read(protocol["approval"])
    for binding in approval["bindings"].values():
        verify(binding)
    proposal = read(approval["bindings"]["proposal"])
    d.require(protocol["proposed_labels"] == approval["bindings"]["proposed_labels"], "Training label authority differs")
    fit_started = d.read_json(output/"fit_started.json")
    d.require(fit_started["protocol"] == training_completion["protocol"], "Fit-start protocol differs")
    initial = read(fit_started["features"])
    emission_protocol_path = output/"emission_protocol.json"
    emission_protocol = d.read_json(emission_protocol_path)
    d.require(emission_protocol["fit"] == training_completion["fit"]
              and emission_protocol["training_protocol"] == training_completion["protocol"]
              and emission_protocol["initial_features"] == fit_started["features"]
              and emission_protocol["selection"] == proposal["authorities"]["selection"], "Emission protocol authorities differ")
    for binding in emission_protocol["implementation"]:
        verify(binding)
    verify(emission_protocol["selection"])
    emission_completion = finished if phase == "features" else d.read_json(output/"emission_completion.json")
    d.require(emission_completion["status"] == "completed" and emission_completion["fit"] == training_completion["fit"], "Completed emission fit differs")
    scores = read(emission_completion["scores"])
    manifest = read(emission_completion["features"])
    d.require(scores["fit"] == training_completion["fit"] and scores["features"] == emission_completion["features"], "Completed score authorities differ")
    d.require(manifest["identity"]["selection"] == proposal["authorities"]["selection"]
              and manifest["identity"]["context"] == d.binding(root,emission_protocol_path)
              and manifest["identity"]["implementation_sha256"] == d.digest(Path(emission.__file__).resolve()), "Completed extraction identity differs")
    d.require(manifest["emission_count"] == len(manifest["emissions"]) == emission.EXPECTED_EMISSIONS
              and set(scores["scores"]) == {r["emission_id"] for r in manifest["emissions"]}, "Completed emission/score census differs")
    if phase == "compare":
        policy_result,report = read(finished["policy"]),read(finished["report"])
        for binding in policy_result["bindings"].values():
            verify(binding)
        for binding in report["bindings"].values():
            verify(binding)
        d.require(policy_result["bindings"]["selection"] == proposal["authorities"]["selection"]
                  and policy_result["bindings"]["fit"] == training_completion["fit"]
                  and policy_result["bindings"]["scores"] == emission_completion["scores"], "Completed policy authorities differ")
        expected = {"policy":finished["policy"],"reference_scores":training_completion["reference_report"],
                    "gap_evaluation":proposal["additional_regression_authorities"]["gap_evaluation"],
                    "old790":proposal["authorities"]["old_790_report"],
                    "prior_object_assessment":proposal["additional_regression_authorities"]["prior_object_assessment"],
                    "proposal":approval["bindings"]["proposal"]}
        d.require(report["bindings"] == expected and finished["decision"] == report["decision"], "Completed comparison authorities differ")
    # Hash feature records and their saved crop/input artifacts; never decode pixels.
    for entry in initial["cache"]+manifest["emissions"]:
        for name in ("feature","crop64","input224"):
            verify(entry[name])
    return finished


def feature_pass(root):
    root = Path(root).resolve(); output = root/OUTPUT
    finished = _completed_phase(root,"features")
    if finished is not None:
        print(json.dumps(finished),flush=True)
        return finished
    completion = d.read_json(output/"completion.json")
    fit = d.read_json(d.bound(root,completion["fit"]))
    d.require(fit["status"] == "converged_fit" and fit["optimizer_calls"] == 1, "A valid single fit is required")
    original_protocol = d.read_json(d.bound(root,completion["protocol"]))
    for binding in original_protocol["implementation"]:
        d.bound(root,binding)
    d.require(screen._runtime() == original_protocol["runtime"], "Frozen runtime changed")
    approval = d.read_json(d.bound(root,original_protocol["approval"]))
    proposal = d.read_json(d.bound(root,approval["bindings"]["proposal"]))
    selection_path = d.bound(root,proposal["authorities"]["selection"])
    fit_started = d.read_json(output/"fit_started.json")
    manifest = d.read_json(d.bound(root,fit_started["features"]))
    cache = {tuple(c["crop_key"]):{k:v for k,v in c.items() if k != "crop_key"} for c in manifest["cache"]}
    protocol = {"schema_version":"nba_ball_distractor_emission_protocol/v0.1",
                "fit":completion["fit"],"training_protocol":completion["protocol"],
                "initial_features":d.binding(root,output/"feature_manifest.json"),
                "selection":proposal["authorities"]["selection"],
                "implementation":[d.binding(root,Path(module.__file__).resolve()) for module in (emission,screen,classifier)],
                "extraction": "unchanged frozen DINOv2, CPU float32 batch1 threads4; exact saved-point crops",
                "training_calls":0,"protected_source_frames":0}
    d.write_once(output/"emission_protocol.json",protocol)
    began = time.monotonic()
    model = screen.load_model(d.bound(root,original_protocol["config"]),d.bound(root,original_protocol["model"]))
    result = emission.extract(root,selection_path,model,cache,output/"emissions",
                              context=d.binding(root,output/"emission_protocol.json"),
                              progress=lambda value:print(json.dumps({"stage":"emission_features",**value}),flush=True))
    scores = classifier.score(result["features_by_emission_id"],fit)
    d.write_once(output/"emission_scores.json",{"scores":scores,"fit":completion["fit"],"features":result["manifest"],
                  "boundary":0.,"calibrated":False,"new_training_calls":0})
    finished = {"status":"completed","features":result["manifest"],"scores":d.binding(root,output/"emission_scores.json"),
                "resources":result["resources"],"feature_attempt":result["attempt"],"elapsed_seconds":time.monotonic()-began,
                "completed_at_utc":d.stamp(),"fit":completion["fit"],"new_training_calls":0}
    d.write_once(output/"emission_completion.json",finished)
    print(json.dumps(finished),flush=True)
    return finished


def compare(root):
    from . import nba_ball_distractor_policy as policy
    root = Path(root).resolve(); output = root/OUTPUT
    finished = _completed_phase(root,"compare")
    if finished is not None:
        print(json.dumps(finished),flush=True)
        return finished
    started = time.monotonic()
    training_completion = d.read_json(output/"completion.json")
    protocol = d.read_json(d.bound(root,training_completion["protocol"]))
    approval = d.read_json(d.bound(root,protocol["approval"]))
    proposal = d.read_json(d.bound(root,approval["bindings"]["proposal"]))
    authority = proposal["authorities"]
    selection = d.read_json(d.bound(root,authority["selection"]))
    feature_completion = d.read_json(output/"emission_completion.json")
    emission_scores = d.read_json(d.bound(root,feature_completion["scores"]))
    d.require(emission_scores["fit"] == training_completion["fit"], "Emission fit identity differs")
    reference_report = d.read_json(d.bound(root,training_completion["reference_report"]))
    prep, proposed = training.labels.load_proposal(root,d.bound(root,approval["bindings"]["proposed_labels"]))
    rows = classifier.reference_rows(prep,proposed)
    d.require(rows == d.read_json(output/"reference_rows.json")["rows"], "Saved reference rows differ from sealed labels")
    old_gap = d.read_json(root/"configs/ball_tracking/reviews/nba_gap_anchor_reference_evaluation_result_v0_1.json")
    d.require(old_gap["saved_selection"] == authority["selection"] and old_gap["original_790_report"] == authority["old_790_report"], "Protected reference authorities differ")
    result = policy.apply(selection,emission_scores["scores"])
    result["bindings"] = {"selection":authority["selection"],"fit":training_completion["fit"],
                          "scores":feature_completion["scores"],"implementation":d.binding(root,Path(policy.__file__).resolve())}
    d.write_once(output/"policy.json",result)
    report = policy.evaluate(result,selection,d.read_json(d.bound(root,authority["old_790_report"])),
                             d.read_json(d.bound(root,old_gap["report"])),gates=proposal["success_gates"],
                             label_rows=rows,label_scores=reference_report["reference_scores"],
                             prior_object_assessment=d.read_json(d.bound(root,old_gap["object_assessment"])))
    report["bindings"] = {"policy":d.binding(root,output/"policy.json"),"reference_scores":training_completion["reference_report"],
                           "gap_evaluation":old_gap["report"],"old790":authority["old_790_report"],
                           "prior_object_assessment":old_gap["object_assessment"],"proposal":approval["bindings"]["proposal"]}
    report["original_pre_fit_adequacy_passed"] = False
    report["decision"] = "rejected_no_adoption" if not report["all_reported_numeric_and_semantic_checks_passed"] else "provisional_coverage_and_human_review_pending"
    d.write_once(output/"evaluation_report.json",report)
    completion = {"status":"completed","decision":report["decision"],"policy":d.binding(root,output/"policy.json"),
                  "report":d.binding(root,output/"evaluation_report.json"),"elapsed_seconds":time.monotonic()-started,
                  "completed_at_utc":d.stamp(),"new_training_calls":0,"new_encoder_calls":0}
    d.write_once(output/"evaluation_completion.json",completion)
    print(json.dumps({**completion,"policy_summary":result["summary"],"checks":report["checks"],
                      "protection_cohorts":report["protection_cohorts"]}),flush=True)
    return completion


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase",choices=("features","compare"),required=True)
    args = parser.parse_args()
    (feature_pass if args.phase == "features" else compare)(Path(__file__).resolve().parents[2])
