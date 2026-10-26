# Ball-tracking successor assessment and TAPNext++ comparison

Date: 2026-10-25, America/Phoenix. This report follows Ryan's approval of the
[critical review](research/ball_tracking_next_step_review_2026-10-25.md) and
[concrete execution scope](ball_tracking_successor_execution_plan.md).
The GPU pause had already been explicitly lifted. No new labels, threshold
search, HLSM fit, resolution fallback or protected evaluation is authorized by
this report.

## Training-only assessment

The saved **epoch-five** model, not the selected epoch-zero baseline, was
evaluated on all 3,329 original training frames across 26 training blocks.
The actual frozen triplet contexts, preprocessing, masked loss and observation
selection were preserved. There were 3,277 inference calls: 3,103 supervised
triplets and 174 all-masked contexts needed for complete temporal observations.
There were no optimizer updates or model-tensor changes.

| Training source | Correct / eligible | Wrong | Missing | Certain-hidden emissions |
|---|---:|---:|---:|---:|
| CHI–IND | 828 / 836 | 8 | 0 | 3 |
| DEN–BOS | 920 / 920 | 0 | 0 | 0 |
| SAC–MEM | 1,053 / 1,055 | 2 | 0 | 0 |
| Possession 001 | 74 / 74 | 0 | 0 | 0 |
| Possession 002 | 31 / 31 | 0 | 0 | 0 |
| Possession 003 | 25 / 25 | 0 | 0 | 0 |
| Total | **2,931 / 2,941 (99.66%)** | **10** | **0** | **3** |

All 130 eligible NFHS training points match. The 147 certain-hidden and 241
masked unique frames remain separate from positive localization denominators.
There are 12 emissions when uncertain-hidden diagnostics are included; only
three are certain-hidden violations. Repeated temporal channels are not extra
independent examples: 9,114 valid channel occurrences include 6,026 repetitions
beyond 3,088 unique supervised frames. Masked channels contribute no loss.

Foreground contributes 51.17% of the measured loss numerator, visible background
48.65%, and certain-hidden frames 0.176%. These observations do not support a
claim that background pixels overwhelmingly dominate this trained model's loss.
The exhaustive single-triplet loss accounting is not the sampled batch-two
training curve.

The conditional epoch-six-to-ten continuation was **skipped**. Strong training
fit makes transfer to other frames a more useful next question than another
five epochs on the same examples. This is a resource-priority decision, not
proof that more training cannot help or that overfitting is the only cause.
The parent five-epoch result, checkpoints and original selection remain intact.

Evidence:

- [Actual assessment](../data/outputs/ball_tracking/completion_next_step_v0_1/training_assessment_epoch005/assessment.json)
- [Independent audit: 30,322 checks, zero discrepancies](../data/outputs/t/successor_assessment_audit_20261025/audit.json)
- [Recorded continuation decision](../data/outputs/ball_tracking/successor_campaign_v0_1/continuation_decision.json)

The independent audit rederived counts, roles, source joins and loss denominators;
raw loss numerators and model-state equality are supported by bound execution
assertions, not a second tensor/logit evaluation.

## Fixed temporal-model comparison

The approved challenger is the released TAPNext++ 512 model at source commit
`730cda1c730877cfedbe01bf87fb1cadb78a565d`, checkpoint SHA256
`6cd0e793fdcface3063d63f8ed3819bcf74c2c0468fe1fef85acee4de2f3609f`.
The 2,532,283,010-byte generation-pinned download matched its published MD5.
Its isolated einops dependency did not alter the existing environment.

Each of eight permitted blocks receives exactly one seed: the first finite,
in-image retained WASB point. The real query and 64 upstream support points
start a fresh recurrent state. There is no reseeding, detector fallback,
manual seed, interpolation, threshold search or selective frame evaluation.
The seed itself is provenance; even its frame publishes only TAP's own
predicted-visible, in-image point. Hidden coordinates remain diagnostics and
cannot enter automatic scores or trajectory overlays.

The adapter uses the pinned upstream image preprocessing and 256-coordinate
convention despite the 512-pixel image input. Source x/y scales are separate.
The full model uses float32 stored weights and CUDA float16 autocast, without
compilation or a smaller-resolution fallback. The prediction interface receives
native timing, the bound RGB image and retained detector output only; annotations
cannot enter it. All block outputs are sealed before label-dependent scoring.

