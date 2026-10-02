# Saved candidate-retention and localization diagnostic

Status: complete on October 2, 2026. The approved diagnostic ran once against
the frozen saved evidence, after focused and full-suite validation passed.
An independent output audit passed. Branch remains `codex/ball-detector-baseline`
at `9fe6a1ef86d23391c64b7d5b16198ad7bb005c25`; implementation and documentation
are unstaged and the index is empty.

Ryan responded **"mover forward chat"** to the concrete diagnostic proposal.
The separate approval record is
`configs/ball_tracking/reviews/saved_candidate_retention_localization_approval_v0_1.json`.
It authorizes this bounded diagnostic's implementation and execution. The
original proposal and design retain their exact bytes and historical status.
No new detector/tracker experiment, training or Git step is authorized.

The new helper is `src/ball_tracking/candidate_retention_diagnostic.py`, with
synthetic tests in `tests/test_ball_candidate_retention_diagnostic.py`.
It uses saved JSON records and file hashes, with no model, selector, evaluator,
renderer or media-decoding imports. The only new geometry calculation is the
signed x/y offset and Euclidean distance between an existing candidate center
and an eligible reviewed reference center. It creates no corrected centers,
new matching outcomes or semantic identity labels.

## What the diagnostic separates

**Retention is a mechanical question.** Fifteen of the twenty persistent
display misses have a saved RF radius-10 match at the .01 floor. Their
confidence is below both .20 and .35. Eight of those fifteen also lose the
match in the separate saved .01 top-twenty reports. These are different
settings' accounts of the same source frames, not additive errors. The five
other frames lack a saved qualifying RF center at the floor; their boxes may
still contain ball-region pixels.

**Candidate choice is a separate stage.** The ledger preserves original
dispositions and arm names. YOLO's top-one `outside_selector_cap` means a final
choice rejected an alternative; the normalized ledger describes that as
`retained_but_not_emitted`, rather than confusing it with preprocessing loss
under the twenty-candidate cap. RF and YOLO indices have distinct namespaces.

**Localization does not establish identity.** The completed agent inspection
describes some failed boxes as containing a ball fragment or ball/hand
boundary. Their center offsets cannot certify a non-ball label. The ledger
keeps all original match results and null matched-error fields, while adding
clearly separate reference-distance fields. Of the 27 eligible reference
frames, 25 use partially visible amodal estimates and two are fully visible.
Annotation uncertainty remains separate; it does not enlarge the radius.

Five hidden frames preserve null geometry and null residuals. All 82 candidate
identities remain uncertified and ineligible for training. Shared observations
from the completed inspection remain attributed shared passages, rather than
being converted into invented candidate-by-candidate judgments.

These four RF examples put numbers beside the existing fragment/ball-hand
observations. Distances are from the saved candidate center to the reviewed
reference, rounded here to two decimals; the ledger preserves full precision.

| Development frame / original RF index | Confidence | Reference distance (px) | Reviewed uncertainty radius (px) |
| --- | ---: | ---: | ---: |
| P001 representative 51 / #0 | 0.279342 | 14.73 | 3.833 |
| P001 representative 59 / #0 | 0.678284 | 12.16 | 4.849 |
| P002 representative 257 / #4 | 0.359894 | 10.41 | 5.421 |
| P003 challenge 164 / #0 | 0.660731 | 11.50 | 3.833 |

All four fail the existing raw 10-pixel comparison. These partially visible
references are amodal estimates: they estimate the whole ball's center despite
occlusion. The discrepancy does not isolate whether the box, occlusion or
reference estimate explains the error, and uncertainty is not added to the
matching radius. In P001 51, the much weaker #99 is only 4.16 pixels from the
reference; in P003 164, #33 is 4.73 pixels away. Both weak alternatives are
also lost under the separate saved .01 top-twenty cap.

The controls expose a different failure. In P002 representative 262, #0 is
5.46 pixels from the reference while #2 is 391.67 pixels away. The earlier
agent inspection describes ball-region and seating-region alternatives,
respectively. Surviving candidates can still lose at final path choice; a
retention change alone does not establish better output. P003 challenge 170
similarly preserves weak #148 at 6.92 pixels and emitted #0 at 494.23 pixels,
alongside the hidden and subsequent reacquisition controls.

