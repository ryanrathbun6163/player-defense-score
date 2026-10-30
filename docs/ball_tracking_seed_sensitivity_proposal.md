# Proposed training-only TAP seed-sensitivity diagnostic

**Not approved and not run.** Prepared October 25, 2026, after the fixed
single-seed TAPNext++ pilot failed. This document proposes one small, optional
best-case feasibility/seed-sensitivity experiment, not a confident route to
finishing the ball phase or a demonstrated cause of the failure. It
authorizes no model calls, implementation, training, labeling, policy change,
or protected evaluation. The original successor proposal and failed pilot stay
frozen. This is not a proposal to rescue that pilot by periodic reseeding.

## Question and reason

Does moving only the initial query from the retained automatic WASB center to
an existing accepted, fully visible observed ball center change subsequent
tracking on the same short training context?

The failed long-context policy does not answer this. Its six NFHS seeds were
within the ten-pixel localization criterion, but a point query can still land
outside a tiny ball. A tracked surface point is also not necessarily a stable
ball center during rotation or occlusion. The completed implementation/transform
checks do not establish which of these mechanisms caused the failures.

This differs from the already completed candidate-pool oracle: that experiment
asked whether saved WASB components contained a matching candidate; the proposed
intervention would change one input query to the learned correspondence model.
The prior candidate experiment recovered availability on nine development frames
while leaving 36 unavailable; repeating its aggregation/selection diagnosis is
not proposed. See [candidate preservation](nba_candidate_preservation_experiment.md#completed-comparison),
[regression mechanisms](nba_adaptation_regression_diagnostic_results.md#what-changed-in-the-saved-outputs),
and the [critical review](research/ball_tracking_next_step_review_2026-10-25.md).

## Exactly three paired contexts

Selection uses the existing frozen training package only: in each NFHS training
block, take its first localization-eligible, certain-identity frame marked
`fully_visible` with geometry source `observed_complete_ball_center`, then run
through that training block's existing end. Require a finite, in-image retained
WASB observation at that same starting frame. Do not move the start in response
to tracker behavior. This deterministic rule gives exactly these three spans:

| Source | Existing training block | Start–end, inclusive | Frames per arm | Post-seed frames per arm | Native first PTS | End-exclusive PTS |
|---|---|---:|---:|---:|---:|---:|
| P001 | `possession_001_frames_0250_0274_expanded_training_v0_1` | 250–274 | 25 | 24 | 128512 | 141312 |
| P001 | `possession_001_frames_0375_0399_expanded_training_v0_1` | 377–399 | 23 | 22 | 193536 | 205312 |
| P003 | `possession_003_frames_0416_0440_expanded_training_v0_1` | 426–440 | 15 | 14 | 218112 | 225792 |
| Total | Three contexts, two sources | | **63** | **60** | | |

All frames are 1920×1080 RGB, time base `1/12800`, duration 512 ticks per frame
(native 25 fps). Each arm makes one model call per frame: **126 calls total**,
three independent recurrent states per arm, no retries counted as successful
extra observations. The paired source duration is 2.52 seconds per arm.

"Training-only" describes the new TAP images, target frames and reference
labels. Saved automatic WASB seeds retain their original full permitted
temporal context: for example, the frame-250 observation can include original
contributors 248–249. Preserve that provenance; do not claim its historical
context was restricted to this training span. No new outside-training image
is decoded for the proposed diagnostic.

The seed frames are fully visible; subsequent frames retain their original
visibility/eligibility and are not asserted to be uniformly visible. The other
NFHS training blocks, P001/100–124 and P002/318–367, have no qualifying
fully visible observed-center seed. **P002 is absent.** Do not substitute a
partial/inferred center, add an example, or extend beyond these training blocks.

| Seed | Retained automatic center | Accepted reference center | Displacement | Accepted uncertainty |
|---|---|---|---:|---:|
| P001/250 | (332.3445510864258, 323.5513687133789) | (332.571, 322.286) | 1.285472 px | 1.715 px |
| P001/377 | (1142.757797241211, 610.9735107421875) | (1143.429, 608.571) | 2.494508 px | 3.834 px |
| P003/426 | (841.0465621948242, 250.71653366088867) | (843.429, 248.571) | 3.206139 px | 1.714 px |

The latter two references carry `motion_blur`. These small coordinate differences
are descriptive seed metadata, not a new confidence or acceptance threshold.

## Two arms; only the initial query changes

1. **Automatic-seed diagnostic arm:** initialize once at the exact saved WASB
   coordinate above, using the original retained checkpoint and record digest.
2. **Accepted-center-seed diagnostic arm:** initialize once at the existing
   accepted coordinate above. Record its reference binding and explicitly name
   the seed origin `accepted_reference`. Never disguise it as a WASB observation.

Use the same pinned TAPNext++ 512 checkpoint/source, 512-square image transform,
256 coordinate space, full-depth eager model, float32 stored weights/CUDA
float16 autocast, native frame sequence, and official 64 local support points
plus one real query. Generate each arm's support points around its own seed with
the identical official rule. Use fresh state at each declared start. Apply
strict visibility-logit `>0` and in-image bounds to both arms, including the seed
frame. Keep state while predicted hidden; publish no hidden coordinate as a
visible estimate. No fallback, internal reseed, fusion, crop, threshold search,
label correction, fitting, resolution change or artificial query-offset sweep.

Both arms must start at the same frame and see the same images through the same
end. Prior long-context pilot outputs cannot stand in for either arm: their
initial state and context differ. After initialization, the prediction interface
receives images/timing and recurrent state only. Subsequent reference labels,
eligibility, and outcome information cannot influence predictions. Seal all six
arm/context outputs before comparison.

## Strict membership and evidence binding

Before any image read, verify the frozen package SHA, original training role,
block ID, source-video SHA, exact frame/PTS/duration sequence, original annotation
and PNG bindings, and membership of every consumed frame in the original
`training_blocks`. Cross-check prepared RGB identity against the already prepared
permitted package; reject any protected, validation-only or evaluation-only
frame. The prepared package supplies saved pixels/automatic observations; its
post-selection role never grants training membership by itself. No raw video
decode is required. Verify all three seed predicates and recorded coordinates
exactly, preserving uncertainty. A discrepancy fails preparation; do not choose
a replacement seed.

| Existing input | SHA-256 | Bytes |
|---|---|---:|
| `data/outputs/ball_tracking/completion_campaign_v0_1/frozen_primary_package_v0_1/package.json` | `5615933dfbb43728a4c67a6c94665157f349f2562ad50bd2c9be02dc86181c9f` | 8885398 |
| `data/outputs/ball_tracking/completion_campaign_v0_1/selected_comparison_v0_1/package.json` | `82d7e6cf8e43e5a9677995d7283e7990c7e3b538b5f469f2159fecd2c360c3f6` | 14422474 |
| `configs/ball_tracking/annotations/possession_001_frames_0250_0274_training_expansion_v0_1.json` | `10fbde5c1565754d62755efeb1d6af18d9264ec42fde7dff45e88522da6d2590` | 14035 |
| `configs/ball_tracking/annotations/possession_001_frames_0375_0399_protocol_adjudication_v0_1.json` | `69aaf19f86f6a47cd507c17eb38186c4c1214979d29558cb5835561e567ba99f` | 14184 |
| `configs/ball_tracking/annotations/possession_003_frames_0416_0440_protocol_adjudication_v0_1.json` | `8e088da8db868e15bd06dd94824d2dcb3412e7772b504d71c286132b4a8149e6` | 13906 |

P001 source SHA is `5c42dad097a27873852d1555a71de36b890eb7bf287cf53ee1cdc693c31fcae6`;
P003 source SHA is `6b0088df4434ebcd9de84997f871f26698544ebdd237f46d1f4a39937cf40531`.
The saved expanded WASB checkpoint remains `09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98`.

The existing asset manifest is
`data/outputs/tapnext_assets/730cda1c730877cfedbe01bf87fb1cadb78a565d/attempts/20261026T000032Z_recovery_47fd97fb/ready_asset_bindings.json`,
SHA `c36702d60fcb7d56d373afffc44f307f279b984158dd8dc70d3fcdec8d5176bc`.
It binds source commit `730cda1c730877cfedbe01bf87fb1cadb78a565d` and checkpoint
SHA `6cd0e793fdcface3063d63f8ed3819bcf74c2c0468fe1fef85acee4de2f3609f`
(2,532,283,010 bytes). No new download or dependency installation is proposed.

## Readouts and stopping decision

The primary comparison is the **60 post-seed frames per arm**; the three seed
frames are reported separately. Giving an arm the accepted center must not earn
it a claimed recovery on that same frame. Keep each span separate, then provide
descriptive source totals. Report paired visible/missing outputs, source-space
center error and inclusive-ten-pixel matches on eligible references, wrong
locations, certain-hidden emissions, and first post-seed loss/recovery with native
timing. Preserve unknown geometry and boundary censoring. Do not pool these short
training contexts into an automatic accuracy or phase-pass claim.

Render three synchronized diagnostic comparisons, clearly captioning the manual
reference initialization. Verify emitted records, native timing, all decoded
frame identities and actual final intervals. Reference markers remain separate;
hidden raw coordinates are diagnostic records only. Human interpretation of
object identity remains separate from geometric distance.

- A clear sustained post-seed improvement from accepted-center initialization
  would establish sensitivity to these small seed changes. It would support
  considering an automatic bootstrap improvement in a separately proposed scope;
  it would not supply that improvement or authorize another run.
- If both arms lose the ball, these center corrections did not solve the tested
  failure. Leave this TAP route rather than add reseeding, offset searches, or
  another tracker parameter campaign.
- If both track these short spans similarly well, short-span correspondence is
  demonstrated but the long-context failure remains unresolved. Do not infer
  that periodic reseeding will work. End this diagnostic without a new TAP policy.
- Mixed results remain inconclusive and end this diagnostic. Do not choose a
  successful span, change thresholds, or use the complete development census to
  tune a follow-up.

This is an optimistic reference-initialization control, sometimes called a
diagnostic ceiling. It is **not a mathematical upper bound**: accepted centers
have uncertainty and are not verified persistent material points on a rotating
ball. Manual seeds cannot satisfy the automatic criteria or accept the phase.
The three short contexts cover only P001/P003 and do not test the larger seed
errors or long rollouts of the failed policy. No result restores that policy,
weakens any quality gate, or opens protected evaluation.

## Resource bound and next authorization

The completed fixed pilot took 534.725 seconds for 3,975 frames. Probe002's three
steady calls took 0.131–0.139 seconds each, with 6.599 seconds inside its four-frame
compatibility operation. At that measured throughput, 126 calls imply about
17 seconds of inference plus model loading and verification. Budget roughly
**30–60 seconds for model execution**, with preparation, focused checks and media
verification separately measured; this is an estimate, not a guarantee. Use one
serialized GPU job under the existing telemetry/process supervisor. Preserve
failure attempts and stop on the existing instability conditions.

No run follows automatically from this document. A new explicit scope decision
is required before implementation/execution. If approved, prepare a small
additive wrapper around the existing verified loader/backend, explicit
diagnostic seed-origin records, and an immutable result. No new framework is
needed. Keep all existing recipes, failed attempts, accepted references and
original reviews unchanged.
