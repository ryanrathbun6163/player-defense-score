# NBA ball tracking: full-history reassessment

October 26, 2026. Reviewed on `codex/ball-detector-baseline`, HEAD
`8c040fca385dd8fffa0d7a13c45c53e79950bae1`. The four pre-existing uncommitted
full-history instruction/context changes were preserved. This is a historical
review, a read-only recount of saved development outputs, and a recommendation.
It does not execute a new selector, inference campaign or training experiment.

## Decision

**Keep the current-model weak-response/motion direction, but put a feasibility
test first, with a small existing-candidate selection control.** Do not build a
large tracker around only candidates above 0.3: its current best-possible
coverage is already below 95% in three NBA contexts. Do not start another
unchanged training extension before distinguishing inadequate visual evidence
from selection failure.

Use saved cosine epoch nine as the declared research control. It retains the
same Houston candidate opportunity as spatial epoch seven while having better
Detroit coverage and fewer certain-hidden Houston emissions. This is a
development comparison choice, not adoption or an independent test result.

This changes the earlier proposed ordering of a substantial strong-candidate
selector followed by weak-candidate work. Measure the weak-response opportunity
and clutter first; a simple paired selector can then test whether it is usable.
The history supports this as the best-supported next bounded experiment among
the inspected options, not a guarantee that it will finish the phase.

## Review coverage and limits

All sixteen numbered Ball Tracking chats were retrieved through their complete
available timelines: **398 turns over 47 pages**, each ending with
`hasMore=false`. Review covered user/final-answer timelines, relevant commentary,
handoffs and decision-relevant primary reports. Some long later messages were
read through bounded excerpts and followed into their full primary reports.
This is not a claim to reread every raw command output or commentary character,
rewatch every video, or independently reproduce every old experiment.

Coverage receipts and extracted messages remain ignored local evidence:

- [Sessions 01–05 coverage](../../data/outputs/t/full_history_review_20261026/session_01_05/coverage.json)
  and [review](../../data/outputs/t/full_history_review_20261026/session_01_05/review.md).
- [Sessions 06–10 coverage](../../data/outputs/t/full_history_review_20261026/session_06_10/coverage.json)
  and [findings](../../data/outputs/t/full_history_review_20261026/session_06_10/findings.json).
- [Sessions 11–16 coverage and review](../../data/outputs/t/full_history_review_20261026/session_11_16/review.json).
- [Earlier foundation review](../../data/outputs/t/full_history_review_20261026/foundation/review.json).

The six earlier foundation chats are a separate series. Their original goal,
selected historical decisions, closing checkpoints and relevant committed
player-pipeline evidence were reviewed; those six full transcripts were not
reread line by line. Current-session completed training and diagnoses were also
included. Original human reviews remain authoritative; AI historical review
does not create new human approvals. No material unresolved historical finding
was identified that changes the recommendation below.

## Evidence across all sixteen sessions

