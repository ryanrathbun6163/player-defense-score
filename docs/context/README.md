# Durable Project Context

## Wider-input pilot completed; ranking gain, no replacement, 2026-10-30

Ryan authorized implementation and execution of the reviewed dual-view experiment.
All eight six-epoch fits, final scores, CPU analysis and independent audits are
complete. See [the results](../ball_tracking_dual_view_context_results.md) and
configs/ball_tracking/reviews/dual_view_context_result_v0_1.json. Reuse these
outputs; the earlier design/unrun status is superseded. No model, selector,
threshold or replacement of saved J is adopted.

Held-NBA full-pool strict-first ranking is LC 2609/2811 (92.81%), Q 2542, LL 2551:
LC gains 69/loses 2 versus Q and gains 61/loses 3 versus LL. This is diagnostic
ordering, not emitted tracking accuracy. Both fixed-zero gates FAIL: LC loses
23 LL-kept correct policy identities; protected Q losses are 14 policy identities
and 1 weak candidate, with 0 HOU stress losses. Protection sets overlap. Saved J
remains stronger: fixed original-Q-top 2541/2811, versus LC 2317. Its fixed-choice
ceiling is 2542; acceptance alone cannot reach 95% on those original choices.

Of net 67 ranking gains versus Q, 66 occur on already-native-correct frames.
The sole native-missing gain remains LC-negative; no native-wrong case improves.
LC has no newly correct J-rejected fixed choice on held NBA or BKN. All LC fitting
targets have correct signs, so the model learned its fitting objective; the
remaining failure mechanism is not uniquely identified. BKN stays exposed
diagnostic/nonfitting, HOU veto/descriptive only, NFHS secondary, DET metadata-only.
Scorer-held NBA games were already seen by the detector; no global 95% claim.

The initial run stopped because a copied event watcher retained the old 30-minute
deadline, not because of a reported GPU fault. The failed attempt is preserved.
Shared-deadline repair and exact SAC-LC epoch 3 continuation reused five completed
fits and all captures. All 67 necessarily replayed loss/gradient-norm values match
exactly. Actual work: 28149 calls/899618 presentations/19807 updates, published
separately from logical 28082/897474/19740. Both launch charges total 48m03.516s,
within the original 90-minute allowance; CPU repair downtime is separate. Final
cleanup is clean, no qualifying fault, peaks 64 C/63 C, no GPU setting change.
True Color remains permitted; standing Debug Mode ON and other guards remain.

Next: CPU-only source/annotation feasibility and design for diverse actual
current-detector failures on additional permitted NBA games, correct controls
and separate evaluation. The old coverage census, 461-point Q+ addition, rank
overlap and curves are already complete; do not repeat or blindly tweak them.
More support is a justified priority, not a proven cure. No new fit, labels,
protected access or source-role reassignment follows automatically.

All 174 inherited working-file contents remain preserved through 165 unchanged
files and 9 reversible history additions. Both final audits pass; original
failure/auditor-correction evidence remains. Branch/HEAD and empty index remain
unchanged. This entry is the current completion and next-step state.


## Controlled wider-input pilot designed, 2026-10-30

Ryan requested an exceptionally critical, informative design. The concrete
[protocol](../ball_tracking_dual_view_context_protocol.md) and its machine-readable proposal are ready; three independent reviews
passed. Implementation, feature capture, fitting and scoring remain unrun.

Two matched arms compare duplicate-local LL with local-plus-192px-context LC.
Both retain frozen fold-specific Q local features, use the same generic DINO
auxiliary final-two-block adaptation, and learn a fresh point+CLS fusion head.
Saved Q/J remain separate controls. Extra capacity/training is controlled; field
of view and auxiliary scale still change together. Frozen features do not promise
preserved predictions. Saved-logit saturation ruled out a zero-residual primary
test; 7,426 existing distant negatives contain the reference center in the wider
crop, supporting explicit checks against accepting the wrong nearby point.

Eight fixed six-epoch fits are proposed: 19,740 updates; total future capture,
training/scoring/parity budget 28,082 backbone calls / 897,474 presentations.
Final fitting-health scores, full-pool ranking, fixed-zero policy gains/losses,
all protected Q successes and comparison to saved J are required. Fixed Q-top
choices have a 2,542/2,811 ceiling; filtering alone cannot reach 95% there.
No result may silently become a new threshold, selector, J substitution or fit.

Next is implementation of this exact protocol, CPU checks and executable freeze;
new neural execution is not authorized by design alone. BKN remains exposed
diagnostic/nonfitting; HOU remains veto/descriptive, never positive feature choice.
DET is metadata-only with no new query. Existing labels/results/hardware policy
and all 172 inherited contents remain preserved. See the design evidence under
data/outputs/ball_tracking/dual_view_context_design_v0_1/ and its design_freeze.json.
Every subsequent recommendation must state useful outcomes and limits before
running; failure need not uniquely identify a cause to supply bounded evidence.


## Input-context information screen completed, 2026-10-30

The authorized CPU screen is complete: 100 candidate points on 69 saved frames,
exact original local input versus unchanged local plus fixed 192px context.
See [the completed report](../ball_tracking_input_context_screen_results.md) and configs/ball_tracking/reviews/input_context_screen_result_v0_1.json.
Two score/reference-blind AI reviewers supplied 400 sealed qualitative ratings.
Four qualifying points on three frames in two frozen failure intervals gained
concrete cues; all are within one two-second BKN clip. All 46 jointly recognized
matched balls retained visual support. Eleven cases remain jointly unresolved.
This is limited input-information evidence, not model accuracy or a gain toward 95%.

Next: design one bounded close-up-plus-context representation pilot; preserve
the existing model/control and exact-success/hidden/weak-recovery protections.
No recipe, fit, new score or selector has run. BKN remains nonfitting; HOU can
only provide descriptive/regression-veto evidence, never positive feature choice.
SAC prior-AI illustrations are nondecision; DET was not opened. The stronger HOU
role was clarified additively before paired review; earlier flags stay archived.
Two focused tests and independent 3243/5464-check audits passed. Existing results,
references, checkpoints, original handoff and GPU operating policy stay intact.
This entry supersedes the unrun context recommendation; do not repeat the screen.


## Fresh-game diagnostic completed; True Color may remain running, 2026-10-30

Ryan clarified that closing True Color was only a temporary GPU troubleshooting
trial. History confirms no causal attribution. Retire that blanket absence
requirement; do not ask him to close it simply to run this experiment. Record
its actual presence and retain other hardware, worker, temperature and fault
checks. Five prior post-cable workloads completed cleanly over 55 minutes; that
does not prove a single hardware cause. Debug Mode remains required ON.

The approved fresh-game run and CPU analysis are COMPLETE. See the
[results](../ball_tracking_fresh_game_diagnostic_results.md) and
[all360-frame source/exact-input viewer](../../data/outputs/ball_tracking/fresh_game_diagnostic_v0_1/diagnostic_review/index.html).
True Color PID 20968 was observed before and after the clean 67.843-second run:
peak 54 C, no qualifying faults, no retry and zero remaining owned workers.
All 354 detector forwards,109 Q batches and 3480 J predictions completed once.
No fitting, new labels, thresholds, selectors, protected access or adoption.

Accepted population:310 eligible/32 certain-hidden/18 unknown. Correct/wrong/hidden
counts: native 298/6/2; native+Q 289/1/1; native+J 298/4/2; fixedQ-top 294/16/32;
Q-top+Q 290/10/2; Q-top+J 293/2/2. J retains every correct native point but still
emits wrong/hidden points. The 96.13% native result is conditional on three short
clips from one game, not attainment of the global 95% goal. Old reported results,
failed Q+ decisions and game roles remain unchanged.

The complete pool supports 305/310 eligible frames. Of 12 native failures, five lack
a matching proposal and seven have one. Six are weak-only;237/47 also has matching
unselected native components. RawQ-top gains 4 correct identities but loses 8.
Actual crops show spectator-head ranking errors, hand/ball confusion and hidden
emissions. Use these exact current-model cases alongside historical failures to
design the next discriminating comparison; no automatic unchanged fit/max-J/
native-first adoption follows. Reuse all saved outputs; do not rerun this study.

Independent neural/output and analysis audits passed 58452 and 321647 checks;
all 360 illustrations are saved and 974 exact-Q-input comparisons passed. A
corrected auditor cache-shape assumption is preserved without any scientific
rerun. All prior 166 contents are retained via 157 unchanged files and 9 reversible
documentation additions. Branch/HEAD and empty index remain unchanged. This
entry supersedes earlier pending-label, unrun and TrueColor-blocker statements.

## Fresh-game references accepted; implementation ready, 2026-10-30

