# Test agreement between the two saved ball detectors

Status: proposed; no implementation, validation or scientific execution authorized.
Prepared 2026-10-07 (America/Phoenix) on `codex/ball-detector-baseline` at
`b71c64d3fd46bb27072efa8644e90c1c222bb65c`. Ryan's "beautiful chat move forward"
authorized preparing this proposal following the simple explanation, not running it.
The companion specification is
`configs/ball_tracking/proposals/rfdetr_yolo_crop_corroboration_v0_1.json`.

## In plain language

We already have guesses from two different detectors, RF-DETR and YOLO. Test
whether asking them to point to roughly the same object helps us choose the ball
and leave fewer guesses on shoes, people or other objects. If their boxes do not
agree, leave the answer blank. If a lower-ranked RF-DETR guess agrees, consider
that guess instead. Keep its original center unchanged.

This could also remove real-ball sightings. Two detectors can agree on the same
wrong object, and boxes around the same ball can differ in size. The test must
show those costs as clearly as any improvement. It does not recognize occlusion:
a blank means "no accepted observation," not "the ball is hidden."

## Why this question now

The mean comparison, six qualitative clip responses and joint 16-frame diagnostic
review are complete. They distinguish other-object marks, ball-center offsets
and absent output; no method or quality gate was selected. In particular,
P003/164 remains a human on-ball, slightly-left judgment despite its saved
distance-based wrong-present state. The human/AI qualifications remain intact.

Completed temporal association already tested tentative starts, confirmation,
loss and reacquisition. The motion study also showed persistent wrong paths and
valid singleton reacquisition. Merely waiting for repeated guesses would not add
new identity evidence. Agreement among TT, mean and top-one would reuse one
detector's candidates; the joint review already includes their shared foot errors.

The completed YOLO comparison supplied different learned detector outputs. Its
lower candidate coverage is a warning, but does not answer whether those outputs
can corroborate RF-DETR selections. At .01/raw10 the recorded availability was
RF 140/145 and YOLO 87/145 eligible frames. The latter is not a mathematical
ceiling on this rule: a correctly centered RF box can overlap a YOLO box whose
center misses raw10. Those are copied historical results, not fresh measurements.

Both detectors saw the same pixels and have overlapping training provenance.
Their agreement is correlated evidence, not independent confirmation of identity.
This is one development comparison, not a trained appearance verifier, a claim
about unseen footage, or another confidence/movement parameter sweep.

## One frozen rule

Arm: `rfdetr_yolo_box_corroborated_top_one`.

1. Use every already exported RF and YOLO sports-ball candidate at the inherited
   inclusive confidence floor .01 in the same source frame. Preserve each
   detector's existing export/postprocessing limits. Add no top-twenty cap,
   deduplication or filtering by player location; an extra cap would introduce
   another source of lost candidates.
2. An RF candidate is supported if at least one YOLO box in that frame has
   intersection-over-union (IoU) at least .50 with its box. IoU is the shared box
   area divided by the area covered by either box. It compares rectangles, not
   certified physical objects. .50 is a fixed experimental choice; it was not
   fitted to the reviewed errors and is not a calibrated quality threshold.
3. Select the supported RF candidate with greatest original RF confidence,
   then lowest original RF candidate index on an exact tie. YOLO confidence
   serves only its own .01 inclusion test. Never add or average detector scores.
4. If no RF candidate is supported, emit nothing. Otherwise emit that original
   RF box, center, index and confidence unchanged. Multiple supporting YOLO
   boxes provide no extra ranking reward.

Startup and reacquisition use this same current-frame rule immediately. Loss
of support means immediate missing output. There is no warmup, prior-target
preference, state carry, motion gate, coordinate fusion, interpolation,
extrapolation or access to future frames. This isolates same-frame corroboration;
it does not claim to produce a robust temporal track.

Use source-pixel `(x1,y1,x2,y2)` rectangles and binary64 arithmetic. Width and
height are differences, without a `+1` pixel convention. For RF box r and YOLO
box y, compute `intersection = max(0,min(r.x2,y.x2)-max(r.x1,y.x1)) *
max(0,min(r.y2,y.y2)-max(r.y1,y.y1))`, then
`union = (area_r + area_y) - intersection`, then `IoU = intersection / union`.
Compare directly with .50; use no tolerance in eligibility or ranking. Invalid
or nonfinite boxes, nonpositive union, missing required provenance or misaligned
inputs fail the entire authorized comparison closed. Never silently drop a bad
candidate or turn an input failure into scientific abstention. Preserve failure
evidence; no partial selection package becomes a valid completed result.

Candidate references include detector/input binding, source frame and original
index. Equal RF/YOLO indices do not imply the same object. Validate source hash
metadata, dimensions, window and exact frame alignment before joining inputs;
do not decode or hash source videos to fill missing provenance.

Audit each RF candidate's inclusion, maximum IoU, deterministic witness YOLO
index (lowest original index for an exact maximum tie), count of supporters,
support decision and emission/rejection reason. With no YOLO candidates the
maximum/witness are null and support count is zero. Original input bindings
make all pair comparisons reconstructible. Store this linear-size witness
record, not a dense pair matrix; scan pairs in bounded chunks with cancellation
checks. The rule examines all candidates without keeping all pairs in memory.

