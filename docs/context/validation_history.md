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

## Ball detector — development execution and visual approval

On 2026-09-19 UTC (2026-09-18 America/Phoenix), the approved versioned
development release completed at clean commit
`84bcc8da143e54ff17a28b39db0e70c4b8b299c8`: 150/150 inference frames,
22,931 raw candidates, two separate 45-cell scoring grids containing 270
per-window reports, and six synchronized comparison clips. Implementation
validation ran 299 tests: 298 passed, one existing directory-symlink capability
test skipped. No production code changed during the later review-record step.

Ryan subsequently approved the six linked comparison videos as a solid starting
point while noting small detection blips. His exact statement is preserved in
`configs/ball_tracking/reviews/rfdetr_medium_development_candidate_comparison_review_record_v0_1.json`
(SHA-256 `a60dea646736135620fb97eba9f1985f7b06f0c7bfc7abee38537580c05f4dba`).
Both bundle-integrity checks, all six original/playback video hash pairs, and
59 protected file hash/Git-blob bindings were reverified when recording approval.
The original execution record remains unchanged as an earlier pending-review
snapshot. The approval receipt is a later audit record, not a new execution permit.

Visual approval does not establish complete trajectories: these remain
independent frame detections. At the two 10-pixel display cells, representative
recall is 62.7% at confidence 0.20 and 52.0% at 0.35; challenge recall is 68.6%
and 58.6%, respectively. P001 remains the weakest possession. All original
v0.1 embargo paths remain absent; only six separately authorized v0.2 development
outputs were generated. Three test holdouts remain sealed, and no operating
point, quality gate, or model winner was selected. A temporal-association
experiment is proposed but has not run.

## Ball temporal association — synthetic implementation validation

The first temporal-association experiment is authorized by Ryan's "lets move
forward" response to its linked design. Separate derived contracts, 54-variant
association, scoring, resumable execution, and synchronized review support are
implemented without changing the frozen detector or annotations. The manifest
specification SHA-256 is
`ef2f7a2a77f334c94d0efc045311c6fd4a3cc86695aec84934bacbfb06605ab5`.

The final focused suite passed 25 tests. The full repository suite ran 324
tests in 147.691 seconds: 323 passed and one existing directory-symlink
capability test skipped. Tests used `.venv` with bytecode disabled. Synthetic
integration exercised all 324 observation files, 1,620 per-window reports,
two distinct 270-cell pools, complete review-video decoding, final-frame
inclusion, exact resume, and tamper rejection. Raw control metrics match the
established evaluator. The first full-suite attempt was stopped after an
agent-inspected synthetic preview prompted a readability fix; the reported
full-suite result is the subsequent run against final code.

Real-data dry-run passed for exactly six saved development windows and 150
frames. Prior protected files, saved detection hashes, and nine absent parent
prediction paths were reverified. No real temporal outputs exist yet. Staging
and committing the documented 13-file scope remain separately authorized steps
before execution at a clean checkpoint. The three holdouts remain sealed, and
operating-point and quality-gate selections remain unset.

## Ball temporal association — execution and inspected evidence

Ryan separately authorized the 13-file implementation commit with "yes commit".
Commit `6769e07476da09d858fa42f82aace024d21f7735` then ran the already approved
experiment at a clean checkpoint: 324 saved-detection observation files,
1,620 per-window reports, two separate 270-cell aggregate pools, and 12 review
clips. All 270 raw-control reports reproduce the earlier detector metrics and
per-frame outcomes, excluding the intentionally different derived input count.
All 2,412 bound review assets verified; 12 original videos and their 12 H.264
playback copies fully decoded through their 25th frame. The agent inspected
the 12 final-frame closeup sheets without claiming all-frame visual inspection.

