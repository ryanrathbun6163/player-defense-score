# Ball-tracking completion plan

Date: 2026-10-21. **Approved; first execution increment prepared.**
The [approval record](../configs/ball_tracking/reviews/ball_tracking_completion_campaign_approval_v0_1.json)
preserves Ryan's statement and binds the exact approved plan at `faa2804`.
The [first increment](ball_tracking_completion_first_increment.md) now delivers
the retained baseline, fixed NBA source/episode roles and 120 assisted references
subsequently accepted by Ryan. No new fit or protected evaluation has run.
Planning evidence baseline:
`codex/ball-detector-baseline` at
`759f43db37ba810ccf6516b2cdfd37a542dc5619`, clean when planning began.

## Recommendation and finish line

Keep the existing three-frame WASB ball model and the reviewed player pipeline.
Replace the sequence of small selector/verifier experiments with one adequately
sampled, validation-selected training campaign. Allow one conditional
higher-resolution fit, then make a definite acceptance or rejection decision.
Do not continue the DINO crop veto, start another model tournament, or extend
the campaign with threshold searches after seeing its results.

The agreed finish line remains **reviewed ball trajectories across the three
curated possessions, synchronized player/ball playback, explicit missing
intervals, quantitative errors, and a repeatable configuration-driven run**.
These clips contain 499, 499 and 500 frames. Existing development playback
exposes 1,273 frames; 225 holdout/buffer positions remain protected. A masked
development video is useful progress, but cannot establish full-clip completion.

NBA transfer remains an essential development direction for the eventual Castle
case study. It must not silently change this milestone into reliable tracking
across arbitrary broadcasts or entire games. Report NBA transfer separately;
full-game validation, possession understanding and defensive scoring remain later
work. A curated success must be described with its same-game and training-exposure
limitations, not presented as an unseen-game benchmark.

## Why this route survives the evidence review

The [research collection](research/README.md) covers ball models, detectors,
player tracking, geometry, datasets, complete sports systems and evaluation.
Its recommendations were checked against the subsequent local experiments;
decisive official sources were refreshed. This is not a claim to have reproduced
every cited paper or reopened every historical URL.

| Evidence | What it supports; what it does not establish |
|---|---|
| [Expanded WASB adaptation](ball_wasb_expanded_adaptation_results.md): doubling accepted NFHS training labels from 75 to 150 raised fixed-threshold development matches from 98 to 120/145. The 0.3 candidate reached 130/145. | Task-specific temporal training has produced substantial improvement here. It has not completed continuous tracking. |
| [NBA pilot](nba_wasb_native_pilot_diagnostic_results.md): retained model matched 120/120 accepted easy positions across two games. | The existing architecture can localize an NBA ball. These short, selected scenes are not a generalization benchmark. |
| [NBA continuation](nba_wasb_adaptation_results.md): 300 SAC + 150 NFHS training frames, 200 updates; SAC training matches 218→265/270, excluded DET 207→206/237, NFHS 130→129/145. | More exposure to the same narrow scenes improved fitting without improving transfer. Neither an optimizer failure nor proof that fine-tuning cannot work. |
| [Saved heatmap diagnosis](nba_hard_example_heatmap_inspection_results.md): 58/69 misses lacked above-threshold local ball evidence in every contributor. [Candidate preservation](nba_candidate_preservation_experiment.md) recovered availability in nine of 45 unavailable cases, leaving 36 absent. | Selecting or joining existing points cannot recover most absent image evidence. Another selector-only diagnostic is not the next milestone. |
| [DINO verifier](nba_ball_distractor_training_results.md): 207/581 protected matches lost; 204 losses came directly from negative classifier decisions. | The single-crop classifier learned an unsuitable rejection boundary. It is rejected. Exact contributions of representation, sampling and labeling are not isolated. |