## Intended future comparison

| Possession | Representative frames | Challenge frames |
| --- | --- | --- |
| P001 | 50-74 | 200-224 |
| P002 | 250-274 | 25-49 |
| P003 | 300-324 | 150-174 |

The same six windows contain 150 frames, 145 localization-eligible labels and
five saved hidden frames, P003/165-169. No added footage, labels, holdouts,
threshold grid or model inference is proposed. Use the unchanged raw-center
evaluator at .01 and radius 10 source pixels. The .01/.50 selection settings
above must be frozen before any new real-data selection or result inspection.

Primary control: saved RF crop top-one at .01. Saved TT and mean at .01 are
descriptive references, not additional newly run selectors. Do not compare
primarily against .20/.35 or replace the primary control after seeing results.
Copy the controls' existing scored reports and actual provenance; never rerun
their selection, scoring or completed review packages.

For each window and each separate representative/challenge pool, report:

- Matched, wrong-present and missing eligible frames with denominators and exact
  frame lists; hidden alarms separately. A wrong present observation is also a
  missed eligible frame, so do not count it twice in a combined error total.
- Paired 3-by-3 state transitions against every control. Against top-one also
  distinguish retained original choices, suppressed choices and replacements
  with lower-ranked RF candidates. Show correct choices lost, errors suppressed,
  matches recovered, and wrong replacements without conflating these outcomes.
- Original RF candidate availability and corroborated-candidate availability
  at raw10, calculated only after selection is sealed. These are label-assisted
  localization diagnostics, not selection inputs or semantic identity labels.
- Correct runs and missed-eligible runs; hidden/ineligible frames break runs.
  Keep windows separate. Show all five hidden frames and the unchanged P003
  boundary frames 163-164 and 170-174, including all arms' first subsequent
  raw10 match in 170-174 (null if none). Report frame/time delay from 170 and
  whether 170 itself had an available raw10 candidate. This is recovery in one
  selected episode, not a general reacquisition guarantee.
- First-frame behavior in every window and paired original center errors on
  frames matched by both arms: old error, new error, difference and whether
  the original RF candidate stayed the same or was replaced. Replacement can
  change the error even though each candidate's own geometry remains unchanged.
  Do not impose the old mean experiment's startup-parity requirement: this new
  rule can intentionally withhold the first-frame top-one choice.

Matched-to-missing is a lost useful observation. Wrong-present-to-missing is
suppression of a false output, not a recovered match. Center-distance failure
does not by itself establish another object's identity. Keep those distinctions
even if the overall result looks favorable.

## Interpretation and new visual review

Use these classifications, in order, against saved RF top-one:

1. `favorable_development`: every window has zero matched-to-wrong-present and
   zero matched-to-missing transitions, no increase in wrong-present count,
   no increase in hidden-alarm count and no new hidden-alarm frame. Require
   at least one strict matched-count gain, wrong-present-count reduction or
   hidden-alarm-count reduction somewhere. Missingness may increase through
   wrong-present-to-missing changes, never through lost baseline matches.
2. `unchanged_measured_outcomes`: every eligible frame has the same three-state
   outcome and every hidden frame has the same alarm status. Changed candidate
   identities and center errors must still be shown; this is not byte equality.
3. `not_favorable`: every other valid completed comparison. Describe any gains
   alongside losses as a tradeoff; report pure regressions plainly. In
   particular, any lost baseline match excludes the favorable classification,
   even if another frame supplies an offsetting gain.

A favorable result must say whether it improves raw10 matched-frame coverage,
suppresses wrong outputs, or both. Suppression alone never counts as recovered
localization; a match gain does not establish better centering or physical
identity. Always report complete window and pool counts, including descriptive
TT/mean regressions. No significance claim, production gate or method promotion
follows from this small, repeatedly inspected development set.

A later execution scope must include six new synchronized 25-frame clips at
5 fps and native overlays/indexed changed decisions through every final frame.
Use source, saved RF top-one and new-output panels; keep reference markings
distinct from predictions. Include lost correct choices as well as apparent
gains. Existing TT/mean review media and the completed 48-image diagnostic
remain closed unless a later scope expressly binds a new presentation need.

Ryan retains human visual authority. If specific new judgments are requested,
seal Codex observations before asking Ryan, keep both records separately, and
preserve uncertainty. Prior judgments attach only to their original candidate
and image, not automatically to a replacement. Completed old reviews are not
reopened; new review evaluates the newly produced comparison. Lack of support
does not supply a new hidden label, and the original center annotations stay fixed.

## Approval requested first: implementation and artificial validation only

This proposal deliberately separates two approvals. The first would permit
new corroboration selector, adapter/evaluation, guarded orchestration and review
support, using artificial fixtures only. Proposed implementation scope is four
new `src/ball_tracking/crop_cross_detector_corroboration*.py` modules and four
matching test modules, enumerated in the JSON. Keep the old selectors,
evaluators, monitor, schemas, scientific manifests and six current unstaged
files unchanged. A necessary broader source edit requires a scope amendment.

