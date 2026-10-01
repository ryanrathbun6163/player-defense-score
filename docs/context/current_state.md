# Current State

## Latest checkpoint: approved motion-factorial implementation validated

Ryan approved the exact factorial comparison with "I approve chat". The new
receipt is
`configs/ball_tracking/reviews/rfdetr_medium_crop_motion_factorial_approval_v0_1.json`
(SHA-256 `5169aee6b162494bf4650c308728459f499ecd9b280242d6c36a43411e962a5d`).
The executable manifest is
`configs/ball_tracking/crop_motion_experiments/rfdetr_medium_crop_motion_factorial_v0_1.json`;
specification digest excluding authorization:
`51bc58477f5e1273e4ec83588003861f3b095ae46923b46915905ca4600f829f`.
The approved design/proposal bytes and original historical status are unchanged.
Do not request this experiment approval again. Git steps remain separate.

Four new `src/ball_tracking/crop_motion*.py` modules implement independent
edge allowance and cost normalization, guarded resumable selection, strict
saved-control scoring, and a nine-panel review. Original crop/ranking/detector
and player code is unchanged. The implementation and exact proposed 15-file
scope are in `docs/ball_crop_motion_factorial_implementation.md`.

All 23 focused tests pass in 191.201 seconds. Synthetic integration covers
378 outputs, 1,890 reports, two 315-cell pools, 270 complete control traces,
1,350 control report cells and 450 aggregate parity checks. All 12 synthetic
review clips decode all 25 frames at 5 fps; 3,000 supporting PNGs preserve
native overlays, exact unmarked source and source-scale closeups. The agent
inspected the synthetic layout. The full suite runs 386 tests: 385 pass and
one existing Windows directory-symlink test skips (482.413 seconds).
Source/test hashes remained unchanged throughout the run; bytecode was disabled.

Ignored evidence is under
`data/outputs/ball_tracking/crop_motion_implementation_validation/`.
The actual-input read-only preflight confirms six windows, 150 source frames,
63 variants and zero model calls. `checkpoint_audit.json` binds the exact
15-file scope and successful logs, preserved prior hashes and committed
blobs, all saved controls, JSON/Python parsing, whitespace and actual
dirty-checkpoint execution refusal. The new real output root is absent. No
completed experiment was rerun, no operating point/gate is selected, and all
nine original embargoes and three sealed holdouts remain intact.

Branch/HEAD remain `codex/ball-detector-baseline` at
`3c4894656fd5da11708a54089444d41f0a6f7773`. The index is empty; preserve the
three intentional context edits and 12 new scope files. No staging, commit,
push, PR or merge is authorized or performed. Next is separate authorization
to stage the exact validated 15-file scope, then separate commit authorization.
The already approved experiment
may execute only after that clean implementation checkpoint. No upstream player
decision changed and no manual command was supplied but left unrun.

## Previous checkpoint: saved ranking diagnosis and motion-factorial proposal

After Ryan said "move forward", the saved remaining misses were diagnosed
without invoking a selector, scorer, renderer or detector. The results are in
`docs/ball_crop_candidate_ranking_results.md`. All 540 history/window/radius
loss partitions reconcile exactly with saved false-negative counts. At
confidence .20/.35 there is no top-twenty cap loss across either pool or any
radius. Wide history's eight additional representative misses at each display
are wrong current choices; challenge has no additional ranking misses at those
settings. Low-confidence candidate proximity is not established ball identity.

The saved paths distinguish mechanisms: P002 representative 262 has an intact
correct path but accumulated false evidence wins. At representative 258, the
same useful path is admissible under both motion limits, yet wide normalization
charges nine times less motion cost. Other useful edges are actually excluded
by the tight gate, including P003's final challenge observation. Hidden P003
false alarms at 167/168 arise from fresh starts, not gap interpolation.

The concrete next proposal is `docs/ball_crop_motion_factorial_proposal.md`
and `configs/ball_tracking/proposals/rfdetr_medium_crop_motion_factorial_v0_1.json`
(SHA-256 `66e7c9aae8c66747d62a480d00c256f1e196df3044d5284be501a76a1edd1c64`).
It crosses edge limits .01/.03 with independent motion-cost scales .01/.03,
retains both old settings and three crop controls, and keeps all other rules
fixed. Proposed scope: 63 variants, 378 window outputs, 1,890 reports, 315
aggregate cells per pool, 1,350 existing-arm report parity checks and 270 full
control-trace checks, plus 12 review clips. It uses only saved candidates and
requires zero detector calls. It is not executable or authorized; the earlier
45-variant approval does not include these new combinations. No operating
point, method, quality gate or holdout release is selected.

Ignored evidence is under
`data/outputs/ball_tracking/crop_ranking_diagnosis/3c4894656fd5/`.
`diagnostic.json` (SHA-256
`b5fc30f8dd8e5bd4b8a7c1bf98bf9e51108cdd3cc45397dd6a12fe614a84014d`)
binds its generator/inputs and holds 540 partitions, 180 aggregate cells,
600 display frame records and 88 detailed endpoint traces. All 270 derived
output hashes and 71 non-context protected files matched; the previous three
context hashes and review receipt matched before this update. All nine original
embargo paths remain absent and all three holdouts sealed. No completed
experiment was rerun. No production code changed, so code tests were not
repeated; the last result is 21 focused passes and 362 full-suite passes with
one existing Windows skip. Independent read-only review checked the mechanism
claims, partition counts and new design.

Branch/HEAD remain `codex/ball-detector-baseline` at
`3c4894656fd5da11708a54089444d41f0a6f7773`, with an empty index. Preserve the
three intentional unstaged context edits and four untracked files: the ranking
visual-review receipt, ranking results note, factorial design and proposal JSON.
No new staging, commit, push, PR or merge occurred or is authorized. The final
context handoff binds these seven files and the successful whitespace/JSON/hash
checks. No upstream player decision changed or manual command remains unrun.
Next: obtain approval of the exact new experiment scope, then implement and
validate it synthetically before any separately authorized Git steps or real
execution. The current new output root is absent.

## Previous checkpoint: ranking visual-review response recorded