Ryan then stated "inspected. please move forward" in response to the linked
temporal review package. The new
`configs/ball_tracking/reviews/rfdetr_medium_temporal_association_visual_review_record_v0_1.json`
binds that statement to the exact 12 clips and review artifacts. Its timestamp
records receipt creation, not an invented event time. This completes the
requested inspection; it does not select a tracker or approve a quality gate.
The original execution record and visual manifest retain their historical
pending-review state. All source media and generated outputs remain ignored.

A read-only closeout over all saved cells found that 63 representative and
29 challenge tracklet cells gain correct matches versus same-cell top-one;
every gain also adds false guesses. The 360 comparisons and 270 raw miss
decompositions are recorded in
`data/outputs/ball_tracking/temporal_closeout/6769e07476da/diagnostic.json`,
SHA-256 `845dc1d7e7ead0ec952c27985595878c3e13488af54c1dc1f946ae207d6cce77`.
These are descriptive correlated comparisons, not independent trials.
At the two displayed confidence settings/radius, every tracklet variant loses
correct matches in both pools. The diagnostic also identifies detector and
confidence-filter losses that association cannot recover with unchanged centers.

Receipt creation rehashed the review assets, playback clips, observations,
reports, six annotations/raw detections, and 59 protected files. All bindings
matched; all nine original prediction output paths remain absent. No new
production code or detector inference was introduced during closeout, so no
new full-suite result is claimed. The next fixed-crop comparison is a concrete
proposal awaiting its own experiment approval, not an executed result. All
three holdouts stay sealed; operating-point and quality-gate fields stay null.

## Ball detector crop comparison — approval and implementation

Ryan approved the linked fixed-crop experiment with "yes i approve". Its new
approval receipt binds the unchanged proposal to executable specification
`3384a930d8633b202b689857de2bea4939277a2d2f0c3da483c2c48e9e9ef023`.
Separate candidate, inference/resume, scoring, and review modules preserve the
existing whole-frame detector contract. Crop geometry is independent of labels;
both coordinate systems, duplicates, original candidate references, timing,
and CUDA peak allocated bytes are recorded. The existing player pipeline and
the approved temporal design/manifest remain unchanged.

Final focused validation passed 18 synthetic tests in 74.915 seconds. Coverage
includes all 600 model calls, exact and interrupted resume, whole-frame control
parity across every cell, all 1,080 per-window scores, 12 fully decoded review
videos, every final frame, and 1,950 supporting images. It also checks dirty-Git
refusal, label-blind loading, all nine original embargo paths, changed input
scope/provenance, and tampering. The first focused run found a sidebar-width
rendering mismatch and a synthetic class-ID fixture mismatch; both were fixed.

Real-input preflight passed against the source clips, frozen RF-DETR package
and weights, and installed RTX 5070 CUDA runtime. No model prediction ran.
Agent visual inspection covered synthetic comparison and closeup previews only.
The final full suite ran 342 tests in 223.084 seconds: 341 passed and one
existing directory-symlink capability test skipped. Bytecode writing was
disabled. Formatting, new-file syntax/whitespace, and exact 15-file scope
checks passed. The final audit reverified 59 protected files, six raw
predictions, all reviewed labels, the immutable proposal, and the nine absent
embargo outputs. Logs, synthetic previews, and hash/Git-blob validation records
remain ignored under `data/outputs/ball_tracking/tiled_implementation_validation/`.

Separate staging and commit approval are still needed for the documented
15-file implementation checkpoint. The already approved experiment may run
after that clean checkpoint, with human visual review afterward. No operating
point or quality gate is selected, and all three test holdouts remain sealed.

## Ball detector crop comparison — committed execution and review handoff

Ryan authorized staging with "yes stage" and the exact 15-file commit with
"commit please". Commit `1a9479f83a1766d8979fad07c604bc686d3c52c6` has parent
`6769e07476da09d858fa42f82aace024d21f7735`; its complete tree and all 15 Git
blobs match the previously validated staged scope. The index and worktree
were clean after commit. Nothing was pushed.

