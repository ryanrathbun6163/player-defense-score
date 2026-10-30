# Candidate acceptance gate v0.1 results — 2026-10-29

The joint acceptance gate adds useful discrimination to the existing quality
score, especially for the quality-top policy, but it fails the complete
preservation criterion. On the three held NBA games, quality-top improves from
2,275 correct / 99 wrong / 28 hidden emissions under raw quality to 2,541 / 34 / 8
under the joint gate at the fixed zero reference. It preserves every NBA
quality-top correct point previously kept by raw quality or the score-only
adjustment. However, it admits new wrong and hidden native points in CHI,
increases HOU hidden emissions, and loses known HOU recoveries. No model,
threshold, selector, or tracker behavior is adopted.

The accepted saved run is
`data/outputs/ball_tracking/candidate_acceptance_gate_v0_1/attempt_001/`.
Independent audits passed: 152,617 neural transport/accounting/supervision
checks, 16,520 tensor checks, and 3,328,460 CPU-output checks. All eight CPU fits
converged. The interpretation below is based on saved outputs; it does not
refit anything or choose an operating threshold.

**What was tested and preserved.** The exact
[candidate acceptance protocol](ball_tracking_candidate_acceptance_gate_protocol.md)
was implemented. Q is the reused raw quality score; S is a monotonic score-only
adjustment; J is the fixed 16-feature joint gate; M is the fixed spatial
competition control, with its declared raw-quality fallback. Both original
native and quality-top choices were fixed before acceptance. A rejected point
becomes abstention, with no reranking, fallback point, trajectory change, or
replacement detection.

The three new single-game quality fits supplied honest nested scores for gate
training: 3,300 updates, 105,144 training presentations, 37,626 cross-game scores,
and 4,481 total neural forwards. Existing checkpoints, caches, original scores,
labels, completed pilot results, and CPU failure-study results were reused.
No completed old experiment was rerun. The supervised neural workload took
448.906 seconds including charged startup, with a maximum observed GPU
temperature of 63 C, power of 155.32 W, and memory of 3,206 MiB across 216 samples.
It exited cleanly, without an automatic retry or surviving owned processes.
The CPU analysis took 28.297 seconds.

Before launch, an initial readiness helper misclassified ordinary NVIDIA WDDM
desktop contexts as competing model workers. That rejection occurred before
any launcher or model execution. The original helper, rejected readiness,
inventories, and unused freeze were preserved; a separately reviewed versioned
classifier corrected the issue without changing the scientific recipe or
supervision policy. Verification included 54 focused tests, 13 supervision
checks, and 12 readiness-correction tests. This establishes the documented
execution conditions; it does not claim the desktop GPU was globally idle or
prove a permanent hardware fix.

The complete analysis retains 4,289 context frames and 31,430 candidate slots
per arm: 31,419 observed and 11 missing. It also retains 8,578 fixed-policy rows,
6,720 original source choices, 6,720 contrast views, 60 historical rows, 5,176
candidate zero tables, 7,904 policy zero tables, 239 candidate curve records,
and 339 policy curve records. The independent audit checked 407,057 candidate
and 103,690 policy curve steps. Unknown labels remain unknown, missing scores
remain null, and repeated candidate slots are distinct from distinct-frame
emission counts.

**Read the fixed-zero results by source first.** Each cell below is
`correct kept / wrong eligible kept / certain-hidden emission frames`.
Acceptance means score strictly greater than zero. Correct and wrong counts
refer to the original eligible frames; hidden emissions refer to the original
certain-hidden frames. The full frame inventory also includes masked or other
unknown-reference frames and missing choices. These are retained in the saved
tables rather than counted as known errors or removed from denominators.

