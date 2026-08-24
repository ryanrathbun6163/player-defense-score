# Validation History

## Possession 001 — reviewed behavioral baseline

- decoded frames: 499;
- camera homographies: 499;
- possible player-frame pairs: 4,990;
- final coordinate rows: 4,948 (99.16%);
- complete ten-player frames: 473/499 (94.79%);
- trajectory corrections: 98;
- interpolated coordinates: 58 across 23 bracketed gaps;
- remaining gaps: 42 leading observations without a left anchor;
- observed outside-court positions preserved: 22;
- audited interpolated outside-court positions: 3;
- visual review completed through frame 498.

This possession defines behavioral compatibility, not the empirical generalization result.

Sources: Chat 05 opening message `a0b4f63f-838f-49f5-a825-e4f2bfb1f971`; `docs/pipeline_generalization.md`.

## Possession 002 — failure-discovery and hardening case

Possession 002 exposed camera-motion, identity-contamination, team-balance, and path-generalization problems. Important reviewed findings included raw tracks that changed players, incorporated bench/referee phases, or crossed team appearance boundaries. These failures drove explicit splits, match accepts/rejects, config-driven review helpers, geometry safety, and resumable execution.

Possession 002 should not be summarized only by a final coverage number; its durable value is the failure taxonomy and the refactors it forced.

Sources: Chats 05–06; committed `configs/possession_002_*` review files; commits `d1e428a` and `8bd9486`.

## Possession 003 — empirical generalization gate

Possession 003 completed all 21 stages against frozen source commit `8bd9486` without possession-specific source edits.

| Metric | Result | Gate |
|---|---:|---:|
| Homographies | 500/500 (100.00%) | 100% required |
| Coordinate coverage | 4,921/5,000 (98.42%) | at least 95% |
| Complete ten-player frames | 431/500 (86.20%) | at least 85% |
| Final identities | 10 (5 white, 5 dark) | expected 10 and 5/5 |
| Unresolved reviews | 0 | 0 |
| Coordinate-key violations | 0 | 0 |
| Final motion-jump candidates | 0 | reviewed zero |
| Final outside-court positions | 0 | audited |

Synchronized visual review reached the final frame, and generated data/media remained uncommitted. The empirical gate passed, unlocking ball tracking.

Sources: `configs/possession_003_generalization_evidence.json`; `docs/pipeline_generalization.md`; commit `7f603af`.

## Migration-time regression

On 2026-08-22, the clean local checkout at `1954053` passed all 56 discovered unit/regression/safety tests with bytecode writing disabled. This verifies the preserved checkout, not GitHub's later README-only merge.

## Ball annotation — Possession 001 pilot reference

On 2026-08-23, Ryan completed and visually reviewed all 25 approved source
frames (`375..399`) from Possession 001. The set contains 25 labeled rows, 25
geometry points, and no unlabeled or excluded rows. The approved review evidence
is bound to the exact source video and draft annotation hashes; finalization
changes only `review.status`, `review.reviewer_id`, and
`review.reviewed_at_utc`. No ball coordinate or frame-level semantic decision
changes during that transition.

The reference set uses the approved single-annotator review path. It is suitable
for the protocol pilot and initial detector experiments, but it does not claim
inter-rater agreement, unbiased benchmark sampling, cross-game generalization,
or a completed ball-tracking quality gate.

## Ball annotation — Possession 002 pilot reference

On 2026-08-23 America/Phoenix (`2026-08-24T00:30:19Z`), Ryan completed and
visually approved all 25 source frames (`318..342`) from Possession 002. The set
contains 17 partially visible geometry estimates and eight reviewed
`not_visible` occlusions. Sixteen geometry points are localization eligible;
frame 335 preserves an ambiguous visible estimate for audit context but excludes
it from localization scoring.

