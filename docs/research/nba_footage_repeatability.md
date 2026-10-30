# Repeated NBA recording access

Date: **October 18, 2026, America/Phoenix**. Starting branch/HEAD: `codex/ball-detector-baseline`, `7785a7bdbe4a3e75b799606e5754db9dbf824015`, clean tracked state. Ryan authorized proceeding after the chosen-game acquisition, whose next access step was to verify additional complete recordings.

## Scope and present result

**Two additional complete public recordings are now local, independently hash-audited and fully decoded:** Sacramento at Memphis on February 23, 2026, and San Antonio at Toronto on February 25, 2026. Sampled images confirm both matchups, all four quarters, opening tips and final results. Together with the previously acquired February 23 Spurs–Pistons recording, the procedure has worked on three specific games across two dates. This is practical access-repeatability evidence, not a basketball-model evaluation or certification of an entire replay catalog.

The three requirements remain distinct:

- **Research clips:** the earlier BARD event clip remains a small acquired research example.
- **The chosen game:** Spurs–Pistons remains locally acquired, with its documented Q4 opening visibility limitation.
- **Repeated complete recordings:** two more complete files have passed technical and sampled visual checks. A complete downloaded object is not proof that its broadcast shows every live possession continuously.

The [machine-readable evidence](nba_footage_repeatability_evidence.json) binds the actual acquisition, recovery, decode, visual and cleanup records. No earlier completed experiment or review was repeated.

## Stable source records