Ryan accepted all three new reference sets and authorized continuing: "ok I've
reviewed them. Move forweard chat". See the [execution preparation state](../ball_tracking_fresh_game_execution_preparation.md).
The separate accepted publication contains 360 AI-authored, human-accepted
frames: 310 eligible centers, 32 certain hidden and 18 unknown. Original proposals
and review media remain unchanged. No repeat reference or experiment approval
is needed. The whole game remains diagnostic development, ineligible for fitting
or checkpoint selection.

Frozen saved-model inference and CPU analysis are implemented; 27 focused tests
and independent implementation review passed. Source-only caches are complete.
No model has run on this sample and no new accuracy result exists. Fresh readiness
stopped before launch: Lively was closed, but protected MSI True Color PID 20968
returned Access is denied and still needs Ryan to quit it. Debug Mode was restored
from OFF to ON under the standing instruction; preserve the truthful setting-change
receipt. Additive readiness v4 narrowly recognizes the observed X-VPN desktop GPU
child; 18 fixture checks passed, with original helper/freeze/rejection preserved.

Next: verify True Color is closed, obtain fresh Debug-ON and readiness evidence,
then run the existing supervisor once. Reuse accepted/reference.json,
inference_preparation/prepared.json, execution_freeze.json and the completed
readiness amendment under fresh_game_diagnostic_v0_1. Do not repeat preparation,
fit models, change selectors, reopen protected sets or claim progress toward 95%.
After clean execution, finish saved-output audits, full analysis and visual review.
All prior 160 file contents remain preserved through reversible additions; Git
branch/HEAD and empty index are unchanged. This entry supersedes the pending-label
and not-yet-implemented state below while retaining it as history.

## Fresh-game diagnostic: new reference review ready, 2026-10-30

Ryan approved moving forward with the bounded fresh-game diagnostic. See the
[preparation result](../ball_tracking_fresh_game_reference_preparation.md) and
[fixed protocol](../ball_tracking_fresh_game_diagnostic_protocol.md). Three
source-first BKN-DET clips (122/237/365, game 0022400861) supply 360 native frames:
310 AI-proposed centers and 50 null centers. All new labels remain pending human
acceptance; no detector/scorer inference, training or adoption occurred.

Complete native/slow overlays, original-frame viewers, exceptions and actual
finals are ready under data/outputs/ball_tracking/fresh_game_diagnostic_v0_1/review/.
All 360 source PNGs match alternate RGB decoding; 12 focused tests and all 720
encoded-frame checks passed. Prior 155 file contents/results remain preserved.
The actual next step is Ryan's review of this concrete new reference set, then a
separate accepted publication and implementation/run of the frozen diagnostic.
The experiment itself is already authorized; do not request its approval again.
The new whole-game role is diagnostic_development, ineligible for fitting or
checkpoint selection. Existing game roles and the failed Q+ result stay unchanged.


## Producer-transfer experiment completed; criterion failed, 2026-10-29

Ryan explicitly authorized implementing and running the designed experiment,
building on saved work and preserving all results. See the
[completed result](../../docs/ball_tracking_candidate_producer_transfer_results.md) and [result ledger](../../configs/ball_tracking/reviews/candidate_producer_transfer_result_v0_1.json). This supersedes
the earlier unrun progress statements below; original design and results remain.

One Q+ treatment added the 461 audited compatible points to the original NBA
population, retaining the original model, objective function and matched budget.
All four fits completed once: 9,870 updates / 315,432 training presentations;
1,014 scoring forwards / 32,341 presentations; four parity calls / 128 points.
Total 10,888 neural forwards / 347,901 presentations. Saved Q controls were
reused; no detector calls, J fits, new labels, protected access or adoption.
The supervised launch took 1,181.296 seconds, peaked at 63C, and ended with no
faults, settings changes, retry or surviving owned process. Debug Mode was ON.

The prespecified fixed-zero criterion FAILS. NBA native correct retention fell
2,309 -> 2,238, with wrong/hidden remaining 0/0. Fixed original-Q-top correct
retention fell 2,275 -> 2,215, wrong 99 -> 90 and hidden 28 -> 27. Correct retention
fell in every held NBA game; CHI and DEN gained wrong acceptances. HOU native
correct rose 798 -> 808 (0/0 errors/hidden), but quality-top rose 825 -> 836 with
wrong 6 -> 8 and hidden 3 -> 4. Net gains cannot conceal exact-success losses.
The protected sets lost 189 fixed-policy rows (182 NBA, seven HOU), 20 weak
candidate rows and four HOU stress probes. These views overlap; do not add them.

Source-held added challenges showed only positive 44 -> 45 (four gains, three
losses); distant-negative acceptances stayed 35 and hidden acceptances stayed 38.
Diagnostic strict-match-first frames fell NBA 2,542 -> 2,534 and HOU 862 -> 855;
NFHS rose 115 -> 118. Full curves contain crossing tradeoffs, so this is not a
claim that every operating point or every aspect of discrimination worsened.
No threshold is selected and no curve rescues the failed fixed-zero criterion.
The exact 21/6 named recovery-query Q signs remain unchanged (13/21 and 2/6
positive), while broader cases include regressions. All missing and historical
roles, complete contrasts and successful/failed evidence remain preserved.

All 45 focused checks passed. Independent neural and analysis audits passed
271,004 and 7,072,931 checks. Two audit-tool representation corrections and their
failed receipts are retained; no scientific output changed or neural work repeated.
The old caches remain unchanged; only 452 new crops were made from 385 PNGs,
and nine additions reuse old pixels with different fractional point inputs.

Keep Q/J controls and the prior reported J quality-top 90.39% result unchanged;
this run adds no gain toward 95%. Do not substitute Q+ into frozen J or launch an
automatic threshold/seed/weight/pool/epoch tweak. Failure is specific to this
population/weight/exposure intervention, not proof that all augmentation or image
representations fail. Any subsequent direction must reconcile this result with
the full prior history and research and identify new information before another fit.

All 147 inherited file contents are preserved: 138 unchanged, nine reversible
history additions, eight new source/test/report/ledger files = 155 current paths.
See data/outputs/ball_tracking/candidate_producer_transfer_v0_1/ for the run,
analysis, independent reviews and documentation_update preservation receipt.
Original handoff/Session 17 chain, branch/HEAD and empty index remain intact.



## Producer-transfer experiment designed, 2026-10-29

Ryan's latest "ok chat move forward" continued the bounded design recommended
after the completed alternate-producer coverage study. See the
[producer-transfer protocol](../../docs/ball_tracking_candidate_producer_transfer_protocol.md) and
[machine-readable proposal](../../configs/ball_tracking/proposals/candidate_producer_transfer_v0_1.json). Design and saved-metadata preparation
are complete; implementation, training and new scoring remain unrun.

Compare the original image-quality model Q with one Q+ treatment: retain all
18,813 original NBA candidate records and add the 461 audited compatible points
(304 distant negatives, 81 certain-hidden negatives, 76 weak positives).
All 3,179 frames, 3,433 original positive candidates and 610 weak positives remain.
No new scenes or labels; the million-point alternate pool is not a fitting pool.
Four future fits use the original representation, weighted objective function,
initialization and optimizer. Six frozen sampled cycles exactly match the old
9,870 updates / 315,432 training presentations; every eligible old/new example
appears. Reuse saved Q controls without refitting. Added all-NBA objective mass
is 8.46924%; weights, exposure, concentration and displaced old presentations
are explicit. Scoring and four parity calls bring the future total to 10,888
neural forwards / 347,901 candidate presentations; this is a budget, not a run.

Freeze original native and original-Q-top identities. Require per-game NBA
nonregression in correct, wrong and hidden outcomes, zero lost protected correct
identities, and a strict primary gain. Keep HOU as an exposed regression veto,
not fitting or threshold selection. A newly declared stricter veto also protects
every old-Q-positive known-correct weak point, including unchosen alternatives.
Retain all 21 HOU recovery cases, the six below-.01 cases, missing slots and
historical semantic roles. No threshold rescue, reranking, fallback or trajectory
claim. Saved acceptance model J is contextual only: changing Q would also change
J's input distribution, so integration requires a later valid design.

This isolates training-population transfer, not detector replacement. Of the 76
alternate recovery frames, 75 already have correct current native choices; the
other lacks original positive support but is not the current missing-native case.
The older producer natively recovers none of the four current wrong/missing cases.
CHI supplies 56/76 positives; DEN has one added hidden point; dense proposals can
produce chance geometric matches. No improvement toward 95% has been measured.

