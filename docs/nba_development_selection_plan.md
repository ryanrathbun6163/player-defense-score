# NBA source selection and proposed development split

## Approval recorded October 18, 2026

Ryan replied, “Yes I approve. Move forward chat,” to the concrete allocation and
120-frame pilot. The [approval record](../configs/ball_tracking/reviews/nba_development_selection_approval_v0_1.json)
binds the unchanged proposal and exact two intervals. This approves the selected
source use, game roles and annotation pilot, including the native-timestamp
workflow needed to prepare it. Training/evaluation, completed label review,
player identity, matchup responsibility and court calibration are not implied.
The proposal below remains preserved as the pre-approval record.

## Original proposal

Prepared October 18, 2026, America/Phoenix, from clean branch `codex/ball-detector-baseline` at `cd8defc3d08a5e54a05db15e1ed64b6ef93a65b6`.

## Result and decision

Six source-only review clips are prepared and inspected. The best first pair is **Sacramento's opening live-action episode** and a **partial Detroit half-court action involving the apparent Cunningham/Castle matchup**. Neither has human selection approval yet. The Detroit opening inbound is not shown, so this is a ball-development action window, not a certified complete possession or defensive-scoring example.

The [machine-readable proposal](../configs/ball_tracking/selections/nba_development_selection_proposal_v0_1.json) is explicitly **non-runnable and pending Ryan's decision**. It proposes game-level roles and a small, prediction-free annotation-protocol pilot: 60 consecutive native source frames from each primary candidate, 120 frames total. No ball labels, model predictions, evaluations or training were created or run. A timestamp-aware annotation path must be implemented and checked before those labels are placed.

The concrete decision is whether to adopt the roles below and this two-clip, 120-frame pilot. It does not authorize a fit, threshold search, new ball-model comparison or release of a test set. [AGENTS.md](../AGENTS.md) requires bringing “substantial scientific, architectural, evidence-integrity, safety, or cost tradeoffs” to Ryan. The new data allocation and annotation scope are the scientific decision here; routine clip preparation and verification are complete.

## Proposed game roles

| Game | Proposed role | Consequence |
| --- | --- | --- |
| Spurs–Pistons, February 23 (`0022500828`) | Target-case development | Inspect and diagnose the chosen case; do not fit on its labels if this allocation is adopted. |
| Kings–Grizzlies, February 23 (`0022500829`) | Future training candidate pool | Prepare training examples only after source/label review; no training recipe is approved here. |
| Spurs–Raptors, February 25 (`0022500843`) | Additional development | Available for later cross-game checks; no new clips or labels selected in this increment. |
| A separate, not-yet-designated game | Future independent test | Reserve before model-driven inspection and define release rules before final evaluation. No such test set currently exists. |

All three acquired games are already development-visible. The proposal does not relabel one as untouched. Keeping training and target development games separate prevents adjacent views of the same play from appearing on both sides. Keep each underlying event, replay, neighboring temporal context, alternate crop and duplicate encoding in the same role. A new clip hash does not erase its parent-game identity. Do not randomly split individual video frames.

One inspected training game and one target development game provide a small starting point, not NBA-wide performance evidence. A later change that uses target-game examples for fitting must explicitly revise this allocation and the resulting claim. No independent benchmark is established by this curated convenience sample.

## Review the primary pair

Both videos are muted, full-resolution H.264 review derivatives. Their frame inventory and measured timestamps match the selected source frames, but their pixels are lossy; they are **not the annotation authority**. Label from original source frames or a separately verified lossless derivative. The original audio and recordings remain intact.

