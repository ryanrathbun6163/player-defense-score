# Player-context comparison: reviewed results and remaining errors

Ryan confirmed **"Yes, reviewed all 12; proceed"** in response to the question
asking whether he had watched all twelve new player-context clips through their
final frames. The separate receipt is
`configs/ball_tracking/reviews/rfdetr_medium_crop_player_context_visual_review_record_v0_1.json`
(SHA-256 `0ebaabad929558d9c07339161f0d37362d6da9477883853146345cc56a848ef6`).
It records review completion, without inventing frame-specific judgments or
asserting that every emitted candidate is correct. Earlier pending-review
snapshots remain unchanged.

The experiment ran at `119159817df5414f534f133f0954c1f78c7e51de` on
`codex/ball-detector-baseline`. Its 216 new outputs, 1,080 new reports and twelve
clips are complete. All 378 saved controls and 1,890 reports were reused.
Neither this closeout nor its diagnosis reran selection, scoring or inference.
The numerical inputs are the two saved pools and their prior independent audit;
new evidence is in
`data/outputs/ball_tracking/crop_player_context_closeout/119159817df5/`.

## What the context term accomplished

The small distance cost reduced some persistent distant distractors. Across
all 1,080 per-window comparisons with the corresponding saved motion control,
there are no newly lost matches, new false-positive frames or increased center
errors on shared matches. This checks local outcomes as well as pooled totals.
The 360 aggregate comparisons therefore do not hide those types of local
regression within these windows.

All comparisons reuse the same 150 development frames. They are not independent
trials, proof of generalization, or evidence for adopting an operating point.
P002 representative frame 262 recovers in all four settings at both display
confidences. Some settings still lose observations already found by top one;
the no-regression finding applies to each paired motion control, not to every
other comparator.

## What remains missing

At the previously declared 10-pixel radius, misses separate into four causes:
**U**: no suitable exported candidate even at .01; **F**: confidence filtering;
**C**: the twenty-candidate cap; **S**: subsequent path selection. U describes
localization availability, not a certified absence of a depicted basketball.

| Pool | Confidence | Shared U / F / C | Selection loss TT / TW / WT / WW |
| --- | ---: | --- | --- |
| Representative (75 eligible) | .20 | 5 / 8 / 0 | 22 / 18 / 5 / 1 |
| Representative (75 eligible) | .35 | 5 / 11 / 0 | 20 / 18 / 5 / 2 |
| Challenge (70 eligible) | .20 | 0 / 7 / 0 | 6 / 10 / 1 / 0 |
| Challenge (70 eligible) | .35 | 0 / 12 / 0 | 6 / 9 / 1 / 0 |

For example, TT at representative .20 has 35 misses: 5 + 8 + 0 + 22.
These settings remain display comparisons, not recommended thresholds.
At other grid settings, cap losses do occur; the full diagnosis retains them.
At .01 and radius 10, the saved candidate pool already covers 140 of the 145
eligible frames. A challenger therefore needs evaluation of false guesses,
confidence separation and localization, not just increased candidate recall.

- The five unavailable radius-10 frames are P001 59/67/68/69 and P002 257.
  A new ranking rule cannot create a missing proposal. Some failed candidates
  may still depict part of the ball; keep localization and object identity apart.
- P002 representative 252-254 and 266-269 include top-one-correct observations
  that some graph settings still lose. P003 challenge 174 remains an available
  but missed observation for TT/TW/WT at both displays.
- All four settings retain hidden false observations at P003 167/168 at .20,
  and 168 at .35. Those emitted candidates have zero node context cost because
  they lie inside player rectangles. Stronger distance penalties cannot change
  that zero cost.
- Even WW retains all-grid weaknesses: at .50 it loses top-one-correct P002
  263/264 at every radius, and 262 at radii 10-30. At .01/.03/.05 it loses the
  top-one-correct P003 171 reacquisition across the radius grid. These are
  residual path-choice weaknesses, not new losses introduced by context.

The saved diagnosis reconciles all 1,080 loss partitions and preserves exact
gain/loss frames against motion, all exported crop candidates, and top one.
Its JSON SHA-256 is
`3f2744d8c88c26abd2595384ac83147b623e35a204dbd4aded1704c92ad569e8`.
The readable `residual_diagnosis.md` includes the full display outcome table.
The review retains its presentation limits: truth-centered closeups omit
off-crop false candidates, some saved labels overlap, and the overview reduces
native resolution. Observed player boxes have uncertified completeness and
offline reviewed inputs may use hindsight. Native evidence remains available.

## Next comparison

Test complementary image evidence before adding another movement or proximity
rule. A single fixed detector challenger can change which ball candidates
exist, as well as their ranking. Compare its exported candidates and simple
top-one/top-twenty selectors against the saved RF-DETR controls, keeping the
same windows and crop geometry. The concrete proposal is
`ball_yolo11x_crop_comparison_proposal.md`; it is not authorized or executed.

The alternative of a learned candidate verifier needs a separate, defensible
training set. A missed radius-10 center is not automatically a non-ball label;
the previous winner-only appearance catalog is also selection-biased. Crop
agreement and longer path support do not independently confirm identity.
The previous diagnosis explains those limits in
`ball_candidate_identity_diagnosis.md`.

The implementation and its validation remain unchanged: 34 focused passes,
419 full-suite passes and one existing Windows capability skip. This evidence
and documentation closeout does not warrant rerunning those tests. All nine
original prediction paths remain absent and the three holdouts sealed.
No method, operating point, quality gate, holdout release or Git mutation is
authorized by the visual review or this closeout.