The accumulated history/research review was reused with targeted original
reports/code and primary research on decoupled classification, failure-directed
training and nested stacking. Independent population, workload, evaluation and
design reviews passed. Next is implementation of this fixed comparison with
focused checks and fresh supervised execution readiness; no extra arm, automatic
retry, settings change, new protected access or Git integration is included.

All 145 inherited file contents remain preserved: 136 unchanged and nine exact
reversible documentation additions; the new protocol and proposal make 147.
See data/outputs/ball_tracking/candidate_producer_transfer_design_v0_1/ for the
finite manifests, reviews and documentation_update preservation receipt.
Original handoff/Session 17 chain, branch/HEAD and empty index remain intact.



## Alternate-producer coverage capture completed, 2026-10-29

Ryan's "ok chat move forward my man" authorized implementing and running the
fixed capture from the completed coverage review. See the
[audited result](../ball_tracking_candidate_proposal_coverage_report.md) and
configs/ball_tracking/reviews/candidate_proposal_coverage_v0_1.json.
This supersedes the earlier proposed/unrun progress statements retained below;
the original protocol and all prior scientific results remain unchanged.

The expanded-NFHS checkpoint completed exactly 3,137 canonical 768x432 forwards
on all 3,179 accepted NBA training frames / 21 blocks. Zero imports, extra parity
forwards, fits, optimizer updates, new labels, selectors or protected evaluation.
Full means and uncapped pools were sealed before joining accepted references.
Capture 236.36s; charged supervised launch 288.75s; maximum 59C; no faults, settings
changes, retry or surviving owned processes. Debug Mode was freshly observed ON.

Both predeclared raw and conservative role/input-screened coverage gates PASS.
Raw chosen known-distant errors 305 -> screened 304; native-hidden 81; weak positive
with that producer wrong/missing 76 (67 wrong, 9 missing). Each combined required
category spans all 3 games and survives every intended outer training fold.
The usable exact-new union is 461 points on 394 existing frames, 18 blocks, 70 physical
consecutive runs: 452 new floor-centered crops and 9 existing crops with different
point readouts. One historical-frame role conflict is excluded; old roles and
unknown targets remain unchanged. Runs do not establish independent plays.
DEN contributes only 1 native-hidden frame; CHI supplies 56/76 weak recoveries.

Counterevidence must remain prominent. The pool has 1,091,879 candidates versus
18,813 current (~58x); only 0.0422% meet the combined required-case/novelty/role
screen. Alternate native choices are 2425 correct / 308 wrong / 81 hidden versus current
2807 / 3 / 2 before J; 382 current-native successes are lost, 180 current-positive pool
frames are lost and only 1 is added. It natively recovers none of the 4 current
wrong/missing cases. Of 76 producer-relative recovery frames, 75 already have a
correct current-cosine choice. The current-policy failure population remains
4 CHI frames, with no fresh-scene or cross-game current-policy coverage claim.
All 610 original weak positives and all 21 HOU external recovery cases, including
6 below-.01 cases, remain preserved regression evidence. No HOU fitting/evaluation
was added. No tracking gain or progress toward 95% is claimed by this data test.

Next is a bounded producer-transfer DESIGN: isolate added role-compatible
examples while retaining successful controls, original representation/objective,
downstream policies and per-source retention/hidden/recovery vetoes. Do not feed
the million-point pool wholesale, swap detectors, fit automatically or sweep
thresholds/checkpoints. New permitted footage remains the direct alternative for
current-detector failures on fresh scenes; representation/visibility diagnostics
require a specific new information hypothesis. Existing context/temporal/point
and origin-ablation evidence plus freshly checked primary research constrain
the recommendation. Ryan's standing due-diligence requirement continues.

All 23 focused checks and independent implementation/capture/analysis audits
passed. Saved means/extraction and all contributor identities are audited;
discarded raw forward channels cannot be numerically reaveraged postrun.
Float32/order reduction is supported by meaningful synthetic tests of the
unchanged reducer. An initial metadata-only source race was preserved and fixed
before successful CPU compatibility/freeze; no neural attempt was repeated.

The inherited 138-file worktree is preserved: 129 files unchanged, 9 maintained
documents receive exact reversible additions, and 7 new source/test/config/report/
ledger paths make 145. Original handoff/Session17 history, branch/HEAD and empty
index persist. No Git integration. Continue from the new result/ledger and the
documentation_update preservation receipt; do not restart completed studies.


## Coverage review completed; due diligence reaffirmed, 2026-10-29

Ryan directed the coverage/design check and reaffirmed critical due diligence
for every recommendation. See [the coverage decision review](../ball_tracking_candidate_training_coverage_review.md) and
configs/ball_tracking/reviews/candidate_training_coverage_review_v0_1.json.
This is a completed saved-metadata review, not another training/capture run.

All 3,179 accepted NBA training frames are already used. The 70 known native
distant-negative candidates are all unchosen alternatives; all three actual
wrong native choices remain boundary-unknown for fitting. Native-hidden support
is one adjacent CHI two-frame interval. Of 610 weak positives, 609 accompany
native success; one accompanies native missing and none native wrong. Actual
leave-CHI-out fitting lacks each of these decision-relevant cases despite real
weak-hidden training support. Existing broad objective balancing is preserved.
This is a conditional support gap, not proof that visual coverage causes errors.

Saved older locally NBA-untrained SAC proposals were checked against the same
accepted 300 frames. They add 23 unchosen negative coordinates on 19 used frames,
but zero selected known wrong/hidden points; 17 coordinates lie outside both
compared current/historical crop registries. Different coordinates are not new
scenes. A SAC-trained older checkpoint adds two adjacent selected wrong points
with same-source exposure. No unused accepted hard-case scene bank was found.
All 21 HOU external weak recoveries remain, including six below-.01 cases;
HOU is an exposed regression veto, not a fitting/sampling repair source.

Next proposed experiment is one alternate-producer coverage capture using the
existing expanded-NFHS checkpoint, on the 21 accepted NBA training blocks only:
3,179 frames, 3,137 canonical768x432 forwards, zero assumed imports, zero fits.
The old512x288 SAC caches remain diagnostic evidence and cannot be imported by
PNG identity. Local NBA nonexposure does not certify global pretraining history.
The separate protocol fixes producer-relative coverage checks before outcomes;
new proposals cannot manufacture cross-game current-cosine recovery failures on
these fixed frames. Passing permits only a later producer-transfer design.
The capture is proposed, unimplemented and unrun; no launch readiness is claimed.

For every recommendation, carry forward the maintained session history and
decision-relevant primary evidence; disclose what was freshly read versus reused.
Check relevant primary research when it can affect the decision. State what
actually changes, meaningful alternatives and counterevidence, assumptions and
limits, the question answered, and proportionate stop/continue criteria before
costly execution. Establish genuine novelty; do not repeat completed experiments
or rename an existing recipe. Challenge important recommendations independently
when useful. A negative experiment can be informative, but audit counts and
activity are not tracking progress. Do not turn this into an endless review or
duplicate-permission loop; existing authorization and routine autonomy persist.

No model load, inference, optimizer update, GPU query, image decoding, new label,
protected access, selector/threshold adoption or Git integration occurred.
The nine maintained files receive exact reversible additions; 126 other prior
files remain unchanged. Three new report/protocol/ledger files make 138 current
worktree paths. The documentation_update receipt preserves all135 prior contents
and the original handoff/Session17 chain. Branch/HEAD/index remain unchanged.
Existing NBA roles, accepted uncertainty, 95%/1%/zero-hidden, temporal/recovery
and human-review gates stand. Quality-top's90.43% ceiling remains a separate
selection problem; this review does not claim a tracking accuracy gain.



## CPU origin ablation completed and audited, 2026-10-29

Ryan authorized the recommended one-change CPU comparison. Four new fits remove
the two explicit origin indicators while reusing all saved detector scores,
feature registries, splits, targets, weights and fixed candidate choices.
The first attempt completed in 19.735 seconds; no neural call or GPU query.
See [the origin-ablation results](../ball_tracking_candidate_acceptance_origin_ablation_results.md) and the ledger
configs/ball_tracking/reviews/candidate_acceptance_origin_ablation_result_v0_1.json.

Removing these indicators does not improve this recipe. At zero, held NBA native
J -> A is 2,806 -> 2,798 correct with the same three wrong/two hidden emissions;
quality-top is 2,541 -> 2,539 correct, 34 -> 48 wrong and eight -> nine hidden.
There is no strict NBA fixed-zero gain; ten exact J-kept correct policy points
on eight distinct frames are lost. The full unselected curves also mostly favor
J for NBA quality-top.
HOU is mixed: native 841/18/18 -> 840/17/16 and quality-top 855/4/14 -> 858/5/16
(correct/wrong/hidden). e01 quality-top recovery improves six -> nine of ten,
and exact stress six -> eight of ten, still below original Q's ten. Three frozen
HOU policy identities and six stress identities are lost; overlapping views
are not additive. Both predeclared criteria fail. No arm, cutoff or selector
is adopted; original J also remains an unadopted experimental comparison.

