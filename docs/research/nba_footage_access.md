# NBA footage access for Player Defense Score

Research date: **October 18, 2026, America/Phoenix**. Repository starting point: `codex/ball-detector-baseline`, `10f3d4cfd0ce2f3fce2be898e8f498fc2cb1d4d6`.

**Subsequent authorized acquisition:** the selected recording has now been downloaded and fully decoded. See the [full acquisition report and continuity limits](nba_game_0022500828_acquisition.md). Its SHA-256, 415,953 decoded frames, failed preliminary attempts and new visual checks are recorded there. All four quarters are present, but the opening Q4 inbound is not visually established because the broadcast returns from an interview with play underway. Every-possession continuity and repeatable complete-game access remain unproven. The findings below preserve the earlier research-stage evidence and recommendations.

## Initial research finding and recommended action

**A technically usable source for the exact February 23, 2026 Spurs at Pistons game has been found.** An unofficial replay page leads to a public OK video with an ordinary MP4 endpoint and an HLS stream. Eight small segments were downloaded and decoded locally at 1920×1080, with an encoded frame rate of 60000/1001, approximately 59.94 fps. Visual inspection shows the opening tip in Detroit, action later in the game, and the final Spurs 114–Pistons 103 scoreboard. This materially changes the earlier conclusion that no workable NBA source had been established.

The full 6,081,103,430-byte MP4 has **not** been downloaded. Sparse samples establish accessible, decodable footage and strong game-identity evidence; they do not certify uninterrupted coverage of every possession. A second public file-hosting route exposes a 5,289,752,196-byte file named for this exact game, but its media has not been decoded. Neither third-party source establishes a footage license for this project.

There are also concrete alternatives for broader NBA work: hosted historical game files in MIT HAN Lab's Inf-Stream datasets, directly downloadable NBA event clips in BARD, and a documented professional full-game download product in Synergy. These serve different needs. A fixed historical corpus is useful for research but is not a current-season feed; event clips cannot silently replace continuous possessions; a professional subscription does not by itself authorize ML use.

**The next practical step is a full acquisition and continuity check of the verified exact-game source**, retaining its original cadence and provenance. Keep the second exact-game route as a backup. Establish at least two additional complete game files before describing the route as repeatable for project use. More labeling or training should follow usable source acquisition and a concrete split plan, not precede them.

## Reading map

| Document | Coverage |
| --- | --- |
| This report | Decision, locally verified findings, original-source correction, and next acquisition steps |
| [Unofficial sources](nba_footage_unofficial.md) | Exact-game replay hosts, file lockers, public archives, torrents, international indexes, failures and repeated endpoint checks |
| [Platforms and professional services](nba_footage_platforms.md) | League Pass, Amazon, Peacock, PlayOn, recording/download products, capture hardware, Synergy, Hudl and licensing |
| [Research datasets](nba_footage_datasets.md) | Actual files versus metadata, full games versus crops/clips, access gates, quality and pretraining-overlap concerns |
| [Source ledger](nba_footage_access_sources.json) | URLs, inspection depth and limitations, including local verification evidence |

Raw page responses, signed media addresses, headers, scripts, images and samples remain ignored under `data/outputs/t/nba_footage_access_research_2026-10-18/`. Stable public source pages are linked here. Expiring CDN addresses are not durable acquisition references.

The new ledger contains **134 source/inspection records with 156 distinct source URLs**, including grouped dataset references and separate local observations. These are not 134 reproduced studies or acquired games. Twelve saved receipt/ledger files are bound by SHA-256; raw responses remain local because some contain expiring media addresses and request headers.

## Requirements and present coverage

