# Proposed diagnostic: candidate retention, identity and center placement

Status: draft for scope review, October 2, 2026. This is a non-executable
saved-evidence proposal. No new experiment or training is approved or run.
The companion specification is
[`saved_candidate_retention_localization_diagnostic_v0_1.json`](../configs/ball_tracking/proposals/saved_candidate_retention_localization_diagnostic_v0_1.json).

We are still building the ball measurement layer, after validating player
coordinates. Before changing tracking, determine whether an observation was
lost before the tracker could consider it, whether the selected pixels depict
the wrong object, or whether a ball-region box places its center poorly.
These need different remedies. This proposal turns the completed inspection
into an auditable mechanism ledger; it does not repeat that inspection or
claim an improved tracker.

## Starting evidence and authority

Preparation began on `codex/ball-detector-baseline` at
`9fe6a1ef86d23391c64b7d5b16198ad7bb005c25`, with a clean worktree and empty
index. That commit records the reviewed YOLO closeout. Ryan's review of all
twelve comparison clips through their final frames is complete and will not
be requested again. The later 32-frame saved-candidate inspection is also
complete. Older context statements about staging or inspection pending are
historical.

The source package is
[`weak_candidate_inspection/9fe6a1ef86d2`](../data/outputs/ball_tracking/weak_candidate_inspection/9fe6a1ef86d2/):

- [`findings.md`](../data/outputs/ball_tracking/weak_candidate_inspection/9fe6a1ef86d2/findings.md)
  supplies the completed agent observations and their limitations.
- `completion.json` binds 231 assets; `inspection.json` binds 177 inputs and
  records exact frame, candidate, report, crop and inference provenance.
- `saved_cap_diagnosis.json` contains the fifteen existing top-twenty checks.
- [`review_native.html`](../data/outputs/ball_tracking/weak_candidate_inspection/9fe6a1ef86d2/review_native.html)
  is the final gallery. Reuse its exact source, context and box views, including
  the six focused plates; preserve both earlier gallery versions.

The companion JSON freezes their hashes, the complete cohort, the completed
YOLO review receipt, and the existing ten-family audit. The prior
[`YOLO results`](ball_yolo11x_crop_recovery_results.md) supply broader context:
RF-DETR has a saved radius-10 match in 140/145 eligible development frames at
the .01 export floor; YOLO has 87/145 and adds no uniquely matched frame there.
Those are label-assisted availability counts, not achievable tracker accuracy
or a detector selection. The saved method tradeoffs remain unselected.

## Fixed scope

Use exactly these already inspected development frames:

| Window | Persistent display misses | Hidden controls | Flight/reacquisition controls |
| --- | --- | --- | --- |
| P001 representative | 51-53, 59, 67-73 | none | none |
| P001 challenge | 204, 217, 219 | none | 200-201 |
| P002 representative | 257 | none | 262-264 |
| P002 challenge | 34 | none | none |
| P003 representative | 304 | none | none |
| P003 challenge | 164, 170, 173 | 165-169 | 171, 174 |

The 32 frames comprise twenty persistent display misses, five hidden controls
and seven other controls. Twenty-seven have eligible reference centers: two
fully visible and twenty-five partially visible amodal estimates. An amodal
estimate describes the complete ball center despite partial occlusion; it is
not an exact center independently measured from fully visible pixels.

Reuse all 82 cataloged detector/frame/candidate identities (56 RF, 26 YOLO),
640 saved outcomes from ten families at .20/.35 and radius 10, and all fifteen
saved .01/radius-10 top-twenty records. The 640 outcomes contain 410 emissions
and 230 abstentions. The catalog is the union of 58 distinct emitted candidates
and 31 saved floor matches, with seven shared entries. The 31 matches are the
evaluator's chosen match for each applicable detector/frame, not every possible
qualifying proposal. Candidate indices have separate RF and YOLO namespaces.

The six permitted source windows are P001 50-74/200-224, P002 250-274/25-49 and
P003 300-324/150-174. Existing six-window aggregate reports remain contextual
references, with representative and challenge pools separate. Do not expand
the 32-frame candidate catalog or create another performance grid. The selected
cohort and repeated settings are neither independent trials nor an unbiased
evaluation set; the earlier winner catalog is not a training split either.

## Three parallel diagnostic fields

### 1. Retention: could selection still consider the saved proposal?

