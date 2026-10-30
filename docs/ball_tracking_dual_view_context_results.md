# Dual-view context pilot: completed results, 2026-10-30

The authorized experiment, exact checkpoint continuation, CPU analysis and independent audits are complete. No model or tracker is adopted. The [original protocol](ball_tracking_dual_view_context_protocol.md) and proposal remain unchanged historical design artifacts; this result supersedes their unrun status.

The wider-context LC arm improved held-NBA full-pool ordering to **2,609/2,811 eligible frames (92.81%)**, compared with Q at 2,542 (90.43%) and the matched duplicate-local LL arm at 2,551 (90.75%). Its gains were 69 improvements and 2 regressions versus Q, and 61 improvements and 3 regressions versus LL. Both prespecified acceptance gates failed: some correct detections were lost, and specific source/error protections regressed. The useful result is better ordering evidence together with a precise account of the remaining harms.

These are diagnostic rankings of saved pools. No new selection policy was emitted, no threshold was selected, and saved J remains unchanged. The saved-J original-Q-top result is still 2,541/2,811 (90.39%). Reaching 95% on the separate strict-ranking diagnostic would require at least 2,671 frames, 62 above LC; this is not a claim that the deployed project is only 62 detections from its goal.

The fixed original-Q-top choices contain only 2,542 correct points in 2,811 eligible frames: a **90.43% ceiling for acceptance/rejection of those fixed choices**. Saved J already retains 2,541 of those correct points. A different selection policy would be needed to exceed that ceiling; none is introduced here.

The NBA source games were held out of their respective scorer fits, but the upstream detector had already seen these games. These are **scorer-held comparisons, not end-to-end unseen-game validation**. The one-seed, three-game, correlated-frame evidence does not establish global 95%-correct / 1%-wrong / zero-hidden or temporal/recovery readiness.

Both arms retained the same frozen original-Q local representation and received the same auxiliary capacity, initialization, six epochs and update schedule. LL used another local view; LC used the fixed 192-pixel context view. Field of view and object scale/resampling changed together. The comparison does not isolate outside-context pixels alone. All existing detector results, reference labels, pools and fixed native/original-Q-top choices were reused.

**Full-pool ranking, with eligible frames as denominator.** Strict match-first requires a correct candidate to score strictly above every wrong candidate. Ties, no-matching-candidate frames and nonlocalizable/hidden frames remain separately represented. Strict first rank can occur even when all scores are negative: it does not mean the correct point is accepted or emitted. J values below are diagnostic scores on the same complete pool, not a newly deployed J selector.

| Context | Eligible | Q strict first | LL strict first | LC strict first | J strict first | LC vs Q gained/lost | LC vs LL gained/lost |
|---|---:|---:|---:|---:|---:|---:|---:|
| Held NBA | 2811 | 2542 | 2551 | 2609 | 2795 | 69/2 | 61/3 |
| HOU exposed | 882 | 862 | 859 | 868 | 865 | 6/0 | 9/0 |
| BKN diagnostic | 310 | 294 | 296 | 301 | 302 | 7/0 | 5/0 |
| NFHS secondary | 130 | 115 | 119 | 114 | 127 | 4/5 | 2/7 |
| NBA in sample | 2811 | 2805 | 2803 | 2805 | inapplicable | 0/0 | 2/0 |

The held-NBA pool contains a matching candidate on 2,809/2,811 eligible frames. Nineteen NBA and two NFHS package-empty frames remain in the inventory; they are not fabricated into scoreable candidates. HOU has matches on 876/882 eligible frames and BKN on 305/310. Ranking gains cannot create the missing proposals.

| Held source | Eligible | Q | LL | LC | LC vs Q gained/lost | LC vs LL gained/lost |
|---|---:|---:|---:|---:|---:|---:|
| DEN | 920 | 899 | 907 | 912 | 13/0 | 6/1 |
| CHI | 836 | 730 | 729 | 756 | 28/2 | 29/2 |
| SAC | 1055 | 913 | 915 | 941 | 28/0 | 26/0 |

Most of the held-NBA gain is ordering among frames whose original native detection was already correct: LC adds a net 66 strict-first frames there, plus the one eligible native-missing recovery. The three native-wrong frames do not improve; two have no matching candidate at all. The sole native-missing ranking gain still has a negative LC matching score; saved J already ranks its matching point first and scores it positively in the separate full-pool diagnostic. Neither is an adopted recovery policy. This remains sparse evidence about recovering genuine detector failures. NFHS ordering regresses by one versus Q and five versus LL. HOU and BKN ordering improves without a Q/LL strict-first loss, but both are exposed diagnostic populations and cannot establish an independent primary win.