| NBA source | All frames | Eligible frames | Certain-hidden frames | Policy | Q0 | S0 | J0 | M0 |
|---|---:|---:|---:|---|---|---|---|---|
| CHI | 960 | 836 | 50 | Native | 637 / 0 / 0 | 656 / 0 / 0 | 831 / 3 / 2 | 733 / 1 / 0 |
| CHI | 960 | 836 | 50 | Quality-top | 636 / 17 / 2 | 653 / 27 / 2 | 729 / 9 / 1 | 729 / 103 / 29 |
| DEN | 960 | 920 | 10 | Native | 808 / 0 / 0 | 855 / 0 / 0 | 920 / 0 / 0 | 894 / 0 / 0 |
| DEN | 960 | 920 | 10 | Quality-top | 811 / 0 / 0 | 856 / 2 / 0 | 899 / 0 / 0 | 897 / 21 / 2 |
| SAC | 1,259 | 1,055 | 68 | Native | 864 / 0 / 0 | 892 / 0 / 0 | 1,055 / 0 / 0 | 904 / 0 / 0 |
| SAC | 1,259 | 1,055 | 68 | Quality-top | 828 / 82 / 26 | 843 / 96 / 28 | 913 / 25 / 7 | 906 / 142 / 49 |

For quality-top, J0 improves correct retention against both controls in every
NBA game while accepting no more wrong points or hidden frames. Its paired
correct gains versus Q0 are 93 in CHI, 88 in DEN, and 85 in SAC, with zero
correct losses. Against S0 the gains are 76, 43, and 70, again with zero losses.
Those are actual point-by-point preservation results, not just offsetting
aggregate changes.

The error improvements still contain individual exceptions. Relative to Q0,
CHI quality-top newly rejects 13 wrong choices but newly accepts five others;
it rejects both previously emitted hidden frames but emits one different
hidden frame. SAC newly rejects 58 wrong choices and accepts one new wrong
choice; it rejects 19 previously emitted hidden frames and adds none. DEN
keeps zero wrong and hidden quality-top choices under both Q0 and J0. The paired
rows preserve these details, so lower totals are not described as eliminating
all new errors.

Native correct retention also improves in every NBA game and loses no
Q0- or S0-kept correct point. Nevertheless, CHI adds three wrong and two hidden
native choices. These fail four of the 36 NBA comparisons: wrong and hidden
against both Q0 and S0. DEN and SAC native choices have no known eligible-miss
or certain-hidden candidate points in this fixed native view; their zero-error
curves cannot establish general discrimination against those absent cases.

Only after these source results are examined are the pooled NBA totals useful:

| Policy, 3,179 total / 2,811 eligible / 128 certain-hidden frames | Q0 | S0 | J0 | M0 |
|---|---|---|---|---|
| Native | 2,309 / 0 / 0 | 2,403 / 0 / 0 | 2,806 / 3 / 2 | 2,531 / 1 / 0 |
| Quality-top | 2,275 / 99 / 28 | 2,352 / 125 / 30 | 2,541 / 34 / 8 | 2,532 / 266 / 80 |

J0 quality-top retains 90.39% of all 2,811 eligible frames. Its original fixed
choice ceiling is 2,542/2,811, or 90.43%, so only one more correct point could be
recovered by changing acceptance while keeping that ranking. Rejection alone
cannot reach the unchanged 95% tracker requirement. Native retains
2,806/2,811 correct at J0 but still emits hidden frames and has unresolved
cross-source preservation. Neither policy has passed the full tracker gate.
M0's high quality-top acceptance is not evidence of a useful zero cutoff: a
unique highest-quality point normally beats its competitors by construction.
Across NBA quality-top pairs, J0 newly rejects 71 wrong choices and newly
accepts six, and newly rejects 21 hidden choices while accepting one new one.
It adds 266 correct choices with zero Q0-kept correct losses; native adds 497
correct choices with zero such losses.

**HOU is a real regression veto.** HOU has 960 frames, including 882 eligible,
34 certain-hidden, and 44 other unknown/nonlocalizable reference frames.

