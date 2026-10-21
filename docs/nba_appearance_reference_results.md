# Candidate appearance references ready for review

Ryan's “Move forward chat” authorized the
[appearance-reference preparation](nba_appearance_reference_preparation.md).
The fixed batch is complete: 15 native target frames, all 26 original mean
candidates at those frames, and 75 consecutive context frames. The separate
[compact result](../configs/ball_tracking/reviews/nba_appearance_reference_result_v0_1.json)
binds source evidence, AI proposals, validation and review media. Human
appearance-label acceptance remains pending; no verifier was fitted or tested.

## What the source inspection found

| Future verifier role | Ball | Other object | Unresolved | Total |
| --- | ---: | ---: | ---: | ---: |
| Potential fit: SAC and P002 | 4 | 6 | 5 | 15 |
| Excluded development checks: DET and P003 | 6 | 4 | 1 | 11 |
| All proposed labels | 10 | 10 | 6 | 26 |

SAC supplies two head candidates, two hand candidates and two nearby patches
on the same jersey, alongside four ball candidates. The four excluded-check
negatives are DET hand candidates. Thus there are non-ball examples on both
sides, but **no new excluded-check head example**. Multiple objects within a
frame and neighboring samples from one basketball action are correlated, not
independent negative episodes. These counts do not establish verifier accuracy.

All five P002 candidates remain unresolved because the local evidence blends
hands, arms, uniforms and a possibly occluded ball. Both AI readers retained
that uncertainty. DET 11499 is also unresolved in the published draft: one
reader identifies upper-arm tissue while the first reader cannot settle the
association with a partly occluded held ball. Both original judgments and the
conservative resolution are saved. No consensus or human verdict is invented.

The proposals preserve source-first AI authorship and prior exposure. They
classify candidate appearance; they do not create new ball centers, correct
coordinates or turn geometric errors into automatic non-ball labels. All
original candidates at the fixed targets remain present; nothing was resampled
after seeing the classes. The six unresolved rows are not training negatives.

## Complete review package

Watch the [48-second compilation](../data/outputs/ball_tracking/nba/appearance_reference_v0_1/review/attempts/e77dd3e85dc44ad9867f48656019b6dd/appearance_review.mp4)
and use the [review guide](../data/outputs/ball_tracking/nba/appearance_reference_v0_1/review/attempts/e77dd3e85dc44ad9867f48656019b6dd/review.html)
to zoom into every target, read the rationale and inspect each context final.
The guide includes all 15 target stills, all 15 context-final stills and the
actual compilation final, P003 frame 430. Each target has two native frames
before and after it, shown at five frames per second, with an extra 1.2 seconds
on the target and one second on the context final.

The full scene appears beside fixed 128×128 source crops. Orange crosses mark
existing saved candidate points, not new reference centers. Proposed classes
appear only on target frames; surrounding frames remain unlabeled context.
No confidence scores are displayed. The separate unmarked source sheets used
for AI inspection are preserved under the output's `source_sheets/` folder.

Ryan should accept or correct **all 26 object proposals**, including the six
unresolved cases and ordinary-looking balls, through the actual final frame.
This is the new appearance-label decision required by the
[working agreement](context/working_agreement.md#assistant-first-pass-ryans-2026-10-18-clarification).
Earlier center-reference and video reviews remain complete and do not need
renewed approval. After acceptance, publish a separate accepted appearance
reference while preserving this draft and its pending-era media receipts.

## Scope, validation and limitations

Metadata was frozen before new source pixels or labels. One source-preparation
attempt completed in 14.968 seconds, reusing 55 hash-verified NBA PNGs and
decoding 20 permitted NFHS frames. Both NFHS clips were checked against their
source hashes before decoding. Native clocks, candidate component indices,
coordinates and provenance remain exact. The preparation performs no model
call, candidate-array read or geometric scoring.

The source-role audit passed 86 checks. Five preparation tests passed in
2.977 seconds, using the actual producing code for critical fixtures. Five
distinct review tests passed across their final affected runs, covering exact
candidate crops, target-only classes, complete encoded transport, final holds,
resume, tamper rejection and failed-attempt retention. The first renderer test
attempt exposed a missing clock field in its synthetic fixture; a later run
also exposed two test-only expected-error-text mismatches. Those failed logs
remain preserved. Corrections affected tests only; production code remained
identical to the successful actual preparations. No full suite was repeated.

The actual review render succeeded on its first attempt in 20.359 seconds.
All 75 frames passed native-source/candidate/class keys, exact review timing,
paired pixels and local-marker checks. An independent audit passed 1,649
checks, including all 75 source/proposal joins and probe times, 31 encoded
target/context/final still keys, and independently paired source/crop pixels.
Maximum independent pixel mean absolute error was 3.255 RGB levels. The
compact record also binds the assistant's actual encoded-still inspection;
this is not a claim of human review or continuous manual playback.

Potential-fit sources are SAC and P002, restricted to historically authorized
training blocks. DET and P003 are excluded from fitting a future verifier.
P003 was already used to train the retained detector and DET has been examined
in development, so these are not unseen checks. The current 34 gap/anchor
regression examples and their 74 context frames do not overlap the new batch.
Existing source-role assignments, protected holdouts, the retained `09da`
checkpoint, rejected NBA continuation, original 790-frame results and accepted
27-frame extension remain unchanged.

This small collection supports an initial appearance-data review. Its unresolved
NFHS examples and lack of excluded-check head negatives limit what a future
trial can claim. A later bounded verifier proposal must account for those gaps,
preserve original points and abstain from unsupported new fills. No fitting,
new inference, selector change, threshold grid, holdout release or broader
adoption is authorized by this preparation.
