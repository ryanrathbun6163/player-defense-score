# Alternate-producer training coverage protocol v0.1

October 29, 2026. **Proposed information-gathering capture; unimplemented and
unrun.** The authorized metadata-only [coverage review](ball_tracking_candidate_training_coverage_review.md)
is complete. This document specifies its recommended next experiment; it does
not certify launch readiness, authorize an automatic GPU call, or start training.

## Question and one controlled producer change

Can one existing detector with no local NBA fitting produce a useful additional
supervision population on already accepted NBA training frames, before changing
the image-quality scorer or acceptance gate? The hypothesis concerns transfer
between proposal producers. It is not a test proving that missing coverage caused
the present failures, nor a claim that another detector is a better tracker.

Use exactly the expanded-NFHS checkpoint:

`data/outputs/ball_tracking/wasb/wasb_basketball_expanded_adaptation_v0_1/training/checkpoint.pth`

SHA256 `09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98`.
Its local adaptation used NFHS 150 and no project NBA frames. Global upstream
pretraining-game exposure is unknown. It was adapted at 512×288; the proposed
execution uses the current canonical 768×432 contract. This is a fixed-checkpoint
probe, not a clean causal test of training-game familiarity.

Keep the existing cosine-nine captures, quality models, J gate and original
choice policies as unchanged saved comparisons. No checkpoint tournament,
resolution arm, new model acquisition or parameter/threshold sweep.

## Exact permitted population and workload

Use the original accepted training package and its 21 NBA blocks only:

| Source | Accepted training frames |
|---|---:|
| CHI–IND | 960 |
| DEN–BOS | 960 |
| SAC–MEM, including retained SAC 300 | 1,259 |
| Total | 3,179 |

No HOU, DET, TOR, protected evaluation or NFHS image input is part of this
capture. NFHS appears only in the checkpoint's existing training provenance.
Preserve every accepted eligible, hidden and masked frame. No label changes,
new semantic judgments, exclusion of difficult frames or altered uncertainty
rules. Frame references are joined only after label-independent predictions and
candidate extraction are sealed.

The canonical complete stride-one triplet schedule contains 3,137 forwards
(sum of block length minus two) and produces 3,179 contributor means. Preserve
the existing source cadence, RGB preprocessing, 768×432 resize, float32 forward
and ascending-contributor float32 mean arithmetic. Stream caches/maps and retain
the exact per-frame contributor ledger, not just final selected coordinates.

Existing expanded-NFHS SAC caches are 512×288. Matching source PNGs alone does
not make their logits or means importable into a 768×432 capture. Therefore the
planned new work is all 3,137 canonical forwards with zero assumed imports.
Those old caches remain reused diagnostic evidence, not discarded results.
Any later discovered donor must match the complete checkpoint/input/context/
shape/contributor contract and be documented before launch; no silent substitution.

Architecture and cache compatibility are currently supported by metadata.
Implementation must verify actual pinned model/state compatibility before
launch, complete focused transport checks and independently review the concrete
producer. Reuse canonical forwards for output/reduction checks; this protocol
includes no extra neural parity forwards. Any material extra call requirement
must be recorded before the execution freeze. There are zero optimizer updates
and zero candidate-quality/gate fits in this experiment.

No measured runtime for this checkpoint at this exact workload is claimed.
Compute required raw-map storage from the bound shapes, include NPY/header and
metadata overhead, and inspect current free space during implementation readiness.
Reuse the existing supervised ownership/telemetry/fault-stop system and standing
Debug Mode ON policy for a later authorized GPU launch. Do not change settings,
repeat an earlier graphics experiment, or substitute CPU inference silently.

## Extraction and truthful target transport

Reuse the unchanged native extraction/selection and strict >.01 weak pool,
original merge radius and uncapped candidate construction. Preserve native
versus weak origin, every component, exact coordinates, padding and extraction
metadata, empty choices, threshold ties and unknown target states. No class or
case label influences extraction, score thresholds or candidate ordering.

Use the original known positive/distant/hidden target rules only for the saved
post-capture census. The original three CHI chosen errors remain boundary-unknown;
never relax placement uncertainty to create negative supervision. Do not use
historical semantic labels as geometric targets. Record exact point/crop overlap
with current training and historical registries; retain any role conflicts for
later explicit resolution rather than silently adding them to a fit.

