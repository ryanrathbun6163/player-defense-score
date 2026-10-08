# Research method, evidence levels, and unresolved questions

Research date: 2026-10-08. Repository starting point: branch `codex/ball-detector-baseline`, HEAD `7698eac7129dbfcf242d8fbc42d6436158b0cc9a`, clean worktree. The assignment was a thorough external research effort to improve implementation choices and reduce repeated custom experimentation.

## How this review was conducted

Four parallel workstreams covered ball-specific models, player/identity/geometry methods, complete sports projects and analytics, and evaluation/data/pipeline design. The synthesis connects them to this repository's completed experiments. Search and citation chaining used original papers, author repositories, official benchmarks, official documentation and first-party vendor descriptions. Discovery hits were not treated as validated performance claims.

For the most relevant candidates, inspection went beyond abstracts and README files to preprocessing, temporal windows, prediction, association, evaluation, configuration and license files. Repository revisions are recorded where retrieved. We distinguish a paper's method from a later repository implementation and a source license from weight/data terms. We also searched newer 2025–2026 work and checked whether attractive results were accompanied by usable artifacts.

The root reviewer independently inspected key WASB loader/evaluator/model-zoo material in addition to the ball workstream's inspection. Other cross-checks address claims that a sports player benchmark measures balls, that occupancy/coverage measures accuracy, or that a floor homography estimates airborne-ball location. These checks target decisions that could cause us to choose the wrong implementation.

This was a broad, source-grounded engineering review, **not a formal systematic review or meta-analysis**. There is no exhaustive-paper-count claim, fixed database search protocol, inter-reviewer agreement score, or assertion that every relevant project worldwide was found. “All possible knowledge” is not a finishable scope; this deliverable instead covers the major technical families and the most actionable sports implementations, with explicit gaps.

## Evidence levels used throughout

| Level | What was actually checked | What can be claimed |
| --- | --- | --- |
| Discovery | Title, abstract, official repository entry or indexed excerpt | A relevant lead exists; details may be incomplete |
| Documentary review | Paper sections, documentation, benchmark protocol, model card | What authors report and the conditions they describe |
| Implementation inspection | Actual source/config/license files | How inspected paths behave or what resources are declared |
| Reproduction | Install, execute and evaluate matching artifacts/protocol | Not performed on any external method during this research |
| Project validation | Run on our agreed data, compare and visually review | No new method received this status during this research |

An inspected project is not a reproduced project. A public weight link is not proof that the bytes were successfully downloaded or that the checkpoint matches a claimed training history. A dataset download page is not permission to republish underlying broadcast footage. A vendor announcement is first-party evidence of a product claim, not an independent accuracy evaluation or an open implementation.

Each source ledger records its own inspection depth and caveats. Bibliographic entries, code/config URLs and license URLs are separate records where useful; their count is not the number of distinct papers or systems deeply reviewed.

The completed collection has eight narrative documents and four JSON source ledgers. The ledgers contain 269 records and 265 distinct exact URLs: 75 ball records, 93 player/geometry records, 73 project/analytics records, and 28 evaluation/detector records. Distinct URLs are not necessarily independent studies; a paper and its implementation can contribute several records. No external method was reproduced.

## Breadth covered and its limits

| Area | Coverage | Principal unresolved issue |
| --- | --- | --- |
| Generic detection | RF-DETR, YOLO ecosystem, slicing, RT-DETR/D-FINE/DEIM alternatives, Grounding DINO | Which changes improve our actual basketball errors |
| Ball-specific perception | TrackNet line, WASB, newer occlusion/blur work, physics-assisted alternatives | Released models' local transfer and visibility semantics |
| Player tracking | Detection association, motion/appearance/pose, learned association, sports benchmarks | Whether replacing our reviewed foundation is worth the disruption |
| Identity/team | ReID, jersey OCR, tracklet evidence, roster linkage | NBA identity under our resolution, uniforms and camera cuts |
| Segmentation/point tracking | Prompted video masks, long-term memory, point propagation | Tiny ball discovery/reacquisition and manual-input requirements |
| Geometry | Court/pitch calibration, camera motion, point/line models, planar/3D distinction | Reliable moving-camera geometry and airborne ball height |
| Full pipelines | SoccerNet/TrackLab, Roboflow, DeepSport, basketball prototypes | No inspected source establishes the entire auditable NBA defensive-value chain |
| Data/analytics | Sports benchmarks, open tracking/event formats, commercial open samples, event/value references | Compatible labels, rights, causal interpretation and transfer |
| AI/video understanding | Event spotting, possession clips, multimodal basketball understanding | Semantic correctness is not metric trajectory correctness |
| ML engineering | Annotation, splits, uncertainty, caching, profiling and proportional checks | Selecting the minimal useful changes instead of adding another framework |

Deep learning fundamentals such as every optimizer, transformer variant or training framework were not individually surveyed. They are not currently the decision bottleneck. Medical, biomechanical and injury-prediction systems appear only where needed to distinguish their sensors/tasks from broadcast basketball. Private commercial algorithms cannot be inspected from product descriptions.

## Known verification gaps

1. **No external runtime result.** Windows installation compatibility, GPU memory, speed, checkpoint loading, frame alignment and local accuracy remain to be measured for the selected candidate.
2. **Some artifact access is documentary only.** Several weights/data are linked through Drive, forms or agreements. No mass download, credentials request or new account was attempted. Availability and terms are recorded as declared or unresolved, as appropriate.
3. **Benchmark versions differ.** Dataset expansions, metric fixes, changed heads and model versions can change results. Read the versioned source notes before repeating a number.
4. **Label meaning differs.** Some datasets include inferred occluded locations, whereas our current reference requires current-frame support. Others primarily annotate players rather than balls.
5. **Our data is narrow.** Three possessions and repeatedly inspected development windows cannot establish broad cross-game generalization. The research does not turn those into a large independent test set.
6. **Research claims are not recommendations to replace everything.** Promising player association and calibration methods are future references while the current ball phase remains unfinished.
7. **License summaries are component triage.** Unclear weight/data terms stay unclear. We do not infer that “public repository” means unrestricted code, models and footage.

Direct opens occasionally failed. We used accessible author text/code when possible and marked discovery-only sources when not. No source was treated as read merely because a search result linked to it.

## Delivery checks

The four source ledgers parse as JSON; source IDs are unique within each ledger and required citation fields are present. Relative links and code-fence structure in the research documents were checked. Independent reviewers checked the main synthesis against the player, project and ball findings, including selected WASB source paths. These checks establish document consistency, not model correctness. No test suite, model run, study dry-run or scientific replay was needed for this documentation-only delivery.

## How to maintain this knowledge without another bureaucracy

Before a material implementation choice, consult the relevant chapter and shortlist. Add a short note only when a new source changes a choice, a reproduction resolves an unknown, or local evidence rejects a method. Record the actual tested revision, weights and protocol in the existing experiment record. Do not create a new release certificate for every research note.

When a model fails, first classify the failure: integration/coordinate mismatch, unavailable candidate, wrong identity, bad temporal selection, visibility policy or domain shift. Fix routine integration errors and continue. Preserve a useful negative result and move on when the evidence rejects an approach. Report what was completed, what it establishes, and what remains unresolved.

The purpose of this collection is to shorten the next implementation decision and produce a usable project increment. It is not a new prerequisite that every paper must be reproduced before work can resume.