Record the saved raw-floor outcome, original confidence and index, saved
top-twenty outcome where bound, displayed emission/abstention, and the original
loss-cause/report pointers. Preserve missing evidence as `unknown` or
`not_applicable`, with a reason. Do not reconstruct a new winner or infer cap
membership solely from an index; verify it against the saved selector trace
and its original candidate mapping.
The .01 top-twenty selector files are not among the inspection's 177 bound
inputs. Resolve membership only after verifying the existing saved report's
`observations_content_sha256` contract, which is a content binding rather
than a claim that those files were already byte-verified in this inspection.
If that binding cannot be verified, retain `unknown` membership and the
unchanged saved cap outcome.

The twenty persistent display misses already separate into:

- **Five without an RF radius-10 match at .01:** P001 representative
  59/67/68/69 and P002 representative 257. This establishes absence of a saved
  qualifying center, not absence of any ball pixels in the proposals.
- **Fifteen with a floor match removed by both display thresholds:** each
  matching RF candidate has confidence below .20. Calling it useful means
  localization-qualified in the saved report; its semantic identity is a
  separate question.

At the existing .01 top-twenty setting, eight of those fifteen still miss:
P001 representative 51/52/70/71/72/73 and P003 challenge 164/170. The other
seven retain a match. These are a separate setting's cap losses, not eight
additional causes to add to the fifteen displayed threshold losses. Lowering
a confidence filter alone would not retain all of these matches under the
existing cap. Conversely, a larger cap alone cannot restore a candidate
already removed by the confidence filter. Neither change is selected here.

Copied counts of retained candidates, false detections and hidden alarms must
accompany availability references. More available candidates also means more
alternatives to reject; availability does not predict the eventual path choice.

### 2. Identity: what do the saved pixels support?

Carry forward only attributed observations from the completed inspection:
`agent_observation`, its exact source passage/plate, and any unresolved question.
Keep `certified_candidate_identity` null and `training_eligible` false for every
entry. Do not invent per-candidate judgments where the findings are broader.

The existing observations include seating-region RF alternatives in P001
representative 67-73 and P002 representative 257/262, floor-reflection YOLO
alternatives in flight/hidden controls, and limb/footwear confusion near
players. They are hypotheses grounded in inspected pixels, not certified
ball/non-ball categories or class-level accuracy measurements. Being near a
player, lasting several frames, or having high confidence does not establish
ball identity. RF and YOLO confidence values are not interchangeable calibrated
probabilities.

`MATCH`, `UNMATCHED`, duplicate false positives and hidden false alarms retain
their evaluator meanings. None automatically supplies a semantic training
label. A hidden frame has no reviewed visible ball center; do not label a
specific crop as certified non-ball from that fact alone. The earlier clip
approval also supplies no new candidate-level identity verdicts.

If identity remains essential to a later change, name the exact candidate pair
and unresolved visual question for Ryan. Do not require another blanket clip
review or a second annotator. This proposal creates no new human labels.

### 3. Localization: where is the saved center relative to the reference?

Retain original box corners, center, crop-local coordinates, source-image
mapping, visibility, geometry source and numeric annotation uncertainty.
For eligible reference geometry, the proposed ledger may calculate only:

```text
dx = saved_candidate_x - reviewed_reference_x
dy = saved_candidate_y - reviewed_reference_y
reference_distance_px = hypot(dx, dy)
```

This is descriptive coordinate arithmetic on immutable observations, including
unmatched candidates whose report has a null matched-error field. It is not a
new prediction, corrected center, matching decision or score. Preserve the
original report's matched-error fields separately, including nulls. Keep all
three residual fields null on hidden/no-geometry frames. Store uncertainty
alongside the raw distance; do not subtract it to change a match or enlarge
the radius. Do not assign a localization-based identity label.

The focused cases are RF P001 representative 51#0 and 59#0, P002 representative
257#4, and P003 challenge 164#0. The completed agent inspection describes ball
fragments or ball/hand boundaries within these boxes despite failed center
comparisons. Broader matching boxes may include an occluding arm or referee.
The discrepancy could reflect box extent, occlusion, or reference uncertainty;
the available evidence does not uniquely identify the cause. A geometric
match can itself be accidental. Retention, identity uncertainty and center
discrepancy can all apply to one entry and must not be forced into exclusive
ball/non-ball bins.

## Controls and evidence needed before a later change

