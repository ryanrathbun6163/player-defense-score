# Candidate-quality continuation: crash after driver replacement

October 28, 2026. Ryan explicitly approved the prepared attempt003, readiness
checks, the remaining 49m6s, monitoring and no automatic retry. It ran on verified
NVIDIA 617.42 with both RAM modules configured at 5200 MT/s, then Windows crashed
and rebooted. **The new Windows record confirms 0x116 / VIDEO_TDR_FAILURE and
names nvlddmkm.sys.** Driver replacement and the memory change did not prevent
recurrence. The underlying cause remains unresolved. No further GPU attempt ran.

## What the records establish

All times below are Phoenix on October 28:

| Time | Evidence |
| --- | --- |
| 16:17:41.380 | Supervisor policy created; startup counts against the approved budget. |
| 16:19:41 | Restored epoch-two parameters, AdamW and CUDA RNG checks pass. |
| 16:20:33.745 | Epoch-three checkpoint saved. |
| 16:21:09.856 | Epoch-four checkpoint saved. |
| 16:21:35.874 | Last successful NVIDIA sample: 60 C, 2,843 MiB, 146.47 W. |
| 16:21:38.246 | NVIDIA telemetry fails; supervisor creates STOP. |
| 16:21:53.263 | Cleanup reports “Owned launcher did not signal exit.” |
| 16:22:25.500 | Windows boots again. |
| 16:22:44 | System bugcheck receipt reports 0x116, C000009A and fourth parameter 4. |

The final supervisor receipt is 494 NUL bytes. Neither clean process exit nor
pre-reboot cleanup is certified. No worker completed/failed receipt exists;
their absence does not make the run successful. The post-reboot process snapshot
contains no Python worker. STOP cannot guarantee recovery of a failed graphics
driver or Windows. There was no automatic retry.

The bounded Windows query successfully inspected 156 System and 41 Application
events. System 1019 names NVIDIA; Kernel-Power 41 independently records decimal
278 (=0x116). Three Application BlueScreen receipts share one report ID and
represent one crash. No matching WHEA/resource-exhaustion provider event was
observed. Event6008's embedded 15:54:30 timestamp is not used as this crash time.
The dump's internal crash time has not yet been read.

Across 116 valid telemetry samples, peaks were 62 C, 2,968 MiB and 158.05 W.
These samples show neither thermal-limit operation nor full GPU memory. They
cannot exclude transients, unmeasured temperatures, power delivery or hardware
faults. Both 32 GB modules still report 5200 after reboot; signed Windows NVIDIA
32.0.16.1742 agrees with the 617.42 launch check. EXPO disabled and the installer
clean-install selection retain their previously stated observation limits.

