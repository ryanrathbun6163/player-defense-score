# NBA difficult-scene reference batch

Ryan approved the exact scope below with “Ok move forward”. The separate
[approval record](../configs/ball_tracking/reviews/nba_hard_example_reference_approval_v0_1.json)
binds the unchanged original proposal, whose pending status is historical.
The four [label-review packages](nba_hard_example_reference_review.md) are now
prepared: 520 AI proposals, including 387 proposed centers and 133 null centers.
The [preparation record](../configs/ball_tracking/reviews/nba_hard_example_reference_preparation_v0_1.json)
binds source evidence, preserved attempts, passing focused tests and all four
completed media audits.

**Ryan's label acceptance is pending.** No new accepted reference, scoring,
inference or training has occurred. After explicit acceptance, publish separate
accepted AI references and score saved outputs within the original approved
scope. The original proposal below remains intact as the record of that decision.

## Original proposal (historical)

Ryan reported review of both longer prediction videos: “Ok reviewed. What’s
the next step”. The [later review record](../configs/ball_tracking/reviews/nba_wasb_action_observation_visual_review_v0_1.json)
records completion without inferring a favorable accuracy judgment. The known
distractor selections and gaps remain in the original outputs.

The next useful measurement is whether the model has no usable ball candidate,
or has one but chooses a hand, head or spectator instead. Correct reference
positions let us distinguish those cases before choosing a model change.

This [exact proposed scope](../configs/ball_tracking/selections/nba_hard_example_reference_proposal_v0_1.json)
is **design-only, awaiting approval**. No new labels, scoring or inference have
been performed in preparing it.

| Game | Original source frames | New labels | Why this section |
| --- | --- | ---: | --- |
| SAC–MEM | 940–1059 | 120 | Distractor switches, missing intervals and recovery |
| SAC–MEM | 1240–1359 | 120 | Repeated missed observations while the ball is held |
| SAS–DET | 11000–11119 | 120 | Wrong-arm selections, the longest gap and recovery |
| SAS–DET | 11420–11579 | 160 | Drive, rim overlap, visibility uncertainty and recovery |
| Total | Four short sections | 520 | About 8.7 seconds of native footage |

The assistant would prepare first-pass labels against the original verified
PNGs: the complete ball center where defensible, visibility and uncertainty.
Unsupported positions stay unknown. Predictions are not reference truth; the
assistant has seen the model output, so this is explicitly not blind labeling.

Ryan would receive four complete short label-overlay videos directly in chat
for phone review, plus an exception list. He reviews each through its actual
final frame. The assistant handles routine corrections. Only after explicit
label acceptance would a separate human-accepted AI reference be published and
used for scoring.

Scoring would consume the already saved predictions and candidate lists. Keep
the existing inclusive ten-source-pixel localization rule and report uncertainty
separately. Count correct positions, wrong selections, visible-ball misses and
hidden-ball alarms where suitable reviewed labels exist. Check whether an
alternative candidate was near the ball when the chosen point was wrong.
Unsupported centers remain unscored; missing output does not prove invisibility.

The 120 accepted short-pilot labels would also serve as separate easy controls
against the longer-context outputs, for at most 640 scored saved observations.
Preserve the original short-context result and distinguish its eight edges that
gain longer context. No new model calls, threshold changes, motion rules,
training or full-game decoding are part of this increment.

These sections were selected after observing failures. They can diagnose
development problems, but cannot estimate overall NBA accuracy or serve as an
independent test. Adjacent frames are correlated. SAC retains future-training
eligibility; DET remains development-only and excluded from fitting. TOR,
protected holdouts, the NFHS finish line and three pending motion-study human
reviews remain unchanged.

Approval would cover preparing these proposals, complete review packages,
routine corrections and scoring saved outputs after label acceptance. It would
not authorize a new fit. A later improvement proposal should follow the measured
split between missed ball evidence and wrong candidate selection.
