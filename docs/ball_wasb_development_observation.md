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

Ryan's instruction "Review. Move forward" authorized continuation. Whether it
also confirmed his acceptance of all six previous 0.3 clips was asked explicitly;
pending that answer, their human review remains pending. The three longer videos
also require their own human visual review. No operating point is promoted.

## Reproduction and evidence

Configuration:
[`wasb_expanded_development_observation_v0_1.json`](../configs/ball_tracking/wasb_experiments/wasb_expanded_development_observation_v0_1.json).
The source, labels, checkpoint, prior results and completed reviews are preserved.

```powershell
.venv\Scripts\python.exe -B -m src.ball_tracking.wasb_development_observation --config configs/ball_tracking/wasb_experiments/wasb_expanded_development_observation_v0_1.json
```

The command reuses completed raw triplets and preserves attempt records; it must
not be run again merely to resume a conversation. Generated artifacts stay under
ignored `data/outputs/ball_tracking/wasb/wasb_expanded_development_observation_v0_1/`.