25 focused tests pass. Independent audits pass 3,072,793 output checks and
2,773,690 saved-model checks. All 31,430 slots, 11 missing scores, 4,289 context
frames, 8,578 fixed-policy rows, 6,720 choices/contrasts and 60 historical rows
remain; A adds 3,270 zero tables and 143 complete unselected curves. Retained
scalers and fitting arrays reconcile with J. No old experiment was rerun.

This rejects removing the two indicators as the repair for this recipe, not all
origin-aware methods or a causal hypothesis. Correlated cues and sparse native
negative/hidden support remain. Quality-top's 2,542/2,811 ceiling is unchanged;
this experiment does not move the 95% milestone. Next is a separate bounded
design addressing native-negative support/objective balance from NBA fitting
evidence, with retained J as a comparison; no weighting, schema, routing or
training follow-up has been run. Exposed HOU cannot choose a repair. Existing
roles, accepted labels, numerical/temporal/human gates and protected closure stand.

All 125 prior worktree contents are preserved through 116 unchanged files and
nine reversible insertions; ten new files make 135 current worktree paths.
The preparation/documentation_update receipt continues the original handoff and
Session17 chain. Branch/HEAD/index remain unchanged. The authorized comparison
is complete. No new labels, settings change, protected access or Git integration.



## Candidate acceptance experiment completed and audited, 2026-10-29

Ryan authorized moving forward with the reviewed acceptance experiment.
Implementation, the fixed new workload and independent audits are complete.
See [the acceptance experiment results](../ball_tracking_candidate_acceptance_gate_results.md) and the ledger
configs/ball_tracking/reviews/candidate_acceptance_gate_result_v0_1.json.

The joint acceptance score J adds useful separation on held NBA quality-top
points: correct kept 2,275 -> 2,541, wrong eligible 99 -> 34, and hidden-frame
emissions 28 -> 8 at the fixed zero reference. Each of the three NBA games
improves or matches both raw Q and score-only S on all three measures for this
policy. Complete unselected curves show added separation; positive-slope S
preserves Q's per-source curve ordering. No evaluation cutoff was selected.

The full predeclared component criterion nevertheless FAILS. Held NBA native
retention rises 2,309 -> 2,806, but CHI adds three wrong and two hidden emissions.
HOU native J keeps 841 correct yet accepts 18 wrong and emits in 18 hidden frames;
HOU quality-top keeps 855 correct with four wrong but 14 hidden frames, versus
Q's 825 correct, six wrong and three hidden. Five protected quality-top choices
and seven exact protected stress probes are newly rejected; four of ten e01
recoveries are lost in each respective view. These overlapping views are not
additive failures. No model, threshold or selector is adopted.

All three single-game quality fits ran from the pinned fresh initialization:
3,300 updates, 37,626 cross-game scores, 4,481 total neural forwards. Supervised
execution took 448.906 seconds, peaked at 63 C, and finished with no qualifying
fault or remaining owned job. Eight CPU gate fits and analysis took 28.297
seconds. Original caches, four-fit quality models and completed studies were
reused; no old experiment was rerun. An initial readiness classifier mistook
ordinary WDDM desktop contexts for training workers; its unused freeze and
rejected evidence were preserved, then a reviewed version distinguished exact
desktop identities from conflicting/unknown runtimes before the only launch.
Debug Mode remained visibly ON; no system settings changed.

54 focused tests, 13 synthetic supervision checks and 12 readiness-correction
tests pass. Independent audits passed 152,617 neural transport/supervision,
16,520 saved tensor/optimizer and 3,328,460 acceptance-output checks. All 31,430
evaluation slots per arm, 11 missing scores, 4,289 context frames, 6,720 old
choices and contrasts, unknown roles and 60 historical rows remain represented.
There are 13,080 zero-reference tables and 578 complete unselected curves.

Next is a controlled follow-up design addressing incorrect/hidden native points
and protected recovery losses while preserving the demonstrated separation.
HOU remains exposed regression evidence and cannot choose a repair. Base-training
size changes across nesting and sparse native-negative support remain limits.
Quality-top's 2,542/2,811 ranking ceiling still prevents a rejection-only route
to 95% correctness; native and quality-top must remain separate. The existing
95%-correct / 1%-wrong / zero-hidden, temporal and human trajectory gates stand.

The current execution request is fulfilled. Outputs are under
data/outputs/ball_tracking/candidate_acceptance_gate_v0_1/attempt_001/.
The implementation_preparation/documentation_update receipt preserves all 113
prior worktree contents through exact unchanged bytes or reversible insertions,
retaining the Session17 and original handoff chain. Branch/HEAD/index remain
unchanged. No new labels, protected access, Git integration or future experiment
is implied. Existing NBA/cosine-nine roles and accepted annotations stand.



## Candidate acceptance experiment designed; unrun, 2026-10-29

Ryan requested a next experiment to preserve correct detections while rejecting
wrong ones, building on the CPU study and earlier work, with online research.
The independently reviewed design is [the candidate acceptance protocol](../ball_tracking_candidate_acceptance_gate_protocol.md), with specification
configs/ball_tracking/proposals/candidate_acceptance_gate_v0_1.json.

Keep original native and quality-top policies fixed: retain their point or
abstain, without fallback, reranking or trajectory changes. Compare reused raw
quality, a score-only adjustment, one 16-feature joint acceptance head, and a
fixed spatial-competition control. Only observable quality/response/pool inputs
are allowed; the target is useful coordinates, not semantic crop presence.

Honest source nesting needs three new single-game quality fits, each scoring
the other two games: 3,300 updates, 37,626 cross-game scores, 4,481 total neural
forwards. Existing models/results/caches are reused; eight small CPU gate fits
follow. None of that work ran. Metadata preparation verified 74 input bindings,
actual counts and feature availability; independent design review passes.
Targeted primary online research and material earlier reports were reconciled
with the completed history review, without claiming an exhaustive reread.

New gate evaluation has 31,430 slots per head (31,419 observed / 11 missing)
and 4,289 context frames. Old NBA fitted controls stay separate. Fixed zero and
complete unselected curves distinguish added information from a moved cutoff.
HOU native/recovery/stress successes and hidden emissions have explicit
regression checks; HOU chooses no weights, feature, cutoff or repair.

Quality-top's held ceiling is 2,542/2,811 (90.43%): rejection alone cannot finish
the 95% tracker gate. Native preservation is a separate primary question.
The existing 95%-correct / 1%-wrong / zero-hidden, temporal and human gates
remain. Mixed outcomes remain mixed; no model, threshold or selector is adopted.

Next: implement this exact bounded design and focused checks, then independent
review and concrete launch readiness before new neural execution. The current
design request is fulfilled; implementation and execution remain unrun.
Evidence is under data/outputs/ball_tracking/candidate_acceptance_gate_v0_1/preparation/.
All 111 prior worktree contents and the Session17 chain remain preserved through
exact additive records. Branch/HEAD/index are unchanged. No labels, protected
access, GPU query, settings change, old experiment rerun or Git integration.
Debug Mode ON remains the standing instruction.


## Saved-score CPU failure study completed and audited, 2026-10-29

Ryan explicitly authorized implementation and execution using saved results.
Accepted output is `data/outputs/ball_tracking/saved_score_failure_study_v0_1/attempt_003/`:
47.722 seconds of CPU consumer work; 25 focused tests and 1,615,156 independent
output checks pass. All 7,468 context frames, 50,243 score slots (11 missing),
18,813 NBA candidate pairs, 3,179 frame pairs, 6,720 contrasts and 60 historical
rows remain. The four-fit pilot and original consumers were reused.

New diagnosis separates rejection from ordering: 267 held-game frames still
rank a match first but contain no positive matching score; 264 paired frames
lose correct first-place ordering versus one gain. Matching native/weak
candidate median held-minus-fitted logits are -4.529/-6.751; full-pool margin
change is -8.310 on 2,694 defined pairs, with 485 named nulls. Source/visibility
patterns differ by game. Actual fitting support is narrow for native negatives
and hidden native candidates, but some zero-support metadata cells succeed and
some supported cells fail. No causal explanation, cutoff or model is selected.

