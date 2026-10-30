# Proposed recovery of the interrupted YOLO11x comparison

Status: **proposed, not approved, not executable**. This document and its JSON
companion describe a contract change for Ryan to review. They do not authorize
the v0.2 recovery implementation, another model call, or a Git operation.
The two-file native-validator fix is already prepared and synthetically tested
in unstaged work. The v0.2 recovery implementation has not started; approval of
this proposal would authorize that recovery design and use of the correction
for the remaining units, subject to the execution and Git conditions below.

The original run at commit `116e3ed9cb4113521fa8c93adf4a100fea4dc0ec`
completed 175 of the 600 crop units. Both failed attempts occurred at P001
challenge frame 218, bottom-right crop. Native postprocessor row 55 had zero
height at the crop's top border, with confidence approximately `8.8e-7`, below
the frozen .01 export floor. Its full generated row remains in the ignored
failure diagnostic. The adapter rejected this native provenance row;
the failed crop had **zero exported candidates**. A trace-only ordinary resume
confirmed the same failure without changing the committed validator.

The independent partial-run receipt verifies 175 unchanged crop checkpoints,
177 actual project attempts/forwards, two failed attempts, two predictor
preparations and four synthetic startup forwards. One completed candidate
window and its 27 selector files remain saved. The original scoring and review
stages have not completed. The receipt also verifies the 98 protected tracked
files and confirms that all nine original embargo paths remain absent.

## The prepared validation correction

Preserve every finite, in-bounds, non-reversed native row in its original return
order, including a zero-width or zero-height row **only when its confidence is
strictly below .01**. Such a row remains provenance and never becomes an
exported ball detection. Every exported row, including exactly .01, must still
have positive width and height. Negative, reversed, out-of-bounds or nonfinite
geometry, invalid confidence, wrong class and changed order still fail.

This changes validation of discarded native rows. It leaves the detector,
weights, runtime, preprocessing, class mapping, NMS, cap, export floor, scores,
cross-crop duplicate retention and selector rules fixed. It does not turn the
failed row into a ball observation or change a scoring threshold.

## Resume only the missing work, with truthful provenance

The companion JSON binds the original experiment, approved proposal, runtime,
execution commit, failure diagnostic and partial-run receipt. It lists each of
the 175 completed checkpoint paths, hashes and unit identities, all 177 paired
attempt receipts, two paired preparation receipts, the completed candidate
file and all 27 existing selector files. All these files stay byte-identical.

The recovery uses a separate subtree:
`data/outputs/ball_tracking/detector_challenger/yolo11x_crop_development_comparison_v0_1/recovery_v0_2`.
It consumes the 175 completed checkpoints without GPU calls and executes only
the exact 425 missing units listed in the proposal. Frame 218's failed
bottom-right unit is one of those 425. The diagnostic's captured raw return is
not promoted to a completed checkpoint; its two failed attempts stay recorded.
Every completed recovery unit receives an immutable checkpoint and retains its
actual inference commit and preparation/attempt receipts.

The original v0.1 schema has one detector code commit for an entire candidate
window. That cannot truthfully describe a window mixing old and corrected
execution. New v0.2 candidate files therefore bind the original checkpoint and
actual inference commit **for every crop unit**, plus a separate assembly
commit identifying the code that joined them. The 175 old units keep commit
`116e3ed9cb4113521fa8c93adf4a100fea4dc0ec`; future units name the separately
authorized clean recovery commit. No copied checkpoint is relabeled.

The shared typed evaluation view may retain a single `ModelProvenance.code_commit`
for compatibility only if its role is explicitly **assembly-view provenance**.
It must never be presented as the actual inference commit for every unit.
Candidate, selector, score and review records must carry the complete per-unit
inference inventory or its exact binding, an explicit mixed-provenance role,
and the assembly/selection/evaluation/rendering commits separately. A new
single `detector_code_commit` claim is not sufficient.

Assemble six new candidate files from the 175 reused and 425 new units. Derive
all 162 simple selector outputs in the recovery subtree, including new derived
views of the completed first window; preserve the original 27 selector files.
This derivation uses saved candidate JSON and never reruns completed inference.
The completed first window must retain identical candidate geometry, scores,
ordering, duplicate provenance and emitted indices in every corresponding
selector, despite the explicitly different assembly metadata.

## Frozen comparison and honest counting

Keep the same six development windows, 150 bound unmarked source PNGs and four
crops per frame. Keep the nine confidence thresholds, five source-pixel radii,
all/top-one/top-twenty selectors, finalized labels and separate representative
and challenge pools. Produce 810 new scoring reports and reuse the exact 810
saved RF-DETR control reports. Each separate pool has 135 new and 135 reused
aggregate cells. Do not rerun any RF-DETR inference, selection, scoring or
rendering.

Prepare the same twelve paired 25-frame clips at 5 fps, at .20/.35 and radius
10, plus native YOLO overlays and source-scale closeups. Reuse the same 1,200
original control/source PNG references. There are 1,500 new PNGs and 12 new
clips. New headers and legends explain the actual inference commits and the
assembly role without implying a calibrated probability or a selected method.
Ryan's visual review of every new clip through its final frame remains pending.

| Accounting item | Preserved | Proposed recovery | Combined if no further retry |
| --- | ---: | ---: | ---: |
| Completed unique crop units | 175 | 425 | 600 |
| Actual project attempts/forwards | 177 | 425 | 602 |
| Failed project attempts | 2 | 0 expected | 2 |
| Predictor preparations | 2 | 1 expected | 3 |
| Synthetic startup forwards | 4 | 2 expected | 6 |

The last column is a conditional expectation, not a result or a cap. Additional
failures, retries or fresh predictors must add their observed counts. Unique
units, project attempts/forwards and synthetic forwards remain separate.

## Conditions before implementation and execution

Approval must bind this exact recovery contract and its frozen inventory.
Implementation must reject missing, extra, duplicate, changed or mis-scoped
checkpoint bindings before constructing a model; a changed original runtime or
source inventory is a contract mismatch. Interrupted new recovery work must
reuse completed new checkpoints without repeating their GPU calls.

Synthetic tests must cover the below-floor zero-area boundary, strict exported
geometry, mixed-commit provenance, both preserved and new checkpoint resume,
exact 175/425 scope, truthful attempt totals, unchanged first-window candidate
and selector semantics, label isolation during inference, report provenance,
unchanged controls and final-frame rendering. Run focused and full tests, then
obtain separate staging and commit authorization. Real recovery requires that
clean tested commit and the exact recovery approval. This proposal does not
authorize staging, committing, pushing, a PR or merging.

All nine original prediction embargoes and the three sealed holdouts remain
intact: P001 300–324, P002 200–224, P003 250–274. No additional frames, training,
model changes, parameter sweep, temporal rule, player-context rule, interpolation,
method selection, operating point or quality gate is included. These repeatedly
reviewed development windows still do not establish unseen-game generalization.

Machine-readable contract:
`configs/ball_tracking/proposals/yolo11x_crop_recovery_v0_2.json`.
Partial-failure audit:
`data/outputs/ball_tracking/yolo11x_execution/116e3ed9cb41/execution_audit.json`.
