# Proposed comparison: retain all saved floor candidates

Status: draft for scope review, not implemented or authorized for execution.
This proposal follows the completed saved-evidence diagnostic in
`ball_candidate_retention_localization_results.md`. The companion specification
is `configs/ball_tracking/proposals/rfdetr_medium_crop_candidate_retention_v0_1.json`.
No method, operating point, quality gate or training plan is selected.

## Question and limits

Does removing the twenty-candidate cap at the existing .01 export floor let
the unchanged path scorer use helpful candidates, and what does it cost in
wrong choices, hidden-ball alarms, missing observations and computation?

The completed inspection found fifteen persistent display misses with a saved
RF floor match below both display confidence cutoffs. Eight of those matches
also disappear under the separate .01 top-twenty cap. These are overlapping
diagnoses. They motivate this comparison; they do not predict fifteen recovered
outputs. More retained candidates can strengthen a clutter path.

The design separates two filters. Confidence decides which saved candidates
qualify. The cap then limits how many qualifying candidates enter the graph.
Removing the cap at .20 or .35 cannot recover a candidate below that cutoff.
In fact, the saved inventory contains at most nine qualifying candidates per
frame at .20 and seven at .35, so the cap has no effect at either setting.
Those comparisons require an equivalence record, not new selection runs.

Object identity and center placement remain separate. This experiment does
not move a box or center, change annotation uncertainty, or certify identities.
It cannot create a radius-10 candidate in the five persistent cases lacking
one at the export floor. MATCH/UNMATCHED remains a localization result, never
a ball/non-ball training label. Existing agent pixel descriptions remain
attributed diagnostic observations, not new human labels.

## Frozen inputs

Use the six existing RF-DETR crop candidate files and reviewed development
annotations, exactly as bound by the completed motion comparison:

| Possession | Representative frames | Challenge frames |
| --- | --- | --- |
| P001 | 50-74 | 200-224 |
| P002 | 250-274 | 25-49 |
| P003 | 300-324 | 150-174 |

The full scope is 150 frames: 145 localization-eligible and five hidden.
Representative and challenge pools remain separate. The selected 32-frame
diagnostic supplies case references; it is not the evaluation denominator.
All nine original prediction embargoes remain absent. P001 300-324, P002
200-224 and P003 250-274 remain sealed, with no holdout-content access.

There are 47,198 already-exported candidates from 600 completed crop views.
"All" means those saved, threshold-qualified candidates, including duplicate
crop hypotheses. It does not mean every detector hypothesis before export.
Preserve original confidence, center, box, crop-local index, global index,
descending global order and all provenance. Detector inference remains at
`1a9479f83a1766d8979fad07c604bc686d3c52c6`; saved motion controls remain at
`2274ab6097cd841421e2b606f723b047cd7dc62b`.

The JSON binds the six crop files, six reviewed annotation files, 126 selected
saved control outputs, two complete saved scoring pools and exact report
pointers, the completed diagnostic, review receipts, and 150 saved unmarked
source PNGs. Source-video metadata is preserved without opening or decoding
the videos. Selection reads candidates and source metadata only. Annotations
and pixels are restricted to subsequent scoring/review.

## Small paired design

Retain all four existing no-context motion settings as fixed probes. T/W mean
tight/wide movement allowance first, motion-cost scale second: .01/.03 source
image diagonals per source-frame interval. None is chosen as the preferred
tracker. Player-context and YOLO variants are outside this mechanism test;
its conclusions cannot establish cap effects for those methods.

| Fixed path scorer | Edge scale | Cost scale | Existing cap | Proposed retention |
| --- | ---: | ---: | ---: | --- |
| TT | .01 | .01 | 20 | All qualified saved candidates |
| TW | .01 | .03 | 20 | All qualified saved candidates |
| WT | .03 | .01 | 20 | All qualified saved candidates |
| WW | .03 | .03 | 20 | All qualified saved candidates |

Use only the existing confidence values .01, .20 and .35. The .01 floor
exposes the diagnosed cap loss; .20/.35 are the unchanged previous display
references. This is a fixed diagnostic subset, not a threshold search or a
selected operating point. Do not add intermediate thresholds after results.

Only **24 new graph outputs** are needed: four scorers times six windows at
.01. Reuse the seven saved control families (raw, top one, top twenty, and
TT/TW/WT/WW) at all three confidences, without rerunning selection or scoring.
Raw/top-twenty multi-candidate results describe availability and candidate
burden; their false-positive totals are not single-output tracker accuracy.

