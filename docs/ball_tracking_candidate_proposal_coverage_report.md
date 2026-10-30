# Alternate-producer candidate coverage result v0.1

October 29, 2026. **Completed capture and independently audited CPU census. The
predeclared coverage screen passes; no scorer fit or model adoption occurred.**
This result supersedes the progress status in the preserved
[capture protocol](ball_tracking_candidate_proposal_coverage_protocol.md).

## Result and its meaning

The fixed expanded-NFHS detector supplies the three decision-relevant example
types that the saved cosine-nine training population lacked across games.
All three categories appear in CHI–IND, DEN–BOS and SAC–MEM. They remain present
in every intended outer training fold after the conservative historical-role
and point-input screen. There are **461 useful, role-compatible exact-new
candidate points on 394 already-used frames** across 18 blocks and 70 consecutive
source-frame runs. This meets the prospective engineering screen for designing
a controlled producer-transfer experiment.

These are new point inputs on existing accepted images, not new scenes or 461
additional correct tracker detections. No trained scorer, gate, selector or
reported tracking accuracy changed. The 95%-correct / 1%-wrong / zero-hidden,
temporal, recovery and human-review requirements remain in force. The previous
quality-top 90.39% result and its 90.43% selection ceiling remain unchanged.

| Required producer-relative case | Raw points/frames | After role/input screen | Games | Consecutive runs | Longest run |
|---|---:|---:|---:|---:|---:|
| Chosen native point is a known distant error | 305 | 304 | 3 | 56 | 73 frames |
| Chosen native point on a certainly-hidden frame | 81 | 81 | 3 | 12 | 28 frames |
| Correct weak alternative while native is wrong or missing | 76 | 76 | 3 | 32 | 13 frames |

The 76 weak recoveries split into 67 while native is wrong and nine while it is
missing. Wrong-case recoveries span all three games; missing-case recoveries
span CHI and SAC, in three runs. The combined recovery category was the frozen
gate; these subgroups were retained separately rather than redefining it.
The raw useful union is 462 points on 395 frames. One selected-error point has
an unresolved historical non-training source-frame overlap, leaving the 461
eligible exact-new points. No historical role or semantic target was changed.
Of these 461 points, 452 have a different floor-centered crop from every
current candidate; nine use an existing crop with a different point readout.
Exact-coordinate novelty therefore does not imply 461 new crop images.

| Source | Known chosen errors, raw / screened | Native hidden emissions | Weak recovery points |
|---|---:|---:|---:|
| CHI–IND | 165 / 165 | 32 | 56 |
| DEN–BOS | 102 / 102 | 1 | 12 |
| SAC–MEM | 38 / 37 | 48 | 8 |

Coverage is uneven. DEN contributes only one native-hidden example, CHI supplies
56 of the 76 weak recoveries, and long adjacent runs remain. The minimum screen
is not a statistical-power calculation, proof of independent plays, or evidence
that these examples will transfer to the current detector's mistakes.

## Counterevidence: volume, retention and the current-policy gap

The uncapped pools contain **1,091,879 candidates**, versus 18,813 in the saved
cosine population: about 58 times as many. There are 6,176 native and 1,085,703
retained weak candidates. The independent extraction also recounts 1,085,983 raw
weak components before native/weak merging. The 461 points meeting the combined
required-case, exact-novelty and role criteria are about 0.042% of the full pool;
this fraction does not declare every other point useless as a possible control.
Dense weak proposals can create geometric matches without useful confidence or
identity discrimination. A million-row training expansion is not justified by
the coverage pass.

The full target census is 3,700 positive, 966,793 known distant negative,
40,341 certain-hidden, 446 boundary-unknown and 80,599 masked-unknown candidate
rows. Candidate-row counts are not frame accuracy. Unknowns remain unknown.
Every frame, empty/native-missing case, original 610 weak-positive candidates
and 60 historical semantic rows remains represented in the comparison.
Among those 610 original weak-positive frames, the alternate pool retains any
positive on 491 and loses all positives on 119; 153 retain a weak positive and
455 receive a correct alternate native choice. These overlapping counts are
not additive, and none of the 610 original points has an exact-coordinate
carryover. The complete old pool covers 2,809 positive frames, versus 2,630 for
the alternate pool, despite its higher positive candidate-row count.

| Unfiltered native choices on accepted training frames | Current cosine nine | Alternate producer |
|---|---:|---:|
| Correct on eligible frames | 2,807 | 2,425 |
| Wrong on eligible frames | 3 | 308 |
| Missing on eligible frames | 1 | 78 |
| Emissions on certainly-hidden frames | 2 | 81 |

This table is before the saved J acceptance gate. Of the alternate producer's
308 wrong choices, 305 are known distant negatives and three remain boundary
unknown. It loses 382 previously correct native choices and natively recovers
none of the current detector's four wrong/missing cases. Its complete pool
loses positive availability on 180 current-positive frames while adding it on
one. The current detector and its saved pools therefore remain the baseline;
the alternate producer's useful role here is supplying different examples.

Current-cosine-relative weak recovery is a separate descriptive result: one
correct alternate weak candidate on a current-wrong CHI frame, zero on the
current-missing frame. The current wrong/missing population is still four CHI
frames. Producer-relative recoveries elsewhere do not create cross-game examples
of current-policy failure on fresh scenes. All 21 saved HOU external recovery
cases, including the six below-.01 cases, remain referenced regression history.
No new HOU, DET, TOR or protected evaluation was performed.
Of the alternate producer's 76 recovery frames, 75 already have correct current
cosine native choices; only one is a current-cosine wrong frame.

