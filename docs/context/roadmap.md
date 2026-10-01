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
Real execution awaits separate authorization for a clean Git checkpoint.
See `../ball_crop_candidate_ranking_implementation.md` for the concrete scope.

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
- [ ] checkpoint its implementation, then evaluate and review the real outputs;
- [ ] compare small-object basketball detectors;
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
