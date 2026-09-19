# First ball temporal-association experiment

Status: proposed design, prepared after Ryan approved the six development
comparison clips. No temporal algorithm has been implemented or run. This
document is not an executable manifest, an operating-point selection, or a
quality gate.

## Question and starting evidence

Can linking nearby detections across successive frames remove isolated false
guesses while retaining real ball observations? A short linked sequence is a
**tracklet**. This first experiment measures tracklets before attempting one
continuous ball trajectory, filling gaps, or inferring who has the ball.

Ryan described the videos as a solid starting point, with small blips of
possible detections. His exact statement and all six clip bindings are in
[`rfdetr_medium_development_candidate_comparison_review_record_v0_1.json`](../configs/ball_tracking/reviews/rfdetr_medium_development_candidate_comparison_review_record_v0_1.json),
SHA-256 `a60dea646736135620fb97eba9f1985f7b06f0c7bfc7abee38537580c05f4dba`.
This is visual approval of the current evidence, not a claim of complete
trajectories or acceptable quantitative performance.

The existing 10-pixel scoring cells show a material limitation. Even at the
stored 0.01 confidence export floor, P001 has a qualifying candidate in only
10/25 representative frames and 18/25 challenge frames. At confidence 0.20,
those counts are 4/25 and 7/25. A selector that retains original candidate
centers cannot exceed the input candidate availability at the same threshold
and tolerance. This is a label-assisted ceiling, not a predicted tracker result.
It suggests that detector/localization work may still be necessary even if
temporal filtering removes many false guesses.

The read-only diagnostic is
`data/outputs/ball_tracking/development_execution/84bcc8da143e/candidate_availability_diagnostic.json`,
SHA-256 `2bf4efc3bf94472c8f5411fd28194c72a308584ece6faab071841cb856cf55b3`.
It extracts existing report cells without new inference or rescoring.

## Fixed input scope

Reuse only the six detection files generated at
`84bcc8da143e54ff17a28b39db0e70c4b8b299c8`, bound by the new review receipt.
Preserve their raw candidates, model provenance, confidence values, centers,
source hashes, frame indices, and ordering. Do not rerun the detector.

| Possession | Representative | Challenge |
| --- | --- | --- |
| P001 | 50–74 | 200–224 |
| P002 | 250–274 | 25–49 |
| P003 | 300–324 | 150–174 |

Each window starts with empty state. Do not extend a window, borrow a warm-up
frame, join the two windows of a possession, or carry state between possessions.
The three holdouts remain sealed, and all nine original v0.1 prediction paths
remain absent. The approved versioned development outputs remain immutable.

These windows contain one second of video each at 25 fps. They can test local
association and failure behavior, not full-possession trajectories or general
performance across basketball events, games, or camera cuts.

## Three comparison arms

1. **Raw candidates:** preserve the existing image-only baseline at every
   declared confidence threshold.
2. **Highest-confidence control:** retain the highest-confidence candidate per
   frame, or no candidate if none qualifies. Break equal-score ties by original
   candidate index. This reveals how much improvement merely discarding extra
   guesses can explain, without using time.
3. **Causal tracklets:** associate candidates with earlier observations using
   the deterministic procedure below. Retain multiple hypotheses when present;
   do not silently claim that a surviving tracklet is the basketball.

All arms use the existing nine confidence thresholds:
`0.01, 0.03, 0.05, 0.10, 0.15, 0.20, 0.25, 0.35, 0.50`.
These are comparison settings. None is selected for deployment.

### Proposed deterministic tracklet procedure

- Filter candidates by the arm's inclusive confidence threshold. Use only
  candidate records and source dimensions/frame timing; annotation files,
  reviewed centers, visibility labels, player tracks, and court geometry are
  unavailable to association.
- For a tracklet last observed at frame `s` and candidate at frame `t`, define
  `delta = t - s`. An edge is eligible when `delta - 1 <= max_missing_frames`
  and center distance is at most `step_limit * source_diagonal * delta`.
  This is a simple image-displacement constraint, not a physical ball-speed
  model or camera-motion compensation.
- Sort eligible edges by displacement per elapsed frame, then tracklet ID,
  then original candidate index. Greedily assign edges one-to-one. Every
  unmatched candidate starts a new provisional tracklet; tracklet IDs follow
  deterministic frame/candidate order.