## Bounded output and evidence

The approved scope is exactly 32 existing development frames, 82 cataloged
candidates, 640 saved display outcomes and fifteen cap records. Candidate-level
dispositions use only the corresponding detector's settings: 56 RF candidates
times eighteen settings plus 26 YOLO candidates times two settings gives
1,060 records. The frame-level outcomes remain 410 emissions and 230 explicit
abstentions. These repeated settings are not independent samples.

The completed output is in a fresh ignored directory:
`data/outputs/ball_tracking/candidate_retention_localization_diagnostic/v0_1_9fe6a1ef86d2/`.
Its three files are `case_ledger.json`, `summary.md` and `integrity.json`.
The existing final gallery remains
`data/outputs/ball_tracking/weak_candidate_inspection/9fe6a1ef86d2/review_native.html`.
Ryan's completed twelve-clip final-frame review remains complete; no repeat
review or new human identity judgment is claimed.

The helper verifies the original 231 asset bindings and 177 input bindings,
saved report/selector pointers, candidate mappings, crop-local provenance and
actual RF/YOLO inference commits. Optional absent cap membership stays unknown;
a contradictory bound hash or record fails. Outputs are create-only. The
creation HEAD and exact uncommitted helper/test hashes are separate from the
original detector inference commits. The branch, HEAD, index and helper bytes
must remain stable during execution.

All fifteen optional cap-membership bindings were available and verified:
eight reject the original floor-match candidate and seven retain it. The
independent audit compared all 82 original candidate payloads, 640 saved
outcome/report/trace records and 1,060 corresponding candidate dispositions.
It independently recomputed the reference distances and rehashed every bound
input and output. The 231 original assets and 177 original inputs are unchanged.

| Completed artifact | SHA-256 |
| --- | --- |
| `integrity.json` | `a15e99a163ee169a38ac37097d3e1ca6b3a4fa827e016b8bc89bddd037f51326` |
| Diagnostic implementation | `12adbe87c83f3f801e7bf76e06d6ea31210c539cec84138c5d6b717e00d93f82` |
| Focused tests | `ecdfcfd516e756cfd5294680d84a08d7345857205a80f3eb91e09634196e5120` |

The integrity file binds the ledger and summary hashes, all source records,
resolved JSON pointers and both execution checkpoints. Its creation HEAD does
not claim to contain the uncommitted helper or replace any inference commit.

## Validation and continuation

The 28 focused synthetic tests pass. They exercise ledger assembly and output,
original indices that differ from array positions, RF/YOLO crop schema and
mixed inference provenance, hidden nulls, uncertainty, separate threshold/cap
losses, contradictory hashes/pointers, missing optional membership, approval
bindings, fixed scope and refusal to overwrite prior output.
The full suite ran 520 tests: 519 passed and one existing Windows
directory-symlink capability test was skipped. Helper and test bytes stayed
unchanged throughout validation and execution. `git diff --check` passes.

Validation logs and the separate output-audit helper are under
`data/outputs/ball_tracking/candidate_retention_localization_implementation/9fe6a1ef86d2_2026-10-02/`.
`final1_tests.json`, `execution_receipt.json` and
`independent_output_audit.json` document completed commands and exact hashes.
Execution returned zero and produced only the three planned diagnostic files.

We remain in the ball-tracking foundation phase; possession understanding and
defensive scoring are later milestones. The next design decision is how to
compare candidate retention while exposing the extra clutter it may admit.
The evidence can support preparing a bounded retention comparison only after
its candidate-load, false-alarm and missingness tradeoffs are specified. The
localization cases remain a separate question. Useful retained candidates lost
at path choice require their own path/cost evidence before another tracking
rule is justified. Any future comparison must include gains and regressions
across all six development windows, with representative and challenge pools
separate. This diagnostic selects no method, threshold or quality gate.

A learned verifier still requires a separate reviewed identity definition and
a defensible training/evaluation split. These inspected frames are selected
development evidence, not an unbiased training or validation sample. All nine
original prediction embargoes and the three sealed holdouts remain protected.
No reviewed player decision changes and no `--rerun-from` stage is needed.
Staging, committing, pushing, PR creation and merging remain separately
unauthorized. No manual command is pending.
