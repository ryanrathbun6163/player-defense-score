# NBA native-cadence pilot diagnostic result

**Current status: accepted.** On 2026-10-19 (America/Phoenix), Ryan reported:
“I reviewed both videos and the predictions look good. Move forward chat.”
The separate [model-output acceptance record](../configs/ball_tracking/reviews/nba_wasb_native_pilot_visual_review_v0_1.json)
records this later event for both presented complete clips and their actual
final frames. No corrections were requested. Original result records, media
and the creation-time pending review page remain unchanged; the
[accepted-status page](../data/outputs/ball_tracking/nba/wasb_native_pilot_diagnostic_v0_1/accepted.html)
links the same videos. Reference-label acceptance remains a separate event.

## Completed diagnostic

On 2026-10-19 (America/Phoenix), Ryan approved the exact
[prepared recipe](nba_wasb_native_pilot_diagnostic.md): “yes I do. move forward
chat”. The [approval record](../configs/ball_tracking/reviews/nba_wasb_native_pilot_diagnostic_approval_v0_1.json)
binds that decision to the configuration. One run completed all 116 distinct
three-frame inputs in 49.766 seconds, with zero failed or unresolved model
calls. No training, threshold search or original-game decode occurred.

The frozen expanded WASB checkpoint and strict heatmap threshold `>0.3`
produced a matching observation on every accepted reference frame in both
pilots. Matches use raw source-pixel distance **less than or equal to 10 pixels**;
annotation uncertainty does not change that decision.

| Game and original frames | Matched | Wrong | Missing | Mean center distance | Maximum center distance |
| --- | ---: | ---: | ---: | ---: | ---: |
| SAC–MEM, 660–719 | 60/60 | 0 | 0 | 2.779 px | 4.400 px |
| SAS–DET, 10788–10847 | 60/60 | 0 | 0 | 2.894 px | 5.179 px |

These are distances from human-accepted AI reference centers, not independently
measured physical truth. The references preserve their AI authorship, acceptance
event and placement uncertainty. All 120 frames are visible-ball cases: 71 fully
visible and 49 partly visible. There are no hidden negatives, so false alarms
when the ball is hidden remain unmeasured.

Each input contains three consecutive original frames at measured 16 or 17 ms
spacing. Predictions for each frame average its aligned contributions from the
available complete triplets, including the endpoints. There is no padding,
interpolation, motion selector or external context. The earlier NFHS inputs
used 40 ms spacing; this run did not compare cadences and cannot show that the
cadence change caused its result.

## Accepted model-output review

Both videos last 11 seconds: all 60 native frames played at 6 fps, followed by
a one-second hold on the actual final frame. Cyan marks the accepted AI
reference; pink marks the model observation. Ryan's reported review and
favorable judgment cover both presented clips. No browser playback telemetry
is claimed.

- [SAC–MEM model-output review, through frame 719](../data/outputs/ball_tracking/nba/wasb_native_pilot_diagnostic_v0_1/sac_mem_q1_c01/review_attempts/b9b4953913dc4706acf3009cea7ec49e/review.mp4)
- [SAS–DET model-output review, through frame 10847](../data/outputs/ball_tracking/nba/wasb_native_pilot_diagnostic_v0_1/sas_det_q1_c02/review_attempts/065345efdf3749c8bd8bbcc09d2d57a9/review.mp4)
- [Current accepted-status page](../data/outputs/ball_tracking/nba/wasb_native_pilot_diagnostic_v0_1/accepted.html)
- [Preserved creation-time pending review page](../data/outputs/ball_tracking/nba/wasb_native_pilot_diagnostic_v0_1/index.html)

Both model-output reviews are complete. His completed acceptance of the
reference labels also remains intact and does not need repeating.
Before human acceptance, the assistant inspected all 120 new overlays through
both final frames and found no obvious distractor switch or dropout; points remain on the visible
ball. That AI check remains distinct from the later human acceptance. The
original review cues included Detroit's hand overlap and blur at frames
10788–10792, 10831–10845 and 10847.

## Saved-output and media verification

An independent [audit of the actual saved artifacts](../data/outputs/ball_tracking/nba/wasb_native_pilot_diagnostic_v0_1/diagnostics/independent_audit_01/audit.json)
passed on its first attempt in 18.094 seconds: 7,015 checks, 494 file bindings and
zero issues. It reconstructed all 120 aligned mean heatmaps from the 116 cached
triplets, all 127 final components and every selected point, and independently
confirmed all 120 scoring outcomes. It made no additional model calls and did
not invoke the project's scoring functions.

Both review videos were fully decoded: 66 frames each at 6 fps. All 132 encoded
frames matched their overlays within the declared lossy tolerance, including
all six extra copies of each final frame. The maximum whole-image RGB mean
absolute difference was 2.2586 for SAC and 2.3794 for DET, below the limit of 4.
These checks verify transport and rendering; they do not measure ball accuracy.
No source or test code changed, and no earlier suite or experiment was repeated.

The inherited adapter provenance describes its default `>0.5` components; this
runner consumes the heatmaps and recomputes the final components at `>0.3`.
The independent reconstruction confirmed the latter for every emitted point.
The [provenance explanation](../data/outputs/ball_tracking/nba/wasb_native_pilot_diagnostic_v0_1/diagnostics/independent_audit_01/threshold_provenance_note.json)
preserves the original metadata and explains the distinct processing layers.

## Evidence and limits

The [compact result record](../configs/ball_tracking/reviews/nba_wasb_native_pilot_diagnostic_result_v0_1.json)
binds the configuration, approval and generated evidence. The ignored
[completion record](../data/outputs/ball_tracking/nba/wasb_native_pilot_diagnostic_v0_1/completion.json)
links both per-game observations, diagnostics and review receipts. Cached model
outputs, all attempt records and generated media remain local and uncommitted.

This establishes a favorable result on two selected scenes, about one source
second per game. It does not establish full trajectories, occlusion recovery,
independent NBA accuracy or ball-phase completion. SAC remains eligible for
future training; DET remains target development and excluded from fitting.
No new fit or broader experiment is approved by this result. Existing holdouts,
completed reviews and the negative motion-selection result remain unchanged;
the motion study's three new human reviews are still pending.

The [next concrete proposal](nba_wasb_action_observation_plan.md) extends the
same frozen recipe across the two previously selected action cores, with
complete review videos and explicit missing intervals. It is design-only and
awaits approval to implement, validate and execute that broader observation
pass. This would test behavior beyond the two easy, one-second pilot scenes;
it would not add training, new labels or an independent accuracy benchmark.