| Candidate | Review video | Proposed action window in original source | What needs review |
| --- | --- | --- | --- |
| `sac_mem_q1_c01` | [45-second opening review](../data/outputs/t/nba_possession_selection_2026-10-18/sac_mem_q1_c01/source_review.mp4) | Source frames **540–2010**, **9.068689–33.592689 s** inclusive; about video 0:09–0:34 | Pre-tip through Sacramento control, attack, made basket and Memphis inbound. Promising complete opening episode; confirm the chosen context and final frame. |
| `sas_det_q1_c02` | [38-second Detroit review](../data/outputs/t/nba_possession_selection_2026-10-18/sas_det_q1_c02/source_review.mp4) | Source frames **10668–11898**, **178.020689–198.540689 s** inclusive; about video 0:14–0:35 | Partial possession: wide-view attack, attempt, offensive rebound and stoppage. Inbound/start remains unseen. Confirm useful ball visibility and the proposed context. |

The official starting lineup/substitution record supports provisional Cunningham/Castle co-presence. Jersey 2 and jersey 5 are visible in the Detroit action, with screens, help and overlap. This does not assign sole defensive responsibility or complete roster-identity reconciliation. Ryan's identity and later calibration gates remain intact.

The proposed 60-frame blocks use a simple source-only rule: start at the first available source timestamp at least two seconds after each proposed action-window start, then retain 60 consecutive frames. They are protocol pilots, not representative performance samples or complete trajectories.

| Proposed label purpose | Original source frames, inclusive | Original source PTS, seconds | Frames |
| --- | --- | --- | ---: |
| Sacramento future-training-eligible pilot | **660–719** | **11.070689–12.054689** | 60 |
| Detroit development-only pilot | **10788–10847** | **180.022689–181.006689** | 60 |

These blocks are only proposed intervals. No annotation JSON, point, visibility category, difficulty label or reviewed truth has been manufactured. Sixty encoded frames cover approximately one second; the first-to-last timestamp span is about 0.984 seconds. Later full-episode trajectory review remains necessary, and a 120-frame pilot is not enough to justify a new training result or phase gate.

## All six candidates, including limitations

Search brackets below are half-open source-time intervals. They deliberately include context and can contain more than one team's action; they are not accepted possession boundaries.

| Candidate | Search bracket | Source-only finding and disposition |
| --- | ---: | --- |
| SAS–DET Q1 C01 | 128–146 s | Detroit transition attempt is visible, but camera changes occur during the attack. Retain as a multi-view challenge; do not use as the first single-camera player-pipeline baseline. An interview inset appears during following Spurs action. |
| SAS–DET Q1 C02 | 164–202 s | Best target development window. Closeups hide the Detroit start; wide action is visible in the proposed core. Keep its partial-possession designation. |
| SAS–DET Q1 C03 | 314–341 s | Closeup hides the Detroit restart; an interview inset and closer basket camera affect the attack. Retain for later overlay/cut handling, outside the primary pilot. |
| SAC–MEM Q1 C01 | 0–45 s | Best proposed training-source episode. Trim proposal excludes pregame closeups and the following partial Memphis possession. Human full-episode acceptance remains pending. |
| SAC–MEM Q2 C02 | 1215–1255 s | START 2ND graphic/dissolve hides the beginning; Memphis already controls the ball when court view returns. Retain as a partial-start example, outside the primary pilot. |
| SAC–MEM Q3 C03 | 2715–2755 s | Prefix contains replay/closeup/wipe; a large logo partly obscures the live inbound. Miss/block and rebound are visible later. Retain the obscured-start qualification, outside the primary pilot. |

No rejected or limited candidate was silently replaced. Ordinary overlap, blur and hidden-ball intervals are valid annotation conditions, not reasons to delete hard frames. Missing broadcast action, replay chronology and camera changes need explicit treatment. The chosen game's previously documented Q4 opening gap remains unresolved.

Inspection used every saved half-second contact panel, selected full-resolution frames, and priorities from adjacent-frame grayscale changes. It did not watch every frame in real time; short edits can escape sampled inspection. A difference peak is not automatically a camera cut. Official game clocks locate candidate plays but do not replace source PTS: visible clocks and official event times differ by several seconds in some samples. No interpolation was used to invent exact possession boundaries.