| Game | Official NBA ID | Public replay record | Public embed | Acquired bytes |
| --- | --- | --- | --- | ---: |
| Kings at Grizzlies, 2026-02-23 | `0022500829` | [Replay page](https://basketball-video.com/sacramento-kings-vs-memphis-grizzlies-full-game-replay-february-23-2026-nba) | [OK 12326430640726](https://ok.ru/videoembed/12326430640726) | 5,112,076,363 |
| Spurs at Raptors, 2026-02-25 | `0022500843` | [Replay page](https://basketball-video.com/san-antonio-spurs-vs-toronto-raptors-full-game-replay-february-25-2026-nba) | [OK 12310562081452](https://ok.ru/videoembed/12310562081452) | 4,876,137,080 |

Official identity references are the [NBA Kings–Grizzlies game page](https://www.nba.com/game/sac-vs-mem-0022500829) and [NBA Spurs–Raptors game page](https://www.nba.com/game/sas-vs-tor-0022500843). Period scores and opening/closing events were checked against their [Kings–Grizzlies gamebook](https://statsdmz.nba.com/pdfs/20260223/20260223_SACMEM_book.pdf) and [Spurs–Raptors gamebook](https://statsdmz.nba.com/pdfs/20260225/20260225_SASTOR_book.pdf); extracts and provenance remain local.

Fresh requests check that each replay page still contains its expected embed, retrieve current public player metadata, select the original `full` MP4 variant, and verify the object's range response and total byte count. Signed media addresses and raw responses stay ignored. The procedure uses anonymous requests without account cookies or decryption.

## Local files and technical checks

Both files are H.264 1920×1080 with nominal 60000/1001 fps and AAC stereo 48 kHz. Average rates and actual timestamps remain separate from the nominal rate; no constant-cadence or native-camera-rate claim is made.

| Recording | Local file under `data/raw/nba/` | Container duration | Actual decoded video frames | Verified ranges | Full A/V decode |
| --- | --- | ---: | ---: | ---: | --- |
| Kings–Grizzlies | `0022500829/0022500829_ok_12326430640726_1080p.mp4` | 5,959.879689 s (1:39:19.880) | 357,233 | 153 | Exit 0; empty warning/error log |
| Spurs–Raptors | `0022500843/0022500843_ok_12310562081452_1080p.mp4` | 7,071.104021 s (1:57:51.104) | 423,838 | 146 | Exit 0; one preserved null-output timing warning |

SHA-256 values:

- Kings–Grizzlies: `420eacca7a05f9eebfab6306fe6d28fe1ee0509362cbcc053fba09cfd61b062b`.
- Spurs–Raptors: `714118e131a6bc3c8b24bfb6e4695feb2cd68aec8837bedadea55fa75e64cd9d`.

The two game-scoped transfers used four concurrent range workers each, eight total, with bounded 32 MiB parts. Exact HTTP status, byte range, length and media type were checked. All 299 ranges completed on their first transfer attempt. Successful parts were assembled in order and hashed; one independent full-file pass per recording checked every assembled range against its recorded hash and checked the overall digest. Both audits passed. The host supplied no publisher checksum or ETag/Last-Modified validator, so this establishes local transfer/assembly integrity, not publisher authenticity.

Each file received exactly one complete video/audio decode. Declared frame counts, packet counts and actual decoded counts agree. Kings–Grizzlies produced 597 overview images plus two exact endpoint images in 170.110 seconds; Spurs–Raptors produced 709 overview images including the exact first and last frames in 190.250 seconds. Overview spacing is 599 decoded frames, about 9.993 seconds. Packet presentation timestamps bind each image to its original frame index. No extra targeted media decode or OCR pass was run. Saved-image contact sheets and selected original overview images were inspected; sparse sampling cannot certify every possession, all 48 minutes of visible action or the absence of small edits.

Spurs–Raptors emitted a 129-byte null-muxer warning: two output DTS values equaled 423840. Source DTS is increasing, presentation-ordered PTS is increasing, all 423,838 frames decoded, and the final image exists. The last two source presentation timestamps, 7071.056689 and 7071.061689, are 5 ms apart and both round to nominal-rate tick 423840. This supports output-timebase rounding as the explanation, but the muxer timebase was not independently probed; the cause remains an inference. The warning and calculation are preserved in `sas_tor/decode_warning_diagnostic.json`. Each file also has one packet with unavailable duration; its available PTS is retained rather than discarded.

The acquisition evidence is under `data/outputs/t/nba_repeatable_access_2026-10-18/`, with separate `sac_mem/`, `sas_tor/` and `official_reference/` directories. Each raw file has a `.source.json` provenance sidecar. Recordings, images, signed addresses and generated evidence remain ignored; sanitized summaries and hash bindings are committed. Existing files and reviewed baselines were not overwritten.

## Observed basketball coverage

Scores below are away–home. An END/FINAL graphic is distinguished from a literal zero clock.

| Boundary | Kings–Grizzlies observation | Spurs–Raptors observation |
| --- | --- | --- |
| Opening | Memphis court, NBC Sports California broadcast, jump ball and early Q1 0–0 | Spurs broadcast introduction, then Toronto center-court jump ball and early Q1 0–0 |
| Q1 end | END 1ST, 33–25 | END 1ST, 30–29 |
| Q2 end | HALFTIME, 63–61 | Late Q2 at 2.3 seconds, 57–59; next START 3RD/arena 12:00 corroborates the score. Exact Q2 zero/end graphic was not isolated. |
| Q3 end | END 3RD/arena 0.0, 92–89 | END 3RD/arena 0.0, 78–90 |
| Q4 end | Q4 00.0 and exact last-frame FINAL, 123–114 | Late inbound at 8.4 seconds, later 0.2 seconds, then FINAL 110–107; exact last frame also shows FINAL 110–107 |

Kings–Grizzlies has a delayed START 4TH graphic: the arena clock is already 11:49 in that sampled image. No claim is made that its opening inbound or every period restart was established. Spurs–Raptors pregame contains Spurs–Pistons highlights; those images were explicitly excluded from the Toronto game's quarter evidence. The final Raptors miss/rebound was not reconstructed from the sparse images. The previously acquired **chosen Spurs–Pistons game's Q4 opening limitation remains unresolved**.

These are assistant checks of source access and sampled content. They do not replace Ryan's identity, calibration, synchronized trajectory, final-frame or other human pipeline-review gates. Source times, frame indices, image paths, image digests and observations are retained in each lane's `visual_access_summary.json` and associated manifests.

## Failed attempts, recovery and resource accounting

Kings–Grizzlies downloaded all 153 ranges but its original process failed before assembly: Windows denied replacement of `acquisition_receipt.json` with `acquisition_receipt.tmp` (`PermissionError`, WinError 5). The exact cause of the access denial is unknown. The original receipt remains **`failed_preserved`**, its original script remains unchanged, and the terminal traceback is saved with its capture provenance. Recovery assembled and checked the existing pieces, consuming **zero additional download bytes**. A separate recovery receipt records the resulting file; it does not turn the original failed attempt into success.

| Work | Recorded elapsed time | Meaning |
| --- | ---: | --- |
| Kings–Grizzlies original attempt | 1,204.344 s | Failed after transfer, before assembly |
| Kings–Grizzlies active recovery | 7.937 s | Local part checks/assembly; no redownload |
| Kings–Grizzlies start through recovery completion | 1,263.384 s | Wall time including original failure and interruption; do not add this to the original attempt |
| Spurs–Raptors acquisition | 1,180.188 s | Original successful acquisition |
| Independent assembled-file audits | 6.203 s / 5.812 s | Kings–Grizzlies / Spurs–Raptors |

The two new media payloads total **9,988,213,443 bytes**, plus two one-byte range probes and page/metadata traffic. This is recorded media payload, not an exact measure of network-wire traffic. The three retained complete recordings total 16,069,316,873 bytes. After full audits and decodes, 299 duplicate successful range files totaling 9,988,213,443 bytes were removed; range sidecars, source recordings, failures and receipts were retained. Cleanup's first preflight failed before deletion because PowerShell's property measurement produced no total for ordered dictionaries. The preserved script/failure record and corrected explicit summation document the routine fix. Two early attempts to view a Kings endpoint before it was written are also retained as diagnostic misses; they caused no extra decode.

Final evidence assembly first stopped before writing outputs because its new hash assertion assumed both visual-summary producers used the same field name. The saved failed helper and preflight record preserve that consumer error. Explicit bindings to the two actual producer fields then passed. The final evidence binds 53 supporting files, including a digest manifest for all 1,308 saved overview/endpoint images; source media was not decoded or downloaded again for this correction.

## What this changes for the project

The public-page-to-file procedure has worked for three specified complete recording objects. The immediate access obstacle is resolved sufficiently to plan NBA development clips. It does not establish all-season availability, future uptime, an alternate source for obscured plays, or rights to the underlying broadcasts. The copies share the same public hosting route and are not independent distribution providers.

Newly inspected footage is development-visible. No game has been designated an independent test holdout, and no train/development/test split is accepted by this access check. The next scientific step requires a concrete possession-selection and split plan, followed by inspection of the exact selected intervals before labeling or training. The source recording and any future clipped version must retain provenance and exact time/frame mappings.

The original NFHS holdouts remain untouched. Earlier model runs, negative results and completed reviews remain complete; the three new motion-comparison human reviews remain pending. No ball-model inference, training or new ball annotations occur in this access check. League Pass playback and the earlier OBS capture failure retain their recorded status; this public-file route does not retroactively fix that capture attempt.
