# NBA difficult-scene reference and saved-output results

Ryan accepted all four complete label-review packages, including uncertainty,
unknown centers and actual final frames, without corrections. The separate
[acceptance record](../configs/ball_tracking/reviews/nba_hard_example_label_acceptance_v0_1.json)
retains his complete statement and binds the presented evidence. A separately
published [accepted AI reference](../data/outputs/ball_tracking/nba/hard_example_reference_v0_1/accepted/reference.json)
contains 520 frames: **387 defensible centers and 133 null centers**. AI authorship,
prior model exposure and the original drafts remain explicit.

The [compact result record](../configs/ball_tracking/reviews/nba_hard_example_saved_diagnostic_result_v0_1.json)
binds the saved diagnostic and validation. The
[completed run](../data/outputs/ball_tracking/nba/hard_example_reference_v0_1/diagnostics/saved_score_v0_1/completion.json)
took 1.094 seconds and consumed existing observations and their complete saved
candidate inventory. It made **zero model calls, training runs, image/video
decodes or heatmap reaggregations**. The frozen checkpoint and strict `>0.3`
component threshold are unchanged.
The [preservation receipt](../data/outputs/ball_tracking/nba/hard_example_reference_v0_1/validation/acceptance_prior_preservation_01.json)
confirms that all 29 scoped prior artifact bindings remain unchanged.

## What the saved predictions show

Matches use the existing inclusive ten-source-pixel rule. Annotation uncertainty
is reported separately and does not change the match boundary.

| Difficult window | Eligible centers | Matched | Wrong location | Missing | Hidden alarms / hidden frames | Other unscored |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SAC 940–1059: distractors and recovery | 90 | 87 | 3 | 0 | 0 / 17 | 13 |
| SAC 1240–1359: held ball | 120 | 71 | 2 | 47 | 0 / 0 | 0 |
| DET 11000–11119: distractors and gap | 65 | 45 | 0 | 20 | 12 / 41 | 14 |
| DET 11420–11579: drive and rim overlap | 112 | 102 | 8 | 2 | 1 / 28 | 20 |
| Total | 387 | 305 | 13 | 69 | 13 / 86 | 47 |

The 305/387 matches represent 78.8% of eligible centers in these selected
windows. All 13 wrong locations lie just beyond ten pixels and at most 14.755
pixels from the accepted center. The mean distance across all 318 emitted
eligible points is 4.909 pixels. A wrong-location count does not imply that each
point is a distant spectator or hand selection.

The 133 null-center frames remain localization-unscored. Of these, 86 have
certain/probable hidden-ball labels, enabling a separate alarm check: 13 emitted
points (15.1%) and 73 quiet outputs. The other 47 frames remain unscored,
including partially visible evidence without defensible geometry and
indeterminate visibility. Missing output does not prove invisibility.

The longest eligible missing run is DET 11075–11093: 19 frames, 0.317 seconds,
followed by an unknown label, so it does not support a recovery claim. SAC's
held-ball gap at 1269–1284 lasts 16 frames, 0.267 seconds, and the following
labeled frame matches. The mean distance on matched points is 4.635 pixels.

**None of the 82 localization failures has an alternative saved candidate within
ten pixels.** This includes all 69 missing outputs and 13 wrong locations.
Reordering the existing strict `>0.3` components therefore cannot fix these
failures. This finding does not establish whether useful ball evidence exists
below the threshold or whether a different heatmap shape would improve centers.

The 120 existing pilot references are separate easy controls: 120 matches,
zero wrong locations and zero missing outputs against the longer observations.
Eight pilot edges have longer context. This new control result leaves the
original accepted 120/120 short-context score unchanged; the cohorts are not
pooled into a headline accuracy number. A separate
[preservation check](../data/outputs/ball_tracking/nba/hard_example_reference_v0_1/validation/original_short_pilot_preservation_01.json)
confirms the tracked original result and five generated score JSON files are
byte-identical to their earlier bindings.

## Validation and interpretation

Thirty distinct focused checks passed in this increment: 21 publication-related
checks (six new, six existing reviewed-reference and nine asset checks), plus
nine scorer checks. The initial scorer run had seven fixture setup errors among
nine tests; the failed attempt and subsequent passing correction are retained.
The prior 26 preparation checks are a separate historical scope. The full suite
and earlier scientific runs were not repeated. Independent review of the scorer
found no actionable issues.

The independent [actual-report audit](../data/outputs/ball_tracking/nba/hard_example_reference_v0_1/diagnostics/saved_score_v0_1/independent_audit_01/audit.json)
passed on its first attempt with zero issues. It checked 20 bound JSON/source
files, all 2,702 producer inventory records and all 640 emitted scored rows;
summaries and native-time intervals agree. It independently confirmed all 112
unchanged pilot interiors and eight changed-context edges. This verifies the
saved diagnostic's computation and evidence joins, not independent label accuracy.

These are correlated, failure-selected development examples with human-accepted
AI labels, not independent human annotations or a representative NBA benchmark.
The four accepted review videos display label centers at six source frames per
second. Their smooth appearance and Ryan's favorable comparison with high-school
clips do not measure improved model trajectories or comparative accuracy.

The recommended next step is to prepare a bounded inspection of saved heatmaps
around the 69 misses and 13 marginal localization errors, to learn why they lack
a usable above-threshold component before deciding on fitting or threshold
changes. That recommendation does not approve a new experiment.

SAC retains future-training eligibility; DET remains excluded from fitting and
TOR remains outside scope. The NFHS finish line, protected holdouts, prior pilot
acceptance and negative motion result are unchanged. Its three human reviews
remain pending. Detailed references, predictions, reports and media stay ignored.