The already approved fixed-crop experiment then ran at that clean commit:
600 crop calls across 150 source frames in exactly the six declared windows,
600 immutable view checkpoints, and six separate candidate files. All stages
used the repository `.venv` with bytecode disabled. End-to-end inference took
136.28 seconds; synchronized model calls totalled 96.02 seconds, including
16.32 seconds for the first call. Median four-crop frame time was 0.532 seconds,
and peak PyTorch CUDA allocation was 0.220 GiB. Saved whole-frame timing was
not measured, so no runtime ratio is claimed. The installed model emitted
the same deterministic keypoint-buffer warning recorded for the frozen control;
package, weights, runtime, precision, and target-class rules were unchanged.

Scoring produced 1,080 per-window reports and 180 aggregate cells in each
separate representative/challenge pool. A read-only audit compared all 540
saved-control raw/top-one cells to the prior reviewed temporal reports.
Scoring metrics and per-frame outcomes match exactly; adapter-stage input and
below-threshold bookkeeping counts are excluded. Candidate provenance,
all 600 crop checkpoints, six saved detection files, six annotation bindings,
and 59 protected files verified. All nine original embargo paths stay absent;
the three holdouts remain sealed.

Rendering produced 1,962 hash-verified assets: 12 synchronized four-panel
videos, 300 comparison PNGs, 300 closeup sheets, 1,200 native overlays, and
150 crop-context images. All 12 originals and separate H.264 playback copies
fully decoded through 25 frames at 5 fps. The agent directly inspected every
final-frame closeup plus a hidden-frame comparison and crop-boundary context;
all-frame human visual review is pending. This does not replace Ryan's review.

At both displayed confidence settings and 10-pixel radius, both pools gain
matches with crop inputs but also add false guesses. Individual deteriorations
are preserved: P002 challenge frames 48-49 lose top-one matches at both views.
The full grid and per-frame recovered/lost lists remain available. No setting,
winner, quality gate, or generalization claim is selected.

The ignored handoff is
`data/outputs/ball_tracking/tiled_execution/1a9479f83a17/review_guide.md`.
The corresponding `execution_record.json` has SHA-256
`4d7977be4e08c9e70df438a007cbe92de4be60bed14eccc4d75a581aff137b52`.
The review bundle is
`data/outputs/ball_tracking/tiled_development/rfdetr_medium_tiled_development_comparison_v0_1/review/a007aa4b358587789f7ef1f28b1c66b5/`.
Execution and verification completed before these three context-file edits.
No new code changed, so the existing 18 focused passes and 341 full-suite
passes plus one skip were not rerun; the context diff received a whitespace
check. Next is Ryan's inspection of all 12 clips through their final frames.

## Ball detector crop comparison — completed human review

Ryan responded to the complete 12-clip review package with "all of them look
pretty good to me. even P002 challenge". The separate receipt
`configs/ball_tracking/reviews/rfdetr_medium_tiled_development_comparison_visual_review_record_v0_1.json`
(SHA-256 `6e108189b792d505c97adbcfcce5aa635a6e140893a6306e0c08bfe910218adb`)
binds his exact statement to the execution commit, review manifest, both scoring
pools, all original/playback clips, and final-frame closeups. Receipt time is
creation time; no separate user-message event time is invented. The original
pending-review evidence remains unchanged as historical provenance.

Read-only closeout rehashed all 1,962 review assets, 12 playback clips and final
closeups, two pool reports, six crop candidate files, and six saved whole-frame
detection files; all hashes matched. All nine original prediction embargo paths
remain absent, and all three holdouts remain sealed. No experiment or tests were
rerun and no production code changed. Visual review completion does not select
an operating point, quality gate, winner, or authorize another experiment or
Git mutation. The previously reported numerical gains and losses remain valid.

## Ball detector crop comparison — saved-result closeout and next design

Following "lets move forward chat", a new ignored diagnostic extracted all
180 same-cell aggregate crop/whole-frame comparisons and 48 displayed
per-window reports from the two bound scoring pools. It checked displayed
per-frame TP/FP/FN/duplicate/hidden counts and exact raw/top-one miss
decompositions. Label-blind overlap counting retains 300 frame/display
records with original cross-crop candidate references. No candidate was
suppressed, no selected output was created, and no detector or scoring ran.

