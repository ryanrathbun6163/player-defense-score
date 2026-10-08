# Implementation recommendations after the sports-video research

Research date: 2026-10-08. These are recommendations based on inspected sources and existing project evidence. They are not new performance results or authorization to replace reviewed decisions. See [the research hub](README.md) for the full collection.

**Subsequent implementation:** the proposed first WASB comparison is now complete.
Read [the local transfer result](../ball_wasb_transfer_results.md) before acting on
the original recommendation below. Its published-threshold output is too sparse
to replace the existing RF control; do not repeat the completed inference to resume.

The subsequent [cached calibration](../ball_wasb_calibration_results.md) also
completed: it improves coverage but does not establish a replacement. The
[adaptation plan](../ball_wasb_adaptation_plan.md) now specifies the pilot-data
split and one small training preset; that training has not run.

## Main recommendation

**Test a released basketball-specific temporal image model, beginning with WASB, through a small adapter into our current evaluation pipeline.** Retain saved RF-DETR results as controls. Do not restart the generic RF-versus-YOLO comparison or replace the reviewed player pipeline.

The reason is specific to our evidence: saved RF crops already contain candidates within the reviewed geometric tolerance on most eligible development frames, while selection still follows wrong objects and emits during occlusion. Geometric proximity alone does not confirm physical ball identity. Motion and player proximity have already been explored. WASB adds learned visual information across frames and has a basketball-specific model resource. It could improve discrimination, but that remains a hypothesis until a local comparison answers it. [WASB official project](https://github.com/nttcom/WASB-SBDT), [our ball review](ball_tracking_research.md), [our completed result](../ball_crop_cross_detector_corroboration_results.md).

## Decisions this research supports

| Choice | Recommendation | Evidence and limitation |
| --- | --- | --- |
| RF/YOLO box-agreement rule | Retire this tested rule | All six development windows regress; no wrong/hidden suppression; this does not rank all detector families |
| Saved RF crop observations | Preserve as baseline/control | Strong candidate availability; imperfect final selection; already computed |
| WASB basketball checkpoint | First new ball representation to evaluate | Basketball benchmark and released model link; old environment and different metric/visibility assumptions |
| TrackNet-derived newer models | Compare selectively if WASB exposes a relevant limitation | Tennis/shuttle/blur/occlusion work is informative, but weights, terms and target definitions vary |
| Basketball fine-tuning | Next if transfer errors justify it | Directly changes visual discrimination; needs independent training data and a checkpoint-selection rule |
| Learned RF candidate verifier | Alternative if proposals remain good | Can target shoe/hand/background confusion; requires candidate labels beyond winner-only examples |
| SAM/point tracking | Assisted annotation or targeted later comparison | Useful propagation; initialization and tiny-object reacquisition are separate problems |
| Player association replacement | Defer until a measured player failure requires it | Existing three-possession foundation is reviewed; modern alternatives are reference options |
| SoccerNet/TrackLab | Borrow modular design and evaluation ideas | Source-inspected reconstruction stack; soccer geometry and athlete scope differ |
| SkillCorner basketball open data | Borrow consumer schemas and analytics examples | Explicit position states/uncertainty/event structures; proprietary estimates are not our ground truth |
| VLM event reasoning | Later, evidence-linked assistance | Can propose semantic events; does not establish metric coordinates or defensive credit |
| New orchestration platform | Defer wholesale migration | Existing provenance is extensive; simpler stage boundaries may solve the actual friction |

No numeric ranking score is assigned to these options: a fabricated weighted total would obscure uncertainty about local accuracy, integration effort and licensing.

## The next comparison, made concrete

This is a proposed implementation outline, not a new mandatory recovery proposal or certificate process.

1. **Obtain the exact basketball checkpoint and pin the inspected code.** Confirm actual weight access and component terms; record its digest once downloaded. Use an isolated dependency environment or a narrowly adapted inference path so the reviewed player environment stays usable.
2. **Adapt inference, not the entire upstream dataset system.** Decode our existing source frames, reproduce required image transforms and temporal input order, and emit source-coordinate points/heatmap candidates with scores and explicit missing states. Bind each output to its target frame. Keep the raw model output separate from selection/interpolation.
3. **Check the real boundary once before expanding.** Pass one actual model output through our actual consumer. Check color order, scaling, channel/frame order, finite values, temporal target alignment, empty output and first/last-frame behavior. Correct ordinary compatibility/path errors and continue.
4. **Run a small transfer comparison using existing development labels and saved controls.** Compare raw observation quality and final selection separately. Preserve representative/challenge splits and existing radius definitions. Do not count temporal context outside a scored window as additional labeled evaluation data.
5. **Read the paired outcome table and inspect the important episodes.** Did it recover correct observations, lose correct ones, follow different distractors, emit on hidden frames, or reacquire more reliably? Review full synchronized clips through their final frames when a trajectory change is proposed.
6. **Make one decision.** If clearly useful, integrate and extend coverage. If mixed, diagnose the specific remaining error and consider fine-tuning. If worse, retain the negative result and move to the next materially different option. Do not open a huge parameter grid by default.

The existing six windows are a cheap transfer/regression diagnostic, not a clean generalization test. New development episodes should add the missing kinds of evidence—especially independent occlusion/reacquisition episodes and longer trajectories. The held-out data still serve their declared role after a method/operating point is chosen. Exact data expansion and acceptance thresholds are consequential project choices; routine adapter repairs are not.

WASB's upstream evaluation cannot simply replace ours. In the inspected evaluator, a wrong visible localization is recorded as FP1; its recall denominator is TP+FN, excluding FP1. Its basketball loader also has assumptions about contiguous local frame indices and annotation visibility. Use the existing reviewed target definition and a deliberate adapter rather than importing external counts as though they meant matched/eligible here. Details and source links are in [the ball chapter](ball_tracking_research.md).

A temporal model's future-frame access, window stride and boundary padding must be stated. This project analyzes saved clips, so offline context may be useful; it should not be advertised as strictly live/causal. Neighboring context must not cross a sealed evaluation boundary or a camera cut unnoticed.

## How this differs from what we have already done

| Existing work | Useful lesson | What the new step adds |
| --- | --- | --- |
| Whole-frame then crop RF detection | More image detail can improve available centers | A basketball temporal representation, not just another crop grid |
| Confidence and top-one controls | Candidate presence and chosen output differ | A new image-based score/heatmap whose errors can be compared |
| Recent-history graph and motion factorial | Motion allowance/cost affect selection; clutter can persist | Learned appearance plus temporal pixels rather than the same boxes alone |
| Soft player-box context | Some distant distractors become less attractive | Evidence for nearby lookalikes; proximity alone cannot separate shoes/hands from balls |
| Human/AI selected-frame review | Identity error and center offset are distinct | A preserved failure taxonomy for interpreting the new method |
| Generic YOLO and agreement | This challenger/filter did not help | A reason to stop that rule, not a reason to abandon all ball tracking |

More temporal context is not automatically better. A model or smoother can continue a wrong object confidently. The hypothesis is that relevant training and temporal visual evidence reduce those errors; the evaluation must still test that claim.

## Reuse from other projects, with boundaries

**SoccerNet/TrackLab:** take the idea of explicit modules, cached intermediate state and joint identity/position evaluation. Avoid a framework migration during the ball correction unless a concrete integration saving justifies it. Its full reconstruction task is athlete-centered and soccer-specific. [Project and inspected configuration](https://github.com/SoccerNet/sn-gamestate).

**Public NBA prototypes:** borrow explicit observed/interpolated/missing states, candidate extraction patterns and useful visualizations. Their Viterbi/proximity/event rules are implementation references; coverage and attractive videos do not establish ball accuracy. The detailed source review found documentation drift and geometry shortcuts worth avoiding. [NBA prototype](https://github.com/cyrushadavi1/nba_video_analysis_v2), [project comparison](sports_projects_and_analytics.md).

**DeepSport/DeepSportradar:** borrow basketball task decomposition and independent geometry/identity evaluation. Oracle-centered ball crops and calibrated arena inputs answer different questions from finding a ball in an edited broadcast. [DeepSportradar](https://arxiv.org/abs/2208.08190).

**SkillCorner basketball data:** study the separation of detected/extrapolated positions, visibility, uncertainty and event provenance. Use open samples to explore downstream consumers without waiting for perfect custom tracking. Keep any such analysis explicitly based on vendor-generated data; it cannot validate our reconstruction. [Official open basketball data](https://github.com/SkillCorner/opendata-basketball).

## Finish the phase with a usable increment

The ball phase should not silently expand into complete-game identity, 3D reconstruction, event understanding and causal defensive value. A credible near-term increment is a selected ball method, reviewed trajectories for the three curated possessions, synchronized player/ball playback, explicit missing intervals, quantitative error summaries and a repeatable configuration-driven run.

If human corrections are needed to make the curated examples useful, record them as reviewed corrections and measure the correction burden. A human-assisted foundation can be a valid project deliverable if Ryan chooses that scope; it must not be presented as fully automatic performance. This is an explicit product/scientific tradeoff to discuss, not a reason to fabricate uninterrupted tracks or to keep improving a demo indefinitely.

After that increment, move to possession/event understanding with separate labels. Do not define possession solely as the nearest player in the image. Then add roster evidence, matchup transitions and a transparent defensive attribution design. Three possessions can demonstrate the pipeline and its reasoning; they cannot train or validate a broadly general defensive-value model.

The research supports a staged architecture and a stronger next candidate. It does not yet establish that WASB improves our ball tracking, that the entire system is production-ready, or that a final defensive score is valid.

## Operational changes that should reduce wasted effort

- Keep expensive inference outputs reusable. Regenerate derived reports from saved results when report delivery fails.
- Use one compact result table with denominators and paired changes before generating large review packages.
- Validate the actual producer/consumer boundary rather than writing many fixtures around assumptions.
- Run focused tests on local changes; use the full suite when risk warrants it. Research documents need document checks, not another scientific run.
- Add a source note when a new reference changes an implementation choice. Do not repeat a survey or completed human review merely to resume.
- Integrate completed increments under the existing Git authorization boundaries; a broader research phase should not keep useful code isolated indefinitely.

These recommendations follow Ryan's current standing policy. They preserve real evidence, failed attempts and human review while removing routine procedural friction.

## What would change this recommendation

WASB would lose first priority if its actual checkpoint cannot be obtained/used, its adapter requires disproportionate work, or its correctly aligned local outputs show no useful advantage. A newer ball model would move ahead if it provides relevant basketball evidence, accessible compatible weights, clear output/visibility semantics and a practical implementation. A learned verifier would move ahead if new labels demonstrate strong existing proposal coverage with systematic, learnable distractor errors.

A different player tracker or camera model becomes urgent only when a measured error in that layer blocks the next deliverable. A new infrastructure tool becomes worthwhile when its maintenance saving exceeds its migration burden. None of these decisions should be based on repository stars, the newest model name, or a benchmark percentage with different definitions.
