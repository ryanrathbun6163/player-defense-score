# Spurs–Pistons footage acquisition — February 23, 2026

Acquisition date: **October 18, 2026, America/Phoenix**. Starting repository state: `codex/ball-detector-baseline`, `016a04a8d753793721161d7332a8cd8ffb80e057`, clean tracked index/worktree. Ryan authorized proceeding after the [footage-access investigation](nba_footage_access.md).

## Result

The selected **6,081,103,430-byte** recording is now local. Every downloaded range matches its assembled position, and the entire video and audio decode successfully. It is 1920×1080, nominally 60000/1001 frames per second (about 59.94), with 415,953 decoded video frames and a container duration of **1:55:39.509**.

Local source: `data/raw/nba/0022500828/0022500828_ok_12326019402326_1080p.mp4`.

SHA-256: `27b5143105f5bf3276a2cc51945133c9fdcd2b82d4247d8365110428062ec21f`.

The [sanitized evidence summary](nba_game_0022500828_acquisition_evidence.json) records the result and binds 42 local receipts, manifests, helpers and review records by SHA-256. A source sidecar sits beside the ignored MP4.

All four quarters appear in the recording. The inspected opening, closing, clock anomalies and long OCR gaps support its practical use for selecting NBA development clips. **The broadcast returns from a coach interview with Q4 already underway; its opening inbound is not visually established. Complete coverage of every possession remains unproven.** Acquisition and complete decoding do not by themselves establish that every live interval was preserved by the uploader. No ball model, labeling, training, identity reconciliation, court calibration or pipeline acceptance occurred during this acquisition.

## Provenance and retrieval