## Timing and implementation boundary

Preserve original encoded frames and their actual presentation timestamps. The footage is nominally 60000/1001 fps, with measured timestamp quantization; nominal rate, average rate and original camera cadence are different facts. There is no silent 25 fps conversion in these review clips.

The local contract inspection found specific incompatibilities with reusing old helpers unchanged:

- The base annotation schema accepts variable window lengths and positive fps, but fixes timestamps to `frame_index / fps`. That is not the measured NBA PTS list.
- Several neutral/label review helpers require 25 frames. Twenty-five frames represent about 0.417 seconds here, rather than one second at 25 fps.
- Old experiment/evaluation joins assume one source-video hash per possession. Multiple NBA episodes must retain distinct clip identity **and** their shared original game/frame mappings.
- The current editor can retain a whole selected RGB window in memory. Twenty seconds of native 1080p video approaches 7.5 GB before overhead; use bounded/on-demand loading for the new path.
- Three consecutive native NBA frames have different temporal spacing from the old 25 fps WASB triplets. Preserving source cadence does not choose a model-input cadence or approve reusing old frame-based motion/gap settings.

The next implementation should add a separate, versioned NBA annotation/source-mapping path, verify actual producer-to-consumer frame/PTS transport, and prepare genuinely unlabeled records for the approved pilot. Preserve the frozen NFHS tools and schemas. Keep source-faithful pixel geometry, explicit uncertainty, reviewed hidden negatives and indeterminate/unscored states. A model-specific temporal recipe and any later training/evaluation must be specified separately.

## Verification, resources and preserved history

The six clips contain **12,466 source-mapped frames**, with **422 full-resolution sampled JPEGs** and **21 contact sheets**. The review videos total **298,291,786 bytes**. Every selected original PTS maps exactly to its derivative presentation PTS on a 90 kHz time base. All six derivative frame counts and final frames were decoded; logs were empty. An independent audit checked packet/frame/image mappings, source references, sizes and hashes without another media decode. It found no material mismatch.

Two parallel preparation lanes used four encoder threads each. Extraction plus verification took 128.344 seconds for the three Detroit clips and 181.547 seconds for the three Sacramento clips; these concurrent lane times should not be added as wall-clock elapsed time. There was no network media transfer, repeat full-game decode or repeat full-source hash pass. Saved completed source audits plus unchanged source size/mtime bound this continued use.

One preflight failed before media reading or clip creation because the chosen-game audit uses `full_file_sha256`/`target_stat_after`, while the newer audit uses `sha256`/`source_stat_after`. The failed helper and failure record remain preserved. The corrected helper explicitly consumes each actual producer format. This correction did not rerun an earlier experiment or a completed scientific review.

A separate visual-note writer initially assumed the frame-map record contained floating-point seconds; it actually stores integer PTS ticks. That pre-output failure is also retained. The corrected writer uses integer ticks for timing bindings and the image manifest's seconds for displayed anchors. It created no new media or labels.

Local evidence is under `data/outputs/t/nba_possession_selection_2026-10-18/`: per-candidate receipts, source/frame mappings, metadata, clips and images; `contracts/preparation_audit.json`; contract notes; and source-selection visual notes. Generated media stays ignored. The committed proposal binds the supporting evidence. Focused proposal checks passed for 53 supporting-file bindings, two prior access records, six candidates, both pilot intervals, eight new/changed local links and the five-file Git scope. The first verification command's unsupported multi-path `git check-ignore --quiet` invocation is preserved; checking each path separately succeeded. No pipeline code changed and no full scientific test suite was rerun.

The existing NFHS finish line—reviewed player/ball trajectories, explicit missingness, synchronized final-frame review and quantitative summaries across the three curated possessions—remains unchanged. The motion comparison stays complete and negative. Its **three new human reviews remain pending**; earlier completed reviews remain complete. NBA source preparation does not promote a method, accept a trajectory or complete the ball phase.