For the 48 higher-confidence graph/window settings, record structural
equivalence: every input frame, hence every five-frame horizon, has at most
twenty qualifying candidates. Their all-candidate interpretation references
the exact existing cap20 output and report bytes. Original headers must still
say cap20 and retain their original execution commits. A comparison record
must say `structural_equivalence_not_executed`; it must not pretend an
uncapped selector or new evaluator ran.

Compare cap20 versus all **at the same confidence and motion setting**.
Confidence contrasts .01 versus .20 and .01 versus .35 are separate, keeping
the cap policy fixed. A contrast changing both cutoff and cap cannot attribute
the difference to either one. The confidence threshold continues to control
which nodes can be emitted; no second output threshold, hysteresis or promotion
rule is introduced. A winning .01 candidate may be emitted with confidence
below .20. This is part of the tradeoff, not a confidence upgrade.

## Unchanged path contract

Change only the cap in both current-frame preprocessing and every historical
frame supplied to the graph. Keep all of these existing rules:

- Five-frame causal horizon, truncated at window start; no future frames,
  retrospective revision, cross-window state or leading-missing penalty.
- Edges only across one, two or three source-frame intervals, with distance
  at most `edge_scale * image_diagonal * elapsed_frames`.
- Singleton score is original confidence. Extension arithmetic is
  `((parent_score + confidence) - gap_cost) - motion_cost`, in binary64 and
  the existing traversal order. Gap cost is `.25 * (elapsed_frames - 1)`;
  motion cost is `.25 * (distance / (cost_scale * diagonal * elapsed_frames))**2`.
  No normalized-distance clipping or confidence recalibration.
- At most two trailing missing frames, costing .25 each; an empty hypothesis
  scores zero and wins zero-score ties. Equal paths use lexicographic original
  `(frame_index, candidate_index)` sequences. Other endpoint ties use latest
  frame, higher original confidence, lower original index, then path order.
- Emit the original candidate only if the winning endpoint is current.
  Otherwise emit null with the original reason. Preserve singleton starts.

No context term, appearance model, deduplication, geometric correction,
smoothing, interpolation, extrapolation, new abstention rule or court mask
is added. Scores and score margins are uncalibrated heuristic quantities.
Record candidate dispositions, every admissible edge and component cost,
best paths, competing endpoints, winner, margin, horizon and missing-output
reason. Lossless per-frame trace shards are allowed; dropping audit fields
or rounding scores to reduce size is not.

The retained graph is a superset of cap20. Every old path must remain feasible
with identical component scores, so the best score cannot decrease. That does
not guarantee more correct outputs or more current-frame emissions: a stronger
wrong path or older endpoint may win.

## Measurement and interpretation

Reuse raw center-distance matching at radii 5, 10, 15, 20 and 30 source pixels.
Uncertainty remains a diagnostic field, not an enlarged matching radius.
Keep hidden geometry null. Preserve original candidate indices and full
annotation/source provenance in all new reports.

Report both pools separately, every window and every frame, including:

- Stored, confidence-qualified, retained and newly admitted candidate counts;
  graph nodes/edges, trace bytes, elapsed time and peak worker memory.
- Candidate availability before filtering, after confidence, after cap and
  final path choice. Use ordered loss partitions so confidence and cap losses
  are not added twice. Higher-confidence cap loss is exactly zero here.
- Paired gained and lost matches, correct-to-wrong and wrong-to-correct
  choices, changed original endpoint indices, emissions versus missing output,
  longest missed runs and localization errors on shared matches.
- False observations on eligible frames and hidden alarms separately from
  candidate burden and duplicate false positives. Only five hidden frames
  from one episode exist; do not claim robust hidden-ball performance.
- Whether a changed output uses a newly admitted current candidate or changes
  the path to a previously retained candidate through newly admitted history.
  Preserve exact winning and competing path/cost evidence for both.

Carry forward the diagnostic's twenty persistent misses, eight cap-loss cases,
five hidden frames and seven controls as tagged subsets within the full 150.
Explicitly examine P001 51/59, P002 257/262 and P003 164/170 for identity versus
center-placement ambiguity; also retain all flight and reacquisition controls.
Show improvements and regressions without picking only favorable examples.
Repeated frames, thresholds, radii and crop hypotheses are not independent
samples. No statistical generalization or trained-verifier claim follows.

| Artifact / comparison unit | Existing distinct | New distinct | Distinct total | Additional equivalence references |
| --- | ---: | ---: | ---: | ---: |
| Window observations | 126 | 24 | 150 | 48 |
| Window/radius reports | 630 | 120 | 750 | 240 |
| Aggregate cells per separate pool | 105 | 20 | 125 | 40 |

Thus the comparison table has 198 observation entries, 990 report entries and
165 aggregate entries per pool, while only the new-distinct column requires
selection/scoring. Equivalence references are not additional trials or files.
There are 120 newly scored same-threshold cap contrasts and 20 per-pool
aggregate cap contrasts; higher-confidence contrasts are exact zero by the
structural certificate. Do not tune parameters or choose a quality cutoff.