See [the complete results](../ball_tracking_saved_score_failure_study_results.md) and the project ledger
`configs/ball_tracking/reviews/saved_score_failure_study_result_v0_1.json`.
Full source/support tables, successful/adverse controls, e01/e05 cases, weak/native,
unknown/missing/hidden populations and historical roles remain in the accepted
attempt. The next recommendation is a bounded design addressing presence/rejection
and cross-source comparability while retaining ordering and coverage constraints;
it is not a new training or selector authorization.

Attempts 001/002 are preserved but not accepted: a doubled summary counter,
numeric-radius category splitting and unavailable threshold metadata were fixed
with regression checks before attempt003. Original scores/labels/design files
never changed. Use the final freeze, audits and additive documentation receipt
under `implementation_preparation/documentation_update/`, rather than treating
the old pre-design handoff verifier as the current file-hash baseline.

All 102 preimplementation worktree contents and the Session17 preservation chain
remain recoverable. Branch/HEAD and empty index stay unchanged. Reuse prior
history/research reconciliation with its stated limits; no fresh full reread is
claimed. NBA/cosine-nine roles, accepted labels, pending human trajectory review,
Debug ON and protected closure stand. No model call, GPU query, new label,
trajectory, protected access, completed-old-study rerun or Git integration.


## Session 19 complete handoff, 2026-10-29

Suggested title: **Ball Tracking 19 — Candidate-Quality Training & GPU Recovery**.
Local thread: `01a1831e-73b0-7532-8b5d-f60486918039`. The app title was retrieved
as `Specify CPU candidate-change comparison`; the title above is generated for
Ryan, not a claim that the app was renamed. Session 18 precedes this continuation.

Read the [complete Session 19 handoff](../../data/outputs/t/handoff_2026-10-29_8c040fca385d_session19/COMPLETE_HANDOFF.txt),
its appended full results report and required reading. The sibling opening prompt,
read-only verifier, exact 100-file snapshots and verification manifest preserve
the current branch/HEAD, empty index, all prior contents and Session 17 chain.
Only these additive handoff pointers changed; no scientific source, run or setting
changed. Current file hashes supersede older context hashes through the recorded
insertion layer; earlier experimental evidence remains frozen.

The four-fit pilot, all scoring, audits, paired/adverse comparisons and posthoc
cross-tab are complete. Reuse them. The next recommendation is to specify the
bounded CPU saved-score failure study; its precise protocol remains unfrozen and
unrun. Preserve useful ranking alongside rejection, weak, hidden, historical and
held-game failures, with full agreement/uncertain/missing coverage. Prior one-run
GPU permission is fulfilled, Debug Mode ON remains the requested configuration,
and no new training, selector, labels, protected access or Git integration follows.
Reuse completed history/research and state new reading limits; no resume reruns.

## Four-fit quality pilot completed; useful ranking, unresolved rejection, 2026-10-29

Ryan authorized the prepared continuation once. All four fixed fits and all
declared scoring completed with Debug Mode observed ON before launch. Inclusive
runtime was 1,125.984 seconds (18m46s); 547 GPU samples peaked at 63C/151.21W/3537MiB.
No qualifying fault or retry occurred; both owned jobs exited cleanly and the
postrun Windows/process query confirms no owned training/watcher remains. This
is encouraging after the native-cable change, not proof of a component cause or
permanent stability. No setting changed.

The unchanged epoch-six diagnostic endpoint was imported exactly for the first
fit, with zero retraining. New work: 7,626 updates, 1,572 score forwards and 3 parity
forwards; 50,232 scored presentations. Independent saved audits pass 246,129/224/
806,799 checks, including exact first-fit CPU tensor equality, complete counters,
score transport and cleanup. All 3,329 package frames/19,632 candidates, 960 HOU
frames, 11,798 query records, 6,720 contrasts and 60 historical rows remain.

HOU ranks a match strictly first on 862/882 eligible frames versus point 527 and
CLS 259. Against peak on 865 complete-feature pairs: 36 gains and 11 regressions;
17 incomplete old rankings remain separate. All ten e01 recovery rankings and
recovery-vs-missing comparisons succeed, but four of six below-.01 e05 gains
score negative. At fixed zero, 798/842 HOU native points survive and 3/34 hidden
frames retain another candidate. Held-game scores keep 2,309/2,807 native-correct
points (498 lost), 402/610 weak-match frames and retain hidden candidates in
28/128 frames. Fitted NBA keeps all native/weak positives.
Correct ordering, zero rejection and missing pool coverage remain distinct.
Historical accepted checks still miss two balls. No threshold or model is adopted.

See [the complete results](../ball_tracking_native_cable_training_results_2026-10-29.md), linked primary outputs and independent
interpretation. Reuse the completed full-history/research reconciliation plus
actual new four-fit evidence; no fresh every-transcript/paper claim. All agreement,
weak/native, hidden, uncertain, missing, adverse and historical cases are retained.
The next recommendation is a bounded CPU saved-score failure study before any
model/selector/training change; its precise follow-up protocol is not frozen or
run. The completed posthoc reporting cross-tab is explicitly descriptive.

All 99 prior worktree contents and the Session 17 chain are preserved beneath
verified additive records; one result report makes 100 paths. Branch/HEAD and
empty index remain unchanged. Earlier failures, checkpoints and physical exposure
11,710 starts/11,709 returns/11,708 updates remain. Historical 1,574 seconds and
the old 2,026-second balance remain but are no longer an active cap; new
1,125.984 seconds are recorded
separately. NBA/cosine-nine roles, accepted labels, quality/human gates and protected
closure stand. No further GPU work, new selector/trajectory, labeling campaign,
outside specialist, ACB prototype, protected access or Git integration occurred.

## Epoch-six checkpoint CPU-validated; continuation prepared, 2026-10-29

Ryan requests CPU validation and preparation of the next supervised continuation,
keeping Debug Mode ON, and explicitly removes the old remaining-time constraint.
The diagnostic epoch-six checkpoint passes 12,181 CPU checks, including actual
pinned model/AdamW restoration at update 2,244 and frozen-prefix identity. CUDA
stayed uninitialized; no neural forward, optimizer step or GPU query occurred.

Prepare completion of the unchanged four-fit pilot: reuse that audited first-fit
endpoint with an explicit diagnostic-origin record, score CHI, then finish the
remaining three six-epoch fits and all fixed scoring. New work is 7,626 updates,
1,572 score forwards and three parity forwards. No first-fit retraining, extra
epochs, outcome-based recipe changes, selected threshold or model adoption.
Full agreement/disagreement, weak/native, hidden, uncertain, missing, e01 and
historical populations remain; HOU stays out of fitting and DET is limited to
the original fixed historical queries.

See [the prepared continuation](../ball_tracking_native_cable_training_continuation_2026-10-29.md) and its linked primary review/audit
records. Reuse the completed full-history/research review plus targeted original
reports, code, primary research and actual new CPU checkpoint evidence; no fresh
all-transcript claim. Source/tests, independent review and supervision checks
pass. Metadata preflight rejects missing new execution approval before Torch.
Nothing has launched; fresh readiness and specific execution direction remain.

Historical 1,574 seconds charged and the old 2,026-second balance are preserved;
that balance is no longer a cap. The fixed workload ends normally when complete,
with a separate 90-minute operational watchdog and 30-second cleanup reserve.
Stop on any renewed fault, with no automatic retry. All 96 prior contents and
the Session 17 chain remain preserved through additive records; three new files
make 99 worktree paths. Original checkpoints/failures, NBA/cosine-nine roles,
accepted labels, all quality/human gates and protected closure remain. No Git
integration or new settings change occurred.

## Native-cable diagnostic completed with Debug Mode ON, 2026-10-29

Ryan approved the revised diagnostic. Fresh readiness passed; Debug Mode was
already observed ON, Lively was closed, and driver 617.42 / RAM 5200 / 250 W
remained unchanged. The fixed epoch-two replay completed all 1,496 updates and
shut down cleanly in 260.781 seconds including startup/cleanup. Peak sampled
62 C; no new matching Windows fault, zero remaining owned GPU/event workers.
The ten-minute value was a cap, not ten full minutes under load.

Independent CPU audit passes 34,315 checks: all 1,015 overlapping updates exactly
match earlier loss/gradient pairs, 481 extend beyond the old recorded range,
and four separate diagnostic checkpoints pass hash/ZIP checks. Their new tensor
semantics are unaudited; no scoring, four-fit comparison or adoption completed.
Original scientific epoch four and all prior unsaved work/failures remain.

