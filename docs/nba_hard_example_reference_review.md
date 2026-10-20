# NBA difficult-scene label review

Four complete label-overlay videos are ready for Ryan's review. His “Ok move
forward” approved preparation of the exact 520-frame batch; it did not accept
the resulting labels. These remain **AI proposals pending human acceptance**.
The [scope approval](../configs/ball_tracking/reviews/nba_hard_example_reference_approval_v0_1.json)
and [preparation record](../configs/ball_tracking/reviews/nba_hard_example_reference_preparation_v0_1.json)
preserve the original [proposal](nba_hard_example_reference_plan.md) and bind
the prepared evidence, corrections and audits.

| Review video | Original source frames | Proposed centers | Unknown centers | Review duration | Actual final frame |
| --- | --- | ---: | ---: | ---: | ---: |
| [SAC distractors and recovery](../data/outputs/ball_tracking/nba/hard_example_reference_v0_1/reviews/sac_distractor_recovery/sac_mem_q1_c01/review.mp4) | 940–1059 | 90 | 30 | 21 seconds | 1059 |
| [SAC held ball](../data/outputs/ball_tracking/nba/hard_example_reference_v0_1/reviews/sac_held_ball_gaps/sac_mem_q1_c01/review.mp4) | 1240–1359 | 120 | 0 | 21 seconds | 1359 |
| [DET distractors and gap](../data/outputs/ball_tracking/nba/hard_example_reference_v0_1/reviews/det_distractor_long_gap/sas_det_q1_c02/review.mp4) | 11000–11119 | 65 | 55 | 21 seconds | 11119 |
| [DET drive and rim overlap](../data/outputs/ball_tracking/nba/hard_example_reference_v0_1/reviews/det_drive_rim_overlap/sas_det_q1_c02/review.mp4) | 11420–11579 | 112 | 48 | 27.667 seconds | 11579 |
| Total | 520 source frames | 387 | 133 | 90.667 seconds | All four inspected |

The videos are delivered directly in chat for phone viewing. They deliberately
play at six source frames per second so individual proposals are readable.
Original source frame numbers and timestamps remain in the review record; the
slowed playback is not the ball's real-time motion. Each video includes every
selected frame in order and a one-second hold on its actual final frame.

The cyan point marks the proposed complete-ball center; its uncertainty circle
shows how precisely the source supports that estimate. A visible fragment may
support the center of the complete ball even when a hand covers part of it.
An unknown center has no point. This can mean the ball is hidden, its identity
is ambiguous, or the visible fragment does not support a defensible center.
Unknown does not automatically mean invisible. The proposals include 24
partially visible frames with no defensible center.

Review each complete video through its final hold. Check whether the point
stays on the complete ball, the uncertainty is credible, and the unknown
intervals are justified. Give particular attention to these source-frame cues:

- SAC 959–999: score-graphic obstruction, handler-body occlusion, uncertain
  fragments and recovery; inspect the adjacent transition at 958 as well.
- SAC 1278–1284 and 1293–1307: hand overlap while the ball is held, where the
  visible fragment and complete-ball center differ.
- DET 11075–11101: prolonged overlap and return of visible evidence; the
  package retains additional transition cues and the final frame.
- DET 11454–11475 and 11480–11496: player overlap and ambiguous ball evidence;
  11511–11513: visible fragments without a supported center;
  11551–11556: rim/arm overlap. The full per-frame exception lists remain in
  each package's proposal and the preparation record.

Every original native source frame was visually inspected, with detailed crops
where useful. The points were proposed from those images without copying saved
prediction coordinates or interpolating unsupported gaps. AI authorship remains
explicit, including for partial-ball geometry. The windows were chosen after
model failures were observed and the assistant had prior qualitative model
exposure, so the process is not blind. These correlated difficult frames cannot
estimate representative NBA accuracy.

Twenty-six focused checks passed. Independent transport checks passed for all
520 source/render PNGs and all four MP4 timelines, including 544 encoded frames
with final holds. All four decoded final frames were visually inspected. These
checks verify evidence transport; Ryan's visual label judgment is still needed.
Initial drafts, corrected proposals and failed helper attempts are preserved.

After Ryan explicitly accepts the labels and unknown intervals, a separate
accepted AI reference will be published and the already saved frozen outputs
scored. The approved maximum is 640 frames, including 120 existing pilot labels
as separate longer-context easy controls. Unsupported centers remain unscored;
the inclusive ten-source-pixel rule and original short-pilot score stay intact.
No new scores, model calls or training have run in this preparation increment.

SAC retains future-training eligibility; DET remains excluded from fitting and
TOR remains outside scope. Protected holdouts, the NFHS finish line, earlier
pilot acceptance and the negative motion result are unchanged. The three
motion-comparison human reviews remain pending.
