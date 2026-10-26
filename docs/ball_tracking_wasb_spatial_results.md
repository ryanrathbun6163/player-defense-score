# Two-epoch spatial augmentation results

October 26, 2026, America/Phoenix. The authorized two-epoch fit and complete
NBA comparison are finished. **Neither checkpoint passes. This pilot does not
support extending this spatial recipe automatically. No model is adopted.**

## What changed

The [frozen execution plan](ball_tracking_wasb_spatial_execution.md) starts from
the same completed 768 epoch-five model, Adam state and random-state history as
the earlier constant continuation. It adds exactly 3,104 optimizer updates,
ending at absolute epoch seven / 10,864 cumulative updates. The only new factor
is synchronized modest scale/translation of existing training triplets and
their targets. Labels, sampling schedule, original mirror/brightness draws,
learning rate, loss, input resolution and native evaluation are unchanged.
Saved constant epochs six and seven supply the matched controls without
repeating their training or inference.

The actual 6,206 draws include 3,127 applied spatial transforms, 3,067 probability
bypasses and 12 clipping fallbacks. CPU preparation verifies supervision
transport and representative transformed images before fitting. Accepted
references, frozen earlier code, failed attempts and checkpoint history remain
preserved. There are no new labels or protected-evaluation reads.

## Complete NBA comparison

Count cells are **correct / wrong / missing** at the unchanged ten-source-pixel
tolerance. HOU totals summarize six separately gated episodes; they are not a
pooled acceptance test. HOU is repeatedly used validation, DET inspected
development excluded from fitting, and SAC training-exposed. These are not
independent test or full-game results.

| Model | Absolute epoch | HOU /882 | HOU certain-hidden emissions | DET /241 | SAC /270 |
|---|---:|---:|---:|---:|---:|
| Parent 768 | 5 | 841 / 20 / 21 | 18 | 219 / 1 / 21 | 269 / 1 / 0 |
| Constant control | 6 | 837 / 25 / 20 | 20 | 219 / 1 / 21 | 269 / 1 / 0 |
| Spatial | 6 | 814 / 47 / 21 | 19 | 219 / 1 / 21 | 269 / 1 / 0 |
| Constant control | 7 | 842 / 20 / 20 | 20 | 218 / 1 / 22 | 269 / 1 / 0 |
| Spatial | 7 | 842 / 19 / 21 | 20 | 218 / 2 / 21 | 270 / 0 / 0 |

Epoch six loses 23 correct HOU positions against its matched control and adds
22 wrong outputs. Epoch seven recovers the HOU correct total, but relative to
constant seven its aggregate totals trade one wrong output for a miss and retain 20
certain-hidden emissions. In DET, epoch seven has the same number correct as
its matched control while its aggregate totals trade one miss for a wrong output. SAC gains
one correct position. This is a mixed outcome, not a broad improvement.

The equal epoch-seven HOU correct total hides four gains and four losses.
No HOU gate improves over constant seven. DET gains frame 11562 from missing to
correct but loses frame 11561 from correct to wrong. Two wrong DET positions
still remain below the 1% wrong-output limit; the deterioration is real without
creating a new wrong-fraction failure. HOU e01/e03/e05 still fail coverage,
e03/e05/e06 fail wrong-output rate, and e05/e06 emit on certain-hidden frames.
SAC's perfect scored-position result does not clear its inconclusive continuity.

**Both checkpoints still miss every eligible DET frame 11075–11093: 19 frames,
317ms.** Neither improves the parent's 219/241 correct (90.9%). The 95% coverage
criterion requires at least 229/241 correct, alongside every other quality
requirement. Lower training loss from 0.00003232898 to 0.00003125827 does not
establish progress on this gap. An augmented training loss is also not directly
interchangeable with the earlier unaugmented diagnostic loss.

The [audited diagnosis](../data/outputs/t/wasb_spatial_20261026/spatial_diagnosis_20261026T205034591837Z.json)
retains both checkpoints, all exact gains/losses, per-episode gates, recoveries,
uncertain-hidden emissions and secondary NFHS comparisons. The original 512
controls remain in the complete evaluation. NFHS is secondary evidence and
does not change any historical acceptance or rejection decision.