Ryan responded "looks good to me" after the linked 12-clip ranking review
package and first embedded clip. The separate receipt
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_ranking_visual_review_record_v0_1.json`
(SHA-256 `21d896cd6842fc28293f3196ecce3b2e3dc81d6ae65c694a0aaa93fb753054a5`)
binds the exact response to execution commit
`3c4894656fd5da11708a54089444d41f0a6f7773`, the manifest/approval, both scoring
pools, all 12 original/playback clips, and final panels/closeups.

This records package-level review completion in response to the requested
12-clip scope. Ryan's statement does not itemize clips or independently attest
every final frame; no extra frame-level or quantitative correctness claim is
added. The receipt timestamp is creation time, not an invented message time.
Earlier execution, guide, manifest, and handoff snapshots retain their
historical pending-review status. No completed stage was rerun.

Read-only verification rehashed all 2,412 review assets, 12 playback clips,
270 derived outputs, both scoring pools, six crop inputs, six saved detections,
and six finalized labels. All bindings matched. All nine original prediction
embargoes remain intact and all three holdouts stay sealed.

The numerical findings remain unchanged: wider links improve challenge
matches across the grid, but lose P002 representative 262 and have five
representative grid cells with fewer matches than crop top one. Tight links
lose many valid matches. Positive visual feedback does not select a winner,
operating point, quality gate, or authorize a new experiment or Git step.

Branch/HEAD remain `codex/ball-detector-baseline` at `3c4894656fd5`; the index
is empty. Preserve the three intentional unstaged context edits and new
untracked receipt. No production code changed; tests were not repeated, and
the diff received a whitespace check. Next is a read-only diagnosis of saved
remaining misses and path choices, separating missing usable candidates from
ranking losses, before proposing any new experiment. P002 representative 262
and P003 hidden frames 165-169 remain useful cases. No upstream player
decision changed and no manual command was supplied but left unrun.

## Previous checkpoint: crop candidate ranking executed; visual review pending

Branch is `codex/ball-detector-baseline` at
`3c4894656fd5da11708a54089444d41f0a6f7773`
(`feat(ball-tracking): add approved crop candidate ranking`), parent
`1a9479f83a1766d8979fad07c604bc686d3c52c6`. Ryan separately approved the exact
15-file staging scope and then the proposed commit with "I approve". The commit
parent, scope, and all file blobs were verified. Nothing was pushed.

The already approved ranking experiment then ran at that clean checkpoint:
270 derived outputs from the six saved development crop files, 1,350 per-window
scoring reports, and 225 aggregate cells in each separate pool. All 540 crop
raw/top-one control cells reproduce saved reviewed outcomes. There were zero
new detector calls. The completed original crop experiment was not rerun.

All 2,412 new review assets were hash-verified: 12 clips and 2,400 PNGs. Every
original clip and separate H.264 playback copy decoded all 25 frames at 5 fps.
The agent inspected all 12 final-frame closeups, P003 hidden frame 165's six
panels at 0.20, P002 representative regression frame 262, and P002 challenge
recovery frame 48. Ryan's review of the new 12 clips is pending; his previous
crop and temporal reviews remain complete.

Start with the ignored guide:
`data/outputs/ball_tracking/crop_ranking_execution/3c4894656fd5/review_guide.md`.
It links every playback clip, final panels/closeups, and exact gain/loss frames.
The same directory holds `results_summary.md`, `score_audit.json`, stage logs,
playback verification, and `execution_record.json` (SHA-256
`95c0b8f92c8af1fde8a842bf7e4bd6993b87880cfbc2a690ae758bf267a14b5d`).
The review bundle is
`data/outputs/ball_tracking/crop_candidate_ranking/rfdetr_medium_crop_candidate_ranking_v0_1/review/b7e93ff579f3d8d6069109c069a5a56d/`.

At confidence 0.20 and radius 10, representative crop top one has 51 TP/23 FP;
wide history has 54 TP/19 FP, while tight history has 29 TP/37 FP. Challenge
top one has 59 TP/13 FP; wide has 63 TP/6 FP and tight 53 TP/13 FP. At 0.35,
wide has 51 TP/17 FP versus top one's 50/19 representative, and 58/2 versus
55/6 challenge. Wider links recover P002 challenge 48-49 at both displays but
lose P002 representative 262 while recovering 258. Tight links lose many
previous matches, including P003 challenge final 174. At all 45 grid cells,
wide improves challenge match counts; representative counts improve in 37,
tie in three, and worsen in five. Tight has fewer matches in all 45 cells of
both pools. These are correlated descriptive comparisons, not independent
trials or a selected method, operating point, or quality gate.

Selection took 51.13 seconds, scoring 60.65 seconds, and rendering with its
deterministic new-score verification 251.09 seconds. All 74 protected file
bindings matched through the final clean execution audit. All nine original
prediction embargo paths remain absent and all three holdouts sealed.

These three context files were updated only after execution and verification;
they are intentional unstaged changes, and the index is empty. Preserve them.
No production code changed after the 21 focused passes and full-suite 362
passes plus one existing skip. The context update receives `git diff --check`.
Next is Ryan's visual inspection of all 12 new ranking clips through their
final frames. Do not rerun completed stages or select an operating point/gate.
No new staging, commit, push, PR, or merge is authorized. No upstream player
decision changed, and no manual command was supplied but left unrun.

## Previous checkpoint: approved crop candidate-ranking implementation

Ryan approved the bound saved-candidate experiment with "I approve chat".
The separate receipt is
`configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_ranking_approval_v0_1.json`.
The executable manifest is
`configs/ball_tracking/crop_ranking_experiments/rfdetr_medium_crop_candidate_ranking_v0_1.json`;
specification digest, excluding its authorization binding:
`c3541d45fcc4db384d2222a56cd4fe18885c7212ad9f7c77b0e933bdd3eb2fe4`.
The original proposal/design retain their historical status and bound bytes.

Four separate modules implement causal selection, guarded/resumable execution,
unchanged matching with saved-control parity and loss decomposition, and
six-panel synchronized review. Exact behavior and the proposed 15-file Git
scope are in `docs/ball_crop_candidate_ranking_implementation.md`. Existing
detector, crop, tracklet, player-pipeline, and reviewed label files are unchanged.

All 21 focused tests pass with `.venv` Python and bytecode disabled. The full
suite runs 363 tests: 362 pass and one existing Windows symlink test skips.
Synthetic integration covers 270 derived outputs with partial resume,
1,350 scoring reports, two separate 225-cell pools, all 540 saved crop control
outcome cells, and 12 fully decoded 25-frame/5-fps clips plus 2,400 PNGs.
The agent inspected synthetic comparison/closeup layouts; this does not approve
real ranking quality. No user source video or model is opened by the synthetic
ranking tests. Real-input read-only preflight verifies the six bound windows,
150 frames, 45 variants, and zero new model calls.

Branch/HEAD remain `codex/ball-detector-baseline` at
`1a9479f83a1766d8979fad07c604bc686d3c52c6`. Exactly three tracked context files
are modified; 12 new scope files are untracked. The index is empty. Prior
intentional context notes remain preserved. The real ranking output root is
absent; the completed crop inference/scoring/rendering were not rerun.
All nine original prediction embargoes and all three sealed holdouts remain.
No operating point or quality gate is selected.

Next: request separate authorization to stage the exact validated 15-file
scope, then separately commit it. The already approved ranking experiment can
execute after that clean implementation checkpoint; no new experiment approval
is needed for its fixed scope. Staging, committing, pushing, PR creation, and
merging remain separate, currently unauthorized actions. Ryan's review of the
12 real ranking clips is pending execution. No upstream player decision or
player-pipeline `--rerun-from` change is involved. No manual command was supplied
but left unrun. Ignored validation evidence is under
`data/outputs/ball_tracking/crop_ranking_implementation_validation/`.
The final `checkpoint_audit.json` binds the exact scope and successful logs,
verifies all 59 protected Git/SHA-256 bindings, six saved detections, six labels,
frozen crop/proposal/review evidence, all nine absent embargo paths and three
holdouts, source/JSON parsing, whitespace, and the dirty-execution refusal.

## Previous checkpoint: saved crop closeout and candidate-ranking design

After completed visual review, Ryan said "lets move forward chat". The next
design is now concrete in `docs/ball_crop_candidate_ranking_proposal.md` and
`configs/ball_tracking/proposals/rfdetr_medium_crop_candidate_ranking_v0_1.json`
(SHA-256 `f9a3ae162d2227ddffab9a9da68811ea629cf7dfa6ffa48625546ac1ab5ad2ca`).
This is a non-executable proposal awaiting exact experiment-scope approval.
No new selection, inference, scoring, or rendering experiment has run.

A new create-only saved-result diagnostic extracts all 180 same-cell aggregate
comparisons and the displayed per-window outcomes, without rescoring. It also
counts label-blind cross-crop box overlaps. The diagnostic is
`data/outputs/ball_tracking/tiled_closeout/1a9479f83a17/diagnostic.json`, SHA-256
`87a2e57e147da2907d42286bc6d81d333c011eb5609ba3f71c09291265c0cc3d`.
Its generator and inputs are bound; displayed frame counts/decompositions were
checked. The results note is `docs/ball_detector_tiled_comparison_results.md`.

At confidence 0.20/radius 10, crop raw has qualifying matches in 62/75
representative and 63/70 challenge frames, while top one retains 51 and 59.
Removing lower-ranked duplicates cannot change the highest-confidence guess.
The proposed next experiment therefore ranks original candidates using a
five-frame causal history, with raw/top-one/top-twenty controls and two motion
limits. It uses saved crop inputs only, preserves explicit missing output,
and does not smooth or invent ball coordinates. Its fixed scope is 45 variants,
270 derived outputs, 1,350 per-window reports, two separate 225-cell pools,
and 12 review clips. No operating point or quality gate is selected.

Branch and HEAD remain `codex/ball-detector-baseline` at
`1a9479f83a1766d8979fad07c604bc686d3c52c6`. Preserve the three existing context
edits, completed crop review receipt, new results/design notes, and proposal
JSON. The index is empty; no staging, commit, push, PR, or merge is authorized.
All nine original embargo paths remain absent; all three holdouts stay sealed.
No production code changed, so focused/full tests were not repeated. Next is
approval of the concrete new experiment, then synthetic-first implementation
and validation before any separately authorized Git steps and real execution.
No upstream player decision changes or unrun manual commands are involved.

## Previous checkpoint: crop comparison visually reviewed

Ryan completed the requested 12-clip crop comparison review and stated:
"all of them look pretty good to me. even P002 challenge". The separate receipt
`configs/ball_tracking/reviews/rfdetr_medium_tiled_development_comparison_visual_review_record_v0_1.json`
binds his exact feedback to execution commit
`1a9479f83a1766d8979fad07c604bc686d3c52c6`, both scoring pools, the review
manifest, all 12 original/playback clips, and their final-frame closeups.
Receipt SHA-256:
`6e108189b792d505c97adbcfcce5aa635a6e140893a6306e0c08bfe910218adb`.
The timestamp is receipt creation time, not an invented message event time.
Earlier pending-review records and notes remain historical snapshots.

Read-only closeout rehashed all 1,962 bound review assets, all 12 playback
clips and final closeups, two scoring-pool reports, six crop candidate files,
and six saved whole-frame detection files. All bindings matched. The three
intentional context edits matched the handoff hashes before this update.
All nine original embargo paths remain absent; all three holdouts stay sealed.
No inference, scoring, rendering, or test suite was rerun, and no production
code changed. The previous 18 focused passes and full-suite 341 passes plus
one existing skip remain the last code validation.

Branch and HEAD remain unchanged; the index is empty. This review adds one
unstaged receipt and updates the existing three context files while preserving
their prior notes. Nothing was staged, committed, pushed, or submitted as a PR.
No operating point, quality gate, winner, or next experiment is approved.
Ryan's favorable visual assessment does not remove the numerical regressions:
crops recover more matches overall but add false guesses; P002 challenge
frames 48-49 still lose top-one matches at both displayed settings.

Next: summarize the saved gains/losses and prepare a concrete next experiment
design before seeking its separate scope authorization. Do not repeat the
completed crop review or rerun the experiment. No upstream player decision
changed, and no player-pipeline `--rerun-from` action is needed. No manual
command was supplied but left unrun.

## Previous checkpoint: crop comparison executed; visual review pending

Branch is `codex/ball-detector-baseline` at
`1a9479f83a1766d8979fad07c604bc686d3c52c6` (`feat(ball-tracking): add approved
fixed-crop detector comparison`). Ryan separately authorized staging with
"yes stage" and committing with "commit please". The exact 15 validated files
were committed, their Git blobs and parent verified, and the worktree was clean
through inference, scoring, rendering, playback verification, and final audit.
Nothing was pushed. The three context files are the only subsequent uncommitted
changes; the index is empty. Preserve these execution notes.

The already approved fixed-crop experiment is now complete at that checkpoint:
600 new model calls on exactly 150 frames in the six development windows,
600 immutable view checkpoints, six candidate files, 1,080 per-window scoring
reports, and 180 aggregate cells in each separate representative/challenge pool.
All 540 saved whole-frame raw/top-one control cells reproduce the prior reviewed
scoring outcomes and per-frame results. Adapter-stage input/below-threshold
counts are excluded from that parity claim. All 59 protected files, six saved
detection files, and six reviewed annotation bindings remain unchanged.

All 1,962 review assets were hash-verified: 12 videos and 1,950 images. Every
original video and separate H.264 playback copy fully decoded through all
25 frames. The agent directly inspected all 12 final-frame closeups, P003
hidden frame 165's four-panel image at 0.20, and P001 frame 74's crop context.
This is not all-frame visual approval. Ryan's review of the new crop evidence
is pending; his earlier temporal inspection remains complete.

At both predeclared display confidences and the raw 10-pixel radius, cropped
inputs improve pooled match counts but add false guesses. For top-one at 0.20,
representative matches rise from 44 to 51 of 75 eligible frames and false
guesses from 20 to 23; challenge matches rise from 46 to 59 of 70 and false
guesses from 10 to 13. At 0.35, the corresponding match counts are 39 to 50
and 41 to 55, with false guesses 5 to 19 and 4 to 6. These are descriptive
comparisons, not selected settings. P002 challenge frames 48-49 lose top-one
matches at both settings; P002 representative frames 258-259 and P001 challenge
frame 219 also regress at 0.20. Review the losses as well as the gains.

New generated evidence is ignored under
`data/outputs/ball_tracking/tiled_development/rfdetr_medium_tiled_development_comparison_v0_1/`.
The verified review bundle is `review/a007aa4b358587789f7ef1f28b1c66b5/`.
The execution handoff is
`data/outputs/ball_tracking/tiled_execution/1a9479f83a17/review_guide.md`,
with links to all 12 playback clips and final closeups. The same directory has
`results_summary.md`, `score_audit.json`, command logs, and `execution_record.json`
(SHA-256 `4d7977be4e08c9e70df438a007cbe92de4be60bed14eccc4d75a581aff137b52`).
Inference took 136.28 seconds end to end; synchronized model calls totalled
96.02 seconds, including first-call initialization. Median four-crop frame
time was 0.532 seconds. No measured runtime ratio to the saved control exists.

The last execution command completed the final record and preservation audit;
the subsequent context-only handoff received `git diff --check`. No new code
changed after the validated 18 focused tests and 341 full-suite passes plus
one existing skip, so those tests were not repeated. No manual command was
provided but left unrun. The exact next action is for Ryan to watch all 12 new
crop-comparison clips through their final frames and report visual findings.
Do not repeat experiment authorization or the earlier temporal review.
All nine original prediction paths remain absent, all three holdouts remain
sealed, and operating-point and quality-gate fields remain null. No upstream
reviewed player decision changed; no player-pipeline rerun is needed.

## Previous checkpoint: approved crop comparison validated; staging approval pending

Branch remains `codex/ball-detector-baseline` at
`6769e07476da09d858fa42f82aace024d21f7735`. Preserve the intentionally dirty
worktree. Ryan approved the concrete crop comparison with "yes i approve".
The receipt is
`configs/ball_tracking/reviews/rfdetr_medium_tiled_development_comparison_approval_v0_1.json`;
it binds the unchanged proposal (SHA-256
`2732e69b19e746b96af7d76e214b08281b5a8f4a58b8f28b494890973f846535`)
and executable specification
`3384a930d8633b202b689857de2bea4939277a2d2f0c3da483c2c48e9e9ef023`.
Do not ask for this experiment approval or the completed temporal review again.

Four separate `tiled_*.py` modules implement crop-local/global candidate
provenance, fixed-window inference with immutable per-crop resume, separate
scoring, and four-panel review rendering. They reuse the frozen per-call
detector without editing its contract, source, tests, saved predictions, or
labels. The new manifest is outside the old experiment registry:
`configs/ball_tracking/tiled_experiments/rfdetr_medium_tiled_development_comparison_v0_1.json`.
The implementation note documents the exact 15-file staging scope:
`docs/ball_detector_tiled_comparison_implementation.md`.

Final focused validation passed all 18 tests in 74.915 seconds. Synthetic
integration exercised 600 model calls, exact and partial resume, 1,080 report
cells, saved-control scoring parity, separate pools, 12 complete review videos,
1,950 review images, and tamper rejection. The agent inspected the synthetic
comparison and closeup previews. Real-input dry-run passed source, frozen
package/weight, and RTX 5070 CUDA checks; it made no predictions. All commands
used the repository `.venv` with bytecode disabled. The final full suite ran
342 tests in 223.084 seconds: 341 passed, one existing directory-symlink
capability skip. `git diff --check`, new-file syntax/whitespace checks, and
exact 15-file scope verification passed. All 59 prior protected files and six
saved detection/label bindings remain unchanged.

Generated validation logs and synthetic previews stay ignored under
`data/outputs/ball_tracking/tiled_implementation_validation/`: `focused_final.log`,
`full_suite_final.log`, `preflight.log`, synthetic PNGs, and
`validation_record.json` with file hashes and proposed Git blobs. The last
completed work is the final validation and input/scope audit. Real crop outputs
remain absent. The next boundary is separately
authorized staging of the exact 15 files, then separate commit authorization.
The approved runner requires a clean committed checkpoint for real inference;
run inference, scoring, and rendering at that same commit before updating
context. The real execution commands are documented for the future checkpoint
and have not run. No manual command was left for Ryan to execute.

The index is empty; nothing staged, committed, or pushed. The earlier temporal
closeout files are preserved in this implementation scope. All nine original
embargo paths remain absent, all three holdouts remain sealed, and no operating
point or quality gate is selected. This changes no upstream reviewed player
decision and needs no player-pipeline `--rerun-from` stage.

## Previous checkpoint: temporal evidence inspected; crop comparison proposed

Branch `codex/ball-detector-baseline` remains at
`6769e07476da09d858fa42f82aace024d21f7735`. Ryan responded
"inspected. please move forward" to the 12-clip temporal review package.
The new receipt records inspection completion with that exact statement:
`configs/ball_tracking/reviews/rfdetr_medium_temporal_association_visual_review_record_v0_1.json`,
SHA-256 `c90aab1535c359e50069fbff5149d26040fd1bc9d1696a1009edf89993cf63a7`.
Its timestamp is receipt creation time. Earlier runtime records remain
unchanged as historical pending-review snapshots; do not request this review
again or equate its completion with selecting a quality gate.

All 2,412 review assets, 12 playback clips, 324 observation files, two scoring
grids, six labels and raw files, and 59 protected file bindings were reverified.
The read-only closeout compared all 360 tracklet aggregate cells with top-one
at identical confidence/radius settings. Some settings gain correct matches,
but all such gains also increase false guesses. At the two predeclared display
settings, every tracklet variant loses correct matches in both pools.

Candidate availability is also limiting: at the 0.01 export floor and 10-pixel
radius, P001 has qualifying candidates in 10/25 representative and 18/25
challenge frames. These are label-assisted availability counts, not a selected
operating point. The new results note separates detector/threshold misses from
additional association losses without relaxing the scoring radius:
`docs/ball_temporal_association_results.md`.
The ignored diagnostic contains every same-cell comparison and all 270 raw
miss decompositions, with exact frame IDs and a bound generating script:
`data/outputs/ball_tracking/temporal_closeout/6769e07476da/diagnostic.json`
(SHA-256 `845dc1d7e7ead0ec952c27985595878c3e13488af54c1dc1f946ae207d6cce77`).

The next proposed experiment gives the same detector more image detail using
four fixed overlapping crops on each of these same 150 frames: 600 new model
calls, no training or new weights, no window expansion. Its concrete design is
`docs/ball_detector_tiled_comparison_proposal.md`; its non-executable scope is
`configs/ball_tracking/proposals/rfdetr_medium_tiled_development_comparison_v0_1.json`.
The existing temporal permit covers only saved detections. The next boundary
is approval of this new prediction experiment, followed by implementation and
validation before separate Git steps and real execution. No manual command
was supplied but left unrun.

This turn changes review/configuration/documentation only. Production code and
the original approved temporal design/manifest remain unchanged. Existing
uncommitted progress was preserved; the index is empty. The seven-file worktree
scope is the three context documents, the new review receipt, results note,
crop proposal document, and crop proposal JSON. Nothing staged, committed, or
pushed. No operating point, quality gate, or model winner selected; all nine
old embargo output paths remain absent and all three holdouts remain sealed.

## Previous checkpoint: temporal execution awaiting visual review

Verified 2026-09-19 UTC (2026-09-18 America/Phoenix). Branch remains
`codex/ball-detector-baseline`, now at
`6769e07476da09d858fa42f82aace024d21f7735`:
`feat(ball-tracking): add approved temporal association experiment`.
Ryan separately authorized staging with "yes go ahead" and committing with
"yes commit". Exactly the validated 13-file scope was committed, with parent
`84bcc8da143e54ff17a28b39db0e70c4b8b299c8`; the resulting worktree was clean.
Nothing was pushed. This later progress note is intentionally uncommitted;
the index remains empty.

Ryan responded "lets move forward" to the linked temporal-association design.
This authorizes its six-window experiment; the exact statement, design hash,
and concrete specification hash are in
`configs/ball_tracking/reviews/rfdetr_medium_temporal_association_approval_v0_1.json`.
Do not request that experiment approval again. The new manifest is
`configs/ball_tracking/temporal_experiments/rfdetr_medium_temporal_association_v0_1.json`;
its specification SHA-256 is
`ef2f7a2a77f334c94d0efc045311c6fd4a3cc86695aec84934bacbfb06605ab5`.
It binds all six saved development outputs and the completed visual review.

The real dry-run, association, scoring, and rendering all completed at that
clean commit using the repository `.venv`. Association reused the six saved
development detection files: no new detector inference ran. All 54 declared
variants produced 324 observation files across 150 frames. Scoring produced
1,620 per-window reports and 270 aggregate cells per separate representative
and challenge pool. All 270 raw-control reports reproduce the prior detector
metrics and per-frame outcomes (the derived input count differs by design).
Matching uses raw center distance; annotation uncertainty is diagnostic only
and does not enlarge the localization radius.

The bound review bundle contains 12 slow comparison videos, 300 comparison
images, 1,800 native overlays, and 300 closeup sheets. All 2,412 assets passed
integrity verification. All original videos and their 12 separate H.264
playback copies decoded through all 25 frames. Agent visual inspection covered
the 12 final-frame closeup sheets, six windows at both display thresholds;
this does not claim a complete visual review of every video frame. Ryan's
review of the new temporal evidence remains pending. Earlier detector-review
approval does not approve these new temporal outputs.

At both predeclared display thresholds (0.20 and 0.35) and the raw 10-pixel
radius, the highest-confidence control retains more correct matches than
every tracklet variant in both pools. Tracklets remove some false guesses but
also suppress correct observations. P001 challenge frame 224 matches in raw
and top-one views but is missed by all four tracklet variants; P003
representative frame 324 is retained by the wider 0.03-step variants but
dropped by both tighter 0.01-step variants. These are descriptive development
results from short windows, not a selected winner or generalization claim.

Final focused validation passed all 25 new tests. The final full suite ran
324 tests in 147.691 seconds: 323 passed, one existing directory-symlink
capability skip. Both used the repository `.venv` with bytecode writing disabled.
`git diff --check`, new-file JSON/Python syntax and whitespace checks, and exact
13-file scope verification passed. The first full-suite run was deliberately
stopped after the synthetic preview prompted larger headings and moving
tracklet labels away from the ball marker; its partial result is not counted.
No association or scoring rule changed after validation. The exact committed
file hashes and Git blobs match the validated scope.

Generated validation artifacts are under
`data/outputs/ball_tracking/temporal_implementation_validation/` and stay ignored:
`focused_final.log`, `full_suite_final.log`, final synthetic preview PNGs, and
`validation_record.json` with output hashes and proposed file/Git-blob scope.
`staging_authorization.json` and `commit_authorization.json` record the later
Git steps. All 59 prior protected files and six raw detection files remain
unchanged, including the six annotation sets and their approval receipts.

Execution logs, `score_audit.json`, `missed_match_diagnostic.json`,
`review_bundle_verification.json`, playback copies, `results_summary.md`,
`review_guide.md`, and `execution_record.json` are ignored under
`data/outputs/ball_tracking/temporal_execution/6769e07476da/`.
The 324 observations and two scoring grids are under
`data/outputs/ball_tracking/temporal_association/rfdetr_medium_temporal_association_v0_1/`.
The review bundle beneath that directory is
`review/fa093f830294c6a4dd4259d318cdcf78/`.

The next action is Ryan's visual review of all 12 linked clips through their
final frames, using the guide's closeups to inspect dropped matches. Approval
records whether the evidence has been reviewed; it does not select a detector
setting, tracker, or quality gate. All nine old prediction paths remain absent,
all three test holdouts remain sealed, and no operating point or quality gate
is selected. No new staging, commit, push, PR, or merge is authorized by the
completed commit request.

The sections below are historical checkpoints. Their Git state, pending
implementation, annotation, and execution statements predate the work above.

## Current checkpoint: development experiment visually approved

Verified 2026-09-19 UTC (2026-09-18 America/Phoenix).

- Branch: `codex/ball-detector-baseline`.
- Exact HEAD: `84bcc8da143e54ff17a28b39db0e70c4b8b299c8`.
- Latest commit: `feat(ball-tracking): activate approved development evaluation`.
  Ryan separately approved staging the six release-checkpoint files, then
  authorized their commit with "yes you may chat". Exactly those six files
  were committed. Parent evidence commit:
  `9521569cab36c8d289c4a341b5f33273062cabb4`. Nothing was pushed.
- Clean-commit release validation passed against 59 protected file bindings.
  Detector dry-run preflight passed for exactly six development windows.
  The real frozen RF-DETR Medium run completed all 150 frames, with zero
  incomplete frames and 22,931 raw candidates retained at the 0.01 export floor.
  No labels, detector settings, or protected source/test files changed.
- Scoring created two separate 45-cell grids, containing 270 per-window
  evaluation reports in total. Representative labels have 75 eligible centers;
  challenge labels have 70 centers plus five reviewed hidden-ball frames.
- Both visual packages were rendered and passed bundle-integrity verification:
  150 synchronized comparison frames, 150 truth-region panels, 300 full-resolution
  overlays, and six 25-frame videos. Every final frame is present. All six
  videos were fully decoded for validation. H.264 playback copies are provided
  for app playback; original bound MP4V videos and PNGs are unchanged.
- Agent inspection covered all six final-frame closeups and selected P003
  occlusion-boundary images (164, 165, 169, 170). Ryan subsequently approved the
  six linked comparison clips: "the videos look good. they pretty much track
  the whole trajectory of the ball, with small little blips of possible
  detections. overall though it looks pretty solid to start". The new review
  receipt preserves this exact statement and binds both packages and all six
  playback clips. This is approval of the visual evidence as a starting point,
  not a quantitative quality gate or a claim of complete temporal trajectories.
- No operating point, quality gate, model winner, or generalization claim was
  selected. All three test holdouts remain sealed. The unchanged parent v0.1
  manifest retains nine embargoes and all nine of its old prediction paths
  remain absent. The six new versioned development outputs are the only newly
  generated predictions authorized by this release.
- Execution, scoring, and rendering all completed with a clean worktree at the
  exact activation commit. Later context, roadmap, and validation-history edits,
  the new visual-review receipt, and a temporal-association proposal remain
  uncommitted; the index is empty. Generated media/results remain Git-ignored.

### Results at the two predeclared display settings

Both use the protocol's 10-pixel localization tolerance with stored label
uncertainty. These are descriptive views, not selected operating points.

| Pool | Confidence | Correct matches | False guesses | Misses | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Representative | 0.20 | 47 | 105 | 28 | 30.9% | 62.7% |
| Representative | 0.35 | 39 | 12 | 36 | 76.5% | 52.0% |
| Challenge | 0.20 | 48 | 53 | 22 | 47.5% | 68.6% |
| Challenge | 0.35 | 41 | 9 | 29 | 82.0% | 58.6% |

P001 is the weakest possession in both displayed views. In P003's five
hidden-ball frames, the 0.20 view includes four false candidates across three
frames; 0.35 includes one false candidate. Frame 164 has an offset candidate
at 0.20 that still counts as FP plus FN under the displayed localization rule.
The six reviewed annotation sets, all approval receipts, the frozen parent,
and the historical pilot scoring report retain their original hashes.

### Evidence and exact next action

- Review guide: `data/outputs/ball_tracking/development_execution/84bcc8da143e/review_guide.md`.
  It links all six playback clips, every final-frame closeup, all-frame contact
  sheets, both full scoring grids, and their review manifests.
- Audited run record: `data/outputs/ball_tracking/development_execution/84bcc8da143e/execution_record.json`.
  This binds all detection/report/visual files and records the exact scope of
  agent image inspection. Its execution-time pending-review state is preserved;
  the later receipt below records completion. Runtime warnings are retained
  in the inference log; the installed source documents `_kp_active_mask` as a
  deterministic keypoint buffer. No package or model configuration was changed.
- Representative visual bundle:
  `data/outputs/ball_tracking/detection_review/rfdetr_medium_development_evaluation_v0_2_representative_evaluation_comparison/5ca366b16581f0a2156f1b64badd39e1`.
- Challenge visual bundle:
  `data/outputs/ball_tracking/detection_review/rfdetr_medium_development_evaluation_v0_2_challenge_evaluation_comparison/a8e607388bfbb511212b3956a63f55a3`.
- Human review receipt:
  `configs/ball_tracking/reviews/rfdetr_medium_development_candidate_comparison_review_record_v0_1.json`,
  SHA-256 `a60dea646736135620fb97eba9f1985f7b06f0c7bfc7abee38537580c05f4dba`.
  Its timestamp is receipt creation time, not an invented message event time.
  Both bundle-integrity checks, all six original/playback clip hashes, all 59
  protected file hashes/Git blobs, and all nine absent old outputs passed again.
- Candidate-availability diagnostic:
  `data/outputs/ball_tracking/development_execution/84bcc8da143e/candidate_availability_diagnostic.json`,
  SHA-256 `2bf4efc3bf94472c8f5411fd28194c72a308584ece6faab071841cb856cf55b3`.
  At the stored 0.01 floor and 10-pixel scoring radius, P001 has a qualifying
  candidate in only 10/25 representative and 18/25 challenge frames. These are
  label-assisted ceilings for retaining original candidate centers at those
  settings, not achievable tracking results. No inference or scoring was rerun.

Next: review the concrete design in
`docs/ball_temporal_association_experiment_proposal.md` and implement its
synthetic-first support before proposing a new execution manifest. It compares
raw candidates, a highest-confidence control, and causal tracklets using only
the six saved development outputs. No tracker has been implemented or run.
The completed visual review need not be requested again. The new proposal is
not an execution permit, operating-point choice, or quality gate. Keep all
holdouts sealed. Completed detector artifacts remain bound to `84bcc8d`;
inspect them without overwriting them or changing provenance to bypass resume
checks. No unrun manual command was left with Ryan. Staging, further commits,
and pushing need separate authorization. No production code changed this turn;
the existing full-suite result remains 299 run, 298 passed, one capability skip.

The release-preparation and annotation snapshots below are historical. This
section supersedes their old Git states and next-action instructions.

## Earlier release-preparation checkpoint

Verified 2026-09-19 UTC (2026-09-18 America/Phoenix).

- Branch: `codex/ball-detector-baseline`.
- Exact HEAD: `9521569cab36c8d289c4a341b5f33273062cabb4`.
- Commit: `feat(ball-tracking): add approved development evaluation support`.
  Ryan separately authorized staging the 35-file scope and then said
  "yes commit please". The commit contains exactly those 35 files; their
  working-file bytes were preserved. Nothing was pushed.
- The clean evidence commit passed release preparation using the repository
  `.venv` with bytecode disabled: full-suite return code 0, 299 tests recorded,
  all six annotation approval chains and 330 review assets verified. The
  validation report binds 59 protected code, test, label, receipt, and proposal
  files to the evidence commit's Git blobs.
- Ignored validation report:
  `data/outputs/ball_tracking/release_evidence/9521569cab36c8d289c4a341b5f33273062cabb4/validation.json`.
  Its copied evidence file has SHA-256
  `9a47a6c4e48a77cf0e91311faceae085956a61952ae01697064d0bf778ef03b4`.
- The approved preparation command created five new activation files: evidence
  copy, release receipt, v0.2 experiment manifest, and two pool review plans.
  Their hashes, approval/parent bindings, exact six-window scope, and global
  window/run/output uniqueness were verified. This context file is the sixth
  proposed release-checkpoint file.
- Current worktree: five untracked activation JSON files and this modified
  context file; the index is empty. No activation file has been staged or
  committed. Runtime release validation correctly refuses this uncommitted
  state before model construction.
- The parent v0.1 manifest is unchanged with all nine historical embargoes.
  None of its nine embargoed prediction files or the six new development
  prediction files exists. The new manifest names only the approved six
  development windows (150 frames); all three holdouts stay sealed.
  No operating point or quality gate was selected, and no real inference ran.

The next step is separate staging authorization for the six exact files below,
followed by review of their staged contents and separate commit authorization.
Ryan's experiment approval is already recorded; do not request it again.
After that activation commit, run the existing detector's dry-run preflight,
then the approved six-window experiment, separate-pool scoring, and both visual
review plans. Do not modify protected source/labels or relax any gate. Ryan
must review the resulting real visual evidence; push remains unauthorized.

### Proposed release-checkpoint staging scope

```text
configs/ball_tracking/reviews/rfdetr_medium_development_evaluation_v0_2_9521569cab36_evidence.json
configs/ball_tracking/reviews/rfdetr_medium_development_evaluation_v0_2_9521569cab36_release.json
configs/ball_tracking/experiments/rfdetr_medium_development_evaluation_v0_2.json
configs/ball_tracking/reviews/rfdetr_medium_development_evaluation_v0_2_representative_evaluation_comparison.json
configs/ball_tracking/reviews/rfdetr_medium_development_evaluation_v0_2_challenge_evaluation_comparison.json
docs/context/current_state.md
```

The checkpoint below records the earlier annotation/implementation work.
Its old HEAD, uncommitted status, and next-action statements are historical;
this section supersedes them. Always verify current Git state first.

## Earlier annotation and implementation checkpoint

Verified 2026-09-18 America/Phoenix (2026-09-19 UTC). This section supersedes
the historical snapshot below for session continuation.

- Branch: `codex/ball-detector-baseline`.
- Exact HEAD: `b7a887f55705623889625edf60028e2e39d38dc4`.
- Worktree intentionally contains uncommitted work. Preserve the existing
  working-agreement edit, six development annotation files, approval and
  finalization receipts, pilot review record, annotation initializer, and its
  tests. This context update is also uncommitted. Nothing is staged; no commit,
  push, PR, or merge was performed during this annotation continuation.
- All six representative/challenge development windows are labeled, visually
  approved by Ryan through their final frames, and finalized as `reviewed`.
  They use the established single-annotator visual self-review policy.

| Possession | Purpose | Inclusive frames | Labeled | Localization eligible | Not visible |
| --- | --- | ---: | ---: | ---: | ---: |
| P001 | Representative | 50–74 | 25 | 25 | 0 |
| P001 | Challenge | 200–224 | 25 | 25 | 0 |
| P002 | Representative | 250–274 | 25 | 25 | 0 |
| P002 | Challenge | 25–49 | 25 | 25 | 0 |
| P003 | Representative | 300–324 | 25 | 25 | 0 |
| P003 | Challenge | 150–174 | 25 | 20 | 5 |

The development sets total 150 labeled frames: 14 fully visible centers,
131 partially visible amodal center estimates, and five `not_visible`
occlusions. All 145 geometry points are localization eligible. There are no
unlabeled or excluded rows. P003 challenge frames 165–169 remain explicitly
occluded by the referee with null geometry; no interpolation crosses this gap.

### Evidence and validation at this checkpoint

- Annotation authority: the six `*_representative_evaluation_v0_1.json` and
  `*_challenge_evaluation_v0_1.json` files in
  `configs/ball_tracking/annotations/`.
- Approval authority: the matching frame-scoped `*_visual_review_approval_v0_1.json`
  and `*_single_annotator_finalization_v0_1.json` receipts in
  `configs/ball_tracking/reviews/`. Receipts bind the source, approved draft,
  visual bundle, and finalized file hashes to Ryan's actual approval statements.
- Finalization changed only `/review/status`, `/review/reviewer_id`, and
  `/review/reviewed_at_utc`. Every frame-level decision is unchanged.
- P003 representative final annotation SHA-256:
  `2b35475e715e9a4b816ad997b58be3201370695a2f420a35a6947696bbe3637e`.
- P003 challenge final annotation SHA-256:
  `ab77e6c8570ee8fc536632e43ee71d978e72cd16188f7564c77ae256873994ee`.
- Generated visual packages remain ignored beneath
  `data/outputs/ball_tracking/annotation_visual_review/`. P003 bundle IDs are
  `82e049e3ea6d16f944f1a64345ef7f692e285864edbf47ce3c27161cf35353bf`
  for frames 300–324 and
  `0c6b7ea0d768643f6f4b36d0151a40001d2b2b88f3dc2db5a091ec5b981fa35b`
  for frames 150–174. Their immutable snapshots correctly retain draft status;
  the receipts document the subsequent metadata-only finalization.
- The repository `.venv` with bytecode writing disabled passed strict schema
  and source-video verification for all six sets, the existing finalization
  receipt assertions for all six, and hash/size verification of all 330 review
  assets. This six-window audit completed; it was not merely proposed. At that
  annotation-only checkpoint, runtime code was unchanged and the full suite
  had not been rerun; the implementation checkpoint below supersedes this.
- The existing local pilot candidate-comparison review record reports Ryan's
  approval at `2026-08-24T05:05:09Z`. Its bound review plan, scoring report, and
  visual manifest still match their recorded hashes. The old snapshot's
  instruction to run the first pilot baseline is historical, not a current
  request to regenerate those artifacts.

### Prediction boundary and next action

All nine evaluation windows still have
`annotation_pending_prediction_embargo` in the unchanged v0.1 experiment
manifest. None of their nine declared prediction output files exists.
Completed annotation does not release predictions. No operating point or
quality gate was selected; no inference ran in this continuation.

Ryan approved the development experiment with "lets move forward I approve
of this experiment". The statement and immutable proposal-inventory hash are
recorded in
`configs/ball_tracking/reviews/rfdetr_medium_development_experiment_approval_v0_1.json`.
This authorizes implementation and the proposed six-window experiment once
its clean-checkpoint release conditions pass; it does not authorize staging,
committing, pushing, a holdout release, an operating point, or a quality gate.

Versioned support is implemented in `development_experiments.py`,
`development_release.py`, and `development_scoring.py`, with explicit v0.2
handling in the existing loader, runner, scorer, and visual renderer. The
strict six-window parent binding retains frozen detector settings and all
45 grid cells. Scoring produces two separate pools and 270 per-window results;
visual review produces one complete three-window package for each pool.
Synthetic tests use artificial frames and injected adapters only.

The release verifier checks approved labels and assets during evidence
preparation. At runtime it checks the release receipt and committed Git blob
identities without opening annotation JSON or review images. Evidence belongs
to a future clean commit; activation artifacts belong to a later separately
authorized commit. The new executable manifest and its six prediction outputs
remain absent. All nine original embargoed outputs remain absent. Existing
uncommitted files and the old manifest are preserved.

Implementation validation completed using the repository `.venv` with bytecode
writing disabled. The 14 new development tests, 10 existing detector visual
review tests, and 27 independent-review tests passed. The final full suite ran
299 tests: 298 passed, one existing directory-symlink capability test skipped.
`git diff --check` passed; new untracked Python syntax and whitespace checks
also passed. The ignored full-suite log is
`data/outputs/ball_tracking/development_implementation_validation/full_suite_20260919_retry.log`.
The first full run exposed an old independent-review test fixture with a fixed
August review timestamp earlier than its newly generated September creation
time. The fixture now derives its timestamp from creation; production review
rules and annotation data are unchanged. The full suite then passed.

The audit reverified all 24 approved inventory bindings, the frozen parent
hash, all nine original absent prediction outputs, and the six absent new
outputs. The existing working-agreement edit retains SHA-256
`55eb9c73c29c3f6f8c8e6c30d8caa1e9506adbded15a57e813b76f4c6fe13be3`.
No operating point or quality gate was selected; no real model inference ran.
The new source code remains uncommitted, so this successful implementation
validation is not a clean-commit release receipt.

The next external boundary is separate staging authorization for the exact
35-file list in the proposal document, then separate commit authorization. The approved experiment does not need approval again.
See `docs/ball_detector_development_release_proposal.md` for the checkpoint
procedure. Keep all three test holdouts sealed.
No development-window visual approvals remain unresolved, and no manual
commands were supplied but left unrun. The existing annotation editors may
still be open; their now-reviewed files must not be edited as drafts.

## Historical snapshot retained for provenance

The sections below describe the earlier checkpoint. In particular, their
inference and annotation to-do lists predate the local evidence above.

Snapshot date: 2026-08-23 (America/Phoenix)

## Repository checkpoint

At the current ball-detector precommit checkpoint:

- branch: `codex/ball-detector-baseline`;
- development base: `51c084c6dc8a11df883db6780a9a024d9506e5bf`
  (`feat(ball-tracking): add reviewed annotation foundation`);
- the strict RF-DETR Medium image-only adapter, resumable inference runner,
  experiment-manifest contract, source verification refactor, and regression
  coverage are implemented;
- Ryan approved nine prediction-blind evaluation windows across the same three
  possessions, and their reproducible selection record is frozen in
  `docs/ball_detector_baseline_selection.md`;
- only the three reviewed protocol pilots are marked `ready_for_inference`;
  all nine new windows remain `annotation_pending_prediction_embargo`;
- focused ball source/detector tests: 129 passed, with one Windows
  symlink-capability skip;
- full test suite: 264 passed, with the same one skip and bytecode writing
  disabled;
- no manifest-authorized baseline run or prediction on any of the nine approved
  evaluation windows has been generated; the quarantined historical exploratory
  prediction at Possession 001 frame 150 remains explicitly excluded.
- the real installed RF-DETR class mapping and a non-inference construction of
  the frozen CUDA model both pass the adapter contract; no video frame was
  supplied.

The preceding durable migration checkpoint was:

- branch: `main`;
- local HEAD and `origin/main`: `1f086ba` (merged PR #7, **Add durable desktop project context**);
- PR #6's thorough README update is included;
- the local and remote `docs/desktop-context-migration` feature refs are deleted;
- worktree: clean;
- all eight durable context files match the reviewed migration proposal;
- full test suite: 56 tests passed using the desktop app's bundled Python, with bytecode writing disabled.

Future work should still begin by checking the current branch, HEAD, worktree, and remote state rather than assuming this snapshot remains current.

## Completed technical foundation

- RF-DETR Medium person detection and ByteTrack multi-object tracking.
- Playable-court filtering and tracking audits.
- Uniform-feature team classification.
- OSNet-AIN ReID embeddings, temporal segmentation, segment reconciliation, and reviewed consolidation.
- Exactly ten persistent player identities, with five white and five dark players in validated possessions.
- Reference court calibration and one homography per decoded frame.
- Player floor-point projection to court coordinates.
- Conservative trajectory refinement and bracketed internal-gap interpolation with provenance.
- Configuration-driven, possession-scoped, resumable 21-stage orchestration.
- Explicit identity and calibration review gates.
- Multi-possession empirical generalization gate passed on Possession 003.
- Reviewed ball-center annotations for three 25-frame protocol pilots, plus a
  strict raw-detection and evaluation data contract.
- A precommitted, label-blind RF-DETR Medium ball-detector baseline contract with
  exact runtime provenance, raw-candidate preservation, resumability, and
  prediction embargoes.

## Not complete

- real ball-detector inference, scoring, temporal tracking, and their quality
  gates;
- automatic possession segmentation and broadcast-cut handling;
- ball-handler and event inference;
- mapping visual identities to NBA rosters;
- primary-defender, switch, help, and contest inference;
- the defensive scoring model;
- complete-game NBA validation and reporting.

## Immediate next task

The annotation contract, detector adapter/runner, experiment contract, scoring
grid, and prediction-blind window selection are complete. The next operational
sequence is:

1. from a clean committed snapshot, run the runner's read-only preflight and
   confirm the exact source clips,
   RF-DETR package, official weight bytes, CUDA runtime, ignored outputs, and
   three authorized pilot windows;
2. run the first descriptive baseline over only the three reviewed pilot
   windows, preserving every exported COCO `sports ball` candidate at or above
   the frozen `0.01` export floor;
3. inspect and score the fixed confidence/localization grid on those pilots;
4. annotate and review the six representative/challenge windows, then use a
   reviewed, versioned schema/manifest release instead of toggling v0.1 in
   place; freeze an operating point before separately releasing the three test
   holdouts;
5. render candidate-versus-truth evidence before proposing a temporal tracker
   experiment or any detector quality gate.

No ball-tracking implementation was started in chats 01–06. The prior blocker was intentionally removed only after Possession 003 passed the generalization gate.

### Ball-tracking annotation checkpoint

- The v0.1 annotation schema, prediction-blind editor, source verification,
  neutral review assets, visual-review renderer, and detection-evaluation
  contract are implemented on `codex/ball-annotation-foundation`.
- Possession 001 frames 375–399, Possession 002 frames 318–342, and Possession
  003 frames 416–440 each contain 25 completed annotations and are
  single-annotator, visually reviewed reference sets. Ryan approved all three
  bound visual-review packages through their final frames.
- Across the three windows, all 75 frames are labeled: 67 contain geometry, 66
  are localization eligible, eight are reviewed `not_visible` negatives, and
  one visible ambiguous frame is intentionally unscored.
- Possession 002 contains 17 geometry estimates, of which 16 are localization
  eligible, plus eight reviewed `not_visible` occlusion frames. Missing geometry
  remains explicit and un-interpolated.
- Possession 003 contains 25 continuous geometry points: five fully visible
  observed centers and 20 partially visible amodal estimates. All 25 are
  localization eligible; no geometry gap or interpolation is present.
- Duplicate or independent annotation is not a prerequisite for review or the
  current milestone. It remains optional for a specifically declared
  inter-rater or intra-rater reproducibility study.
- The protocol-declared synthetic evaluator cases pass. The raw, image-only
  detector export harness and precommitted experiment manifest are implemented.
  The next runtime task is the clean preflight and three-pilot descriptive run,
  not temporal tracking yet.

## Local data checkpoint

At migration time, the ignored `data/` tree contained 856 files totaling
6,710,202,697 bytes, all successfully SHA-256 hashed in the external manifest
`manifests/local-data-files.csv`. The ball-annotation workflow subsequently
added ignored review assets beneath `data/outputs/`; that migration-era count
is therefore historical, not the current tree total. All three source clips
still match their declared hashes, and generated review media remains ignored.
