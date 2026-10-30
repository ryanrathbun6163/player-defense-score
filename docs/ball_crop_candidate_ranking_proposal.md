# Saved crop candidates: recent-history ranking experiment

Status: proposed experiment; no new association, scoring, or rendering has run.
Machine-readable scope:
`configs/ball_tracking/proposals/rfdetr_medium_crop_candidate_ranking_v0_1.json`.

## Question

Can a short recent history choose a useful ball observation when the highest
detector confidence points elsewhere, while keeping gaps and wrong guesses
visible? The reviewed crop evidence offers more qualifying candidates, but
top-one choice loses 11 representative and four challenge matches at the
0.20/10-pixel display cell. See `ball_detector_tiled_comparison_results.md`.

This is a bounded experiment in image-space candidate selection. It does not
establish a ball tracker, an accepted operating point, or a quality gate.
Persistent clutter can also form a convincing path, and ball motion, camera
movement, crop boundaries, or occlusion can break a correct one.

## Fixed input scope

Reuse the exact six saved crop candidate files from execution commit
`1a9479f83a1766d8979fad07c604bc686d3c52c6`. Preserve every raw candidate,
confidence, original global/crop-local index, center, box, view, and model
provenance. The completed crop-review receipt and both scoring pools are bound
in the proposal. No new detector calls, model downloads, training, frame
extension, or source-window selection is involved.

| Possession | Representative frames | Challenge frames |
| --- | --- | --- |
| P001 | 50-74 | 200-224 |
| P002 | 250-274 | 25-49 |
| P003 | 300-324 | 150-174 |

Every window resets state. There is no warm-up, look-ahead, transfer between
windows, or player/court input. Candidate selection reads saved candidates,
source dimensions, and frame indices only. Reviewed annotation content and
visibility labels are available solely to later scoring/review.

## Five comparison arms

At each existing confidence threshold, compare:

1. **Crop raw:** every threshold-qualified candidate.
2. **Crop top one:** the highest-confidence candidate, or no observation.
3. **Crop top twenty:** up to 20 threshold-qualified candidates, in original
   global order. This isolates any loss caused by the computational cap.
4. **Recent history, tight links:** rank paths over the top-twenty candidates
   with a displacement limit of 0.01 source diagonals per elapsed frame.
5. **Recent history, wide links:** the same algorithm with limit 0.03.

All five use the inclusive confidence grid
`0.01, 0.03, 0.05, 0.10, 0.15, 0.20, 0.25, 0.35, 0.50`.
No threshold is selected. Controls preserve the existing descending-confidence
global ordering, including its deterministic ties. The 20-candidate cap and
scoring constants below are predeclared engineering probes, not fitted from
label geometry or claimed basketball dynamics. Any revision needs a new
specification version; do not adjust them after seeing experiment results.

## Exact recent-history rule

For source frame `t`, rebuild hypotheses from only frames
`max(window_start, t-4)..t`. Five frames span four frame intervals: 0.16 seconds
at 25 fps. Older candidates expire; no accepted output is rewritten.

Each threshold-qualified, top-twenty candidate is a node with its original
center and detector confidence. A path can start at any node. An edge from
node `a` at frame `s` to node `b` at frame `u` is eligible when:

- `1 <= u-s <= 3`, allowing at most two intervening missing frames;
- center distance is at most `step_limit * source_diagonal * (u-s)`.

The motion limit is about 22 or 66 source pixels per frame. It is an image
displacement constraint; it includes camera motion and is not a physical speed.
Define `normalized_step = distance / (step_limit * source_diagonal * (u-s))`.
An eligible path's score at `t` is:

```text
sum(original detector confidences on its nodes)
  - 0.25 * (internal skipped frames + trailing skipped frames)
  - 0.25 * sum(normalized_step ** 2 on its edges)
```

An endpoint at `e` can compete only when `0 <= t-e <= 2`; its trailing
skipped-frame count is `t-e`. Include one empty hypothesis with score 0.
Leading frames before a path starts incur no penalty. This allows a fresh
hypothesis without inventing warm-up observations. A singleton's score is its
original confidence. Recompute from raw recent candidates each frame rather
than forcing future choices to follow a previous emitted result.

Use exact dynamic programming over the ordered acyclic candidate graph.
For each endpoint, retain its maximum-score path. Equal path scores use the
lexicographically smallest sequence of `(frame_index, global_candidate_index)`.
Then select the maximum endpoint score, breaking endpoint ties by latest
endpoint frame, higher endpoint confidence, lower global candidate index,
and lexicographic path. For a score-0 tie with the empty hypothesis, select
empty. Do not round scores before comparing. Persist the winning path and
all endpoint scores, including competing alternatives and score margins.

