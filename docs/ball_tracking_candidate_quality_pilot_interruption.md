# Candidate-quality pilot interrupted by graphics failure, 2026-10-28

The approved four-fit pilot started, but **the scientific comparison is incomplete**.
Only epoch one of the first fit has a valid recovery checkpoint. No held-game,
HOU or historical scoring output was produced. This is an interrupted execution,
not a rejected image-learning recipe or an adopted model.

Ryan explicitly approved the frozen four-run pilot, its one-hour supervised limit
and GPU monitoring, then asked to continue after another computer restart.
The exact approval remains in
`data/outputs/ball_tracking/candidate_quality_pilot_v0_1/execution_approval.json`.
It has not been replaced with a new model, recipe, threshold or training budget.

## What actually ran and survived

- Branch `codex/ball-detector-baseline`, HEAD
  `8c040fca385dd8fffa0d7a13c45c53e79950bae1`, empty index. All 72 prepared worktree
  bindings and 45 frozen execution bindings passed before launch and after reboot.
- The first fit was `leave_chi_out`. The durable journal contains 461 training
  starts and returns, 14,738 training candidate presentations, and one extra
  producer-parity forward over 32 candidates. These are recorded lower bounds
  after an unclean restart; lost unflushed activity cannot be excluded.
- Epoch one completed at 374 updates / 11,954 candidate presentations. Its
  43,272,971-byte recovery checkpoint matches the original recorded SHA-256 and
  passes ZIP CRC inspection. CPU-only loading verified all 42 trainable tensors
  (3,600,641 parameters), finite optimizer moments, optimizer step 374 for every
  parameter, and saved Python/NumPy/Torch/CUDA RNG states. CUDA remained
  uninitialized; no model was constructed or forwarded during this inspection.
- Both trained parameter groups changed from initialization. The first actual
  point-readout parity difference was 2.78e-17 and both groups received nonzero
  finite gradients. Final frozen-tensor parity was not reached; do not claim a
  completed end-of-fit check from these partial records.
- The next 87 recorded updates occurred after that checkpoint and are not saved
  as recoverable model state. A later exact continuation would preserve epoch
  one and explicitly account for any recomputation of this lost suffix.
- Epoch-one weighted online loss was 0.1773554. This changing-model training loss
  is neither held-out performance nor evidence that hidden separation succeeds.
  Gradient clipping was active on 338/461 recorded updates; preserve this as
  training-health evidence without changing the frozen objective mid-pilot.

The checkpoint SHA-256 is
`fad2666942384ef3131ac946a230564d1ef947f299d21b1c82afd59e9bbcdb84`.
The [independent partial audit](../data/outputs/ball_tracking/candidate_quality_pilot_v0_1/interruption_v0_1/partial_audit.json)
retains exact counts, bindings, limits and CPU inspection details. Original
attempt files and failures remain untouched.

## GPU monitoring and Windows evidence

The existing owned-job supervisor took 83 valid telemetry samples. The sampled
maximum was 61 C, 2,688 MiB of GPU memory and 156.26 W; thermal flags were not
active in the saved samples. The last valid sample, at 14:05:08 Phoenix time,
was 57 C. At 14:05:11 the supervisor recorded that NVIDIA telemetry failed.
Sampled temperatures do not rule out every hardware or electrical fault.

The supervisor's `finished.json` exists but consists of 441 NUL bytes. Its STOP
file also exists. Preserve both; there is no valid clean-exit or job-cleanup
certificate. A fresh process inventory after reboot found no surviving Python
worker. The damaged final receipt must not be overwritten with a synthetic
successful shutdown report.

Windows recorded a new boot at 14:10:15.5 and a bugcheck `0x116`, with Windows
Error Reporting naming `nvlddmkm.sys`. Microsoft describes this stop as a failed
attempt to recover the display driver after a timeout. This identifies the
graphics failure class, not its root cause or proof of defective hardware.
[Microsoft's 0x116 documentation](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x116---video-tdr-failure).

The report includes status `0xC000009A`, which denotes insufficient resources
for the failed request. It does not establish that this model exhausted GPU
VRAM; the saved memory samples are well below the device's 12,227 MiB total.
[Microsoft's NTSTATUS definitions](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-erref/596a1078-e883-4972-9bbc-49e60bebca55).

Installed display drivers are NVIDIA 616.56 (Windows version 32.0.16.1656) and
AMD Radeon 32.0.13066.12. The NVIDIA version is a released WHQL driver, but neither
its age nor this crash report establishes which replacement would fix this
machine. No driver, TDR registry setting, GPU clock, fan, power limit, startup
configuration or system service was changed.
[NVIDIA's 616.56 release](https://www.nvidia.com/de-de/geforce/drivers/details/278153/).

Lively was verified and temporarily stopped before launch; MSI True Color was
absent at the readiness check. Both appeared again after reboot. This does not
establish their process state at the instant of failure or prove either caused
it. The prior successful response capture and earlier graphics faults remain
separate evidence; a cool successful short capture did not establish a cure.

The Windows 6008 event's embedded shutdown time differs from the worker/telemetry
timeline. Preserve the original timestamps instead of forcing them to agree.
Using policy creation through the next observed boot conservatively debits
**474 seconds**, leaving **3,126 seconds (52 minutes 6 seconds)** of the approved
hour. This is an upper-bound accounting choice, not measured active GPU time.
The budget must not reset to a fresh hour after a restart.

## Work continuing and current access limit

The full-history/research reconciliation from the
[frozen protocol](ball_tracking_candidate_quality_pilot.md) remains applicable.
This step reuses that review and examines new execution evidence plus primary
Windows documentation; it proposes no new scientific method. All source roles,
NBA priority, cosine-nine control, uncertain references, historical failures and
human/numerical gates remain unchanged. There is no permission for a new selector,
labeling campaign, protected evaluation, driver installation or Git integration.

The best-supported immediate step is to inspect the actual crash dump before
choosing a repair or another GPU launch. Windows denies this process read access
to `C:\Windows\Minidump\102826-18890-01.dmp` (6,535,415 bytes). WinDbg/cdb is
already installed; no debugger installation is needed. No permission workaround
or privilege escalation was attempted. Copying the dump through an administrator
session into the existing ignored local interruption folder would allow local
read-only analysis without uploading it or changing drivers.

The next GPU run remains deferred while the repeated driver fault is unresolved.
Approval for the same pilot is retained, but recovery execution has not been
implemented or run. Do not overwrite `attempt_001`, rerun completed epoch one,
return to update-500, silently reset consumed resources, or treat this interruption
as a completed four-fit comparison.
