# Retained-model temporal gap selection: one bounded trial

## Prospective decision and authorization

Ryan's “Ok awesome move forward chat” authorizes the next fixed temporal
selection trial proposed after candidate preservation. Starting state:
`codex/ball-detector-baseline`, clean at
`ae7ad9a28de9691296eb3b567398b69ff4814b4f`. The retained expanded model is
`09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98`.
The failed NBA continuation remains rejected. This trial uses the already
audited **old-arm** pool; it needs no fit, inference, checkpoint load, new
heatmap processing, annotation edits or protected data.

The question is whether a conservative temporal rule can turn some of the
newly available candidates into correct selected points while preserving the
existing error limits. The nine newly available DET/NFHS frames are an upper
bound, not an expected gain. Thirty-six eligible development frames still have
no matching candidate in this pool. This rule also cannot correct a wrong
existing prediction, recover a long gap, or demonstrate full-possession quality.

## Fixed context and policy

Use all 790 original scored frames in the twelve original contiguous windows:
300 SAC, 340 DET, and six 25-frame NFHS windows. The 120 easy controls are
included subsets. Preserve all 652 eligible, 91 hidden and 47 unknown rows.
Use the original pool coordinates and contributor contexts exactly as saved;
do not recompute means with different boundaries. Selector state resets at
every window boundary. There is no tracking across unexamined gaps between
windows. This is a short-window development trial, not a continuous NBA-core
or long-context NFHS evaluation.

Apply exactly one rule, with no subsequent parameter or threshold sweep:

1. Preserve every original nonmissing selected point exactly. Do not change its
   coordinates, selection or meaning, including an out-of-image original point.
2. Find maximal runs of **originally** missing points within each window.
   A run needs an original nonmissing, in-image point immediately before and
   after it. Window-edge runs remain missing.
3. Using source presentation timestamps (PTS), require the time between those
   anchors to be at most **0.12 seconds**, inclusive, and their displacement
   divided by elapsed time to be at most **one source-image diagonal per second**.
   The native 60-ish fps NBA and 25 fps NFHS cadence must not share a
   per-frame speed allowance.
4. For each missing frame in that run, linearly interpolate the two anchors
   **only to obtain an expected position for ranking**. Keep all saved in-image
   candidate coordinates within **0.006 image diagonals**, inclusive, of that
   expectation. Exact duplicate coordinates do not gain extra weight.
5. If any frame has no such coordinate, or the maximum pairwise separation
   of its plausible coordinates exceeds **0.006 image diagonals**, abstain
   for the **entire** run. This rejects spatial ambiguity rather than treating
   correlated contributor counts as independent confidence.
6. Otherwise choose the saved coordinate nearest the expected position,
   breaking ties by its earliest original pool-record index. Emit that exact
   saved coordinate and retain its original provenance. New points never
   become anchors for another decision.

The numeric settings are fixed engineering hypotheses, not learned estimates,
confidence probabilities or acceptance thresholds. A 0.12-second anchor span
permits only very short gaps; 0.006 diagonals is about 13.2 pixels at 1920×1080.
The spatial tolerance governs temporal consistency, not reference matching.
Reference matching remains the independent, unchanged inclusive ten-pixel rule.
Linear image motion can fail at bounces, camera changes or accelerations; an
existing false anchor can also support a false candidate. These are measured
risks, not reasons to relabel a bad result.

This is an offline rule with explicit future-anchor context, in addition to the
original model's future-image context. It is not causal/live tracking. It differs
from the earlier negative motion selector: there is no greedy propagation,
immediate maximum-mass reacquisition, existing-point replacement, or per-frame
velocity gate. It is deliberately a limited repair operation.

## Label separation, comparison and decision

The selector receives an explicit projection containing only source/window/frame
identifiers, dimensions, PTS, original centers and saved candidate coordinates
with provenance. It receives no annotations, eligibility, cohort, control flags,
old scores or availability diagnostics. Persist all 790 choices **before**
passing labels to evaluation. Development labels were inspected in prior work;
this separation does not make these windows an independent test.