**Original fixed choices at logit > 0.** Each cell is correct kept / wrong eligible kept / certain-hidden emission frames. Unknown labels are excluded from errors. These counts are policy-specific, overlapping views and must not be added as independent detections.

| Context / original choice | Eligible | Q | LL | LC | J |
|---|---:|---:|---:|---:|---:|
| Held NBA / native | 2811 | 2309 / 0 / 0 | 2348 / 0 / 0 | 2359 / 0 / 0 | 2806 / 3 / 2 |
| Held NBA / quality_top | 2811 | 2275 / 99 / 28 | 2312 / 103 / 30 | 2317 / 93 / 29 | 2541 / 34 / 8 |
| HOU exposed / native | 882 | 798 / 0 / 0 | 798 / 0 / 0 | 804 / 0 / 0 | 841 / 18 / 18 |
| HOU exposed / quality_top | 882 | 825 / 6 / 3 | 824 / 6 / 3 | 830 / 6 / 3 | 855 / 4 / 14 |
| BKN diagnostic / native | 310 | 289 / 1 / 1 | 286 / 1 / 1 | 290 / 1 / 1 | 298 / 4 / 2 |
| BKN diagnostic / quality_top | 310 | 290 / 10 / 2 | 287 / 7 / 2 | 291 / 6 / 2 | 293 / 2 / 2 |
| NFHS secondary / native | 130 | 59 / 0 / 0 | 63 / 0 / 0 | 65 / 0 / 0 | 130 / 0 / 0 |
| NFHS secondary / quality_top | 130 | 66 / 0 / 0 | 68 / 0 / 0 | 69 / 0 / 0 | 115 / 2 / 0 |

LC keeps 50 more held-NBA correct native choices and 42 more correct original-Q-top choices than Q. Against LL, those net gains are 11 and 5. They do not satisfy preservation: versus LL the native policy gains 22 correct identities and loses 11; original-Q-top gains 17 and loses 12. Versus Q, the corresponding gains/losses are 57/7 and 49/7.

**The gates fail for specific reasons.** LC versus LL loses 23 previously kept correct policy identities. SAC also falls from 870 to 869 correct native choices and from 831 to 829 correct original-Q-top choices. Six metric cells improve, but the required source and identity nonregression conditions fail.

LC versus Q loses 14 of 6,207 protected policy identities and one of 547 protected weak-candidate identities; none of 745 protected HOU stress queries is lost. These protection sets overlap and are not summed. DEN original-Q-top accepts one wrong point versus Q's zero, and SAC original-Q-top emits on 27 certain-hidden frames versus Q's 26. Eight primary metric cells improve, but the component gate fails. Every HOU episode/policy count check passes, with no newly accepted Q-rejected wrong/hidden policy identity.

The single lost protected weak point is in SAC episode e06, candidate_7016b37a94c47105e662aa72ade54cda110ba8643f45fd0143b50a389ebb8603. Its logits are Q 1.0654973, LL 0.5476043 and LC -0.0413807. That near-zero example is retained for diagnosis; it does not authorize moving the threshold. Exact policy identities and per-cell checks are in [decision.json](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/dual_view_context_v0_1/analysis_attempt_002/decision.json).

All 21 named stress recovery queries and all six below-.01 queries retain their roles and identities. Q, LL and LC each accept 13/21 and 2/6, respectively; the remaining named negative controls are preserved, not turned into invented positive-veto requirements. Saved J accepts 6/21 and 0/6 on these separate stress selections.

**Overlap with saved J.** The comparison retains all 8,578 original and 720 BKN fixed-policy rows. LC supplies zero newly correct J-rejected choices on either held-NBA policy. It loses 447 J-correct native choices and 224 J-correct original-Q-top choices. On original-Q-top it rejects seven errors J kept but accepts 87 errors J rejected. Across all contexts/policies, the independent audit finds 859 J-correct policy-identity losses and seven error-increase cells; these are overlapping policy views, not 859 independent frames. Drop-in readiness is precluded. HOU original-Q-top has five newly correct J-rejected choices but loses 30 J-correct choices; this exposed slice cannot override the primary failures.

