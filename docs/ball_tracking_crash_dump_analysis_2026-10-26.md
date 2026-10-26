# Local crash-dump analysis, October 26, 2026

Ryan copied the protected Windows dump into the ignored diagnostic directory
from an administrator PowerShell window. The first pasted multiline command
lost its separators and failed to parse; the replacement single-line copy
completed, refused overwriting, and produced a readable 6,423,664-byte file.
Its SHA256 is `09983d19edbe9a51cd3ef47b922e852a5554c6f12baaa3982edbfc4a309abe5b`.
The original system dump and its permissions were not changed.

Microsoft WinDbg 1.2610.1001.0 was installed through the official `Microsoft.WinDbg`
winget package, whose installer hash was verified. Its packaged amd64 command-line
debugger analyzed the local copy using Microsoft symbols. No driver, BIOS,
registry, memory, clock, power or fan setting was changed. No GPU fit or stress
test ran. The training experiment remains stopped at zero scientific updates.

## What the dump establishes

- Crash snapshot: **08:01:03.311 Phoenix time**, uptime 19 minutes 53.523 seconds.
  This is about 19 seconds after the recorded telemetry failure and precedes
  the Windows reboot/event-registration timestamps in the original incident.
- Bugcheck: **0x116 / VIDEO_TDR_FAILURE**. The stack shows Windows entering
  `dxgkrnl!TdrBugcheckOnTimeout` after adapter-reset/recovery routines.
- The second bugcheck parameter points inside **`nvlddmkm.sys`**, NVIDIA's
  display driver, at module offset `0x1935300`. The debugger's failure bucket
  is `0x116_IMAGE_nvlddmkm.sys`.
- The installed NVIDIA image is **616.56**, file version **32.0.16.1656**, with
  a valid Microsoft Windows Hardware Compatibility Publisher signature. Its
  PE timestamp, image size and checksum match the dump's loaded-module metadata.
  Its SHA256 is `39f23e999f4ec35f592196e61d1a49438e91066762834d412a8eb86f0f14dbd2`.
- Parameter three, `0xC000009A`, decodes to **STATUS_INSUFFICIENT_RESOURCES** for
  the last failed operation. The dump does not identify which resource was
  unavailable or establish that GPU VRAM, RAM or the original model allocation
  was exhausted.

Microsoft's [0x116 reference](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x116---video-tdr-failure)
defines this as failed graphics-timeout recovery and identifies the roles of
the module pointer and last-operation status. The observed reset stack and
module attribution are stronger evidence than the earlier event code alone.
They still do not establish a defective GPU or a specific NVIDIA software bug.

## Limits and earlier history

This is a kernel triage dump, not a full-memory image. WinDbg reports missing
triage-extension/XState data, and the `_TDR_RECOVERY_CONTEXT` type is unavailable
in the loaded symbols. NVIDIA private function symbols are unavailable. These
limits are preserved; they do not invalidate the visible bugcheck/stack/module
mapping or prove that the whole dump is corrupt.

`PROCESS_NAME: System` describes the reset worker context; it does not establish
that the preceding workload was unrelated. The debugger's 98 MB analysis
commit-peak describes the debugger, not the computer's RAM usage at the crash.
The PnP blackbox mentions problem code 24 on `ROOT\SYSTEM\0001`; no evidence here
connects that record to the NVIDIA GPU, so it is not used as a causal explanation.

A fresh seven-day System-event query also finds the October 23 0x116 event.
This corroborates the already preserved October 25 investigation rather than
discovering a new history: that earlier audit recorded **17 distinct 0x116
receipts from August 10 through October 23**, predating the current driver and
the new resolution experiment. Ryan previously reported intermittent crashes
since the build and temporary benefit from driver updates. Different observed
screen/restart symptoms can coexist with this recurring graphics-failure category;
a shared underlying cause remains unproved.

Earlier hardware/build evidence and Ryan's preference for other diagnostic
avenues before physical cable inspection remain applicable. Stopping the graphics
extras did not prevent the latest incident. A repeated driver installation is
not established as a cure. The prior staged stock-memory investigation was not
recorded as completed, but this dump does not prove RAM instability either.

## Decision and preservation

The manual access step and local dump analysis are complete. No further copy or
elevated command is needed for this dump. The next decision is a controlled
stability investigation informed by the existing history, with any substantial
settings/remediation change reviewed with Ryan. Do not resume training, raise
timeout settings, run a stress test or start another fit automatically.
The approved experiment, labels, quality criteria and protected boundary remain
unchanged.

Debugger attempt 01 failed because `.sympath` interpreted the rest of a command
line as a path; its log is retained and is not analysis evidence. Attempt 02 used
a newline command file and completed `!analyze -v`, the stack and status decode.
Attempt 03 supplied the matching local NVIDIA image and completed metadata and
blackbox inspection. Both later debugger processes exited zero. Their warnings
and unavailable fields remain in the original logs.

Evidence is bound in the [analysis receipt](../data/outputs/t/nba_resolution_restart_20261026/crash_dump_analysis_v0_1.json),
SHA256 `1ea39209ae64ea4b4ee523523c2e8c013742638ced2c1f7c4d0bc6a714a82fa7`.
It links the copied dump, all debugger attempts, commands, verified driver image,
fresh bugcheck history and the earlier history summary. See the
[original incident record](ball_tracking_nba_resolution_restart_2026-10-26.md)
for the preserved failed fit and valid update-zero state. No earlier model
results, references or recovery evidence were replaced.