| HOU fixed policy | Q0 | S0 | J0 | M0 |
|---|---|---|---|---|
| Native | 798 / 0 / 0 | 807 / 0 / 0 | 841 / 18 / 18 | 830 / 0 / 13 |
| Quality-top | 825 / 6 / 3 | 834 / 7 / 4 | 855 / 4 / 14 | 862 / 20 / 34 |

J0 preserves all 798 Q0-kept correct HOU native points and adds 43, but admits
18 wrong and 18 hidden native choices. Quality-top adds 35 correct choices
while losing five Q0-kept correct choices, for the net gain of 30 shown above.
It rejects three previously accepted wrong choices and accepts one new wrong
choice; it rejects two previously emitted hidden frames and adds 13 new ones.
The resulting hidden count of 14 exceeds both Q0's three and S0's four. All
four HOU policy/comparator hidden checks fail.

The protected quality-top losses are e01 frames 198, 199, 200, and 201, plus e05
frame 21. These include four of the ten e01 recoveries: only six of those ten
quality-top points remain accepted. The exact stress-probe protection is
separate: 738 of 745 Q0-positive, known-correct protected probes survive, and
seven fail. Those losses are e01 frames 196, 197, 198, and 200, plus e05 frames
14, 15, and 21. The ten exact e01 stress probes also retain only six. The
chosen-point and stress losses occur on different coordinates in some frames;
they must not be conflated.

The e05 six-frame below-.01 group has two Q0-positive correct stress probes
(frames 14 and 15), both rejected by J0. The useful e05 frame-206 quality-top
point remains accepted. The 17 incomplete original peak frames retain all 17
Q0-kept correct native points, all 17 quality-top points, and all 17 exact
correct stress probes in that view. All named groups, including the adverse
hidden and rank-regression groups, remain in the saved case views. Groups
overlap and their counts must not be summed. Other matching candidate
alternatives remain diagnostic rather than becoming a new unstated veto.

**The complete curves show information beyond a shifted cutoff.** All four
S slopes are positive, with no constant-score degeneracy. For every individual
game and fixed policy, Q and S have identical attainable
correct/wrong/hidden count triples across their full tied-score curves. S's
fixed-zero differences are score adjustment; it cannot explain J's different
tradeoff curves.

The following descriptive comparison uses every shared integer retained-correct
level. At each level, it takes the first reachable tied-score outcome that
retains at least that many correct points. Because adding accepted points cannot
reduce wrong or hidden counts, that outcome minimizes both error counts at the
retention floor. It never splits a tied group or invents an intermediate
outcome. “J improves” means fewer wrong or hidden emissions without increasing
the other; “Q/S improves” is the reverse. Equal means equal error counts at the
same retention floor. This is an annotated oracle comparison of saved curves,
not a threshold choice, new pass rule, or validation claim.

| Source and policy | Correct-retention levels | J improves | Q/S improves | Equal | Wrong/hidden tradeoff |
|---|---:|---:|---:|---:|---:|
| CHI native | 832 | 16 | 137 | 679 | 0 |
| CHI quality-top | 730 | 510 | 0 | 220 | 0 |
| DEN native | 920 | 0 | 0 | 920 | 0 |
| DEN quality-top | 899 | 85 | 0 | 814 | 0 |
| SAC native | 1,055 | 0 | 0 | 1,055 | 0 |
| SAC quality-top | 913 | 890 | 0 | 23 | 0 |
| HOU native | 842 | 23 | 0 | 811 | 8 |
| HOU quality-top | 862 | 124 | 0 | 718 | 20 |

For NBA quality-top, the J curve is no worse on either error count at any shared
retention floor and is better at many floors in every game. CHI improves at
levels 221–730, DEN at 815–899, and SAC at 24–913. At each source's full correct
choice ceiling, the reachable count triples are:

| Quality-top source | Q/S curve: correct / wrong / hidden | J curve: correct / wrong / hidden |
|---|---|---|
| CHI | 730 / 105 / 14 | 730 / 44 / 5 |
| DEN | 899 / 21 / 5 | 899 / 0 / 0 |
| SAC | 913 / 142 / 48 | 913 / 23 / 7 |

These endpoints are oracle potential, not the J0 results or proposed deployment
settings. The corresponding native picture is weaker: CHI's Q/S curve has fewer
errors at 137 retention levels, versus only 16 levels favoring J. For example,
at a floor of 656 correct native points, Q/S can retain 656 with zero wrong and
zero hidden, whereas J requires one wrong point. DEN/SAC native curves contain
no known wrong/hidden native choices and remain equal on these error measures.

HOU quality-top has genuine potential at intermediate retention levels: at the
Q0 retention floor of 825 correct, J's curve can retain 825 with zero wrong and
zero hidden, versus Q/S's 825 / 6 / 3. At 834 correct it permits 834 / 0 / 0,
versus Q/S's 834 / 7 / 4. But levels 843–862 trade fewer wrong points for more
hidden frames; at the full ceiling J is 862 / 12 / 27 versus Q/S's
862 / 14 / 22. HOU native also has eight levels with an error tradeoff. Those
curves do not license selecting a HOU cutoff or overriding its protected
point losses.

**Secondary NFHS checks also remain source-specific.** The same fixed-zero
count convention applies. Possession 001 has 75 frames, 74 eligible and one
hidden; possession 002 has 50 frames, 31 eligible, 18 hidden and one masked;
possession 003 has 25 eligible frames.

| NFHS source | Policy | Q0 | S0 | J0 | M0 |
|---|---|---|---|---|---|
| Possession 001 | Native | 33 / 0 / 0 | 35 / 0 / 0 | 74 / 0 / 0 | 50 / 0 / 0 |
| Possession 001 | Quality-top | 37 / 0 / 0 | 37 / 0 / 0 | 68 / 0 / 0 | 52 / 6 / 1 |
| Possession 002 | Native | 11 / 0 / 0 | 13 / 0 / 0 | 31 / 0 / 0 | 23 / 0 / 0 |
| Possession 002 | Quality-top | 12 / 0 / 0 | 14 / 0 / 0 | 23 / 1 / 0 | 23 / 8 / 14 |
| Possession 003 | Native | 15 / 0 / 0 | 18 / 0 / 0 | 25 / 0 / 0 | 23 / 0 / 0 |
| Possession 003 | Quality-top | 17 / 0 / 0 | 18 / 0 / 0 | 24 / 1 / 0 | 23 / 1 / 0 |

All three native views improve retention without observed wrong/hidden
emissions. Quality-top adds a wrong choice in possessions 002 and 003. Its
complete curves improve over Q/S at 29 of 68 retention levels in possession
001 and seven of 23 in possession 002, with no reverse levels there.
Possession 003 has one reverse level, at 20 correct, and 23 equal levels.
These small secondary views do not repair the failed NBA/HOU requirements.

The 60 historical rows retain their original four semantic roles. Their
positive-score counts are diagnostics, not geometric accuracy:

| Historical role | Rows | Q positive | S positive | J positive | M positive |
|---|---:|---:|---:|---:|---:|
| Exposed regression | 34 | 18 | 19 | 16 | 18 |
| Reference bank | 10 | 6 | 6 | 6 | 6 |
| Resolved check | 10 | 4 | 4 | 4 | 4 |
| Unresolved audit | 6 | 0 | 0 | 0 | 0 |

The accepted historical balls at `sas_det_q1_c02:11008:mean:1` and
`sas_det_q1_c02:11107:mean:1` remain negative under J, as under Q. The six
unresolved rows remain unresolved. No semantic label is promoted into a new
geometric target, no protected source is reopened, and no historical row
chooses a threshold. Historical pool unavailability and the stress probes'
unavailable component metadata remain explicitly out of the fitting schema.

