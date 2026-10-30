# Completion campaign: accepted package and primary training

The final curated reference group has Ryan's explicit acceptance: **“Accept all
269 proposals.”** This closes the permitted reference-labeling milestone. The
campaign approval already authorizes the primary fit after the accepted package
and executable recipe are frozen. No repeat fit approval is required.

## Latest result: primary fit completed; epoch zero retained, 2026-10-25

Ryan explicitly lifted the later stability pause and requested monitored progress.
Attempt `b898cdd299724f1b97a492cc77648462` resumed the original frozen run from
update 500, replayed the 22 unsaved updates and completed **five epochs / 7,760
scheduled updates**. The attempt took **1,060.663 seconds**; its supervisor took
**1,065.360 seconds**. Both earlier failures, their consumed work and the original
recovery state remain preserved.

Only epoch zero satisfies the fixed selection rule. At epoch five, P001 improves
**41→42** correct development matches and P002 **49→50**, but P003 falls
**40→38**. NBA validation improves **845→848/882** correct, **29→9** wrong and
**25→17** certain-hidden emissions. Those improvements do not override the
per-possession nonregression requirement. The trained model is rejected for
adoption; retained checkpoint
`09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98`
remains selected.

The supervisor collected **518 GPU samples**, spanning **44–60 C**, with maxima
of **133.27 W** and **4,253 MiB** used. No monitor flags, query errors or matching
new diagnostic events were recorded. NVIDIA Overlay, Lively Wallpaper and MSI
True Color remained stopped. This establishes a completed monitored attempt,
not a stability cure or the underlying cause of the earlier failures.

The [completed result and review report](ball_tracking_completion_primary_results.md)
records the actual selected-result transport check and fixed comparison:
**3,975 permitted frames / 16 cohorts**, unchanged baseline outputs and **zero
new model calls**. Permitted curated results are P001 **300/355** correct,
**12 wrong / 43 missing / 5 certain-hidden emissions**, worst eligible gap
**0.48s**; P002 **291/360**, **8 / 61 / 4**, **0.40s**; P003 **333/402**,
**8 / 61 / 0**, **0.64s**. All three development screens fail. The P001/P002
certain-hidden emissions independently block the approved resolution fallback.
No second fit or threshold change follows, and the 225 protected positions stay
closed.

The [independent actual-result audit](../data/outputs/t/completion_actual_result_audit_20261025_01/audit.json)
passes **104,212 checks**, re-deriving validation selection, every permitted
observation comparison, all cohort counts and integer deficits. It verifies
118 reference/acceptance bindings and both accepted inventory hashes. The new
orchestration and NBA renderer pass **19 focused CPU checks (12 + 7)**; their
receipts are distinct from the earlier 28 preparation checks and 32 fitting
implementation checks. No full-suite repeat was run. Three curated review videos
cover all 1,498 timeline slots with 225 black protected panels and verified
actual finals; the result report records the remaining delivery and human review
status.

The sections below preserve the earlier preparation, interrupted-run and pause
snapshots. Their statements about then-pending work do not supersede this result.

## Fixed roles

The complete curated census contains **1,273 permitted judgments**. New campaign
curated labels remain evaluation-only. Historical NFHS roles are retained:
**150 training frames** and the existing **150 development frames** used for
checkpoint selection. No protected labels or images enter the package.

The fixed NBA package contains **3,839 accepted judgments**: **2,879 training**
from CHI–IND, DEN–BOS and SAC–MEM, and **960 checkpoint-validation judgments**
from HOU–OKC. Retain the earlier **300 accepted SAC training frames**. Parent
games and their alternate encodes keep their roles; DET and TOR stay excluded
from fitting and checkpoint selection. The completed curated census is evaluated
only after selecting a checkpoint.

This gives **3,329 training frames in 26 blocks** and **1,110 selection frames
in 12 blocks**, with **3,103 usable training triplets**. Another **174 triplets**
have no supervised outputs and are retained as exclusions. Unknown outputs are
masked. The package records source identities, native timing, reference
authorship and acceptance. All **4,439 distinct source-frame images** are present.

