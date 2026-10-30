# Candidate-quality pilot: recovery after the memory change

This specifies recovery of the already-approved four-fit pilot. Ryan reported
setting DRAM frequency to 5200 and disabling EXPO Profile 1, then said
**"ok do that please chat"** after the explanation of checkpoint recovery within
the remaining 52 minutes 6 seconds and GPU monitoring. This is a directed
continuation of the same experiment, not an automatic retry or a fresh hour.
Implementation and verification precede launch; this specification alone is
not a claim that recovery has run or that the computer is now stable.

## Evidence and unchanged decision

Reuse the full-history/research reconciliation in the
[original protocol](ball_tracking_candidate_quality_pilot.md), including the
completed Sessions 1-16 review, selected foundation evidence, complete Session
17/18 handoffs and subsequent capture/comparison results. This recovery reads
the maintained source map, validation history, current decisions/agreement and
roadmap; the actual frozen worker/model, proposal, approval, supervisor/guard,
checkpoint audit, initial runtime records, crash analysis and new memory-change
snapshot. It does not repeat completed experiments or claim a fresh reading of
every transcript or research paper. No new scientific direction is introduced.

The [interruption](ball_tracking_candidate_quality_pilot_interruption.md) left
one valid completed epoch. The [dump analysis](ball_tracking_crash_dump_analysis_2026-10-28.md)
identified recurrent NVIDIA timeout recovery failure without establishing its
underlying cause. Windows now reports both 32 GB modules at 5200 MT/s; EXPO off
is Ryan's BIOS observation. A successful boot and cool idle GPU do not establish
load stability. Driver and hardware alternatives remain open if the fault recurs.

NBA remains the target, cosine nine the research control. Preserve the fixed
four six-epoch fits, crops, point features, optimizer, batch order, uncertainty
masks, all native/weak/hidden/missing cases, 960 HOU frames, seven old arms and
6,720 contrasts. Preserve adverse e01/visibility/history alongside useful point
information. HOU stays excluded from fitting; DET retains only its original
fixed diagnostic queries. No selector, threshold fitting, labels, protected
evaluation, model adoption, extra benchmark or stress test follows.

## What is restored

The original `attempt_001` and its corrupted supervisor receipt remain untouched.
The additive recovery worker writes only a new `attempt_002` and a separate
supervisor directory. Original frozen source, configuration and approval remain
unchanged; a supplementary freeze binds the recovery implementation and source
checkpoint to them.

Restore `leave_chi_out/recovery_epoch_01.pth`, SHA-256
`fad2666942384ef3131ac946a230564d1ef947f299d21b1c82afd59e9bbcdb84`:
epoch one, 374 optimizer updates and 11,954 training candidate presentations.
Restore all trainable parameters, AdamW state and Python/NumPy/Torch/CUDA RNG
state. Reconstruct the same frozen prefix from pinned original weights and
require its fingerprint to agree with the first attempt. Validate restoration
before any further update. Start this fit at epoch two; initialize the other
three fits using the unchanged original seed and recipe.

The first fit's successful producer parity and gradient checks are retained by
binding. They are not rerun as a new scientific experiment. Each later fresh
fit still performs its declared first-batch parity and gradient check. All
final frozen-tensor, trained-group and exact population checks remain required.
Only final epoch-six checkpoints enter the comparison. Restoration preserves
the saved state; it does not prove hypothetical uninterrupted GPU execution
would be bit-identical without a separate comparator run, which is not proposed.

## Resource accounting and stop behavior

Keep logical progress and physical expenditure separate:

| Quantity | Preserved checkpoint | New work if completed | Cumulative physical lower bound |
| --- | ---: | ---: | ---: |
| Training updates | 374 | 9,496 | 9,957 |
| Training candidate presentations | 11,954 | 303,478 | 318,216 |
| Producer parity forwards | 1 | 3 | 4 |
| Scoring forwards | 0 | 1,572 | 1,572 |

The original journal records 87 additional unsaved updates / 2,784 candidate
presentations after the saved epoch. They are recomputed to continue from the
available state and remain charged as previously consumed physical work. Full
logical training remains 9,870 updates / 315,432 presentations; the extra 87
are recovery overhead, not additional epochs or a changed recipe. Original
crash records are durable lower bounds; unknown unflushed work stays unknown.

The existing conservative 474-second debit remains. The continuation receives
**3,126 seconds total**, measured from the new supervisor's policy creation,
including startup/preflight/cache preparation. Request STOP 30 seconds before
that absolute deadline to leave room for telemetry polling and owned-job
cleanup. The existing supervisor samples every two seconds, stops at 80 C or
thermal/device failure, and owns only its worker process tree. No further
automatic retry or budget extension is permitted after a stop or crash.

Immediately before launch verify the new memory configuration, original and
recovery bindings, empty index, current branch/HEAD, GPU telemetry and absence
of old workers. Temporarily restore the previously authorized graphics-extra
isolation; record what was actually stopped and leave startup settings intact.
Inspect new Windows graphics/hardware events during the active continuation.
Any renewed graphics fault stops this attempt and returns to diagnosis; do not
use repeated launches as a stability test.

## Records

`data/outputs/ball_tracking/candidate_quality_pilot_v0_1/recovery_preparation_v0_1/`
contains the supplementary freeze, user authorization, focused CPU checks,
independent review and prelaunch readiness. Generated outputs stay ignored.
The original 75 worktree paths are preserved through additive documentation;
new recovery code/tests are separate files. Branch and HEAD stay
`codex/ball-detector-baseline` /
`8c040fca385dd8fffa0d7a13c45c53e79950bae1`. No staging, commit or publication is
included. A completed fit, partial continuation and accepted deployable result
remain distinct outcomes.
