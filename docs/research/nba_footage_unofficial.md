# Unofficial NBA footage access: practical verification

[Main findings and acquisition plan](nba_footage_access.md) · [Combined source ledger](nba_footage_access_sources.json)

Local receipts mentioned below are under the ignored `data/outputs/t/nba_footage_access_research_2026-10-18/` tree, in this chapter's `unofficial/`, `platforms/`, or `datasets/` directory unless otherwise stated.

Research date: 2026-10-18 America/Phoenix (some HTTP timestamps are 2026-10-19 UTC). Scope: third-party replay indexes, public video hosts, public shared downloads, torrent indexes, fan references and historical archives. No model work, labeling, evaluations, holdout inspection, tests or Git mutations were performed by this researcher.

## Result and limits

The strongest exact-game route is the basketball-video.com replay page embedding OK video 12326019402326. The page, player metadata, HLS master and direct MP4 endpoint were live. The local verification independently downloaded and decoded sparse segments and visually identified Spurs at Detroit, including the final 114-103 score. This establishes practical access to genuine media from the chosen game. It does **not** establish a completed local full-game acquisition or uninterrupted coverage of every possession.

An independent archive, sport-video.org.ua, lists an exact-game MEGA share whose anonymous metadata and binary endpoint were live. The decrypted public filename matches the selected matchup/date and the file is 5,289,752,196 bytes. No media from this alternative was downloaded or decoded, so it remains a live file candidate rather than visually verified game footage.

Repeatability has modest empirical support: two additional basketball-video → OK → MP4 endpoint chains succeeded out of two attempted endpoint checks, spanning two dates; three sport-video → MEGA metadata checks succeeded out of three sampled shares across January and February. This is not evidence that every season game is present, complete, downloadable, or durable.

Rights and provenance remain uncertain for these unofficial copies. Neither page presence nor technical download access establishes permission to redistribute or train on the footage. No licensing conclusion was inferred from embeds or disclaimer text. These findings distinguish research clips, the chosen full game, and repeatable full-game access; none substitutes for the others.

## Exact game: basketball-video and OK

Stable source page:
https://basketball-video.com/san-antonio-spurs-vs-detroit-pistons-full-game-replay-february-23-2026-nba

Stable player:
https://ok.ru/videoembed/12326019402326

The page explicitly names the exact matchup and February 23, 2026, and lists three servers. Its first iframe is the OK player above. Public HTTP GET of that embed returned player metadata, including movie ID 12326019402326, content ID 11318997682774, title '.', status OK, non-live status, nominal duration 6939 seconds, and 1920×1080 maximum dimensions. The punctuation-only host title makes the source-page mapping and visual confirmation essential; the host title alone does not identify a game.

Six MP4 variants were exposed: mobile, lowest, low, sd, hd and full, all marked disallowed=false. A HEAD request to the full variant returned HTTP 200, video/mp4, Accept-Ranges: bytes, and Content-Length 6,081,103,430. The server attachment name was 11318997682774.mp4. This is endpoint evidence, not a six-gigabyte download.

HLS master advertised the following renditions. These are manifest values, not independently decoded cadence except where the separate local sampling establishes it:

| Rendition | Dimensions | Advertised fps | Average bandwidth |
|---|---:|---:|---:|
| mobile | 256×144 | 30 | 336375 |
| lowest | 426×240 | 30 | 540557 |
| low | 640×360 | 30 | 1002085 |
| sd | 852×480 | 30 | 1702101 |
| hd | 1280×720 | 60 | 3859336 |
| full | 1920×1080 | 60 | 7251740 |

The local verification recorded eight sparse 1080p segments, 52,881,180 bytes including the media playlist, successfully decoded. The measured video rate was 60000/1001 fps; media playlist duration 6939.513 seconds, 694 segments, ENDLIST, no encryption tag. The local verification visually identified the opening tip, later game footage and a final 114-103 scoreboard. Review `exact_game_samples/receipt.json` under the ignored research root and recovery/final-frame evidence for exact sampling and consumed bytes. This researcher did not duplicate those downloads. No claim is made that sparse samples prove uninterrupted footage, correct timestamps throughout, complete audio, or every possession. The initial thumbnail-generation failure and subsequent recovery are separate retained evidence.