The [exact-game replay page](https://basketball-video.com/san-antonio-spurs-vs-detroit-pistons-full-game-replay-february-23-2026-nba) embeds [public OK video 12326019402326](https://ok.ru/videoembed/12326019402326). Its saved player metadata identifies movie `12326019402326`, content `11318997682774`, and the `full` MP4 variant. Anonymous retrieval used no account cookies or decryption. Stable source pages are retained here; expiring media addresses and raw responses remain ignored locally.

All acquisition diagnostics are under `data/outputs/t/nba_full_game_acquisition_2026-10-18/`, abbreviated **acquisition root** below. The original research samples and their receipts remain in the separate `nba_footage_access_research_2026-10-18/` directory. They were not substituted for this full-file verification.

The first, single-connection transfer was deliberately interrupted because it sustained only roughly 1.2 MB/s. Its 188,743,680-byte partial file remains beside the completed source. The original receipt last recorded 184,549,376 bytes: one additional 4 MiB chunk had reached disk before the interruption. Its original `started` status and the explicit process-interruption record are preserved; that invocation is not relabeled a success.

The continuation reused this prefix once. It checked both ends of the prefix against fresh remote ranges, then used eight concurrent workers for 176 disjoint suffix ranges of up to 32 MiB. Every response had the expected HTTP 206 status, exact byte range and length. All 176 completed on their first attempt. Assembly and hashing took the continuation to **835.094 seconds** overall.

An independent local audit reread the assembled file once, compared every suffix range against its recorded hash, compared the prefix against the retained partial, and reproduced the full SHA-256. It passed in 6.719 seconds. This proves agreement with the acquisition records; the host supplied no published checksum, ETag or Last-Modified value establishing publisher authenticity.

## Full decode and timing

FFmpeg decoded the complete video and audio with errors treated as fatal. It exited zero after **150.094 seconds**, emitted **415,953 video frames**, reached end-of-stream, and produced an empty warning/error log. The same pass extracted 6,933 scoreboard images at every 60th decoded frame and 694 overview images at every 600th frame. No second full decode was needed.

The source is H.264 with AAC audio at 48 kHz. Its nominal video rate is `60000/1001`; the reported average is the slightly different `1534918101/25607525`. All 415,953 packets have presentation timestamps. The first is 0.033 seconds, the last 6939.508689 seconds. After one opening 0.026689-second step, the observed presentation intervals are 0.016 or 0.017 seconds. One encoded packet lacks a duration field, but has valid presentation and decode timestamps. There are no non-increasing decode timestamps. These container details do not establish native camera cadence or absence of editorial cuts.

Two verification preflights stopped before full decoding and remain recorded. The first incorrectly required the nominal and average frame-rate fractions to be identical. The second incorrectly discarded a packet with a missing duration and overflagged normal millisecond timestamp quantization. The corrected helper parses fields independently and binds image times to actual presentation timestamps. Original scripts, receipts and diagnostics remain intact. The successful full decode belongs only to the corrected third helper.

## Basketball coverage

The official reference is the [NBA game book](https://statsdmz.nba.com/pdfs/20260223/20260223_SASDET_book.pdf). It records Spurs–Pistons quarter-end scores of 24–27, 57–55, 83–75 and 114–103. The final scoring event occurs with 56.7 seconds left; the final recorded event is a shot-clock turnover with 17.6 seconds left. Seeing 114–103 alone would not establish the end of play.

The actual first frame shows the center-court opening-tip setup before the scoreboard appears. A separate short decode of the last 2.5 seconds reached the exact last video timestamp, 6939.508688889, and saved the final image showing FINAL, 114–103. Closing samples show the last score transition at 56.7 seconds, the clock reaching the official final-event time of 17.6, later 7.9 seconds, and a separately inspected `00.0` before FINAL. The brief endpoint extraction does not repeat the full-file decode.

Windows OCR processed all **6,933** sampled scoreboard images once in **406.126 seconds**. It returned text for 5,554 and empty text for 1,379, with zero processing errors. The conservative spatial parser found **2,781 exact quarter/clock pairs (40.1% of sampled images)**. This is a text-reading yield, not a percentage of complete game coverage. Raw OCR text, unreadable images and ambiguous readings are retained; official scores are not used to rewrite OCR text. No calibrated OCR confidence is available.

Three raw adjacent-pair flags were raised. Two came from one Q3 OCR mistake: the saved images visibly read 7:37 → 7:36 → 7:35, while OCR read the middle clock as 9:36. The Q2 9:20 → 9:28 increase is actually visible in the scoreboard, within the same close-up during a stoppage, with 29–29 and a 24-second shot clock unchanged. Earlier images show a stopped 9:28; later images show Detroit inbounding at 9:28 and the clock resuming. This is consistent with a clock correction, rather than evidence of omitted play; its cause is not independently established. Original OCR and the first production analysis remain unchanged; visual findings are separate records.

There are **366 interior gaps longer than roughly three seconds between parsed quarter/clock pairs**, plus separately reported leading/trailing unparsed spans. These are gaps in usable OCR, not demonstrated gaps in the recording. The largest interior gap is 186.186 seconds across halftime. The three largest within-quarter gaps were visually inspected using 35 existing overview images and six endpoint crops:

| Source interval (seconds) | Visible quarter/clock endpoints | What the sampled images show |
| --- | --- | --- |
| 5849.887–5968.005 | Q4 4:04 → 4:00 | Court play, free-throw setup, Detroit 91 → 92, then prolonged huddles and bench views at 4:00 |
| 6791.828–6878.915 | Q4 1:11 → 45.8 | Free throws, the 1:02 stoppage, the final scoring transition at 56.7 and resumed court play |
| 5647.685–5728.766 | Q4 5:53 → 5:33 | A stopped clock, replay/closeups and a schedule graphic, followed by live wide court views |

No omitted live interval was confirmed in these three sampled reviews. Their sparse images cannot certify everything between them. The clock-jump detector also allows two seconds of tolerance; small cuts can escape that check.

The separate period-boundary review confirms `00.0` displays and the official scores at each quarter end:

| Quarter | Source timestamp at inspected zero clock (seconds) | Spurs–Pistons |
| --- | ---: | --- |
| Q1 | 1361.402689 | 24–27 |
| Q2 | 3010.049689 | 57–55 |
| Q3 | 4827.865689 | 83–75 |
| Q4 | 6934.970689 | 114–103 |

Q2 begins with 12:00 and 24–27 visible. Q3 court action is visible with the arena clock at 12:00 and shot clock at 24 at source time **3119.008689 seconds**, before the broadcast score graphic appears at 11:57. Q4 has a different limitation: the full-screen coach interview persists through **4868.022689 seconds**, dissolves toward the court at **4869.023689**, and reaches a clear court view at **4870.024689**, with play already underway. The first clear score graphic reads **11:53** at **4874.028689**. This establishes a broadcast-view limitation at the Q4 opening, not a corrupt downloaded byte range. The exact unseen duration and opening inbound are not established. That boundary must be excluded from uninterrupted-possession claims unless another view supplies it.

The parser found clock candidates for 31 of 50 selected official anchors, but only two anchors had an exact OCR match to both post-event scores. Missing score text, graphics timing and sparse sampling limit this automated comparison. These counts are not 31 verified plays or evidence that the other 19 events are absent. Manual opening/closing/quarter findings are distinct from these machine candidates.

## Resources, failures and scope

The completed recording accounts for 6,081,103,430 retained media bytes. The continuation additionally checked two 65,536-byte overlaps; the separate preliminary range probe transferred 65,536 bytes. These measured payloads do not include all HTML, metadata, transport overhead or any buffered bytes discarded when the original process stopped. Do not present them as an exact network-usage total. After independent hash/assembly and full-decode verification, 176 successful duplicate suffix binaries totaling **5,892,359,750 bytes** were removed with path/size/status guards. Their hash sidecars, the interrupted prefix, failed attempts and completed full source remain. `successful_range_cleanup.json` records the exact cleanup.

The official direct-PDF request timed out after 30 seconds with zero bytes and one NBA live play-by-play endpoint returned HTTP 403. The full game-book play-by-play was obtained through the web reader instead. Both failures are retained. Windows OCR helper development also retained its initial type-projection and unsupported Gray8 pixel-format failures before a successful BGRA8 implementation. The first inline endpoint-extraction helper failed at Python parsing before reading media; its later successful script preserves that failure. The Q2 contact-sheet helper retained an unavailable-PIL environment error and a Python-boolean typo before its local correction; previously written images were compared and reused. No OCR model download or software installation was needed.

This recording and its inspected images are **development-visible**. No independent test split has been accepted. Existing NFHS holdouts were not opened, and no earlier training, evaluation or completed review was repeated. The negative motion comparison remains negative; its three new human video reviews remain pending. Older completed reviews remain complete.

One acquired target game is distinct from repeatable access to full games. The earlier research verified responding endpoints for two other games, but their complete media has not been acquired or checked. The separate acquired BARD event clip remains a short research clip. The uploader's underlying redistribution authority and permission for project use remain unestablished.

## Next concrete steps

Use this source to prepare a possession-selection and split plan, then inspect the exact candidate intervals for continuous suitable court views before labeling. Preserve the Q4 opening limitation in any later full-game assessment; an alternate feed would be needed to establish the obscured opening. Separately, acquire and verify additional complete game files before calling the access route repeatable. These are distinct from running another ball experiment. No additional game or backup full source was downloaded during this acquisition.

## Local evidence

Paths below are relative to the acquisition root unless stated otherwise:

- `acquisition_receipt.json`, `interrupted_sequential_processes.json`, the retained raw `.partial`: original interrupted transfer.
- `parallel_acquisition_receipt.json`, `range_parts/*.json`: range acquisition, accounting and hashes.
- `independent_audit/assembly_audit.json`: independent range/prefix/full-hash audit.
- `full_verification/ffprobe.json`, `full_verification/video_packets_v3.csv`, `full_verification/packet_timing_audit_v3.json`: container and actual packet timestamps.
- `full_verification/verification_receipt.json`, `full_verification/ffmpeg_progress.txt`, `full_verification/full_decode.stderr.txt`, `full_verification/decoder_done.json`: successful full decode and sampled-image counts.
- `full_verification/verification_receipt_v1_preflight.json`, `full_verification/verification_receipt_v2_preflight.json` and corresponding helper versions: failed preflights.
- `full_verification/ocr_manifest.jsonl`, `full_verification/overview_manifest.jsonl`: exact frame indices and timestamp bindings.
- `ocr/full_scoreboard_ocr.jsonl` and its summary: retained OCR output, including missingness.
- `official_timeline/`: saved complete official play-by-play text, 539 timed/boundary rows, 110 scoring rows, 50 selected anchors and failed requests.
- `continuity/run_001/`: one production analysis of saved OCR, raw flags, missingness, quarter bounds and official-anchor candidates.
- `continuity/visual_review/`, `visual_boundary_audit/`: separate visual findings, source-indexed contact sheets, actual first/last images and their receipts.

All media and generated artifacts remain ignored. Only documentation and the sanitized evidence summary are intended for Git. All 6,933 actual emitted OCR records were checked against their image manifest for ID, path, frame index, timestamp, source hash and crop origin. There were no binding mismatches or missing IDs. The completed file's size and modification time still match the independent audit. Focused evidence/documentation checks apply; the project's scientific test suite is not relevant to this acquisition-only change.
