# Candidate preservation from saved WASB outputs

Ryan authorized this experiment after the 37-frame diagnostic, asking for a
carefully developed comparison, concrete progress and efficient use of resources
under the existing quality requirements. Starting state: clean
`codex/ball-detector-baseline` at `14f5ce7aa986ae3454b2e3cd4bbc4617c55673bd`.
This document records the design before numerical execution. Results will be
appended after the frozen comparison completes.

## Decision this experiment must resolve

Does the existing visual evidence contain accurate ball candidates that are lost
when overlapping predictions are averaged? If so, how much extra ambiguity and
hidden-ball clutter must a future selector handle? This experiment ends with a
decision about further candidate-selection work. It does not itself select new
predictions, accept a checkpoint or complete the ball-tracking phase.

The retained expanded checkpoint is the primary arm. The unsuccessful NBA
continuation is a separate diagnostic arm; their candidates are never combined.
The prior failed trial and the ten-pixel quality requirements remain unchanged.

## Frozen comparison

Use all 790 existing labeled frames: SAC 300, DET 340 and six NFHS development
windows totaling 150. The 120 easy NBA controls are included subsets. There are
652 localization-eligible frames, 91 hidden frames and 47 other unscored frames.
Keep SAC training-fit evidence separate from DET and NFHS development evidence.
TOR, protected NFHS holdouts and buffers are excluded.

For each frame and checkpoint, compare two pools:

1. The complete published mean-map candidate pool.
2. That same pool plus every in-image component above the original strict
   `>0.3` threshold in each original contributor prediction for that frame.

Preserve original float32 averaging, complete original contributor contexts,
source-frame/PTS mappings, accepted labels, uncertainty and inclusive ten-source-
pixel matching radius. Reproduce the original mean, candidates, selected output
and score before measuring the added pool. Existing mean-pool availability is
not always the selected-output count: old/new availability is SAC 218/266,
DET 207/207 and NFHS 130/129.

Keep every candidate's checkpoint, source/window, frame, plane kind, triplet
start/channel and component index. There is no spatial suppression, proximity
merging or threshold search. Report both raw provenance-record counts and
groups of exactly equal floating-point coordinates. These groups are not counts
of distinct physical balls. Original out-of-image mean records remain recorded;
only in-image centers can match, and only in-image contributor candidates are
added. Annotation geometry is used for evaluation only.

## Readouts and advance/stop screen

For each checkpoint, domain and reference window, report:

- availability of any candidate within the fixed radius, newly available frames
  and remaining unavailable frames;
- raw and exact-coordinate candidate counts, added nonmatching candidates and
  median, 95th-percentile and maximum burden;
- frames containing both matching and nonmatching candidates, wrong-only pools
  and empty pools;
- hidden frames newly becoming nonempty, and burden on already nonempty hidden
  frames; other unknown geometry remains unscored;
- easy-control subsets and gains outside the ten prior diagnostic anchors,
  with gains outside the entire previous 37-frame scope also reported.

Because the old pool is retained, losing candidate availability is an
implementation failure. Zero availability losses are therefore a structural
property, not evidence of improved selection accuracy. A reference-informed
best-candidate count is an upper bound on what a selector could achieve; a
deployable selector does not have access to reference labels.

Before execution, fix this minimal usefulness screen: the retained baseline
must gain at least one previously unavailable, non-anchor eligible frame in
**each** of DET and NFHS. Failure rejects further broad candidate-pool work on
this evidence. Passing only supports one future, predeclared, label-blind
selection experiment. It is an analyst-chosen minimum for deciding where to
spend effort, not a new scientific quality gate, statistical significance or a
phase pass. Added hidden-frame clutter and ambiguity remain explicit costs;
they are not subtracted from localization gains to manufacture a net score.
The original ten anchors are fixed by the preceding diagnostic scope. None of
these previously inspected development frames becomes an independent test.

## Execution and proportional validation

Reuse the verified read-only cache loader and native component producer. The
metadata inventory requires 1,580 distinct caches (790 per checkpoint), totaling
2,519,893,616 compressed bytes, plus six original NFHS mean bundles totaling
79,271,884 bytes. Measure 4,668 original contributor planes and 1,580 means.
Keep a rolling cache of at most three triplets and one NFHS bundle at a time.
These array inventories do not claim to measure total process RAM.

Run focused producer/consumer and policy-boundary tests, followed by one real
cached-output run. Preserve failed attempts if any. Independently verify all
emitted frame-arm memberships, labels, summaries and decision counts. Numerically
audit all claimed availability gains and newly nonempty hidden cases, the prior
anchors, and deterministic unchanged endpoint/midpoint samples in every window
and checkpoint. Disclose the actual numerical audit coverage rather than
claiming a second full reconstruction.