| Route | NBA research footage | Exact chosen game | Repeatable complete games | Present evidence |
| --- | --- | --- | --- | --- |
| Basketball-Video → OK | Yes, actual samples decoded | Strong visual match to target | Promising, not fully established | Target samples plus live endpoints for two additional games |
| Sport-Video → MEGA | Potentially | Exact filename and live file metadata | Several live game-file records | Target binary endpoint and metadata; no decoded media |
| Inf-Stream hosted NBA files | Yes, historical broadcast files | Not established | Fixed historical corpus | Public file headers and container metadata; no complete-game audit |
| BARD | Yes, short event clips | Different season/game in checked sample | Repeated event-file access, not complete-game coverage | One complete local 473-frame clip decoded |
| SportsMOT | NBA tracking sequences | No | Fixed clip dataset | Public archive byte-range access; no clip decoded in this investigation |
| PL-NBA / FineSports / SportsHHI | Potentially useful possession/action clips | No target established | Fixed research datasets | Different access gates; see detailed chapter |
| NBA Games metadata / YouTube | Historical full-game references | No target in downloaded metadata | Finite, changing public catalog | 189 metadata records; example video retrieval was not verified |
| League Pass → Prime / Peacock → PlayOn | Plausible consumer fallback | Replay catalog must be checked | Conditional on catalog and recorder compatibility | Documented components, no end-to-end NBA recording test |
| Synergy Video Express | Potentially | Entitlement/catalog unverified | Documented full-game download and scheduling | Product workflow verified; researcher eligibility and ML permission unresolved |
| Hudl Instat | Potentially | Unverified | Professional film workflow | Generic capabilities; NBA export and use entitlement unresolved |
| Antenna/tuner recording | Selected future broadcasts | Cannot recover this past Peacock game | Conditional future channel coverage | Documented local DVR capability, no local reception test |

Technical retrieval, scientific suitability, and permission to use or publish footage are separate questions. The table answers the first two only to the stated depth. Publisher license labels and a code repository's MIT license do not establish rights to underlying NBA broadcasts.

## Exact game evidence

### Stable acquisition chain

