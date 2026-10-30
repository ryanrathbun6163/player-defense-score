"""Approved mixed-provenance recovery; never repeat the 175 completed crops."""
from __future__ import annotations

import argparse
import copy
import json
import time
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from . import yolo_crop_experiment as original
from . import yolo_crop_candidates as simple
from .annotations import SourceVideo
from .detections import BallDetectionRun, ModelProvenance
from .development_experiments import bound_file, canonical_sha256, closed, read_json, safe_path, sha256_file
from .temporal_experiment import _tracked, clean_commit, file_binding, git, persist_once, spec_digest
from .tiled_candidates import crop_views

OUTPUT_ROOT = original.OUTPUT_ROOT + "/recovery_v0_2"
ORIGINAL_COMMIT = "116e3ed9cb4113521fa8c93adf4a100fea4dc0ec"
PRIOR_COMMIT = original.PRIOR_COMMIT
PROPOSAL_SHA = "b0a6a6ee81711d59f35b6360ce6c9595fce80c1625d45ff407683958a65612fe"
ROLE = "assembly_view_only_not_actual_inference_commit_for_all_units"
SCHEMA = "ball_yolo_crop_observations/v0.2"
CANDIDATE_SCHEMA = "ball_yolo_crop_candidates/v0.2"
PROVENANCE_FIELDS = ("assembly_code_commit", "model_code_commit_role", "inference_inventory_sha256", "actual_inference_commits")
ARMS, SelectorConfig, experiment_grid = simple.ARMS, simple.SelectorConfig, simple.experiment_grid
load_saved_control = original.load_saved_control
FIELDS = {"schema_version", "experiment_id", "recovery_proposal", "original_experiment", "authorization", "runtime", "output_root", "selected_operating_point", "quality_gate"}


def unit(window, frame, view):
    return {"window_id": window["window_id"], "possession_id": window["possession_id"], "frame_index": frame,
            "view_id": view["view_id"], "view_ordinal": view["ordinal"]}


def key(record):
    return record["window_id"], record["frame_index"], record["view_id"]


def _units(proposal):
    return [unit(w, f, v) for w in proposal["windows"] for f in range(w["start_frame_index"], w["end_frame_index"]+1) for v in crop_views()]