**Interpretation and next design recommendation.** The predeclared overall
fixed-reference criterion is false. The measured branch is useful added
discrimination with an unresolved operating point and policy/source-dependent
preservation failures. It is not “only score adjustment helps”: Q and S have
the same per-source attainable curves while J substantially separates the
quality-top cases. It is also not a general presence detector or a completed
tracker. The actual target remains coordinate usefulness, and the observed
features alone do not establish semantic ball presence.

The next design should retain the successful quality-top discrimination as a
baseline and explicitly address preservation and hidden-frame rejection across
native and weak/recovery contexts. A bounded follow-up should specify its
training-source balance, policy-conditioned error accounting, and how missing
component/pool schema cases are handled before execution. It should test
whether the gate is learning transferable evidence of a useful point rather
than relying on candidate-origin shortcuts. The existing CPU failure study's
narrow native-negative/hidden training support is relevant context; this run
does not isolate the causal feature or prove a particular repair will work.

Any score-to-abstention calibration must be developed within honest training
source splits and then evaluated once on held sources. HOU should remain a
locked preservation veto, with the exact e01/e05 losses visible; it must not be
used to choose weights, features, cutoff, or case-specific exceptions. If
training-supported balancing and schema handling cannot separate valid native
points from hidden/wrong ones, a separately designed wider image-context or
frame-answerability objective is the next question. No such modification,
ablation, calibration run, image fit, or additional experiment is authorized or
executed by this recommendation.

Ranking failures remain a separate problem. The quality-top ceiling is still
below 95%, and the native view's stronger eligible ceiling does not remove its
hidden/preservation failures. The original >=95% correct, <=1% wrong,
zero-hidden, temporal/recovery, and human trajectory requirements remain
unchanged. Existing training-size differences across the nested quality bases,
the exposed nature of HOU, small NFHS samples, and out-of-schema stress/history
inputs limit generalization claims. Frame counts are descriptive observations,
not independent trial counts or confidence guarantees.

**Saved evidence.** Paths below are relative to the repository and point to
actual retained files. Exact byte lengths and SHA-256 bindings for this report's
source evidence are in
`data/outputs/ball_tracking/candidate_acceptance_gate_v0_1/implementation_review/scientific_interpretation_bindings_v2.json`.

- Design: `docs/ball_tracking_candidate_acceptance_gate_protocol.md` and
  `configs/ball_tracking/proposals/candidate_acceptance_gate_v0_1.json`.
- Main results: `attempt_001/analysis/completed.json`, `summary.json`,
  `decision.json`, `policy_zero_tables.jsonl`, `policy_curves.jsonl`,
  `paired_policy_rows.jsonl`, `frame_registry.jsonl`, `candidate_scores.jsonl`,
  `missingness.json`, `historical_rows.jsonl`, and `fits/*.json`, all beneath
  `data/outputs/ball_tracking/candidate_acceptance_gate_v0_1/`.
- Preserved populations: analysis `source_choices.jsonl`, `contrast_views.jsonl`,
  `candidate_zero_tables.jsonl`, `candidate_curves.jsonl`, and
  `preserved_controls_and_cases.json` under the same attempt.
- Independent verification: `implementation_review/analysis_output_audit.json`,
  `implementation_review/neural_output_audit.json`, and
  `postrun_tensor_audit/attempt_001.json` under the experiment directory.
- Execution: `launch_v0_1/launcher_finished.json`, neural `completed.json`,
  `implementation_review/readiness_correction_review.json`,
  `implementation_preparation/focused_tests_final.json`,
  `implementation_review/supervision_review.json`, and
  `implementation_review/readiness_correction_tests.json`.
- Independent interpretation: `implementation_review/interpretation_plan.json`,
  `interpret_analysis.py`, and `scientific_interpretation_receipt.json` retain
  the method, exact source tables, paired changes, complete retention-floor
  comparison ranges, named HOU losses, and historical-role counts.
