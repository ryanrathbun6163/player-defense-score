# Ball tracking: results and research lessons

The ball-tracking work has produced useful detector learning, better candidate scoring and controlled evidence about remaining failures. It has **not** produced an accepted complete automatic tracker or a validated defensive score. This overview distinguishes those outcomes so the numbers can be evaluated on their actual populations.

## What the components mean

| Component | Role |
|---|---|
| **Native detector** | A temporal WASB-based heatmap model and its original point-selection rule. The current research control is the cosine-epoch-nine checkpoint. |
| **Q** | A learned image score for the geometric usefulness of an existing candidate point, using partially adapted DINOv2 features. |
| **J** | A separate acceptance score combining Q with observable response and candidate-pool evidence. It keeps or rejects an already selected point. |
| **LL** | Experimental fusion of frozen Q local features with a trainable auxiliary view of the same local crop. |
| **LC** | The matched fusion experiment using a fixed 192-pixel context crop for the auxiliary view. |

“Original Q-top” fixes the candidate chosen by the original highest Q score. Changing its acceptance score does not rerank candidates or fall back to another point. Full-pool ranking is a separate diagnostic. A correct top-ranked candidate can still have a negative score and be rejected.

## 1. Learned detection made a real difference

Specialized adaptation improved a small NFHS development sample from **31 to 98 to 120 correct locations out of 145** at the same 0.5 threshold. A separately reviewed 0.3 setting reached 130/145. These are development results, not NBA-wide performance. Later research moved to harder NBA footage and larger accepted reference sets. See the [adaptation results](ball_wasb_expanded_adaptation_results.md).

The current native research detector obtains 219/241 correct on inspected DET footage, 842/882 on exposed HOU development frames and 298/310 on the three-window BKN diagnostic. These populations must remain separate. The persistent 19-frame DET gap lasts about 317 ms, and HOU/BKN retain wrong or hidden emissions. High correct-location fractions alone do not establish readiness. See [continuation results](ball_tracking_wasb_continuation_results.md).

## 2. Acceptance improved without changing the selected point

On 2,811 eligible NBA frames, applying J instead of Q to identical original-Q-top choices produced:

| Fixed original-Q-top acceptance | Correct kept | Wrong eligible kept | Certain-hidden emission frames |
|---|---:|---:|---:|
| Q | 2,275 | 99 | 28 |
| J | **2,541** | **34** | **8** |

This adds 266 correct acceptances, removes 65 wrong outputs and removes 20 hidden emissions relative to Q. It restores points Q rejected; it does not find 266 additional balls beyond the native detector. The result is 90.39% correct on this population, and other gates still fail. [Acceptance results](ball_tracking_candidate_acceptance_gate_results.md).

There is also a structural limit: original Q-top selected only 2,542 correct points before rejection. Its 90.43% ceiling is below 95%, so acceptance alone cannot complete this particular policy. The native choice is a distinct control; its success must be protected when considering alternatives.

## 3. A new-game diagnostic exposed useful tradeoffs

The BKN diagnostic contains 360 accepted frame judgments: 310 eligible centers, 32 certainly hidden and 18 unknown. No model was fitted on it.

| Fixed policy on BKN | Correct / 310 | Wrong eligible | Hidden emissions / 32 |
|---|---:|---:|---:|
| Native, without acceptance filtering | 298 | 6 | 2 |
| Native + J | 298 | 4 | 2 |
| Original Q-top + J | 293 | 2 | 2 |

J preserves every correct native choice while rejecting two wrong ones, but hidden emissions remain. A matching proposal exists on 305/310 eligible frames: five lack a usable candidate, while other failures involve choice or rejection. These three two-second windows are diagnostic development, not representative full-game evaluation. [Diagnostic results](ball_tracking_fresh_game_diagnostic_results.md).

## 4. Wider context helped ranking but failed preservation

Eight fixed six-epoch fits compared LC against matched LL capacity and the saved Q/J controls. On the complete held-NBA candidate pools:

| Score | Strict correct-first frames / 2,811 |
|---|---:|
| Original Q | 2,542 — 90.43% |
| Duplicate-local LL | 2,551 — 90.75% |
| Local-plus-context LC | **2,609 — 92.81%** |

LC gained 69 and lost 2 strict-first frames versus Q. However, both prespecified acceptance gates failed: it lost 23 LL-kept correct policy identities, 14 protected Q policy identities and one protected weak candidate. Those protection views overlap. Of the net 67 ranking gains over Q, 66 occurred where the native detector was already correct; the sole native-missing gain remained LC-negative.

The 92.81% is **ranking evidence, not emitted tracking accuracy**. Saved J remains stronger on the primary fixed choices and has 2,795 strict-first diagnostic rankings on the same pool. No LC replacement, new threshold or argmax selector was adopted. [Context results](ball_tracking_dual_view_context_results.md).

## Evaluation discipline and scope

The target combines at least 95% correct locations within ten source pixels, at most 1% wrong eligible outputs, zero certain-hidden emissions, per-context checks, bounded missing runs and recovery, and complete synchronized human review. Unknown references are not relabeled as negatives. Exact gains/losses matter alongside totals.

The NBA scoring folds hold games out of the candidate scorers, but the detector previously trained on those games. They are **not end-to-end unseen-game tests**. HOU is repeatedly exposed development; BKN is now exposed diagnostic data; protected evaluation remains closed. Upstream pretraining's complete game inventory is unknown. Adjacent frames are correlated observations, not independent trials.

These controls helped reject specific unsuccessful recipes: origin-feature removal, a 461-point alternate-producer addition and the wider-context acceptance treatment. The evidence favors addressing actual current-detector failures on additional sources, rather than repeatedly optimizing the same exposed examples. [Training-support review](ball_tracking_candidate_training_coverage_review.md), [producer-transfer results](ball_tracking_candidate_producer_transfer_results.md).

## Inspecting and reproducing the work

The repository provides [evaluation code](../src/ball_tracking/candidate_acceptance_evaluation.py), [synthetic CPU tests](../tests/test_candidate_acceptance_evaluation.py), frozen protocols and result summaries. Full reproduction additionally requires the original permitted video, accepted references, model checkpoints and saved artifacts; these large/local inputs are not bundled with the source repository. The [project overview](project_overview.md) provides the architecture and code tour. Reported component progress does not substitute for a complete trajectory evaluation or the future defensive-scoring model.
