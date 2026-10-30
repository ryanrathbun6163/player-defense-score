# Fresh-game diagnostic implementation and launch state

October 30, 2026. This records completed preparation, not a scientific result.

Ryan accepted all three presented reference sets with “ok I've reviewed them.
Move forweard chat.” The separate publication contains 360 AI-authored,
human-accepted frames: 310 eligible centers, 32 certain-hidden frames and 18
unknown frames. Original proposals, review media and uncertainty remain intact.
The whole game remains diagnostic development, ineligible for fitting or
checkpoint selection. Do not request reference or experiment approval again.

## Completed implementation

`src/ball_tracking/fresh_game_inference.py` implements the unchanged
[frozen protocol](ball_tracking_fresh_game_diagnostic_protocol.md). CPU-only
preparation verified the 360 source PNGs and made three native-frame input
caches. Reuse these caches; no model has run on the new sample.

Execution will use saved cosine-nine, original Q and saved CPU J. The exact
budget is 354 detector forwards, then ceil(K/32) Q forwards, where the complete
in-bounds candidate count and order are sealed before Q. No fitting, new labels,
threshold changes, selector changes, fallback, extra context, parity forwards,
protected access or automatic extension is included.

`src/ball_tracking/fresh_game_analysis.py` retains every frame and candidate,
fixed native/Q-top choices, strict-zero acceptance, unknown/OOB/missing cases,
full denominators and exact paired gains/losses. It distinguishes missing
matching candidates, wrong choices, rejected correct points and hidden emissions.
The all-frame source/exact-crop diagnostic renderer and independent saved-output
audits are prepared for use after a clean inference completion.

The 12 inference tests and 15 analysis tests passed, including actual producer
records passed through the analyzer. Independent implementation review passed.
The previous 12 source-reference tests and completed pixel/video audits are
reused rather than repeated. These checks are implementation evidence, not
performance measurements.

## Actual launch blocker

No scientific worker was launched. Fresh readiness rejected running Lively,
MSI True Color, and an unclassified X-VPN desktop graphics subprocess. Lively was
temporarily stopped under the standing isolation instruction. MSI True Color
PID 20968 remained running; Windows returned Access is denied when stopping it.
MSI Center exposed a privacy agreement, not an accessible True Color quit
control. Opening the known standalone True Color executable timed out and
exposed no targetable window. Ryan was asked only to quit True Color manually.

The exact X-VPN child and its same-executable main parent were inspected in the
saved snapshot. Additive readiness v4 classifies that specific desktop graphics
process with strict identity/role/parent checks. Eighteen saved-fixture checks
passed, including rejection of altered/missing identities, Lively and other
model runtimes. This is a routine inventory correction; it does not certify zero
desktop GPU activity or change the experiment. Original helper, rejected
readiness and original freeze/authorization bytes are preserved.

NVIDIA Debug Mode was observed OFF and restored ON under the standing project
instruction. The restoration and later ON observation are recorded truthfully;
this was not a no-settings-change session. Driver 617.42, 250 W, and both RAM
modules configured at 5200 MT/s were observed. A new live ON observation and
successful readiness capture are still necessary immediately before launch.

## Resume without repeating work

Use `C:/Users/Ryan/Projects/player-defense-score`, branch
`codex/ball-detector-baseline`, HEAD
`8c040fca385dd8fffa0d7a13c45c53e79950bae1`. No Git mutation is authorized here.
All artifacts below are under
`data/outputs/ball_tracking/fresh_game_diagnostic_v0_1/`.

1. Reuse `accepted/reference.json`, `inference_preparation/prepared.json`,
   `focused_checks.json` and `review/implementation_review.json`.
2. Verify True Color and Lively are absent. Capture a **new**, uniquely named
   Debug Mode UI observation; keep the old observation and restoration receipt.
3. Use `launch_v0_1/readiness_snapshot_v4.py --capture --ui-receipt <new receipt>`
   after verifying the completed readiness amendment. Do not run the old freezer
   again or overwrite any prior receipt.
4. Run only `launch_v0_1/run_supervised.py`, which owns the scientific and event
   workers. Preserve the 1800-second outer deadline and cleanup safeguards.
5. Verify clean completion and postrun Windows/process evidence, run the prepared
   independent neural-output audit, then the CPU analyzer into `analysis/` and
   its independent recount. Render all 360 frames and inspect actual successes
   and failures with exact model inputs before recommending an intervention.
6. Publish results and update maintained context. Three short event-clip starts
   from one game cannot establish cross-game accuracy or achievement of 95%.

The current state is **accepted and implemented; not run; waiting only for the
protected graphics app to be closed**. There are no new accuracy numbers.
