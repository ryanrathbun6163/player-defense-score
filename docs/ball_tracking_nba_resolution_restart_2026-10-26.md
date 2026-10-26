# Resolution experiment interrupted by a Windows graphics crash

October 26, 2026, America/Phoenix. Ryan reported: "sorry chat my computer
restarted. this was different than the black screen issue I discussed before".
That distinction in observed symptoms is preserved. The available records do
not establish whether the incidents share an underlying cause.

The approved experiment was frozen and committed at
`3605648f0a4243bc67dcce49e60caa5d0642f873` on
`codex/ball-detector-baseline`. Its first supervised attempt stopped during
fresh **epoch-zero validation, before any scientific optimizer update**.
There is no completed new epoch, accuracy comparison or trained candidate.
The successful disposable readiness check remains separate from this failed
scientific attempt. The prepared 768x432 recipe remains unchanged.

## Observed sequence

All times below are Phoenix local time, converted from the recorded UTC values.

| Time | Evidence |
|---|---|
| 08:00:08 | Supervisor started the owned experiment process |
| 08:00:41.406 | Last valid GPU sample: 47 C, 126.95 W, 2,441 MiB, 63% utilization |
| 08:00:44.058 | Supervisor recorded `NVIDIA telemetry failed: `; the query returned nonzero with empty stderr |
| 08:00:44.059 | Supervisor cleanup created its STOP file |
| 08:00:44.241 | Fit recorded `KeyboardInterrupt` during initial validation: zero updates, no attempted training update |
| 08:00:59.076 | Cleanup recorded `Owned launcher did not signal exit` |
| 08:01:32.500 | Windows recorded the new OS startup |
| 08:01:51.587 | Windows System event 1001 reported a reboot from bugcheck `0x00000116` |

All eighteen surviving telemetry samples parse. Observed maxima are 50 C,
126.95 W and 2,460 MiB; all recorded thermal/power-brake slowdown flags are
inactive. This is not a recorded temperature-limit stop. Samples end before
the reboot and cannot establish conditions afterward or exclude a hardware fault.
The monitor's STOP was a response to telemetry failure, not evidence that
the monitor itself caused the crash. Cleanup was not confirmed successful.

Microsoft identifies [bugcheck 0x116 as VIDEO_TDR_FAILURE](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x116---video-tdr-failure):
recovery from a graphics timeout failed. This identifies a failure category,
not a proven driver defect, defective GPU, heat, power, VRAM exhaustion or
training-code cause. Parameter three is preserved as `0xffffffffc000009a`;
no specific resource shortage is inferred from it here.

The earlier Event 6008 shutdown time of 07:41:26 is not used as the onset of
this incident. Windows also records an earlier 07:41:08 boot and continued
logging afterward. Original timestamps and complete XML are retained rather
than forcing them into a misleading twenty-minute outage narrative.

## What is recoverable

The fit attempt is `54f9b9548c33481bb44bd21ca40e88e8`. Its failure record is
valid and cites `states/update_000000.pth`, SHA256
`ea673c5604a9fc5744c7d369cc0d2f1b8d8884ea118b61755177ac2628be2229`.
CPU-only deserialization verifies the exact identity, epoch/batch/update zero,
empty losses and Adam state, correct optimizer settings, 644 finite CPU tensors,
and unchanged BatchNorm references. CUDA remained uninitialized during that
audit. This is a valid initial recovery state, not saved trained progress.

The incident audit passes 270 checks with no unexpected discrepancies. All 25
frozen parent dependency hashes and nine new code bindings match. Other fit
JSON, readiness records and telemetry parse, and all 38 cache receipts, native
frame joins and array headers/lengths verify. The 4.418 GB cache payload was not
rehashed in this targeted incident audit; normal cache reopening must still
verify its recorded payload hashes before reuse. An audit helper's initial NumPy
private-API error and corrected public-API attempt remain preserved separately.

The supervisor's `finished.json` has the expected filename and 493-byte length
but contains only NUL bytes. It is corrupt and remains untouched. Its final
return code, forced-stop flag and remaining-process count cannot be recovered
from that file or reported as success. Surviving telemetry, console output and
the fit failure record are separate evidence. Post-reboot process inspection
finds no Python training/supervisor process. Do not reset this attempt or
replace its corrupt summary with a fabricated completion record.

## System evidence and operating state

Windows reports a 6,423,664-byte dump at
`C:\Windows\Minidump\102626-18781-01.dmp`. This session can read its metadata
but Windows denies content access. The matching WER report is also inaccessible.
No WinDbg/cdb installation was found in the queried package, PATH or standard
locations. No debugger was installed, privilege escalation attempted, driver
changed, registry setting changed, stress test run or GPU retry launched.

CPU driver inventory reports RTX 5070, NVIDIA driver `32.0.16.1656`,
`oem11.inf`. No responsible-driver stack was decoded. The bounded exports contain
323 System events from 07:35 through 08:03, with complete XML; no Display,
`nvlddmkm` or WHEA provider event appeared in those windows. Absence of those
events does not exclude a graphics driver or hardware fault.

The three graphics extras were confirmed stopped before the failed GPU attempt.
Lively and MSI True Color restarted with Windows. Their absence before the run
did not prevent this incident. GPU work is now operationally withheld while
the crash is investigated; this is a response to observed failure, not a new
claim that Ryan revoked the approved experiment. Do not retry automatically or
silently reduce batch size, resolution or precision. The next useful step is
authorized local dump analysis and a concrete stability/recovery decision.
The already approved labels and quality criteria do not need renewed approval.
Protected evaluation remains closed.

## Preserved evidence

- [Frozen approved execution](ball_tracking_nba_resolution_execution.md) and [recipe](../configs/ball_tracking/proposals/wasb_resolution_v0_1.json).
- [Original interrupted attempt](../data/outputs/ball_tracking/wasb_resolution_v0_1/fit_v0_1/attempts/54f9b9548c33481bb44bd21ca40e88e8/failed.json).
- [Monitor timeline](../data/outputs/t/nba_resolution_restart_20261026/MONITOR_TIMELINE.md) and [bound machine-readable timeline](../data/outputs/t/nba_resolution_restart_20261026/monitor_timeline.json).
- [CPU event/dump review](../data/outputs/t/nba_resolution_restart_20261026/cpu_event_dump_review_20261026T1510.json).
- [CPU integrity audit](../data/outputs/t/nba_resolution_restart_20261026/incident_audit_20261026T151254792630Z.json), SHA256 `a76c8623daf4fc668885db155fed8a5d9952b0d8708c96bc664793f005f76b23`.
- [Status page](../data/outputs/ball_tracking/wasb_resolution_v0_1/index.html).

All earlier model results, accepted labels, high-school work and historical
checkpoint-recovery records retain their original status. This interruption
provides no new evidence that the resolution method passes or fails ball quality.

## Subsequent local dump analysis

Ryan subsequently supplied a local copy through administrator PowerShell.
The [completed WinDbg analysis](ball_tracking_crash_dump_analysis_2026-10-26.md)
resolves the access blocker and identifies NVIDIA `nvlddmkm.sys` / version
616.56 in the failed graphics-reset path. This does not establish the underlying
cause or permit a GPU retry. The original access-denied observations and failed
attempt above remain preserved as recorded at that time.