See [the completed result](../ball_tracking_native_cable_diagnostic_results_2026-10-29.md). This short pass after the user-reported
native cable change is encouraging, not proof of a component cause or lasting
stability. Reuse completed history/research plus actual readiness, journals,
telemetry, events and independent reviews; no fresh all-transcript claim.
Conservative debit 261 seconds leaves 2,026 seconds (33m46s), with no automatic
continuation. All 95 prior contents and the Session 17 chain remain preserved
through additive records; one new report makes 96 worktree paths. NBA, cosine
nine, full case coverage, labels, uncertainty and protected closure are unchanged.
No new setting, scientific direction or Git integration follows this result.

## Cable replay revised to Debug Mode ON; still unrun, 2026-10-29

Ryan clarified that OFF was only the default and permits configuration choice.
Select Debug Mode ON to match the directly observed failing epoch-two replay
before the native cable change. Keep driver 617.42, RAM 5200, power limit 250 W
and the training recipe unchanged. This is a closer comparison, not a cure or
proof of cable causality. The original OFF preparation remains preserved/unrun.

The separate v0_2 preparation retains the 600-second cap and fault/stop guards.
CPU checks pass; actual ON observation, fresh readiness and explicit workload
execution direction remain required. Configuration selection is not a setting
change or launch: neither occurred. Earlier no-launch instruction still applies.

See [the revised protocol and commands](../ball_tracking_native_cable_reference_diagnostic_2026-10-29.md). Reused completed history and
targeted actual failure evidence; freshly read NVIDIA Debug Mode guidance.
No fresh all-transcript claim, GPU work, additional exposure or Git integration.
Preserve all 92 prior contents, Session 17 chain, scientific checkpoints and
2,287 remaining seconds; no automatic retry or further training follows.


## Native cable diagnostic prepared; do not launch, 2026-10-29

Ryan reports replacing the breakout cable plus ASUS adapter with the original
Corsair RM850e 2025 native 16-pin cable. Keep reported Debug Mode OFF. Photos
were reviewed in the browser chat; no specific cable fault is proven. A separate
ten-minute epoch-two replay is prepared, not authorized or run. The previous
clock diagnostic used Debug Mode ON, so configuration is not identical.

The last directed training retry failed after 83 returned forwards / 82 completed
updates, all replayed; no new checkpoint or scores. This time cleanup certified
zero owned processes. Debit 150 seconds; 2,287 seconds remain. Scientific epoch
four and its original 267 unsaved logical updates remain preserved.

Read-only checks find driver 617.42, both RAM modules at 5200, Lively running and
True Color absent. Apps and settings were left untouched. New owned supervision
has a 600-second hard deadline and a 30-second fault-cleanup guard; CPU checks
pass and missing execution approval is rejected before Torch import. Fresh
isolation/readiness and explicit execution direction are still required.

See [the protocol, commands and evidence](../ball_tracking_native_cable_diagnostic_2026-10-29.md). Reuse completed history and
research with targeted primary reads; no fresh all-transcript claim. All 89
prior contents and Session 17 chain remain preserved through additive records.
No automatic retry, further training, scientific-role change or Git integration.


## Powered-off connection check recommended, 2026-10-28

After the completed Debug Mode crash comparison, recommend photographs of the
existing GPU plug, cable/adapter route and accessible PSU label/ports, with the
PC off and AC unplugged. Keep internal connections untouched. This closes an
unresolved physical-evidence gap after inaccurate original cabling advice;
one native cable can be correct, and normal photos cannot prove electrical
health. See [the recommendation](../ball_tracking_nonphysical_crash_diagnosis_2026-10-28.md). The check is proposed, not performed.

Reused full history/research with original build messages, current primary crash
evidence and manufacturer guidance. No new setting, GPU work, retry or scientific
direction. All 87 prior contents, Session 17 chain and 2,437 seconds remain.

## Debug Mode crash dump comparison complete, 2026-10-28

The copied dump is verified and locally analyzed. It repeats the earlier
0x116/C000009A/4 failed-reset stack and 617.42 module offset. Raw same-build
context plus Windows report fields corroborate timeout-path 9 versus earlier 3,
consistent with an engine timeout escalated to adapter reset versus an earlier
display-flip timeout. Private type symbols are missing; no component cause is
identified. The retained power-cable string is in an identical firmware ROM,
not an active alert. See [the dump comparison](../ball_tracking_nonphysical_crash_diagnosis_2026-10-28.md).

The copy request is fulfilled; no further copy is currently needed. No GPU
query/workload, settings change, retry or new direction occurred. Reused completed
history/research plus relevant original logs and primary Microsoft documentation;
no fresh all-transcript claim. All 87 prior contents and Session 17 preservation,
scientific checkpoints, failures, roles/gates and 2,437 remaining pilot seconds
stand. Physical inspection remains deferred; no automatic GPU continuation.

## Debug Mode test failed; no retry, 2026-10-28

Ryan approved the single-setting diagnostic. Debug Mode was observed enabled,
but NVIDIA telemetry failed and Windows rebooted with another0x116/nvlddmkm
crash. The setting did not prevent recurrence; a faulty component is not yet
identified. Peak sampled63C/2525MiB; worker cleanup failed. Readable final receipts
and the live event watcher preserve this failure. See [the completed diagnostic](../ball_tracking_nonphysical_crash_diagnosis_2026-10-28.md).

Independent CPU recount:441 returned updates, all exactly matching attempt003's
recorded loss/gradient pairs; one unreturned start. Separate epoch3 checkpoint
hash/ZIP passes;67 later diagnostic updates unsaved. Original scientific epoch4,
267 original unsaved updates and all earlier failures remain. Conservative debit
through reboot leaves2437seconds (40m37s), with no reset or retry authorization.
New dump ordinary access is denied; exact local administrator-copy helper is
prepared/unrun. No further GPU/settings action, scoring, adoption, protected
access or Git integration. Post-reboot Debug Mode state is uninspected.

Reuse completed history/research and targeted primary/current-run evidence; no
fresh all-transcript claim. Original85 contents and Session17 chain are preserved
beneath additive documentation; two new worker/test files make87worktree paths.
All scientific roles, full case coverage and review gates remain unchanged.

## Reference-clock diagnostic recommended, not run, 2026-10-28

Ryan requests one change at a time. The actual NVIDIA App shows Debug Mode off;
recommend enabling it as the single setting change for a bounded replay of the
same first fit, from the already audited epoch-two state through epoch six, at
most10 minutes including startup/cleanup. See [the proposed contract](../ball_tracking_nonphysical_crash_diagnosis_2026-10-28.md).
The worker/launch inventory still needs preparation; no setting or GPU workload
changed. Reuse completed history and targeted primary evidence; current off state
does not establish the historical toggle state. A short pass is not a cure.
Preserve all85 prior contents, Session17 chain, latest checkpoint,267 unsaved
updates and2661 seconds remaining. No automatic retry, new scientific recipe,
protected access or Git integration; physical inspection remains deferred.

## Watchdog dump analyzed; cause still unresolved, 2026-10-28

The verified live dump captures graphics-scheduler hang detection at16:21:38.251,
19.296 seconds before the final116, with the same recovery-context address. It
confirms the same incident and earlier failure stage, not a faulty component.
Missing context/process memory and an undecoded retained graphics block limit
causal diagnosis. An embedded firmware power-cable message is not an active alert.
See [the completed follow-up](../ball_tracking_nonphysical_crash_diagnosis_2026-10-28.md). The watchdog-copy request is fulfilled.

Three local debugger passes and independent reviews are complete; no settings
change, GPU query/workload or retry occurred. No further copy is currently needed.
Reuse completed history/research and targeted primary evidence, without a new
all-transcript claim. All 85 prior worktree contents and Session17 preservation,
epoch-four checkpoint,267 unsaved updates and2,661 remaining seconds stand.
Existing diagnostic alternatives remain proposed/unrun; physical inspection is
deferred. No new scientific direction, protected access or Git integration.

## Existing timeout report analyzed, 2026-10-28

The copied Kernel117 report is verified and independently reviewed. It records
an NVIDIA timeout at 16:21:41.478 Phoenix, 16.069 seconds before the final 0x116
crash, with matching boot/bucket evidence. Its repeated AAAA parameters and generic
"Hardware error" label do not identify a faulty component or underlying cause.
The prior report-copy request is fulfilled. See [analysis receipt](../../data/outputs/ball_tracking/candidate_quality_pilot_v0_1/post_driver_recovery_preparation_v0_1/attempt003_interruption_v0_1/nonphysical_diagnosis_v0_1/kernel117_analysis_v0_1/analysis_receipt.json).

The report names WATCHDOG-20261028-1621.dmp; ordinary access is denied, so its
survival/content is not yet verified. An exact-file administrator copy helper is
prepared and unrun. No settings changes or GPU work occurred. Reuse the completed
history/research review and prior dump/event evidence; no fresh full-history claim.
All 85 prior worktree contents and Session 17 preservation remain intact. Physical
inspection is deferred; 2,661 pilot seconds, the epoch-four checkpoint and 267
unsaved updates remain unchanged. No automatic retry or scientific-role change.

