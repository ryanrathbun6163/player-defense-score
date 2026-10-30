# Appearance references accepted

Ryan explicitly said: “I accept the proposals. Move forward chat”. The
[acceptance record](../configs/ball_tracking/reviews/nba_appearance_reference_acceptance_v0_1.json)
records acceptance of all 26 proposals, including the six unresolved cases.
One publication run created a separate human-accepted AI reference in 0.696
seconds. The original pending proposal, seal, review media and disagreement
record remain unchanged. The
[publication result](../configs/ball_tracking/reviews/nba_appearance_reference_publication_result_v0_1.json)
binds the accepted artifact, exact implementation and validation.

| Source role | Ball | Other object | Unresolved |
| --- | ---: | ---: | ---: |
| Potential reference bank: SAC/P002 | 4 | 6 | 5 |
| Excluded development checks: DET/P003 | 6 | 4 | 1 |
| Accepted total | 10 | 10 | 6 |

Acceptance closes this appearance-label review. It preserves assisted
authorship and uncertainty; it does not assert independent human annotation,
measured playback telemetry or acceptance of new model predictions. DET11499
remains unresolved, with both earlier AI judgments preserved. Unresolved
records are not negative examples. No new ball center or geometric score was
created, and no coordinate or trajectory changed.

## What this evidence can support

All ten resolved potential-fit examples are from SAC: four balls and six
distractors across five targets in two short action blocks. All five P002
examples are unresolved. The SAC negatives include two heads in one frame,
two hands, and two nearby patches of one jersey. These are candidate records,
not ten independent episodes.

The ten resolved checks contain five DET balls, four DET hands and one P003
ball. Neighboring hand observations are correlated, and there is no excluded
head or clothing negative. The checks are separated from a future reference
bank, but were already seen in development; P003 also trained the retained
detector. The batch cannot establish reliable trained-verifier accuracy or
support threshold selection. Contributor-only fill candidates have no new
accepted appearance labels in this batch.

The concrete next proposal is a
[single frozen image-feature screen](nba_appearance_feature_screen_plan.md).
It asks whether one unchanged pretrained representation can separate the ten
resolved checks using only the ten resolved SAC examples as references. It
will not train a classifier or update trajectories. All six unresolved records
remain unscored, and prior gap/anchor cases remain a separately reported,
previously exposed regression challenge. A pass would support designing one
later conservative appearance policy, not adopting a verifier.

## Publication validation

Six focused tests passed on their first run in 10.845 seconds. Fixtures use the
authorized captured producer records. Checks cover exact candidate/source/label
transport, role and seal mismatches, altered review joins, same-length encoded
media mutation, failed-attempt preservation and exact resume. A final test-only
correction made the suite skip a checkout without the ignored captured records;
all six checks passed again in 10.971 seconds. The original test source and log
are preserved. The publisher and actual publication were unchanged, and no full
suite or earlier media render was repeated.

The actual publication verified all 33 reviewed media files by byte hash
(24,201,866 bytes), without source-pixel decoding, model calls, candidate-array
reads or geometric scoring. It preserves all 26 candidates, fifteen targets,
75 source contexts, source roles and exact proposal rows. The independent
actual-publication audit passed 380 checks and is bound in the compact result.

Implementation ran as the exact tested local files, then was integrated with
this record; no pre-execution commit is claimed. The original 790-frame report,
accepted 27-reference extension, seven controls, retained checkpoint, rejected
NBA continuation, protected holdouts and all earlier review statuses remain
unchanged. No feature extraction, fitting, new scientific screen, threshold
search, push, PR or merge was performed in this acceptance increment.
