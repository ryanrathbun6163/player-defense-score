# Roadmap

## Phase 1 — Player-coordinate foundation

Status: complete for curated possessions and empirically generalized.

- person detection, court filtering, and multi-object tracking;
- team classification;
- ReID segmentation and reviewed player identities;
- camera calibration and motion compensation;
- court-coordinate export;
- audited refinement and interpolation;
- configuration-driven resumable orchestration;
- multi-possession gate.

## Phase 2 — Ball tracking

Status: in progress. The protocol, three-window annotation pilot, six reviewed
development windows, frozen image-only detector execution, separate-pool scoring,
and detector-comparison visual review are complete. The first temporal
experiment also completed execution, scoring, and Ryan's visual inspection.
It exposed losses of valid observations; it does not establish a selected
tracker or a quality gate. The current Git checkpoint is in `current_state.md`;
the all-grid closeout is in `../ball_temporal_association_results.md`.
Ryan approved the fixed overlapping-crop comparison on the same six windows.
Separate inference/scoring/review support passed focused and full tests and
was committed with separate authorization at `1a9479f83a17`. Real execution
then completed at that clean checkpoint: 600 crop calls, 1,080 reports, and
12 synchronized clips with 1,950 supporting images. All 540 saved-control
scoring cells reproduce prior outcomes. Cropped inputs improve pooled matches
at both display settings but add false guesses and have local regressions;
Ryan completed review of the new 12-clip package, stating "all of them look
pretty good to me. even P002 challenge". A separate evidence-bound receipt
records completion and preserves earlier pending-review snapshots. See `current_state.md`
for the exact evidence links and next action. No operating point or quality
gate is selected, and all nine original prediction embargoes remain intact.

The saved-grid closeout separates candidate availability from candidate choice:
at the 0.20/10-pixel display cell, crop raw matches 62 representative frames,
but top one matches only 51. A concrete recent-history candidate-ranking
experiment is specified in `../ball_crop_candidate_ranking_proposal.md`.
Ryan approved its exact scope with "I approve chat". Separate implementation
now reuses the six saved crop files with raw/top-one/top-twenty controls and
two motion limits. All 21 focused tests pass; the full suite has 362 passes
and one existing Windows symlink skip.
Ryan separately approved staging and committing that implementation at
`3c4894656fd5`. Real execution is complete: 270 derived outputs, 1,350 reports,
all 540 saved crop control parity checks, and 12 review clips plus 2,400 PNGs.
Both originals and separate H.264 copies decoded all 25 frames at 5 fps.
Wide links improve challenge matches in all 45 grid cells but lose matches
in five representative cells; tight links lose matches in all 45 cells of
both pools. No method, operating point, or quality gate is selected.
Ryan responded "looks good to me" to the linked ranking review package.
A separate receipt records that package-level response and its scope limits;
the exact statement does not itemize clips or separately attest every final
frame. Earlier crop/temporal reviews remain complete. The saved-evidence
diagnosis is now complete in `../ball_crop_candidate_ranking_results.md`.
It separates unavailable/filtered candidates from cap and ranking losses,
and identifies that the tight/wide comparison couples allowed movement with
movement cost. The concrete next proposal, `../ball_crop_motion_factorial_proposal.md`,
crosses those two parameters while fixing the rest of the algorithm. Ryan
approved its exact seven-arm scope with "I approve chat". Four separate modules
and 23 passing focused tests now implement it. The full suite has 385 passes
and one existing Windows directory-symlink skip.
The synthetic comparison covers 378 outputs, 1,890 reports, all 270 trace/1,350
report/450 aggregate control checks and 12 complete clips with 3,000 PNGs.
Ryan separately authorized the exact staging scope and commit at `2274ab6097cd`.
The real comparison is now complete: 378 outputs, 1,890 reports, all saved
control checks, 12 clips and 3,000 PNGs. All original and H.264 copies decode
25 frames at 5 fps. Increasing movement allowance recovers matches throughout
the grid; penalty effects depend on the allowance and pool. Persistent clutter,
P002 representative 262 and hidden-ball false starts remain unresolved.
Ryan confirmed "I have reviewed all of these clips. move forward". A separate
receipt records completion of the requested 12-clip review without invented
frame-level verdicts. The saved-evidence closeout reconciles all 1,080 loss
partitions and audits 4,843 emitted winners across 216 history outputs. Persistent
wrong paths already have multiple observations, while correct starts can be
singletons. A read-only feasibility audit examines existing player/scene context
without applying a new rule or projecting the ball to the floor. The next design
question is candidate identity evidence, with abstention treated as a separate
tradeoff. See `../ball_crop_motion_factorial_results.md`.
No method, operating point, quality gate or holdout release is selected.
See `current_state.md` for exact evidence bindings and preservation checks.