## Further nonphysical diagnosis requested and completed, 2026-10-28

Ryan prefers further diagnosis before opening the case; physical inspection is
deferred. The [targeted review](../ball_tracking_nonphysical_crash_diagnosis_2026-10-28.md) identifies an unread protected Kernel117
report near the last crash, MSI/Ryzen helpers loaded in the actual dump, later
exact-board PCIe/graphics firmware fixes and untested NVIDIA reference-clock
mode. Chipset support/version differences are real but no CPU-specific or
NVIDIA-crash cause is established. Runtime/code review finds no obvious mismatch
or defect; that is not a software-health certificate.

Next is copying the existing small117 Report.wer with the prepared administrator
helper, then reading its actual metadata. Windows ordinary access is denied;
the copy is prepared and unrun. No new GPU workload, settings change, installation,
stress test or physical action occurred. One read-only NVIDIA query and one
saved-dump module inspection are recorded. Any later reference-clock or isolation
experiment still needs a concrete protocol and explicit execution direction.

All84 prior worktree contents and Session17 preservation remain intact. Reuse
completed history with targeted primary evidence; no fresh all-transcript claim.
Epoch-four checkpoint,267 unsaved updates, failures and2,661 seconds remaining
stand. No automatic retry, scientific-role change, protected access or Git
integration. Earlier cable-inspection recommendation remains historical.

## New dump analyzed after driver change, 2026-10-28

Ryan's new dump copy is verified and analyzed locally. It repeats 0x116,
C000009A and the Windows failed graphics-reset stack at 16:21:57.547 Phoenix,
now with verified 617.42. The changed NVIDIA offset reflects a different binary;
no identical private-function or specific faulty-component claim is justified.
Configured 5200 and driver replacement did not prevent recurrence. No retry ran.

The [comparison and diagnostic proposal](../ball_tracking_crash_dump_post_driver_2026-10-28.md) reuse completed history plus
actual earlier/new debugger evidence and primary vendor guidance. Next proposed
step is a powered-off photographic check of the GPU power connector/cable route
and accessible PSU label/ports. Earlier build advice was inaccurate; the actual
route is unknown, and one cable alone does not prove incorrect wiring. No
physical inspection, settings change, stress test or new GPU work occurred.

The dump-copy request is fulfilled. All 83 prior worktree contents remain intact
through additive records. Epoch-four checkpoint, 267 unsaved updates, previous
failures and 2,661 seconds (44m21s) remaining stand; no budget refund or automatic
retry. NBA, cosine nine, labels, full case coverage, gates and protected closure
are unchanged. No Git integration or new scientific direction.

## Post-driver continuation crashed; no retry, 2026-10-28

Ryan explicitly approved attempt003 and its remaining 49m6s. Readiness passed,
but NVIDIA telemetry failed and Windows rebooted with confirmed 0x116 naming
nvlddmkm.sys. Verified 617.42 and 5200 MT/s did not prevent recurrence; root cause
remains unresolved. STOP was requested, cleanup failed, and the final receipt
is 494 NUL bytes. Post-reboot snapshot finds no Python worker. No retry ran.

The independent CPU recount passes 3,474 recorded checks: 1,015 new updates,
exact replay of 213 old updates, epoch-four checkpoint retaining 1,496 logical
updates, and 267 later unsaved updates. Hash/ZIP CRC pass; new tensor semantics
are unaudited. No fit/scoring comparison completed. Peak sampled 62 C.
Conservative debit through reboot leaves 2,661 seconds (44m21s), not a new hour.

See [the interruption report](../ball_tracking_candidate_quality_post_driver_interruption.md). Windows denies ordinary access to the
new minidump; an administrator copy is the next local diagnostic step. The
guarded copy script is prepared, not run. All 82 prior worktree contents and
original Session17 preservation remain intact through additive records.
Reuse completed history/research with targeted crash/producer evidence; no fresh
all-transcript claim, new recipe, labels, protected access, adoption or Git
integration. Remaining time does not authorize another GPU attempt.

## Post-driver recovery validated and prepared, 2026-10-28

Ryan authorized CPU checkpoint validation and preparation only. The actual
epoch-two checkpoint passes 5,056 independent CPU checks: 42 finite trainable
tensors, exact parameter/AdamW restore at update 748, and CPU RNG checks. CUDA
remained uninitialized. Nine focused recovery tests and independent code review
pass. Actual frozen metadata preflight verifies original 45, prior 10 and new
22 bindings, and rejects the missing attempt003 execution approval without
importing Torch. No GPU worker or neural call started.

The [prepared continuation](../ball_tracking_candidate_quality_post_driver_recovery.md) resumes epoch three on driver 617.42 with
9,122 updates left, unchanged science and all original case coverage. The
2,946-second limit includes startup and a 30-second cleanup reserve. Preserve
both failures, 213 newly unsaved updates and all 300 replay-overhead updates;
cross-driver bit identity is not promised. All 79 prior worktree contents and
Session 17 preservation remain intact through additive records.

Next launch needs explicit direction for this prepared attempt and fresh
telemetry, event/memory and graphics-isolation checks; Lively was running at the
preparation snapshot and was not closed. Short idle readiness is not a cure.
Reuse completed history/research with targeted producer/crash/recovery evidence.
No automatic retry, new recipe, labels, protected access, adoption or Git integration.

## Driver 617.42 verified after installation, 2026-10-28

Ryan explicitly approved the Studio 617.42 clean installation, followed the
walkthrough and reported rebooting. Windows now reports signed driver
32.0.16.1742, and NVIDIA telemetry confirms 617.42 at a sampled 42 C. Boot was
15:54:12.5 Phoenix. Both 32 GB modules remain configured at 5200 MT/s. The
clean-install checkbox was not independently observed; EXPO off remains Ryan's
reported BIOS setting.

The successful since-boot queries inspected 147 System and 33 Application
events, with no matching graphics/WHEA/resource-exhaustion/WER reports. No
Python worker was present. This verifies replacement and short idle operation,
not a cure or load stability. No training, stress test or automatic retry ran.

[Observed installation snapshot](../../data/outputs/ball_tracking/candidate_quality_pilot_v0_1/studio_61742_install_v0_1/post_install_snapshot.json). All 79 prior worktree contents and
original 45/recovery 10 execution bindings remain preserved. The interrupted
epoch-two checkpoint retains 748 logical updates; its tensor semantics still
need CPU validation before any future recovery preparation. The 213 unsaved
updates, prior failures and 2,946-second remaining budget stand. Reuse completed
history/research and targeted incident evidence; no method, labels, protected
access, adoption or Git integration changes. Further GPU continuation requires
an explicit direction after concrete recovery/readiness preparation.

## Recovery interrupted again at 5200 MT/s, 2026-10-28

The directed attempt002 ran and failed again: CUDA unknown error and lost NVIDIA
telemetry, with a same-time Windows141 NVIDIA graphics timeout. Ryan restarted;
both RAM modules still report5200, EXPO off remains user-reported. No new0x116
is established for this incident. The memory change alone did not prevent it;
root cause remains unresolved. No further GPU retry follows.

The independent CPU recount preserves587 new updates, exact replay of87 old
updates, an epoch-two checkpoint retaining748 logical updates and213 later
unsaved updates. Hash/ZIP CRC pass; new checkpoint tensor semantics are not yet
audited. Supervisor cleanup certifies zero owned workers; no fit/scoring result
is complete. Peak sampled62 C. Budget remaining2946 seconds (49m6s), no reset.

See [the recovery interruption and evidence limits](../ball_tracking_candidate_quality_pilot_recovery_interruption.md). Original78 worktree
contents, attempts, approvals and scientific roles/gates remain preserved.
Reuse completed history/research with targeted current evidence; latest driver
review precedes any proposed installation. No automatic retry, adoption,
protected access, settings change or Git integration.

## Directed pilot recovery prepared, 2026-10-28

Ryan directed recovery after the verified 5200 MT/s memory change and reported EXPO disablement. The additive worker restores the first fit at epoch two from its 374-update checkpoint, with unchanged scientific recipe. Six actual-checkpoint CPU recovery tests and six original pilot checks pass; independent implementation review and original45/recovery10 metadata bindings pass. No CUDA/model call occurred during preparation.

The remaining supervised budget is 3,126 seconds from policy creation, with 30 seconds reserved for shutdown. New work if complete is 9,496 updates; logical total remains 9,870, while the physical lower bound becomes 9,957 because 87 unsaved recorded updates must be recomputed. No fresh hour or further automatic retry. Attempt001 and all original75 worktree contents remain preserved; attempt002 and monitoring/attempt002 are the continuation locations. Read their current started/completed/failed receipts before asserting execution status.