**Additional report-only comparison with J's full-pool ranking.** A post-outcome summary of the already-audited rows finds only three LC gains versus J on held NBA, against 189 losses. All three gains are CHI e02 frames 77, 94 and 102, whose original native choices were already correct. Thus LC's 2,609 strict-first frames are still below J's 2,795 diagnostic strict-first frames. Neither number is an adopted selector result.

On BKN, LC gains three ranking frames versus J and loses four. The gains are adjacent c237 frames 44–46, one short native-failure episode; the losses include three native-correct frames and native-failure frame 47. This is a bounded hypothesis clue, not three independent successes or new validation. The [source-bound derivation](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/dual_view_context_v0_1/report_complementarity.json) is explicitly post-outcome and changes no gate, threshold or policy. An independent reviewer reproduced all these counts.

**Useful error slices.** Among held-NBA weak candidates, correct accepted points rise from 402 (Q) and 409 (LL) to 411 (LC), while wrong eligible accepted points fall from 341/357 to 290. Certain-hidden accepted weak candidates rise from Q's 38 to LC's 40; their distinct hidden emission frames rise from 28 to 29. Candidate counts and frame counts are different units.

| Known distant-negative geometry | Candidate rows | Q accepted | LL accepted | LC accepted |
|---|---:|---:|---:|---:|
| inside192_inside_nominal56 | 2673 | 6 | 9 | 8 |
| inside192_outside_nominal56 | 4753 | 60 | 61 | 48 |
| outside192 | 6350 | 281 | 294 | 241 |

This geometry describes where an accepted reference center falls relative to a candidate crop. It does not certify ball visibility or semantic identity. The 65 NBA boundary-unknown training targets remain masked and separate from the 13,776 known distant negatives; their original fixed-10px evaluation categories remain unchanged. Game/block, visibility, origin, native outcome, padding, boundary and historical-role slices are saved in the full zero tables and paired rows. All score breakpoints are diagnostic, with no chosen threshold.

**Fitting health.** Final weighted BCE uses the original training multipliers and the final epoch-six scores. Captured Q uses the original checkpoint for the same fit; saved control logits are unchanged.

| Fit | Known fitting rows | Captured Q weighted BCE | LL weighted BCE | LC weighted BCE | Q / LL / LC strict-sign correct |
|---|---:|---:|---:|---:|---:|
| leave_chi_out | 11954 | 1.1731036e-05 | 1.38319851e-05 | 9.78875089e-06 | 11953 / 11953 / 11954 |
| leave_den_out | 11912 | 0.000497507874 | 2.10470485e-05 | 1.91172573e-05 | 11909 / 11912 / 11912 |
| leave_sac_out | 11182 | 1.67228848e-05 | 1.41475145e-05 | 1.30307604e-05 | 11182 / 11182 / 11182 |
| all_nba | 17524 | 0.000158833179 | 7.79200875e-06 | 6.42445435e-06 | 17522 / 17524 / 17524 |

LC classifies every known fitting target with the correct strict sign in all four fits and has lower final weighted BCE than LL in each fit. LL has only one strict-sign miss, in the CHI-held fit. This argues against a gross failure to learn the fitting objective; it does not uniquely separate generalization, training-support, representation and optimization limits. All-NBA in-sample ordering remains a separate view and must not be pooled with source-held evidence.

**Population and verification.** The report contains 53,723 candidate views, 9,298 fixed-policy rows, 7,828 frame views and 177,484 final scores. The candidate/frame views include a separately labeled 18,813-candidate/3,179-frame NBA in-sample view. The original package is 19,632 candidates/3,329 frames; HOU retains all 960 frames, BKN all 360 diagnostic frames, and NFHS all 150 frames. Eighteen DET historical queries remain metadata-only with no new score or evaluation; all eleven originally missing stress slots remain explicitly missing. All 6,720 saved source-choice rows and 6,720 contrast rows are preserved.

