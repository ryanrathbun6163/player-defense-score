# Longer WASB development observation

The expanded model gives a useful improvement on the six labeled development
clips: at the inspected 0.3 candidate, 130 of 145 eligible positions match, one
is outside the ten-pixel radius and 14 are missing. The next question is how
those observations behave over longer stretches of play. This pass uses that
same frozen checkpoint and threshold; it adds no training or motion rule.

## What the remaining-gap review establishes

The saved threshold grid does not support simply lowering the threshold again.
At 0.2, two missing positions become correct, but three become wrong. Across
the already-completed grid, eight of the 14 missing positions are selected
correctly somewhere. The other six have a matching raw component somewhere
but never select it correctly. That is label-assisted diagnosis, not a method
that can choose the right component without knowing the answer. No matching
component for P003/164 falls within ten pixels at any declared setting.

Thirteen missing frames occur in runs touching the edges of the short review
windows. Only five have fewer than three aligned heatmap contributions, and
the longer segments below can add context to only three of those: P001/223,
P001/224 and P002/49. The P003 segment still starts at frame 300. Longer playback
can expose the surrounding behavior; it is not a promise that the gaps will
disappear. One missing frame, P001/208, has observations on both sides inside
its existing window. No interpolation has been applied.

Source-image inspection of the released windows shows visible orange ball
regions in all 14 missing frames, with partial occlusion, blur and nearby
distractors. It supports an appearance/localization difficulty but does not
override reviewed labels or establish a single cause. The saved numerical and
appearance records are under the expanded trial's
`diagnostics/remaining_gaps_v0_1/` directory.

## Scope and interpretation

| Possession | Visible source frames | Withheld frames |
|---|---|---|
| 001 | 0–274 and 350–498 | 275–349 |
| 002 | 0–174 and 250–498 | 175–249 |
| 003 | 0–224 and 300–499 | 225–299 |

The protected bands retain each sealed holdout and a 25-frame buffer on both
sides. Each visible segment starts its own temporal context. The 1,273 visible
frames need 1,261 three-frame inputs: 138 existing raw triplets are reused under
their original model/input identities, leaving 1,123 new triplets. The three
source-rate videos preserve all 1,498 timeline positions, replacing the 225
protected positions with black slates. Player identities are display context
only and do not influence ball selection.

`observed` means the model emitted a point, not that the point is correct.
`missing` means no component cleared the threshold, not proof that the ball was
hidden. `withheld` means no source image was supplied to the observation or
rendering pipeline. The videos use no connecting trail or invented position.
They include training frames and unlabeled frames, so output counts are
availability counts, not accuracy or independent generalization estimates.
These masked timelines do not complete the full-possession phase gate.

Existing six-window metrics remain frozen. Enlarging context can change at most
20 boundary-frame means; the other 130 should remain identical. Results from
this pass must not silently replace the original comparison.

Ryan subsequently confirmed: "Ok what’s the next move. I reviewed the possessions".
The [human review record](../configs/ball_tracking/reviews/wasb_expanded_development_observation_visual_review_v0_1.json)
binds all three longer videos. Review completion supplies no new frame-specific
judgments and does not promote an operating point or accept the phase gate.
Original render receipts retain their creation-time pending status. The earlier
six short candidate clips were not separately named; their historical status
is not rewritten or requested again as a blocker to planning the next step.

## Completed run and review videos

The pass completed once under implementation commit
`23fc90876458068ca422708bef92a35357bfa201`, without a retry. It took 212.761 seconds
including cache work and rendering; new model calls accounted for 17.832 seconds.
Peak allocated GPU memory was 263 MiB (400 MiB reserved). Exactly 1,123 new calls
ran, and all 138 prior triplets were reused. No additional fit or threshold
screen ran. Nine focused checks passed in 1.808 seconds; no full suite was run.

| Possession | Model points | Missing | Withheld | Review |
|---|---:|---:|---:|---|
| 001 | 324 | 100 | 75 | [20-second video](../data/outputs/ball_tracking/wasb/wasb_expanded_development_observation_v0_1/possession_001/render_attempts/e263e1d9cb5649638b8ec1754f7a2feb/review.mp4) |
| 002 | 308 | 116 | 75 | [20-second video](../data/outputs/ball_tracking/wasb/wasb_expanded_development_observation_v0_1/possession_002/render_attempts/8c1301e21ea149a1afdde0d1b0de9228/review.mp4) |
| 003 | 347 | 78 | 75 | [20-second video](../data/outputs/ball_tracking/wasb/wasb_expanded_development_observation_v0_1/possession_003/render_attempts/89da7bdc01974c81a2b2801d0d7ae75f/review.mp4) |

All 1,498 encoded frames decode, including each final frame. All 225 withheld
source areas are black. AI inspection of the three decoded endpoints confirmed
readable state/threshold labels, synchronized player context and magenta model
points; it does not supply human visual acceptance. Watch for false points,
disappearance/reacquisition around occlusion and plausible ball motion. These
videos provide longer context for the remaining development decision.

Start with these review locations; playback time is source frame divided by 25:

| Possession | Missing interval | Largest adjacent-point jump |
|---|---|---|
| 001 | Frames 26–40, about 1.04–1.60s (15 missing frames) | 440→441, about 17.60s: 796.81 pixels |
| 002 | Frames 421–437, about 16.84–17.48s (17 missing frames) | 2→3, about 0.08s: 58.16 pixels |
| 003 | Frames 24–39 and 42–57, about 0.96–1.56s and 1.68–2.28s (16 each) | 63→64, about 2.52s: 517.93 pixels |

These are ranked inspection cues, not confirmed identity errors. P001 also has
a jump out and back at 246→247→248 (465.94 then 458.38 pixels). No motion filter
has removed or corrected these outputs. Longer gaps must not be filled merely
to raise coverage.

AI spot-review of both jump endpoints finds:

- P003/63→64: the marker leaves the visible ball with white jersey 24 at the
  lower left and moves to white jersey 21's side/arm. The ball remains with 24.
- P001/440→441: the marker moves from a dark-uniform player's upper arm/torso
  near the center to the visible ball held by white jersey 24 at the right.
  This appears to be recovery from a false selection.
- P002/2→3: the marker stays on the visible dribbling ball in both images;
  its comparatively large displacement is not itself a visible failure.

These are concrete visual review cues, not new scored labels. A rule that simply
rejects the later endpoint of every large jump would reject P001's apparent
recovery. Motion-based selection needs to handle both distractors and
reacquisition after gaps. Missing samples P002/421 and /429 and P003/24, /31 and
/39 visibly contain a ball; P001/26, /33 and /40 are less certain because of body
and arm overlap. This bounded spot-review does not classify every missing frame.
Exactly five frames per possession were extracted from the new rendered videos,
with no withheld pixels. The frames, manifests and AI notes are under the new
trial's `diagnostics/visual/` directory. Ryan's later review is recorded above.

The independent saved-output audit passed: all 130 unchanged-context means are
identical, while all 20 changed-context boundary means differ. Of the original
14 missing frames, 13 remain missing; P002/49 now emits an unscored point.
P001/223–224 remain missing despite gaining context. The audit used saved
outputs only, without new inference, reference-label scoring or media decoding.

## Reproduction and evidence

### Recommended next development step

Test one motion-assisted selector on the existing 0.3 components, with the same
checkpoint, threshold and visible segments. This tests whether the stronger
adapted observations can support useful temporal selection; earlier RF motion
experiments did not establish that benefit. Do not repeat their broad grids.

The selector may choose an existing candidate or leave a frame missing. It must
allow recovery after a gap rather than locking onto a stale false point. No
coordinate interpolation, lower-threshold candidate expansion, player-proximity
rule or additional training belongs in this first comparison. Freeze one
configuration before scoring and compare it against native-mass selection on
the same longer-context outputs at the 150 existing development label frames.
Preserve the original short-window results as separate evidence.

The immediate opportunity and limit are concrete. P001/247 has an alternate
candidate continuing the 246→248 path, while P003/64 has only the false candidate
at 0.3. P001/440 also has only a false candidate, followed at 441 by both the
false candidate and the apparent recovered ball. Motion needs to distinguish
those situations; simply choosing the nearest point can preserve a false track.
No selector confined to these candidates can fill the 294 empty frames.

Positive evidence would be fewer false selections without losing correct
localizations, adding hidden alarms or suppressing legitimate recovery. Inspect
all changed outputs alongside the baseline and explicitly report gains and
losses. If that fails, record the negative result and target visual evidence
rather than launching another broad motion search. Gap recovery is a later,
separate question requiring weaker visual candidates or improved recognition.
This is the recommended scope; no new selector has been implemented or run,
and Ryan has not yet approved this specific scientific change.

Configuration:
[`wasb_expanded_development_observation_v0_1.json`](../configs/ball_tracking/wasb_experiments/wasb_expanded_development_observation_v0_1.json).
The source, labels, checkpoint, prior results and completed reviews are preserved.

```powershell
.venv\Scripts\python.exe -B -m src.ball_tracking.wasb_development_observation --config configs/ball_tracking/wasb_experiments/wasb_expanded_development_observation_v0_1.json
```

The command reuses completed raw triplets and preserves attempt records; it must
not be run again merely to resume a conversation. Generated artifacts stay under
ignored `data/outputs/ball_tracking/wasb/wasb_expanded_development_observation_v0_1/`.

The [completed summary](../data/outputs/ball_tracking/wasb/wasb_expanded_development_observation_v0_1/summary.json)
has SHA-256 `722a60dab8d34aa7acd3cbc5d1fc1635042050fb8a5d0f65fa96a7e380ae1b9f`.
The successful invocation and its earlier start record are preserved in
`invocations/20261009T020518Z_f622c5aeba31439e98e69db71f386147*.json`.
The [independent audit](../data/outputs/ball_tracking/wasb/wasb_expanded_development_observation_v0_1/diagnostics/post_runtime_audit_v0_1.json)
has SHA-256 `0d86a7a72d1767c5dfd7e92965edd5f6e6643c00b06ae6358967ca8f60e23cb2`.