Diagnostic SHA-256:
`87a2e57e147da2907d42286bc6d81d333c011eb5609ba3f71c09291265c0cc3d`;
path: `data/outputs/ball_tracking/tiled_closeout/1a9479f83a17/diagnostic.json`.
The new results note distinguishes extra qualifying centers from geometric
overlap and preserves all-grid losses as well as gains. It does not select
a winner or interpret correlated grid cells as independent trials.

The next recent-history ranking proposal binds this diagnostic, reviewed crop
receipt, saved candidates, scoring pools, labels, and exact six-window scope.
Its SHA-256 is `f9a3ae162d2227ddffab9a9da68811ea629cf7dfa6ffa48625546ac1ab5ad2ca`.
It remains non-executable and awaits specific experiment approval; no selector
support or experiment validation is claimed. No production code changed, so
the prior code-test result remains unchanged. Git staging and other mutations
remain unauthorized; all original embargoes and holdouts are preserved.

## Approved saved crop candidate ranking — implementation validation

Ryan's "I approve chat" authorizes the exact saved-six-window, 45-variant
experiment. A separate approval receipt binds the unchanged proposal; the
new executable specification digest is
`c3541d45fcc4db384d2222a56cd4fe18885c7212ad9f7c77b0e933bdd3eb2fe4`.
This approval does not authorize staging, committing, pushing, PRs, or merging.

Four new modules implement exact five-frame causal ranking, immutable/resumable
execution, separate scoring, and six-panel synchronized review. New synthetic
tests cover exhaustive small-graph agreement, deterministic ties including
empty-score-zero, lower-confidence recovery and stable-clutter failure,
tight/wide motion limits, cap losses, duplicate retention, causal prefixes,
window reset, gaps/expiry without extrapolation, hidden-frame false alarms,
malformed inputs, label-blind loading, immutable inputs, dirty-checkpoint
refusal, exact scope and all nine embargo paths, and tampered provenance.

All 21 focused tests pass in 97.651 seconds. The full suite runs 363 tests in
325.472 seconds: 362 pass, with one existing directory-symlink skip because
Windows symlinks are unavailable. Both commands use
`.venv` Python with `-B`. The synthetic integration reproduces all 540 saved
crop raw/top-one outcome cells across 1,350 reports and two 225-cell pools;
adapter input/below-threshold bookkeeping is the sole parity exclusion.
It creates all 270 outputs, interrupts after seven and resumes only the
remaining 263, verifies exact reuse, and rejects changed derived outputs.
Twelve synthetic review clips fully decode all 25 frames at 5 fps. Their
2,412 assets have complete inventories and hashes, including final frames.
The agent directly inspected the synthetic comparison and unmarked-source
closeups; Ryan's real ranking visual review remains pending execution.

Real-input read-only preflight verifies six windows, 150 source frames,
45 variants, and zero model calls. The real ranking output root remains absent.
The completed crop inference/scoring/rendering were not rerun. No upstream
player, detector, crop, tracklet, or label decision changed. The prior three
context-file edits and historical snapshots remain preserved.

The final `checkpoint_audit.json` binds the exact 15-file scope and successful
test logs, all 59 unchanged protected Git/SHA-256 bindings, six saved detections,
six finalized labels, and frozen proposal/crop/review bindings. It confirms
all nine original embargo paths absent, all three holdouts sealed, an absent
real ranking output root, successful `git diff --check`, Python/JSON parsing,
and refusal to execute before the clean implementation checkpoint.
All generated synthetic outputs, previews, logs, and audits are ignored under
`data/outputs/ball_tracking/crop_ranking_implementation_validation/`.
The index remains empty at branch `codex/ball-detector-baseline`, HEAD
`1a9479f83a1766d8979fad07c604bc686d3c52c6`. No operating point, quality gate,
winner, holdout release, staging, commit, push, PR, or merge was performed.
Next is separately authorized staging/commit of the exact validated 15-file
scope, followed by the already approved real experiment and Ryan's final-frame
review. No unrun manual command or player-pipeline rerun stage is involved.

