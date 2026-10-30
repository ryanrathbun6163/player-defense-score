# Repeated graphics crash: local dump analysis, October 28, 2026

The copied dump confirms **a graphics timeout followed by failed NVIDIA adapter
recovery**, causing Windows bugcheck `0x116 / VIDEO_TDR_FAILURE`. It reproduces
the October 26 failure signature. It does not identify the underlying driver,
memory, power or hardware defect. The approved candidate-quality pilot remains
interrupted, with its epoch-one checkpoint preserved and 3,126 seconds remaining
under the existing conservative one-hour accounting.

Ryan's administrator copy completed successfully. The 6,535,415-byte local dump
matches the copy receipt and SHA-256
`73440eac3429380e9921138bebfb70eb54a463e763b7de6eacc567496e0211e0`.
The already-installed Microsoft debugger analyzed it locally with Microsoft
symbols. The dump was not uploaded. No installation, settings change, memory
test, stress test, model forward, training retry or reboot occurred in this
diagnostic step.

## Findings and limits

| Evidence | What it establishes |
| --- | --- |
| Internal dump time 14:05:31.131 Phoenix, uptime 48m39.847s | The failure occurred 19.325 seconds after the saved telemetry error at 14:05:11.806. This is distinct from the later reboot/report registration time. |
| `nvlddmkm+0x1935300`; last-operation status `0xC000009A`; fourth parameter 4 | The same module offset/status/context pattern as the October 26 dump. |
| `dxgkrnl!TdrBugcheckOnTimeout`, adapter-reset and timeout-recovery worker stack | Windows tried and failed to recover the graphics adapter. `PROCESS_NAME: System` describes that kernel worker, not the original triggering application. |
| NVIDIA 616.56 / Windows driver 32.0.16.1656 | Current driver metadata and loaded-image timestamp, size and checksum agree with the prior analysis. Private NVIDIA function symbols are unavailable. |
| 83 saved valid telemetry samples: peak 61 C, 2,688 MiB, 156.26 W; last temperature 57 C | No sampled overheating or near-full GPU memory. Sparse samples cannot exclude a transient, other temperatures or electrical faults. |
| Kernel triage dump, missing recovery-context type, unavailable `MiVisibleState` | This dump cannot establish full memory/pool availability or decode the private NVIDIA cause. |

Microsoft defines this stop as failed recovery from a display timeout. Driver
software, memory configuration, cooling, power and defective hardware can all
contribute; naming NVIDIA alone does not distinguish them.
[Microsoft 0x116 reference](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x116---video-tdr-failure).

`0xC000009A` means an operation lacked resources; it does not identify VRAM,
system RAM, the page file or a model allocation as the exhausted resource.
The debugger's own analysis-memory peak is not the computer's crash-time usage.
[Microsoft status definitions](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-erref/596a1078-e883-4972-9bbc-49e60bebca55).

The PnP blackbox records problem 24 on `ROOT\SYSTEM\0001` at 13:17:39.813,
approximately 48 minutes before the crash and shortly after boot. A current
device lookup did not resolve it. The same identifier appears in the older
dump; no evidence here ties it to the NVIDIA PCI device or the crash. Loaded
AMD graphics and Hyper-V/VSM flags are likewise presence evidence, not causes.
No security feature, integrated GPU or timeout setting should be disabled on
that basis. The debugger's generic Windows 10 kernel label does not supersede
the live Windows 11 build 26200 inventory.

## Reconciliation with the earlier investigation

Actually read or reused for this decision:

- Read the complete [October 26 dump report](ball_tracking_crash_dump_analysis_2026-10-26.md),
  its linked primary analysis receipt through the independent history review,
  both new debugger logs and the current hardware snapshot.
- Read the maintained current-state hardware investigation, current decision,
  agreement and source-map entries; read the October 25 `summary_v2.json`,
  `other_avenues_findings.json`, and captured original turns from **Diagnose
  recurring monitor and input**. This is targeted original evidence plus reused
  history, not a fresh review of every chat.
- Reuse the completed full-project history/research reconciliation in the
  [frozen pilot protocol](ball_tracking_candidate_quality_pilot.md). No scientific
  direction, label, evaluation role or model recipe is changing here. No fresh
  every-paper or full-transcript reread is claimed.
- Independently correlate the new dump with seven days of System events and
  consult current primary Microsoft, AMD, MSI and NVIDIA documentation. Complete
  NVIDIA release-note PDFs were inaccessible; release highlights and support
  lists do not establish a fix for this machine.

