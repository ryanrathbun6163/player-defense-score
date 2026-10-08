# RF and YOLO ball comparison release proposal

This proposal connects the tested detector agreement rule to six saved development clips. The result will show which wrong detections disappear, which correct ball sightings are lost, and whether lower ranked ball candidates become usable. Six synchronized videos will let Ryan inspect the same decisions visually.

The rule and its evaluation and rendering functions are already implemented. They passed 63 focused tests and a full suite with 1,166 passes and one existing Windows skip. Those results establish behavior on artificial data. The real comparison remains unperformed, so no improvement in tracking accuracy is claimed.

## Concrete progress and remaining work

The exact input inventory is now complete: 190 files covering 150 frames. Their expected hashes come from existing administrative records; present sizes and filesystem identity come from metadata. Scientific bodies, images and the resource journal stay closed during proposal preparation.

The remaining application work is two new files: `src/ball_tracking/crop_cross_detector_corroboration_release.py` and its matching test module. The eight tested Stage 1 files stay unchanged. The new module will supply verified file access, owned execution, output publication and release checks around the existing selector, evaluator and renderer. The existing artificial entry point stays disabled for real execution.

The companion JSON names every input and output, each input's authority and permitted phase, and each output's size ceiling. It is a proposed scope, not an executable release or approval record.

## The fixed scientific question

On each frame, consider every already exported sports-ball candidate from RF-DETR and YOLO at confidence at least .01. Support requires source-space box intersection-over-union at least .50. Select the supported RF candidate with greatest original RF confidence, breaking exact ties by its original index. Emit its unchanged box, center and confidence, or emit no accepted observation when none is supported. There is no temporal state, fusion, interpolation, additional candidate cap or tuning.

Compare with the saved RF top-one result as the primary control. Saved TT and mean-confidence results are descriptive controls. Evaluate only the new selections at the existing .01 threshold and ten-source-pixel center radius. Keep representative and challenge pools separate and disclose every window's result. The five hidden frames remain separate from the 145 localization-eligible frames.

The fixed favorable-development classification requires no lost baseline matches in any window, no increased wrong detections or hidden alarms in any window, no new hidden-alarm frames, and at least one match gain or error/alarm reduction somewhere. Suppressing an error is useful but does not itself improve localization. Detector agreement does not certify object identity. A successful completed run may report an unfavorable result; it never automatically selects a method or production quality gate.

## Exact evidence access

| Phase | Files | Purpose |
| --- | ---: | --- |
| Selection | 12 | Six RF and six YOLO saved candidate files |
| Evaluation | 28 | Six labels, eighteen saved observation files and four scoring pools |
| Review rendering | 150 | The existing source PNGs for the same six windows |

All six new selections must be published, verified and sealed before labels, saved observations or scoring pools become accessible. Source PNGs become accessible only after evaluation is complete. Selection sees source metadata but never labels, saved scores or pixels. Embedded provenance paths remain inert.

The twelve older top-one and TT reports have existing exact content hashes and JSON pointers. Mean observations and mean scoring pools have exact whole-file hashes but no separately published inner digests in the allowed records. The owned worker will verify those whole-file hashes first, extract only the six declared mean report pointers, verify their expected identities and provenance, and derive inner digests after selection is sealed. Preparation must not open those bodies to manufacture new digest records.

Both original motion scoring pools remain necessary: the mean pools contain mean reports and references to older reports, not copies of their bodies. Whole pool files may be parsed only to extract the eighteen total declared reports; unrelated reports have no analytical role. No historical selector or evaluator runs again.

YOLO recovery files distinguish assembly code from the actual inference commits that produced their candidates. Preserve that provenance and the embedded inference inventory. Do not relabel all detections with the assembly commit. Pure adapters may translate the already saved candidate formats without inference, reordering or dropping candidates.

## Execution and outputs

A new study-specific release module will call the unchanged responsive monitor and its ownership primitives. It must not call the old mean study's launch, history or worker entry points, whose authority binds a different experiment. It must not route real data through `run_synthetic_comparison` or weaken its artificial restrictions.

The owned worker performs twelve verified candidate reads, six new selections, a complete selection seal, approved saved-evidence reads and six evaluations of the new arm. It then renders six 25-frame videos at five frames per second. Each video shows unmarked source, saved RF top-one and the new corroborated result. Native overlays preserve the source scale; changed decisions and lost correct choices are indexed explicitly. Every final frame is included.

