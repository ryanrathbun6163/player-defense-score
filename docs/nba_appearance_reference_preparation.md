# Candidate appearance reference preparation

Ryan's “Move forward chat” approves the next preparation proposed in the
[accepted gap-reference evaluation](nba_gap_anchor_reference_evaluation_results.md).
Starting state: clean `codex/ball-detector-baseline` at
`31c84281821d22f66ae3963e88301cc556087218`. This increment prepares source-bound
ball / other-object / unresolved judgments and a compact human review. It does
not fit a verifier, run inference, choose a threshold or change predictions.

## Fixed prelabel census and source roles

The input is the retained baseline's original mean-component candidates from
the completed continuous selection. Use `original_observation.candidates` in
its exact saved order at every target; keep all components and provenance.
Do not mix this consistent pool with the expanded/pruned pools used only for
some repaired gaps. The frozen scope binds the exact continuous selection,
historical fit authorities, current regression preparation and this plan.

| Source | Entire prior block, inclusive | Targets | Role for a future verifier | Objects |
| --- | --- | --- | --- | ---: |
| SAC | 940–1059 | 942, 961, 999 | Potential fit | 6 |
| SAC | 1240–1359 | 1299, 1346 | Potential fit | 4 |
| Possession 002 | 318–367 | 325, 341, 347 | Potential fit | 5 |
| DET | 11000–11119 | 11008, 11059, 11107 | Excluded development check | 5 |
| DET | 11420–11579 | 11431, 11444, 11499 | Excluded development check | 5 |
| Possession 003 | 416–440 | 428 | Excluded development check | 1 |

There are 15 targets and 26 objects: eight potential-fit targets/15 objects
and seven check targets/11 objects. Each target receives two consecutive
source frames on both sides: 75 disjoint source-context frames in total.
Target selection uses saved component counts and temporally separated ordinary
representatives before new source inspection; the ignored inventory records
the exact census and rationale. This intentionally candidate-rich sample is
not representative of all outputs and supplies no prevalence estimate.

Keep source ownership fixed: SAC and possession 002 are on the potential-fit
side; DET and possession 003 stay excluded. Only historically approved
training blocks may supply fitting examples; possession 002's old development
windows do not become training data. Keep its 318–367 block together across
the historical 342/343 boundary. Omit possession 001 from this small batch.
All target context and overlapping three-frame detector input support must
remain inside the assigned block and a permitted source segment.

These are checks withheld from a future appearance verifier, not unseen data.
SAC was consumed by the rejected NBA continuation. Both NFHS sources were
consumed by the retained detector; DET was repeatedly inspected in development.
Some DET targets/context also appeared in earlier diagnostics. Whole-source
role separation reduces direct leakage but cannot establish generalization
from this small, previously seen collection.

The current 34 gap/anchor examples and all their 74 context frames stay out of
the new target/context census and remain linked regression evidence. SAC's
three head frames represent one known episode. No sealed holdout, buffer,
TOR footage or newly selected source video is accessed.

## Source inspection and review

Freeze metadata before extracting or inspecting new pixels. Preserve native
source keys, clocks, source image hashes, exact saved candidate coordinates,
component indices and provenance. Read existing NBA PNGs and decode only the
permitted NFHS context segments. No candidate arrays or model calls are needed.

Inspect full source context and unmarked candidate-centered crops before
proposing each object's class. Coordinates identify an existing saved candidate;
they are not a new accepted ball center. The question is whether source evidence
supports the candidate as a ball, a clearly different object, or remains
ambiguous. An amodal ball center can lie on an occluding arm. Geometric errors,
unknown ball visibility and response strength do not automatically establish
non-ball identity. Preserve ambiguous boundaries as unresolved.

Each proposal carries actual AI authorship, candidate key, classification,
other-object subtype when defensible, and a short source-based rationale.
No class balancing, center correction, label-driven resampling or replacement
of disappointing examples is allowed in this batch. Report all classes by
source and assigned role. If checks lack distinct defensible wrong-object
episodes, report the coverage gap before any future fitting proposal.

Deliver a complete short review with all 75 consecutive context frames, all
26 target candidates and every actual context final, plus a guide with every
target still and uncertainty notes. Make target-only candidate marks and
proposed classes distinguishable from surrounding unlabeled context. Verify
encoded keys, timing, pixels and final-frame coverage; inspect all targets and
finals. Ryan accepts or corrects this appearance-label batch. Existing center
references and prior video approvals do not need renewed review.

## Decision after preparation

After reference acceptance, use the observed object diversity and uncertainty
to decide whether there is enough evidence for one bounded appearance rule.
A future rule should check both original anchors and proposed fill candidates,
preserve original points, and abstain from unsupported additions. The known
SAC head episode remains a regression requirement, while valid near-head DET
balls prevent a blanket head-proximity veto. Any future fitting or inference
scope and its evaluation criteria must be specified from this evidence.
This preparation does not authorize that experiment or broader rule adoption.