## Saved crop candidate ranking — committed execution and review package

Ryan separately approved staging the exact validated 15 files and committing
them as `feat(ball-tracking): add approved crop candidate ranking`, each with
"I approve" in response to that specific step. Commit
`3c4894656fd5da11708a54089444d41f0a6f7773` has the expected parent
`1a9479f83a1766d8979fad07c604bc686d3c52c6`, exact file scope and staged blobs,
and a clean worktree/index. Separate ignored staging/commit receipts are under
`data/outputs/ball_tracking/crop_ranking_implementation_validation/`.
Nothing was pushed. The unchanged implementation retains 21 focused passes
and full-suite 362 passes with one existing Windows directory-symlink skip.

Real execution at the clean new commit completed all 270 derived outputs in
51.13 seconds with zero new model calls. It used exactly six saved development
crop files and the approved 45 variants. Scoring completed in 60.65 seconds:
1,350 per-window reports and 225 aggregate cells per separate pool. All 540
saved crop raw/top-one scoring cells reproduce the prior reviewed outcomes;
only adapter input/below-threshold bookkeeping is excluded from parity.

Rendering plus deterministic verification of the new scoring outputs took
251.09 seconds. All 2,412 review assets were hash-verified: 12 videos, 300
comparison PNGs, 1,800 native overlays, and 300 closeups. All 12 originals and
12 separate H.264 playback copies fully decoded 25 frames at 5 fps, including
each window's final frame. Original crop inference/scoring/rendering were not
rerun. No label, detector, tracklet, or upstream player decision changed.

The agent inspected all 12 final-frame closeups, P003 hidden frame 165 at 0.20,
P002 representative 262's regression, and P002 challenge 48's recovery. This
is structural/targeted visual inspection; Ryan's full new clip review remains
pending. The guide links all clips, final evidence, P002 gains/losses, and P003
hidden frames 165-169 and boundaries 164/170/174.

Descriptive findings at 0.20/10 pixels: wide history changes representative
top-one 51 TP/23 FP to 54/19 and challenge 59/13 to 63/6. Tight history has
29/37 representative and 53/13 challenge. At 0.35/10, wide changes 50/19 to
51/17 representative and 55/6 to 58/2 challenge. P002 challenge 48-49 recover
at both settings; P002 representative 262 loses while 258 recovers. Tight
loses many matches, including P003 challenge final 174. Across all 45 grid
cells per pool, wide has 37/3/5 representative gains/ties/losses and 45/0/0
challenge; tight has 0/0/45 in both. Grid cells are correlated and do not
constitute independent trials. No winner, operating point, or gate is selected.

All 74 protected Git/SHA-256 bindings matched through final execution audit;
all nine original embargo paths remain absent, and the three holdouts remain
sealed. The execution evidence is under
`data/outputs/ball_tracking/crop_ranking_execution/3c4894656fd5/`, including
`review_guide.md`, `results_summary.md`, `score_audit.json`, and the final
`execution_record.json` (SHA-256
`95c0b8f92c8af1fde8a842bf7e4bd6993b87880cfbc2a690ae758bf267a14b5d`).
The actual review bundle is
`data/outputs/ball_tracking/crop_candidate_ranking/rfdetr_medium_crop_candidate_ranking_v0_1/review/b7e93ff579f3d8d6069109c069a5a56d/`.

Only after the clean execution audit were these three context files updated
as intentional unstaged notes. The index remains empty; no further Git step
is authorized. No code changed or tests needed repeating. The context diff
receives a whitespace check, with its new hashes saved in an ignored handoff.
Next: Ryan reviews all 12 clips through their final frames. No unrun manual
command or upstream player-pipeline rerun is involved.