The older audit found **17 distinct 0x116 System receipts from August 10 through
October 23**, predating the current driver's September 3 installation. Ryan
reported similar symptoms since the build and outside model training, with only
temporary improvement after driver updates. The fresh bounded seven-day scan
contains five matching 0x116 receipts, including three today. It also records
an NVIDIA BusReset TDR at 13:14:25, before the current pilot launched. Repeated
WER reports are not counted as distinct crashes.

No WHEA or resource-exhaustion provider events appeared in that bounded scan;
this is not a hardware-health certificate. Earlier application isolation and
the successful short response capture did not establish stability. Training is
a plausible trigger for this incident; it cannot explain the entire prior
history. The machine's underlying instability remains unresolved.

## Proposed next diagnostic: inspect and reduce memory configuration

Ryan now explicitly confirms: **"No, I haven’t tried that"** in response to
whether EXPO/XMP-off or lower RAM speed was tested. This closes the historical
ambiguity about the previously proposed default-memory investigation.

Current firmware-reported metadata shows two 32 GB Micron/Crucial
`CP32G60C40U5B.M8B3` modules in A2/B2 configured at **6000 MT/s**, with the separate
Speed field 5600. These fields do not identify the enabled BIOS profile or
measure live voltage. The Ryzen 7 7800X3D's published two-DIMM rating is
**DDR5-5200** for either rank configuration.
[AMD processor specifications](https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-7-7800x3d.html).

The best-supported next diagnostic is one controlled memory-configuration
change, after inspecting the actual BIOS settings: disable any active memory
overclock profile and establish a conservative speed at or below DDR5-5200,
with automatic timings/voltages. This is a diagnostic choice, not a diagnosis
of bad RAM. Running at 6000 can work normally; its presence alone proves no fault.
The new information from this test would be behavior with that variable removed.

The immediate user step is to save work, restart into MSI BIOS with Delete, and
provide the initial/OC settings screen before changing anything. MSI documents
F7 for advanced mode, the OC memory controls and F10 for reviewing saved changes.
Exact controls must be matched to the installed BIOS screen. Auto alone may
select a speed above the CPU rating; verify the resulting frequency instead of
assuming that disabling EXPO always means 5200. Do not load all BIOS defaults,
flash firmware or guess voltage values as part of this test.
[MSI AM5 BIOS guide](https://download-2.msi.com/archive/mnu_exe/mb/AMDAM5BIOS.pdf).

Preserve the existing settings before any change. After a user-approved change,
verify the configured memory speed and an ordinary successful boot, keeping
driver version and other settings fixed for comparison. A short quiet period
would be encouraging, not proof of a cure; another matching failure at verified
conservative memory settings would weaken the memory-profile explanation.
Any workload validation must be separately explicit or within the unchanged
pilot's existing approval, supervisor, remaining budget and recovery safeguards;
this report starts none and does not authorize a new stress test.

A clean supported NVIDIA driver installation remains a reasonable later
alternative. The independent driver review initially favored it, then revised
the ordering after reconciling the older history and the untried memory test;
both conclusions and their chronology are preserved. NVIDIA 616.56 already
meets CUDA 13.x's R580 minimum, so simple minimum-version incompatibility is
unsupported. Current Game Ready 621.01 WHQL supports this GPU/OS, but no inspected
release highlight proves it fixes this TDR. Firmware, GPU/PCIe, power and other
hardware remain open if controlled software/configuration tests fail. Ryan's
preference to investigate other avenues before physical cable inspection remains
applicable.
[NVIDIA CUDA compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html),
[NVIDIA driver 621.01](https://www.nvidia.com/en-gb/drivers/details/282478/).

## Preservation and evidence

Branch `codex/ball-detector-baseline`, HEAD
`8c040fca385dd8fffa0d7a13c45c53e79950bae1`, empty index. All 74 prior worktree
bindings were verified before this additive documentation. No frozen source,
proposal, input, approval or checkpoint is changed. Original Session 17 content
and the subsequent preservation chain remain intact. No staging or committing.

The diagnostic folder is
`data/outputs/ball_tracking/candidate_quality_pilot_v0_1/interruption_v0_1/driver_diagnosis/`.
It contains the original debugger logs, hardware snapshot, independent history,
driver/memory research and interpretation review, plus the bound analysis and
documentation-preservation receipts. The dump and generated evidence remain
ignored local files. The original interruption report/ledger remain unchanged
as historical records; their access-blocked next step is fulfilled by this
analysis. No new copy or debugger installation is needed.

The interrupted pilot's 374-update checkpoint, 87 later unsaved recorded updates,
corrupted supervisor receipt, all uncertainty and consumed time remain preserved.
The same approved pilot still has 3,126 seconds available; the internal crash
time does not automatically refund the conservative debit. Recovery execution
has not been implemented or run. NBA remains the goal, cosine nine the research
control; no model, selector, labels or protected evaluation is adopted or opened.