def load_manifest(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    safe_path(root, path.relative_to(root).as_posix(), "configs/ball_tracking/yolo_crop_experiments")
    m = closed(read_json(path), FIELDS, "recovery manifest")
    if (m["schema_version"] != "ball_yolo_crop_recovery_experiment/v0.2" or m["experiment_id"] != "yolo11x_crop_recovery_v0_2"
            or m["recovery_proposal"]["sha256"] != PROPOSAL_SHA or m["output_root"] != OUTPUT_ROOT
            or m["selected_operating_point"] is not None or m["quality_gate"] is not None):
        raise ValueError("Recovery manifest differs from approved contract")
    recovery = read_json(bound_file(root, m["recovery_proposal"], "configs/ball_tracking/proposals"))
    if (recovery["schema_version"] != "ball_yolo_crop_recovery_proposal/v0.2" or recovery["recovery_output_root"] != OUTPUT_ROOT
            or recovery["original_experiment"] != m["original_experiment"] or recovery["original_runtime"] != m["runtime"]
            or recovery["original_execution_commit"] != ORIGINAL_COMMIT):
        raise ValueError("Recovery original provenance differs")
    approval = closed(read_json(bound_file(root, m["authorization"], "configs/ball_tracking/reviews")),
        {"schema_version", "proposal", "approved_by", "user_statement", "approved_at_utc", "implementation_and_recovery_authorized", "git_authorization"}, "recovery authorization")
    if (approval["schema_version"] != "ball_yolo11x_crop_recovery_approval/v0.2" or approval["proposal"] != m["recovery_proposal"]
            or approval["approved_by"] != "Ryan" or approval["implementation_and_recovery_authorized"] is not True
            or not isinstance(approval["user_statement"], str) or not approval["user_statement"].strip()
            or approval["git_authorization"] != {"stage": False, "commit": False, "push": False, "pull_request": False, "merge": False}):
        raise ValueError("Exact recovery authorization is required")
    original_path = bound_file(root, m["original_experiment"], "configs/ball_tracking/yolo_crop_experiments")
    old_m, p = original.load_manifest(root, original_path)
    if (spec_digest(old_m) != recovery["original_experiment_spec_sha256"] or old_m["runtime"] != m["runtime"]
            or p["windows"] != recovery["windows"] or p["crop_views"] != recovery["crop_views"]
            or p["sealed_holdouts"] != recovery["sealed_holdouts"] or recovery["holdout_release_authorized"] is not False):
        raise ValueError("Original approved comparison changed")
    design = recovery["design_document"]
    if sha256_file(safe_path(root, design["path"], "docs")) != design["sha256"]:
        raise ValueError("Recovery design changed")
    return m, p, recovery, old_m


def preserved_bindings(recovery):
    return [*[r["checkpoint"] for r in recovery["completed_crop_units_reuse_without_inference"]],
            *[b for r in recovery["preserved_attempt_receipts"] for b in (r["start"], r["result"])],
            *[b for r in recovery["preserved_preparation_receipts"] for b in (r["start"], r["result"])],
            *recovery["preserved_candidate_files"], *recovery["preserved_selector_files"]]


def validate_partition(root, recovery, p):
    expected = _units(p)
    old, missing = recovery["completed_crop_units_reuse_without_inference"], recovery["missing_crop_units_only_allowed_new_inference"]
    old_units = [{k:r[k] for k in expected[0]} for r in old]
    if (old_units != expected[:175] or missing != expected[175:] or len(expected) != 600
            or len({key(r) for r in old+missing}) != 600 or any(r["actual_inference_commit"] != ORIGINAL_COMMIT for r in old)
            or len(recovery["preserved_attempt_receipts"]) != 177 or len(recovery["preserved_preparation_receipts"]) != 2
            or len(recovery["preserved_candidate_files"]) != 1 or len(recovery["preserved_selector_files"]) != 27):
        raise ValueError("Exact 175/425 recovery partition or receipts changed")
    bindings = preserved_bindings(recovery)
    if len(bindings) != 561 or len({b["path"] for b in bindings}) != 561:
        raise ValueError("Recovery must preserve exactly 561 distinct original files")
    for b in bindings:
        bound_file(root, b, original.OUTPUT_ROOT)
    expected_files = {b["path"] for b in bindings}
    existing = {f.relative_to(root).as_posix() for f in safe_path(root, original.OUTPUT_ROOT).rglob("*")
                if f.is_file() and not f.is_relative_to(safe_path(root, OUTPUT_ROOT))}
    if existing != expected_files:
        raise ValueError("Original partial-run files were added, removed or changed")
    return {key(r):r for r in old}, {key(r):r for r in missing}


def preflight(root, path, *, require_clean=True):
    root, path = Path(root).resolve(), Path(path).resolve()
    m, p, recovery, old_m = load_manifest(root, path)
    commit = clean_commit(root) if require_clean else git(root, "rev-parse", "HEAD")
    if require_clean:
        for target in (path, root/m["authorization"]["path"], root/m["recovery_proposal"]["path"], root/recovery["design_document"]["path"]):
            _tracked(root, target)
    # The original metadata-only preflight validates runtime and source PNG bytes;
    # it never invokes a completed detector/selector/scorer/renderer pipeline.
    old_loaded, original_p, inputs, original_head = original.preflight(root, root/m["original_experiment"]["path"], require_clean=require_clean)
    if old_loaded != old_m or original_p != p or original_head != commit:
        raise ValueError("Original preflight differs")
    validate_partition(root, recovery, p)
    for item in inputs:
        item.update(recovery=recovery, original_manifest=old_m)
    return m, p, inputs, commit


def unchanged(root, path, m, commit):
    current, _, _, now = preflight(root, path)
    if current != m or now != commit:
        raise ValueError("Recovery inputs/code changed")


def output_path(root, window, config=None):
    name = "candidates.json" if config is None else config.variant_id+".json"
    return safe_path(Path(root), f"{OUTPUT_ROOT}/{window['window_id']}/{name}", OUTPUT_ROOT)


candidate_path = output_path


def checkpoint_path(root, window, frame, view):
    return safe_path(Path(root), f"{OUTPUT_ROOT}/{window['window_id']}/views/frame_{frame:06d}_{view['view_id']}.json", OUTPUT_ROOT)


def _unit_header(m, window, model, sources):
    return {"experiment_spec_sha256": spec_digest(m), "recovery_proposal": m["recovery_proposal"], "runtime":m["runtime"],
            "window":window,"source_frames":sources,"crop_views":crop_views(),"per_view_model_provenance":model.to_dict(),
            "actual_inference_commit":model.code_commit,"selected_operating_point":None,"quality_gate":None}


def _read_new_checkpoint(root, target, header, frame, view, source_png, model):
    value = read_json(target)
    if value["schema_version"] != "ball_yolo_crop_checkpoint/v0.2":
        raise ValueError("Wrong recovery checkpoint schema")
    if value["content_sha256"] != canonical_sha256({k:v for k,v in value.items() if k != "content_sha256"}):
        raise ValueError("Recovery checkpoint content changed")
    from .yolo11x_adapter import validate_prediction
    closed(value, {"schema_version","header","frame_index","source_png","result","content_sha256",
                   "attempt_start","preparation_start","preparation_result"}, "recovery checkpoint")
    if value["header"] != header or type(value["frame_index"]) is not int or value["frame_index"] != frame or value["source_png"] != source_png:
        raise ValueError("Recovery checkpoint scope/provenance changed")
    record=value["result"]
    closed(record,simple.VIEW_FIELDS,"recovery crop record")
    if record["view"] != view or not isinstance(record["attempt_id"],str) or not record["attempt_id"]:
        raise ValueError("Recovery checkpoint view/attempt changed")
    from .tiled_candidates import finite_nonnegative, validate_local
    finite_nonnegative(record["elapsed_seconds"],"crop seconds")
    if type(record["cuda_peak_allocated_bytes"]) is not int or record["cuda_peak_allocated_bytes"] < 0:
        raise ValueError("Invalid recovery CUDA peak")
    validate_prediction(record["prediction"],model)
    validate_local(record["prediction"]["candidates"],view,SourceVideo.from_mapping(header["window"]["source_video"]),model)
    for name in ("attempt_start","preparation_start","preparation_result"):
        bound_file(root,value[name],OUTPUT_ROOT)
    return record


def _load_units(root,m,p,inputs,commit):
    recovery=inputs[0]["recovery"]; old,missing=validate_partition(root,recovery,p)
    records,origins={},{}
    for item in inputs:
        w,model=item["window"],item["model"]
        if model.code_commit != commit:
            raise ValueError("Assembly preflight model code changed")
        for source in item["source_frames"]:
            f=source["frame_index"]
            for v in crop_views():
                k=(w["window_id"],f,v["view_id"])
                if k in old:
                    row=old[k];target=bound_file(root,row["checkpoint"],original.OUTPUT_ROOT)
                    actual_model=replace(model,code_commit=ORIGINAL_COMMIT)
                    header=original.make_header(item["original_manifest"],w,actual_model,item["source_frames"])
                    record=original.read_checkpoint(target,header,f,v,source["source_png"],actual_model)
                    if record["attempt_id"] != row["attempt_id"]:
                        raise ValueError("Preserved actual attempt changed")
                    attempt=next(a for a in recovery["preserved_attempt_receipts"] if a["attempt_id"] == record["attempt_id"])
                    prep=next(a for a in recovery["preserved_preparation_receipts"] if a["preparation_id"] == attempt["preparation_id"])
                    origin={**unit(w,f,v),"checkpoint":row["checkpoint"],"actual_inference_commit":ORIGINAL_COMMIT,
                            "attempt_start":attempt["start"],"attempt_result":attempt["result"],
                            "preparation_start":prep["start"],"preparation_result":prep["result"]}
                else:
                    target=checkpoint_path(root,w,f,v)
                    if not target.exists():continue
                    header=_unit_header(m,w,model,item["source_frames"])
                    record=_read_new_checkpoint(root,target,header,f,v,source["source_png"],model)
                    origin=_new_origin(root,w,f,v,target,commit)
                records[k],origins[k]=record,origin
    expected_new={checkpoint_path(root,next(w for w in p["windows"] if w["window_id"]==r["window_id"]),r["frame_index"],crop_views()[r["view_ordinal"]]) for r in missing.values()}
    if not set(safe_path(root,OUTPUT_ROOT).glob("*/views/*.json")) <= expected_new:
        raise ValueError("Recovery has an undeclared or repeated original checkpoint")
    return records,origins


def _new_origin(root,w,f,v,target,commit):
    cp=read_json(target)
    result_path=_event_path(root,"attempts",cp["result"]["attempt_id"],"result")
    return {**unit(w,f,v),"checkpoint":file_binding(root,target),"actual_inference_commit":commit,
            **{k:cp[k] for k in ("attempt_start","preparation_start","preparation_result")},
            "attempt_result":file_binding(root,result_path) if result_path.exists() else None}


def _candidate_header(m,w,model,sources,origins,commit):
    units=[origins[w["window_id"],s["frame_index"],v["view_id"]] for s in sources for v in crop_views()]
    return {"experiment_spec_sha256":spec_digest(m),"recovery_proposal":m["recovery_proposal"],"runtime":m["runtime"],"window":w,
        "per_view_model_provenance":model.to_dict(),"source_frames":sources,"crop_views":crop_views(),"inference_units":units,
        "inference_inventory_sha256":canonical_sha256(units),"actual_inference_commits":sorted({u["actual_inference_commit"] for u in units}),
        "assembly_code_commit":commit,"model_code_commit_role":ROLE,"selected_operating_point":None,"quality_gate":None}


def _build_candidate(m,item,records,origins,commit):
    w,model=item["window"],item["model"]
    frames=[simple.make_frame(s["frame_index"],s["source_png"],[records[w["window_id"],s["frame_index"],v["view_id"]] for v in crop_views()],
                SourceVideo.from_mapping(w["source_video"]),model) for s in item["source_frames"]]
    header=_candidate_header(m,w,model,item["source_frames"],origins,commit)
    return {"schema_version":CANDIDATE_SCHEMA,"header":header,"frames":frames,"content_sha256":canonical_sha256({"header":header,"frames":frames})}


def _first_window_parity(root,recovery,payload,commit):
    """Compare original completed semantics before constructing another model."""
    original_payload=read_json(bound_file(root,recovery["preserved_candidate_files"][0],original.OUTPUT_ROOT))
    if payload["header"]["window"] != original_payload["header"]["window"] or payload["frames"] != original_payload["frames"]:
        raise ValueError("Completed first-window candidate semantics changed")
    run=candidate_run(payload)
    saved={}
    for b in recovery["preserved_selector_files"]:
        obs=read_json(bound_file(root,b,original.OUTPUT_ROOT))["observations"]
        c=SelectorConfig.from_mapping(obs["config"])
        if c.variant_id in saved or obs["ranking_code_commit"]!=ORIGINAL_COMMIT:
            raise ValueError("Completed original selector inventory differs")
        saved[c.variant_id]=obs
    if set(saved)!={c.variant_id for c in experiment_grid()}:
        raise ValueError("Completed original selector grid differs")
    for c in experiment_grid():
        new=simple.select_candidates(run,c,commit)
        old=saved[c.variant_id]
        for k in ("frames","config","variant_id","source_video","window","possession_id","score_semantics","selected_operating_point","quality_gate"):
            if new[k]!=old[k]:raise ValueError("Completed first-window selector semantics changed")
    return saved


def candidate_run(payload):
    if payload["schema_version"] != CANDIDATE_SCHEMA or payload["header"]["model_code_commit_role"] != ROLE:
        raise ValueError("Candidate assembly role missing")
    header=payload["header"]
    if (header["per_view_model_provenance"]["code_commit"] != header["assembly_code_commit"]
            or header["inference_inventory_sha256"] != canonical_sha256(header["inference_units"])
            or header["actual_inference_commits"] != sorted({u["actual_inference_commit"] for u in header["inference_units"]})):
        raise ValueError("Mixed inference provenance differs")
    # The legacy typed shape carries the clearly declared assembly-view commit;
    # all actual inference commits remain in the bound v0.2 candidate header.
    projection={**payload,"schema_version":simple.CANDIDATE_SCHEMA}
    return simple.candidate_run(projection)


def load_candidate_run(root,m,p,window,commit,*,model=None):
    recovery=read_json(bound_file(root,m["recovery_proposal"],"configs/ball_tracking/proposals"))
    old_m=read_json(bound_file(root,m["original_experiment"],"configs/ball_tracking/yolo_crop_experiments"))
    if model is None:
        runtime=read_json(bound_file(root,m["runtime"],"data/outputs/ball_tracking"))
        _,model=original.inspect_runtime(root,runtime,commit)
    sources=[s for s in p["inference_source_frames"] if s["window_id"]==window["window_id"]]
    item={"window":window,"model":model,"source_frames":sources,"recovery":recovery,"original_manifest":old_m}
    records,origins=_load_units(root,m,p,[item],commit)
    _load_ledger(root,m,p,commit,model=model)
    expected=_build_candidate(m,item,records,origins,commit)
    payload=read_json(candidate_path(root,window))
    if payload != expected:raise ValueError("Recovery candidates differ from actual bound checkpoints")
    return candidate_run(payload),payload,payload["content_sha256"]


def observation_provenance(payload,candidate_binding):
    return {**{k:payload["header"][k] for k in PROVENANCE_FIELDS},"input_candidate_file":candidate_binding}


def observations(run,config,commit,payload,candidate_binding):
    obs=simple.select_candidates(run,config,commit)
    obs.pop("detector_code_commit")
    obs.update(schema_version=SCHEMA,**observation_provenance(payload,candidate_binding))
    return obs


def _event_path(root,folder,identity,kind):
    return safe_path(Path(root),f"{OUTPUT_ROOT}/{folder}/{identity}.{kind}.json",OUTPUT_ROOT)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load_ledger(root,m,p,commit,*,model):
    """Validate both directions of immutable receipts, preserving unknown tails."""
    preparations,attempts={},{}
    for folder,destination in (("preparations",preparations),("attempts",attempts)):
        directory=safe_path(root,OUTPUT_ROOT+"/"+folder,OUTPUT_ROOT)
        for target in sorted(directory.glob("*.start.json")):
            start=read_json(target);identity=target.name.removesuffix(".start.json")
            field="preparation_id" if folder=="preparations" else "attempt_id"
            if start.get(field) != identity or identity in destination:
                raise ValueError("Recovery receipt identity differs")
            end=_event_path(root,folder,identity,"result")
            result=read_json(end) if end.exists() else None
            if result is not None and (result.get(field) != identity or result.get("start_sha256") != sha256_file(target)):
                raise ValueError("Recovery receipt result lost start binding")
            destination[identity]={"start":start,"result":result,"start_binding":file_binding(root,target),
                "result_binding":file_binding(root,end) if result is not None else None}
        expected={_event_path(root,folder,i,"start") for i in destination}|{_event_path(root,folder,i,"result") for i,r in destination.items() if r["result"] is not None}
        if set(directory.glob("*")) != expected:
            raise ValueError("Orphan or extra recovery ledger file")
    for identity,entry in preparations.items():
        s,r=entry["start"],entry["result"]
        closed(s,{"preparation_id","experiment_spec_sha256","runtime","code_commit","accounting_before","started_at_utc"},"recovery preparation")
        if (s["experiment_spec_sha256"] != spec_digest(m) or s["runtime"] != m["runtime"] or s["code_commit"] != commit
                or s["accounting_before"] != {"synthetic_forwards":0,"project_attempts":0,"project_forwards":0,"preparation_complete":False}):
            raise ValueError("Recovery preparation provenance differs")
        if r is not None:
            closed(r,{"preparation_id","start_sha256","status","accounting_after","error","finished_at_utc"},"recovery preparation result")
            if r["status"] not in ("prepared","failed"):
                raise ValueError("Invalid recovery preparation status")
            after=original._accounting(r["accounting_after"],prepared=r["status"]=="prepared")
            if after["project_attempts"] or after["project_forwards"] or ((r["error"] is None) != (r["status"]=="prepared")):
                raise ValueError("Preparation used project work or lost error")
    windows={w["window_id"]:w for w in p["windows"]}
    sources={(s["window_id"],s["frame_index"]):s["source_png"] for s in p["inference_source_frames"]}
    if model.code_commit!=commit:raise ValueError("Recovery ledger model commit differs")
    expected_headers={w["window_id"]:_unit_header(m,w,model,[s for s in p["inference_source_frames"] if s["window_id"]==w["window_id"]]) for w in p["windows"]}
    allowed={key(u) for u in _units(p)[175:]}
    completed_units={};tails=0;known_attempts=known_forwards=0
    for identity,entry in attempts.items():
        s,r=entry["start"],entry["result"]
        closed(s,{"attempt_id","preparation_id","unit","header_sha256","source_png","accounting_before","started_at_utc"},"recovery attempt")
        k=key(s["unit"]);prep=preparations.get(s["preparation_id"])
        if (k not in allowed or prep is None or prep["result"] is None or prep["result"]["status"] != "prepared"
                or s["source_png"] != sources.get(k[:2]) or s["header_sha256"] != canonical_sha256(expected_headers[k[0]])):
            raise ValueError("Attempt outside missing units or before prepared predictor")
        w=windows[k[0]];v=next(v for v in crop_views() if v["view_id"]==k[2])
        if s["unit"] != unit(w,k[1],v):raise ValueError("Attempt unit metadata differs")
        before=original._accounting(s["accounting_before"],prepared=True)
        if before["synthetic_forwards"] != prep["result"]["accounting_after"]["synthetic_forwards"]:
            raise ValueError("Attempt synthetic count drift")
        target=checkpoint_path(root,w,k[1],v)
        cp=read_json(target) if target.exists() else None
        mine=cp is not None and cp["result"]["attempt_id"]==identity
        if r is not None:
            closed(r,{"attempt_id","start_sha256","status","accounting_after","checkpoint","error","finished_at_utc"},"recovery attempt result")
            if r["status"] not in ("completed","failed"):raise ValueError("Invalid recovery attempt status")
            after=original._accounting(r["accounting_after"],prepared=True)
            if r["status"]=="completed":
                if not mine or r["checkpoint"] != file_binding(root,target) or r["error"] is not None:
                    raise ValueError("Completed recovery attempt lost exact checkpoint")
            elif r["checkpoint"] is not None or not isinstance(r["error"],str) or mine:
                raise ValueError("Failed attempt cannot certify a recovery checkpoint")
        elif mine:
            after={k:v for k,v in cp["result"]["prediction"]["forward_accounting"].items() if k!="this_project_attempt_forwards"}
            original._accounting(after,prepared=True);tails+=1
        else:
            after=None;tails+=1
        if mine:
            if (cp["header"]["actual_inference_commit"] != commit or cp["header"]["per_view_model_provenance"]["code_commit"] != commit
                    or cp["header"]["experiment_spec_sha256"] != spec_digest(m) or cp["header"]["window"] != w
                    or cp["frame_index"] != k[1] or cp["source_png"] != s["source_png"] or cp["result"]["view"] != v
                    or canonical_sha256(cp["header"]) != s["header_sha256"] or cp["attempt_start"] != entry["start_binding"]
                    or cp["preparation_start"] != prep["start_binding"] or cp["preparation_result"] != prep["result_binding"]
                    or cp["result"]["prediction"]["forward_accounting"] != {**after,"this_project_attempt_forwards":1}
                    or k in completed_units):
                raise ValueError("Checkpoint actual inference/attempt/preparation provenance differs")
            completed_units[k]=identity
        if after is not None:
            da,df=after["project_attempts"]-before["project_attempts"],after["project_forwards"]-before["project_forwards"]
            if (after["synthetic_forwards"] != before["synthetic_forwards"] or not 0 <= df <= da <= 1
                    or (mine and (da,df)!=(1,1))):raise ValueError("Recovery actual-forward delta differs")
            known_attempts+=da;known_forwards+=df
        entry["effective_after"]=after
    for identity,prep in preparations.items():
        chain=sorted([r for r in attempts.values() if r["start"]["preparation_id"]==identity],key=lambda r:r["start"]["started_at_utc"])
        previous=prep["result"]["accounting_after"] if prep["result"] else None
        for entry in chain:
            if previous is None or entry["start"]["accounting_before"] != previous:
                raise ValueError("Recovery counters have a gap, duplicate or unknown predecessor")
            previous=entry["effective_after"]
    all_checkpoints=set(safe_path(root,OUTPUT_ROOT).glob("*/views/*.json"))
    expected_paths={checkpoint_path(root,windows[k[0]],k[1],next(v for v in crop_views() if v["view_id"]==k[2])) for k in completed_units}
    if all_checkpoints!=expected_paths:raise ValueError("Recovery checkpoint has no actual started attempt")
    return {"preparations":preparations,"attempts":attempts,"completed_units":completed_units,
        "known_project_attempts":known_attempts,"known_project_forwards":known_forwards,"unfinished_attempt_records":tails,
        "known_synthetic_forwards":sum(r["result"]["accounting_after"]["synthetic_forwards"] for r in preparations.values() if r["result"]),
        "unfinished_preparation_records":sum(r["result"] is None for r in preparations.values())}


def _start_preparation(root,m,commit,adapter):
    before=original._accounting(adapter.accounting)
    if before!={"synthetic_forwards":0,"project_attempts":0,"project_forwards":0,"preparation_complete":False}:
        raise ValueError("Recovery requires a fresh predictor")
    identity=uuid.uuid4().hex;start=_event_path(root,"preparations",identity,"start");end=_event_path(root,"preparations",identity,"result")
    persist_once(start,{"preparation_id":identity,"experiment_spec_sha256":spec_digest(m),"runtime":m["runtime"],"code_commit":commit,
                        "accounting_before":before,"started_at_utc":_now()})
    try:
        adapter.prepare();after=original._accounting(adapter.accounting,prepared=True)
        if after["project_attempts"] or after["project_forwards"]:raise ValueError("Recovery warmup used project forwards")
    except Exception as error:
        persist_once(end,{"preparation_id":identity,"start_sha256":sha256_file(start),"status":"failed",
            "accounting_after":original._accounting(adapter.accounting),"error":type(error).__name__+": "+str(error),"finished_at_utc":_now()})
        raise
    persist_once(end,{"preparation_id":identity,"start_sha256":sha256_file(start),"status":"prepared","accounting_after":after,"error":None,"finished_at_utc":_now()})
    return identity,file_binding(root,start),file_binding(root,end)


def run_experiment(root,path,*,dry_run=False,adapter_factory=None,png_reader=None):
    root,path=Path(root).resolve(),Path(path).resolve()
    m,p,inputs,commit=preflight(root,path,require_clean=not dry_run)
    records,origins=_load_units(root,m,p,inputs,commit)
    ledger=_load_ledger(root,m,p,commit,model=inputs[0]["model"])
    first_payload=_build_candidate(m,inputs[0],records,origins,commit)
    first_selectors=_first_window_parity(root,inputs[0]["recovery"],first_payload,commit)
    # Existing derived files are checked before any new model or pixel access.
    for item in inputs:
        w=item["window"];target=candidate_path(root,w)
        if target.exists():
            expected=_build_candidate(m,item,records,origins,commit)
            if read_json(target)!=expected:raise ValueError("Existing recovery candidate changed")
            run=candidate_run(expected)
            for c in experiment_grid():
                if output_path(root,w,c).exists():load_observations(root,m,p,w,run,expected["content_sha256"],c,commit,rederive=False)
        elif any(output_path(root,w,c).exists() for c in experiment_grid()):raise ValueError("Recovery selector without candidate file")
    if dry_run:
        return {"dry_run":True,"preserved_crop_units":175,"missing_crop_units":600-len(records),"cached_new_crop_units":len(records)-175,
                "new_candidate_files":6,"new_selector_outputs":162,"model_constructed":False}
    adapter=None;created=0
    if len(records)<600:
        first=inputs[0];adapter=(adapter_factory or original.create_adapter)(first["weights_path"],first["runtime_record"],commit)
        prep_id,prep_start,prep_result=_start_preparation(root,m,commit,adapter)
    for item in inputs:
        w,model=item["window"],item["model"]
        header=_unit_header(m,w,model,item["source_frames"])
        for source in item["source_frames"]:
            f=source["frame_index"]
            needed=[v for v in crop_views() if (w["window_id"],f,v["view_id"]) not in records]
            rgb=(png_reader or original.read_source_png)(root,source) if needed else None
            if needed and (rgb.shape!=(1080,1920,3) or str(rgb.dtype)!="uint8"):raise ValueError("Recovery source reader must return native uint8 RGB")
            for view in needed:
                identity=uuid.uuid4().hex;start=_event_path(root,"attempts",identity,"start");end=_event_path(root,"attempts",identity,"result")
                before=original._accounting(adapter.accounting,prepared=True);target=checkpoint_path(root,w,f,view)
                persist_once(start,{"attempt_id":identity,"preparation_id":prep_id,"unit":unit(w,f,view),"header_sha256":canonical_sha256(header),
                    "source_png":source["source_png"],"accounting_before":before,"started_at_utc":_now()})
                began=time.perf_counter()
                try:
                    x1,y1,x2,y2=view["xyxy_half_open_px"]
                    pred=adapter.predict_frame(rgb[y1:y2,x1:x2].copy())
                    after=original._accounting(adapter.accounting,prepared=True)
                    if (after["synthetic_forwards"]!=before["synthetic_forwards"] or after["project_attempts"]!=before["project_attempts"]+1
                            or after["project_forwards"]!=before["project_forwards"]+1 or pred["forward_accounting"]!={**after,"this_project_attempt_forwards":1}):
                        raise ValueError("Exactly one recovery project forward required")
                    record={"view":view,"prediction":pred,"elapsed_seconds":time.perf_counter()-began,"cuda_peak_allocated_bytes":adapter.cuda_peak_allocated_bytes,"attempt_id":identity}
                    cp={"schema_version":"ball_yolo_crop_checkpoint/v0.2","header":header,"frame_index":f,"source_png":source["source_png"],"result":record,
                        "attempt_start":file_binding(root,start),"preparation_start":prep_start,"preparation_result":prep_result}
                    cp["content_sha256"]=canonical_sha256(cp)
                    from .yolo11x_adapter import validate_prediction
                    validate_prediction(pred,model)
                    if type(record["cuda_peak_allocated_bytes"]) is not int or record["cuda_peak_allocated_bytes"]<0:raise ValueError("Measured CUDA peak required")
                    persist_once(target,cp)
                    _read_new_checkpoint(root,target,header,f,view,source["source_png"],model)
                    persist_once(end,{"attempt_id":identity,"start_sha256":sha256_file(start),"status":"completed","accounting_after":after,
                        "checkpoint":file_binding(root,target),"error":None,"finished_at_utc":_now()})
                    k=(w["window_id"],f,view["view_id"]);records[k]=record;origins[k]=_new_origin(root,w,f,view,target,commit);created+=1
                except Exception as error:
                    if not target.exists():persist_once(end,{"attempt_id":identity,"start_sha256":sha256_file(start),"status":"failed",
                        "accounting_after":original._accounting(adapter.accounting,prepared=True),"checkpoint":None,
                        "error":type(error).__name__+": "+str(error),"finished_at_utc":_now()})
                    raise
        payload=_build_candidate(m,item,records,origins,commit)
        persist_once(candidate_path(root,w),payload)
        run=candidate_run(payload);b=file_binding(root,candidate_path(root,w))
        for c in experiment_grid():
            obs=observations(run,c,commit,payload,b)
            if w==inputs[0]["window"] and obs["frames"]!=first_selectors[c.variant_id]["frames"]:
                raise ValueError("Completed first-window selector changed during derivation")
            persist_once(output_path(root,w,c),{"experiment_spec_sha256":spec_digest(m),"input_candidates":b,"candidate_content_sha256":payload["content_sha256"],
                "observations_content_sha256":canonical_sha256(obs),"observations":obs})
    unchanged(root,path,m,commit)
    ledger=_load_ledger(root,m,p,commit,model=inputs[0]["model"])
    return {"unique_completed_crop_units":600,"preserved_original_crop_units":175,"new_crop_units":425,"created_new_checkpoints_this_invocation":created,
        "candidate_files":6,"selector_outputs":162,"preserved_original_selectors":27,"known_total_project_attempts":177+ledger["known_project_attempts"],
        "known_total_project_forwards":177+ledger["known_project_forwards"],"known_total_synthetic_forwards":4+ledger["known_synthetic_forwards"],
        "failed_original_attempts":2,"failed_recovery_attempts":sum(r["result"] is not None and r["result"]["status"]=="failed" for r in ledger["attempts"].values()),
        "recorded_attempt_starts":177+len(ledger["attempts"]),"predictor_preparations":2+len(ledger["preparations"]),
        "unfinished_attempt_records":ledger["unfinished_attempt_records"],"unfinished_preparation_records":ledger["unfinished_preparation_records"],
        "unfinished_accounting_is_unknown":bool(ledger["unfinished_attempt_records"] or ledger["unfinished_preparation_records"]),
        "assembly_code_commit":commit,"model_code_commit_role":ROLE,"selected_operating_point":None,"quality_gate":None}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--repository-root",type=Path,default=Path.cwd())
    parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args();root=args.repository_root.resolve()
    print(json.dumps(run_experiment(root,(root/args.manifest).resolve(),dry_run=args.dry_run),indent=2))


def validate_saved_observations(obs,run,payload,candidate_binding):
    if ("detector_code_commit" in obs or obs.get("schema_version") != SCHEMA or any(obs.get(k) != v for k,v in observation_provenance(payload,candidate_binding).items())
            or obs.get("ranking_code_commit") != payload["header"]["assembly_code_commit"]
            or obs.get("input_candidate_content_sha256") != canonical_sha256(run.to_dict())):
        raise ValueError("Recovery observations lost actual-inference/assembly provenance")
    projection={k:v for k,v in obs.items() if k not in (*PROVENANCE_FIELDS,"input_candidate_file")}
    projection.update(schema_version=simple.SCHEMA,detector_code_commit=run.model_provenance.code_commit)
    simple.validate_saved_structure(projection,run)
    return SelectorConfig.from_mapping(obs["config"])


def load_observations(root,m,p,window,run,digest,config,commit,*,rederive=False):
    envelope=closed(read_json(output_path(root,window,config)),original.ENVELOPE_FIELDS,"recovery selector envelope")
    payload=read_json(candidate_path(root,window));b=file_binding(root,candidate_path(root,window));obs=envelope["observations"]
    if (envelope["experiment_spec_sha256"] != spec_digest(m) or envelope["input_candidates"] != b
            or envelope["candidate_content_sha256"] != digest or payload["content_sha256"] != digest
            or envelope["observations_content_sha256"] != canonical_sha256(obs)
            or obs.get("config") != config.to_dict() or obs.get("variant_id") != config.variant_id
            or obs.get("source_video") != run.source_video.to_dict() or obs.get("window") != run.window.to_dict()
            or obs.get("possession_id") != run.possession_id or obs.get("selected_operating_point") is not None or obs.get("quality_gate") is not None):
        raise ValueError("Recovery selector envelope differs")
    validate_saved_observations(obs,run,payload,b)
    if rederive and obs != observations(run,config,commit,payload,b):raise ValueError("Recovery selector derivation differs")
    return obs


if __name__=="__main__":main()
