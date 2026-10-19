# NBA footage access: datasets and public archives

[Main findings and acquisition plan](nba_footage_access.md) · [Combined source ledger](nba_footage_access_sources.json)

Local receipts mentioned below are under the ignored `data/outputs/t/nba_footage_access_research_2026-10-18/` tree, in this chapter's `unofficial/`, `platforms/`, or `datasets/` directory unless otherwise stated.

Research date: October 18, 2026 (America/Phoenix); HTTP probes timestamped October 19 UTC. Scope: actual NBA media beyond SportsMOT. Dataset-specific checks and the separate local BARD decode are distinguished below. The [main report](nba_footage_access.md) adds successfully decoded samples of the exact case-study game from an unofficial source.

## Findings that change the practical options

1. **Small NBA research clips are obtainable.** BARD hosts individual NBA MP4s on Hugging Face. This subagent verified public HTTP access and MP4 headers. The separate local verification subsequently downloaded one 5.87 MB clip, matched its published SHA-256, decoded all 473 frames including the final frame, and visually identified Brooklyn at Detroit's opening tip with an NBA Advanced Stats watermark. This establishes one usable local NBA clip; it does not establish a complete possession or game.
2. **Historical game-length NBA files have a credible direct-download route.** MIT HAN Lab's Inf-Stream hosts hundreds of MP4s in NBA directories. Two independently probed files return public HTTP 200/206 and contain 720p H.264 video lasting approximately 1h55m and 2h7m. They are encoded at **24 fps**, even though one filename says 60 fps. No entire Inf-Stream file was downloaded or decoded in this subtask, so complete four-quarter coverage, playback integrity, camera continuity and ball visibility remain unverified.
3. **The chosen February 23, 2026 Spurs–Pistons game remains a separate requirement.** No dataset or archive investigated here establishes access to that complete game. A fixed historical corpus also does not establish repeatable access to arbitrary new NBA games.
4. **Download availability and media rights are separate evidence.** Several repositories put open licenses on code, annotations or a dataset card without establishing permission to redistribute or reuse the original NBA broadcast. No signup, agreement, permission request or external message was performed.

