# Crop comparison: reviewed results and next question

The fixed-crop experiment completed at
`1a9479f83a1766d8979fad07c604bc686d3c52c6`. Ryan reviewed its 12 clips and
stated "all of them look pretty good to me. even P002 challenge". His separate
receipt binds that feedback to the original evidence:
`configs/ball_tracking/reviews/rfdetr_medium_tiled_development_comparison_visual_review_record_v0_1.json`.
Earlier pending-review snapshots remain unchanged.

## What the saved grid establishes

Each row below counts 45 aggregate cells: nine confidence thresholds by five
localization radii, compared at identical settings. These cells reuse the same
short windows and are not independent trials. Pools remain separate.

| Pool | Selector | More correct matches | Equal | Fewer | More matches without more false guesses |
| --- | --- | ---: | ---: | ---: | ---: |
| Representative | All candidates | 44 | 1 | 0 | 0 |
| Representative | Top one | 40 | 1 | 4 | 20 |
| Challenge | All candidates | 45 | 0 | 0 | 0 |
| Challenge | Top one | 45 | 0 | 0 | 26 |

The pooled gains do not erase individual regressions. P002 challenge frames
48-49 lose top-one matches at both displayed settings; P002 representative
258-259 and P001 challenge 219 regress at 0.20. Neither a detector winner nor
an operating point follows from this grid.

## Candidate availability and candidate choice are different problems

At the existing 10-source-pixel radius, a raw match means at least one accepted
candidate has a qualifying center. Top one uses only the most confident guess.

| Pool | Confidence | Crop raw matches | Crop top-one matches | Frames with no qualifying crop candidate | Additional misses caused by top-one choice |
| --- | ---: | ---: | ---: | ---: | ---: |
| Representative, 75 eligible | 0.20 | 62 | 51 | 13 | 11 |
| Representative, 75 eligible | 0.35 | 59 | 50 | 16 | 9 |
| Challenge, 70 eligible | 0.20 | 63 | 59 | 7 | 4 |
| Challenge, 70 eligible | 0.35 | 58 | 55 | 12 | 3 |

This decomposition extracts existing report cells; it does not rerun scoring.
It identifies room for a selector to retain an existing better candidate,
not performance a tracker is guaranteed to achieve. A selector preserving
candidate centers cannot repair a frame with no qualifying accepted center.

## Duplicate removal has a narrower role

The evaluator calls an extra candidate within the truth matching radius a
duplicate false positive. This is a label-assisted scoring category, not a
complete classification of repeated object detections.

| Pool | Confidence | Crop raw false guesses | Extra qualifying centers | Other false guesses |
| --- | ---: | ---: | ---: | ---: |
| Representative | 0.20 | 278 | 26 | 252 |
| Representative | 0.35 | 190 | 24 | 166 |
| Challenge | 0.20 | 81 | 6 | 75 |
| Challenge | 0.35 | 30 | 4 | 26 |

Other false guesses can themselves be repeated clutter detections. A separate
label-blind box-overlap diagnostic therefore counts different-crop candidate
pairs at intersection-over-union (IoU) 0.30, 0.50, and 0.70. IoU is intersection
area divided by union area. Geometry alone does not prove that two boxes depict
the same object, and these counts are not suppression results.

Across the 150 development frames, at IoU 0.50, 101 of 484 accepted candidate
observations at confidence 0.20 and 62 of 337 at 0.35 have a different-crop
overlapping neighbor. These are descriptive composition totals, not merged
representative/challenge performance metrics. The diagnostic retains every
window, frame, pair, and original candidate reference.

Removing lower-ranked duplicates while keeping the highest-confidence
candidate leaves top-one output unchanged. It may reduce candidate clutter,
but cannot recover the additional top-one misses above. The next proposed
experiment therefore targets choosing among crop candidates using recent
history. It does not promise to solve either persistent clutter or detector
misses. The exact design is `ball_crop_candidate_ranking_proposal.md`.

## Reproducibility and boundaries

The create-only diagnostic is
`data/outputs/ball_tracking/tiled_closeout/1a9479f83a17/diagnostic.json`, SHA-256
`87a2e57e147da2907d42286bc6d81d333c011eb5609ba3f71c09291265c0cc3d`.
It binds its generating script, both pool reports, six crop candidate files,
completed review receipt, and original embargo manifest. It contains all 180
aggregate comparisons, displayed per-window outcomes, and 300 frame/display
overlap records. No detector inference, rescoring, suppression, or new
selection output was generated.

All nine original prediction paths remain absent and all three holdouts stay
sealed. No operating point, quality gate, winner, or new experiment is approved.
No production code changed; the existing 18 focused passes and full-suite
341 passes plus one capability skip remain the last code validation.
