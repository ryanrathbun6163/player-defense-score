# Native GPU cable: prepared diagnostic, October 29, 2026

**Prepared for review; no GPU workload launched.** Ryan requests one replay of
the existing training loop after a physical cable change, capped at ten minutes.
Keep Debug Mode OFF. This is a diagnostic exposure, not continuation of the
four-fit scientific comparison. No automatic retry or subsequent training follows.

## Evidence read and reused

Reuse the maintained source map, decisions, validation history and agreement,
the completed Sessions 1–16 historical review (398 available turns / 47 pages),
selected foundation evidence, previously read Session 17/18 handoffs, and the
subsequent weak-response, point, candidate-change, capture and pilot records.
This turn directly inspected the original recovery and diagnostic producers,
attempt004 receipts and journals, checkpoint audits, supervision code, current
read-only system observations and Ryan's browser handoff. This is not a fresh
all-transcript or every-paper reread. No completed scientific experiment was
repeated to prepare the replay.

The scientific recipe remains fixed. NBA footage is the goal; cosine nine is
research control. Preserve the complete weak, native, hidden, uncertain and
missing populations, useful point information and adverse e01/visibility/history
evidence. No new labels, selector, trajectory, model adoption or protected
evaluation are part of this diagnostic.

## The final pre-change retry failed, but cleanup completed

Ryan explicitly directed one more unchanged training attempt. Attempt004 started
at 13:09:41.396 Phoenix and its launcher finished at 13:12:10.868 on October 29.
It restored the scientific epoch-four checkpoint and attempted epoch five.
NVIDIA telemetry failed. The worker caught KeyboardInterrupt at gradient
clipping; that is the interruption location, not an identified fault origin.

The independent saved-output audit passed 507 checks, plus 54 checks separating
neural forwards from optimizer updates. There were 83 returned neural forwards
but only 82 completed optimizer updates: 2,656 forward-associated presentations
versus 2,624 update-associated presentations. All 82 updates exactly match the
previously recorded loss/gradient pairs. No new checkpoint, completed fit or
scores were produced. The scientific epoch-four checkpoint still retains 1,496
updates, and the original 267 unsaved logical updates remain. The additional
82 replay updates are physical expenditure, not 82 distinct new logical steps.

Unlike the earlier Debug Mode failure, attempt004's actual final receipts certify
zero remaining owned workers, no job-cleanup error and zero remaining event
watcher processes. Its 149.469-second outer runtime is rounded up to 150 seconds,
leaving **2,287 seconds (38 minutes 7 seconds)** of the original allowance.
Prior failures and conservative debits remain intact. Sampled peaks were 54 C,
2,716 MiB and 145.73 W; they do not identify the cause or exclude transients.

Evidence: `data/outputs/t/training_retry_2026-10-29_v0_1/postrun_audit/`
contains `attempt004_partial_audit_001.json` and
`attempt004_forward_accounting.json`. The original attempt004 receipts remain
in the pilot and retry directories.

## Physical intervention and configuration limits

Ryan reports that the original Corsair RM850e 2025 native 16-pin-to-16-pin cable
now connects directly to the RTX 5070. The previous Corsair breakout cable and
ASUS two-8-pin-to-16-pin adapter were removed. Browser-reviewed photographs
showed no obvious heat damage, and Windows boots normally. Those are user-supplied
findings; the photographs were not independently inspected in this local turn.
No specific cable fault has been proven.

Ryan reports NVIDIA App Debug Mode OFF at 14:17 and instructs us to keep it off.
The last reference-clock diagnostic had Debug Mode observed ON; attempt004's
mode was unverified. This is not an identical-configuration cable-only comparison.
Changing the route also reseats contacts and removes an adapter, and a reboot
occurred. A short pass would show successful exposure under the new configuration,
not prove the former cable caused the faults or certify hardware health.

## Read-only preparation snapshot

At 14:25 Phoenix, NVIDIA telemetry returned the expected GPU UUID and driver
617.42, with 35 C, 1% utilization, 1,569 / 12,227 MiB and 7.89 / 250 W.
Windows reports both 32 GB modules configured at 5200 MT/s. The separate SMBIOS
Speed=5600 field is not the configured operating speed. Boot was 14:11:49.500.
EXPO state is not independently inspected here.

Lively was running as PID 28740. MSI True Color and Python workers were absent;
other MSI services remain. No application was closed and no setting changed
during this preparation. Launch must freshly verify the prior isolation policy;
the current snapshot is not permission to launch with Lively running.

The event query found the later boot's Kernel-Power 41 and two delayed 0x1B8 WER
records referencing 13:12 WATCHDOG4400/4401 filenames, marked BAD_DUMPFILE. These
are not established new post-cable faults. Microsoft documents 0x1B8 as a
[black-screen live-dump identifier](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x1b8--video-miniport-black-screen-livedump),
not a fatal bugcheck code. The repeated AAAA parameters do not resolve its trigger.
No new 0x116 is established for attempt004, and these dumps were not opened.
Two MigrationService APPCRASH registrations are retained separately, without a
causal claim. The new watcher includes 0x1B8 and deduplicates exact prior report IDs.