The saved candidate-identity diagnosis is now complete in
`../ball_candidate_identity_diagnosis.md`: 12 agent-inspected sheets cover 215
unique saved winners. Repeated distant clutter supports testing context;
near-player confusion and imprecise ball localization limit its claim.
`../ball_crop_player_context_proposal.md` specifies a single fixed soft
distance penalty alongside all four motion settings, with all seven existing
controls reused. The proposal binds 1,353 observed player rows in the same six
windows. Ryan approved that exact scope with "I approve chat". Four separate
modules now implement it, with 34 focused passes and 419 full-suite passes
plus one existing Windows skip. Synthetic execution verifies 216 new outputs,
1,080 new reports, 12 complete paired clips and unchanged reuse of all prior
controls. Ryan separately authorized exact staging and committing at
`119159817df5`. The real comparison then completed at that clean checkpoint:
216 new outputs/1,080 new reports, unchanged reuse of all saved controls, and
12 complete paired clips with 2,100 new PNGs plus 2,400 native image references.
Every original and H.264 playback copy decodes 25 frames at 5 fps. No aggregate
cell loses matches or increases false positives across the fixed comparison
grid; local false alarms and final-frame misses remain. These are correlated
development results, not independent trials. Ryan explicitly confirmed reviewing
all twelve new clips through their final frames. The evidence-bound receipt and
saved-results closeout are recorded in `current_state.md` and
`../ball_crop_player_context_results.md`. All 1,080 local paired comparisons
preserve matches and do not add false-positive frames or increase shared-match
error; residual detector/filtering/path-selection weaknesses remain.
The next concrete proposal, `../ball_yolo11x_crop_comparison_proposal.md`, tests
one fixed detector bundle on the same windows/crops with simple selectors and
byte-reused controls. Its approved implementation was committed at `116e3ed9cb41`;
the run preserved 175 crop units before a validator failure. Ryan approved the
versioned recovery plan, and its tested seventeen-file implementation was
separately staged and committed at `3326482e6f7e`. Recovery completed the 425
missing units without a new failure, preserving all 175 original units and
their actual inference commits. Scoring and rendering are complete, and Ryan
approved all twelve new clips in response to the final-frame review request.
The separate review receipt and closeout are in `current_state.md` and
`../ball_yolo11x_crop_recovery_results.md`. YOLO has fewer matches in all 270
paired aggregate cells on these development windows. The bounded saved-results
comparison of ten single-detection families is complete: 900 aggregate cells,
2,700 reports and 3,000 displayed frame-setting records reconcile, with copied
controls counted once. It retains tradeoffs without choosing a setting and
separates twenty persistent display misses into five unavailable RF proposals
and fifteen confidence-filtered RF proposals. The subsequent saved-evidence
inspection is complete: 32 existing frames and 82 candidate identities include
weak proposals, emitted alternatives, flight, hidden and reacquisition controls.
This is agent diagnosis, not new human identity labels. The closeout was
separately committed at `9fe6a1ef86d2`; the later inspection is preserved under
`data/outputs/ball_tracking/weak_candidate_inspection/9fe6a1ef86d2/`.
The bounded proposal, `../ball_candidate_retention_localization_proposal.md`,
separates candidate retention, object identity and center placement using those
saved records. Ryan approved this diagnostic with "mover forward chat"; a
separate receipt preserves the proposal's historical bytes. Implementation,
28 focused tests, the full suite (519 passes and one existing Windows skip),
and one real saved-evidence execution are complete. The independently audited
ledger preserves 32 frames, 82 candidates, 640 outcomes and fifteen cap records.
All original 231 assets and 177 inputs are unchanged. See
`../ball_candidate_retention_localization_results.md` for retention losses,
descriptive center offsets and remaining identity uncertainty. The next
bounded design is now drafted in `../ball_crop_candidate_retention_proposal.md`.
It proposes removing the cap at .01 in the four unchanged motion settings:
24 new window outputs, 120 reports and six new review clips. Saved .20/.35
inputs never reach the cap, so their corresponding settings reference existing
results through explicit structural equivalence. The proposal measures extra
candidate load alongside false alarms, missingness, gains and regressions
across all six windows with pools separate. It includes resource bounds and
keeps identity/localization questions distinct. Ryan subsequently approved that
exact comparison with "I approve. Please move forward chat". Five modules and
five synthetic test files implement the approved scope. Validation is complete:
78 focused passes, 597 full-suite passes with one existing Windows skip, and
both dense/sparse 400-candidate/25-frame benchmarks passed. The implementation note is
`../ball_crop_candidate_retention_implementation.md`. Real execution awaits
the required clean tested commit, with staging and committing separately
authorized. Training remains unapproved.
No method, operating point, quality gate or holdout release is selected.