Files in the ignored `unofficial/` evidence directory: `ok_12326019402326_metadata.json`, `ok_hls_master.txt`, `ok_full_variant_head.txt`. Raw metadata/master contain expiring signed CDN URLs; use the stable source page and embed in shared references and refresh metadata when needed.

## Other servers on the exact page

**Dailymotion:** server 2 embeds `https://geo.dailymotion.com/player.html?video=xa0mx9w` and `https://geo.dailymotion.com/player.html?video=xa0mxja`. Search/web snapshots showed SAS@DET1 and SAS@DET2 pages. Current local HEAD of the corresponding `www.dailymotion.com/video/` pages returned HTTP 410 Gone, including a page-gone indication; the geo embed fetch was blocked with HTTP 403. Cached page titles are not current playback evidence. This route currently failed the anonymous endpoint check.

**Byse:** server 3 points to https://bysesukior.com/e/gdhdjqdk7t5h . Local GET returned HTTP 200 and a 1649-byte JavaScript application shell titled Byse Frontend, referencing `/assets/index-DocunfmE.js`. No video endpoint or working player was verified. HTTP 200 for a shell is insufficient.

**BasketballReplays.net:** the separate exact page is https://basketballreplays.net/nba/nba_2025_26/san_antonio_spurs_detroit_pistons_23_february_2026_nba_full_game_replay/33-1-0-2275 . Web extraction showed the exact title and iframe placeholders. Local Invoke-WebRequest encountered TLS EOF; curl returned HTTP 403/Caddy and no useful page body. No embed destination or media was verified. This may be another index over the same hosts; independence is unproven.

## Independent exact-file candidate: sport-video / MEGA

Source page: https://sport-video.org.ua/basketball7.html

Public shared file: https://mega.nz/file/wPsWSADZ#nI4GEuBVNmO_zqn74uZr8ZBcEj1SOaG1QYIv8CIDnCI

The page row explicitly names San Antonio Spurs at Detroit Pistons 23.02.2026 and links the share. An anonymous MEGA public-file metadata request returned a file size, encrypted attributes and a live download endpoint. File attributes were decoded using the key already included in the public share URL. This is ordinary shared-file metadata handling; no DRM or protected player was bypassed. Decoded name: `San Antonio Spurs at Detroit Pistons 23.02.2026.mkv`. Size: 5,289,752,196 bytes. HEAD of the returned binary endpoint returned HTTP 200, application/octet-stream and that exact Content-Length.

No MKV bytes were downloaded. Codec, dimensions, frame cadence, duration, actual matchup, broadcast origin and continuous completeness are therefore **unknown**, regardless of the filename. MEGA transfer quotas, sustained transfer and ordinary browser download usability were not exercised. The anonymous metadata call does not prove a multi-gigabyte transfer will finish.

Evidence: `sportvideo_exact_game_fragment.html`, `mega_metadata_request.json`, `mega_metadata_response.json`, `mega_public_file_metadata.json`, `mega_exact_download_head.txt`. Raw response includes an expiring download URL and belongs in ignored local evidence only.

The archive has repeated dated game listings. Two additional shares were inspected without downloading media:

| Matchup/date | Decoded filename | Bytes | Public metadata |
|---|---|---:|---|
| Spurs at Toronto, 2026-02-25 | San Antonio Spurs at Toronto Raptors 25.02.2026.mkv | 5,062,868,623 | Live endpoint returned |
| Spurs at Boston, 2026-01-10 | San Antonio Spurs at Boston Celtics 10.01.2026.mkv | 6,246,397,017 | Live endpoint returned |

