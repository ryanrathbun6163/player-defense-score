# WASB cached calibration results

Completed 2026-10-08 using the existing six development windows. **Calibration
improves WASB's coverage, but does not establish a replacement for RF or finish
ball tracking.** Among the eight tested settings, threshold 0.2 gives the most
matches with no wrong selections or hidden alarms: 62/145, versus 31/145 at 0.5.
It still leaves 83 eligible frames missing. RF's pool-wise confidence ranking at
the same output count gives 61 matches and one wrong selection.

At the more permissive threshold 0.1, WASB gives 70 matches and five wrong
selections; equal-count RF gives 72 matches and three wrong selections. No
operating point or quality gate is promoted. Keep RF as the working control and
proceed toward testing learned visual adaptation, rather than assuming a lower
threshold solves the remaining localization problem.

## What was computed

The fixed grid `[0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5]` was declared before
this screen, after the earlier transfer comparison and forced-peak diagnostic
had been inspected. This is a development calibration screen, not a prospective
independent evaluation. It reuses cached mean heatmaps, with no model loading,
media reads, new inference, training, holdout access or rendering.

Every setting uses the existing strict `>` threshold, official eight-connected
weighted components, highest-native-mass selection and ten-source-pixel matching.
The temporal means, frame coverage and original uncertainty semantics are
unchanged. Raw availability means a candidate exists close to truth; it does not
mean the model could identify that candidate without the label.

For each setting, RF's comparison retains the same number of emitted frames as
WASB **separately within each pool**, including hidden/unscored frames in that
count. It ranks saved RF top-one points by confidence, with stable window/frame
ties. Neither ranking nor output-count calculation uses labels. Labels score the
retained results afterward. This is a post-hoc ranking diagnostic, not a deployable
RF threshold or a promise that both methods report the same frames.

## All tested settings, with pools kept separate

Each triple is **matched / wrong-present / eligible missing**. These partition
75 representative or 70 challenge eligible frames. There are no representative
hidden frames; challenge has five hidden frames in one episode.

| Threshold | Representative WASB triple | Representative equal-count RF triple | Challenge WASB triple | Challenge equal-count RF triple | Challenge hidden alarms, WASB / RF |
| --- | --- | --- | --- | --- | --- |
| 0.01 | 18 / 57 / 0 | 51 / 24 / 0 | 18 / 52 / 0 | 60 / 10 / 0 | 5 / 5 |
| 0.025 | 33 / 42 / 0 | 51 / 24 / 0 | 36 / 34 / 0 | 60 / 10 / 0 | 5 / 5 |
| 0.05 | 36 / 11 / 28 | 42 / 5 / 28 | 39 / 30 / 1 | 60 / 10 / 0 | 5 / 4 |
| 0.1 | 33 / 0 / 42 | 32 / 1 / 42 | 37 / 5 / 28 | 40 / 2 / 28 | 0 / 0 |
| 0.2 | 29 / 0 / 46 | 29 / 0 / 46 | 33 / 0 / 37 | 32 / 1 / 37 | 0 / 0 |
| 0.3 | 27 / 0 / 48 | 27 / 0 / 48 | 27 / 1 / 42 | 27 / 1 / 42 | 0 / 0 |
| 0.4 | 21 / 0 / 54 | 21 / 0 / 54 | 21 / 0 / 49 | 20 / 1 / 49 | 0 / 0 |
| 0.5 | 17 / 0 / 58 | 17 / 0 / 58 | 14 / 0 / 56 | 14 / 0 / 56 | 0 / 0 |

The descriptive combined totals clarify the main tradeoff:

| Method / policy | Matches | Wrong eligible outputs | Eligible missing | Hidden alarms |
| --- | ---: | ---: | ---: | ---: |
| Existing RF baseline, confidence 0.01 | 111 | 34 | 0 | 5 |
| WASB 0.5, original policy | 31 | 0 | 114 | 0 |
| WASB 0.2 | 62 | 0 | 83 | 0 |
| RF ranked to the same pool output counts as WASB 0.2 | 61 | 1 | 83 | 0 |
| WASB 0.1 | 70 | 5 | 70 | 0 |
| RF ranked to the same pool output counts as WASB 0.1 | 72 | 3 | 70 | 0 |