Reuse pure evaluation summaries/transitions and the existing evaluator for new
outputs only. Do not call old observation validators that rerun selectors. Do
not reuse mean-specific assumptions that a ranking winner must emit or that
startup must equal all controls. Reuse the responsive monitor's policy, without
repeating its completed benchmarks or modifying historical release validation.
Real execution entry points must fail closed without a future exact approved
inventory, consumed-attempt protection, clean implementation certificate and
new release receipt. No real-science access is permitted by artificial tests.

Meaningful artificial checks cover exact IoU boundary/disjoint/contained boxes,
source mismatch and detector namespaces, absent candidates, deterministic ties,
all-candidate coverage including a supported candidate below rank twenty,
replacement versus withholding, unchanged geometry/confidence, duplicate support
without reward, immediate startup/loss/reacquisition, refusal of invalid input,
bounded streaming/cancellation, phase isolation, immutable saved controls,
complete transition accounting and rejection without later execution authority.
Use explicit fixtures where two detectors agree on a non-ball distractor: support
must not be reported as a semantic identity verdict or calibrated probability.

After code exists, run focused tests, then the required full suite with
`.venv\Scripts\python.exe -B`. Propose a NEW artificial-validation ceiling of
4,200 supervised seconds total, focused invocation <=600 and full <=3,600,
including necessary corrections. This is not reuse/reset of the previous
2,164.2970000000005 consumed seconds. Bound new validation to 8 GiB sampled
combined memory, >=50 GiB free disk, and 4 GiB aggregate new outputs/temporaries;
account for fixtures outside the chosen temporary directory. Save create-only
records under `data/outputs/t/corroboration_validation_b71c64d3fd46/` if approved.
Ordinary helper failures can be corrected within these limits; material
correctness, evidence, resource or scope problems require investigation.

No tests, synthetic experiment, package installation or model loading are
authorized merely by preparing this document. Approval is still pending.

## Second boundary: an exact real-execution request

Before requesting real execution, bind exact saved RF and YOLO candidates,
controls/reports, labels and source PNGs using their existing administrative
receipts and metadata. This proposal intentionally has no executable input
inventory. The mean proposal binds 176 older inputs but does not bind the new
mean outputs or saved YOLO candidate bodies; do not silently extend it.

That later request must specify each path/hash/size, phase access, output name
and per-file/aggregate bounds, selected code commit and independent review.
Selection may see only the two candidate inventories and source metadata.
Freeze all six new selections before reading labels, old scoring bodies or
pixels. Only the owned monitored worker may then verify/read the approved
scientific inputs, score the new arm, copy saved controls and render the new
review package. The parent receives a bounded administrative return.

Planning ceiling for that future request: one distinct attempt, <=1,200 charged
seconds, <=4 GiB new aggregate artifacts/temporaries within the existing 32 GiB
root cap, bounded parent return <=512 KiB, receipt <=1 MiB, no automatic retry
or fallback. Use the unchanged responsive monitor and its memory/free-space,
scan freshness, timeout and owned-cleanup safeguards. This is a proposed maximum,
not a reservation, renewed budget, launch permission or runtime promise. If
complete processing does not fit, preserve the failure and propose a change;
never silently truncate candidates or adopt partial windows.

Separately authorized staging/committing and a clean tested implementation
checkpoint are prerequisites to that future launch. Do not discard the six
current files to obtain cleanliness. Push, PR and merge remain separately
authorized steps. No player-pipeline `--rerun-from` stage applies.

## Preserved state and preparation scope

The handoff binds 3,330 resource events and 63 closed attempts (59 successes,
four historical failures); scientific seconds consumed
`3547.523999999985`, remaining `10852.476000000015` of 14,400. All attempts remain
consumed; all historical failures and 636 mean artifacts remain preserved.
Old validation stays 55 focused passes, 1,103 full passes and one existing skip.

Preserve all six unstaged files byte-for-byte, the completed human/AI reviews,
nine original prediction embargoes, and sealed holdouts P001 300-324,
P002 200-224, P003 250-274. There is no label correction, new inference, holdout
access/release, scientific-body read/hash or media access during preparation.
Do not replay the resource journal or old tests, experiments, reviews, renders
or release checkpoints. No existing approval is renewed by unused time.

Preparation adds only this document and its companion specification. Current
authorization covers preparing/discussing those two files only; implementation,
validation, real execution, new visual review and every Git mutation remain
unapproved. If this fixed comparison later loses useful balls or accepts common
distractors, record that result; do not tune .50 on these windows. A semantic
candidate-label/appearance-verifier design would need a separate proposal.

Design sources: the complete October 7 handoff and completed joint review;
`docs/ball_crop_motion_factorial_results.md`,
`docs/ball_candidate_identity_diagnosis.md`,
`docs/ball_yolo11x_crop_recovery_results.md`, and existing detector, temporal,
mean-comparison and evaluator source. Scientific bodies and pixels stayed closed.