New-producer choices are diagnostic. They do not replace the current native,
quality-top or recovery decisions. Keep both producers' chosen identities and
full candidate pools so apparent recovery gains cannot hide correct-point losses.

## Required outputs and predeclared coverage decision

Save all raw float32 frame means, forward/contributor accounting and numerical
checks, all component/choice records, frame registry, geometric
targets and a complete paired census against the saved cosine-nine population.
For every population retain candidate count, unique frame, source game, episode,
canonical source-video identity and consecutive-frame runs. A block boundary must
not manufacture a new physical run. Adjacent runs are not proof of independent
plays or statistically sufficient samples.

Report these three **producer-relative** conditions separately:

1. The new producer's chosen native point is a known distant negative.
2. The new producer emits a chosen native point in a certainly-hidden frame.
3. Its weak pool contains a known positive while its chosen native point is
   wrong or missing. Keep wrong-versus-missing recovery subgroups separate.

For the intended joint negative/recovery transfer experiment to be eligible for
design, each condition must occur in at least two permitted NBA games, and every
intended outer training fold must retain nonzero support for each condition.
This is a prospective engineering coverage screen, not a statistical power
calculation. Report actual run lengths and concentration without inventing
independence. Unchosen negatives do not satisfy selected-error coverage, weak
hidden points do not satisfy native-hidden coverage, and boundary-unknown points
never satisfy known-negative coverage.

Also establish whether the proposed additional population contains genuinely
new canonical point inputs, versus only relabeling an existing point's producer
or origin. Report exact-coordinate overlap, floor-centered crop overlap, and
source-frame overlap separately. If all useful inputs are duplicates, the
data-addition premise fails even if producer-relative names changed. New crop
geometry alone is not proof of a new visual object or scene. A later fit design
must specify what role-compatible inputs it would actually add.

Report the same opportunities relative to the **current cosine-nine choices**
as a separate descriptive view. Their wrong/missing training frames are fixed
and confined to CHI; changing proposals on these images cannot create cross-game
current-policy recovery situations. Do not impose an impossible cross-game gate
on that view or claim the producer-relative gate fills this real-world gap.

Include full positive retention, lost positives, all native/weak known negatives,
masked and boundary cases, empty frames, and the original 610 weak positives.
Keep all saved HOU recovery and below-.01 evidence unchanged as referenced
regression history; there is no new HOU evaluation or sampling in this capture.

Passing the screen permits only a concrete later producer-transfer design. It
does not authorize scorer training, select an acceptance threshold, establish
an improved tracker, or certify 95% generalization. The next design must isolate
added proposal population from changes to loss, image context and architecture,
and retain per-source correct/wrong/hidden plus exact recovery protections.

If any required category lacks coverage, or the useful population is entirely
duplicate/uncertain/role-incompatible, stop this joint augmentation branch.
Preserve any narrower findings without silently weakening the gate or launching
a narrower fit. Do not respond with an outcome-selected checkpoint, resolution,
threshold or sampling sweep. A subsequent choice would explicitly compare new
permitted footage with a representation/visibility diagnostic using this result.

## Implementation and execution boundary

Add a new consumer/runner without modifying frozen captures, source data or prior
analysis. Reuse tested schedule/reduction/extraction utilities where their
contracts match. Bind package, accepted references, source roles, cache arrays,
checkpoint, producer source, this protocol, test/review receipts and the actual
execution direction before launch. Verify no evaluation pixels enter the frame
store. Use an exclusive new output attempt, preserve partial/failure state, and
stop on identity, runtime, nonfinite, telemetry or graphics fault. No automatic
retry, checkpoint fallback or optimizer step.

The original cosine capture's assertion that native observations equal its
saved cosine-nine observations must not be inherited for this changed producer.
Keep source/cache/checkpoint guards, but compare extraction against this
producer's own saved means and independently reconstructed native components.
Differences from cosine-nine are paired outcomes, not transport failures.

The independent post-capture check must recount source/target identities, actual
calls and all missing/unknowns, raw-mean transport, extraction parity, old/new
paired results, novelty/role overlap and each coverage decision. It must not
rerun the model. Keep validation proportionate to this one producer change.

Current state: metadata feasibility/design only. No capture has started; no
implementation or execution freeze is claimed. Existing model/data roles,
95%-correct / 1%-wrong / zero-hidden, temporal and human-review requirements,
original worktree and the full prior handoff chain remain unchanged.