Reproduce original selected outcomes and errors against the bound original
report. Compare actual selected outputs, not label-selected candidate availability.
Report group and window counts, controls, visibility, unknowns, paired outcome
transitions, emitted-position errors, changed frames and missing intervals.
SAC is reported separately as previously used training evidence.

Retain all nine original adaptation conditions: DET matches at least 208,
missing at most 21, wrong at most 8, hidden alarms at most 13, and 60/60 easy
controls; NFHS matches at least 130, missing at most 14, wrong at most one,
and zero hidden alarms. Also retain SAC's 60/60 easy controls and require no
additional wrong outputs or hidden alarms in **any** group relative to its
original control. Human review is a separate necessary condition. No numeric
pass promotes the model, replaces a baseline, establishes full-game performance,
or completes the ball phase.

If the trial fails, preserve that result and do not tune this rule on the same
windows or automatically launch another diagnostic. If it passes, publish the
specific increment and its limits, with actual trajectory review still pending.
Any broader continuous-context integration is a separate scope decision.

## Validation and delivery

Use focused tests for timestamp boundaries, ambiguity, missing edges,
all-or-none decisions, exact candidate provenance, label separation and actual
producer transport. Validate the bound report and original window inventory.
Run the fixed selector once; record runtime and failures without overwriting
attempts. An independent audit checks all emitted choices, scores, gates,
unchanged predictions and source membership.

Render three synchronized comparison videos covering every trial frame:
SAC, DET and the six NFHS windows. Show original selection and gap repair on
the same source image, accepted labels separately, explicit missing states,
window/source-frame/PTS identifiers and a shared zoom. Clearly mark window
changes. NBA plays at 30 fps and NFHS at 6 fps, with a one-second final hold
at **each** window's last frame. Verify every encoded frame's identity and timing,
paired pixels and final frame. These are source/ball comparisons; they do not
claim completion of the full synchronized player/ball pipeline milestone.

Keep generated media and full reports ignored. Retain a compact committed result
and update current context. Local staging/commit authorization carries forward;
push, PR and merge remain unauthorized. Existing baseline trajectories and
upstream reviewed decisions are unchanged, so no production rerun stage is
invoked. A future integration must declare its downstream effects.

## Execution result

Pending the frozen single run. A byte-bound copy of the prospective text above
will be saved before execution; later results belong below this section.


## Completed single-run result

The prospective text above is preserved byte-for-byte, including its historical
pending-result line. Ryan approved the fixed trial with “Ok awesome move forward
chat”. The [frozen scope](../configs/ball_tracking/selections/nba_temporal_gap_selection_v0_1.json)
and [compact result](../configs/ball_tracking/reviews/nba_temporal_gap_selection_result_v0_1.json)
bind the evidence. One selector/scoring run completed in **0.391 seconds**.
All 790 choices were written before scoring; there was no parameter sweep.

| Group | Matched, original → selected | Wrong | Missing, original → selected | Hidden alarms |
| --- | ---: | ---: | ---: | ---: |
| SAC training-fit, 270 eligible | 218 → 218 | 5 → 5 | 47 → 47 | 0 → 0 / 17 |
| DET development, 237 eligible | 207 → 209 | 8 → 8 | 22 → 20 | 13 → 13 / 69 |
| NFHS development, 145 eligible | 130 → 131 | 1 → 1 | 14 → 13 | 0 → 0 / 5 |

Both NBA easy controls remain 60/60. The 47 other unscored frames preserve their
uncertainty. All sixteen fixed numeric conditions pass: the nine original
adaptation conditions, SAC's easy control and no additional wrong outputs or
hidden alarms in each of the three groups. **Human review remains pending;
this is not acceptance or baseline replacement.**

Only three source frames changed, each originally missing and now matched:

| Source/window | Frame | Error to accepted center | Saved candidate origin |
| --- | ---: | ---: | --- |
| DET drive/rim overlap | 11437 | 4.879 px | triplet 11435, channel 2, component 0 |
| DET drive/rim overlap | 11438 | 4.556 px | triplet 11438, channel 0, component 0 |
| P001 challenge, frames 200–224 | 208 | 1.938 px | triplet 208, channel 0, component 0 |

The rule fills two maximal gaps. It abstains on eleven gaps whose anchor span
exceeds 0.12 seconds, one whose speed exceeds one diagonal per second, three
with an empty or ambiguous plausible set, and three window-edge gaps. These
reasons are fixed-rule decisions, not post-result tuning. Every original point,
component identity and native score is retained exactly. Candidate provenance
is separate from the original mean-component index; no interpolated coordinate
is emitted. Missing intervals distinguish eligible errors from all null outputs,
and final-window duration is marked right-censored when a following native
frame is outside scope.

Thirteen distinct focused tests passed on their first commands: eight selector
and five renderer checks. The selector tests cover producer
transport, exact timing and spatial boundaries, ambiguity, all-or-none behavior,
label separation and failed-attempt preservation; the synthetic scoring failure
is a deliberate test, not an actual experiment failure. Renderer checks include
actual selector records consumed by the review join. No full
suite was repeated. The selector itself made no model calls, checkpoint loads,
heatmap-array reads or source/media decodes. Its runtime excludes audit and
review-video production.

Independent audit passed **165,219 checks in 0.281 seconds** on its first
attempt. It independently verifies all 790 source/label joins and choices,
1,580 before/after scores, twenty maximal gaps, missing intervals and all
sixteen conditions. All 597 original emitted points are unchanged; two gaps
are filled and eighteen remain abstained. The audit used no model, heatmap
arrays or source/media decoding. Producer and audit each completed once with
no actual failed attempt.

All three comparison videos completed on their first attempts and passed
verification for every source key, native timestamp, encoded duration, source
PNG/RGB identity and paired image. Each window has a one-second final hold;
twelve actual encoded final-frame images were verified. Rendering plus complete
verification took **306.063 seconds**, separately from the selector and audit.

| Verified comparison | Source frames | Playback duration |
| --- | ---: | ---: |
| [SAC: original / gap selection](../data/outputs/ball_tracking/nba/temporal_gap_selection_v0_1/review/sac_training_fit/attempts/cacc463c9c8048a3bfc6a5e8d17488cc/review.mp4) | 300 | 13 seconds |
| [DET: original / gap selection](../data/outputs/ball_tracking/nba/temporal_gap_selection_v0_1/review/det_development/attempts/adb74988de4c43e09dc85e76bd8d0507/review.mp4) | 340 | 14.333333 seconds |
| [NFHS: all six windows](../data/outputs/ball_tracking/nba/temporal_gap_selection_v0_1/review/nfhs_development/attempts/09cea1318de1465987ec34e01c68b4d1/review.mp4) | 150 | 31 seconds |

AI visual inspection covered the three actual encoded changed frames and all
twelve actual encoded window finals. The added markers appear near the accepted
cyan references; known missing finals at P001/224 and P002/49 and the original
DET/11579 offset remain unchanged in both panels. This was sampled AI inspection,
not continuous manual review of all 790 frames. **Ryan's human review is pending.**

This is a measured **three-frame gain** on correlated development windows. It
does not resolve the broader missing-ball problem, existing wrong selections,
long gaps or continuous possession tracking. The retained expanded checkpoint
and its original outputs remain intact; the unsuccessful NBA continuation stays
rejected. Protected holdouts, DET's exclusion from fitting, the NFHS finish line
and three earlier pending motion reviews are unchanged.

Next, review these three comparisons. After review, prepare a bounded
continuous-context validation/integration plan with explicit window boundaries,
future-context allowances, missingness and unchanged quality gates. This pass
does not automatically authorize broader inference, a new fit, a parameter
sweep or a full-game run.
