# Proposed WASB training-data expansion

Prepared 2026-10-08 after the completed six-clip human review and
[remaining-gap diagnosis](ball_wasb_remaining_gap_diagnosis.md).
Status: proposed; no new labels or training have been produced.

## Decision

Add **75 training-only frames**, label and visually review them under the existing
ball annotation protocol, then run one controlled comparison from the original
pretrained checkpoint using the combined 150 training frames. This requires
Ryan's approval of the added data and labeling work. The current checkpoint and
its completed reviews remain intact.

The first 75 frames improved the model substantially. Remaining P001 failures
have weak nearby candidate responses but usually stronger responses elsewhere.
Simply lowering the threshold or taking the strongest pixel adds wrong outputs.
More relevant visual examples are the proposed correction; improvement is still
a hypothesis, not an established result.

## Exact additional windows

Each link opens a five-second, slowed source-only preview of 25 source frames.
There are no model predictions or generated labels in these previews.

| Additional training window | Source time | Reason for inclusion | Preview |
| --- | --- | --- | --- |
| P001 frames 100–124 | 4.00–4.96 s | Left-side handling with ball/hand/body overlap and bleacher context; differs from the old right-side pilot | [Source clip](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/diagnostics/next_training_source_preview_v0_1/possession_001_000100_000124_source_preview.mp4) |
| P001 frames 250–274 | 10.00–10.96 s | A left-side pass/receive/handling sequence with a different player arrangement and ball background | [Source clip](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/diagnostics/next_training_source_preview_v0_1/possession_001_000250_000274_source_preview.mp4) |
| P002 frames 343–367 | 13.72–14.68 s | Extends the existing 318–342 training episode past its ending occlusion; visible ball recovery appears in the added footage | [Source clip](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/wasb/wasb_basketball_adaptation_v0_1/diagnostics/next_training_source_preview_v0_1/possession_002_000343_000367_source_preview.mp4) |

The ball's exact visibility and center remain annotation decisions for each frame;
the source-preview descriptions are qualitative observations, not accepted labels.
The seven source-only candidate contact sheets inspected during selection remain
preserved, including the four candidate windows not selected. AI inspection used
four sampled frames per candidate window; it was not a completed label review. Selection was
informed by development failures and source appearance; it is not blind sampling.

None of these new frames overlap the six development windows or three holdouts.
The minimum separation from those evaluation/holdout windows is 25 intervening
frames. This buffer prevents direct or neighboring-triplet overlap, but does not
make footage from the same possession/game statistically independent. Existing
development windows remain development diagnostics; holdouts retain their role.

The P002 addition intentionally adjoins its existing training pilot. After label
review, compose a training-only 318–367 view while preserving both original and
new annotation files. This allows triplets through the old boundary at 342.
Do not extend temporal context beyond the combined training range.

## Label and comparison rules

- Add exactly 75 frame annotations. Preserve ambiguity and reviewed hidden frames;
  do not force a center or turn uncertain visibility into a negative target.
- Ryan retains visual review of the new labels. No AI-generated point is silently
  accepted as human ground truth, and no already-completed review is reopened.
- Keep all original 75 labels unchanged. Combined positive/hidden/ambiguous counts
  are determined only after the new labels are complete and reviewed.
- Start one new fit from the same original pretrained checkpoint. Keep 200 updates,
  batch two, seed 1234, Adam 0.0001, frozen BatchNorm running buffers, float32,
  target/loss definitions, masking and no augmentation unchanged. Use all 140
  complete triplets from the five combined training blocks in a deterministic
  400-triplet schedule. Do not continue the old fit or choose an intermediate
  checkpoint based on evaluation results.
- Evaluate the final checkpoint on the same six development windows using the
  existing primary 0.5 policy, ten-pixel matching and fixed eight-setting cached
  screen. Compare with both the preserved first adapted checkpoint and saved RF
  controls. No new holdout release, threshold search or operating-point promotion.
- Report P001 recovery and any regression in P002/P003, wrong-object/center errors,
  missing frames and hidden alarms. If useful, render the changed output for its
  own human review. Run focused checks for changed data-loading boundaries; the
  data addition alone does not justify another full-suite run.

Keeping optimizer exposure fixed makes this a practical comparison of the expanded
training set under the same recipe. It does not isolate each appearance/position
factor, guarantee improvement, or eliminate same-game correlation.

## What is ready

The proposed windows and bound previews are recorded in
`configs/ball_tracking/proposals/wasb_training_data_expansion_v0_1.json`.
The three preview videos each decode all 25 frames. No annotation template has
been passed off as completed data, and no new model inference or training was run
to prepare this proposal. Approval covers this data addition and one fit after
the new labels pass their human review; broader data expansion or repeated tuning
would be a separate scientific decision.