Captured Q agrees with 53,694 overlapping saved controls, with maximum absolute difference 9.5367431640625e-07, within the frozen tolerances and with identical zero signs and saved identities. [Independent analysis audit](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/dual_view_context_v0_1/audit/independent_analysis_audit_attempt_002.json) passed: exact score routes and source joins, all 25,384 zero-table cells, 694,421 strict-curve breakpoints, full uncapped rankings, all gates/protections/cases and final weighted-BCE arithmetic were independently checked without importing the project analysis helpers. The separate [combined numerical/journal audit](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/dual_view_context_v0_1/audit/combined_attempt_002/completed.json) also passed. It covers all 177,484 final head scores through CPU reconstruction and reused immutable proofs, with zero sign changes, and independently accounts for all 76,105 journal events. The largest new head reconstruction difference was 3.814697265625e-6, within unchanged tolerances. No encoder/CUDA work occurred during these audits. The initial implementation had 47 passing focused tests; 19 additional recovery checks covered actual checkpoint restoration, the watcher-loop defect and shared deadlines. The original tests had not covered the copied watcher deadline mismatch. Three auditor-ledger regression tests cover a metadata-only normalization fix: the failed audit receipt and prior auditor source remain preserved; predictions and numeric tolerances were unchanged.

**Operational interruption and exact continuation.** The first attempt stopped because a copied event watcher still used a 1,770-second soft deadline/1,800-second limit even though the reviewed launcher/worker used 5,370/5,400 seconds. The adapter had changed the launcher constants but missed the watcher. Its ready handshake checked status without checking deadline agreement. This was a software supervision defect, not an observed GPU fault. The first launcher retained its failed status; its peak temperature was 64 C and zero owned processes remained after cleanup.

New helpers use one shared 3,611-second remaining execution cap with a 3,581-second soft stop, debiting the first launcher's 1,788.469 seconds conservatively as 1,789 from the original 5,400-second allowance. CPU-only repair time was excluded explicitly; no fresh 90-minute GPU budget was created. Actual watcher-loop tests reproduced the old failure and verified the corrected deadline behavior. The second launcher completed cleanly with peak temperature 63 C, no forced stop, no cleanup error and zero owned processes remaining. Its charge was 1,095.047 seconds; the conservative cumulative charge was 2,884.047 seconds. The exact sum of both launch charges was 2,883.516 seconds (48 minutes 3.516 seconds), excluding CPU-only repair downtime. Both post-stop/post-run checks found no qualifying Windows fault or remaining owned worker. True Color remained permitted under the existing exception; Debug Mode ON was freshly observed, and no GPU setting was changed.

The continuation reused all six completed local-capture streams and five completed fits. SAC LC restored the epoch-three checkpoint at 1,050 logical updates, including trainable tensors, optimizer moments and RNG state; the trainable/optimizer round trip was exact. Sixty-seven updates after that saved checkpoint had already run before interruption and were necessarily replayed. Their loss and gradient-norm values matched exactly, with zero added forwards for that diagnostic. No completed fit or local capture was rerun.

| Work accounting | Logical frozen endpoint | Actual physical work | Difference |
|---|---:|---:|---:|
| Backbone forward calls | 28,082 | 28,149 | 67 |
| Candidate presentations | 897,474 | 899,618 | 2,144 |
| Optimizer updates | 19,740 | 19,807 | 67 |

The completion and analysis publish both logical and actual physical counters. Actual work is not disguised as the original logical count. No extra epoch, seed, model, data addition, threshold tuning/selection or selector integration was introduced. The full diagnostic threshold curves were computed as prescribed.

**Bound interpretation.** The wider-input package improved held-source ordering and reduced several wrong-candidate slices beyond matched extra local capacity. It did not meet the fixed-zero acceptance or original-success-preservation requirements, and it does not beat the existing saved J on the original primary choices. The result supports preserving the exact ranking gains and harms for the next design decision. It does not support adopting LC, rescuing this run by choosing a new threshold, declaring context solved, or claiming 95% project completion.

Primary artifacts: [summary](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/dual_view_context_v0_1/analysis_attempt_002/summary.json), [decision](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/dual_view_context_v0_1/analysis_attempt_002/decision.json), [ranking tables](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/dual_view_context_v0_1/analysis_attempt_002/ranking_tables.jsonl), [final training health](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/dual_view_context_v0_1/analysis_attempt_002/training_health_summary.jsonl), [preserved named cases](C:/Users/Ryan/Projects/player-defense-score/data/outputs/ball_tracking/dual_view_context_v0_1/analysis_attempt_002/preserved_cases.json).


## Next recommendation and due diligence