Exactly 342 published files are proposed: six selections with linear candidate audits, six window evaluations containing the new report and unchanged copies of all three saved control reports, two pool comparisons, 300 native overlays, six videos, twelve first/last composites, six review indexes, and four freeze/provenance/summary files. All names and individual limits are enumerated in the JSON. The directory is new and create-only; incomplete outputs and failed evidence are retained but cannot be adopted as successful results.

Stream images and video temporaries instead of loading the media inventory into memory. Bound the entire parent return to 512 KiB and the worker receipt to 1 MiB. The parent may receive verified artifact bindings, compact scientific counts/frame lists and review paths. Full candidate audits, copied reports and media stay in the declared outputs. Exceeding a limit fails the attempt; no candidate, frame or report truncation is permitted.

## Resource limits and consumed history

The proposed real comparison is one distinct attempt, at most 1,200 charged seconds, and at most 4 GiB of additional outputs and temporaries within the existing 32 GiB root cap. Keep the existing 8 GiB sampled combined-memory policy, at least 50 GiB free disk, responsive safety polling and complete final accounting. These are ceilings, not runtime promises. There is no automatic scientific retry or fallback.

The administrative history remains 3,330 events and 63 closed attempts, including four historical failures. Scientific time consumed remains 3547.523999999985 seconds, leaving 10852.476000000015 of 14,400. All prior attempts stay consumed.

The unchanged monitor necessarily validates the administrative budget journal when launching. A future execution approval must explicitly allow that budget and reservation verification in the owned supervisor and worker. It is distinct from replaying a scientific experiment. Preparation does not read the journal. The new reservation must verify the exact preserved prefix and reject a consumed unit, an unexplained suffix or an orphaned attempt before admitting work.

For the remaining release implementation, propose a separate 4,200-second artificial-validation allowance: focused invocation at most 600 seconds, full invocation at most 3,600, corrections included. Preserve both prior consumed balances: 2164.2970000000005 seconds from the earlier work and 2295.467999999999 seconds from Stage 1. Unused time does not renew old authority. Keep 8 GiB sampled memory, 50 GiB free disk and 4 GiB of validation outputs and temporaries, including fixtures outside the temporary directory.

The next full suite is justified by the new file-access and release code. Reuse completed selector tests and monitor design evidence; do not repeat monitor benchmark experiments. Tests should target allowed paths and phases, real saved formats represented by artificial files, frozen selections, immutable controls, output completeness, bounded transport, owned-worker checks, consumed-attempt refusal and dirty/uncommitted checkpoint refusal.

## Approval and Git boundaries

Current authority covers preparation of this proposal and its companion scope. It does not grant scientific body access, real execution, a release checkpoint or Git mutations.

The immediate requested next scope is the two-file release implementation, independent review and the new bounded artificial validation. Administrative evidence belongs in a fresh ignored `data/outputs/t/corroboration_release_validation_b71c64d3fd46/` directory. No production approval or clean-commit receipt may be fabricated from implementation permission.

Real execution additionally requires explicit approval of this exact input/access/output scope, the administrative history checks, and presentation of the newly verified review media. Only then may the exact runtime manifest and execution approval receipt be created. A tested source certificate must bind the frozen scope and validated source files; the later release receipt must additionally bind the actual manifest, execution approval and clean implementation commit. Unknown future commit/hash fields remain unavailable, never invented.

Staging and committing each require Ryan's explicit authorization, with the exact branch, HEAD, status and file scope reported before each mutation. The clean checkpoint must preserve all sixteen current dirty files and their bytes, including the original six-file handoff. Do not discard or stash that work to manufacture cleanliness. Push, PR and merge remain separate steps. No player-pipeline rerun stage applies.

After successful real execution, present only its verified new review assets. Ryan makes the final visual judgments, including each clip's final frame. Previous reviews remain closed. Any new frame-level identity adjudication beyond this six-clip review needs its own bounded scope; it must not silently change center labels or inherit old judgments for replacement candidates.

## Status reporting and decision point

Each progress update should state what is now complete, what that establishes about tracking, and the next unresolved question. During a long check, report its observed progress and resource use; do not present test counts as accuracy gains or invent a completion estimate.

The delivery should lead with wrong detections removed, correct sightings lost and matches recovered, per window and separate pool, followed by the clips needed to inspect those changes. Include startup behavior, the fixed P003 recovery interval and paired center errors. If agreement preserves shared distractors or discards correct balls, report the tradeoff plainly. Any parameter change or appearance/identity method becomes a new scientific proposal.

The nine prediction embargoes, three sealed holdouts, 636 mean artifacts, completed human/AI reviews and all historical failures stay preserved. This comparison produces development evidence; it cannot establish full-game generalization or a completed Player Defense Score.
