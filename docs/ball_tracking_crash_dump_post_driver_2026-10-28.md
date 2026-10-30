# Crash-dump comparison after Studio 617.42 installation

The new dump confirms recurring **NVIDIA graphics timeout recovery failure**,
not a newly identified CPU, RAM or power-supply failure. Windows could not reset
the graphics adapter and stopped with 0x116. It follows the same Windows recovery
stack as the two previously analyzed dumps, despite the driver replacement and
configured RAM speed of 5200 MT/s. The underlying cause is still unresolved.

Ryan's administrator copy is verified: 7,841,199 bytes, SHA-256
`a999f2a4430c53c3eab6f7c0f9338996721ff10473945052351c51c9dde9af56`.
The installed Microsoft command-line debugger analyzed the copy locally in two
successful invocations. Only Microsoft symbols were fetched; the dump was not
uploaded. No GPU query/model call, stress test, settings change or retry ran.

## Comparison with earlier crashes

| Dump snapshot, Phoenix | Driver | Bugcheck / last-operation status | NVIDIA module offset |
| --- | --- | --- | --- |
| October 26, 08:01:03.311 | 616.56 | 0x116 / C000009A, parameter4=4 | 0x1935300 |
| October 28, 14:05:31.131 | 616.56 | 0x116 / C000009A, parameter4=4 | 0x1935300 |
| October 28, 16:21:57.547 | 617.42 | 0x116 / C000009A, parameter4=4 | 0x193b450 |

All three show `dxgkrnl!TdrBugcheckOnTimeout`, adapter reset and timeout-recovery
worker calls, with the same named Windows call sequence/offsets. Their generic
failure bucket/hash agrees. This establishes a repeated failure pathway, not a
unique fingerprint of a faulty component. NVIDIA's changed offset belongs to a
different binary; private function equivalence cannot be inferred.

The new dump's uptime is 27m45.432s. Its crash snapshot is 19.301302 seconds after
NVIDIA telemetry failed and 21.673264 seconds after the last successful sample.
It precedes the 16:22:25.5 reboot and later event registration. This approximately
19-second telemetry-to-crash sequence also occurred in the earlier two dumps.
Attempt002's intervening 141 live graphics timeout remains a distinct observed
outcome; its inaccessible watchdog dump was not analyzed here.

The currently installed NVIDIA image has file version 32.0.16.1742 and a valid
Microsoft hardware-compatibility signature. Its independently read PE timestamp
`6ABD8060`, image size `06D45000` and checksum `06CB596E` match the dump metadata.
Supplying that image to the debugger identifies product version 617.42. Thus the
new dump is not simply the old 616.56 crash being reported again.

## What this does and does not explain

Microsoft defines 0x116 as an unsuccessful attempt to reset the display driver
after a timeout; driver software, configuration, power and other hardware can
contribute. The failure names NVIDIA but does not isolate a driver bug or a
defective GPU. C000009A is an insufficient-resources status for the last failed
operation, without identifying which resource was unavailable.
[Microsoft 0x116](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x116---video-tdr-failure),
[status definitions](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-erref/596a1078-e883-4972-9bbc-49e60bebca55).

This is a kernel triage dump. The private NVIDIA symbols, TDR recovery-context
type and `MiVisibleState` are unavailable; the secondary Winlogon extension also
did not load. The analysis therefore cannot reconstruct full crash-time memory
usage or the original device failure. Debugger memory usage is not the target
PC's RAM use. `PROCESS_NAME: System` describes the recovery worker, not proof
that the training workload was uninvolved.
[Microsoft small-dump limitations](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/small-memory-dump).

The repeated PnP problem24 entry is `ROOT\SYSTEM\0001`, recorded at 15:55:00.086,
near boot and about 27 minutes before this crash. It has not been identified as
the NVIDIA PCI device and supplies no causal GPU diagnosis. Hyper-V/VSM flags
and a loaded AMD graphics driver likewise establish presence, not causation.
No security feature, integrated GPU or timeout setting is changed on that basis.

The saved samples peaked at 62 C and 2,968 MiB GPU memory, without active thermal
slowdown flags. They do not show thermal-limit operation or full VRAM, but cannot
rule out electrical transients, other temperatures or hardware faults. The
bounded Windows scan had no matching WHEA/resource-exhaustion events; that is not
a hardware-health certificate.