At 0.5, equal-count RF also gets 31 matches, zero wrong outputs and zero hidden
alarms. Its correct frames differ: each method supplies eleven correct frames
absent from the other's retained set. Thus the original sparse zero-error result
is not unique evidence of superior discrimination. This does not measure a
combined method or authorize selecting correct outputs using labels.

At 0.2, WASB recovers one match absent from the full RF baseline and loses 50 RF
matches. At 0.1 it recovers one and loses 42. The largest WASB match total in this
grid is 75 at 0.05, accompanied by 41 wrong eligible outputs, 29 missing frames
and five hidden alarms; its equal-count RF comparison has 102 matches, 15 wrong
outputs, 28 missing frames and four hidden alarms. A much lower threshold can
merge components, move their weighted centers and change their mass ordering;
neither correct localization nor raw availability is monotonic in the threshold.
The largest sampled raw WASB availability is 85/145 at 0.025, compared with
140/145 for the saved RF candidates. Raw availability at 0.2 is exactly its 62
selected matches. A better final selector alone cannot recover candidates that
this thresholded representation did not emit near the reviewed center.

## Where threshold 0.2 still fails

| Possession / pool | Inclusive frames | WASB matched / wrong / missing |
| --- | --- | --- |
| 001 representative | 50–74 | 0 / 0 / 25 |
| 001 challenge | 200–224 | 4 / 0 / 21 |
| 002 representative | 250–274 | 19 / 0 / 6 |
| 002 challenge | 25–49 | 20 / 0 / 5 |
| 003 representative | 300–324 | 10 / 0 / 15 |
| 003 challenge | 150–174 | 9 / 0 / 11; five hidden frames also withheld |

Possession 001 remains particularly weak. At 0.1 its representative window still
has zero matches, while its challenge window has four matches, one wrong point
and twenty missing frames. This agrees with the earlier cached peak diagnostic:
some useful response was below the published threshold, but some strong responses
were in the wrong locations. Threshold calibration alone has not solved that.

## Evidence and checks

Committed configuration:
`configs/ball_tracking/wasb_experiments/wasb_basketball_calibration_v0_1.json`,
SHA-256 `24961ca05fdd8c8ac925843b77f59fa87ee8db959ff63f8ef4e9d502f35c5cb6`.
It binds six genuine caches, annotations, RF candidates and original reports.
Generated evidence is under
`data/outputs/ball_tracking/wasb/wasb_basketball_calibration_v0_1/`.
The summary SHA-256 is
`2d177321c08cb600a4d54ccb324e1113c1583eda4ab167f299a8f4d2dcde4552`.

One cached-screen invocation completed successfully in 2.851 seconds. Its source
and input digests, software versions and completion receipt are preserved. All
42 bound original input files remain unchanged. The 0.5 output reproduces the
original candidate records and raw/top-one reports on all six windows; the saved
RF baseline reports also agree on all six. Nine focused tests passed, covering
actual component-to-evaluator behavior, strict thresholds, label-free ranking,
hidden-frame accounting, cache integrity and preserved failure records. An
independent code review found no actionable scoring or label-boundary defect.
An independent saved-record audit reconciled all 48 window evaluations and
verified all 16 equal-count RF ranking records against the original predictions.
No full-suite run or rerun of the earlier scientific comparisons occurred.

No human review of these new threshold outputs has occurred. Numerical rejection
of an inadequate setting does not require repeated visual review. Earlier reviews,
failed attempts, consumed resources, original predictions and holdouts remain
unchanged. Ten-pixel agreement is still a geometric measure, not independent
proof of physical ball identity or a continuous trajectory.

## Next useful step

The [adaptation plan](ball_wasb_adaptation_plan.md) specifies one small pretrained
training trial using the three already reviewed pilots, then evaluation on these
six development windows. There are 66 eligible training centers, eight hidden
negatives and one ambiguous frame to mask. Training and evaluation inputs are
disjoint; both remain correlated same-game footage. No additional labels are
needed for this limited diagnostic. Training has not run, and no training-derived
checkpoint exists yet.

This screen answers the calibration question without another model run. Reliable
ball tracking across the complete three possessions, synchronized human visual
acceptance, and broader generalization remain unresolved.
