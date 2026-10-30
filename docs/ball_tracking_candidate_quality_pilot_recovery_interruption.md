# Candidate-quality recovery interrupted again, October 28, 2026

The directed continuation ran after Windows verified both 32 GB RAM modules at
5200 MT/s and Ryan reported EXPO disabled. It again lost CUDA/NVIDIA access.
Windows recorded a **141 NVIDIA graphics-engine timeout** at the same time.
The memory change alone did not prevent the failure. The underlying cause is
still unresolved; this result does not exonerate RAM or prove a defective GPU.
No further GPU retry is authorized or launched by this record.

## What actually happened

Attempt002 started at 15:28:13.628 Phoenix. It restored the original first-epoch
checkpoint and continued the same first fit at epoch two. Actual CUDA RNG,
parameter and optimizer restoration checks passed. All 87 replayed updates
matched the first attempt's recorded loss and gradient norm exactly. This is a
specific reproducibility witness, not a claim about every hypothetical future
update or a new model comparison.

It completed epoch two and recorded 213 further updates in epoch three. The
console then reports `torch.AcceleratorError: CUDA error: unknown error` while
moving the next input batch to CUDA. The supervisor also lost NVIDIA telemetry.
Its stop signal interrupted creation of the worker's `failed.json`, which is
absent. The original console, journal and supervisor receipt preserve failure;
absence of the worker receipt is not success. No completed fit, scoring output
or scientific comparison exists.

The supervisor finished at 15:31:12.744, certifying **zero remaining owned
processes**, no job-cleanup error and no forced job termination. Its process exit
code was 3221225786, alongside the console's final KeyboardInterrupt. This is
different from attempt001's corrupted final supervisor receipt, which remains
unchanged. The valid attempt002 receipt does not certify GPU/Windows recovery.

Across 86 telemetry samples, peak GPU temperature was 62 C, peak GPU memory
3137 MiB and peak power 155.34 W. These samples do not show overheating or full
GPU memory; they cannot exclude brief transients, other temperatures, power
delivery problems or hardware defects. The same installed driver remains
616.56 (Windows version 32.0.16.1656).

## Windows evidence after Ryan's restart

Ryan reported restarting after the GPU fault. Current boot is 15:33:23.500
Phoenix. Both modules still report configured speed 5200. EXPO state remains
user-reported rather than independently read from BIOS. No Python worker was
present in the post-reboot snapshot.

The bounded query from 15:27 inspected 152 System and 41 Application events.
System has Kernel-Power41 with BugcheckCode0, and no new 0x116 receipt. No new
minidump appears in the accessible Minidump listing. The unexpected-shutdown
event's embedded 15:10:14 timestamp is not treated as this fault's exact time.

Application WER has a 141 LiveKernelEvent at 15:31:15.217 and a later archived
report at 15:31:32.498 with the same report ID. Its bucket names
`LKD_0x141_Tdr:6_IMAGE_nvlddmkm.sys_Blackwell`. These are two receipts for one
report, not two additional crashes. Two companion1b8 watchdog reports occur at
15:31:17; their cause is not independently interpreted here.

Microsoft describes141 as a display-engine timeout recorded in a live dump,
not itself a Windows stop code. Thus this is a newly confirmed graphics hang,
not a newly proven identical0x116 blue screen. Earlier analyzed0x116 failures
remain evidence of failed graphics recovery.
[Microsoft141 reference](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x141---video-engine-timeout-detected).

WER identifies `C:\Windows\LiveKernelReports\WATCHDOG\WATCHDOG-20261028-1531.dmp`.
Ordinary filesystem access is denied; the new dump has not been analyzed or
uploaded. No elevation, ownership change or permission bypass was attempted.
Its existence is reported by WER, not independently confirmed by a readable
file. Missing dump access limits diagnosis, but does not erase the event record.

## Saved progress, audit and budget

The independent standard-library CPU audit records587 new returned updates and
18,770 training candidate presentations. Cumulative physical lower bounds are
1048 returned training updates and33,508 training presentations, plus the
original32-presentation parity forward. Unknown unjournaled activity remains
unknown. No scoring calls or completed fits occurred.

