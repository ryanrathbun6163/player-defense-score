# Temporal-association experiment: reviewed results

Ryan acknowledged inspection with "inspected. please move forward" after the
12-clip review request. The receipt is
`configs/ball_tracking/reviews/rfdetr_medium_temporal_association_visual_review_record_v0_1.json`.
It records inspection completion and permission to continue work, not a
quantitative quality judgment or a selected tracker.

## What the experiment established

The approved experiment ran at `6769e07476da09d858fa42f82aace024d21f7735` using
six immutable development detection files. It produced 324 observation files,
1,620 per-window reports, two separate 270-cell aggregate grids, and 12 review
clips. All raw-control reports reproduce the earlier detector outcomes.
The original execution record and media manifests retain their historical
pending-review state; the later receipt records Ryan's inspection.

At both predeclared display thresholds (0.20 and 0.35), with a 10-pixel raw
center-distance radius, the highest-confidence control retains more correct
matches than every tracklet variant in both pools. Tracking sometimes removes
false guesses, but also removes real observations. P001 challenge frame 224 and
P003 representative frame 324 show this loss directly.

The complete grid is more nuanced than those two views. The table counts the
180 tracklet cells in each pool: four linking variants, nine confidence
thresholds, and five radii, each compared with top-one at the same settings.

| Pool | Fewer correct matches | Equal matches | More matches | More matches without more false guesses |
| --- | ---: | ---: | ---: | ---: |
| Representative | 112 | 5 | 63 | 0 |
| Challenge | 150 | 1 | 29 | 0 |

Every tracklet cell gaining correct matches also adds false guesses. For
example, at confidence 0.01 and radius 10, the wide-link/two-missing-frame
variant gives 54 correct matches and 10,347 false guesses in the representative
pool, versus top-one's 46 and 29. Challenge counts are 57 and 10,048 versus 47
and 28. Retaining many hypotheses can increase candidate availability without
identifying one reliable ball trajectory.

These cell counts are correlated comparisons over the same short clips, not
independent trials or a statistical significance claim. Top-one has not been
selected as an operating policy; it remains a comparison control.

## Detector limitations remain upstream of association

At the saved 0.01 export floor, count eligible frames with at least one
candidate within the existing 10- and 30-pixel grid radii:

| Window | Eligible frames | Candidate within 10 px | Candidate within 30 px |
| --- | ---: | ---: | ---: |
| P001 representative | 25 | 10 | 25 |
| P002 representative | 25 | 23 | 25 |
| P003 representative | 25 | 25 | 25 |
| P001 challenge | 25 | 18 | 25 |
| P002 challenge | 25 | 25 | 25 |
| P003 challenge | 20 | 19 | 19 |

A selector preserving original candidate centers cannot create a qualifying
center where none was exported. At radius 10, 17 representative and eight
challenge frames lack one even at the export floor. At confidence 0.20,
another 11 representative and 14 challenge frames lose their qualifying
candidates to confidence filtering. These two causes account exactly for the
raw baseline's 28 and 22 misses. Association can introduce further losses.

The 30-pixel column describes localization sensitivity; it does not relax the
protocol or select a radius. At low confidence there are many candidate boxes,
so proximity to a label alone does not prove a candidate represents the ball.
Nor do these counts prove that input resolution, blur, or camera movement
caused the detector's errors. Missingness remains explicit.

## Next concrete experiment

Test the same frozen detector on a fixed grid of overlapping image crops,
using these same six development windows. This gives small objects more input
pixels and tests whether candidate coverage/localization improves. Cropping
also changes context and increases computation, so improvement is a hypothesis.

The exact proposed scope is in
`docs/ball_detector_tiled_comparison_proposal.md` and its proposal JSON.
No new detector experiment has run. The original nine prediction paths remain
absent, the three holdouts remain sealed, and no quality gate or operating
point has been selected. The existing player pipeline is unchanged.

## Reproducibility and validation

The ignored diagnostic is
`data/outputs/ball_tracking/temporal_closeout/6769e07476da/diagnostic.json`,
SHA-256 `845dc1d7e7ead0ec952c27985595878c3e13488af54c1dc1f946ae207d6cce77`.
It contains all 360 same-cell comparisons, all 270 raw miss decompositions with
frame IDs, both report bindings, and its generating script hash. It checks
that threshold-qualified matches are a subset of export-floor matches and that
both miss categories sum to every stored raw false-negative count.

Receipt creation reverified all 2,412 review assets, 12 playback clips, 324
observation files, two scoring grids, six labels/raw files, and 59 protected
file bindings. This closeout changes documentation and review records only.
The completed implementation's full-suite result remains 323 passed and one
existing capability skip; no new production-code test run is claimed.