See [the recovery specification](../ball_tracking_candidate_quality_pilot_recovery.md) and ignored recovery_preparation_v0_1 evidence. Existing pilot approval and this explicit continuation apply; no new method, selector, labels, protected access, adoption or Git integration. The memory change is a diagnostic intervention, not a proven cure. Completed history/research review is reused with targeted recovery/crash evidence reads.


## Memory change verified after reboot, 2026-10-28

Ryan reports setting DRAM speed to 5200 and EXPO Profile 1 to Disabled. Windows independently reports both 32 GB modules configured at 5200 MT/s, with all 64 GB installed. EXPO state is user-reported; exact BIOS timing/voltage controls were not remotely inspected. The separate SMBIOS Speed=5600 field does not contradict ConfiguredClockSpeed=5200.

Boot was 15:09:56.5 Phoenix. The successful read-only query inspected 147 System events since boot and found no matching graphics/WHEA/resource-exhaustion provider events. NVIDIA 616.56 responds at sampled 40-41 C. These are a successful boot and short idle observations, not proof of stability or a confirmed cure. Lively has restarted; no Python worker was found. No GPU model call, training retry, stress test or further system change occurred.

[Verification snapshot](../../data/outputs/ball_tracking/candidate_quality_pilot_v0_1/interruption_v0_1/memory_change_v0_1/readiness_snapshot.json). All 75 prior worktree files and 45 frozen execution bindings pass; additive records preserve earlier contents. The approved pilot checkpoint and 3,126-second remaining budget stand. Next is CPU preparation of exact checkpoint recovery and fresh supervisor/isolation readiness before any explicitly directed GPU continuation; no automatic launch. Reuse the completed history/research review and preserve all scientific roles, gates, uncertainty and prior failures.


## Crash dump analyzed; controlled memory check proposed, 2026-10-28

Ryan supplied the local dump copy; analysis is complete. It repeats the October 26 NVIDIA 0x116 reset-failure signature, with crash time 14:05:31.131 Phoenix. The underlying cause remains unresolved. Earlier crashes predate this pilot and current driver; sampled GPU peak was 61 C with 2,688 MiB used. Ryan confirms the previously proposed lower-memory-speed test was never tried. Current 2x32 GB RAM remains configured at 6000; AMD rates this CPU at 5200 for two DIMMs. Next: inspect and preserve actual BIOS settings before one proposed conservative memory-profile/speed test. No BIOS/driver/settings change, stress test or GPU retry occurred. A supported clean-driver installation remains an alternative, not a proven cure.

See [the completed dump analysis and evidence limits](../ball_tracking_crash_dump_analysis_2026-10-28.md). The older dump-access request below is fulfilled. Same pilot approval/checkpoint/recipe and 3,126 seconds remaining are preserved; no budget reset, automatic retry, new scientific direction, protected access or Git integration. All 74 prior worktree files are preserved through additive documentation.


## Approved quality pilot interrupted, 2026-10-28

Ryan explicitly approved the frozen four-run pilot and one-hour supervised limit. It launched, then NVIDIA telemetry failed and Windows recorded a 0x116 graphics bugcheck naming nvlddmkm.sys. There are 461 durably recorded updates; the valid epoch-one recovery checkpoint retains 374. The 87 later updates are unsaved. No development scoring or completed scientific comparison exists. Sampled peak 61 C; the supervisor final receipt is corrupted (441 NUL bytes), so clean exit/cleanup is not certified. Original failure evidence remains intact.

CPU-only checkpoint audit verifies its original hash/CRC, finite trainable/optimizer state and saved RNG; CUDA stayed uninitialized. All 72 prior worktree bindings and 45 execution bindings pass. Conservative debit through reboot is 474 seconds, leaving 3,126 seconds of the approved hour. Approval persists for the same recipe; no fresh hour, automatic retry, alternate model or unrecorded replay is authorized. Further GPU work is deferred while the repeated graphics fault is unresolved. Windows denies access to the crash dump; an administrator-provided copy into the ignored local interruption folder is needed for deeper diagnosis. No drivers or system settings were changed.

See [the interruption and recovery record](../ball_tracking_candidate_quality_pilot_interruption.md). Earlier prepared/unrun entries remain historical. Preserve the full-history/research reconciliation, all roles and gates; no selector, new labels, protected access, model adoption or Git integration follows.


## Candidate-quality pilot prepared, 2026-10-28

The candidate-point quality pilot is specified and CPU-prepared; training and neural scoring remain unrun. It uses one pinned point-readout recipe, four fixed six-epoch fits, exact game grouping, complete weak/native/hidden/unknown/missing coverage and unchanged acceptance gates. The budget is 9,870 updates plus fixed scoring/parity, with a one-hour supervised attempt limit. New-scorer game splits are not end-to-end unseen-game tests: cosine nine already saw all three NBA sources. HOU stays excluded from fitting; DET has only the original fixed historical diagnostics. No selector, new labels, protected access, Git integration or training execution is authorized. The earlier capture approval is fulfilled, not recurring.

The protocol is the current entry point for the next experiment, with its data manifest, reading limits and execution boundary.

See [the complete protocol](../ball_tracking_candidate_quality_pilot.md) and its frozen proposal.


## Latest completed evidence, October 28, 2026

[Training-response capture and support census](../ball_tracking_training_response_capture_results.md)
records the approved capture, exact original-output parity, complete hidden/weak/
masked accounting, audit and in-sample limitations. No training or method adoption.


Session 18 resume entry: [complete handoff and required reading](../../data/outputs/t/handoff_2026-10-28_8c040fca385d_session18/COMPLETE_HANDOFF.txt),
prepared October 28, 2026. The completed studies and current worktree are saved;
the next accepted step is to specify the bounded saved-candidate comparison.

Latest continuation: the [point-feature comparison](../ball_tracking_point_feature_comparison_results.md)
is completed and independently audited. Point improves CLS ordering but fails
standalone visibility separation; no new training or tracker is adopted.
Current state, decisions, validation history and source map record both the
useful increments and adverse subgroups. Earlier proposed/not-run language is
preserved as historical context, not the current execution status.

Latest completed work: [saved-response feasibility diagnosis](../ball_tracking_candidate_response_feasibility.md).
The [point-local image-feature comparison](../ball_tracking_point_feature_feasibility_proposal.md)
is the subsequent proposal, not an implemented or run experiment. Current state
and source map distinguish both from the earlier weak-response result below.

Latest completed work: [NBA weak-response feasibility and bounded selection](../ball_tracking_weak_response_results.md).
Use `current_state.md` for the resulting decision and `source_map.md` for the
frozen recipes, primary outputs and historical-review coverage. Earlier handoff
and proposed/not-started records remain historical evidence, not current status.

This directory is the compact desktop handoff for `player-defense-score`. It captures decisions and operating constraints that are important but cannot be reconstructed reliably from source code alone.

## Reading order

- `current_state.md`: exact migration-time checkpoint and next task.
- `decisions_and_invariants.md`: architectural rules that future work must preserve.
- `working_agreement.md`: how to collaborate safely with Ryan and Git.
- `validation_history.md`: reviewed quantitative milestones.
- `roadmap.md`: completed and planned phases.
- `source_map.md`: traceability back to Git, transcripts, attachments, and migration evidence.

The repository README remains the public project overview. `docs/pipeline_generalization.md` remains the detailed authority for the generalized player-coordinate workflow.

## Archive boundary

The six foundation browser transcripts, raw conversation JSON, attachment manifest, and account-export ZIP are archival evidence, not current instructions to replay. They should remain outside Git because they are large, contain repetitive historical commands, and may reference local paths, copyrighted footage, or transient download links.

Before consequential project decisions, consider the entire project history
through `source_map.md` and the linked evidence, then inspect the relevant
primary records in depth. This is required by Ryan's October 26 instruction in
`AGENTS.md` and `working_agreement.md`. The archive boundary keeps bulky raw
transcripts out of Git; it does not prohibit retrieving them when needed.
Track coverage honestly and do not substitute a recent-session summary for
the full-history review.

## Migration snapshot

- Context snapshot date: 2026-08-22 (America/Phoenix)
- ChatGPT project ID: `g-p-6a79418b44a48191a8a902c2ceb0f859`
- Archived chats: 01–06
- User attachments accounted for: 119 of 119
- Separate browser Sources: none
- Local ignored data files hashed: 856 of 856
- Repository context migration: merged through PR #7 at `1f086ba`