The first compatibility attempt stopped before loading weights because an
import-integrity check rejected a valid namespace package. Its failure is
preserved. The correction has a regression check using actual upstream imports.
The second attempt completed four training-image calls; an independent audit
verified exact coordinate transforms, support queries, seed provenance,
visibility and native timing without scoring those frames or changing policy.

- [Compatibility attempt 001 failure](../data/outputs/ball_tracking/successor_campaign_v0_1/compatibility_probe_001/failed.json)
- [Compatibility attempt 002](../data/outputs/ball_tracking/successor_campaign_v0_1/compatibility_probe_002/completed.json)
- [Independent compatibility audit](../data/outputs/t/tapnext_probe002_cpu_audit_20261026/audit.json)

The interrupted first checkpoint download and its 1,287,651,328-byte partial file
also remain preserved. A new generation-bound range-download attempt produced
the verified checkpoint; no failed attempt was relabeled successful.

## Result: reject this fixed pilot

All 3,975 permitted frames completed: 3,947 actual recurrent model calls and
28 pre-seed missing frames. All eight outputs were sealed before scoring.
The candidate fails **12 of 13 guarded cohorts**; the other three cohorts remain
descriptive because of historical training exposure. The SAC 60/60 control
falls to 0/60 correct, and DET falls to 38/60. No candidate is adopted.

| Possession | WASB correct | TAP correct | TAP wrong | TAP missing | Certain-hidden: WASB → TAP | Longest eligible gap: WASB → TAP |
|---|---:|---:|---:|---:|---:|---:|
| 001 | 300/355 | 111/355 | 154 | 90 | 5 → 11 | 480 → 960 ms |
| 002 | 291/360 | 145/360 | 79 | 136 | 4 → 1 | 400 → 1,160 ms |
| 003 | 333/402 | 100/402 | 278 | 24 | 0 → 2 | 640 → 240 ms |
| Total | **924/1,117** | **356/1,117** | **511** | **250** | **9 → 14** | — |

There are **21 gained matches and 589 lost matches**, all gains in P003.
P003's smaller missing count is accompanied by 278 wrong published centers;
it is not reliable recovery. No semantic wrong-object identity is inferred from
coordinate error. The wrong-object review gate remains inconclusive.

The [independent actual-output audit](../data/outputs/t/tapnext_pilot_audit_20261025/audit.json)
passes **124,853 checks with zero discrepancies**. It rederives source/timing
joins, first-seed policy, visibility, native transforms, per-frame geometric
outcomes and cohort counts without importing the project scorer, loading models
or reading pixels. The retained baseline's original rows and counts reproduce.

All six NFHS initial seeds are within 10 pixels of the accepted center
(errors 7.33, 4.87, 3.61, 2.97, 4.96 and 8.27 pixels). That tolerance does **not**
establish that a point query lies on an actual visible ball pixel. The NBA seed
frames lack accepted references, so their correctness is unknown. This result
rejects the tested single-seed policy; it does not establish that every TAP
configuration or learned temporal approach is unsuitable. Reseeding or fusion
would be a new method, not a post-result repair of this experiment.

The original WASB baseline remains retained and still fails the permitted
completion screen. Neither extra training nor a new tracker has earned adoption.
No protected evaluation was opened and no full-clip/phase pass is claimed.

- [Immutable inference seal](../data/outputs/ball_tracking/successor_campaign_v0_1/tapnextpp512_pilot_v0_1/inference_sealed.json)
- [Full evaluation](../data/outputs/ball_tracking/successor_campaign_v0_1/tapnextpp512_pilot_v0_1/evaluation.json)
- [Completed pilot](../data/outputs/ball_tracking/successor_campaign_v0_1/tapnextpp512_pilot_v0_1/completed.json)
- [Retention decision](../data/outputs/ball_tracking/successor_campaign_v0_1/tapnextpp512_pilot_v0_1/retention_decision.json)

## Synchronized review delivery