The reviewed sequence preserves an internal no-geometry gap at frame 330 and a
trailing no-geometry interval at frames 336–342. No hidden-ball coordinate is
interpolated or invented. The approved review package reaches frame 342 and is
bound to the exact source, neutral bundle, draft annotation, generator, and
manifest hashes. Finalization changes only `review.status`,
`review.reviewer_id`, and `review.reviewed_at_utc`.

Like Possession 001, this is a single-annotator pilot reference suitable for
initial detector experiments. It does not claim inter-rater agreement,
unbiased benchmark sampling, cross-game generalization, or a completed
ball-tracking quality gate.

## Ball annotation — Possession 003 pilot reference

On 2026-08-23 America/Phoenix (`2026-08-24T01:05:50Z`), Ryan completed and
visually approved all 25 source frames (`416..440`) from Possession 003. The set
contains five fully visible observed centers and 20 partially visible amodal
center estimates. All 25 identities are `certain`, all 25 geometry points are
localization eligible, and no geometry gap, interpolation, excluded row, or
unlabeled row remains.

The annotation has geometry on every frame, and the center sequence is visually
continuous through final frame 440. Visual review explicitly included the
motion slowdown around frames 432–434 and the overlap-heavy final frames. The
approved package is bound to the exact source, neutral bundle, draft annotation,
generator, and manifest hashes. Finalization changes only `review.status`,
`review.reviewer_id`, and `review.reviewed_at_utc`; the frame-level decision
payload is unchanged.

The three reviewed pilot references now total 75 labeled frames, 67 geometry
points, 66 localization-eligible positives, eight reviewed `not_visible`
negatives, and one visible ambiguous frame intentionally excluded from
localization scoring. These are suitable for initial detector experiments but
remain a curated one-game protocol pilot, not an unbiased benchmark,
cross-game validation set, or completed ball-tracking quality gate.

## Ball detector — label-blind baseline precommit

On 2026-08-23 America/Phoenix, before any selected-window detector prediction
was generated or viewed, Ryan approved three 25-frame evaluation windows per
possession:

| Possession | Representative | Challenge | Holdout |
| --- | ---: | ---: | ---: |
| `possession_001` | `50..74` | `200..224` | `300..324` |
| `possession_002` | `250..274` | `25..49` | `200..224` |
| `possession_003` | `300..324` | `150..174` | `250..274` |

The selection used only verified source pixels and metadata. It applied fixed
edge, pilot, historical-prediction, and between-split separation guards; a
deterministic SHA-256 holdout rule; robust raw-video representative metrics; and
a frozen motion/blur/variability challenge score. Prediction-free 5-by-5 source
contact sheets confirmed uninterrupted live play and no cuts or corruption.
Post-selection congestion observations did not enter the numeric ranking. The
complete reproducibility record and the P001 stale temporary-sheet
reconciliation are in `docs/ball_detector_baseline_selection.md`.

The accompanying feature foundation freezes RF-DETR Medium 1.9.1, the official
weight filename and SHA-256 with package-resolved absolute-path verification,
CUDA FP32 uncompiled inference at 576 by 576,
the raw COCO `sports ball` candidate contract, an inclusive `0.01` export floor,
strict source/Git/runtime provenance, atomic resumability, and an unselected
confidence/localization-radius scoring grid. Focused source/detector validation
passed 129 tests; the full repository suite passed 264 tests. One Windows-only
directory-symlink capability test was skipped in both runs. Bytecode writing was
disabled and formatting checks passed.

The installed RF-DETR 1.9.1 package's real sparse 80-class mapping passed the
adapter contract, and a non-inference construction loaded the frozen weights on
CUDA with the declared 576-pixel resolution, 300 queries, 90 detector classes,
and `num_select=27300`. No source or synthetic frame was supplied. RF-DETR
reported that the older checkpoint lacks `_kp_active_mask`; package source
defines that item as a deterministic keypoint-schema buffer rather than a
learned ball-detection weight.

Only the three reviewed protocol pilots are ready for inference. The nine new
windows remain `annotation_pending_prediction_embargo`, the detector output
directory is absent, and no operating point or ball-detector quality gate has
been selected.
