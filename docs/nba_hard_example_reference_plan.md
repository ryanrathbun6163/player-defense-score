# NBA difficult-scene reference batch

**Current status: approved batch accepted and saved-output scoring complete.**
Ryan approved this exact scope with “Ok move forward”, then accepted all four
complete [label-review packages](nba_hard_example_reference_review.md) without
corrections. The separate [scope approval](../configs/ball_tracking/reviews/nba_hard_example_reference_approval_v0_1.json),
[preparation record](../configs/ball_tracking/reviews/nba_hard_example_reference_preparation_v0_1.json)
and [label acceptance](../configs/ball_tracking/reviews/nba_hard_example_label_acceptance_v0_1.json)
preserve those distinct events and the unchanged original proposal.

The [completed diagnostic](nba_hard_example_reference_results.md) uses the
accepted AI reference: 387 defensible centers and 133 null centers among 520
frames. Saved outputs produce 305 matches, 13 localization errors and 69 missing
outputs on eligible centers, plus 13 alarms in 86 hidden-ball frames. Separate
longer-context pilot controls remain 120/120, including their eight changed
context edges; the original short-context result is unchanged.

No new inference, training, threshold change or heatmap reaggregation occurred.
None of the 82 localization failures has a usable alternative in the saved
strict `>0.3` component inventory. The next recommendation is to prepare a
bounded inspection of saved heatmaps before choosing fitting or threshold
changes; no new experiment is approved here. The original proposal below is
preserved as historical evidence, including its original pending status.

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