The maintained earlier investigation records 17 distinct 0x116 System receipts
from August10–October23 and Ryan's reports of symptoms outside training and
since the build. Application isolation and previous successful GPU workloads did
not establish stability. Recurrence at 5200 after reported EXPO disablement weakens
a 6000-profile-only explanation; recurrence on 617.42 weakens an old-driver-only
explanation. Neither intervention excludes every memory/controller or driver
cause. Training can trigger an underlying problem without explaining its entire
history. No model failure or adoption decision follows from this hardware event.

## Best-supported next bounded diagnostic

**Propose a powered-off visual identification of the GPU power connection and
cable route, initially without disconnecting internal components.** Ryan earlier
preferred other avenues before physical inspection. Those nonphysical checks
have now failed to prevent recurrence. The proposed inspection closes a concrete
remaining evidence gap without another crash-provoking workload.

The previously preserved build conversation explicitly lists a Corsair RM850e
(2025) and ASUS TUF RTX5070 OC. Captured original turns include incorrect assistant
claims about two 8-pin sockets on the GPU and reassurance about an assumed cable
layout. Ryan then described the supplied adapter. No captured photograph or
inspection establishes the currently installed route or connector seating.
These old instructions must not be reused as verified wiring guidance.

ASUS specifies one 16-pin GPU connector and a 750 W recommended PSU. The 850 W
build listing is not obviously below that recommendation, but does not establish
the installed PSU's condition. ASUS documents secure connector insertion and
adapter connection requirements.
[Exact GPU specification](https://www.asus.com/ie/motherboards-components/graphics-cards/tuf-gaming/tuf-rtx5070-o12g-gaming/techspec/),
[installation guidance](https://www.asus.com/support/faq/1047391/).

Corsair's 2025 manual includes both a native 12V-2x6 cable and a 12V-2x6-to-two
6+2 cable, as well as conventional PCIe cables. Therefore “one cable” or one PSU
connector alone does not prove improper wiring. Identify both ends and any adapter
before judging the route. Use only supplied or confirmed-compatible cables;
the actual PSU label/revision remains to be checked.
[Corsair RMe 2025 manual](https://www.corsair.com/ca/en/explorer/diy-builder/power-supply-units/corsair-rme-series-2025/).

The review material would be photographs of the GPU power plug/latch, the complete
visible cable/adapter route, and accessible PSU label/ports. Save work, shut down,
switch the PSU off and unplug AC before opening the case; do not open the PSU
housing. Preserve the original arrangement for inspection before proposing any
reseating or cable substitution. This is proposed user-assisted inspection,
not an executed intervention or authorization for a new workload.

A visible gap, damage or confirmed incompatible route would direct a specific
corrective plan. A correctly identified and apparently seated connection would
close that visible evidence gap but not prove electrical health. Then choose one
separately prepared isolation step using actual firmware/clock information;
GPU/PCIe, power, firmware/driver and memory/controller possibilities remain open.
No blind firmware update, arbitrary timeout change, new driver installation,
stress test, component purchase or outside specialist is prescribed here.

## Actual reading, preservation and continuation state

Reused the completed full-project Sessions1–16 review, selected foundation
evidence, previously read Session17/18 handoffs and subsequent results. Read the
current maintained context/authority entries, both previous dump reports and
relevant actual logs/receipts, captured original troubleshooting/build turns,
new Windows and telemetry records, and new debugger output. Independently checked
the driver image, timing and interpretation; refreshed relevant Microsoft, ASUS
and Corsair primary documentation. No fresh full-transcript/every-paper reread,
full historical event recount or physical inspection is claimed.

Evidence is ignored beneath
`data/outputs/ball_tracking/candidate_quality_pilot_v0_1/post_driver_recovery_preparation_v0_1/attempt003_interruption_v0_1/dump_analysis_v0_1/`:
input verification, commands, debugger logs/exits, driver and timing check,
independent interpretation, history review and analysis/preservation receipts.
The first debugger lacked the local NVIDIA image; the second supplied it and
verified its version. Both exited zero; all warnings and unavailable fields remain.

All 83 prior worktree contents and the original Session17 preservation chain
remain intact through additive documentation. Branch is
`codex/ball-detector-baseline`, HEAD `8c040fca385dd8fffa0d7a13c45c53e79950bae1`,
empty index. No staging, commit, push or merge. The dump-access step is complete;
do not request that copy again.

The saved epoch-four checkpoint, 267 unsaved updates, all prior failures and
44m21s remaining budget stand. New dump timing does not refund the conservative
debit. Training stays stopped with no automatic retry. NBA, cosine nine, accepted
labels, full case coverage, uncertainty, numerical/human gates and protected
evaluation boundaries remain unchanged.
