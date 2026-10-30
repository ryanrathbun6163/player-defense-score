"""Finite, score-blind CPU image information screen. No inference or fitting.

Freeze candidates before rendering. Wider input is an engineering contrast, not
a new model or a reference-centered oracle crop. Existing local pixels are exact.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .candidate_quality_model import point_geometry, preprocess
from .nba_appearance_feature_screen import crop_and_preprocess

BASE = Path('data/outputs/ball_tracking/input_context_screen_v0_1')
FRESH = Path('data/outputs/ball_tracking/fresh_game_diagnostic_v0_1')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def rows(path):
    return [json.loads(s) for s in Path(path).read_text(encoding='utf-8').splitlines() if s]


def bind(root, path):
    p = (root / path).resolve()
    assert p.is_relative_to(root)
    return {'path': p.relative_to(root).as_posix(), 'bytes': p.stat().st_size,
            'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write('\n')


def geometry(center, size):
    x, y = (math.floor(float(v)) for v in center)
    return [x-size//2, y-size//2, x+size//2, y+size//2]


def paired_inputs(image, center):
    raw, local, chw = crop_and_preprocess(image, center)
    box = geometry(center, 192)
    context = image.convert('RGB').crop(box).resize((224, 224), Image.Resampling.BICUBIC)
    return raw, local, chw, context, box


def episode(key):
    clip, idx = key.split(':'); n = int(idx)
    groups = {'122': [(7,9),(18,19),(52,58),(71,72),(92,93)],
              '237': [(40,47),(51,51)], '365': [(41,41)]}
    for a,b in groups[clip[-3:]]:
        if a <= n <= b:
            return f'{clip}:{a}-{b}'
    return f'{clip}:source_time_controls'


def freeze(root):
    base = root / BASE
    recommendation = read(base/'recommendation.json')
    frames = {r['frame_key']: r for r in rows(root/FRESH/'analysis/frames.jsonl')}
    candidates = {r['candidate_id']: r for r in rows(root/FRESH/'analysis/candidates.jsonl')}
    inputs = {r['candidate_id']: r for r in rows(root/FRESH/'attempt_001/Q_inputs.jsonl')}
    failures = set(recommendation['fresh_failure_related_frames'])
    controls = set(recommendation['source_time_control_frames'])
    selected = []
    missing = []
    for key in sorted(failures | controls):
        f = frames[key]
        ids = set(f['pool']['matching_candidate_ids'])
        for name, choice in f['choices'].items():
            if choice['candidate_id'] is not None:
                ids.add(choice['candidate_id'])
            else:
                missing.append({'frame_key': key, 'choice': name})
        for cid in sorted(ids, key=lambda c: candidates[c]['candidate_index']):
            c = candidates[cid]
            assert inputs[cid]['source_png']['sha256'] == f['source_png']['sha256']
            selected.append({'candidate_id': cid, 'frame_key': key,
                'source_png': f['source_png'], 'center_xy_px': c['center_xy_px'],
                'reference_category': c['reference_category'],
                'evaluation_category': c['evaluation_category'],
                'distance_to_reference_px': c['distance_to_reference_px'],
                'boundary_uncertainty': c['within_recorded_uncertainty_of_match_boundary'],
                'reference_authority': 'AI_authored_human_accepted',
                'role': 'BKN_diagnostic_development_no_fitting',
                'cohort': 'fresh', 'episode_group': episode(key),
                'failure_related': key in failures, 'source_time_control': key in controls,
                'choice_origins': [n for n,ch in f['choices'].items() if ch['candidate_id']==cid],
                'reference_assisted_matching_membership': cid in f['pool']['matching_candidate_ids'],
                'Q_input': inputs[cid]})
    legacy = read(base/'legacy_preparation/legacy_candidates.json')
    legacy_rows = legacy if isinstance(legacy, list) else legacy['candidates']
    for c in legacy_rows:
        selected.append(dict(c, cohort='legacy', failure_related=True, source_time_control=False))
    assert len({(r['cohort'],r['candidate_id']) for r in selected}) == len(selected)
    random.Random(20261030).shuffle(selected)
    for i,r in enumerate(selected):
        r['blind_id'] = f'C{i+1:03d}'
    files = subprocess.check_output(['git','ls-files','--modified','--others','--exclude-standard'],
                                    cwd=root, text=True).splitlines()
    write(base/'baseline_worktree.json', {'files':[bind(root,Path(p)) for p in files],
        'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        'branch':subprocess.check_output(['git','branch','--show-current'],cwd=root,text=True).strip(),
        'index':subprocess.check_output(['git','diff','--cached','--name-only'],cwd=root,text=True)})
    manifest = {'status':'frozen_before_treatment_render_and_review',
        'utc':datetime.now(timezone.utc).isoformat(),
        'authorization':'Ryan: Ok chat move forward (continuation of recommended bounded CPU screen)',
        'candidates':selected, 'missing_choice_slots':missing,
        'fresh_frame_count':len(failures|controls), 'legacy_frame_count':len({r['frame_key'] for r in legacy_rows}),
        'selection':'Union of native choice, original-Q-top choice, and ALL already-matching candidate identities on every frozen fresh frame; legacy separately frozen. Diagnostic reference-assisted sampling is not model selection or accuracy evaluation.',
        'context_size_source_px':192, 'local_size_px':224, 'context_display_px':224,
        'pixel_rule':'Exact original floor-centered64 -> bicubic256 -> center224 local; unchanged beside floor-centered192 -> bicubic224 current-frame context. No reference-centered crops.',
        'review_rule':'Two independent AI reviewers with no inherited case history. Each seals all local-only ratings before accessing paired views. Hide scores, source identities and reference categories. Same anonymous IDs across phases; possible memory/expectancy and shared-model biases acknowledged. Not human validation.',
        'go_rule':'Repeated concrete new cues in at least two frozen failure episodes, agreed by both reviewers and reconciled with existing reference authority, without weakening any matched success control. Case-selected engineering evidence only; no statistical or model-performance pass.',
        'roles':'BKN/HOU remain diagnostic, not fitting. Historical AI-only semantics never pooled with accepted truth. Unknowns retained. Geometric misses are not automatically non-ball.',
        'scope':'No model calls, fitting, new labels, selector, threshold sweep, protected access, footage acquisition or model adoption.',
        'inputs':[bind(root,BASE/'recommendation.json'),bind(root,BASE/'legacy_preparation/legacy_candidates.json'),
                  bind(root,FRESH/'analysis/frames.jsonl'),bind(root,FRESH/'analysis/candidates.jsonl'),
                  bind(root,FRESH/'attempt_001/Q_inputs.jsonl'),bind(root,FRESH/'attempt_001/Q_crops.npy'),
                  bind(root,Path('src/ball_tracking/input_context_screen.py'))]}
    write(base/'frozen_manifest.json',manifest)
    print(json.dumps({'frozen_candidates':len(selected),'fresh_frames':len(failures|controls),
                      'legacy_candidates':len(legacy_rows),'categories':dict(Counter(r['cohort'] for r in selected))}))


def render(root):
    base=root/BASE
    freeze_path=base/'frozen_manifest.json'
    manifest=read(freeze_path)
    for b in manifest['inputs']:
        assert bind(root,Path(b['path']))==b,b['path']
    out=base/'blind_media';out.mkdir(exist_ok=False)
    for d in ['local','paired','sheets_local','sheets_paired']:(out/d).mkdir()
    cache=np.load(root/FRESH/'attempt_001/Q_crops.npy',mmap_mode='r',allow_pickle=False)
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',16)
    checks=[]
    for r in manifest['candidates']:
        p=root/r['source_png']['path']
        assert bind(root,p)['sha256']==r['source_png']['sha256']
        im=Image.open(p).convert('RGB');xy=r['center_xy_px']
        raw,local,chw,context,box=paired_inputs(im,xy)
        assert np.array_equal(chw,preprocess(im,xy)[0])
        check={'blind_id':r['blind_id'],'source':bind(root,p),
            'local_exact_original_preprocess':True,'local_geometry':point_geometry(xy,*im.size),
            'context_box':box,'context_padding':not(box[0]>=0 and box[1]>=0 and box[2]<=im.width and box[3]<=im.height),
            'context_point_xy':[(xy[j]-box[j]+.5)*224/192-.5 for j in (0,1)]}
        if r['cohort']=='fresh':
            saved=np.asarray(cache[r['Q_input']['cache_index']])
            assert np.array_equal(np.asarray(raw),saved)
            assert np.array_equal(chw,crop_and_preprocess(Image.fromarray(saved),[32.,32.])[2])
            check['saved_Q_raw_and_tensor_equal']=True
        else:
            old=r['prior_input_binding']
            for field,array in [('crop64_rgb_sha256',np.asarray(raw)),
                                ('input224_rgb_sha256',np.asarray(local)),
                                ('input_chw_float32_sha256',chw)]:
                assert hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()==old[field],(r['blind_id'],field)
            check['saved_legacy_raw_rgb_tensor_hashes_equal']=True
        # Review marks occupy margins only; all 224x224 local pixels stay intact.
        a=Image.new('RGB',(244,270),'#16212b');d=ImageDraw.Draw(a)
        d.text((10,4),r['blind_id']+'  Local',font=font,fill='white');a.paste(local,(10,32))
        u,v=check['local_geometry']['point_input_xy']
        for pos in [(10+u,27,10+u,31),(10+u,257,10+u,263),(3,32+v,9,32+v),(235,32+v,241,32+v)]:d.line(pos,fill='#38e9ff',width=2)
        pair=Image.new('RGB',(488,270),'#16212b');pair.paste(a,(0,0));d=ImageDraw.Draw(pair)
        d.text((254,4),'Same point: wider view',font=font,fill='white');pair.paste(context,(254,32))
        u,v=check['context_point_xy']
        for pos in [(254+u,27,254+u,31),(254+u,257,254+u,263),(247,32+v,253,32+v),(479,32+v,485,32+v)]:d.line(pos,fill='#38e9ff',width=2)
        assert np.array_equal(np.asarray(a)[32:256,10:234],np.asarray(pair)[32:256,10:234])
        a.save(out/'local'/f"{r['blind_id']}.png")
        pair.save(out/'paired'/f"{r['blind_id']}.png")
        check['unchanged_local_in_treatment']=True
        checks.append(check)
    cache._mmap.close()
    for phase,cols,count,width in [('local',4,16,244),('paired',2,8,488)]:
        for n in range(0,len(checks),count):
            part=checks[n:n+count];sheet=Image.new('RGB',(width*cols,270*math.ceil(len(part)/cols)),'#16212b')
            for i,c in enumerate(part):sheet.paste(Image.open(out/phase/f"{c['blind_id']}.png"),((i%cols)*width,(i//cols)*270))
            sheet.save(out/f'sheets_{phase}'/f'{n//count+1:02d}.png')
    assert 'torch' not in sys.modules,'Unexpected Torch import'
    write(base/'render_receipt.json',{'status':'complete','utc':datetime.now(timezone.utc).isoformat(),
        'frozen_manifest':bind(root,freeze_path),'candidates':len(checks),'checks':checks,
        'media':[bind(root,p) for p in sorted(out.rglob('*.png'))],
        'model_calls':0,'torch_imported':False,'references_changed':False})
    print(json.dumps({'rendered':len(checks),'CPU_only':True,'path':str(out)}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','render']);args=p.parse_args()
    {'freeze':freeze,'render':render}[args.action](Path.cwd().resolve())