The epoch-two checkpoint retains748 logical updates. Its43,271,595 bytes match
SHA-256 `49cb7ebce977266def654893e3705f0bc9d4cae80c2989369f4233944451db7f`;
all176 ZIP member CRC checks pass. Tensor finiteness, optimizer semantics and
future recovery readiness were not revalidated in this no-Torch audit. The213
later recorded updates /6816 presentations are unsaved. The original first
checkpoint and all17 bound attempt001 files remain unchanged.

Policy creation to certified worker cleanup is179.116348 seconds, rounded up
to180. Adding the existing474-second conservative debit yields654 consumed
seconds and **2946 seconds (49m6s) remaining**. The later user restart is after
certified worker exit, so it is not charged as continuing worker execution.
No earlier debit is refunded, no fresh hour is granted and remaining time is
not permission for another attempt.

## Reading, interpretation and next operational decision

Reuse the completed full-history/research review, original frozen pilot and
recovery specification; NBA, cosine nine, accepted labels, all weak/native/
hidden/uncertain/missing cases, adverse e01/visibility/history and evaluation
gates remain unchanged. This is operational diagnosis, not a new scientific
direction. No fresh full-transcript or every-paper reread is claimed.

Targeted reads covered maintained source-map/current-state/decision/agreement/
validation/roadmap entries, the October28 dump report and its earlier-history
review, prior remedy review, actual recovery console/journals/receipts, new
Windows events, restored-checkpoint record and independent partial audit.
The earlier review found recurrent faults predating this pilot and current
driver, with symptoms outside training and only temporary benefit from driver
updates. Application isolation and this memory change have not established a
cure. Training can trigger the problem without explaining that older history.

The next diagnostic review is preserved in
`recovery_preparation_v0_1/recurrence_diagnostic_review.json`. It refreshes the
official NVIDIA release information before choosing a clean-install candidate;
the earlier621.01 suggestion must not be reused without that review. A clean
supported driver installation remains a proposed operational intervention, not
a release-note-proven fix or authority to install/reboot/retry automatically.
Power, GPU/PCIe, firmware and other hardware remain alternatives if controlled
software work fails. No new driver, BIOS setting, stress test, model or data
change occurred in this post-fault investigation.

The refreshed recommendation is one official clean installation of desktop
Studio617.42, preserving5200/EXPO-off and other settings. This is a diagnostic
judgment, not a claim that Studio is inherently better for PyTorch. Earlier
ordinary updates reportedly helped temporarily; the exact prior clean-install
method is undocumented, so this is not asserted to be an entirely untried route.
NVIDIA's newly inspected621.12 notice documents an RTX50 video freeze introduced
by621.01 and describes the hotfix as optional beta. That regression cannot
explain failures on installed616.56, but makes blindly selecting621.01 unwise.
[Official hotfix notice](https://nvidia.custhelp.com/app/answers/detail/a_id/5938),
[Studio617.42](https://www.nvidia.com/en-us/geforce/drivers/details/280101/).

The Studio page's WHQL label conflicts with the live lookup's IsWHQL=0 field;
this discrepancy remains unresolved. Full release-note PDFs and installer
internals/signature were not inspected; no installer was downloaded. Before an
approved installation, preserve display/profile settings, verify the official
desktopx64 installer signature and version, close GPU applications, use Custom
Advanced / Perform a clean installation, and arrange the reboot. Clean install
resets driver settings. Preserve the new watchdog dump first if Ryan can supply
an administrator-readable copy. No claim is made that this dump will isolate
the cause. Installation and any later workload validation require explicit
direction; neither follows from this recommendation.
[NVIDIA installation guidance](https://nvidia.custhelp.com/app/answers/detail/a_id/10/kw/recording%20video).

## Preservation

Ignored evidence is under
`data/outputs/ball_tracking/candidate_quality_pilot_v0_1/recovery_interruption_v0_1/`:
post-reboot snapshot, denied live-dump-access receipt, documentation snapshots
and verification. The independent partial audit/helper are in the existing
`recovery_preparation_v0_1/` folder. Raw attempts and freezes remain unchanged.

All78 prior worktree bindings pass before these additive notes; their previous
bytes are preserved and each insertion can be removed exactly to recover the
prior file. This extends the original47/Session17 preservation chain. Branch
`codex/ball-detector-baseline`, HEAD `8c040fca385dd8fffa0d7a13c45c53e79950bae1`,
empty index. No staging, commit, push, PR or merge.