If the winning endpoint is at `t`, emit that original candidate as a tentative
observation. If it ends earlier, or empty wins, emit null: a hypothesis surviving
a gap is not an observed or extrapolated ball location. Emit at most one
candidate per frame. Do not interpolate, smooth, average boxes, move centers,
deduplicate, backfill, or alter detector confidence. The path score is a
heuristic ranking value, not a probability; its alternatives remain visible.
No ambiguity-margin acceptance threshold is introduced by this experiment.

This rule may prefer a persistent wrong object, withhold a newly appearing
ball while an earlier hypothesis remains competitive, or reject a fast ball.
These are explicit evaluation targets, not cases to hide or hand-correct.

## Derived audit contract

Create a separate schema and versioned output root. Each output binds the
immutable crop-input bytes/content digest, original detector execution commit,
new selector code commit/specification, source/window identity, and threshold.
Do not serialize selected outputs as frozen raw detections.

Each frame records all original candidate dispositions (below threshold,
outside top twenty, eligible, emitted, or not emitted), window/horizon bounds,
eligible edges and component scores, best path per endpoint, deterministic
ties, winner, original candidate references, and explicit no-observation state.
Retain detector confidence separately from path score. Candidate alternatives
are hypotheses rather than established ball identities or persistent track IDs.
Resume only outputs with exactly matching input/code/specification provenance;
changed or tampered existing outputs must be refused.

## Evaluation

Use the unchanged six reviewed annotation sets and radii `5, 10, 15, 20, 30`
source pixels. Matching remains raw center distance; annotation uncertainty is
diagnostic only. Representative and challenge pools and per-possession results
remain separate.

Five arms by nine thresholds produce 45 variants and 270 per-window derived
outputs. Five scoring radii yield 1,350 per-window reports and 225 aggregate
cells per pool. All 540 raw/top-one control reports must reproduce saved crop
metrics and per-frame outcomes; adapter input/below-threshold bookkeeping is
reported separately when it differs by contract.

Compare each history variant against raw, top one, and top twenty at identical
settings. Report TP/FP/FN, duplicate and hidden-frame false alarms, localization
error, emitted and missing frame counts, longest missed-eligible run, and
newly recovered/lost matches. Decompose losses caused by the top-twenty cap
from additional ranking losses. Audit history decisions against retained
original candidate references; no truth information may enter path ranking.

P003 hidden frames 165-169 keep null truth geometry. Every emitted candidate
there remains a false alarm. Report frames 164, 170, and final 174 explicitly.
Preserve the reviewed P002 challenge 48-49 and other crop regressions as
comparison context; a favorable visual assessment does not change their score.

## Synchronized review

Predeclare 12 slow clips: all six windows at confidence 0.20 and 0.35, radius
10. Show crop raw, crop top one, crop top twenty, both history variants, and
saved whole-frame top one as six synchronized panels. The whole-frame panel
reuses the exact saved control/results and is context rather than a new arm.
Use 25 frames per clip at 5 fps; verify decoding through the actual last frame.
Provide native overlays, unmarked source closeups, alternative hypotheses,
gap reasons, and final-frame evidence. Ryan reviews every clip after execution.

## Implementation and authorization boundary

The current crop permit explicitly excludes temporal filtering. The completed
visual-review receipt and "lets move forward chat" authorize this closeout and
concrete next design; they do not bind an experiment that was not yet specified.
Approve this exact saved-candidate experiment before implementation/execution.
Record approval in a separate receipt without rewriting this proposal's status.

Implement separately from the frozen detector, original tracklet modules, and
21-stage player pipeline. Synthetic validation must cover exact DP choices
against exhaustive small graphs, a wrong top-confidence candidate, stable
clutter, fast motion, crop duplicates, ties, top-twenty loss, empty/failed frames,
two-frame gaps and expiry, restart/horizon behavior, no future access, missing
output without extrapolation, window reset, malformed/tampered provenance,
unauthorized windows, and all-grid control parity. Run focused tests followed
by the full suite with `.venv` and bytecode disabled, plus `git diff --check`.

Real execution requires a validated executable manifest at a clean committed
implementation checkpoint. Staging, commit, push, PR creation, and merge each
need separate explicit authorization. Proposed ignored output root:
`data/outputs/ball_tracking/crop_candidate_ranking/rfdetr_medium_crop_candidate_ranking_v0_1/`.

Keep all nine original embargo paths absent and P001 300-324, P002 200-224,
and P003 250-274 sealed. No upstream reviewed player decision changes, so no
player-pipeline `--rerun-from` action is needed. No detector/selector winner,
operating point, quality gate, basketball event, or holdout release is selected.
