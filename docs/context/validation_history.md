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

## Crop motion factorial - clean execution and pending visual review

Ryan separately approved staging the validated 15-file scope ("yes you may mr
chat sir") and committing it ("yes you may"). Commit `2274ab6097cd841421e2b606f723b047cd7dc62b`
on `codex/ball-detector-baseline` has the expected parent, title, exact file
scope and blobs. No push, PR or merge occurred. The existing experiment approval
then permitted execution at the clean checkpoint with an empty index.

Selection produced all 378 outputs from six saved crop windows and 63 variants
in 87.632 seconds. Scoring produced 1,890 reports and 315 aggregate cells per
pool in 113.247 seconds. All 270 complete control traces, 1,350 control reports
and 450 aggregate cells reproduce saved evidence exactly. An independent saved
report extraction checked all 1,080 history/window false-negative partitions
and 2,100 displayed arm/frame rows without rerunning selectors or scorers.
There were zero new model calls; completed original crop/ranking runs were not
rerun. The initial local-helper preflight stopped on a stale manifest filename
before creating outputs; correcting that helper required no source change.

Rendering completed in 418.471 seconds with 3,012 hash-verified assets: 12
clips, 300 comparison panels, 2,100 native overlays, 300 unmarked source images
and 300 closeups. All 12 original clips and 12 separate H.264 copies fully decode
25 frames at 5 fps, including each final source frame. Agent image inspection
covers all 12 final closeups and selected mechanism cases. Ryan's review is
pending; agent checks do not assert his approval or a full-clip visual judgment.

Increasing movement allowance at fixed cost scale improves matched-frame counts
in all 45 grid cells in each pool without adding false positives. Gentler cost
with tight allowance loses challenge matches in all 45 cells; with wide allowance
it gains in 37 and ties in eight. These repeated development comparisons are
correlated. All four histories still choose incorrectly at P002 representative
262. P002 challenge 48 exposes a new tight-allowance/gentler-cost loss at .20;
only wide-allowance/gentler-cost matches P003 challenge final 174 at both display
settings. Hidden P003 false alarms remain in every history arm. No winner,
operating point, quality gate or holdout release is selected.

Ignored evidence is under
`data/outputs/ball_tracking/crop_motion_execution/2274ab6097cd/`.
Start with `review_guide.md`. `execution_record.json` SHA-256 is
`1e732738669cb3f6c4389a92248cd1435b376b2fb023a2b02abacda9bb4eb40f`. It binds 86 protected files,
all derived outputs, both scoring pools, the review manifest, playback and
inspection records. All protected inputs and previous controls stayed unchanged;
all nine original embargo paths remain absent and all three holdouts sealed.
The implementation retains its 23 focused passes and full-suite 385 passes plus
one existing Windows directory-symlink skip. No production code changed and tests
were not repeated. Only three intentional context files changed after the clean
execution audit; the index remains empty and whitespace is checked. The final
ignored receipt binds those edits. Next is Ryan's 12-clip final-frame review.

## Crop motion factorial - completed human review and saved-evidence closeout

Ryan said "I have reviewed all of these clips. move forward" in response to
the 12-clip final-frame review package. The separate receipt
`configs/ball_tracking/reviews/rfdetr_medium_crop_motion_factorial_visual_review_record_v0_1.json` has SHA-256
`d629f93d4c4081dd89fcbc98c997fff0f5aea7fe9d8555a16d9328f803d6fd40`. It binds the precise scope and statement
without adding individual-frame verdicts or quality/operating-point decisions.
All 3,012 review assets, 12 playback copies, 378 outputs, two scoring pools,
six crop files, six saved whole-frame detections and six finalized labels were
rehashed. Previous execution/guide snapshots remain unchanged.

The new saved-evidence audit independently reconciles 1,080 loss partitions and
extracts 4,843 emitted winners from all 216 history outputs. It preserves path
support, source-frame span, gaps, boundary flags, candidate coordinates and
confidence, component scores and competing endpoint records, joined to saved
radius-10 outcomes. No matching or abstention policy is recomputed. Its JSON
SHA-256 is `2eb17ff8c26237f3009396a5a54f9646fba187db7409d9e87cfe83c678361c5c`.
Across correlated arm/confidence records there are 313 matched singleton
emissions, 71 unmatched eligible singleton emissions and 19 hidden singleton
false alarms; 1,221 unmatched eligible and 52 hidden emissions already have
at least two supporting nodes. Independent review reproduced these counts,
all eight paired-grid contrasts, all four display table rows and receipt bindings.

The mechanism diagnostic copies 112 saved traces with 38 exact input bindings.
Its SHA-256 is `496a2c6cdfa01d46e43ca7dec052bdffbe0329876cc6d9018618b3acee2b203a`.
All arms at both displays choose a five-node false path at P002 262 despite an
available five-node ball path. P003 hidden .20/168 has two nodes, whereas correct
171 is a singleton in every arm/display. Tight allowance/gentler cost rewards
a distractor at P002 challenge48. These findings bound what support rules can
address. The context feasibility audit inventories reviewed image-space inputs
and existing candidate geometry without changing any emitted observations;
its JSON SHA-256 is `cb06d0804bed5ea5f0ca76685696f87dd12bfe7d0e99157ff7735132c0471a0e`.
It does not infer ball possession or project airborne points onto the court.

Artifacts are under `data/outputs/ball_tracking/crop_motion_closeout/2274ab6097cd/`.
The compact result is `../ball_crop_motion_factorial_results.md`. No selector,
scorer, model or renderer ran; no new prediction or quality gate is produced.
All 83 protected non-context files remain unchanged, all nine original embargo
paths remain absent and all three holdouts stay sealed. HEAD remains
`2274ab6097cd841421e2b606f723b047cd7dc62b` with an empty index. Preserve the three
context edits plus new review receipt/results note. Whitespace, exact scope,
hashes and JSON/Python parsing are checked in `closeout_handoff.json`. The last
production tests remain 23 focused passes and 385 full-suite passes plus one
existing Windows skip; no code change required repeating them. No staging,
commit, push, PR or merge occurred. Next is a bounded candidate-identity design,
with abstention treated separately and no operating point or winner selected.

## Candidate identity diagnosis and proposed soft player context

At unchanged HEAD `2274ab6097cd841421e2b606f723b047cd7dc62b`, the agent inspected all 12
new diagnostic sheets covering 215 distinct already emitted candidates. The
catalog preserves 430 exact native bbox/context crops from 149 saved unmarked
review PNGs; source/crop hashes and decoded crop pixels were verified. Radius-10
scoring labels remain diagnostic outcomes, not semantic object annotations.
No candidate selection, matching, model, completed pipeline or clip render was
rerun. Bright distant seating objects, near-player body/footwear regions and
imprecisely localized genuine balls are distinct observed failure patterns.

The crop audit found that 93/125 matched centers have no alternate crop coverage,
while a hidden false candidate repeats closely across two views. No cross-view,
size, color, border or clustering rule was applied. A create-only context
snapshot preserves all 20 original CSV fields, typed and string-valued, for
exactly 1,353 rows/150 frames/six windows, with all six prior window digests
reproduced. SHA-256: `272c0f14e86420f4b667a0a24d4723914c87efa31fdc0244b1348573a2a441a0`.
No sealed holdout geometry was decoded. Current hashes and metadata alignment
do not create missing historical player video/model provenance.

The proposed comparison JSON SHA-256 is `b41dd0094755de726db6de196c28376cdfc2bceb40b645b1ce91fa56a6be80e7`.
It fixes one bounded coefficient/formula before execution, applies it separately
to each motion control, preserves signed utilities and original confidence,
uses neutral explicit missing context, and reuses all 378 previous outputs and
1,890 reports. Planned new work is 216 outputs/1,080 reports and 12 synchronized
clips, with no detector calls. The exact recurrence, independent synthetic
oracle/parity tests, separate score components, own-frame context and offline
player-provenance limitation are specified. The proposal is not an approved
manifest or completed experiment, and no quality or operating-point decision
is made.

See `../ball_candidate_identity_diagnosis.md`,
`../ball_crop_player_context_proposal.md` and the ignored
`data/outputs/ball_tracking/candidate_identity_diagnosis/2274ab6097cd/` evidence.
Independent reviews checked input hashes, pixel provenance, frozen row digests,
formula/counts, and the proposal's human-review scope. JSON/AST parsing and
`git diff --check` pass. All 83 protected non-context files, prior review/results
bytes and saved controls remain unchanged. Nine embargo outputs remain absent
and three holdouts sealed. The final `diagnosis_handoff.json` binds the eight
unstaged/untracked files; index empty, no Git mutation. Production code/tests
remain at 23 focused and 385 full passes plus one existing Windows skip, without
unnecessary reruns for this saved-data/documentation change.

## Player-context comparison - approval and synthetic implementation validation

Ryan's "I approve chat" approves the unchanged proposal SHA-256
`b41dd0094755de726db6de196c28376cdfc2bceb40b645b1ce91fa56a6be80e7`.
The separate approval receipt SHA-256 is
`6e6f0fa4016c2b187593a11af55e45ef5a0d3f87ad26783af05136d9d80c84c1`;
the new experiment manifest SHA-256 is
`716b397d5ef03b178f8c59565f6c1b41574674a6390cb457dfba258fa3c989c4`.
The experiment specification remains
`7478fe4a3e5a3aaeb328c71b6ed1fe06db42dd3f904af17ca4ed13eb8a294e0d`.
The historical proposal bytes/status remain unchanged. Scope approval does
not authorize Git mutations or select an operating point or quality gate.

Four new modules implement the fixed .25*z/(1+z) cost with signed node utility,
own-frame observed box context and exact prior graph/tie/missingness rules.
All 34 focused tests pass, followed by 419 full-suite passes and one existing
Windows directory-symlink skip. Bytecode writes were disabled. Ninety-six
positive-cost graph cases use an independent exhaustive path/geometry oracle;
zero-cost traces reproduce the old graph across nine confidence thresholds,
four motion settings and seven horizons. Tests cover malformed/missing context,
filter-before-cost, original-confidence ties, negative utility/abstention,
window reset, future independence and annotation exclusion.

Synthetic workflow validation covers resumable creation of 216 new outputs,
exact reuse of 378 prior outputs and 1,890 reports, 1,080 new reports, and 495
aggregates per separate pool. Saved-control execution is disabled during the
new stages. Tests exercise cross-purpose frame alignment, complete provenance,
all nine embargoes, dirty-checkout rejection and changed-input rejection.
The production renderer preparation function is exercised on synthetic saved
outputs/reports with ranking/scoring disabled and a substituted image inventory;
separate renderer tests verify the native PNG bindings.
Twelve synthetic clips decode all 25 frames at 5 fps; their 2,112 new assets and
2,400 reused native references pass hash, final-frame, atomic resume and tamper
checks. Independent review tightened exact source-PNG evidence validation and
the saved alternate-hypothesis legend. Agent inspection of the final synthetic
comparison, closeups and player-box view found readable, aligned layouts; this
does not establish Ryan's real-data visual judgment.

The separate real-input dry run checks the approved six windows/150 frames and
1,353 frozen player rows with every selector/scorer and media decoding disabled.
The saved-native preflight also verifies all 2,400 actual existing source/control
PNG bindings with both image and video decoding disabled. Its separate
`saved_native_input_preflight.json` preserves those exact bindings.
The real execution gate rejects the current dirty checkout. No new real output
root exists. No completed model/crop/ranking/motion experiment was rerun and no
sealed holdout geometry was decoded. Legacy missing player-source/model
provenance and possible offline hindsight remain explicit limitations.

Evidence and actual test logs are under
`data/outputs/ball_tracking/crop_player_context_implementation/2274ab6097cd/`.
`implementation_handoff.json` binds the final exact eighteen-file scope,
test receipts, real-input preflight and v3 synthetic QA images. All 83 protected
existing files and five prior untracked files remain unchanged; nine original
embargo paths stay absent and three holdouts sealed. JSON/AST parsing and
whitespace checks pass. Branch/HEAD remain `codex/ball-detector-baseline` at
`2274ab6097cd841421e2b606f723b047cd7dc62b`; index empty, no Git mutation. The three
intentional context documents are advanced with their prior bytes saved locally.
Next is exact-scope staging approval, then staged verification and separate
commit approval. Already approved real execution waits for that clean tested
commit. No manual command is pending.

## Player-context comparison - clean execution and pending new visual review

Ryan explicitly approved staging the eighteen-file scope ("yes go ahead and
stage"), then committing it ("yes you may"). Commit
`119159817df5414f534f133f0954c1f78c7e51de` has the exact expected title, parent,
scope and blobs. Git metadata required the sandbox's write-permission override;
the authorized actions completed and were verified. No push, PR or merge ran.
The earlier experiment approval then permitted execution at the clean tested
checkpoint. Production code is unchanged from 34 focused passes and 419 full
passes plus one existing Windows directory-symlink skip; tests were not repeated.

Selection created all 216 new outputs in 157.302 seconds. Scoring added
1,080 new reports in 420.797 seconds; all 378 saved outputs, 1,890 reports
and 630 aggregate cells retain their exact bytes/content and prior provenance.
Together the two pools contain 2,970 reports; each has 495 aggregate cells.
Completed detector/crop/ranking/motion stages were disabled by execution guards;
no detector calls or source-video decoding occurred. Frozen PNG inputs remain
confined to the approved six windows. No sealed holdout geometry was decoded.

Independent audits read saved evidence only. The selection audit checks 216
outputs/5,400 frames, 47,198 source candidate records (crop duplicates retained), 222,888 node-cost
and recorded-path records, 684,466 edges and 145,400 endpoint/trailing records.
It replays recorded arithmetic without choosing winners. Every frame has
observed player context. The scoring audit reconciles 2,970 reports, 990
aggregate cells, 1,080 paired differences, 1,080 loss partitions and 360 aggregate
contrasts, with exact saved-control equality and all 594 output bindings checked.

Across the 360 correlated paired aggregate cells, none reduces matched frames
or increases false positives. At the two fixed review settings (.20/.35,
radius 10), representative gains are 6-11 matches per variant and challenge
gains 0-4, with no matched display-frame losses. P002 representative 262 recovers
for all four arms at both displays; P002 challenge 48 recovers for TW at .20.
Hidden false alarms persist at P003 167 (.20) and 168 (both displays). P001
representative final 74 recovers at .20 but remains wrong at .35; P003 challenge
final 174 still matches only for WW. These are development observations, not
independent-trial evidence, a selected winner or a quality/operating-point gate.

Rendering finished in 414.968 seconds. The 2,112 new assets (2,100 PNGs,
12 clips) and 2,400 reused native/source PNG references are hash verified.
All 12 originals and 12 separate H.264 copies fully decode 25 frames at 5 fps,
including their final source frames. Independent helper review tightened
per-clip sidecar identity/destination checks before playback preparation.
Agent image inspection covers all 12 final closeups and targeted real panels;
Ryan's new visual review remains pending. Existing crop/ranking/motion approvals
do not assert review of this new package.

Evidence is under
`data/outputs/ball_tracking/crop_player_context_execution/119159817df5/`.
Start with `review_guide.md`; `results_summary.md` contains the exact tables.
`execution_record.json` SHA-256 is
`300eecaecc8b99c2e44d765ec1757a10f9431a1f2e1c2766ccfddcd86b3c1615`. It binds the stages,
new/reused output inventories, score/selection audits, review manifest, playback,
inspection and 101 protected files at the clean execution checkpoint.
Only the three context documents were advanced afterward, with their original
bytes retained locally and final hashes in `post_execution_context.json`.
Whitespace passes, index empty, nine original embargo paths absent, and three
holdouts sealed. No upstream reviewed player decision changed. No manual
command is pending. Next is Ryan's review of all twelve new clips through their
final frames; completed stages must not be rerun.

## Player-context visual review complete and saved-results closeout

Ryan answered "Yes, reviewed all 12; proceed" to the explicit question about
watching all twelve new player-context clips through their final frames.
The separate review receipt SHA-256 is `0ebaabad929558d9c07339161f0d37362d6da9477883853146345cc56a848ef6`.
All 2,112 new assets, 2,400 reused PNG references, twelve playback copies,
216 new outputs, 378 controls and 98 protected non-context files were rehashed.
An independent read-only check verified all 73 receipt file bindings and exact
agreement of its twelve clip entries with the playback manifest. Historical
pending-review evidence was preserved; no itemized human verdict was invented.

The new saved-evidence diagnosis reconciles all 1,080 per-window comparisons
and loss partitions. Compared with each matching motion control, there are
no newly lost matches, added false-positive frames or worse center errors on
shared matches. It separately preserves residual failures against top one and
all exported candidates. At radius 10 the .01 exported pool covers 140/145
eligible frames; .20/.35 still have confidence and path-selection losses.
The hidden P003 167/168 cases retain zero context cost. No selector, scorer,
renderer, model, source-video decoder or holdout geometry reader ran.

The numerical artifact `residual_diagnosis.json` has SHA-256
`3f2744d8c88c26abd2595384ac83147b623e35a204dbd4aded1704c92ad569e8`.
The closeout document is `docs/ball_crop_player_context_results.md`.
All settings reuse the same six windows and do not establish generalization.

Primary-source research supports preparing one bounded YOLO11x Detect
challenger; the concrete proposal JSON SHA-256 is `f891c04464422428dadbcfdf425436d3347464dbcab6d96ae23cac963dca5492`.
It binds 150 unmarked source PNGs, all 162 reused simple-selector outputs,
two saved scoring pools (405 selected report cells each), labels and protected
embargo/holdout scope. Published checkpoint digest and package version are
pinned; local artifact verification and isolated runtime validation are future
preconditions. No package or model was downloaded, installed, loaded or run.
The design explicitly retains preprocessing/NMS/candidate-budget differences,
uncalibrated model confidences and unverified exact training overlap. It is
not an execution permit and requires separate exact-scope experiment approval.

Only evidence/design/context files changed; production code and prior evidence
are unchanged. The latest 34 focused and 419 full-suite passes plus one existing
Windows skip remain applicable; no redundant tests were run. Index empty,
nine original prediction paths absent, three holdouts sealed, no selected
method/point/gate and no Git mutation. Previous context bytes and final binding
inventory are preserved under
`data/outputs/ball_tracking/crop_player_context_closeout/119159817df5/`.
No manual command is pending. Next is the exact new proposal review, not a
repeat of Ryan's completed clip inspection.

## Approved YOLO11x implementation and synthetic validation

Ryan's exact approval is bound by the new approval receipt and executable
manifest. The design JSON remains SHA-256
`f891c04464422428dadbcfdf425436d3347464dbcab6d96ae23cac963dca5492`.
The isolated Ultralytics 8.4.171 environment records exact package/wheel/file
inventories and verified publisher weights. Baseline package metadata remains
unchanged. The runtime receipt SHA-256 is
`bd549dff7c4d7810b3154c9a5442cf43516e15bd5c72ab6abe631f819652e7ba`.

Actual synthetic GPU tests passed color conversion, 640-square letterbox with
140-pixel vertical pads, normalization, inverse boxes and FP32 device 0 checks.
Each fresh predictor performed two synthetic startup forwards and one further
ordinary-route forward on a constant synthetic image. No project pixels were
used. SDK deepcopy and canonical precision handling were checked against the
installed version. Offline configuration remains inside the ignored runtime.

All 41 focused tests pass, followed by 460 full-suite passes and
1 existing Windows directory-symlink skip. Focused tests cover all 600
synthetic crop units, retry/preparation accounting, 162 new outputs, 810 new plus
810 unchanged saved reports, 270 aggregate cells per pool and twelve 25-frame
synthetic clips with 1,512 new assets and 1,200 reused references. Independent
review caught and fixed wrong-prefix acceptance and a PNG hash/decode race.
Root and renderer agent inspected synthetic comparison/native/closeup layouts.
The first combined test invocation failed on flat fixture imports; the normal
repository discovery command passed. Failed and passing logs are preserved.

Read-only actual preflight verified 150 PNGs/600 planned crop units without
constructing a model. The dirty-tree gate was separately verified before
runtime access. No new real inference, scoring or rendering has occurred;
the approved challenger output root remains absent. All 98 protected files,
four preceding design/review files and old local evidence bindings are intact.
No old pipeline or source-video decoding occurred. Embargoes and holdouts
remain protected, with no operating point, method or quality gate selected.

The final implementation checkpoint and before-context backups are under
`data/outputs/ball_tracking/yolo11x_implementation/119159817df5/`.
Git branch/HEAD are unchanged and the index is empty. Exact next step is
separate staging authorization for the nineteen-file scope documented in
`docs/ball_yolo11x_crop_implementation.md`, followed by separate commit approval.
