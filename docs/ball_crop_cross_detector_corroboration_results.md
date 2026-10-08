# RF/YOLO agreement: recovered development results

The tested agreement rule worsened ball localization on all six development
windows. Keep this rule out of the working tracker. This experiment supplies a
negative result we can use to stop pursuing this particular approach; it does
not finish the broader ball-tracking phase or establish a general detector winner.

The rule kept RF-DETR candidates supported by a YOLO box at IoU at least .50,
then chose the supported RF candidate with highest RF confidence. Both saved
candidate sets used the .01 export floor. A match means a center within ten
source pixels of the reviewed reference; it is not an independent object-identity
judgment. Representative and challenge pools remain separate.

## Recovered numerical answer

| Pool | Eligible frames | RF top-one matches | With YOLO agreement | RF wrong-present | With YOLO agreement |
| --- | ---: | ---: | ---: | ---: | ---: |
| Representative | 75 | 51 | 41 | 24 | 33 |
| Challenge | 70 | 60 | 37 | 10 | 32 |

The rule lost 10 correct choices in the representative pool and 23 in the
challenge pool. It recovered no match, suppressed no wrong output, and suppressed
no hidden-ball alarm in either pool. All five existing hidden-ball alarms remained.
Each pool gained one missing output. Suppressing wrong output would not itself
recover localization, but this rule did not deliver that benefit either.

| Window | Matched: RF → agreement | Wrong-present: RF → agreement | Missing: RF → agreement |
| --- | ---: | ---: | ---: |
| P001 representative, 50–74 | 8 → 2 | 17 → 23 | 0 → 0 |
| P002 representative, 250–274 | 20 → 18 | 5 → 7 | 0 → 0 |
| P003 representative, 300–324 | 23 → 21 | 2 → 3 | 0 → 1 |
| P001 challenge, 200–224 | 20 → 10 | 5 → 14 | 0 → 1 |
| P002 challenge, 25–49 | 23 → 15 | 2 → 10 | 0 → 0 |
| P003 challenge, 150–174 | 17 → 12 | 3 → 8 | 0 → 0 |

Every window lost correct matches. The predefined development interpretation is
`not_favorable`, with `pure_regression: true`. No method, operating point, or
production quality gate is selected. These repeatedly inspected development
windows do not establish unseen-game performance.

The earlier standalone YOLO comparison is a different result: at the same
ten-pixel radius, the exported candidate sets covered 87/145 eligible frames for
YOLO and 140/145 for RF-DETR, with no additional matched frame supplied by YOLO.
See [the reviewed detector comparison](ball_yolo11x_crop_recovery_results.md).
Candidate availability is distinct from the selected top-one counts above.

## What failed and what was recovered

Attempt `dcdfd95a942c44f3bccb8d41fe8c795c`, at commit
`decfcbaf642bcff8d04496f8c1274a1c7a415811`, completed selection, evaluation,
rendering, and the compact JSON summary before failing to write `summary.md`.
The Markdown writer serialized raw totals containing per-frame lists and exceeded
its 65,536-byte limit. The saved compact summary is 73,647 bytes, within its own
131,072-byte limit. Its SHA-256 is
`426f07bf143dbe08ca16f5d9eb384bb0e9a20de318fbdd3bcb64c155ad39deb5`.

The original attempt remains failed. Its 340 published files are preserved;
`summary.md`, `provenance.json`, and a completed worker receipt were not produced.
The sealed finished event records 58.562999999994645 charged seconds, verified
owned cleanup, and no memory, time, or output-resource overshoot. Reading this
one finished event for accounting did not replay the journal.

Ryan's October 8 standing policy authorized necessary development-data reads and
routine recovery without another proposal. The recovery read the existing summary
and checked its six frame-state partitions, denominators, paired transitions,
separate pool totals, effects, and interpretation with `_validate_summary`.
An independent read of the six saved window evaluations, two pool evaluations,
and generated manifest agreed with those numbers and the attempt/commit identity.
No detector inference, selection, scoring pass, rendering, or full test suite was
repeated to recover this answer. Recovery does not reclassify the failed attempt
as a successful publication or imply that new human visual review occurred.

Evidence is preserved in:

- `data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/audit/cross_detector_corroboration_v0_1/summary.json`
- `data/outputs/t/corroboration_path_normalization_c946aed/saved_numeric_recovery.json`
- `data/outputs/t/corroboration_path_normalization_c946aed/runtime_failure_audit.json`

## What this establishes for the project

The detector comparison was useful for eliminating this agreement filter. It did
not improve the tracker. Retain RF-DETR candidates as the working baseline and
direct the next ball-tracking work toward selecting the ball and withholding
unreliable observations through occlusion. The earlier completed diagnostic and
human reviews remain available; do not repeat them to resume.

Player-coordinate foundations for three curated possessions are complete. A
usable, reviewed ball trajectory across those possessions remains the immediate
deliverable. Possession understanding, matchup inference, defensive scoring, and
full-game validation still follow it. Existing new corroboration clips have not
received human review; rejecting this numerically worse rule does not promote a
new tracker or certify a visual quality gate.