The [validation-reference audit](../data/outputs/ball_tracking/completion_campaign_v0_1/training_implementation/validation_reference_coverage.json)
checks all 960 HOU–OKC frame/label/timestamp joins: **882 centers and 78 nulls**,
including **34 certain-hidden frames**. Frozen source reviews cover held ball,
ordinary movement, overlap, pass/shot and small/distant views. Accepted e05/e06
labels include occlusion followed by sustained eligible visibility. Events at
window boundaries and ambiguous transitions retain their censoring; this is
available reference coverage, not a claim about model recovery performance.

## Executable recipe

The [frozen recipe](../configs/ball_tracking/completion_campaign/primary_recipe_v0_1.json)
has SHA-256 `d8f53baf72412db535e989b4086e8fb23e02f79ef058829539d1bbe9a486e83c`.
The final producer rebuild and the real runner's read-only preflight both passed
before model execution. The recipe binds 25 local implementation dependencies,
the complete accepted package and all 20 planned epochs.

The primary fit retains WASB at **512×288**, starting from checkpoint
`09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98`.
It uses three chronological native RGB frames, batch two, fresh Adam at 0.0001,
seed 1234, the existing gamma-2 masked binary loss and 2.5-pixel target disk.
Batch-normalization running statistics remain frozen; all parameters remain
trainable. No augmentation, mining, threshold search or temporal resampling is
added.

The sampler allocates 25% of draws to NFHS replay and 75% to NBA, balanced over
the three NBA games and then their episodes. Persistent shuffled queues carry
across epochs. One epoch has exactly the number of usable training triplets in
draws. Cumulative quarter quotas use deterministic half-up rounding; actual
fractions, repeats and distinct triplet/frame coverage are recorded. An odd
draw count produces a final singleton batch rather than an extra sample.

The loader verifies accepted native PNG bytes and RGB hashes, performs the same
affine warp as the retained adapter, and stores each warped frame once as uint8
on disk. It assembles normalized float32 triplets on demand. This avoids scaling
the older cache of every complete float32 triplet. Partial cache attempts are
preserved; only completed, hash-verified blocks are reused after a restart.

The [NFHS input manifest](../data/outputs/ball_tracking/completion_campaign_v0_1/training_inputs_nfhs_v0_1/package_inputs.json)
contains all **300 historical training/selection inputs**. Five already approved
training blocks were prepared separately in **32.181 seconds**, with all 150 PNGs
matching a second native-PTS-trimmed extraction. The six existing clean validation
PNG sets were reused and verified in **6.628 seconds**. Older ACL-restricted review
directories were left alone. The package uses actual source PTS at timebase
1/12800: P001/P002 start at 512, P003 at zero, with 512-tick display intervals.
Original synthetic index/25 timestamps remain unchanged in historical records.
No new labels or model work were needed. Codec-internal reference dependencies
remain uninstrumented; successful preparation returned only permitted frames.

Epoch zero is the retained model. Validate it and each trained epoch on exactly
the same fixed contexts. Keep strict `>0.3`, ascending float32 aligned-contributor
averaging, component-mass selection and inclusive ten-source-pixel matching.
Within each of the three NFHS possession cohorts and the fresh NBA cohort, an
eligible checkpoint cannot lose baseline correct matches or add wrong eligible
outputs or certain-hidden emissions. Rank eligible checkpoints by NFHS matches,
NBA validation matches, shorter worst eligible NFHS missing run, then earlier
epoch. A tie retains the earlier checkpoint, including epoch zero.

Run at most 20 epochs. After at least five, stop when five consecutive epochs
have not improved the selected rank. Save the best and final checkpoints plus
resumable optimizer/RNG state and actual exposure. If epoch zero wins, retain it
and reject the trained model for adoption. Selection is not a ball-phase pass.

## Execution interrupted by GPU loss