The [official WASB model](https://github.com/nttcom/WASB-SBDT) already uses three
RGB frames and predicts three location maps. We have implemented that central
idea. The [paper](https://arxiv.org/html/2311.05237v2) used basketball training
data from 70 games, whereas our NBA continuation used one. Its additional
target/loss and sample-mining methods are not all reproduced locally, but the
local binary-target loss matches an upstream baseline; it is not an identified
implementation bug. Copying the paper's epoch count alone is not a remedy.

TrackNet variants, TOTNet and BlurBall supply useful temporal/occlusion ideas;
their sport assumptions and available implementations do not establish a better
NBA solution here. DeepSport has relevant ball annotations but a different
camera/data setup. Prompted trackers can assist annotation but require discovery
and recovery decisions. Generic detector upgrades and crop embeddings have no
local evidence sufficient to displace the temporal ball model. These remain
research options, not additional arms of this campaign.

The process also needs correction: we spent too many increments improving
selection and documenting narrow experiments without a finalized numerical
phase exit contract. The useful infrastructure and negative results remain;
the next work must produce complete reference coverage, stronger training and
an integrated result. Progress is measured in verified usable trajectories and
closed decisions, not numbers of reports, tests or experiments.

## Accepted numerical exit contract

**Ryan accepted these new ball-phase criteria on 2026-10-21.**
They were proposed in this plan and are not the existing 95%/85% player gate.
They do not revise old experiment gates or turn failed experiments into passes.

Apply the following separately to each complete curated possession. Freeze a
human-accepted reference census before scoring the candidate. Use the existing
annotation protocol and inclusive ten-source-pixel localization tolerance.

| Requirement | Proposed passing condition |
|---|---|
| Correct automatic observations | At least 95% of localization-eligible reference frames have a selected center within ten source pixels. |
| Wrong automatic observations | No more than 1% of eligible frames have an emitted center outside that tolerance; report missing frames separately. Integer counts must satisfy the fraction, without favorable rounding. |
| Certain hidden/out-of-view ball | Zero coordinate emissions on frames confidently labeled hidden/out of view under the existing protocol. Unknown and partially visible states retain their actual definitions. |
| Continuity while visibly localizable | No missing run longer than 200 ms within a continuously eligible interval; no confirmed wrong-object run lasting 120 ms or longer. |
| Recovery after occlusion | First correct observation within 120 ms of eligible visibility returning; that frame and the next two consecutive eligible frames must all be correct. |
| Complete evidence | All 1,498 source-frame records, exact timestamps, explicit status and actual final frames; full synchronized visual review accepted by Ryan. |

Use source presentation timestamps, not an assumed NBA frame rate. A run's
duration includes each frame's display interval. A camera cut starts a new
segment; do not measure recovery across a cut. Occlusion terminates an eligible
run. If fewer than three eligible frames remain starting at the first correct
observation, report recovery as censored rather than claiming stability. List
every censored/unknown interval, its reason and the number of scored recovery
events. No occlusion event means recovery is not applicable for that clip. An
event that exists but cannot be assessed is inconclusive, not a pass. Likewise,
reference uncertainty that could conceal an excessive visible gap makes that
continuity decision inconclusive; an unknown interval cannot automatically split
a potentially failing run into passing fragments.

The 95% target limits total loss; the time-based gates prevent that loss from
being concentrated in the exact pass or recovery we need to analyze. The 1%
wrong allowance permits small isolated localization failures, not sustained
tracking of a head or hand. Quantitative passage is necessary, not a substitute
for trajectory review. Hidden points must remain missing rather than fabricated.

Freeze eligibility from source evidence, never from model success. Publish all
reference categories and their counts, including unresolved centers. Report
training-exposed, development and protected evaluation cohorts separately.
Unknown frames do not become hidden negatives or correct outputs. Use one
automatic-only series for matches, missing runs and recovery: inferred or
manually corrected points count as absent in that series. Separately check all
published trajectory points for hidden emissions and wrong-object runs.
Sparse or ambiguous evidence can limit the claim even when a percentage passes.

## One data package, with the roles fixed first

The main intervention is diversity of independent episodes, not a larger pile
of neighboring frames from one play. Proposed new NBA annotation scope:

| Role | Games and episodes | New native-frame judgments, at up to 60 fps |
|---|---|---:|
| Training | Existing SAC game plus two additional games; six new episodes per game: four 2-second windows and two 4-second recovery windows | Up to 2,880 over 48 seconds |
| Validation for checkpoint selection | One separate fresh game; the same six-episode/16-second pattern | Up to 960 |
| Existing replay/training | Retain 300 accepted SAC and 150 accepted NFHS training frames, deduplicated against new selections | No relabeling of accepted rows |

Use half-open timestamp windows and actual frame counts; the ceiling counts
new label judgments only. Extra native model-context frames add decode/storage
work, not labels. Select nonoverlapping new episodes across
distinct plays. Include ordinary visible movement as well as small/distant ball,
held ball beside hands/heads, pass/shot motion, blur, player overlap, and
occlusion/reappearance. Select scenes from source playback before new-model
predictions. Publish the observed category coverage and any unavailable category;
do not manufacture labels to satisfy a quota. If a required event is absent,
resolve source selection before freezing the package rather than start a fit
with a knowingly unsuitable validation set.

The existing DET game stays excluded from fitting and checkpoint selection;
it is already exposed development evidence, not an untouched test. TOR is also
development-visible and is not a substitute for a fresh validation game without
explicitly changing that claim. Keep entire parent games, replays and alternate
encodes in one role. Assign roles before constructing triplets; do not allow a
context frame to cross roles. Unlabeled context can support a triplet, but its
supervision is masked. Keep existing NFHS training roles, including the accepted
P003 training block at frames 416–440; add no P003 development or protected frames,
or any other development/holdout frames, to fitting. Disclose exposure of each
curated possession rather than claiming pristine held-out possessions.

In parallel, complete references for the 1,273 permitted curated frames by
reusing accepted labels and proposing only the missing coverage. This is an
evaluation deliverable, **not permission to train on all three possessions**.
The remaining 225 protected positions are handled only in final validation.

I prepare first-pass centers, visibility/uncertainty, full short overlays and
an exception list. Ryan reviews the complete overlays, corrects mistakes and
accepts labels in batches. Preserve AI authorship and original proposals.
Existing accepted references do not need another review. The rejected verifier's
unaccepted labels are not silently promoted into this training set.

[BARD](https://huggingface.co/datasets/GabrieleGiudici/BARD) is a practical lead
for individual game-organized clips, not ready-made ball-center labels. Confirm
access, native source quality and distinct-game roles before extraction; acquire
selected individual clips from three additional games, not whole-game downloads.
The [WASB setup](https://raw.githubusercontent.com/nttcom/WASB-SBDT/main/GET_STARTED.md)
also requires external SAM images and separate ball annotations; current access
is not a dependable critical path, and overlapping pretraining data would not
be an independent test. [DeepSport](https://ispgroup.gitlab.io/code/deepsport/)
offers ball-center/visibility image pairs, not ordinary native three-frame
sequences. Do not spend another research phase trying to avoid the small local
labeling package. Source-acquisition failure is a concrete data blocker to
resolve, not permission to substitute an excluded game.

## Training campaign: one primary fit and one conditional fallback

Start both possible fits from retained checkpoint
`09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98`.
Keep previous checkpoints and failed outputs intact. Freeze the accepted source,
label and role manifests plus the executable recipe before fitting.

**Primary fit:** WASB at 512×288, three chronological native RGB frames,
batch two, Adam at 0.0001, seed 1234, existing gamma-2 masked binary loss and
trainable parameters with batch-normalization running statistics frozen.
Keep the existing target rasterization, 2.5-working-pixel target radius and
supervision masks. This intentionally retains a tested objective. No new
loss, augmentation/mining system, crop policy or temporal resampling is bundled
into the first fit. The substantive changes are diversity, sampling/exposure
and validation-based checkpoint selection.

Use 25% NFHS training replay and 75% NBA samples, balanced across the three NBA
training games and then their episodes. These are declared design choices, not
claimed optima. An epoch is a fixed number of draws equal to the unique usable
training-triplet count; log repeat counts and distinct triplet/frame coverage.
Balance with shuffled queues so rare scenes get repeated without accidentally
omitting most of a larger episode. Define the deterministic schedule before
running; the word "epoch" must not hide unmeasured sampling coverage.

Run up to 20 epochs; validate each epoch. After at least five epochs, stop if
five consecutive epochs do not improve the selection rule. Save best and final
checkpoints. Do not select merely the last update or impose the old 200-update
limit. Validate on the fresh NBA package **and the existing 150-frame NFHS
development cohort**, with fixed identical contexts for baseline and candidates.
That NFHS cohort becomes an explicit checkpoint-selection set for this campaign;
it remains exposed development evidence. None of its labels enter training.

Include the retained model as epoch zero in selection. Within each NFHS
possession's existing development cohort and the fresh NBA validation cohort,
an eligible checkpoint must retain at least the baseline's correct matches,
with no increase in wrong eligible outputs or certain-hidden emissions. Rank
eligible checkpoints by total correct NFHS development matches first, then
correct NBA validation matches, then shorter worst eligible NFHS missing run,
then earlier epoch. A trained model replaces epoch zero only if it improves
this fixed ranking. If epoch zero wins, keep it and reject the primary model
for adoption. This targets the actual curated finish line while protecting NBA
performance. Passing selection is not passing the phase gate.

For both fits, epoch zero and every nonregression comparison use the retained
model's original 512×288 output policy. Re-evaluating its weights at 768×432
would be a different method and must not redefine the baseline.

Keep the strict `>0.3` heatmap threshold, aligned-contributor averaging, existing
mass-based selection and source-space scoring fixed. Do not use DET or the new
complete permitted curated reference census to select epochs. After selection,
compare once against the retained baseline on those sets, with matched context.
Require
no aggregate loss of correct matches or increase in wrong/hidden outputs within
each existing scored regression cohort, and retain both 60/60 NBA pilot controls.
This prospective screen does not replace any historical experiment's gates.
Publish individual gained/lost points as well as counts. The complete curated
exit contract remains the decisive phase test.

**The only fallback:** a separate WASB fit at 768×432 using the same initial
checkpoint, labels, sampling seed, loss, optimizer, exposure and selection rule.
Increase target radius from 2.5 to 3.75 working pixels to preserve its source-space
footprint; leave the ten-source-pixel scoring radius unchanged. The five current
sources are 1920×1080; new BARD clips can be 1280×720, so validate each source's
dimensions and transform separately. The working resolution provides 1.5 times
the linear sampling density while retaining full-frame discovery, but cannot
recreate detail absent from a source. Confirm compatible output shapes and memory with
a synthetic forward/backward check before the scientific fit. Approximately
2.25 times the pixels is a planning estimate, not a measured runtime guarantee.

Authorize that second fit only conditionally. After the primary fit, evaluate
the selected method (which may still be epoch zero) on the complete **permitted**
curated reference census. Apply the proposed phase criteria to its allowed
segments as a development screen, without claiming full-clip passage. If it
fails coverage/localization, classify every eligible error in each failing
possession from those already-reviewed frames. Directly visible small-ball weak
responses or near-center localization must account for a majority of errors in
each such possession. The potentially recoverable counts must suffice to close
its deficit to 95% matches and at most 1% wrong outputs; affected runs must also
have a plausible path to the continuity limits. This uses the same cohort and
denominator for the failure and the fallback rationale, not NBA errors to explain
an NFHS failure. If no trained checkpoint qualified, the retained model's census
can justify the fallback under these same conditions; rejection is preserved.

Do not invoke resolution when distant distractor switches, certain-hidden
emissions or unresolved reference evidence independently block acceptance.
Report the census and deficit calculation, not hand-picked examples. The trigger
supports trying resolution; it does not prove that those errors will be fixed.
No sealed test is inspected to choose or justify the fallback.

No third fit, new cutoff grid, DINO veto, motion-rule search or alternative-model
tournament follows within this campaign. Paper-specific loss/mining, learned
visibility or a different architecture would require a new evidence-based
decision after this campaign closes. Operational retries needed to fix genuine
tooling defects preserve consumed work and are not disguised scientific trials.

## Delivery, resources and sequence

The verified local machine has an RTX 5070 with about 12 GB VRAM, 63 GiB RAM
and roughly 1.29 TiB free disk. Prior WASB fits used about 1.87 GiB allocated GPU
memory at batch two. Buying hardware or cloud training is not the next step.
The old trainer cached about 3 GB of preprocessed triplets for only 450 reference
frames; scale with a bounded loader or unique-frame cache instead. Decode each
source once, reuse accepted assets, and avoid retaining every epoch's full
heatmaps. Keep selected-checkpoint evidence needed for reproducibility.

For roughly 3,300 training triplets, extrapolation from measured local throughput
puts 10–20 primary epochs around 0.6–2.3 hours of training, excluding decoding,
validation and media. Profile the first epoch and update the estimate. Allow
approximately one working day of compute for the campaign and review outputs,
with 50–100 GB of working storage; these are planning allowances, not arbitrary
limits that justify convoluted implementation. No unapproved paid compute.

Human review is the likely scheduling constraint. Checking up to 3,840 new NBA
frames at an assumed 2–5 seconds per frame is 2–5.3 hours before corrections,
source playback and difficult cases. Budget roughly 4–8 hours for that package,
plus the remaining curated references and final trajectories. Calibrate the
estimate using the first 120–240 proposed frames. This is an estimate, not
measured review speed or a request for Ryan to enter thousands of coordinates.

| Milestone | Concrete output and completion decision |
|---|---|
| 1. Make the current foundation usable | Reuse saved retained-model observations and reviewed player exports to produce one indexed, synchronized development package across all three possessions; protected frames remain masked. Show current errors and missingness. No new model needed. |
| 2. Finish one reference package | Complete permitted curated references and the fixed multi-game NBA package; review all short overlays, accept/correct labels, freeze roles and manifest. Show actual coverage and unknowns. |
| 3. Train and decide | Fix loader scaling, run primary fit and fixed evaluation; invoke the single resolution fit only if its stated condition holds. Deliver baseline/candidate scorecard and synchronized comparisons, including failures and final frames. |
| 4. Freeze and test the complete clips | Only a candidate passing development screens proceeds. Freeze weights and policy, obtain protected-evaluation authorization, review protected reference labels without candidate overlays, then evaluate once. Deliver all 1,498 frame records and complete videos. |
| 5. Close or explicitly reject | Ryan reviews actual final tracks. If all requirements pass, integrate the reusable ball output and publish the phase result. Otherwise retain the baseline, publish the failed gates and choose the next scope explicitly. |

Aim for the first integrated development package in the first implementation
increment. The entire campaign is plausibly one to two focused workweeks if
sources are accessible and review time is available. That is a planning target,
not a promise of accuracy or completion by a calendar date. At each milestone
report usable output, elapsed effort, measured change and the next decision;
do not spend repeated sessions on another diagnostic without an actionable fit
or acceptance decision.

## Integration and final evaluation

Reuse the existing configuration, readers, scorer and renderer. Add only the
loader/training-selection functionality and ball-result integration that are
needed. Preserve reviewed player identity/calibration and their existing stage
outputs; no rerun of upstream player stages is justified by this ball-only work.
If an upstream reviewed decision really must change, identify its `--rerun-from`
stage and downstream effects before editing it.

The output contract records image-space center, native frame/time, model and
source provenance, confidence, status and explicit missing reason. Distinguish
image-based observations, inferred points, manual corrections and missing or
withheld frames. The default automatic evaluation uses image-based observations.
The accepted three-point bounded gap result stays preserved separately; it does
not authorize all fourteen continuous fills. Do not use inference to conceal
weak automatic coverage or map an airborne ball through a court homography.

Before the sealed evaluation, freeze the selected checkpoint hash, complete
inference policy, context rules, scoring code and exit contract. The 75 existing
holdout frames plus their 150 protected buffer positions remain closed until
that freeze and explicit authorization. Define and review their references
without candidate predictions first. Once opened, do not tune on them or call
them untouched again. A failed final evaluation remains failed; the optional
resolution fit must already have been decided on development evidence.

Publish full-clip per-possession metrics, exposed/training/holdout cohorts,
wrong-object episodes, worst eligible gaps, recovery events and every unresolved
interval. Complete transport checks must cover all frame records, synchronization
and actual finals. Use focused tests for changed behavior and actual producer/
consumer integration; broaden only when reach or failures warrant it. Existing
passed tests do not validate new code. No new audit/certificate framework.

Final deliverables: one frozen run manifest and repeatable command; one
frame-level result per possession; three synchronized player/ball videos; one
scorecard and concise result page; model/data provenance and reproduction notes.
Keep footage, weights and generated media ignored. Public portfolio material
should explain the pipeline, honest measured results, limitations and one or two
informative failures, using suitable shareable visuals. It must not imply that
defensive value, NBA player identity or full-game generalization is already solved.

If neither candidate qualifies, this campaign ends. Deliver the best valid
automatic result and a quantified explanation of the remaining gap. Ryan can
then choose a specifically justified architecture/data investment or a separately
labeled human-assisted trajectory product with correction effort measured.
Human correction is potentially useful for a portfolio, but cannot silently
replace the accepted automatic quality goal or be called automatic phase success.

## Decision and current execution boundary

Ryan requested reconsideration and a complete plan. This document is that plan;
no new source acquisition, source-pixel inspection, labels, inference, training,
threshold sweep or holdout access ran to produce it. Read-only research,
repository/result inspection and machine-resource checks informed the proposal.

Ryan subsequently approved the new numerical exit contract and the single
data/training/integration campaign, including the conditional second fit under
its stated trigger, and requested execution in a new session. That approval is
already recorded; do not ask for the same campaign approval again.
New reference acceptance and final trajectory review remain
human decisions. Protected evaluation needs explicit authorization after the
freeze; it is not silently included in a generic request to resume. These are
substantial scientific/evidence decisions under the
[working agreement](context/working_agreement.md), not routine tooling gates.

First execution action in the next session: assemble the
retained-baseline development package and select the fixed source episodes/roles,
while preparing the first 120–240 reference proposals to calibrate review effort.
No additional diagnostic experiment is a prerequisite. Existing accepted reviews
remain accepted; pending failed-verifier label/output reviews remain pending and
are not prerequisites for adopting a separately reviewed retained-model result.
