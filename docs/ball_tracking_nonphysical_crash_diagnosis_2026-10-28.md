# Further diagnosis before physical inspection

## Next recommendation: powered-off connection photographs, 2026-10-28

Ryan asks for the best next step, explained simply, with one change at a time.
Recommend documenting the GPU power connection and actual cable route with the
computer powered off. This is a proposed visual check, not an executed physical
change. Ryan's earlier preference to exhaust useful nonphysical evidence first
is acknowledged; the latest dump comparison is now complete.

The reason is a specific evidence gap. We have verified repeated graphics faults
after reducing RAM speed, replacing the driver and enabling Debug Mode. The
actual GPU plug seating, cable/adapter route and physical PSU label have not
been independently seen. Original captured build advice incorrectly described
two 8-pin sockets on this card. The exact ASUS model has one 16-pin socket and
a supplied 1-to-2 adapter. The reported RM850e 2025 also supports a native
16-pin cable. One cable or one PSU port alone therefore does not prove a mistake.
[ASUS card specifications](https://www.asus.com/ie/motherboards-components/graphics-cards/tuf-gaming/tuf-rtx5070-o12g-gaming/techspec/),
[Corsair's exact-series manual](https://www.corsair.com/ca/en/explorer/diy-builder/power-supply-units/corsair-rme-series-2025/).

Save the instructions on a phone before shutdown. Shut Windows down, switch
the PSU to O/off and unplug AC power. Remove only the case side panel as needed.
Photograph (1) the plugged GPU connector/latch from the side, including its nearby
bend and panel clearance; (2) the visible cable path and any adapter connections;
(3) the accessible PSU exterior model label and connected ports. Keep all
internal connectors as found. Do not remove the PSU/GPU, open the PSU enclosure,
or change/reseat cables merely to obtain a photograph. If damage or deformation
is apparent, leave AC disconnected. [ASUS power-off guidance](https://www.asus.com/support/faq/1047391/).

This check can reveal a visible seating/routing/identification issue without
another load exposure. It cannot certify internal contacts, PSU output or GPU
health. If a concrete issue appears, identify the exact connection before
proposing one correction. Normal-looking photos close only the visible evidence
gap. No automatic GPU replay, reseat or cable substitution follows either result.

Alternatives remain open. A verified clean boot is a useful software-isolation
option, but changes a group of background components and needs separate exposure.
A power cap also needs load and can obscure GPU-versus-power attribution; a mild
cap may not bind a workload previously sampled at 148.5 W under a 250 W limit.
BIOS/chipset compatibility leads exist without a cause-specific fix. Memory tests
and known-good GPU/PSU substitution remain legitimate later investigations.
None is rejected as a category or executed now. The visual check is prioritized
for its concrete information gap, not a claim that power is the likeliest cause.

Reused the completed full-history/research review and subsequent incident records;
reread maintained context/authority entries, the historical review's coverage,
captured original build/cabling messages, latest dump/run evidence and relevant
firmware/hardware records, plus current primary ASUS/Corsair guidance. No fresh
full-transcript/every-paper review or new scientific-method direction is claimed.
Two internal reviews support this bounded recommendation. All scientific roles,
accepted labels, full case coverage, failures, checkpoints, Session 17 contents
and 2,437 remaining pilot seconds stand. No system change, GPU query/workload,
physical action or Git integration occurred.

[Proposed scope and evidence](../data/outputs/t/gpu_connection_visual_proposal_v0_1/proposal.json).

## Debug Mode crash dump analyzed and compared, 2026-10-28

The administrator copy is verified: `102826-18687-01.dmp`, 7,449,418 bytes,
SHA256 `36cc243e946842001499a9e62fd478a7015fe52449e646f3834c60550ff1514c`.
The copy request is fulfilled. Two local debugger passes on this new dump and
one targeted raw-context read of the prior 16:21 fatal dump exited successfully.
The earlier completed full analyses were reused rather than repeated. No dump
was uploaded; no GPU query/workload, setting change, installation or retry ran.

**The new dump confirms the same failed graphics-reset category, with a useful
change in timeout-path evidence but no identified underlying component defect.**
The internal crash time is 17:39:41.127 Phoenix, 20.291254 seconds after telemetry
failed and 5.260896 seconds after the supervisor recorded cleanup failure. These
are distinct from the next boot and Windows report-registration times.

| Fatal dump | NVIDIA build | Module-relative second argument | Shared findings |
| --- | --- | --- | --- |
| Oct 26, 08:01:03.311 | 616.56 | `+0x1935300` | 0x116, C000009A, fourth argument 4, failed graphics-reset stack |
| Oct 28, 14:05:31.131 | 616.56 | `+0x1935300` | Same broad pattern |
| Oct 28, 16:21:57.547 | 617.42 | `+0x193b450` | Same broad pattern after driver replacement |
| Oct 28, 17:39:41.127 | 617.42 | `+0x193b450` | Same broad pattern with Debug Mode observed on before load |

All four contain the same nine Windows reset-worker stack calls and offsets,
including `TdrBugcheckOnTimeout`, adapter reset and timeout recovery. The latest
NVIDIA image metadata agrees with the preceding 617.42 dump: timestamp
`6ABD8060`, image size `06D45000`, checksum `06CB596E`, file version
32.0.16.1742. The symbol `nvDumpConfig+795ee0` is an export-symbol fallback,
not identification of a private NVIDIA function that originally failed.
The earlier 16:21 watchdog 0x117 is an earlier snapshot of that same incident,
not another independent fatal crash.

### What the new comparison adds

The fatal dumps retain readable raw recovery-context memory. Both have the
`vTDR` signature and the same Windows graphics-kernel build 10.0.26100.9711.
At context offset +0x10, the preceding fatal dump contains 3 and the new one 9,
matching their respective Windows-report Tdr fields. This corroborates a change
in recorded timeout path. Microsoft's definitions are consistent with an earlier
display-flip timeout versus a GPU engine timeout promoted to a full-adapter reset
in this incident. It does not identify which engine, workload or component caused
that timeout. [Microsoft timeout types](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/d3dkmddi/ne-d3dkmddi-dxgk_tdr_type).

This remains a bounded interpretation of raw bytes and matching report fields:
the private recovery-context type is absent from available symbols. In these
actual dumps the NVIDIA owner pointer is at +0x68, unlike +0x58 in Microsoft's
older example, so that example cannot safely decode all current fields. Earlier
missing recovery-context memory referred to the watchdog snapshot; it must not
be generalized to these two fatal dumps. The new `!thread` output identifies the
System reset worker, not the originally responsible application.

The new graphics diagnostic block was extracted and matched byte-for-byte to
one location in the dump: 2,302,818 bytes, GUID
`270A33FD-3DA6-460D-BA89-3C1BAE21E39B`. Its contents differ from the prior watchdog
block, but no supported local decoder produced a causal diagnosis. The embedded
64,000-byte NVIDIA PCI ROM is exactly identical. Its power-cable warning text
remains generic firmware content, not evidence that an alert occurred. Raw
`python.exe` strings likewise do not identify a failing CUDA operation.

### What remains unresolved

The dump still cannot distinguish GPU hardware, power/contact/PCIe problems,
platform/firmware, memory-controller or software/driver interaction. Lower RAM
speed, replacement driver and Debug Mode have each failed to prevent recurrence;
none clears its whole category. Earlier crashes outside this pilot and previous
successful workloads remain relevant. The saved replay's 441 exact matching
loss/gradient pairs do not certify all software or hardware behavior.

C000009A is the last failed operation's insufficient-resource status; it does not
identify system RAM or VRAM exhaustion. Full memory/pool state is unavailable.
The PnP record is ROOT\SYSTEM\0001/code24 at 16:23:19.416, roughly 76 minutes
before this crash and near boot; it is not identified as the NVIDIA PCI device.
Loaded helpers or virtualization flags are presence evidence, not causes.
[Microsoft 0x116 interpretation](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x116---video-tdr-failure).

The earlier peak samples of 63 C and 2,525 MiB still show no sampled overheating
or full VRAM, but cannot exclude electrical transients, other temperatures or a
hardware fault. No new experiment or change is selected by this analysis. The
existing diagnostic did not pass; no further GPU execution follows. Physical
inspection remains deferred. No additional administrator copy is currently
needed for this completed comparison.

The completed full-project history/research review is reused, with the maintained
context and authority map, earlier dump reports and actual debugger logs, current
run receipts, prior watchdog payload/decoder review and targeted Microsoft
primary documentation read for this comparison. No fresh full-transcript or
every-paper reread is claimed. All 87 prior worktree contents and Session 17
preservation remain intact through additive records. Scientific checkpoints,
failures, 267 original and 67 diagnostic unsaved updates, accepted labels, full
case coverage, NBA goal, cosine-nine research control and protected closure are
unchanged. The budget remains 2,437 seconds (40m37s); analysis used no GPU time.

[Verified local analysis and comparison](../data/outputs/t/reference_clock_test_v0_1/dump_analysis_v0_1/analysis_receipt.json).
Earlier inaccessible-dump and proposed/unrun statements below retain their
historical status and are superseded only as to this fulfilled copy/analysis.

## Debug Mode diagnostic crashed; no retry, 2026-10-28

Ryan explicitly approved enabling only NVIDIA Debug Mode and one supervised test
of up to ten minutes. The toggle was observed off, enabled and independently
re-observed on before load. Driver617.42, configured5200 RAM, the scientific
recipe, batch32 and original inputs remained fixed. Lively was temporarily
closed to match the earlier isolation; no service/startup, power, fan, BIOS or
other setting was changed. MSI services and user applications remained. The
previous attempt did not record Debug Mode or actual load clocks, so the
historical comparison has that limitation.

**The diagnostic failed with a renewed NVIDIA graphics fault and Windows reboot.**
This disproves Debug Mode as a sufficient fix for this attempt; it does not
identify a defective component or eliminate GPU/clock-margin, power/connection,
platform/firmware, memory/controller or driver/software interaction. Reference
clocks are the vendor's intended behavior, not independently measured against
an otherwise identical prior-run clock baseline. No automatic retry occurred.

### What actually happened (Phoenix time)

| Time | Observed evidence |
| --- | --- |
| 17:36:25.891 | Diagnostic launcher started; deadline included event-monitor startup and cleanup. |
| 17:39:17.312 | Last successful GPU sample. |
| 17:39:20.828 | Live watcher captured new nvlddmkm event153, level2. |
| 17:39:20.836 | NVIDIA telemetry failed; supervisor entered its stop/cleanup path. |
| 17:39:22.613 | Event companion independently requested STOP for the graphics fault. |
| 17:39:35.866 | Owned GPU launcher did not signal exit; worker cleanup was not certified. |
| 17:39:35.874 | Valid final launcher receipt recorded failure; no retry. |
| 17:40:09.500 | Next Windows boot, independently read after Ryan reported restart. |

The 85 saved GPU samples peaked at63C,2525MiB and148.5W, with no sampled thermal
or hardware-power-brake flag. Recorded loaded clocks included2805MHz graphics/SM
and13801MHz memory. These samples do not establish hotspot/transient health,
power-delivery integrity or continuous reference-clock enforcement. Advertised
maximum3090MHz is not the measured current clock. Idle-versus-load memory-clock
differences do not measure the intervention against attempt003.

Post-reboot Windows events confirm one new0x116 crash naming nvlddmkm.sys, with
C000009A and final parameter4, matching the earlier broad reset-failure pattern.
Three Application WER entries share report ID4226fa64-b33e-4d8f-a7e0-7d0eee90bcb7;
they are not three independent crashes. The new bucket containsTdr:9 instead of
the earlierTdr:3/TdrVTR:0; this is retained metadata, not a decoded cause. The new
dump has not been read, so no identical stack/private-function claim is made.
C000009A alone does not diagnose exhausted system RAM or VRAM.
[Microsoft's 0x116 meaning](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x116---video-tdr-failure).

The live captured event153 used System record25296. The saved post-reboot log
uses25296 for a new boot Kernel-General event instead; the latest pre-crash event
may not have persisted. Preserve both records and their timestamps; do not join
across this reboot by record number alone. Post-reboot queries inspected150
System and34 Application events. No Python worker was present in that snapshot;
this does not retroactively certify the failed pre-reboot cleanup. Event-job
cleanup alone recorded zero owned processes. Final receipts are readable this
time, unlike earlier NUL-filled receipts. STOP is empty after reboot; its request
is established by the saved action/control records, not surviving text contents.

### Saved work, resource accounting and preservation

The independent saved-output audit passes21,397 checks:442 starts,441 completed
updates,14098 returned training presentations, last logical step1189, and one
unreturned32-candidate start. All441 recorded loss/gradient pairs exactly match
attempt003, with zero updates beyond that attempt's returned range. Earlier
failure within the same numerical replay does not support a single consistently
failing batch, but does not exclude software timing or a workload-triggered issue.

Only epoch3 completed. Its separate diagnostic checkpoint retains logical1122,
passes hash/ZIP CRC checks, and has67 later returned updates unsaved. New tensor
semantics are unaudited. The original scientific epoch4 checkpoint at1496,
its267 later unsaved updates, all earlier failures and300 prior replay-overhead
updates remain preserved. Cumulative durable physical work is2504updates/80058
training presentations, plus the original32 parity presentations; diagnostic
replay is not a completed scientific fit or comparison. No scoring, other fit,
new labels, protected evaluation or model adoption occurred.

The valid launcher measured189.985seconds, but GPU-worker cleanup was uncertain.
Conservatively debit224seconds through the next boot, leaving2437seconds
(**40m37s**) of the original hour. No budget reset/refund or new GPU authorization.
The ten-minute endpoint was not reached and this is not a stability pass.

Seven worker checks, eight event-helper checks, actual producer/consumer records
and an independent prelaunch review passed. A monotonic hard deadline included
all startup/cleanup, and two owned jobs bounded the worker/event companion.
These controls detected the failure and attempted termination; they could not
prevent a kernel-level graphics fault/reboot. Original frozen workers were not
edited. The two additive source/test files and all85 prior worktree contents,
including the original Session17 preservation chain, remain accounted for.

### Current diagnostic limit and next local evidence

Windows lists new dump `C:\Windows\Minidump\102826-18687-01.dmp` (7449418bytes),
but ordinary read access is denied. The guarded, syntax-checked
[local copy helper](../data/outputs/t/reference_clock_test_v0_1/copy_crash_dump.ps1)
is prepared and unrun; an administrator copy would permit inspection without
another GPU test or settings change. The accessible logs already establish that
this intervention did not prevent recurrence. A dump copy may refine comparison,
but a new root cause is not promised. Physical inspection remains deferred.
Debug Mode was observed on before this crash; its post-reboot state has not been
inspected or changed. The app described the override as lasting until restart.

Reused the completed full-history/research reconciliation, including prior
foundation/session coverage and all later result/incident summaries. This turn
read maintained context/authority/history sections and targeted original worker,
checkpoint-audit, supervision, crash/watchdog and current-run evidence; current
[NVIDIA Debug Mode guidance](https://nvidia.custhelp.com/app/answers/detail/a_id/5802/)
and Microsoft0x116 documentation were reopened. No fresh full-transcript,
every-paper reread or new scientific direction is claimed. NBA remains the goal;
cosine nine remains research control. All weak/hidden/uncertain/missing cases,
accepted labels, adverse evidence and numerical/human-review gates stand.

[Actual execution and evidence folder](../data/outputs/t/reference_clock_test_v0_1/)
contains frozen approval/input bindings, before/on UI records, supervision and
live event logs, post-reboot snapshot, independent audits and preservation
receipts. Earlier proposed/unrun statements below are historical states.

## Recommended next single-setting test, 2026-10-28

Ryan asks for the best next diagnostic, explained simply, changing one thing at
a time. Recommend NVIDIA Debug Mode, now independently observed **off** in the
installed NVIDIA App at System > Advanced. The grey toggle is left; it was not
clicked. The current app describes removal of user/factory overclocking until
system restart. Its existing Automatic Tuning off announcement was also visible;
the Performance tab and other utilities' complete tuning state were not verified.
No configuration change, new telemetry command or workload has run.

NVIDIA documents that Debug Mode applies its reference clocks and disables
factory/manual GPU overclocking. This is the most focused reversible next test
among the inspected options: configured5200 and driver617.42 have already failed
to prevent recurrence, while a clean boot changes multiple services and no
cause-specific BIOS/chipset fix is established. Clock sensitivity is plausible,
not diagnosed. Firmware, utility interaction, memory/controller and power/hardware
remain open alternatives. Physical inspection stays deferred.
[NVIDIA's current primary instructions](https://nvidia.custhelp.com/app/answers/detail/a_id/5802/).

### Proposed diagnostic contract; implementation and execution still pending

- Record then enable only Debug Mode. Keep driver617.42, RAM5200/reported EXPOoff,
  power/fan controls, BIOS, runtime, batch32, model/data and optimization recipe
  fixed. Recheck the toggle immediately before load and after any restart. Restore
  the recorded off state through the same toggle when explicitly ending the test;
  the app says a system restart removes the override. Do not reboot to create a
  second variable or automatically re-enable/retry after a fault.
- Match attempt003's documented pre-run background/graphics isolation as closely
  as possible and record differences. Do not add a service clean boot, software
  uninstall or utility setting change to this test. The earlier attempt did not
  record Debug Mode UI; today's off observation does not retrospectively prove
  its earlier state. This is one planned setting change with a historical
  comparator, not a perfectly controlled randomized A/B experiment.
- Use a separate diagnostic output and replay the same first `leave_chi_out` fit
  from the already CPU-audited epoch-two checkpoint at update748. Stop after the
  unchanged epoch-six endpoint/update2244: at most1496 physical updates, including
  replay of1015 updates returned by attempt003 and481 beyond its last returned
  update. No next fit, scoring or adoption follows. The replay tests stability;
  it does not overwrite/resume the retained epoch-four checkpoint or pretend
  repeated work is new scientific progress. Preserve all case/data roles.
- Maximum600 seconds from supervisor policy creation, including startup and a
  30-second cleanup reserve; stop new work by570 seconds. Finish earlier if the
  first-fit endpoint is reached. Debit actual elapsed time against the existing
  2661 seconds, with conservative accounting through reboot if needed. No reset
  of the original hour. Endpoint completion and time-cap termination are distinct.
- Use the existing2-second telemetry cadence and80C stop threshold, CUDA/telemetry
  failure stops, owned-worker cleanup and explicit user-stop control. Add checked
  Windows graphics-event monitoring before declaring this diagnostic prepared.
  Any renewed fault ends the attempt; no automatic retry. Monitoring cannot
  guarantee prevention of another Windows restart, as attempt003 demonstrated.
- Before execution, implement/review the bounded first-fit-only worker/supervisor
  path without modifying the frozen historical workers; verify metadata, input
  bindings, before/after setting, current event/memory/isolation readiness and
  preservation. Existing CPU checkpoint audit is reusable by unchanged hash.
  Exact launch command and final execution inventory are not prepared yet. No
  GPU execution approval is inferred from this request for a recommendation.

A completed clean segment supports clock/load-margin sensitivity only. It cannot
separate GPU silicon, power delivery, platform or software, and cannot establish
long-term stability: earlier different workloads succeeded for about46 minutes.
Another117/141/116 or telemetry loss weakens the factory-clock-only explanation.
A time cap before comparable exposure is inconclusive; do not call it a pass.
Observe actual clocks under load to establish whether the intervention took
effect; no independent power-limit reduction or other setting is included.

The completed full-history/research reconciliation is reused (Sessions1-16,
selected foundation evidence, earlier Session17/18 handoff reads and subsequent
results). This turn reopens maintained context/authority/history sections,
historical-review coverage/lessons, primary watchdog/crash and recovery/audit
records, targeted worker/limits, and current NVIDIA guidance; it also inspects
the actual UI. No new full-transcript or every-paper reread is claimed. An
independent design review supports this conditional choice and first-fit endpoint.
NBA/cosine-nine, accepted labels, uncertainty, gates, protected closure, earlier
failures, epoch-four checkpoint and267 unsaved updates remain unchanged.

[Proposal and before-state evidence](../data/outputs/t/reference_clock_test_proposal_v0_1/proposal.json).
Earlier sections below remain historical evidence, including completed copy tasks.

## Watchdog dump follow-up completed, 2026-10-28

The supplied watchdog copy is verified: 2,645,061 bytes, SHA256
`e1ef25c197bd91df7b2803c7562a3cdbf2427af0d0d3546e27521030f68be640`.
Three local saved-dump debugger invocations exited successfully. The copy request
is fulfilled. No additional protected file copy is currently identified as needed.

The live dump captures the scheduler detecting stalled graphics progress at
**16:21:38.251 Phoenix**, 19.296 seconds before the final 0x116 snapshot. This is
essentially contemporaneous with the supervisor's 16:21:38.245698 telemetry failure.
The later 16:21:41.4779308 WER timestamp describes report metadata, not the original
hang onset. The same TDR recovery-context address `ffff808b8c5ef010` appears in both
dumps, strongly linking the timeout and fatal recovery failure to the same event.
The inspected NVIDIA image remains driver 617.42.

The live stack is `VidSchiCheckHwProgress` / `VidSchiReportHwHang`, followed by TDR
checking and diagnostic capture. The fatal dump is the later failed adapter-reset
path. This establishes the failure sequence, not a faulty component. The live
0x117 parameter3 is zero and is a driver-specific bucketing key; it is not the
same field as the fatal 0x116 last-operation status C000009A. Neither establishes
RAM or VRAM exhaustion. `System` identifies the scheduler worker, not the workload
that caused the hang. The NVIDIA export-symbol fallback `nvDumpConfig+795b30`
does not identify a private failing function.
[Microsoft 117](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x117---video-tdr-timeout-detected),
[Microsoft 116](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x116---video-tdr-failure).

The snapshot is a small kernel triage dump. Direct reads confirm that its TDR
context and argument4 process-object memory are unavailable; full memory-use
state is unavailable too. A secondary TDR block is present: 2,382,869 bytes,
GUID `270A33FD-3DA6-460D-BA89-3C1BAE21E39B`. Its extracted bytes match the original
dump exactly and are retained. The installed `!ext.blackboxdxg` command yielded
no decoded output. Installed extension inventory and public primary documentation
did not establish a supported decoder/schema for this block. Microsoft's WinDbg
maintainer identifies `dxgkdx.dll` as internal and dependent on internal symbols.
This is an interpretation limit, not evidence that the block contains no useful
information. No internal/private access or external upload was attempted.
[Callback-data documentation](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/reading-bug-check-callback-data),
[Microsoft tooling clarification](https://github.com/microsoft/WinDbg-Feedback/issues/348).

One raw string says to connect the PCIe power cables. It sits inside an embedded
64,000-byte NVIDIA option-ROM image with 55AA/PCIR headers, vendor10de/device2f04
and checksum zero, alongside VBIOS version98.05.28.00.AD and other generic firmware
messages. Its presence is not evidence that this warning was displayed or that a
power cable caused the fault. Likewise, a `python.exe` string does not identify
a failing CUDA kernel. Two independent reviews agree with these limits.

**The cause remains unresolved.** This strengthens the earlier GPU-stall diagnosis
but does not distinguish driver interaction, reference-clock stability,
firmware/platform compatibility, power/connection problems or defective hardware.
The earlier failures predating this pilot, recurrence at5200 and on617.42, sampled
low temperatures/memory use, and previous successful workloads remain relevant
but do not clear any entire category. Existing nonphysical diagnostic candidates
remain proposed, unfrozen and unrun; this follow-up selects or executes none.

Reused the maintained full-history/research review and prior dump/event evidence;
new work was actual watchdog analysis, targeted memory/tag checks and primary
Microsoft documentation. No fresh all-transcript/every-paper review is claimed.
No GPU query/workload, Torch import, system/driver/BIOS change, training retry,
labels, protected evaluation or Git integration occurred. The epoch-four
checkpoint, 267 unsaved updates and 2,661-second remaining pilot budget stand.

[Local analysis and exact evidence bindings](../data/outputs/t/gpu_timeout_1621_v0_1/analysis_v0_1/analysis_receipt.json).
The earlier sections below preserve the prior investigation and proposal states.

Ryan asked to investigate further before opening the case. **Software and
firmware avenues are not exhausted.** The earlier power-connection inspection
remains an unperformed option; it is deferred in favor of this requested
nonphysical investigation. None of the findings below establishes a root cause.

## New evidence and its limits

| Finding | What it contributes |
| --- | --- |
| A protected `Kernel_117` WER archive folder was modified at 16:21:56.156, near the 16:21:57.547 final crash snapshot | Potential additional evidence from an earlier timeout stage. Its contents, associated live-dump path and exact incident relationship have not yet been read. |
| MSI/Ryzen hardware-control drivers were loaded in the actual crash dump | Closing Lively and True Color did not isolate all background hardware-control software. Presence does not prove interference or active overclocking. |
| Installed BIOS remains 1.L0; later exact-board releases describe PCIe and graphics compatibility fixes | A concrete firmware avenue remains; no inspected note identifies this RTX5070/0x116 failure. |
| Installed AMD chipset package is 7.06.24.2226; later notes explicitly add Windows11 25H2 support | A version/support difference worth assessing, not proof of incompatibility or a cause. |
| NVIDIA documents a reference-clock Debug Mode; no completed test of it is recorded | A reversible diagnostic for GPU clock sensitivity remains available before requiring physical inspection. It is unperformed and not automatically authorized. |

The expanded bounded query inspected 1,014 System and 269 Application events
around the three latest incidents. No WHEA, storage, resource-exhaustion or
graphics precursor appears in the selected immediate pre-failure windows.
Missing/unflushed events remain possible. Nine WER receipts represent five
report IDs. More detailed WER buckets differ (`Tdr:9` versus `Tdr:3_TdrVTR:0`);
their undocumented interpretation is unresolved. The earlier statement of a
shared generic failure pathway does not mean every report field is identical.

Microsoft defines 0x117 as a display-timeout live dump, distinct from the final
0x116 stop. A report from that stage could identify an existing attachment with
additional information. The archive timestamp alone does not establish the
dump's internal time or a cause.
[Microsoft 0x117](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x117---video-tdr-timeout-detected).

## Software and platform checks actually performed

Fresh read-only inventory confirms 5200 MT/s, driver617.42, Windows11 build26200,
system-managed page file and substantial current free RAM. These are current
observations, not crash-time resource measurements. One bounded NVIDIA telemetry
query succeeds at 44 C with default/requested/current power limit250 W and zero
reported PCIe replay counters. Idle link/clock readings and maximum boost values
do not establish a fault, absence of factory overclocking, or electrical health.

Windows is configured for small dumps (`CrashDumpEnabled=3`), which explains an
important evidence limitation. Automatic/kernel capture could provide more
kernel state if a future failure occurs, with additional storage/privacy costs;
no capture setting was changed and no failure should be induced merely for it.
[Microsoft automatic dumps](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/automatic-memory-dump).

A targeted read of the existing dump confirms `AMDRyzenMasterDriver`, two
`NTIOLib_X64` modules and `MsIo64` loaded at the crash. Current inventory likewise
shows MSI Center services and Ryzen Master SDK helpers running. These are not
proof of causation, active tuning, or an invalid driver. A clean-boot-style
isolation remains distinct from closing user applications. Any such test must
preserve original states and verify which components actually stopped; disabling
services does not by itself certify every kernel helper unloaded. No service or
driver was stopped, disabled or uninstalled.
[Microsoft clean boot](https://support.microsoft.com/en-us/windows/experience/startup-boot/how-to-perform-a-clean-boot-in-windows).

Targeted training-code and metadata review found no obvious retained-graph leak,
custom CUDA kernel or runtime-pin mismatch. Torch2.13.0+cu130 matches the frozen
recipe;617.42 meets the inspected published CUDA13/Blackwell driver floor.
Earlier roughly46-minute WASB fits completed on the same runtime, but used a
different workload. DINO attention/backward remains a possible trigger; neither
runtime compatibility nor prior success clears software or hardware. CUDA is
asynchronous, and `train_start` is journaled after device transfer, so the final
record does not identify the failing kernel. No Torch import or model run was
used in this code/metadata review. Full617.42 release-note coverage remains
incomplete; no universal absence-of-known-issues claim is made.

NVIDIA's Debug Mode explicitly forces reference clocks and disables factory or
manual GPU overclocking. The ASUS model is a factory-OC product; its current
Debug Mode state and actual tuning profile have not been visually verified.
Default power limit alone does not settle them. A later approved test should
change only the reference-clock setting, preserve/restorable prior state and
define the workload, stop rules and interpretation beforehand. A pass would show
limited stability at that setting, not prove the GPU healthy or distinguish all
power/clock/software causes. Another fault would weaken a clock-only explanation.
No Debug Mode change or new test was executed.
[NVIDIA procedure](https://nvidia.custhelp.com/app/answers/detail/a_id/5802/).

MSI's rendered official exact-board list includes later PCIe-device compatibility
work (7D75v1P8, March20,2026), graphics/wake/boot fixes (1P, April28,2026) and an
IGD/Hybrid Graphics black-screen fix (1M, May14,2025). Hybrid Graphics settings
are unknown; a loaded AMD display driver does not establish that configuration.
The list does not specifically identify RTX5070, CUDA,0x116 or C000009A. Version
suffixes were not used to invent beta/stable labels. No flash target was selected.
[MSI support](https://www.msi.com/Motherboard/MAG-B650-TOMAHAWK-WIFI/support).

AMD's7.11.26.2142 notes list Windows11 25H2 support and V-Cache optimizer1.0.0.12;
installed optimizer is1.0.0.11. PSP/PPM components also trail later versions.
The notes do not specify functional applicability of the optimizer change to
this single-CCD7800X3D. Do not call it a diagnosed scheduling defect or GPU fix.
Older7.06 notes were unavailable; lack of a later support statement does not
prove the installed package cannot work. Current8.09.28.1124 has generic fixes,
not an identified remedy for this incident. No installation was performed.
[AMD support addition](https://www.amd.com/en/resources/support-articles/release-notes/RN-RYZEN-CHIPSET-7-11-26-2142.html).

## Concrete next step and boundaries

Read the **existing small 0x117 Report.wer first**, without changing settings or
creating another failure. Its exact path is recorded in `event_correlation.json`.
Ordinary access to that protected archive is denied. The prepared administrator
copy script copies just that report, checks repository/branch/HEAD/empty index,
refuses overwrite, checks that it is a small report and verifies source/copy SHA.
It is syntax-checked and unrun. No dump path or attachment size is guessed.
After reading it, identify whether a surviving live dump adds useful evidence;
another triage dump may still have the same private-symbol limitations.

This is prioritized because it adds information without another workload or
configuration change. Reference-clock testing, verified background isolation,
platform-driver maintenance and firmware review remain separate candidates.
They should not be combined into an uninterpretable sequence of simultaneous
changes. No automatic retry, firmware flash, TDR/security modification, driver
installation, stress test, memory test or physical action follows from this note.

The proposal changes if the existing report identifies a specific actionable
driver/device condition. If it adds only the same generic timeout, choose one
reversible diagnostic after inspecting its actual starting state. The exact
execution protocol is not yet frozen or approved. Diagnosis may eventually need
hardware isolation, but the available nonphysical work is not exhausted.

## Reuse, evidence and preservation

Reused the completed full-history/research review, current context/authority map,
earlier actual dump analyses, captured troubleshooting/build evidence, completed
CPU/GPU results and their limitations. New work is targeted event correlation,
inventory, existing-dump module inspection, code/runtime review and relevant
primary Microsoft/NVIDIA/AMD/MSI documentation. No fresh every-transcript or
every-paper reread or repeated scientific experiment is claimed. MSI's dynamic
page was read in a temporary browser after static retrieval failed; no installed
package was downloaded. Review limits and source bindings are saved separately.

Ignored evidence is under
`data/outputs/ball_tracking/candidate_quality_pilot_v0_1/post_driver_recovery_preparation_v0_1/attempt003_interruption_v0_1/nonphysical_diagnosis_v0_1/`:
platform/telemetry inventory, module-presence debugger log, event correlation,
firmware and runtime reviews, copy helper and preservation records. One read-only
NVIDIA query and one saved-dump debugger invocation occurred; zero GPU workloads,
Torch imports, settings changes or installations occurred.

All84 prior worktree contents and Session17 preservation remain intact through
additive records; branch/HEAD/empty index remain unchanged. The epoch-four
checkpoint,267 unsaved updates, all failures and2,661 seconds remaining stand.
NBA/cosine-nine, accepted labels, full case coverage, uncertainty, quality/human
gates and protected closure remain unchanged. No Git integration.