Microsoft defines 0x116 as failed graphics timeout recovery; it can involve
driver behavior, configuration or hardware. The visible reboot differs from
attempt002's recorded 141 engine timeout, while belonging to the same failure
class as earlier 0x116 crashes. Naming NVIDIA does not identify a defective GPU,
and C000009A does not identify which resource failed.
[Microsoft 0x116](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x116---video-tdr-failure),
[Microsoft timeout recovery](https://learn.microsoft.com/en-us/windows-hardware/drivers/display/timeout-detection-and-recovery).

## Saved progress and honest accounting

The standard-library partial CPU audit passes 3,474 recorded checks. It verifies
all 82 previous worktree bindings, the original 45/prior 10/new 22 frozen inputs,
33 preserved prior-attempt files, journal order, checkpoint links and ZIP CRCs.
Its first execution failed parsing the corrupt final receipt; that failed audit
and original helper are preserved. A separate helper records corruption and
permits partial accounting only; complete mode still rejects that receipt.
No Torch, GPU query, neural forward or optimizer update ran in this recount.

- Attempt003 recorded 1,015 returned updates / 32,452 training presentations.
- All 213 replayed updates exactly matched the earlier recorded loss and gradient
  norm. This is a limited observed comparison, not general cross-driver identity.
- Logical progress reached update 1,763; the epoch-four checkpoint retains 1,496.
- The later 267 recorded updates / 8,544 presentations are unsaved.
- Across all attempts, durable physical lower bounds are 2,063 returned training
  updates / 65,960 training presentations, plus the original parity call / 32
  presentations. Unjournaled work remains unknown.
- No full fit, scoring result or scientific comparison completed. Online training
  loss is not evaluation, and no model is adopted.

The latest checkpoint is
`data/outputs/ball_tracking/candidate_quality_pilot_v0_1/attempt_003/leave_chi_out/recovery_epoch_04.pth`,
43,271,723 bytes, SHA-256
`6d37ee0184b68fb08a12ca0fa4bb686f8ba7353e7cafe01282f8dfc620ee15f0`.
All 176 ZIP member CRC checks pass. Its tensor/optimizer semantics have not been
audited; the earlier epoch-two semantic audit does not cover this new checkpoint.

With cleanup uncertified, conservatively debit policy creation through verified
reboot: ceil(284.120448) = 285 seconds. Prior debit 654 remains, giving 939 consumed
and **2,661 seconds (44m21s) remaining**. No previous debit is refunded. Remaining
time is not authorization to retry. Already incurred replay overhead remains
300 updates; any future replay of the newly unsaved 267 must be additional and
explicitly accounted, not silently erased or charged as already executed replay.

## Reading, next diagnostic and limits

Reuse the completed Sessions1–16 history/research review, selected foundation
evidence, previously read complete Session17/18 handoffs and the subsequent
candidate comparisons/capture and frozen pilot. This incident changes execution
status, not scientific recipe or evaluation interpretation. Relevant maintained
current-state, source-map, validation, decisions, agreement and roadmap entries
were consulted; targeted reads covered the prepared continuation, previous
interruption/dump reports and history review, actual new journals/telemetry,
Windows XML and independent recount. Microsoft primary TDR documentation was
reopened. No fresh all-transcript or every-paper reread is claimed.

The earlier history includes crashes before this pilot/current driver and outside
training; app isolation and successful short workloads did not establish a cure.
Now 5200 MT/s plus Studio617.42 also failed to prevent recurrence. This weakens a
single memory-profile or old-driver explanation, without excluding memory,
driver behavior, GPU/PCIe, power or firmware. No new settings intervention,
stress test, driver change or training variation is proposed by this record.

The bounded next step is local analysis of the new crash dump against the already
analyzed earlier dumps. Windows lists
`C:\Windows\Minidump\102826-18968-01.dmp` (7,841,199 bytes), but ordinary content
access is denied. An administrator must copy it into the ignored incident folder;
the prepared `copy_crash_dump.ps1` checks branch/HEAD/empty index, expected size,
non-overwrite and source/copy SHA equality. It is syntax-checked, not executed.
It changes no driver, BIOS, permissions or startup setting and uploads nothing.
New dump internals may refine the comparison; repeating the same TDR stack alone
would not isolate the faulty component. Further GPU execution remains stopped.

NBA stays the goal and cosine nine the research control. All weak/native,
agreement/disagreement, hidden, uncertain and missing cases remain in scope;
point gains and adverse e01/visibility/history are preserved. Accepted labels,
quality and human-review gates, protected closure and no selector/adoption stand.

## Evidence and preservation

Ignored incident evidence is under
`data/outputs/ball_tracking/candidate_quality_pilot_v0_1/post_driver_recovery_preparation_v0_1/attempt003_interruption_v0_1/`:
Windows events and 20 XML records, post-reboot snapshot, dump-access failure,
prepared copy script, additive document snapshots and verification. The parent
preparation folder contains the failed/passing partial audits, their helpers,
the explicit execution approval, corrected path-format failure, launch readiness
and graphics-isolation records. Raw attempts, freezes and receipts stay intact.

Branch remains `codex/ball-detector-baseline`, HEAD
`8c040fca385dd8fffa0d7a13c45c53e79950bae1`, empty index. All 82 prior worktree
contents, including the original Session17 preservation chain, remain recoverable
exactly beneath additive context updates. No staging, commit, push or merge.