The primary run started from local commit
`2aa2342e2f43a6a6365f579471971b9ecbd77cf9`. Its first attempt prepared and verified
all 4,439 unique source images in **122.340 seconds**, using **1,963,671,552 bytes**
of uint8 frame cache and no source-video decode. It failed during epoch-zero
validation after **141.409 seconds**, with a CUDA unknown error and **zero
optimizer updates**. Independently, `nvidia-smi` reported “GPU is lost” and
requested a reboot.

Ryan reported a restart and requested continuation. The same frozen run resumed,
reused the verified cache, completed baseline validation in **15.593 seconds**,
and entered epoch one. A second GPU loss occurred after **522 completed updates**
while attempting update **523**. The second attempt lasted **88.576 seconds**.
The latest durable state is **update 500**; 22 unsaved completed updates remain
in the attempt log and must be replayed on resume. No trained epoch has completed
validation, and no trained checkpoint has been selected.

The [read-only recovery audit](../data/outputs/ball_tracking/completion_campaign_v0_1/primary_fit_v0_1/gpu_recovery_after_attempt_02.json)
verifies the update-500 state, finite tensors and exact sampling history. Both
failed attempts, the update-zero state, baseline validation and image cache are
preserved. Last saved training peaks were approximately **2.01 GB allocated /
2.49 GB reserved** on the 12 GB GPU. Neither attempt reported an out-of-memory
error. The cause of device loss remains unestablished; no particular Xid,
driver defect, thermal problem or hardware failure is asserted.

The later [Windows error-reporting evidence](../data/outputs/ball_tracking/completion_campaign_v0_1/primary_fit_v0_1/windows_gpu_events_after_attempt_02.json)
contains live-kernel code **141** near the first failure and **117** with
`nvlddmkm.sys_Blackwell` near the second, plus black-screen diagnostic reports.
Microsoft defines [141](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x141---video-engine-timeout-detected)
and [117](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x117---video-tdr-timeout-detected)
as graphics-engine/driver timeouts. This corroborates a graphics-system hang,
without distinguishing the underlying cause. No driver, registry, clock, power
or system-restart setting was changed by the agent.

Baseline selection results are **130/145 NFHS matches, one wrong output and
14 missing**, and **845/882 HOU–OKC matches, 29 wrong and eight missing**, with
25 emissions on certain-hidden HOU frames. These are the retained model's fixed
selection-set results, not completed-campaign or full-possession results.
Protected evaluation remains closed. The same frozen run must resume with
`--run --resume` once GPU availability and repeated loss are addressed; no
independent restart, CPU fallback or recipe change is authorized by this failure.

## Black-screen investigation, 2026-10-25

Ryan subsequently reported that the screens turn off, fans spin hard, and the
keyboard/mouse remain illuminated. He requested investigation of whether our
work was responsible. The latest system boot was **14:16:05 America/Phoenix**.
The [read-only diagnostic evidence](../data/outputs/t/gpu_crash_investigation_20261025_142204/summary.json)
preserves seven days of relevant Windows events, hardware/driver versions and
post-reboot NVIDIA telemetry. These are local machine diagnostics, not scientific
evaluation results.

| Time, America/Phoenix | Evidence |
| --- | --- |
| October 23, about 14:05-14:07 | Windows recorded `0x116`, with `nvlddmkm.sys` as the suspected driver, plus graphics-timeout dump references. This precedes the primary fit; that earlier workload is unknown. |
| October 25, 09:04 dump / 09:07 report | Earlier NVIDIA black-screen diagnostic, also before the primary fit. Report time and dump-name time are distinct. |
| October 25, 13:33:29-13:35:50 | First primary attempt: CPU cache preparation followed by GPU baseline inference, then CUDA device loss; Windows graphics-engine timeout `141` at 13:35:54. |
| October 25, 13:54:53-13:56:22 | Resumed primary attempt: baseline inference then 522 completed optimizer updates; Windows `117` and black-screen diagnostics at 13:56. |
| October 25, 14:16:05 | Latest boot; Event 41 records an unclean previous shutdown with zero bugcheck code. It does not establish a power-supply failure or the precise preceding crash time. |