| Secondary NFHS /145 eligible | Correct | Wrong | Missing | Certain-hidden emissions |
|---|---:|---:|---:|---:|
| Parent five | 126 | 3 | 16 | 0 |
| Constant six | 130 | 3 | 12 | 0 |
| Spatial six | 134 | 4 | 7 | 0 |
| Constant seven | 128 | 3 | 14 | 0 |
| Spatial seven | 135 | 2 | 8 | 0 |

Most secondary gains are in possession 001. The gain is retained as evidence,
but does not offset failures of the primary NBA milestone.

## Interpretation and review

This particular two-epoch intervention did not resolve the measured NBA failure
families. It does not prove that all augmentation, further training or another
architecture would fail. It also provides no measured basis to promise that
simply extending this same recipe will reach 95%. Preserve this bounded result
and use the remaining failure mechanisms to justify any next experiment.

Spatial epoch seven is the explicit **diagnostic review choice**, compared with
constant epoch seven. It is the final checkpoint, restores HOU coverage relative
to spatial six, and matches all scored SAC positions, while exposing the DET
and hidden-emission tradeoffs. Spatial six has better DET coverage; seven is
not declared an overall winner. This post-comparison choice is not adoption or
the frozen qualifying rule, which returns null.
The earlier cosine-nine checkpoint already has the same HOU correct/wrong/
missing and SAC totals, with fewer HOU certain-hidden emissions (19 versus 20)
and better DET results (219/1/21 versus 218/2/21).

The [result page](../data/outputs/ball_tracking/wasb_spatial_v0_1/index.html)
links the complete synchronized comparison: constant seven on the left,
spatial seven on the right. Human trajectory/object-identity acceptance remains
pending. Automated file-URL browsing was previously rejected by the browser
security policy; no workaround is used. Filesystem checks and exported-image
inspection are distinct from interactive playback verification.

The nine previously audited source-uncertain recovery events remain inconclusive
independently of model predictions. They require evidence-supported resolution
through an explicit reviewed process if resolvable, not more training or a
silent label upgrade. That separate limitation does not excuse actual detection
failures. All numerical and visual criteria remain unchanged; protected
evaluation stays closed pending a frozen method and separate authorization.

## Verification and resources

Twenty focused implementation checks passed before the frozen preparation
commit `297938e0088f71901c8f93c5d3592a97044b763c`. Independent CPU audits verify
the completed fit and complete comparison. Fit checks cover the exact parent
handoff, optimizer/random states, every scheduled update/augmentation draw,
frozen BatchNorm buffers, checkpoint recovery history and validation transport.
The NBA audit reconstructs all 5,404 saved native mean-map frames, verifies
7,324 observation rows, 5,396 new calls and 1,920 reused HOU observations.

| Workload | Elapsed seconds | Peak temperature | Peak power | Peak GPU memory |
|---|---:|---:|---:|---:|
| Two-epoch fit | 1,427.657 | 60 C | 134.56 W | 7,512 MiB |
| Complete NBA comparison | 280.172 | 60 C | 104.97 W | 2,993 MiB |

The supervised workloads total **28.5 minutes**, excluding preparation, CPU
audits, rendering and reporting. Both exit zero with no stop condition, cleanup
error or remaining owned process. The fit has one attempt and no replayed
updates. A metadata-only review-preparation failure from an incorrectly copied
hash literal is preserved with its draft; the actual saved control was unchanged,
and no model execution or rendering occurred in that failed preparation.

The post-run Windows System query at 20:50 UTC finds no matching graphics,
WHEA, power, bugcheck or unexpected-shutdown events since 20:15 UTC, with no
query errors. NVIDIA Overlay, Lively Wallpaper and MSI True Color remain absent;
GPU was 47 C at the check. No stress test or driver/clock/power setting change
was performed. A successful workload does not resolve the previous crash cause.