- Confirm a provisional tracklet only after a match on the next consecutive
  frame. Emit its original candidate starting at that confirmation frame.
  Do not backfill its first frame. Unconfirmed single-frame guesses expire.
- Confirmed tracklets can reconnect within the declared missing-frame limit.
  Emit no coordinate during an unmatched frame. Expire state before matching
  when the allowed gap is exceeded; a later candidate must start anew.
- Preserve the original candidate center and confidence for every emitted
  observation. Confidence remains detector confidence, not a calibrated
  probability for a tracklet. Do not smooth, interpolate, extrapolate output
  coordinates, or move candidate centers toward the labels.
- Record every candidate's disposition (provisional, emitted, below threshold),
  every association edge and distance, tracklet ID, confirmation, expiry, and
  each frame's empty-output state. Missing output means no accepted observation;
  it does not assert that the true ball was invisible.

Compare `step_limit` values `{0.01, 0.03}` of the source diagonal per frame and
`max_missing_frames` values `{0, 2}`. At 1920 by 1080 these are approximately
22 and 66 pixels per frame; two omitted frames permit a three-frame interval
between observations. These four variants at nine thresholds give 36
tracklet configurations. The numbers are proposed broad engineering probes,
not fitted speed estimates or approved acceptance thresholds. Keep all results,
including unfavorable ones; any later grid changes receive a new version.

## Evaluation and review

Use the same reviewed annotations and all five localization radii
`5, 10, 15, 20, 30` pixels, including existing annotation-uncertainty treatment.
Keep the representative and challenge pools separate, with per-possession
results. Evaluate a derived output contract carrying association provenance;
never relabel processed results as raw image-only detector outputs.

Report precision, recall, false-positive counts, duplicate counts, hidden-frame
false alarms, localization error, and emitted-frame coverage. Compare with
both controls at identical confidence/radius cells. An all-missing result must
not look successful merely because it emits no false positives. Add descriptive
longest consecutive missed-eligible-frame run, correct-match run lengths, and
tracklet fragmentation. Interpret these over the short windows only.

For P003 frames 165–169, truth geometry stays null. Every emitted candidate on
these frames remains a false alarm under the existing protocol. Association
must not read the hidden-frame labels to suppress candidates. Report the
behavior at frames 164, 170, and final frame 174 explicitly.

For visual review, predeclare the same display cells as the reviewed detector
comparison: confidence 0.20 and 0.35, radius 10 pixels. For each window and
display cell, show raw candidates, the highest-confidence control, and all four
tracklet variants in synchronized panels. Provide native-resolution PNGs,
unmarked source closeups, legends, gap states, tracklet IDs, and final-frame
details. Review all variants; do not choose a favorable example after seeing
the scores. Ryan makes the final visual judgment on the new evidence.

## Implementation and validation sequence

1. Add separate association/output contracts, configuration, runner, scoring,
   and rendering support; preserve the frozen raw-detector contract. Bind exact
   input detection bytes and this design in a new manifest outside the existing
   experiment registry until support validates it. The review receipt alone
   is not an execution permit for this experiment.
2. Test deterministic ties, intersecting hypotheses, startup delay, isolated
   guesses, short/expired gaps, window resets, empty frames, hidden-frame false
   alarms, malformed provenance, and rejection of unauthorized window inputs.
   Include a fixture where the most confident candidate is wrong, ensuring
   evaluation cannot influence association. Use synthetic candidates first.
3. Run focused tests, the full suite with the repository `.venv` and bytecode
   disabled, and `git diff --check`. Validate input hashes and ignored output
   locations before any real association run. Preserve input detection commit
   separately from new association/scoring commits; never rewrite old provenance.
4. Use separately authorized Git steps for a reproducible implementation
   checkpoint. Real execution requires a new experiment authorization binding
   the concrete manifest; the old six-window detector approval covers its
   completed image-only experiment only. Then run every declared variant into
   new ignored output paths and prepare synchronized quantitative/visual review.

No upstream reviewed decision is changed, so no existing player-pipeline
`--rerun-from` stage is involved. This experiment remains outside the 21-stage
player pipeline. It defines no operating point, detector winner, pass/fail
quality gate, ball-handler decision, or holdout release.