## What changed, and what was reused

One fixed checkpoint changed: expanded-NFHS SHA256
`09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98`.
Its local adaptation used NFHS 150 and no project NBA images; the upstream
pretraining-game inventory is unknown. Its earlier adaptation resolution was
512×288. Consequently the result cannot isolate NBA familiarity from weight
and resolution-history effects or certify globally unseen NBA data.

The capture reused all 3,179 accepted NBA training frames, existing RGB caches,
768×432 preprocessing, canonical cadence, float32 contributor means, native
strict >.3 extraction, weak strict >.01 extraction and two-source-pixel merging.
The old 512×288 SAC caches remain historical evidence and were not imported.
All 3,137 scheduled triplets returned; there were zero extra parity forwards,
zero imports, zero optimizer updates and zero new labels. Predictions and full
pools were sealed before accepted references were joined. The new code lives
in `src/ball_tracking/candidate_proposal_coverage_capture.py` and
`src/ball_tracking/candidate_proposal_coverage_analysis.py`.

The earlier CPU failure study, acceptance experiment, origin ablation and
coverage review were reused. None was rerun. Exact point overlap, floor-centered
64-pixel crop overlap and source-frame overlap are separate recorded fields;
different coordinates do not prove a new object or scene.

## Recommended next decision

Design one bounded comparison asking whether adding the newly covered examples
helps the existing scorer/gate retain correct detections and reject errors.
Hold representation, objective and downstream policies fixed so that the added
proposal population is the isolated change. Specify the exact role-compatible
training additions, deduplication, source/run concentration, successful controls,
fit budget and retention/recovery vetoes before fitting. Preserve the complete
saved populations, including every weak recovery, as comparisons. Passing this
capture authorizes neither an automatic fit nor adoption.

Fresh permitted footage remains the direct alternative for obtaining failures
of the current detector on genuinely new scenes. A representation/visibility
diagnostic remains plausible if there is evidence that existing inputs omit
necessary information. This metadata census cannot establish that limitation.
Earlier player-context, temporal/head-fill, point-versus-CLS and acceptance
experiments remain counterevidence against simply renaming an existing recipe.

The due-diligence review freshly rechecked those project results and primary
research. DCR supports studying hard false positives but also warns that nearby
true objects can contaminate classification through large receptive fields;
it does not establish that wider context will help our point target
([DCR paper](https://arxiv.org/html/1803.06799v3)). JTT uses informative errors and
a small group-annotated validation set; it does not guarantee transfer from an
alternate producer or justify arbitrary error upweighting
([JTT paper](https://proceedings.mlr.press/v139/liu21f.html)). The basketball crop
study evaluates a different diameter/presence task and does not establish
crop-size superiority for these proposal errors
([basketball study](https://arxiv.org/html/2204.00003)). Error-enriched examples
must be distinguished from representative accuracy samples; successful controls
are necessary to assess retention, and matched challenge controls alone do not
estimate real-world prevalence.

## Verification and continuation record

All 23 focused tests passed. A CPU-only strict checkpoint load used no forward
or CUDA initialization. Fresh observed Debug Mode ON and device/process checks
preceded the owned supervised run. Capture took 236.36 seconds; total charged
launcher time was 288.75 seconds. Maximum GPU temperature was 59°C. No qualifying
fault, settings change, retry, model-tensor change or surviving owned process
was recorded. All 21 mean files occupy 4,218,866,304 bytes; the complete capture
occupies 4,688,120,502 bytes.

Independent capture review checked all saved means, native/weak extraction,
3,137 attempted/returned calls and 9,411 channel contributions. Independent CPU
analysis review reconstructed all candidate targets, paired outcomes, novelty,
retention, category/run populations and both coverage decisions. Raw per-forward
channels were discarded as specified: their actual numerical means cannot be
recomputed after the run. Saved means/extraction and contributor bookkeeping
were audited; numerical reduction order is supported by synthetic float32 tests
of the unchanged streaming reducer. This limitation is explicit in the receipts.

Evidence is under `data/outputs/ball_tracking/candidate_proposal_coverage_v0_1/`:

- `preparation/` and `launch_v0_1/` retain immutable input, compatibility,
  execution, readiness and supervision receipts.
- `attempt_001/capture/` retains full means, candidate pools and accounting;
  `attempt_001/analysis/` retains the complete census and decisions.
- `review/capture_output_audit.json` and `review/analysis_audit.json` record
  the independent successful audits. The report review and final preservation
  review are recorded in the same directory.
- `support/interpretation_due_diligence.json` and the subsequent interpretation
  record distinguish conditional reasoning from the audited outcome.
- `documentation_update/receipt.json` preserves the inherited 138-file worktree
  through exact backups and reversible history insertions. The result ledger is
  `configs/ball_tracking/reviews/candidate_proposal_coverage_v0_1.json`.

An early metadata-only preparation raced a final source edit; its hash guard
stopped CPU compatibility before Torch/model construction. That preparation was
preserved and rebuilt against the final source before the successful compatibility
check and freeze. No neural attempt was repeated. The original handoff and
Session17 history chain, standing due-diligence instruction, branch/HEAD and
empty index remain preserved; no Git integration occurred.