| Case | Diagnostic purpose | What would justify proposing a later change |
| --- | --- | --- |
| Eight .01 cap-loss cases, with the other seven weak-match cases retained | Separate confidence loss from candidate-budget loss | Exact saved membership and pixel evidence supporting useful alternatives could justify a bounded retention comparison. Its candidate load and hidden-alarm tradeoffs would need a separately specified test. No new cap or threshold follows automatically. |
| P002 representative 262#0 versus seating-region #2, plus 263-264 | Distinguish a surviving alternative from a bad path choice | Establish that the intended alternative survives preprocessing and inspect the saved path/cost evidence and identity ambiguity before proposing a ranking change. A low-confidence loss alone cannot justify another motion rule. |
| P001 representative 51/59, P002 representative 257, P003 challenge 164 | Separate wrong object from ball-region center discrepancy | Supported ball-region identity with remaining center discrepancy could justify a separate localization study. It cannot justify treating these failures as negative identity examples or moving the annotation to fit predictions. |
| P003 challenge 165-169 | Preserve abstention while the ball is hidden | Any later retention/identity idea must account for saved hidden emissions and missing observations explicitly. Do not invent hidden coordinates or fill this gap. |
| P001 challenge 200-201; P002 representative 262-264 | Preserve flight and successful comparison cases | A later proximity or support rule must explain how it avoids discarding these observations, using the saved controls and subsequently approved validation. |
| P003 challenge 170/171/173/174 | Preserve ambiguous and stronger reacquisitions | Keep 170's weak RF #148 beside the shoe-region #0; retain the stronger return at 171 and endpoint 174. A proposal must address both false starts and recovery, without inventing continuity across 165-169. |

This is an evidence checklist for formulating a later proposal, not a numerical
quality gate or automatic authorization. An unresolved outcome is valid.
If the saved evidence cannot separate mechanisms, record that limitation and
the smallest missing evidence; do not compensate with a fitted rule.
Any later comparison proposal must expose gains, regressions, false alarms
and missingness across all six approved development windows, with separate
pools, rather than reporting improvement only on this selected cohort.

A learned verifier would require a separate identity-semantics proposal,
explicit human review and a defensible training/evaluation design. Adjacent
frames, repeated crops and copies of one candidate must not masquerade as
independent train/test examples. Neither inspected catalog supplies that
design, and the sealed holdouts are not available for training or tuning.

## Proposed deliverables and verification

If Ryan approves implementing and running this exact diagnostic, it could
create one fresh,
ignored, versioned directory under
`data/outputs/ball_tracking/candidate_retention_localization_diagnostic/`.
No diagnostic runner or execution manifest is created by this draft. Planned
deliverables are:

1. `case_ledger.json`: 32 frame records, 82 candidate records, all 640 saved
   display outcomes and fifteen cap records, with the parallel fields above.
2. `summary.md`: the mechanism matrix, unique-frame denominators, separate
   pool/control summaries, contrary cases, unresolved questions and evidence
   needed for a subsequent proposal. Reference the existing gallery directly.
3. `integrity.json`: source and helper hashes, JSON pointers, current Git
   checkpoint, counts, original-file preservation and embargo checks.

Keys must bind detector, possession/window, frame and original candidate index
to the exact candidate-file hash. Preserve crop ID/rectangle, local-to-source
mapping and actual per-crop inference commit; a later ledger creation commit
must never replace inference provenance. Keep overlapping-crop candidates
distinct. Reference all saved source/box/context hashes. Missing diagnostics
need reasons, not invented geometry or identity.

Verification would resolve every copied pointer and candidate mapping, reconcile
32/82/640/15 records without treating repeated settings as independent samples,
and preserve original nulls and numeric values. Synthetic checks would cover
threshold/cap overlap, namespace collisions, nonzero center residuals on a
ball-region hypothesis, uncertain amodal references and hidden-frame nulls.
If implementation changes code, run focused tests then the full suite with
bytecode disabled. Any optional visual consultation uses the existing stills;
this proposal calls for no new renderer, clip or source-video decode.

Use create-only outputs; refuse an existing destination or mismatched binding.
Do not rerun the completed inspection helpers, model inference, selectors,
evaluators or review renderers. No filtering experiment, deduplication rule,
new center estimator, smoothing, interpolation, floor-homography projection,
ball-handler inference or training is included. Reviewed player decisions and
pipeline stages remain unchanged; no `--rerun-from` action is needed.

## Protected boundaries and next decision

All nine original prediction embargoes remain in force. Check only their path
absence against the frozen closeout inventory. P001 300-324, P002 200-224 and
P003 250-274 remain sealed: do not open their footage, labels, predictions or
outputs. Preserve reviewed annotations, configs, prior source evidence and
all generated baselines byte-for-byte. Do not select a method, operating point,
radius or ball-tracking quality gate, or alter the player generalization gate.

The next decision is review of this bounded diagnostic scope. Draft preparation
does not authorize a new experiment or training. Any later tracking experiment
needs its own concrete design and explicit authorization. Staging, committing,
pushing, PR creation and merging each remain separate explicit decisions under
`AGENTS.md`; none occurs in this preparation. No manual command is pending.