Session numbers resolve to the exact titles and IDs in the
[source map](../context/source_map.md#ball-tracking-session-coverage-2026-10-26).
The group receipts above retain additional source paths and review-status detail.

| Session | Turns | Material finding and consequence |
|---|---:|---|
| 01 | 56 | Accepted-label and RF-DETR baseline work already found correct balls outranked by distractors. Lowering .35 to .20 recovered nine correct detections but added 48 false candidates. More candidates was never sufficient by itself. |
| 02 | 21 | Pilot human review and development labeling progressed. A calendar gap and annotation work were not months of uninterrupted model fitting. Completed reviews should not be requested again. |
| 03 | 26 | Early tracklets commonly lost correct detections; settings gaining matches also added false guesses. Crops improved candidate availability but left selection and clutter problems. |
| 04 | 28 | Related motion and player-context iterations made real gains. The context refinement corrected P002/262 without regressions against its paired window controls. RF contained qualifying candidates on 140/145 eligible frames, yet selection remained difficult. The tested generic YOLO challenger was weaker. |
| 05 | 12 | Of 20 persistent misses, 15 had weak qualifying candidates and eight also suffered top-20 cap loss. The uncapped .01 comparison ran; rendering interruptions delayed its answer. Those interruptions were engineering failures, not scientific rejection evidence. |
| 06 | 13 | Render recovery and six human reviews completed. Later scientific interpretation found no correct-count benefit from removing the cap in the four settings; some wrong/hidden outputs increased. Preserve both completed review and adverse result. |
| 07 | 45 | A half-second folder-accounting rule caused extensive monitor/recovery work. Separating frequent safety checks from slower accounting resolved the design issue. Do not recreate this administrative overhead for the next small experiment. |
| 08 | 25 | Human inspection of eight selected failures found seven other-object marks and one off-center ball mark. Historical confidence could outweigh stronger current evidence. Stable history can preserve the wrong object. |
| 09 | 16 | Average instead of summed path confidence improved pooled counts but lost seven previously correct P001 challenge frames. Complete window-level gains/losses matter more than an attractive aggregate. |
| 10 | 15 | Cross-detector implementation and process-ownership repairs completed, but the scientific run had not succeeded by session close. Later recovered results reduced correct counts and removed no wrong/hidden alarms; software completion was not model progress. |
| 11 | 35 | WASB's fixed-.5 results improved 31 to 98 to 120/145 through adaptation and data expansion; the reviewed .3 setting reached 130/145. Training and iteration worked. Old weak-response diagnosis also found matching components that blind mass selection failed to choose. |
| 12 | 12 | Past-only WASB motion selection tied the same-context scored totals, while changing unscored frames, including visible-ball losses. It left all 294 empty frames empty. This was not a current-model weak-response test. |
| 13 | 10 | NBA acquisition and 120 accepted easy references established usable footage and labels. Easy pilot success did not establish difficult continuous tracking or a fresh independent test game. |
| 14 | 17 | NBA adaptation improved training-scene SAC but slightly regressed excluded DET. Expanded strict-.3 contributor pools recovered nine of 45 unavailable DET/NFHS candidates while adding ambiguity. Short-gap repair then produced three accepted corrections. |
| 15 | 17 | Continuous repair gained additional points but followed a head between two wrong anchors. Later labels confirmed eight additional geometric matches, with identity caveats. A fitted DINO-based crop verifier removed 207/581 previously correct points. Neither smoothness nor this generic appearance veto solved identity. |
| 16 | 50 | The accepted reference campaign and fixed data roles became substantial reusable assets. Primary GPU failures left update 500 as a recovery checkpoint. Actual fit completion belongs to this later continuation; preserve both failure history and subsequent completion. |

Key primary reports include the [crop/motion factorial](../ball_crop_motion_factorial_results.md),
[player-context refinement](../ball_crop_player_context_results.md),
[cross-detector result](../ball_crop_cross_detector_corroboration_results.md),
[WASB expanded adaptation](../ball_wasb_expanded_adaptation_results.md),
[remaining-gap diagnosis](../ball_wasb_remaining_gap_diagnosis.md),
[WASB motion result](../ball_wasb_motion_selection.md),
[candidate preservation](../nba_candidate_preservation_experiment.md), and
[appearance-verifier result](../nba_ball_distractor_training_results.md).

### Correcting the historical gap-repair summary

The original [short-gap comparison](../nba_temporal_gap_selection_experiment.md)
added three correct positions on the original 790-frame reference set. Its
continuous extension added fourteen positions: those three plus eleven that
were initially unscored. The later
[accepted-reference evaluation](../nba_gap_anchor_reference_evaluation_results.md)
added 27 judgments, of which 22 were geometrically eligible and five unknown.
Fourteen original matches plus eight original misses became 22 matches.

Six of those eight additional matches had AI-supported ball identity; the two
P001 additions remained identity-ambiguous. SAC/1419–1421 retained unknown true
ball centers while separate visual evidence identified a head at the original
anchors and new fill. Therefore neither "only three gains ever" nor "eight
additional confirmed ball identities" is an accurate history. Unknown geometry
must not erase an adverse object-identity observation or become a hidden-negative
label without evidence.

### Lessons from the earlier foundation

Forced five-to-five player assignment once manufactured wrong identity links;
cleaner evidence exposed them. A court-motion repair initially trusted frame
492, while later video review showed corruption began much earlier and frame
469 was the usable anchor. Bracketed player interpolation remained explicitly
inferred, preserving observed rows and leaving leading gaps missing. Numerically
clean player counts still required visual identity review.

Apply those lessons here: do not force one ball per frame, do not assume stable
endpoints identify the ball, do not count a predicted line as an observation,
and fix the causal layer rather than smooth over a recognition failure. The
[P003 player gate](../pipeline_generalization.md#possession-003-empirical-validation)
does not certify NBA identities, calibration, or ball tracking.

## Current saved-output check

A CPU-only recount checked the current cosine-nine and spatial-seven paired
review inputs against all sixteen original producer records: hashes and all
7,324 observation rows agree. It reproduced the published correct/wrong/missing
totals and counted whether each existing candidate pool contains a point within
the unchanged ten-source-pixel radius. No selector or model ran.

Evidence: [candidate recount](../../data/outputs/t/full_history_review_20261026/current_candidate_audit.json),
[recount source](../../data/outputs/t/full_history_review_20261026/current_candidate_audit.py),
[producer agreement](../../data/outputs/t/full_history_review_20261026/current_candidate_producer_check.json).

| Cosine-nine context | Current correct | Maximum with perfect choice from existing >.3 candidates | Correct needed for 95% |
|---|---:|---:|---:|
| DET | 219/241 | 219/241 | 229 |
| HOU e01 | 110/120 | 110/120 | 114 |
| HOU e05 | 195/212 | 200/212 | 202 |

These are label-informed diagnostic ceilings, not demonstrated automatic
performance. They prove existing-candidate selection alone cannot pass those
three contexts. Across HOU, 15 of cosine-nine's 19 wrong selections do contain
a correct alternative (the same 15/19 count as spatial seven). That remains a
real selection opportunity, not proof a label-blind rule will recover all fifteen.
HOU pooled totals must not replace per-episode gates.

The [completed continuation](../ball_tracking_wasb_continuation_results.md) and
[spatial experiment](../ball_tracking_wasb_spatial_results.md) show repeated
training variants, not just one attempt. Current training fit is 2,937/2,941,
yet the 19-frame DET gap persists. Cosine nine has DET 219/1/21 and 19 certain-hidden
HOU emissions; spatial seven has DET 218/2/21 and 20 such HOU emissions. Both
have HOU 842/19/21 and SAC 270/0/0. Neither passes or is adopted.

## Revised next experiment

1. **Freeze one current checkpoint and paired baseline.** Use cosine nine as a
   declared development control; preserve the retained reviewed baseline and
   every other checkpoint. Spatial seven can corroborate saved diagnostics,
   without becoming an opportunistically selected replacement after tuning.
2. **Measure weak-response feasibility before a large selector implementation.**
   On the permitted existing contexts, measure actual extracted weak candidates,
   coverage ceilings, competing candidates, hidden-frame responses and path
   ambiguity. A nonzero pixel near a reference is insufficient. Include heads,
   hands, wrong anchors and real reacquisition. Use references only to assess
   diagnostic opportunity or score outputs, never to seed or choose a deployed
   path. Check both mean-map extraction and whether it discards useful local
   structure; do not assume lowering a cutoff always preserves separate objects.
3. **Run a small paired selection comparison if usable support exists.** Compare
   unchanged selection, a simple sequence rule on existing candidates, and that
   same rule with weak candidates. Make before-and-after context available,
   retain an explicit missing state, and allow revision of an original wrong
   choice. Fix one factor at a time in a few reasoned follow-ups. Do not preserve
   an original head detection merely because the old gap-only method did so.
4. **Judge complete trajectories and exact gains/losses.** Apply every existing
   per-context accuracy, error, hidden-output, gap, recovery and human-review
   rule. A positive development increment can justify another refinement while
   the phase still fails. It does not become an accepted method automatically.
5. **Change the recognition experiment when the evidence warrants it.** If weak
   candidates cannot cover the actual remaining deficits, or cannot be separated
   from persistent wrong-object paths, stop geometry-only tuning. A higher-detail
   view can test whether image scale is the missing information; matching crop-aware
   training would be justified only if that probe supports it. Existing RF crop
   work and the later resolution fit are prior evidence to compare, not untouched
   ideas. Existing training labels stay in their original roles.

The old greedy motion rule was past-only and never introduced sub-.3 candidates.
The old two-ended repair was already offline, but used strict-.3 contributor
candidates, preserved all original observations, and limited anchor span to
120ms. The proposed test must be distinguished by its actual weak-response,
wrong-choice and uncertainty handling, not merely by calling it temporal.

Saved DET/SAC raw maps can support CPU analysis. The inspected HOU comparison
directories reuse validation observations and do not contain those raw maps;
do not promise the whole study is inference-free. Inventory upstream caches,
then obtain any genuinely missing maps with one scoped monitored inference pass
if the experiment is authorized. This requires no new labels or initial fit.
No precise runtime is claimed before that inventory and implementation scope.

## Data roles and unchanged acceptance

The [source-role manifest](../../configs/ball_tracking/completion_campaign/source_roles_v0_1.json)
keeps SAC/CHI/DEN in fitting, HOU in checkpoint validation, and DET excluded from
fitting/checkpoint selection. Proposed selector-parameter use of HOU must be
declared prospectively; its old role is not unlimited tuning authorization.
Apply a locked method to DET. Its inspected labels can establish diagnostic
ceilings but must not become inference anchors or training targets. DET and HOU
have been inspected repeatedly and are not independent final-test evidence.

Keep at least 95% correct automatic locations within ten source pixels, at most
1% wrong eligible outputs, zero certain-hidden/out-of-view emissions, no eligible
missing run over 200ms, no confirmed wrong-object run lasting 120ms or longer,
and the existing 120ms recovery/stability definition. Preserve synchronized
human review, original uncertainty/censoring, and inferred/manual-as-absent
automatic scoring. Protected evaluation stays closed.

Nine source-uncertain recovery events remain independently inconclusive under
the frozen scorer, as documented in the continuation result. Improving predictions
alone cannot clear them. Preserve that separate evidence limitation without
quiet relabeling, changing the scorer, or treating it as an excuse for real errors.

## Alternatives and operating decision

More unchanged epochs have weaker support than this diagnostic because multiple
continuations improved training fit without fixing the key development gap.
A new pretrained model remains a possible comparison, not an established shortcut:
the project already used basketball-pretrained WASB, generic YOLO and TAPNext++.
The TAP result rejects its tested single-seed policy, not all learned tracking.
MonoTrack remains one possible bounded challenger if current evidence is
inadequate; its availability does not show superiority. Repeating the rejected
DINO hard veto is likewise not supported.

NBA footage remains the goal. No ACB metric prototype or outside CV reviewer is
part of this recommendation. Preserve the high-school evidence as secondary
regression history. Keep routine engineering and validation proportional: one
reused comparison path, a few justified variations, and concise decision reports.
Infrastructure check counts and successful rendering are not ball-quality gains.

This review authorizes no new scientific execution. The next implementation
should turn the experiment above into a concrete bounded comparison using the
existing pipeline and unchanged criteria; it should not restart labeling,
create another large release framework, or promise phase completion.