Our GPU workload is a strongly supported trigger for the two primary-attempt
failures. The earlier graphics failures show the problem predates this fit; they
do not establish whether earlier project work was running. Microsoft describes
[116](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x116---video-tdr-failure),
[117](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x117---video-tdr-timeout-detected)
and [141](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x141---video-engine-timeout-detected)
as graphics timeout/recovery failures. Driver/software, power delivery, cooling,
settings and hardware remain possible underlying causes. A driver module in a
failure report alone does not prove a driver defect. No WHEA event appeared in
the queried seven-day System-log selection; that does not rule out hardware.

The runner performs continuous single-process CUDA work with batch two and no
automatic restart loop. Read-only process and Scheduled Tasks inspection found
no running training process or project restart action. There is no recorded
temperature, power, fan-speed or utilization history from the failures. The
2.49 GB reserved-memory peak and absence of an out-of-memory exception do not
establish low electrical load. No specific CUDA kernel was identified as causal.

After reboot, the RTX 5070 responded with NVIDIA driver **616.56**, roughly
**40 C**, **0-1% GPU activity**, and **9-21 W** across two idle samples. The power
limit read **250 W**, matching the driver-reported default. These present-time
samples cannot establish temperatures, power transients or stability during the
crashes. CPU is Ryzen 7 7800X3D; board is MSI MAG B650 TOMAHAWK WIFI, BIOS 1.L0.
No user overclock/undervolt setting or PSU model has been verified.

Windows denied ordinary read access to the deeper live-kernel dumps and WER
archive report body. The first collection helper therefore ended after saving
the event and telemetry files; a separate summary preserves that limitation.
No permissions were changed or circumvented. No driver/BIOS installation,
registry edits, power/clock changes, reboot or stress workload was performed.
The next troubleshooting decision depends on Ryan's crash history outside
training and PSU/tuning details. Keep GPU fitting stopped during diagnosis;
preserve the same frozen run and update-500 state for eventual continuation.

### Build archive recovered after Ryan's reply

Ryan confirmed **the same behavior outside training** and pointed to his October
2025 build history. The original migrated account export contains **PC build
recommendation**, conversation `68df402f-fbf8-832b-b061-ac2b15334fb4`.
The [targeted archive evidence](../data/outputs/t/gpu_crash_investigation_20261025_142204/build_archive_evidence.json)
binds the source JSON and nine active-path messages, preserving user statements
separately from historical assistant advice. The October 10 cart names the
**Corsair RM850e (2025), 850 W, ATX 3.1/PCIe 5.1**, and **ASUS TUF Gaming RTX
5070 OC 12 GB**. Later user messages confirm possession of all build parts and
assembly, with **Corsair 3500X ARGB** explicitly replacing the earlier case.
Current OS metadata confirms the CPU, motherboard, RTX 5070/ASUS subsystem and
Crucial two-by-32-GB DIMMs, each configured at **6000**. The PSU has not been
physically inspected and Windows cannot verify its health from its nominal rating.