Stable shares and exact source pages are in `mega_repeatability_metadata.json`. Including the target, this is 3/3 metadata successes; only the target received a binary HEAD check. No visual or full-transfer success is implied. The index covers selected daily games and has current October entries, but some games are absent from inspected date areas. Its NBA ALL GAMES forum link returned HTTP 429. A heading or forum title is not a season-completeness audit.

## Replay access beyond the selected game

The basketball-video 2025-26 category at https://basketball-video.com/2025-26 displayed roughly 141 paginated pages, and the home page showed current October 2026 preseason listings. Category volume and recent posts establish an active index, not guaranteed availability. A Spurs team-menu URL returned 404. A Toronto exact-page web extractor attempt timed out, but direct local HTTP succeeded.

All three February 23 matchup pages were found. Additional host metadata was inspected for Sacramento–Memphis, Utah–Houston, and Spurs–Toronto February 25. Four OK entries across these three additional games returned status OK and HLS metadata; Toronto exposes two different-duration copies (7071 seconds at 1080p and 5536 seconds at 720p), so source edits and timeline differences must be preserved.

Two of those games were carried through to live full-MP4 HEAD requests:

| Game/date | OK ID | Nominal duration | Metadata dimensions | Full MP4 HEAD |
|---|---|---:|---|---|
| Sacramento at Memphis, Feb 23 | 12326430640726 | 5960 s | 1920×1080 | 200; video/mp4; 5,112,076,363 bytes |
| San Antonio at Toronto, Feb 25 | 12310562081452 | 7071 s | 1920×1080 | 200; video/mp4; 4,876,137,080 bytes |

Endpoint check denominator: **2 attempted game chains, 2 successes** after a local parser correction. These two sources were not decoded or visually identified. There is no statistically representative coverage sample, whole-season inventory, historical retention guarantee, or transfer-speed result. The same method can locate further candidate games; each needs its own provenance and completeness receipt.

Evidence: `repeatability_page_sample.json`, `repeatability_ok_metadata_sample.json`, `repeatability_two_game_endpoint_checks_recovery.json`, plus raw recovery metadata and HEAD files. Two local extraction failures are retained: the initial iframe regex assumed `https://` and missed protocol-relative `//ok.ru/` embeds; a later script attempted ConvertFrom-Json on already-decoded metadata. Neither is a website-access failure. The first endpoint receipt contains nulls and is superseded for conclusions by the recovery receipt, not erased.

## Regional replay indexes

https://www.724zbw.com/nba/95088.html labels the selected game as February 24 in China, with final 114-103, and supplies Tencent links for full-game and quarter replays in original audio and Chinese commentary. Date shift is consistent with a U.S. February 23 game, but this alone is not media verification. Full original-audio candidate: https://v.qq.com/x/cover/mzc00200z9n8cnk/z4101d4cnwo.html . Chinese full-game candidate: https://v.qq.com/x/cover/mzc00200z9n8cnk/u3192rehd0s.html . All extracted links are in `tencent_exact_game_links.json`.

Web extraction could not access selected Tencent pages. Local HEAD and GET of the original-audio URL returned HTTP 200 but a generic Tencent Video page; the requested video ID was absent from the saved body. No actual player stream, regional entitlement, download option or exact video metadata was verified. This is a concrete lead to a regional platform, not successful footage acquisition. No login, payment, regional evasion or client install was attempted. A second Chinese index at https://m.zhangchu.net/lanqiu/nba/video-66672.html lists the same ten full/quarter categories; it is not demonstrated as an independent media copy.

The fan discussion at https://chinaspurs.com/t/topic/44941 links a Castle defensive compilation at https://x.com/BalaPattySZN/status/2026162929217769822 . That is a research-clip lead, not a full-game solution, and is separate from the project's existing NFHS source. No clip was fetched or relabeled.

## Torrent and historical archive investigation