No model inference, training, checkpoint deserialization, source image/video
decoding, label edits, prediction replacement or holdout access is needed.
No new trajectory review is implied by unchanged selected outputs. Old NFHS
cache lineage retains its historical limitation: source/window/frame and model
identity were saved, but captured PNG/PTS hashes were not.

## Execution result

Pending the approved frozen run. The existing baseline and prior comparison
remain unchanged.

### Completed comparison

This post-execution result supersedes the pending status in the frozen design
above. One **22.094-second** run completed all 790 frames, 1,580 means and
4,668 contributor planes. The minimum usefulness screen passes: the retained
baseline gains candidate availability beyond the ten diagnostic anchors in
both DET and NFHS. This supports one bounded selector trial, not a quality pass.

| Retained baseline | Eligible frames | Matching candidate available, mean → expanded pool | Hidden frames nonempty | Ambiguous eligible frames |
| --- | ---: | ---: | ---: | ---: |
| DET development | 237 | 207 → 213 (+6) | 13 → 18 of 69 | 21 → 53 |
| NFHS development | 145 | 130 → 133 (+3) | 0 → 0 of 5 | 27 → 46 |

An ambiguous frame contains both matching and nonmatching candidates. The nine
gains cover **20% of the 45 previously unavailable development frames**;
**36 still have no matching candidate**, so selection from this pool cannot
repair them. Five DET and two NFHS gains lie outside the ten anchors; five DET
and one NFHS gain lie outside the entire prior 37-frame context. The three NFHS
gains are P001/208, 217 and 221; only 217 is outside that context.

The cost is substantial: 51 more ambiguous development frames, five newly
nonempty DET hidden frames, and median raw candidate records rising from one
to four per frame in both development groups. The easy controls retain 120/120
availability, but their ambiguous frames rise from seven to 20. These are
candidate-pool costs, not newly selected false predictions.

SAC remains separate: baseline availability is 218→227/270, while the unsuccessful
continuation's training-fit availability is 266→270/270. That diagnostic arm gives
DET 207→212/237 and NFHS 129→136/145, with DET hidden nonempty frames rising from
nine to 21. Its candidates are not combined with the retained baseline. Availability
is an upper bound using reference labels; it is not selected-output accuracy.

### Verification and decision

Seven distinct focused tests pass. The first command passed six and exposed a
fixture missing `game_id`; only the corrected case was rerun and passed. The
original fixture and failed log are preserved, production source was unchanged,
and the actual metadata check passed. The full suite was not repeated.

Independent audit passed **181,673 checks in 4.423944 seconds** on its first
attempt. It checked all 790 rows, 1,580 frame-arm evaluations/cache sidecars,
aggregates and the decision. Numerical reconstruction covered 141 unique
frame-arm rows: every availability gain and newly nonempty hidden frame, all
prior anchors and fixed window endpoint/midpoint samples. The overlapping
selection reasons are not additive. It read 325 cache bodies (518,372,749 bytes),
recomputed 373 contributor planes and compared 26 original NFHS means after
loading six bundles containing 150 planes. Ordinary cases outside this sample
were not independently reconstructed numerically. No producer or audit retry
was needed.

No fit, inference, checkpoint load, source-media decode, selected-prediction or
score change occurred. The failed continuation, retained `09da1214e94f` baseline,
completed reviews, uncertainty and holdout boundaries remain unchanged.

**Next:** specify one fixed, label-blind temporal selector trial on the retained baseline's
saved pool. The rule must permit missing/uncertain output and be fixed before
evaluation. Use original selected outputs as the control and existing gates,
including no additional wrong outputs/alarms and retained easy controls. Judge
matches, wrong outputs, misses and hidden alarms at the unchanged threshold and
ten-pixel boundary, with synchronized review of any new trajectories. This trial
has **not been executed or authorized** here.
The aggregation question is resolved; another heatmap diagnosis or threshold
sweep is not the next step. A selector restricted to this fixed pool cannot
recover the remaining 36 unavailable frames; they need separate detection or
localization work, not necessarily new training or images.

Evidence: [compact result](../configs/ball_tracking/reviews/nba_candidate_preservation_result_v0_1.json),
[completion](../data/outputs/ball_tracking/nba/candidate_preservation_v0_1/completion.json),
[summary](../data/outputs/ball_tracking/nba/candidate_preservation_v0_1/attempts/8e13c6cb5e07440692563a09168de0cf/summary.json),
[independent audit](../data/outputs/ball_tracking/nba/candidate_preservation_v0_1/independent_audit/audit_01.json),
[initial focused tests](../data/outputs/ball_tracking/nba/candidate_preservation_v0_1/preparation/tests_01.log)
and [corrected fixture check](../data/outputs/ball_tracking/nba/candidate_preservation_v0_1/preparation/tests_02.log).