- [x] define the ball annotation and detection-evaluation protocol;
- [x] label and visually review a 75-frame pilot spanning three possessions;
- [x] precommit new contiguous representative, challenge, and holdout pools;
- [x] implement the frozen image-only detector adapter and guarded runner;
- [x] annotate, approve, and finalize all six development windows;
- [x] execute the approved 150-frame development baseline and review its six clips;
- [x] compare saved detections with causal tracklets and inspect all 12 temporal clips;
- [x] execute the approved fixed-crop comparison on the six development windows;
- [x] visually review all 12 fixed-crop comparison clips through their final frames;
- [x] approve the fixed recent-history selector experiment on saved crop candidates;
- [x] implement and synthetically validate the approved candidate-ranking experiment;
- [x] commit and execute the approved ranking comparison on the saved development inputs;
- [x] record Ryan's visual-review response to the requested 12-clip ranking package;
- [x] diagnose remaining candidate/ranking misses from saved evidence before a new design;
- [x] specify a bounded comparison separating movement allowance from movement cost;
- [x] approve and implement the exact motion-factorial experiment;
- [x] validate the motion-factorial implementation with focused and full suites;
- [x] separately authorize staging and committing its exact validated scope;
- [x] execute, score and render the approved motion-factorial comparison;
- [x] record Ryan's completed review of the requested 12-clip final-frame package;
- [x] close out motion results and diagnose saved path support and remaining failures;
- [x] audit feasibility of existing image-space player/context evidence;
- [x] inspect saved candidate appearance and crop-view evidence;
- [x] specify a bounded soft player-context comparison;
- [x] approve the exact proposed player-context scope and implement/synthetically validate it;
- [x] separately authorize staging and committing its exact validated eighteen-file scope;
- [x] execute, score and render the approved player-context comparison at the clean commit;
- [x] review all twelve new paired context clips through their final frames;
- [x] close out saved player-context results and specify one detector challenger;
- [x] approve, implement and synthetically validate the fixed YOLO11x crop comparison;
- [x] separately authorize staging and committing the exact nineteen-file YOLO scope;
- [x] execute clean preflight and preserve the interrupted 175-unit YOLO run with a diagnosed validator failure;
- [x] review and approve the v0.2 recovery proposal that preserves original per-crop code provenance;
- [x] implement and validate approved recovery support;
- [x] separately authorize staging and committing the exact recovery implementation;
- [x] complete the remaining 425 YOLO crop units, score/render and review all twelve new clips;
- [x] compare the fixed RF-DETR and YOLO11x detector configurations;
- [x] record the completed YOLO review and close out the saved comparison;
- [x] consolidate existing single-detection settings and persistent errors from saved results;
- [x] inspect weak matching proposals and emitted alternatives in the bounded saved-frame cohort;
- [x] draft a bounded candidate-retention and localization diagnostic proposal;
- [x] approve, implement and validate the bounded saved-evidence diagnostic;
- [x] execute it once and independently audit its ledger and source preservation;
- [x] prepare the next bounded comparison with retention and localization questions separate;
- [x] review and approve the exact retention-comparison scope;
- [x] implement the bounded selector, preserved-control scoring and saved-PNG review;
- [x] finish focused/full regression and dense/sparse resource validation;
- [ ] separately authorize staging and committing the tested retention implementation;
- [ ] execute the approved retention comparison from that clean checkpoint;
- [ ] review the six new .01 clips through their final frames;
- [ ] associate detections through blur, occlusion, passes, shots, and rebounds;
- [ ] preserve uncertainty and missing observations;
- [ ] map ball observations into court/time context where defensible;
- [ ] render synchronized ball/player review output;
- [ ] pass a multi-possession quality gate.

## Phase 3 — Possession and event understanding

- segment live play, dead balls, transitions, cuts, and replays;
- infer ball handler and possession changes;
- detect passes, shots, rebounds, turnovers, and fouls;
- attach events to players, time, and court position.

## Phase 4 — NBA player identity and lineup context

- map persistent visual identities to rostered players;
- add jersey-number and metadata evidence;
- track lineups and substitutions across possession boundaries.

## Phase 5 — Defensive matchup inference

- primary on-ball assignments;
- switches, help, traps, and recoveries;
- defender distance, angle, closing speed, screen navigation, and contest quality;
- uncertainty for ambiguous assignments.

## Phase 6 — Defensive scoring

- define transparent features and outcome weights;
- build a human-labeled evaluation set;
- compare heuristic and learned approaches;
- validate stability across players, teams, lineups, and contexts;
- aggregate possession scores to matchup, player, and game reports.

The original made-shot/foul/pass/miss/turnover values were brainstorming examples, not approved final weights.

## Phase 7 — Full-game NBA scale

- replace/extend the current NFHS right-half-court profile with NBA court profiles;
- support both directions and full-court transitions;
- handle overlays, bench views, camera cuts, and replays;
- batch GPU stages and checkpoint long jobs;
- reduce manual review while retaining auditable thresholds;
- validate full games.

## Phase 8 — Reporting and product layer

- possession-level JSON and review clips;
- per-player and per-matchup reports;
- interactive court/timeline visualization;
- stable CLI, API, or dashboard output.

Source: merged GitHub README from PR #6, cross-checked with Chat 01's initial goal and Chat 06's clean generalization checkpoint.
