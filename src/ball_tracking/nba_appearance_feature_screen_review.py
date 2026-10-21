"""Bound query/nearest-reference sheets for the fixed feature screen."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import textwrap
import uuid

from PIL import Image, ImageDraw

from . import nba_action_review as review
from . import nba_wasb_diagnostic as d

SCHEMA = "nba_appearance_feature_screen_review/v0.1"
WIDTH, ROW_HEIGHT, HEADER = 1600, 340, 130
PANELS = (30, 360, 690)


def load_inputs(root, completion_path):
    path = d.contained(root, str(completion_path)); completion = d.read_json(path)
    d.require(completion["status"] == "completed", "Feature screen is incomplete")
    d.bound(root, completion["protocol"])
    report = d.read_json(d.bound(root, completion["report"]))
    d.require(report["protocol"] == completion["protocol"] and report["features"] == completion["features"], "Report protocol/feature inventory differs")
    features = {}
    for entry in completion["features"]:
        feature = d.read_json(d.bound(root, entry["feature"]))
        case = feature["case"]; key = case["case_id"]
        d.require(key == entry["case_id"] and key not in features, "Feature identity duplicated or changed")
        d.require(feature["protocol"] == completion["protocol"], "Feature protocol differs")
        for name in ("crop64", "input224"):
            d.require(feature[name] == entry[name], "Feature image transport differs")
            d.bound(root, entry[name])
        features[key] = feature
    bank = report["reference_bank_case_ids"]
    d.require(bank == [key for key,f in features.items() if f["case"]["screen_role"] == "reference_bank"], "Reference bank order differs")
    d.require([q["case_id"] for q in report["queries"]] == [key for key in features if key not in bank], "Query coverage or ordering differs")
    for query in report["queries"]:
        case = features[query["case_id"]]["case"]
        d.require(all(query[k] == v for k,v in case.items()), "Query source/provenance/semantic transport differs")
        d.require([s["reference_case_id"] for s in query["similarities"]] == bank, "Similarity bank inventory differs")
        d.require(all(s["classification"] == features[s["reference_case_id"]]["case"]["accepted_appearance"]["classification"] for s in query["similarities"]), "Similarity reference label differs")
        for label, field in (("ball", "ball"), ("other_object", "other")):
            selected = [s for s in query["similarities"] if s["classification"] == label]
            maximum = max(s["cosine_similarity"] for s in selected)
            nearest = [s["reference_case_id"] for s in selected if s["cosine_similarity"] == maximum]
            d.require(query[f"s_{field}"] == maximum and query[f"nearest_{field}_case_ids"] == nearest, "Nearest-class maximum/ties differ")
            d.require(all(features[k]["case"]["accepted_appearance"]["classification"] == label for k in nearest), "Nearest reference class differs")
        d.require(query["margin"] == query["s_ball"]-query["s_other"], "Class margin differs")
        expected = "ball_preferred" if query["margin"] > 0 else "other_preferred" if query["margin"] < 0 else "abstain_tie"
        d.require(query["preference"] == expected, "Retrieval preference differs")
    return completion, report, features


def crop_image(root, feature):
    with Image.open(d.bound(root, feature["crop64"])) as image:
        d.require(image.size == (64,64) and image.mode == "RGB", "Native crop differs")
        return image.copy()


def semantic_text(query):
    if "accepted_appearance" in query:
        row = query["accepted_appearance"]
        return f"Accepted appearance: {row['classification']}" + (f" ({row['subtype']})" if row["subtype"] else "")
    assessment = query.get("prior_ai_assessment", {})
    label = assessment.get("assessment", "unresolved") if isinstance(assessment,dict) else str(assessment)
    return f"Prior AI only: {label}; not accepted class truth"


def gate_text(report):
    summary=report["summary"]
    return (f"Main gate: {'PASS' if summary['main_gate']['passed'] else 'FAIL'} | clean screen: {'YES' if summary['clean_screen'] else 'NO'}"
            f" | SAC head: {'FLAG' if summary['challenges']['sac_wrong_head']['flagged'] else 'clear'}"
            f" | DET near-head: {'FLAG' if summary['challenges']['det_near_head_ball']['flagged'] else 'clear'}")


def row_image(root, query, features, ordinal):
    image = Image.new("RGB", (WIDTH, ROW_HEIGHT), "#101722"); draw = ImageDraw.Draw(image)
    draw.text((18,8), f"{ordinal:02d}  {query['case_id']}  |  {query['screen_role']}", font=review.font(22), fill="#ffd380")
    selected = [query["case_id"], query["nearest_ball_case_ids"][0], query["nearest_other_case_ids"][0]]
    titles = ["QUERY: SAVED POINT", "NEAREST BALL REFERENCE", "NEAREST OTHER REFERENCE"]
    for x,key,title in zip(PANELS,selected,titles,strict=True):
        feature = features[key]; case = feature["case"]
        draw.text((x,40), title, font=review.font(17), fill="white")
        image.paste(crop_image(root,feature).resize((224,224),Image.Resampling.NEAREST),(x,66))
        short = f"{case['continuous_source_id']}  f{case['source_frame_index']}"
        draw.text((x,295), short, font=review.font(17), fill="white")
        suffix = "query" if key == query["case_id"] else case["accepted_appearance"]["classification"]
        draw.text((x,316), suffix, font=review.font(15), fill="#a9c9e8")
    lines = [query["preference"].replace("_"," ").upper(),
        f"Ball cosine: {query['s_ball']:.6f}", f"Other cosine: {query['s_other']:.6f}",
        f"Margin: {query['margin']:+.6f}", semantic_text(query),
        (f"Prior AI disagreement: {query['qualitative_disagreement']} | tie: {query['qualitative_tie']}" if query["screen_role"] == "exposed_regression"
         else f"Accepted check: {query['accepted_check_outcome'] or 'not scored'}"),
        f"Native frame {query['source_frame_index']} / PTS {query['source_pts_ticks']}",
        f"Nearest ties: ball {len(query['nearest_ball_case_ids'])}, other {len(query['nearest_other_case_ids'])}",
        "First tied reference shown; all IDs in guide.", "Similarities are not probabilities."]
    y=67
    for line in lines:
        for part in textwrap.wrap(line, width=45):
            draw.text((1030,y),part,font=review.font(18),fill="white"); y+=22
    d.require(y <= ROW_HEIGHT, "Review row text exceeds panel")
    return image


def build_review(root, completion_path, output):
    root=Path(root).resolve(); completion,report,features=load_inputs(root,completion_path)
    output=d.contained(root,str(output)); d.require(output.is_relative_to(root/"data/outputs"),"Review output must remain ignored")
    identity={"schema_version":SCHEMA,"completion":d.binding(root,d.contained(root,str(completion_path))),
        "report":completion["report"],"protocol":completion["protocol"],
        "implementation":d.binding(root,root/"src/ball_tracking"/Path(__file__).name),
        "font_implementation":d.binding(root,root/"src/ball_tracking/nba_action_review.py")}
    final=output/"completion.json"
    if final.exists():
        prior=d.read_json(final); d.require(prior["identity"]==identity,"Existing review identity differs")
        for record in prior["artifacts"].values():d.bound(root,record)
        for sheet in prior["sheets"]:d.bound(root,sheet["image"])
        return prior
    folder=output/"attempts"/uuid.uuid4().hex; folder.mkdir(parents=True)
    d.write_once(folder/"started.json",{"identity":identity,"at_utc":d.stamp()})
    try:
        queries=report["queries"]; d.require(queries,"Empty query report"); sheets=[]
        for start in range(0,len(queries),5):
            subset=queries[start:start+5]; canvas=Image.new("RGB",(WIDTH,HEADER+len(subset)*ROW_HEIGHT),"#101722")
            draw=ImageDraw.Draw(canvas)
            draw.text((18,12),"Frozen appearance screen — model preferences for review",font=review.font(28),fill="#ffd380")
            draw.text((18,52),f"Queries {start+1}–{start+len(subset)} of {len(queries)} | "+gate_text(report),font=review.font(22),fill="white")
            draw.text((18,89),"Native 64×64 crops enlarged for inspection; unknowns stay unscored; prior AI judgments remain qualitative.",font=review.font(20),fill="white")
            for offset,query in enumerate(subset):
                row=row_image(root,query,features,start+offset+1); canvas.paste(row,(0,HEADER+offset*ROW_HEIGHT))
                if start+offset == len(queries)-1:row.save(folder/"actual_final_query.png")
            path=folder/f"queries_{start+1:02d}_{start+len(subset):02d}.png"; canvas.save(path)
            sheets.append({"query_case_ids":[q["case_id"] for q in subset],"image":d.binding(root,path)})
        manifest={"identity":identity,"query_case_ids":[q["case_id"] for q in queries],"reference_bank_case_ids":report["reference_bank_case_ids"],
            "query_count":len(queries),"sheets":sheets,"actual_final_case_id":queries[-1]["case_id"],"tie_display":"first in frozen bank order; all tied IDs preserved in guide/report","coordinates_or_labels_changed":False}
        d.write_once(folder/"manifest.json",manifest)
        build_html(folder,report,sheets)
        result={"status":"completed","identity":identity,"query_count":len(queries),"sheets":sheets,
            "artifacts":{name:d.binding(root,folder/file) for name,file in {"manifest":"manifest.json","guide":"review.html","actual_final":"actual_final_query.png"}.items()},
            "model_preferences_human_review":"pending","trajectory_changes":False}
        d.write_once(final,result);return result
    except Exception as error:
        d.write_once(folder/"failed.json",{"error_type":type(error).__name__,"error":str(error)});raise


def build_html(folder,report,sheets):
    images="".join(f"<figure><a href='{Path(s['image']['path']).name}'><img loading='lazy' src='{Path(s['image']['path']).name}'></a><figcaption>Queries {5*i+1}–{5*i+len(s['query_case_ids'])}</figcaption></figure>" for i,s in enumerate(sheets))
    rows=[]
    for query in report["queries"]:
        cells=[query["case_id"],query["screen_role"],semantic_text(query),query["preference"],repr(query["s_ball"]),repr(query["s_other"]),repr(query["margin"]),
            "; ".join(query["nearest_ball_case_ids"]),"; ".join(query["nearest_other_case_ids"]),query["accepted_check_outcome"] or "unscored",
            str(query["qualitative_disagreement"]),str(query["qualitative_tie"])]
        rows.append("<tr>"+"".join("<td>"+html.escape(v)+"</td>" for v in cells)+"</tr>")
    summary=html.escape(json.dumps(report["summary"],indent=2))
    text=f"<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>Frozen appearance screen review</title><style>body{{max-width:1600px;margin:20px auto;padding:0 16px;background:#101722;color:white;font:18px system-ui}}img{{width:100%}}a{{color:#9fd9ff}}figure{{margin:28px 0}}.scroll{{overflow:auto}}td,th{{padding:8px;border:1px solid #637080;text-align:left}}table{{border-collapse:collapse}}pre{{white-space:pre-wrap}}</style><h1>Frozen appearance screen</h1><p><b>{html.escape(gate_text(report))}</b></p><p>All {len(report['queries'])} queries appear beside their nearest ball and other-object references. Crop appearance is enlarged from 64×64 native pixels. The model input used the frozen 224×224 transform. References are human-accepted AI proposals; model preferences are new results for review.</p><p>Similarity is not probability. Unknowns remain unscored. Prior AI object assessments remain qualitative and are not newly accepted classification truth. No coordinate, label or trajectory was changed.</p><p>If a class has tied nearest references, its first reference in frozen bank order is shown; all tied IDs and exact scores appear below. The report retains every bank similarity.</p><p><a href='actual_final_query.png'>Actual final query</a></p><details><summary>Recorded result summary</summary><pre>{summary}</pre></details>{images}<div class='scroll'><table><thead><tr>{''.join('<th>'+v+'</th>' for v in ['Case','Role','Reference status','Preference','Ball cosine','Other cosine','Margin','Nearest ball IDs','Nearest other IDs','Accepted check','Prior AI disagreement','Prior AI tie'])}</tr></thead><tbody>{''.join(rows)}</tbody></table></div></html>\n"
    (folder/"review.html").write_text(text,encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--completion",required=True);parser.add_argument("--output",required=True)
    args=parser.parse_args();print(json.dumps(build_review(Path(__file__).resolve().parents[2],args.completion,args.output),indent=2))


if __name__=="__main__":main()