Sources: [BARD university page](https://bodai.unibs.it/basketball-action-recognition/bard/), [BARD files](https://huggingface.co/datasets/GabrieleGiudici/BARD), [Inf-Stream official project](https://github.com/mit-han-lab/streaming-vlm), [Inf-Stream Train](https://huggingface.co/datasets/mit-han-lab/Inf-Stream-Train). Direct HTTP/container evidence is preserved in `access_probes.json`; source summaries are in `sources.json`.

## Keep the three requirements separate

| Requirement | Best evidence from this subtask | What remains unresolved |
|---|---|---|
| Representative NBA research clips | BARD individual MP4 publicly accessible; one full local decode completed. BasketEvent has an accessible example; Roboflow has a public short-clip folder. | Representative continuous possessions, ball visibility, provenance and development split assignment need human review. |
| Exact Spurs–Pistons game, February 23, 2026 | None of these dataset routes demonstrates it. League Pass replay and failed OBS capture are historical project evidence; see the main report for newer exact-game samples. | Complete local acquisition, continuity verification and usage permission remain; the main investigation has identified a workable source. |
| Repeatable full-game access | Inf-Stream is an accessible fixed historical corpus, with game-length headers independently verified. | Full-file validation, game deduplication, rights, and whether a historical fixed corpus meets the intended research need. It does not supply arbitrary/current games on demand. |

## Historical full-game dataset alternative: Inf-Stream

The [official StreamingVLM repository](https://github.com/mit-han-lab/streaming-vlm) links its [Train](https://huggingface.co/datasets/mit-han-lab/Inf-Stream-Train) and [Eval](https://huggingface.co/datasets/mit-han-lab/Inf-Stream-Eval) media repositories. The [paper](https://arxiv.org/html/2510.09608v1) describes collecting 712 basketball games alongside other sports and standardizing media to 24 fps at 360p–720p. Its commentary targets come from speech recognition with subsequent language-model processing; these are not ball coordinates or verified player trajectories.

Current public tree metadata, rather than a search snippet, gives:

| Directory | Current inventory | Bytes |
|---|---:|---:|
| Train/Baidu_NBA_EN | 538 MP4 files | 1,468,044,741,903 |
| Train/Youtube_NBA | 171 MP4 files, plus one MP3 and `.gitattributes` | 285,622,080,624 for MP4s |
| Eval/Baidu_NBA_EN | 4 MP4 files | 15,973,781,985 |
| Eval/Youtube_NBA | 1 MP4 file | 1,038,525,650 |

**709 Train NBA-directory MP4s does not mean 709 unique complete games.** Some names indicate quarters or parts, and duplicate games across sources are possible. An older catalog count of 532 Baidu files differs from the observed 538; the live inventory above is the current access evidence. No filename in those inventories contains 2026, but opaque YouTube identifiers and later repository changes prevent a filename scan from proving corpus-wide date exclusion.

### Exact files probed

| Candidate | Public access | Verified MP4 header | Size |
|---|---|---|---:|
| [Train: `01.03.13 MEM@MIA.mp4`](https://huggingface.co/datasets/mit-han-lab/Inf-Stream-Train/resolve/main/Baidu_NBA_EN/01.03.13%20MEM%40MIA.mp4) | HEAD 200; 64-byte and 4,096-byte requests returned 206 | H.264, 1280×720, 24 fps, 165,121 samples, 6,880.0417 seconds of video | 2,981,260,794 bytes |
| [Eval: Pelicans–Warriors March 15, 2016](https://huggingface.co/datasets/mit-han-lab/Inf-Stream-Eval/resolve/main/Baidu_NBA_EN/20160315_RegularSeason_PelicansVSWarriors_ILP_720P_60fps.mp4) | HEAD 200; 64-byte and 4,096-byte requests returned 206 | H.264, 1280×720, **24 fps**, 182,986 samples, 7,624.4167 seconds of video | 3,513,623,547 bytes |

The four-kilobyte front-header reads contained the movie duration, video dimensions and complete constant-rate sample timing entry. They did **not** read the entire multi-megabyte `moov` atom or any meaningful span of video. The rate is supported by the container's timing entry, not inferred from a filename. Duplicate or interpolated source frames are still possible.

The Train candidate's published whole-file LFS SHA-256 is `84f5d87d3a5a74bc2abd1bfd027fbfa96123896b1e7a7a8a43abae62f853b7fd`; its 4,096-byte prefix SHA-256 is `fc3d80cea746b07cba3806dd5886691ccbca45450b7aa4c246d59206c4b596cb`. The 2016 Eval file's published LFS SHA-256 is `7e72b6a761b4075367074537db4a3823febd6aeee0a99ca7953e42624971c655`; its prefix SHA-256 is `6a7c4223eaa793e65fa26a8eb1e289edf737a905d0e41a211554303974ef680e`. Prefix hashes are not whole-file checksums, and published whole-file hashes have not been independently verified by this subagent.

**Next check for this historical-dataset alternative:** use one Train file, not Eval, for a bounded acquisition feasibility check. The main investigation prioritizes the exact February 2026 game first. After any full-file acquisition, record its published hash and actual hash, decode it, and inspect chronological coverage across all quarters before calling it a complete usable game. Decide whether its 24 fps and historical broadcast style suit this project before labeling. The candidate is approximately 2.98 GB; downloading the entire multi-terabyte corpus is unnecessary for this decision. This subtask did not perform that download.

**Rights and provenance:** the official GitHub MIT license covers software/documentation. The observed Train README is actually headed “Inf-Stream-Eval” and has no media license; the Eval page has no dataset card. These documentation defects do not negate the verified media bytes, but they leave terms and source provenance incomplete. Academic hosting does not by itself establish NBA footage rights. The historical filenames suggest mixed Baidu/YouTube sourcing; they do not establish an NBA-issued media license.

## Best small-clip route: BARD

The [University of Brescia BARD page](https://bodai.unibs.it/basketball-action-recognition/bard/) and [official repository](https://github.com/GabrieleGiudic/BARD) describe NBA event/action clips from 60 games across the 2024–25 season, covering all 30 teams. The description distinguishes 24,692 initial clips from 14,676 after filtering and consolidation. The currently hosted [Hugging Face dataset](https://huggingface.co/datasets/GabrieleGiudici/BARD) presents the larger 24,692-row inventory, approximately 182 GB. Preserve the raw-versus-final distinction rather than presenting these counts as identical.

The public tree lists 60 game folders. The inspected Brooklyn–Detroit folder contains 472 MP4s totaling 3,233,574,908 bytes. Each file is individually addressable, avoiding an archive-sized initial download.

**Verified sample:** [Brooklyn–Detroit `0.mp4`](https://huggingface.co/datasets/GabrieleGiudici/BARD/resolve/main/bkn-vs-det-0022400861/0.mp4), 5,867,901 bytes, SHA-256 `c6dab08b325dc571d88231619a2e3890a9007a36e13e3457df0e322ebf5bdb78`. Subagent checks: HEAD 200, Range 206, H.264 1280×720, 60 fps, 473 frames, 7.8833 seconds video. The separate local verification subsequently verified the complete download, hash, all-frame decode and final frame, and identified an NBA opening tip. The saved local verification artifacts remain authoritative for that later local check; this report does not claim an independent duplicate decode.

Labels concern actions and descriptive captions, including team/jersey references. No frame-level ball-center ground truth was established. Event clipping can omit possession beginnings or endings, so adjacent files must not simply be concatenated into a claimed continuous possession. The original 2024–25 inventory is not the February 2026 case-study game.

HF and the project license claim CC-BY 4.0; that is the dataset provider's license statement, not independently verified clearance of NBA broadcast rights. The official [download script](https://raw.githubusercontent.com/GabrieleGiudic/BARD/master/src/download_video.py) also obtains video sources from NBA event pages through Selenium. It was inspected, not executed; a frozen HF collection and a maintained current NBA event downloader are different forms of repeatability.

## Other acquisition routes

| Dataset / source | Released media and scale | Access actually established | Ball labels and suitability |
|---|---|---|---|
| [PL-NBA](https://github.com/holhouse/PL-NBA-Dataset) | README: 40 NBA games from 2022–25, 7,000+ possession clips, mean 12.11s, 1080p. Paper version says 60 games/11,000 clips. | 4,461,082-byte annotation ZIP listed in GitHub; Baidu media URL reaches extraction-code page. No media bytes verified. | Event/possession annotations, not established ball-center labels. Strong possession semantics if access works; not released full broadcasts. |
| [FineSports](https://github.com/PKU-ICST-MIPL/FineSports_CVPR2024) | 10,000 NBA action videos, released structure organized as frames. Broadcast-derived; action/person tracks. | Official instructions require a signed release agreement sent to the authors. No agreement or email sent. | No ball trajectory ground truth established. Purposeful filtering limits full-broadcast diversity. |
| [SAM / NUST-NBA181](https://ruiyan1995.github.io/SAM.html) and [WASB](https://github.com/nttcom/WASB-SBDT) | Original source: 181 games, 9,172 six-second clips, 72 images/clip at declared 12 fps, 1920×1080, approximately 135 GB. WASB annotates only a subset. | Current SAM page 404; historical official page says academic request due to copyright. WASB extra annotation ZIP is discoverable on Drive; that does not provide source images. | Only route here with relevant released WASB NBA ball annotations, but high pretraining-overlap risk and media-access friction. |
| [MultiSports / SportsAction](https://huggingface.co/datasets/MCG-NJU/SportsAction) | 3,200 action clips across four sports; 800 basketball clips. Current basketball archive 15,545,866,240 bytes. | Public metadata works; actual basketball archive HEAD returns **401 GatedRepo**. Agreement/login needed. | Human action boxes, no ball labels. Basketball mixes leagues/genders; do not label all of it NBA. Short clips, not source full games. |
| [SportsHHI](https://huggingface.co/datasets/MCG-NJU/SportsHHI) | 160 MultiSports-derived clips, 80 basketball; average 603 frames at 25 fps, 720p. `frames.zip` 23,985,057,701 bytes. | HEAD **401 GatedRepo**. | Human interactions and boxes on sampled keyframes; no ball labels. Shares footage with MultiSports, so not independent evidence. |
| [BASKET](https://huggingface.co/datasets/yulupan/BASKET) | 4,477 hours of **player highlight reels**, typically 8–10 min, 21 leagues; seasons 2018–19 to 2022–23. HF currently reports 1.93 TB. | NBA directory metadata works; a listed NBA MP4 HEAD returns **401 GatedRepo**. Contact-sharing agreement required. | Twenty player skill ratings, not ball coordinates. Source full-game footage is not equivalent to released full games. |
| [F-16-NBA](https://huggingface.co/datasets/tsinghua-ee/F-16-NBA) | Caption-train video multipart archive: 55,782,029,305 bytes. Shot-test archive: 14,744,200,878 bytes. Shot-train videos not uploaded. | First 5,242,880,000-byte caption-train part HEAD 200; 64-byte Range 206 with gzip signature. | Event/video-language supervision; no verified ball coordinates. Much less convenient than individual BARD clips. Designated test data remains separate. |
| [NSVA](https://github.com/jackwu502/NSVA) | NBA.com event clips; a collection script builds per-event `videos.nba.com` URLs from date/game/event/UUID metadata. | Official original-data Dropbox landing page HEAD 200; no direct video bytes checked. Features are separate. | Caption/action dataset, not full-game coverage. Collection scripts inspected, not executed. |
| [NBA-Identity](https://github.com/Zeyu1226-mt/LLM-IAVC) | Identity-aware event captioning, thousands of NBA clips. | Official repository exposes feature and supplement links; actual RGB-video release was not established. | TimeSformer features are not usable footage. Do not treat a paper's “dataset released” statement as a raw-video download. |
| [BasketEvent](https://github.com/zhangyu2003/BasketEvent) | At least one actual example MP4 in official GitHub, 6,277,476 bytes; annotation examples and event labels. | Example HEAD 200; 64-byte Range 206 with MP4 signature. Full corpus release not established. | SAM3/Qwen-derived trajectories and events include machine-generated supervision; not automatically human ground truth. |
| [Roboflow tutorial clips](https://roboflow.com/blog/identify-basketball-players) | Public Drive folder lists 10 short Celtics–Knicks Game 1 clips, named by quarter/game-clock span. | Official notebook links the folder; ordinary HTTP metadata 200 and filenames recovered. No clip downloaded here. | Tutorial assets, not complete possessions/games or a verified ball-label set. |
| [SpaceJam](https://github.com/simonefrancia/SpaceJam) | 32,560 player examples, each 16 RGB frames plus pose joints. Reports of 15 source full games do not mean released full broadcasts. | Official Drive file link returned **404**. | Tight player clips are unsuitable as a substitute for continuous full-court ball tracking. |
| [Kaggle Gemini NBA Dataset](https://www.kaggle.com/datasets/manjyotsinghkalkat/gemini-nba-dataset) | Uploader says first half of Cavaliers–Warriors, December 25, 2016; listed MP4 1,512,465,489 bytes. | Metadata/file listing 200. Attempted individual-file download HEAD returned 404; file body not verified. | Half a game, no verified ball labels. Uploader GPL3 tag does not establish underlying broadcast rights. |
| [Internet Archive historical game](https://archive.org/details/philadelphia-76ers-vs-memphis-grizzlies-20-11-2002-nba-season-2002-2003-full-game) | User-uploaded Sixers–Grizzlies November 20, 2002; metadata: 6,695.24 seconds, 540×360, 423,042,658 bytes. | Original MP4 HEAD 200 with video/mp4 and byte-range support. No decode here. | Low resolution and unverified completeness/rights make it weaker than Inf-Stream. It is not an NBA-authorized upload merely because metadata says NBA. |

### Important dataset details and limitations

**PL-NBA:** [Baidu media link](https://pan.baidu.com/s/1jlB-cpXSjEnyEbv53gsf-w?pwd=pnba) currently redirects to a Chinese extraction-code interface. This is a reachable gate, not proof of a dead dataset or a successful download. The [annotation ZIP](https://raw.githubusercontent.com/holhouse/PL-NBA-Dataset/main/PL-NBA-JSON.zip) is separately listed. The [paper](https://arxiv.org/abs/2608.19646) and repository currently describe different counts; do not silently choose the larger version. The repository states CC-BY-NC 4.0/noncommercial scientific use.

**FineSports:** the [release agreement](https://github.com/PKU-ICST-MIPL/FineSports_CVPR2024/tree/main/agreement) is an explicit acquisition step, not an assumed approval to contact authors. A web PDF open failed; the GitHub API confirms a 69,388-byte agreement file. The [paper](https://openaccess.thecvf.com/content/CVPR2024/papers/Xu_FineSports_A_Multi-person_Hierarchical_Sports_Video_Dataset_for_Fine-grained_Action_CVPR_2024_paper.pdf) describes filtering to suitable overhead action views, including removing unsuitable cuts/replays. Such a dataset cannot validate robustness to the entire original broadcast by itself.

**WASB / SAM:** the official setup calls for `NBA_data.zip` segments from SAM and separately downloads [basketball annotations](https://drive.google.com/file/d/1eH3n4uB4d8T-YKLRh46SshD0jYqQbnGF/view). The Drive page returns 200 and identifies `basketball_annos.zip`; it was not downloaded. A secondary project incorrectly reported those annotations as unreleased, so its claim was not adopted. The [official setup script](https://raw.githubusercontent.com/nttcom/WASB-SBDT/main/src/setup_scripts/setup_basketball.sh) is the stronger evidence.

The current SAM page was deleted November 6, 2025, according to its own GitHub history. The [preserved official page](https://raw.githubusercontent.com/ruiyan1995/ruiyan1995.github.io/9757967f504b10631144065b568ed2e8bafbcce6/SAM.html) describes the image-sequence corpus and [academic request form](https://forms.gle/tshJV5tZayzqWnvS8); the form was not submitted. Its 12 fps statement pertains to the original SAM release. The [WASB paper](https://arxiv.org/html/2311.05237) leaves cadence unspecified for its adapted basketball subset: 81 annotated games, 3,824 clips/275,328 images, with 70 training games and 11 test games. Do not invent native-video timestamps for image sequences.

**MultiSports/SportsHHI/BASKET:** readable file trees do not bypass or satisfy dataset agreements. All three actual media probes returned authentication/access gates. MultiSports and SportsHHI advertise CC-BY-NC 4.0; BASKET's card advertises Apache 2.0 but also requires accepting conditions and sharing contact details. Preserve the actual conditions separately from generic license tags.

**NSVA:** the [official data README](https://raw.githubusercontent.com/jackwu502/NSVA/main/SportsFormer/data/README.md) explicitly places responsibility for permitted use on users. Its event-URL collection code is useful acquisition evidence, not a tested guarantee of current endpoint reliability or full-game reconstruction. No collection script was run.

**Roboflow:** the [official notebook](https://github.com/roboflow-ai/notebooks/blob/main/notebooks/basketball-ai-how-to-detect-track-and-identify-basketball-players.ipynb) names [this Drive folder](https://drive.google.com/drive/folders/1eDJYqQ77Fytz15tKGdJCMeYSgmoQ-2-H). Directory metadata yielded ten filenames spanning short Q1/Q2 clock intervals. The tutorial describes deliberately short clips with all players initially visible. A bounded 2 MiB notebook read could not parse the complete JSON because large embedded outputs exceeded the cap; a later 64 KiB source-prefix read recovered the download reference without executing anything. No software was installed.

**Archive/Kaggle:** broad archive searches include simulated NBA2K games and user uploads with ambiguous provenance. A Spurs/Pistons/2026 query found no qualifying exact-game file; that is a search result, not proof that none exists. Kaggle's dataset listing also included an unrelated small JSON file whose name resembled a client credential file; it was not opened. The MP4-specific route failed and no whole dataset bundle was requested.

## Explicit non-NBA exclusions

- [DeepSport/DeepSportRadar](https://ispgroup.gitlab.io/code/deepsport/) is valuable for ball annotations but uses French LNB basketball, not NBA. Its [Kaggle Basketball Instants listing](https://www.kaggle.com/datasets/deepsportradar/basketball-instants-dataset) reports 700+ high-resolution images and 6,599,984,284 bytes. Paired images 40 ms apart and fixed multi-camera views are not a continuous broadcast. The dataset card states CC-BY-NC-SA 4.0; code has separate terms. The university acknowledges LNB image rights.
- [Play by Play on Zenodo](https://zenodo.org/records/12698090) provides synthetic player-coordinate material derived from Spanish regional sports footage, not NBA RGB video.
- [MUVS](https://zenodo.org/records/20708683) exposes multiview sports-video routes, but no NBA provenance was established; it is not a substitute for the requirement.
- Figshare searches did not establish a usable NBA video release; results were largely statistics/tables or documents. This was a bounded search, not an exhaustive absence claim.
- TeamTrack, Synergy/DeepSport and generic basketball tracking repositories are not automatically NBA simply because they concern professional basketball. This report does not promote them to NBA candidates without source-game evidence.

## Split integrity and future use

1. **WASB's NBA-pretrained weights create a direct leakage concern for SAM/NUST-NBA181.** Its [basketball config](https://raw.githubusercontent.com/nttcom/WASB-SBDT/main/src/configs/dataset/basketball.yaml) names test game IDs; its [loader](https://raw.githubusercontent.com/nttcom/WASB-SBDT/main/src/datasets/basketball.py) defines training as the complement among available annotated games. The config's 30 source test IDs and paper's 11 annotated test games refer to different source/subset counts. Randomly splitting released frames does not establish unseen-game performance.
2. **BARD's 2024–25 dates offer a useful chronology separation from the original 2023 WASB publication, conditional on using the actual frozen original checkpoint.** Verify checkpoint provenance and game IDs before claiming non-overlap. A similarly named later fine-tuned model could change the answer.
3. **Keep source games together.** Adjacent action clips, alternate encodes, highlights and complete games may duplicate the same footage across BARD, NSVA, F-16-NBA, PL-NBA, Inf-Stream, MultiSports/SportsHHI, or public archives. Game IDs plus source/time metadata and duplicate checks are needed before assigning development/holdout roles.
4. **Do not consume designated benchmark tests for development.** Inf-Stream Eval and F-16 shot-test were inspected only as public metadata/container availability in this research; no labels, frames or model outputs were inspected. Prefer Train media for any next acquisition sample. Existing project sealed holdouts were untouched.
5. **Availability is not ball-tracking quality.** 60 fps short clips, 24 fps re-encoded full games, 25 fps action clips and 12 fps image sequences have different motion information. No dataset's event captions or automated trajectories should be silently promoted to manual ball ground truth.

## Evidence preservation and resources

The original dataset investigation used public page/API metadata, HEAD requests, and bounded byte reads. It made no model, training, evaluation, test-suite, historical review or holdout run, and no signups, agreement acceptance, paid request or external contact. Its original reports and receipts were written only in the ignored research directory, without Git mutations. This chapter and the combined ledger were subsequently integrated into repository documentation.

`access_probes.json` retains attempted URLs, times, method/read caps, observed HTTP status, relevant metadata and prefix hashes, including failures. It records payload bytes explicitly read by the Python probes; web-tool traffic and transport buffering are not measurable from those counters. No complete media file was saved by this subagent. The subsequent complete BARD download and decode are separately attributed rather than concealed in these small-probe totals.

Preserved dead ends include the deleted SAM page, SpaceJam Drive 404, a mistaken WASB setup path, an initial mistaken BASKET directory name, BASKET/MultiSports/SportsHHI gates, an unsuccessful individual Kaggle download route, web-tool PDF/Drive failures, and the capped notebook JSON parse. None has been converted into a success merely because another route worked.

The earlier negative motion comparison, failed OBS capture, already consumed training/evaluation resources, completed earlier reviews, and three still-pending new motion-comparison human reviews remain unchanged. This report addresses footage access only.