**720pier:** https://720pier.ru/viewforum.php?f=34 is active with many seasons, roughly 14.7k NBA threads and roughly 590 pages. Cached snapshots disagreed on exact counts/dates, so no precise live archive-size claim is warranted. Sample thread https://720pier.ru/viewtopic.php?t=76971 describes Spurs at Phoenix October 10, 2026, MKV/H.264, 1280×720, 59.94 fps, approximately 6000 kbps, AAC stereo, ESPN2. These are uploader claims, not probed media. The page explicitly denied attachment access to the anonymous reader. No torrent, magnet, peers or media were accessed. Exact target searches produced no verified thread. Registration might expose attachments but was not attempted; successful login, seeds and transfer remain unknown.

**RGFootball:** https://rgfootball.net/viewforum.php?f=50 exposed a 2025-26 NBA category including All-Star and finals series releases with claimed 720p25/50 and 1080 formats. No exact chosen-game thread or live torrent was verified. Index availability is weaker than usable files.

**RuTracker:** https://rutracker.org/forum/viewforum.php?f=1997 could not be opened via web tool. Searches found old automation recipes and a public plugin maintainer note discussing a 2026 Cloudflare break; neither establishes a working current download. No plugin, torrent client or account was installed/used.

**EXT/Torlock public indexes:** searches returned 2026 finals and selected regular-season metadata. EXT's NBA-finals results included a purported five-game 1080p60 bundle, 44.35 GB; a Denver search showed selected February/October titles. The exact Spurs–Pistons game was not found in searched results. Claimed seed counts are transient index claims, not peer verification. No magnet or torrent was fetched. Stable query pages are in the ledger; these are low-priority leads compared with the exact OK and MEGA candidates.

**Internet Archive:** an anonymous search for Spurs AND Pistons in movies returned 20 results, mostly historical/irrelevant/highlights. The candidate https://archive.org/details/nba-regular-season-archive was inaccessible to the web extractor but its public metadata API worked. It contained 510 files, including thumbnails and 16 MP4 filenames representing older 2017–2024 games and derivative copies. No filename matched the February 2026 target. This collection may support separate historical research, but does not satisfy the selected game or current-season repeatability requirement. No video was downloaded. The full and compact metadata are retained; a too-broad console filter initially included thumbnails and truncated console output, corrected by a compact video-only inventory without refetching the collection.

**Other checks:** watchreplay.net showed NBA zero events/no videos; Basketlita returned a search application and StreamPass promotion but no exact-game player was verified; fishkernba.com timed out; nbareplay.net and nbafullhd.com were inaccessible through the web tool. These tool-level failures are not proof the domains are permanently dead. Reddit/forums supplied generic replay/download suggestions but no stronger exact-game route than those above.

## Evidence handling, resources and next step

This researcher saved only metadata, HTML, manifests, headers and reports, all in this ignored directory. No media payload was downloaded by this subagent. The separate sparse exact-game media acquisition must be counted from its receipts. Network request bytes for search/HTML were not instrumented globally, so an exact total is unavailable; do not equate saved-file size with total consumed bandwidth. No signup, payment, software install, contact, agreement acceptance or account alteration occurred.

CUA browser inspection was attempted: creating an in-app browser returned Browser unavailable; inventory returned no browsers/apps. This is an environmental limitation, not a site verdict. Bounded direct HTTP and web extraction supplied the evidence instead. Failed fetches, stale cached pages, parser failures and corrected conclusions are retained above and in the source ledger.

Practical next access action: use the verified exact-game OK route to acquire a local working copy recording the stable page/embed, retrieval time, selected rendition, hash/bytes, decoder checks and game-clock coverage. Full continuity still needs inspection before this becomes a full-game validation source. Keep the live MEGA candidate as an independent fallback pending actual media verification. For repeatable access, expand a deliberate multi-date/multi-team sample and record the successes and missing games instead of extrapolating from the present 2/2 endpoint result. No additional labeling or training follows automatically from this research.