## Resource bounds and validation

The source inventory reaches 400 candidates in one frame and 1,924 in a
five-frame horizon. The current nested-loop traversal would visit 165,815,730
prior-node pairs per motion family across the six windows, before temporal
and spatial rejection; four families total 663,262,920 visits. These are
count-derived upper-work inventories, not measured runtime or executed graphs.
The cap20 input has 3,000 retained nodes across the 150 frames at .01; all
retains 47,198. Candidate count therefore rises about 15.7-fold, while pair
work can rise much faster.

Proposed execution limits: one worker, at most 8 GiB combined resident memory
for its process tree, 32 GiB for the entire new output root, and at least
10 GiB remaining free disk. The 32 GiB includes partial shards, temporary
serialization files, logs and playback copies; new run temporaries stay inside
that root. Allow at most 30 minutes for each window/scorer selection unit,
including loading, selection, trace writing and unit verification. Allow four
cumulative active worker hours for all real preflight, selection, scoring,
rendering and verification, including failed attempts and resumed work. A
resume does not reset either consumed budget; idle time between invocations
and human review is excluded. Synthetic implementation tests have separate
recorded validation costs and do not consume this real-run budget.

Monitor memory, bytes, free space and elapsed budgets at least once per second
and between stages. On crossing a limit, stop the worker tree, record measured
usage and any overshoot, and mark the unit incomplete. A monitoring interval
is not permission to report an over-budget run as compliant. These are resource
limits, not ball-tracking quality gates. Benchmark fabricated
dense and sparse 400-candidate/25-frame fixtures before any real execution;
verify bounded memory, complete trace serialization and safe abort behavior.
Do not claim the real run will fit until this implementation evidence exists.

Process and checkpoint units independently in immutable, resumable outputs.
At a limit, retain a failure receipt and completed units, mark the comparison
incomplete and stop. Never silently truncate, deduplicate, approximate, skip
a window, change the horizon or fall back to cap20. A budget or design change
requires a revised explicit scope; no result-dependent workaround is allowed.

Focused synthetic tests must cover original indices beyond 20, inclusive
thresholds, stable equal-confidence order, cap application throughout history,
exhaustive small-graph path enumeration, all four edge/cost settings, ties,
gaps, horizon expiry, nulls, window resets and no annotation/future access.
Verify old paths remain feasible, cap20 exact parity and all-candidate equality
when every frame has at most twenty nodes. A graph-score increase must not be
misreported as an accuracy improvement. Test alias provenance, tamper rejection,
partial resume, resource abort, report partitions and final-frame rendering.
Run focused tests and then the full suite with bytecode disabled.

Existing `validate_observations()` rederives rankings, and old review entry
points may score or decode footage. They must not be used as saved-control
loaders. New reuse paths verify frozen bytes, configuration keys, canonical
content hashes and JSON pointers without calling selectors/evaluators.

## Review and execution boundary

If approved and successfully executed, create **six new .01 comparison clips**,
one per window, all 25 frames at 5 fps and display radius 10. Use four rows:
TT, TW, WT, WW; first column saved cap20, second new all-candidate output;
third column unmarked source, saved raw reference, saved top-twenty reference,
then legend. Label motion scales, confidence, cap policy and missing output.
Raw references show candidate availability, not an asserted ball trajectory.

Use only the 150 bound saved unmarked PNGs. Make fresh .01 overlays from
saved control observations and new outputs, native views, source-scale
closeups and complete mosaics. This is new review presentation of frozen
controls, not rerunning their selection/scoring. No source-video decode.
Validate every clip's first/final source indices, 25 frames and final panels.
Ryan reviews these six new clips through their final frames. Existing .20/.35
motion review and all twelve YOLO final-frame approvals remain complete and
must not be requested again. No new human object-identity labeling is implied.

Proposed output root:
`data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/`.
Keep all existing evidence immutable. Bind the new implementation/selection,
evaluation and rendering commits separately from actual detector and reused
control provenance. The already completed diagnostic's dirty helper hashes
remain explicit; its creation HEAD is not an inference or implementation claim.

This turn prepares documents and source inventories only. The next step is
review of this exact proposal. Implementation and real execution remain
unapproved. Future execution requires scope-bound authorization, tested
implementation, resource checks and a clean committed checkpoint. Staging,
committing, pushing, PR creation and merging each still require separate
explicit authorization. No upstream player decision changes and no
`--rerun-from` stage is needed. Stop on a bound-input change and identify its
upstream/downstream effects before revising the scope.