1. [Exact Basketball-Video replay page](https://basketball-video.com/san-antonio-spurs-vs-detroit-pistons-full-game-replay-february-23-2026-nba).
2. Its Server 1 embeds [OK video 12326019402326](https://ok.ru/videoembed/12326019402326).
3. The public embed response contains player metadata with multiple MP4 variants and an HLS master playlist. No account cookies, credentials, subscription session or decryption were needed for the checked source.
4. The full-resolution MP4 returned HTTP 200, `video/mp4`, byte-range support, and a content length of **6,081,103,430 bytes**. The HLS master advertises 1080p/60 and 720p/60 alternatives; the decoded 1080p samples establish the more precise rate of **60000/1001**.

This is different from extracting League Pass's protected playback. The tested object is a third-party public upload. Its provenance includes the visible Peacock/NBA broadcast marks, but the uploader's redistribution authority was not established.

### Downloaded and decoded evidence

The full-resolution media playlist contains **694 segments**, totaling **6,939.513221 seconds**, approximately **1:55:39.5**, and ends with `EXT-X-ENDLIST`. No `EXT-X-KEY` tag occurs in that inspected playlist. Eight selected segments and the playlist transferred **52,881,180 bytes**. The selected segments all decoded successfully with FFprobe. This is a bounded sample check, not 694 successful segment downloads.

| Segment start in source | Evidence visible in inspected image |
| --- | --- |
| 0.000 s | Opening tip, Spurs white uniforms and Detroit dark uniforms in Detroit |
| 894.050 s | Replay/close view within the same broadcast |
| 1,794.047 s | Basketball action near the Detroit basket |
| 2,994.043 s | Late second quarter, 0.7 seconds remaining, score 56–55 before the remaining free throw |
| 4,194.039 s | Later live action on the same court |
| 5,394.037 s | Fourth quarter, 8:40, Spurs 92–Pistons 82 |
| 6,594.034 s | Fourth quarter, 1:12, Spurs 110–Pistons 100 |
| 6,930.037 s | Final seconds; the segment's last decoded frame displays FINAL, 114–103 |

The last segment decoded **568 video frames**, including its actual final frame. The visible final result and team records agree with the [official NBA game book](https://statsdmz.nba.com/pdfs/20260223/20260223_SASDET_book.pdf). The game book records a 57–55 halftime score: the 56–55 image above is explicitly **before halftime ended**, not a conflicting halftime result.

Local evidence:

- `exact_game_samples/receipt.json`: original network/download/probe receipt and the first thumbnail helper's failure.
- `exact_game_samples/still_extraction_recovery.json`: local-only correction using already downloaded segments.
- `exact_game_samples/final_frame_check.json`: last-segment frame count and final-frame evidence.
- `exact_game_samples/contact_sheet_recovered.jpg`: eight source positions.
- `exact_game_samples/source_final_frame.jpg`: final scoreboard.

Paths in this list are relative to the ignored research root above. The first helper's six seek-based thumbnail failures and subsequent contact-sheet failure remain recorded; the successful local correction does not turn that original invocation into a success. Media was not downloaded again for the correction.

### What the evidence does not establish

The official event lasted 2:39; the retrieved program is shorter. Removed advertising, halftime or dead time could explain the difference, but the difference alone cannot distinguish harmless edits from omitted live play. The source must be checked for all four quarters, game-clock continuity, replay transitions and any missing live-action interval. A title, runtime and final score are insufficient for that check.

The measured rate describes encoded frames, not a proof of original camera cadence or absence of repeated frames. Compression, overlays, pans, cuts and replay sequences remain present. No ball localization, player identity, geometry, possession annotation or tracking accuracy was assessed. These inspected source positions are development-visible and must not later be represented as unseen holdout evidence.

### Backup and repeated endpoint checks

The [Sport-Video basketball archive](https://sport-video.org.ua/basketball7.html) links a public [MEGA file for the target](https://mega.nz/file/wPsWSADZ#nI4GEuBVNmO_zqn74uZr8ZBcEj1SOaG1QYIv8CIDnCI). Its public sharing metadata identifies `San Antonio Spurs at Detroit Pistons 23.02.2026.mkv`, **5,289,752,196 bytes**. The binary endpoint responded, but the shared file was not downloaded or decoded. Its codec, actual cadence, completeness and equivalence to the OK copy remain unverified. The public share key is part of the published link; no private account or DRM material was accessed.

The same replay-to-OK procedure was checked on **two additional games**, Sacramento at Memphis on February 23 and San Antonio at Toronto on February 25. **Both MP4 endpoints responded successfully**, with declared full-resolution sizes of 5,112,076,363 and 4,876,137,080 bytes. This supports practical repeatability of endpoint discovery on those examples; it is not proof that their footage matches the titles or that every season game is available. Separately, three Sport-Video-to-MEGA records, including the target, had live public metadata. Shared hosting and possible duplicate encodes mean these should not be counted as fully independent original sources.

Other exact-game embeds were less useful: both Dailymotion parts returned 410 Gone locally despite indexed pages; another host required unresolved JavaScript; a Tencent link returned a generic page without demonstrated target playback. Those failures remain in the detailed source chapter.

## Other concrete acquisition options

### Historical full-game files in Inf-Stream

[MIT HAN Lab's streaming-vlm project](https://github.com/mit-han-lab/streaming-vlm) links hosted training and evaluation video datasets. Actual file-tree inspection found **538 MP4 files** in the training `Baidu_NBA_EN` directory and **171** in `Youtube_NBA`. These are file counts, not unique complete-game counts: some names denote parts. Together those two directories are about 1.75 TB; there is no reason to download them wholesale.

The evaluation `Baidu_NBA_EN` directory contains four long NBA MP4 files. Anonymous HEAD and byte-range requests succeeded on selected training and evaluation files. Container parsing found a Pelicans–Warriors example with a container duration of **2:07:04.417**, and a Memphis–Miami example of **1:54:40.048**, both H.264, 1280×720, **24 fps**. A filename claiming 60 fps was therefore not reliable. These observations establish actual public media files and usable metadata; complete decoding and game-identity/coverage verification remain next checks.

The inspected dataset cards did not provide a clear footage license. The project's code license is not a broadcast license. This route is a promising source for a fixed historical research corpus, not evidence of access to our 2026 target or future games. See [dataset details](nba_footage_datasets.md) and the [training](https://huggingface.co/datasets/mit-han-lab/Inf-Stream-Train/tree/main/Baidu_NBA_EN) and [evaluation](https://huggingface.co/datasets/mit-han-lab/Inf-Stream-Eval/tree/main/Baidu_NBA_EN) file listings.

### A locally usable NBA event clip from BARD

The [BARD dataset](https://huggingface.co/datasets/GabrieleGiudici/BARD) exposes individual NBA MP4s. The checked [Brooklyn–Detroit sample](https://huggingface.co/datasets/GabrieleGiudici/BARD/resolve/main/bkn-vs-det-0022400861/0.mp4) downloaded anonymously and completely:

| Property | Verified result |
| --- | --- |
| Bytes | 5,867,901 |
| SHA-256 | `c6dab08b325dc571d88231619a2e3890a9007a36e13e3457df0e322ebf5bdb78` |
| Resolution | 1280×720 |
| Encoded rate | 60 fps |
| Decoded video | 473 frames, approximately 7.8833 seconds |
| Final frame | Decoded |
| Visible content | NBA Brooklyn–Detroit opening tip, NBA Advanced Stats watermark |

This is the first fully downloaded, completely decoded small NBA MP4 in this investigation. It proves a practical research-clip route; an opening-tip event is not a complete offensive possession. The checked game directory has hundreds of short files, but stitching event clips would introduce overlaps, omissions and selection bias. It must not be presented as reconstruction of an uninterrupted full broadcast. Dataset-provided licensing statements and underlying NBA footage rights remain distinct.

### SportsMOT, PL-NBA and other research releases

[SportsMOT](https://github.com/MCG-NJU/SportsMOT) remains an accessible player-tracking dataset with NBA sequences. The hosted 6,703,191,552-byte training TAR responded to anonymous byte-range retrieval; an 8,192-byte check returned valid TAR structure. The basketball sequence list also downloaded. No full archive or NBA sequence was decoded here. The format is image sequences, with publisher-described 720p/25 fps cadence, not a normal full-game file. Its noncommercial/no-redistribution terms and potential overlap with other basketball research sources need to be retained.

PL-NBA's complete-possession design is relevant, but its Baidu video route still needs actual file verification. FineSports requires an application/release, SportsHHI has an access gate, BASKET releases highlight reels rather than its source full games, and SpaceJam releases short player crops rather than all source broadcasts. The original SAM/NBA_data access problem was traced beyond a broken link: its official history contains a request-only academic-data notice, so a dead landing page must not be treated as an open download. See the [dataset chapter](nba_footage_datasets.md) for each actual release and limitation.

### YouTube and public full-game metadata

The [NBA Games metadata release](https://huggingface.co/datasets/choucsan/NBA_Games) was downloaded and parsed: **189 records**, with dates from **May 8, 1970 through February 3, 2025**. It does not include the chosen 2026 game. Some references point to official NBA or ESPN uploads, while others require uploader verification. The release supplies URLs, statistics and event data, not the video files themselves.

Example YouTube retrievals failed or were throttled in this environment. That does not prove the videos are unavailable in Ryan's browser, and it does not establish a successful local download. The ordinary YouTube toolchain is useful where a video remains publicly available, but a maintained downloader's existence does not prove compatibility with League Pass's protected player. Historical metadata, source terms and current media availability must each be checked. The original [repository](https://github.com/choucisan/nba_games) remains a discovery aid.

## Consumer recording and professional access

The [platform chapter](nba_footage_platforms.md) evaluates these in detail. The practical ranking changed once actual public exact-game media was verified: there is less reason to buy or install speculative capture products merely to reach the first usable source.

**League Pass and Peacock downloads:** current official instructions describe app-managed offline playback, not an ordinary Windows file. Premium upgrades alone are not an established solution. The target was a Peacock NBA Monday broadcast, but October availability in Peacock's authenticated replay catalog was not verified.

**Prime plus PlayOn:** NBA now documents linking an eligible existing NBA-direct League Pass subscription to Prime Video. PlayOn supports Amazon and Peacock and describes ordinary MP4 output. This creates a concrete hypothesis, but no end-to-end NBA-through-Prime recording was tested. Generic channel logos, an old NBA FAQ and a separate subscription are not proof. Confirm the target catalog and current NBA support before purchasing anything. Cloud recordings consume credits and cannot simply be cancelled after a 30-second test.

**Commercial downloaders:** StreamFab, KeepStreams, FlixPal, Audials and Replay Video Capture have relevant vendor claims. The most specific NBA-through-Amazon report found described a regression, not a current verified fix. Some products use DRM decryption; none was installed or operated. The report distinguishes ordinary recording from downloader claims and does not assign vendor claims the status of a successful local file.

**OBS and capture hardware:** the recorded Chrome/OBS black-video attempt remains failed. Protected-content masking is a documented Windows behavior, and ordinary capture cards do not capture HDCP-protected HDMI. This does not prove every supported browser/capture combination would fail, but it makes another generic recorder or capture-card purchase a poor first move. Filming a monitor adds a substantial unmeasured quality penalty. Future unencrypted over-the-air recordings are a different, narrower source option and cannot recover this historical Peacock game.

**Synergy Video Express:** this is the strongest documented professional file workflow found. Its official help describes downloading raw or Synergy full-game video to ordinary local folders and scheduling future game downloads. NBA/WNBA film access appears in professional/coaching packages. However, researcher eligibility, exact-game entitlement, export quality, price and use permission remain open. Current Synergy terms expressly restrict dataset/analytics and ML uses unless permitted in writing. The appropriate next commercial step is a scope-specific inquiry and authorized sample, not a blind annual purchase. Hudl Instat is another professional inquiry candidate but has less specific verified NBA file entitlement in this investigation.

Direct NBA/broadcaster licensing remains an option if sustained, clearly permitted access is important. It is no longer the only identified technical way to get a file. No contact, purchase, subscription change or agreement was made during this research; the platform chapter contains concrete unsent inquiry drafts.

## The original NFHS source is now traced

Ryan correctly recalled that the assistant supplied `playon_full_game.mp4` early in the project. The migrated first-session transcript establishes the source and actual download:

- On August 8, 2026, the assistant recommended the [PlayOn basketball-analysis sample repository](https://github.com/playon/basketball-analysis-samples), explicitly as a temporary development source before the Castle–Cade NBA game.
- The download command used that repository's public CloudFront HLS stream and FFmpeg stream-copy/remuxing. It did not use the PlayOn Home/Cloud recording app.
- Ryan's terminal output later recorded **4,849,555,188 bytes**, successful OpenCV opening, approximately 25 fps, and **180,350 frames**. The byte count matches the current local inventory.
- The first curated clip was chosen by Ryan at **19:35–19:55**. Other historical extraction commands exist in later transcripts, but no raw-video pixel scan or holdout exposure was performed here.

Archive authority: `C:/Users/Ryan/Documents/Codex/2026-08-18/he/outputs/player-defense-score-context-migration/transcripts/01-active-transcript.md`, particularly lines 5858–5891, 6516–6551, 6614–6646 and 6738–6754. The original download-instruction message is `323b42d1-dde5-48e3-bb1a-e03baf4a9f37`; the actual user verification message is `cdcc47f7-d875-4f63-9cf7-a4aaa6531063`.

The earlier handoff's unknown-acquisition-method statement is therefore resolved by newly consulted archival evidence, rather than guessed from the filename. The prior decision to defer NBA acquisition explains the present obstacle; it did not establish that switching to NBA input would later be effortless. The NFHS foundation remains valuable, but it is not evidence of NBA access or validation.

## Acquisition and validation plan

### First acquire the selected game

Use the verified public exact-game embed to obtain a fresh MP4 address when acquisition begins. The saved CDN addresses contain expiry and source-IP fields; do not hard-code them into committed configuration or treat them as permanent URLs. Save the raw file under a new ignored game-scoped directory such as `data/raw/nba/0022500828/`, never over an existing reviewed input.

Record the source page, embed ID, retrieval time, declared and actual byte counts, checksum, container/codec, dimensions, frame rate and timestamps. Retain the original encoding. The preferred tested source is approximately 6.08 GB; the approximately 5.29 GB MEGA alternative needs its own media verification. A changed quality variant or host is a distinct acquisition, not interchangeable evidence.

Then decode the full local file and check the beginning, all quarter boundaries and actual final frame. Verify game-clock progression against the official game book/play-by-play, especially around edits, broadcasts returning from breaks and replay segments. Record missing or ambiguous intervals explicitly. A full decode proves technical readability; clock/event review addresses basketball completeness. Neither is player/ball-tracking acceptance.

### Establish repeatability with complete files

Repeat the acquisition procedure on two additional games with different dates and teams. The two successful endpoint checks already provide concrete candidates. Preserve failed endpoints, host changes, rate limits, retrieval duration and file differences. If one host disappears, refresh from its stable embed/index before declaring the whole route dead. Shared source copies do not constitute independent coverage.

For broader research, select individual historical Inf-Stream files or suitable possession datasets instead of bulk downloading terabytes. Inspect the exact chosen file and publisher terms first. A named 60-fps file may actually encode 24 fps, as the header checks demonstrated.

### Resume scientific work only after source and split decisions

New NBA inputs need an NBA court profile, feed/camera review, game/possession boundaries and game-scoped provenance. The existing NFHS right-half-court calibration cannot simply be reused. Preserve human identity and calibration gates and the configuration-driven design.

Frame counts must follow actual time. A 75-frame episode lasts 3 seconds at 25 fps, but only about 1.25 seconds at 59.94 fps. Do not silently downsample a new source merely to reuse an old label count. Choose episode duration and temporal-model context deliberately, then define labels and train/evaluation separation.

The WASB basketball checkpoint already has NBA pretraining exposure. A research corpus sourced from the same games or parent datasets may overlap it. Establish source-game identities and available training provenance before claiming independent generalization. Missing overlap documentation remains uncertainty. All source images inspected during this access investigation are already seen development material.

No new fit, threshold search, model inference, scoring, old review, full suite or existing scientific audit ran. The motion comparison stays complete and negative; its three new human reviews stay pending; earlier completed reviews and sealed NFHS holdouts remain unchanged. This investigation establishes acquisition options, not the ball-phase acceptance gate.

## Method and limits

The investigation covered official playback/export channels, alternate distributors, broadcaster catalogs, consumer recorders, downloader projects and vendors, Windows/HDMI capture, future broadcast recording, professional film platforms, direct licensing, academic datasets, university-hosted media, public video platforms, unofficial replay indexes, file lockers, torrent/forum routes and historical archives. Promising routes were followed beyond search snippets into primary pages, public metadata, headers, byte ranges or local decoding where feasible.

Verification levels are intentionally distinct: a search result is a lead; an inspected page is a documented route; an HTTP response proves that endpoint responded; container parsing establishes declared media properties; local decoding establishes readable pixels; a complete-game content audit establishes coverage. No route receives a higher level merely because another route worked.

Private invitation-only catalogs, authenticated services, inaccessible hosts and negotiated licenses could not be exhausted from public evidence. No universal claim that every possible source was found is warranted. The useful result is narrower and concrete: the exact game's public footage has been sampled successfully, multiple independent route families now have file-level evidence, and the next acquisition no longer depends solely on a speculative licensing response.