The [five-video comparison](../data/outputs/ball_tracking/successor_campaign_v0_1/tapnextpp512_pilot_v0_1/review_attempts/dc8b3eaa31c04586a6ad6c1e1b046264/review/index.html)
shows retained WASB and the fixed TAP pilot on the same native frames. All
**4,200 displayed slots** are present: 3,975 permitted images and 225 protected
black positions. Encoded frame and packet timing, native display intervals,
serialized observation transport and all five actual finals were checked.
The original renderer's generic "selected model" caption means the comparison
candidate, not an adopted model; the page identifies it as the TAP pilot.

Curated final frames are 498, 498 and 499. NBA finals are SAC frame 2010 at PTS
3,023,342 and DET frame 11898 at PTS 17,868,662, each with its true 1,530-tick
final interval at time base 1/90000. No extra final hold is added. Root inspected
all five decoded final images for layout/transport; this is not Ryan's human
trajectory acceptance. The quantitative failure already rejects this policy.

- [Review publication](../data/outputs/ball_tracking/successor_campaign_v0_1/tapnextpp512_pilot_v0_1/review_publication.json)
- [Render summary](../data/outputs/ball_tracking/successor_campaign_v0_1/tapnextpp512_pilot_v0_1/review_attempts/dc8b3eaa31c04586a6ad6c1e1b046264/review/summary.json)

## Resources and PC observations

The training assessment's supervisor finished in **88.812 seconds**, with
44 samples and peaks of 59 C, 102.02 W and 2,553 MiB. The successful compatibility
probe finished in **12.422 seconds**, with peaks of 47 C and 4,780 MiB.
The full pilot worker completed in **534.725 seconds**; its supervisor finished
in **539.734 seconds**, with 263 samples and peaks of **64 C, 149.66 W and
5,009 MiB**. Each successful supervisor returned zero, with no stop condition,
forced termination, cleanup error or remaining owned process.

The supervisor samples every two seconds and owns the Windows process tree
before allowing the worker to run. It stops for failed telemetry, 80 C or an
active thermal slowdown, with graceful interruption before terminating only
its owned job. No clock, voltage, power-limit, fan or driver settings changed.

A [post-run query](../data/outputs/ball_tracking/successor_campaign_v0_1/post_run_machine_state.json)
found NVIDIA Overlay, Lively and MSI True Color absent; the GPU was back at 43 C
and 1% utilization. No matching Display 4101, NVIDIA, WHEA or Kernel-Power 41
events were returned for the assessment-through-pilot window, with no query
errors. This is a successful monitored workload observation, not proof that
the prior blackout cause is resolved. CPU video rendering runs afterward.

## Validation and preservation

The [focused-validation receipt](../data/outputs/t/successor_validation_receipt_20261026/validation_v2.json)
maps 38 passing checks: training assessment 10, owned GPU supervision 4, adapter
11, pilot transport 5, and evaluation/rendering 8. Recorded test-time hashes are
distinguished from current hashes where historical bindings were not captured.
Later decision-validation edits were exercised by actual preflight and execution,
not attributed retroactively to earlier tests. The full suite was not repeated.

All 25 original frozen dependencies remain unchanged. Accepted references,
original reviews, failed training attempts, update-500 recovery history and all
later checkpoints are preserved. Generated weights, images, videos and inference
records remain ignored. The 225 protected positions remain closed; human
trajectory acceptance and any full-phase acceptance remain separate gates.

## Optional next question, not an approved run

The [training-only seed-sensitivity proposal](ball_tracking_seed_sensitivity_proposal.md)
defines a small paired diagnostic: the same three existing training spans,
initialized once from the automatic WASB center or from the accepted fully
visible observed center. It requires **126 model calls**, no new labels, no
fitting and no protected frames. The primary readout excludes the three seed
frames in each arm, leaving 60 post-seed frames per arm. Based on measured
throughput, model execution is roughly 30–60 seconds; preparation and media
verification are additional.

This can test a basic seed/short-track limitation, but it cannot establish a
working automatic method. P002 has no qualifying training seed, the three
offsets are only 1.3–3.2 pixels, and the spans are short. A positive result would
not justify a larger pilot automatically; a negative result would not rule out
all effects of larger seed errors. Reference-seeded outputs would remain
diagnostic and could never count toward automatic phase acceptance. This is a
new scientific scope, left unapproved and unexecuted rather than silently
altering the completed automatic pilot.
