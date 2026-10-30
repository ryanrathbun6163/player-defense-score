# Native cable replay with Debug Mode ON: prepared revision

October 29, 2026. **Configuration selected; no setting changed or workload
launched.** Ryan clarified that OFF was only the default and permits choosing
the experiment configuration. The earlier instruction to prepare without
launching still applies. This revision supersedes the unrun OFF preparation for
the next proposed diagnostic; all of that preparation remains intact.

## Why ON

The earlier epoch-two diagnostic failed while Debug Mode was directly observed
ON. Restoring that setting gives a better comparison after changing the physical
cable path. NVIDIA states that [Debug Mode uses reference clocks and disables
factory/manual overclocking](https://nvidia.custhelp.com/app/answers/detail/a_id/5802/).
It is not a claim that Debug Mode fixes the issue: the earlier ON failure remains
the comparator.

| Configuration | Previous failed diagnostic | Prepared replay |
| --- | --- | --- |
| GPU cable route | Previous breakout cable and ASUS adapter, per later user handoff | Original Corsair native cable, per user handoff |
| Debug Mode | Observed ON | ON required before launch; not yet applied/observed here |
| Driver / RAM / power limit | 617.42 / 5200 MT/s / 250 W | Same |
| Workload | Audited epoch-two state, first fit | Same state and recipe |
| Maximum duration | 600 seconds | 600 seconds |

OFF would be reasonable for a later test of ordinary default operation. It is a
weaker comparator here: attempt004's Debug Mode state was unknown and it started
from epoch four. No power cap, driver/firmware installation, memory adjustment or
other tuning is added. Those diagnostic alternatives remain unrun.

Matching the setting does not establish identical measured clocks. The cable
change also reseated contacts and removed an adapter; reboot and background state
can vary. A short pass would show successful exposure under this configuration,
not prove a particular cable/adapter defect or lasting stability. A failure would
leave the cause unresolved. Neither outcome automatically launches another test.

## Evidence actually used

Reused the completed Sessions 1–16 historical/research review, selected foundation
evidence, Session 17/18 handoffs and subsequent scientific records. Revisited the
maintained source map, validation history and current decisions, the actual
observed-ON UI record, failed diagnostic receipts and audit, attempt004's unknown
clock-mode record, and the prepared cable intervention protocol. NVIDIA's primary
Debug Mode guidance was freshly read. This is not a fresh all-transcript or
every-paper reread, nor a repetition of completed experiments.

The [original cable protocol](ball_tracking_native_cable_diagnostic_2026-10-29.md)
retains the full crash/accounting history and read-only snapshot. Its requirement
to keep OFF is superseded by this revision; its failure evidence is unchanged.
Photos and cable installation remain user/browser-reported, not independently
inspected locally. No new GPU telemetry or system observation was taken merely
to select this configuration.

## Same bounded workload and exposure

Restore `attempt_002/leave_chi_out/recovery_epoch_02.pth`, SHA-256
`49cb7ebce977266def654893e3705f0bc9d4cae80c2989369f4233944451db7f`.
Run only epochs 3–6 of the existing first fit, at most 1,496 updates / 47,816
presentations, from logical step 748 to 2,244. There is no scoring, new fit,
repeated parity forward, selector, adoption or subsequent training. Scientific
epoch four, all old checkpoints and the original 267 unsaved logical updates remain.

Prior physical expenditure remains 2,588 forward attempts, 2,587 forward returns,
2,586 optimizer updates and 82,682 optimizer-associated presentations. The
remaining original allowance is **2,287 seconds**. Preparation consumes no GPU
attempt time; any later diagnostic is charged against that allowance. NBA,
cosine-nine control, accepted labels, full weak/hidden/uncertain/missing coverage,
adverse point/e01/visibility/history evidence and protected closure remain intact.

The tested supervision logic is retained: two-second telemetry, a separate
Windows event watcher, STOP at 570 seconds, hard exit at 600 including startup
and cleanup, and an independent 30-second fault/operator-stop guard. Only the
owned process groups are terminated. Unknown cleanup remains a failure; no
software guard guarantees Windows kernel or graphics-driver recovery.

## Future readiness and commands

The last reported actual state was OFF. Before a separately authorized launch,
observe Debug Mode ON in NVIDIA App or obtain Ryan's direct observation. The
setting is at **NVIDIA App → System → Advanced → Debug Mode**. Record any toggle
as the sole permitted setting change. Fresh readiness must also verify 617.42,
the expected GPU, 5200 on both RAM modules, 250 W, no conflicting graphics apps
or GPU workers, and a timestamp no older than 120 seconds. The earlier Lively
snapshot is not launch readiness. No apps were closed during this revision.

The new output directory is
`data/outputs/t/native_cable_reference_diagnostic_2026-10-29_v0_2/`.
Worker outputs go to `attempt_001/`, GPU logs to `monitoring/attempt_001/`,
Windows logs to `events_attempt_001/`, and outer timing/cleanup to
`launcher_started.json` / `launcher_finished.json`.

Future launch command, **not run**:

```powershell
& 'C:\Users\Ryan\Projects\player-defense-score\.venv\Scripts\python.exe' -B -u 'C:\Users\Ryan\Projects\player-defense-score\data\outputs\t\native_cable_reference_diagnostic_2026-10-29_v0_2\run_supervised.py'
```

Stop a later approved run from another PowerShell window:

```powershell
& 'C:\Users\Ryan\Projects\player-defense-score\.venv\Scripts\python.exe' -B 'C:\Users\Ryan\Projects\player-defense-score\data\outputs\t\native_cable_reference_diagnostic_2026-10-29_v0_2\request_stop.py'
```

Configuration selection is recorded separately from actual system state and
execution approval. The future launch receipt may record only the permitted
Debug Mode change; launcher/worker receipts state that those processes themselves
do not modify settings. Missing approval blocks launch before Torch import.
Original OFF artifacts remain frozen, unrun historical preparation. Current
revision test, independent-review, freeze and preservation receipts live in the
new directory. No Git integration is authorized or performed.