## Saved crop candidate ranking — visual-review response recorded

Ryan replied "looks good to me" after being given the 12-clip guide and the
first embedded clip. A separate evidence-bound receipt records package-level
review completion in response to that requested scope. The exact statement
does not enumerate the clips or independently attest each final frame; the
receipt does not invent those details or claim per-frame/quantitative approval.
Receipt creation time is distinguished from the unknown user-message timestamp.

The new receipt is
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_ranking_visual_review_record_v0_1.json`,
SHA-256 `21d896cd6842fc28293f3196ecce3b2e3dc81d6ae65c694a0aaa93fb753054a5`.
It binds the execution commit, approved manifest, scoring reports, review
manifest/guide, all 12 original/playback clips, and final comparison/closeup
images. Older pending-review snapshots remain immutable historical evidence.

Read-only closeout rehashed all 2,412 review assets, 12 playback clips,
270 derived outputs, two pool reports, six crop inputs, six saved detections,
and six finalized labels. All bindings matched. Protected committed blobs
and all 71 non-context protected worktree files remain unchanged. The three
intentional context-file hashes matched the prior handoff before this update.
All nine embargo paths remain absent, and all three holdouts remain sealed.

No selection, inference, scoring, rendering, or code tests were rerun; the
prior 21 focused passes and full-suite 362 passes plus one skip still apply.
The new receipt parses as JSON and the context diff receives a whitespace
check. Branch/HEAD remain `codex/ball-detector-baseline` at `3c4894656fd5`,
with three unstaged context edits, one untracked review receipt, and an empty
index. No staging, commit, push, PR, or merge was performed.

Favorable visual feedback does not remove the recorded numerical losses or
select a method, operating point, quality gate, or new experiment. Next is
read-only analysis of saved misses/path choices before proposing another
design; no holdout access or rerun is needed for that analysis.

## Saved crop ranking — mechanism diagnosis and next design

After "move forward", a create-only diagnostic joined immutable saved scoring
outcomes and endpoint traces. It invoked no detector, selector, scorer or
renderer. All 540 history/window/radius cells partition exactly into no match
at export floor, confidence loss, top-twenty cap loss and additional ranking
loss. The last category also separates wrong current emissions from null
observations. An independent read-only calculation reproduced all counts.

At radius 10/confidence .20, representative tight losses are 5+8+0+33=46;
wide losses are 5+8+0+8=21. Challenge tight losses are 0+7+0+10=17; wide
losses are 0+7+0+0=7. At .35, the respective partitions are 5+11+0+30=46,
5+11+0+8=24, 0+12+0+8=20, and 0+12+0+0=12. There is no cap loss in any
of the 120 .20/.35 history/window/radius cells. Proximity of a low-confidence
exported candidate to a label is not proof of reliable ball identity.

The diagnostic binds its generator and inputs, verifies all 270 derived
outputs and 71 protected non-context files, and records 180 aggregate cells,
600 display frame outcomes and 88 detailed endpoint traces. It is
`data/outputs/ball_tracking/crop_ranking_diagnosis/3c4894656fd5/diagnostic.json`,
SHA-256 `b5fc30f8dd8e5bd4b8a7c1bf98bf9e51108cdd3cc45397dd6a12fe614a84014d`.
The prior three context hashes and review receipt matched before updating
context. All nine embargo paths remain absent and all three holdouts sealed.

Results and case details are in `../ball_crop_candidate_ranking_results.md`.
P002 262 is a wrong-path scoring choice despite available correct continuity;
P002 258 reveals a ninefold motion-cost change without changing that useful
path's admissibility. P003 has both motion-gate exclusions and false singleton
starts while hidden. Stored score margins compare endpoint hypotheses,
including old/empty alternatives, and are not object-level probabilities.

The next concrete design is `../ball_crop_motion_factorial_proposal.md`, bound
by `configs/ball_tracking/proposals/rfdetr_medium_crop_motion_factorial_v0_1.json`
(SHA-256 `66e7c9aae8c66747d62a480d00c256f1e196df3044d5284be501a76a1edd1c64`).
Its independent edge/cost grid adds two combinations while retaining all
existing controls. Counts, mechanism claims and scope received independent
read-only review. No new experiment approval, implementation or execution is
claimed. The new output root remains absent.

No production code changed and no code tests were repeated; the previous 21
focused passes and full-suite 362 passes plus one skip remain applicable.
The proposal's JSON, hashes, exact input/control bindings, counts and whitespace
receive validation. HEAD remains `3c4894656fd5`, the index stays empty, and the
worktree has three intentional context edits plus four untracked scope files.
No staging, commit, push, PR or merge occurred. The final ignored handoff saves
their exact hashes. No upstream decision changed or manual command is unrun.

## Crop motion factorial - approved implementation validation

Ryan approved the exact new comparison with "I approve chat". The separate
receipt is
`configs/ball_tracking/reviews/rfdetr_medium_crop_motion_factorial_approval_v0_1.json`
(SHA-256 `5169aee6b162494bf4650c308728459f499ecd9b280242d6c36a43411e962a5d`).
The new executable manifest is under `configs/ball_tracking/crop_motion_experiments/`;
specification digest excluding authorization is
`51bc58477f5e1273e4ec83588003861f3b095ae46923b46915905ca4600f829f`.
Approved proposal/design bytes remain immutable. No Git step is authorized.

All 23 focused tests pass in 191.201 seconds. The full suite runs 386 tests:
385 pass and one existing Windows directory-symlink test skips in 482.413
seconds. Python bytecode is disabled; hashes for the four source modules and
new test file were recorded before the full run and verified afterward. Logs and synthetic
previews are in `data/outputs/ball_tracking/crop_motion_implementation_validation/`.

Tests cover independent exhaustive path enumeration across all four parameter
pairs, inclusive edge limits, independent unclipped normalization above one,
full legacy control traces, deterministic path/endpoint/empty ties, gaps and
expiry, cap/threshold losses, duplicates, causality and window reset, immutable
inputs, hidden-frame false alarms, label-free selection, dirty-checkpoint
refusal, exact approval/window binding, all nine original embargoes, and
rebound crop-content mismatch/tampered-output refusal.

Synthetic integration creates 378 derived outputs with interrupted-run resume,
1,890 per-window reports and 315 aggregate cells per pool. All 270 saved trace,
1,350 report and 450 aggregate control checks pass. The synthetic review has
3,012 assets: 12 fully decoded 25-frame/5-fps clips plus 3,000 PNGs. The agent
inspected the nine-panel comparison and closeups. Exact unmarked source pixels
are verified separately. Synthetic inspection establishes rendering behavior,
not real ball-tracking quality; Ryan's new review remains pending execution.

Read-only real-input preflight verifies six windows, 150 frames, 63 variants
and zero model calls without invoking ranking or creating real outputs. The
new output root is absent. The final `checkpoint_audit.json` binds the exact
15-file scope, successful logs and preview hashes; it verifies all 71 protected
non-context files, four prior untracked evidence/design files, 270 saved ranking
outputs, two saved pools, six crop/whole-frame inputs and labels, and unchanged
approved documents. JSON/Python parsing, whitespace, empty index and actual
dirty-checkpoint refusal pass. All nine original embargo paths remain absent
and all three holdouts stay sealed. No completed real experiment was rerun.

HEAD remains `3c4894656fd5da11708a54089444d41f0a6f7773` on
`codex/ball-detector-baseline`. Preserve three intentional unstaged context
edits and 12 new scope files. No staging, commit, push, PR or merge occurred.
Next is separate staging approval for the exact validated scope, then separate
commit approval. Existing experiment approval permits the fixed new execution
after that clean checkpoint; do not request it again. No operating point,
quality gate or holdout release is selected, no upstream player decision
changes, and no manual command was supplied but left unrun.