Prioritize a **CPU-only design/feasibility check for a small, diverse set of actual current-detector failures on additional permitted NBA development games**, together with correct source-time controls and an explicit separate evaluation source. This is the next design question, not an approved new fit, data acquisition result or claim that more data must solve the problem. First determine which suitable sources and reference workflow are available without reopening protected footage or repurposing diagnostic games. Do not rerun the completed overlap tables, curves, coverage census or old-proposal experiment merely to obtain the same conclusion.

The immediate question is whether we can obtain usable, clearly labeled examples of the decisions that are currently missing from fitting: selected wrong native points, certain-hidden native emissions and genuinely needed weak recoveries, across distinct games/plays. Existing correct decisions remain preservation controls. Freeze source roles before future scoring or reference-assisted selection; retain unknown/boundary labels and human reference acceptance. If no suitable sources exist, report that concrete limitation before proposing new acquisition or annotation work. If support exists, only then design one controlled comparison, with its recipe and held-source evaluation fixed before a new fit. HOU remains descriptive/veto only; BKN stays exposed diagnostic/nonfitting and cannot supply primary validation or be silently converted into fitting data.

This priority follows several specific findings:

- The [training-support review](ball_tracking_candidate_training_coverage_review.md) already established that all 3,179 accepted NBA frames are used. The three selected wrong native points are boundary-unknown for fitting; the only two native-hidden targets are adjacent frames; 609 of 610 weak positives accompany a correct native choice. Reweighting cannot create absent situations.
- The [alternate-producer treatment](ball_tracking_candidate_producer_transfer_results.md) already tested 461 additions on existing scenes and failed. It did not supply diverse fresh-scene failures of the current detector. Repeating those additions is not the proposed direction.
- This context experiment learned all known fitting targets yet failed preservation; its extra ranking successes are predominantly already-native-correct frames. No new correct J-rejected fixed choice appears on held NBA or BKN. Immediate LC-for-J substitution, a blind fusion fit, or a threshold rescue is therefore not supported.
- Context still provides controlled ordering evidence versus LL and a narrow BKN diagnostic clue. Preserve its checkpoints and exact successes/harms as potential ingredients for a later comparison. Do not discard the evidence or assume the representation question is settled.

The lack of fitting support is demonstrated; its causal responsibility for every error is not. Representation limits, target ambiguity and source generalization remain alternatives. A new source/support design is valuable only if it creates the missing decision situations and an honest evaluation opportunity, not merely more correlated points. Fitting an integration model to the present mistakes would risk teaching or selecting against the same exposed few episodes. Any future integration must retain original Q/J as controls and use a newly specified training/evaluation design rather than treating their logits as interchangeable.

The completed design's research review was reused, and two primary sources were refreshed for this recommendation. [DCR, especially its hard-false-positive and training/sampling discussion](https://arxiv.org/html/1803.06799v3) supports investigating actual detector mistakes with correct/background controls; it does not validate this project's crop geometry, point labels or a particular quota. [Kumar et al. on feature distortion](https://arxiv.org/abs/2202.10054) shows why strong fitting can coexist with worse shifted-source results; its abstract does not establish the mechanism in our frozen-local/partially-adapted auxiliary model or justify an automatic LP-FT change. These are motivations and cautions. The recommendation is an inference from this project's saved evidence, not an imported promised effect size.

This turn reused the maintained Sessions 1–19 reconciliation and subsequent results, then directly reviewed the current protocol, saved failure/acceptance/support/producer-transfer findings, actual new scores and independent audits. It does not claim a fresh reread of every historical chat or paper. Independent reviewers challenged both numeric interpretation and the next recommendation.

## Preservation and reproducibility

Both frozen implementation packages, original failed run, exact continuation checkpoints, all completed captures/fits and failed-audit evidence are retained. The result ledger is `configs/ball_tracking/reviews/dual_view_context_result_v0_1.json`. The delivery bindings and `data/outputs/ball_tracking/dual_view_context_v0_1/documentation_update/receipt.json` record final review and additive maintained-history updates. All 174 inherited working-file contents are preserved: 165 remain byte-identical and nine receive reversible additions with exact prior-byte archives. Original scientific inputs and reused runtime outputs are additionally verified by their frozen bindings. Git branch `codex/ball-detector-baseline`, HEAD `8c040fca385dd8fffa0d7a13c45c53e79950bae1`, and the empty index remain unchanged; no staging, commit, push or cleanup occurred.