## Frozen replay scope

- Restore the previously audited epoch-two checkpoint from
  `attempt_002/leave_chi_out/recovery_epoch_02.pth`, SHA-256
  `49cb7ebce977266def654893e3705f0bc9d4cae80c2989369f4233944451db7f`.
- Run only the same `leave_chi_out` fit, epochs 3–6, from logical update 748
  through at most 2,244: maximum 1,496 new updates / 47,816 presentations.
- Preserve the exact model, data, order, optimizer, batch size and deterministic
  recipe. No scoring, repeated producer-parity forward, second fit or tuning.
- Put all diagnostic checkpoints in the new diagnostic directory. They do not
  replace the scientific epoch-four state or complete the scientific comparison.
- Stop at the fixed endpoint or the first stop condition, whichever comes first.

All replay work counts as exposure. Prior physical lower bounds are 2,588 forward
attempts, 2,587 forward returns, 2,586 optimizer updates and 82,682
optimizer-associated presentations. A complete replay would add at most 1,496
updates / 47,816 presentations. The ten-minute maximum is charged against the
remaining 2,287 seconds; no fresh hour is created. Nothing is charged for an
unrun GPU attempt. Unknown work remains unknown.

## Timeout, fault and cleanup handling

The existing supervisor owns its worker process tree in a Windows kill-on-close
job. Telemetry samples every two seconds with a five-second query timeout. The
separate owned event watcher checks new Windows graphics, WHEA and resource
faults. Stop conditions include telemetry failure, 80 C, thermal or hardware
power-brake flags, a new relevant event, watcher failure or an operator request.

The launcher uses monotonic elapsed time from entry, including startup and cache
reconstruction. It requests STOP at 570 seconds and exits at 600 seconds. The
hard deadline stays armed through final receipt writing. A separate guard latches
a detected fault or operator stop before STOP-file I/O and exits the launcher
after at most 30 seconds if cleanup stalls. Closing the launcher closes both
owned job handles. The existing ten-second graceful interval precedes forced
termination of only the owned worker job when necessary.

These are user-space guards. A kernel-stuck GPU process or Windows failure can
prevent certified cleanup. Missing/corrupted final receipts, nonzero/unknown
worker counts or cleanup errors remain failures; no success or safe cleanup is
inferred merely because the launcher disappeared. No driver reset, TDR change,
blanket Python termination or automatic retry is included.

## Commands and outputs for review

The exact future launch command is below. **Do not run it yet.** Preparation
deliberately leaves `execution_approval.json` and `launch_readiness.json` absent;
the launch gate rejects their absence before Torch import or worker creation.
After explicit execution direction, a fresh UTC readiness receipt must be at
most 120 seconds old and verify the expected driver/GPU, RAM, app isolation,
no existing worker, and Debug Mode still OFF. The user/UI observation basis is
recorded. Earlier approvals cannot authorize this new diagnostic.

```powershell
& 'C:\Users\Ryan\Projects\player-defense-score\.venv\Scripts\python.exe' -B -u 'C:\Users\Ryan\Projects\player-defense-score\data\outputs\t\native_cable_diagnostic_2026-10-29_v0_1\run_supervised.py'
```

During a later approved run, request STOP from another PowerShell window:

```powershell
& 'C:\Users\Ryan\Projects\player-defense-score\.venv\Scripts\python.exe' -B 'C:\Users\Ryan\Projects\player-defense-score\data\outputs\t\native_cable_diagnostic_2026-10-29_v0_1\request_stop.py'
```

The helper creates only this diagnostic's operator/STOP markers. It handles
startup before monitor creation, refuses a different module, and never kills
unrelated processes. Leave the launcher to write cleanup receipts. If Windows
itself freezes, software cannot guarantee a working stop command; no automatic
restart follows after recovery.

All new outputs are beneath
`data/outputs/t/native_cable_diagnostic_2026-10-29_v0_1/`:

- `attempt_001/`: worker journal, diagnostics and separate recovery checkpoints;
- `monitoring/attempt_001/`: GPU telemetry, console, policy and cleanup receipt;
- `events_attempt_001/`: Windows event baseline, polls, faults and final receipt;
- `launcher_started.json` / `launcher_finished.json`: outer timing and status;
- preparation proposal, intervention/readiness observations, freeze and review.

Preparation reused the earlier 5,056-check CPU epoch-two audit and revalidated
its hash bindings. Ten focused worker tests, four owned-cleanup fault injections
and 57 launcher/deadline/event/operator checks pass. The latter checks use
captured event evidence and mocked system operations, not a GPU stress test.
Exact final preparation and missing-approval preflight results are recorded
under this directory. Original contents and Session 17 preservation remain;
no staging, commit, push or protected evaluation occurred.