[ASUS specifies](https://www.asus.com/ie/motherboards-components/graphics-cards/tuf-gaming/tuf-rtx5070-o12g-gaming/techspec/)
750 W recommended system PSU and **one 16-pin** power connector for this card.
Therefore the archived 850 W choice meets the published capacity recommendation;
this is not grounds to replace it solely with a higher-wattage unit.
[Corsair's 2025 manual](https://www.corsair.com/ca/en/explorer/diy-builder/power-supply-units/corsair-rme-series-2025/)
lists a native 12V-2x6 cable, a separate 12V-2x6-to-dual-6+2 cable, and separate
PCIe 8-to-6+2 cables. Historical assistant messages repeatedly claimed the card
had two eight-pin sockets and gave conflicting port/cable descriptions. Those
claims are incorrect or unreliable, not instructions to replay. Ryan described
the card's included adapter, but the final installed cable route, seating and
condition remain unverified. Inspecting that actual connection is the next
useful hardware check; the archive alone does not demonstrate a wiring defect.

No user-confirmed manual CPU/GPU overclock or undervolt was found in the searched
export. The card's OC product name is a factory model designation. EXPO was
recommended in the build chat; a later August 2026 assistant interpreted a BIOS
photo as EXPO Profile 1, but its pixels were unavailable for independent review.
Today's 6000 configured-memory value supports a faster RAM setting without
establishing the exact BIOS profile or attributing the graphics crashes to RAM.
The August CRITICAL_PROCESS_DIED/SSD-firmware episode remains a separate issue.
Driver installation metadata reports NVIDIA 616.56 installed September 3, 2026;
no system changes or GPU workload were performed during this archive follow-up.

### Other diagnostic avenues and previous Codex work

Ryan asked to defer physical cable inspection and check other causes. He
clarified that this has recurred periodically since the October 2025 build,
including outside training, and that driver updates help for a while. The
October 12 chat **Diagnose recurring monitor and input**, ID
`01a13241-1dbf-71c3-8b3f-45baac4ab9a4`, was retrieved through the app. Its
[relevant turns](../data/outputs/t/gpu_crash_investigation_20261025_142204/prior_codex_investigation.json)
confirm the earlier 591.86-to-616.56 update and subsequent failures. Ryan then
said no other tuning, BIOS or cable changes had been made. He also described an
earlier no-display startup that recovered after removing power. The proposed
default-memory test was not recorded as completed; today's two DIMMs still
report configured speed 6000. These facts widen the investigation beyond a
specific training kernel or monitor cable.

The [expanded Windows history](../data/outputs/t/gpu_crash_other_avenues_history_20261025/summary_v2.json)
contains **17 distinct System 0x116 bugcheck receipts**, August 10-October 23,
plus graphics-memory-manager-associated 0x7e and 0x10e reports. Retained System
and Application logs start August 9. Graphics report rows span 23 dates but
include queue/archive duplicates; 265 rows do not mean 265 crashes. Three NVIDIA
Event 153 records identify GPU errors or TDR bus resets, without a specific Xid.
No WHEA or resource-exhaustion record was returned in this selection. Four SATA
controller resets occurred August 13, not near today's incidents. The initial
derived history summary had a dictionary-sort/group error and is preserved;
use corrected `summary_v2.json` with the unchanged raw records.

Current Windows is **11 Home 25H2, build 26200.9711**; offline update history
records October 15 cumulative **KB5127648**. The graphics-failure history
predates both that update and the September 3 installation of 616.56, so neither
alone explains original onset. Driver/software defects remain possible.
NVIDIA's documented CUDA 13.x driver minimum is 580; 616.56 is not below that
minimum. This is not a blanket compatibility or stability guarantee. Published
later browser-flicker/RDP fixes do not establish a cure for these local GPU-loss
incidents. A newer supported WHQL driver is a possible separate diagnostic
intervention, not an installed fix.

The [read-only machine findings](../data/outputs/t/gpu_crash_investigation_20261025_142204/other_avenues_findings.json)
show about 50,038,040 KiB free physical memory at sampling, an automatically
managed pagefile with zero current usage, and both NVMe drives reporting
Healthy/OK. These lightweight checks do not replace memory, storage or thermal
testing. NVIDIA Overlay, Lively Wallpaper, MSI True Color, MSI Center and Discord
were running; background graphics interaction is a testable possibility,
not an attribution to any of those applications.

[AMD specifies DDR5-5200 for two DIMMs](https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-7-7800x3d.html)
on this CPU. Configured 6000 is above that rating; an EXPO/default-memory
comparison remains a meaningful separate test, particularly given the startup
history, without proving RAM is faulty. BIOS 1.L0 is unchanged. No BIOS flash,
TDR registry edit, HAGS change, memory test, clean boot, app termination, driver
installation or stress test was performed. Current execution is not elevated;
protected crash dumps were not bypassed. Suggested next steps are a reversible
graphics-background-software isolation test, a separately evaluated clean
supported NVIDIA installation, and stock-memory testing if failures persist.
Change one diagnostic variable at a time; a brief crash-free interval is not
proof of resolution. Training stays stopped while diagnosis continues.

A subsequent [read-only NVIDIA App inspection](../data/outputs/t/gpu_crash_investigation_20261025_142204/nvidia_app_readonly.json)
visually confirms Automatic Tuning is off, GPU and VRAM tuning offsets are both
+0 MHz, power maximum is 100%, voltage maximum is 0%, and fan target is Automatic.
These are app settings, not proof of stock CPU/RAM settings or removal of the
ASUS card's factory overclock. The lightly loaded GPU displayed 43 C and 25 W;
these are not measurements from a crash. The Drivers page shows installed
616.56 and offers 621.01, released October 21. Its listed fixes do not establish
a match for these incidents. The app was opened and navigated only; no download,
installation, tuning scan or setting change was started. The original evidence
and prior recommendations remain preserved.

### Authorized background-app isolation, October 25

Ryan then explicitly authorized temporarily disabling the graphics extras and
keeping training paused. NVIDIA Overlay changed from On to Off in the normal
NVIDIA App Settings > Features control. The final UI explicitly reports Off,
and no NVIDIA Overlay processes remain. Game filters were already off.

Lively was running without any configured wallpaper (`WallpaperLayout.json`
contains `[]`). The normal Store launch opened its control UI, but both direct
EXE activation and its documented command-line shutdown returned Access is
denied. The exact verified main/UI process IDs were then stopped successfully;
subsequent process checks show no Lively processes. Settings and wallpaper layout
were copied before exit. Startup entries were not changed, so a restart may
reopen Lively. Restore by launching it from Start; restore NVIDIA Overlay via
the same Features switch when ending the diagnostic trial.

MSI True Color remains active as PID 19316. Registered MSI Center activation
exposed no targetable window, and stopping that verified process returned Access
is denied. No elevation or unrelated MSI service stop was attempted. Thus this
is a partial isolation test, not a completed clean boot or proof of a cause.
The 14:50 Phoenix process check found no Python, FFmpeg, Lively or NVIDIA Overlay
processes, with True Color and MSI's motherboard services still running.
No driver, BIOS, clock, fan or startup change was made; no training was resumed.
The [action receipt](../data/outputs/t/gpu_crash_investigation_20261025_142204/background_isolation_01/actions.json)
and [process snapshot](../data/outputs/t/gpu_crash_investigation_20261025_142204/background_isolation_01/after_processes.json)
preserve the exact scope and restoration steps. PowerShell serialized the empty
wallpaper array as null in the process snapshot; the copied raw layout remains
the authoritative `[]` record. Stability has not yet been established.

At **14:53 Phoenix**, after Ryan reported ending MSI True Color manually, a
[fresh verification](../data/outputs/t/gpu_crash_investigation_20261025_142204/background_isolation_01/user_completed_verification.json)
found no True Color, NVIDIA Overlay, Lively, Python or FFmpeg processes. MSI Case,
Center and Companion services remained running. The requested app isolation is
now established; training stays paused. This does not establish a stability cure
or reset display profiles previously applied by True Color. Restore True Color
through MSI Center when ending the trial. Preserve the earlier denied attempt
and partial-state records as history.

## Post-selection preparation while the GPU is unavailable

The additive evaluation-package builder prepares the six complete permitted
curated segments and the original complete SAC/DET action contexts. Its final
[preparation receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/training_implementation/evaluation_package_preflight_attempt_04.json)
passes in **39.967 seconds**: **3,975 verified PNG inputs, eight inference blocks,
16 named reference cohorts and no missing assets**. The curated portion retains
all 1,498 timing slots, with 225 protected positions carrying only withheld
metadata. Original references, exposure roles, baseline observations and both
60-frame pilot controls remain bound to their exact contexts.

The [prepared package](../data/outputs/ball_tracking/completion_campaign_v0_1/training_implementation/evaluation_package_prepared_inputs_v2.json)
is explicitly **not executable**: no completed checkpoint-selection result
exists. Seven focused package tests and actual retained-policy/component joins
pass. An initial metadata check failed because the older source parser expected
an FPS field for NBA records; the annotation dimension-bounds adapter fixes that
transport issue. All earlier attempts and producer versions remain preserved in
the [validation receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/training_implementation/evaluation_package_validation.json).
No model calls, scientific scoring or source-video decoding ran during preparation.

TOR remains a development-visible excluded game, but there is no existing fixed
TOR execution window or accepted reference cohort in the current selections.
No TOR screen was invented. The approved post-selection scope is the permitted
curated census and existing scored comparison cohorts, including DET and both
pilot controls. A completed selected-model result still needs its actual
producer/consumer transport check before any scoring or comparison rendering.

### CPU-only preparation completed before handoff

The package builder, pure scorer and synchronized comparison renderer now pass
**28 combined focused checks** (7 package, 17 scoring, 4 renderer), in **0.275s**
unittest time and **2.506s** process time. The
[combined receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/training_implementation/evaluation_focused_validation.json)
binds the exact six source/test files and complete log. Actual annotation parsing,
observation production, scoring, JSON transport and synthetic CPU video encoding/
decoding are exercised together. Invalid native timestamps, stale source/timing
joins, failed inference represented as an ordinary miss, and protected prediction
leakage are rejected. Wrong-object runs touching unknown scope boundaries remain
inconclusive unless the observed run already establishes failure; actual camera
cuts still terminate runs.

The initial renderer fixture used a 36-by-64 heatmap and failed four tests at the
production shape guard. Correcting it to the real 288-by-512 producer format
resolved that implementation-check failure. The final combined run passed on its
first execution; earlier package preparation failures remain preserved. No full
suite repeat was needed for these additive modules.

The [handoff integrity receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/training_implementation/resume_integrity_before_handoff.json)
passes 32 hash checks, including all 25 frozen training dependencies and the
update-500 state. No frozen fitting code changed. The prepared package remains
non-executable: no completed fit exists, so real selected-result transport and
the scientific inference/comparison orchestration are not yet completed. No real
model, scoring or comparison-rendering run occurred during this preparation.
Training remains explicitly paused and protected evaluation closed.

## Preparation validation before fitting

All **32 focused checks passed** on the final package, policy, runtime and runner
modules: native-frame/annotation joins, role and protected-band exclusion,
unknown supervision, exact preprocessing, balanced sampling, nonregression
selection, checkpoint transport and interrupted-run recovery. The
[validation receipt](../data/outputs/ball_tracking/completion_campaign_v0_1/training_implementation/focused_validation.json)
binds the actual source and test bytes; the full suite was not repeated.

The initial loader fixture had two invalid schema enum values; correcting those
and closing memory maps explicitly fixed the test failures. The first full
package preflight rejected SAC display intervals because a generic packet helper
used raw packet duration. The correction uses the existing SAC presentation
census and next-frame PTS, retaining original evidence. The corrected preflight
passed in **83.644 seconds**. A final package rebuild during the freeze also
checks all 300 NFHS joins against independently bound native packet records.
These were implementation checks, not scientific fitting attempts.

At this pre-fit checkpoint, **no completion-campaign model inference or optimizer
update has run**. Source labels, original review artifacts and failed attempts
remain preserved. The frozen recipe binds the accepted package, complete
20-epoch sampling schedule, implementation dependencies and runtime versions.
Each epoch draws 3,103 triplets in 1,552 updates, ending with one singleton batch.
Durable update logs and optimizer/RNG saves every 25 updates preserve recovery
evidence; completed epoch model files and validation reports are retained.

The single conditional resolution fit remains subject to the approved
[census and deficit trigger](ball_tracking_completion_plan.md#training-campaign-one-primary-fit-and-one-conditional-fallback).
The **225 protected holdout/buffer positions remain closed** until a frozen
method and separate explicit authorization. New model trajectories still need
Ryan's visual review.
