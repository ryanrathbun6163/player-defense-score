# NBA footage access: platforms, recorders, professional film services

[Main findings and acquisition plan](nba_footage_access.md) · [Combined source ledger](nba_footage_access_sources.json)

Local receipts mentioned below are under the ignored `data/outputs/t/nba_footage_access_research_2026-10-18/` tree, in this chapter's `unofficial/`, `platforms/`, or `datasets/` directory unless otherwise stated.

Research date: 2026-10-18 (America/Phoenix). This is an evidence report, not a record of successful acquisition.

## Result

The consumer subscription routes inspected here do not establish a working, repeatable local NBA file pipeline. They do reveal two concrete routes worth checking: existing NBA League Pass can now be linked to Prime Video in eligible markets, potentially exposing games to PlayOn's supported Amazon channel; and Synergy documents ordinary full-game file downloads plus scheduled downloading. Neither has been tested with Ryan's account or the exact game. Synergy's current terms expressly restrict dataset/ML use without written permission, so a standard film subscription is not sufficient evidence of suitability.

The exact target is Spurs at Pistons, February 23, 2026, NBA game ID `0022500828`. Ryan's ordinary NBA League Pass browser playback already works. His attempted OBS Chrome Window Capture produced browser UI with a black video region; that failed attempt remains a failure. The existing NFHS `playon_full_game.mp4` is not NBA evidence. These observations come from the complete local handoff, not from new capture tests.

This subtask performed public documentation/search and public GitHub metadata reads only. It did not install software, log into services, change accounts, link subscriptions, buy anything, accept agreements, send inquiries, extract credentials, decrypt DRM, download NBA media, or run models/tests/reviews. The other research lanes cover datasets, official YouTube samples, and unofficial replay sources; their results must be assessed separately rather than inferred from this report.

## Three requirements kept separate

| Requirement | What would satisfy it | What does not establish it |
|---|---|---|
| Representative NBA research footage | Actual usable NBA clips with adequate context and provenance | A dataset's basketball label alone, inaccessible links, or highlights without required possession context |
| Chosen case-study game | Verified playable frames from game `0022500828`, then the required game coverage | Any other Spurs/Pistons game, classic NBA footage, or an event-title match without media inspection |
| Repeatable full-game access | A reproducible source/file procedure across several games, with quality, completeness, access conditions, and costs understood | One cached file, one successful replay, a vendor's generic compatibility claim, or cloud DVR availability |

## Consumer services and broadcasters

### NBA League Pass and Prime Video

NBA's current [Amazon linking help](https://support.watch.nba.com/hc/en-us/articles/34476165179799-Link-your-Amazon-Prime-and-NBA-ID-League-Pass-Subscription?hidenav=true), directly re-opened with an October 15, 2026 update date, permits eligible NBA-direct or Amazon League Pass subscriptions to authenticate on both services. Linking is one NBA ID to one Amazon account; having active subscriptions through both prevents linking. The page lists excluded markets, not including the US. Prime viewing remains restricted to the purchase country, and Amazon exclusives have platform restrictions. **Do not buy a second League Pass subscription merely to investigate this route.** Account linking was not performed.

The concrete unanswered question is whether the existing subscription exposes the February 23 replay in Prime's authenticated catalog and whether PlayOn can enumerate/record that specific NBA add-on item. NBA playback success on nba.com answers neither question. A future authorized catalog check should record the exact title/date/game, available replay duration, feed, and whether it is a normal on-demand listing.

NBA [offline downloads](https://support.watch.nba.com/hc/en-us/articles/24939268210455-Download-for-Offline-Viewing) are a League Pass Premium feature in the mobile/tablet app and expire after 30 days. The documentation includes full and condensed games but no Windows media-file export. Paying for Premium does not, on this evidence, solve local computer-vision input.

NBA's [replay availability help](https://support.watch.nba.com/hc/en-us/articles/360011802673-Full-Game-Replays-and-Condensed-Game-Availability) documents national replay availability the following 6 AM ET and local replays after three days. These timing rules describe playback; they are not export permission or a guarantee that every historical stream is presently in every distributor's catalog. The [blackout guide](https://support.watch.nba.com/hc/en-us/articles/115002481154-League-Pass-Blackout-Guide) distinguishes national and local access. There is no reason to treat a blackout workaround as the access plan for a replay Ryan can already view.

### Peacock: the original broadcaster for this exact game

Peacock's own [February 23 viewing guide](https://www.peacocktv.com/blog/watch-spurs-pistons-jazz-rockets-on-peacock-nba-monday-feb-23) identifies Spurs at Pistons at 7 PM ET as that Monday's Peacock game. This gives a specific second catalog to inspect. It does **not** prove that the February replay remains available in October, that a current subscription includes it, or that PlayOn can record it. The public [NBA hub](https://www.peacocktv.com/sports/nba) primarily exposed current schedules, not a verified historical target replay.

[Peacock offline downloads](https://www.peacocktv.com/help/article/can-i-watch-peacock-content-offline) apply to selected Premium Plus titles on supported mobile/tablet devices. Limits include 25 downloads across the account, 30 days unwatched, and 48 hours after playback begins; titles can leave earlier. No download icon means no offline option. This does not establish NBA replay eligibility or an ordinary transferable MP4. Do not purchase Premium Plus solely on the phrase “offline downloads.”

### YouTube TV, Hulu, cable, ESPN/ABC/NBC

The current [Google League Pass notice](https://support.google.com/youtubetv/answer/9148808?co=GENIE.Platform%3DDesktop&hl=en) says NBA/WNBA League Pass is no longer available on YouTube TV or Primetime Channels and that all League Pass content, including library recordings, became unavailable September 30. The page does not state a year in that sentence. Older advice to subscribe to YouTube TV League Pass and use its DVR is superseded by the current notice. Ordinary nationally televised NBA games are a separate channel-rights question.

[YouTube TV DVR help](https://support.google.com/youtubetv/answer/7129564?hl=en-NE) concerns adding currently airing/upcoming programs to a cloud library. It does not establish a retrospective copy of the chosen game or portable file export. [Hulu's current offline help](https://help.hulu.com/article/hulu-downloads) limits downloads to eligible streaming-library titles on supported mobile devices, excludes premium add-ons and extra Live TV on-demand content, and excludes computer downloads. [Hulu + Live TV](https://www.hulu.com/live-tv) advertises cloud DVR retention up to nine months, not ordinary exported files. A new subscription cannot recreate a recording that was never made.

NBA lists [US TV-provider partners](https://support.watch.nba.com/hc/en-us/articles/16847553816087-US-TV-Provider-Partners), including traditional cable/satellite and streaming distributors. Provider authentication establishes viewing eligibility, not DVR file portability. Provider-specific DRM, retention, supported devices, and historical catalog need separate checking. Prime, Peacock/NBC, ESPN/ABC and local channels distribute different schedules; no single broadcaster subscription is established here as a complete NBA file source. The exact February 23 game was Peacock, so an ESPN-only or future NBC-over-the-air workflow would be a scope change.

## Recording and downloader products

### PlayOn: a real MP4 mechanism, with the NBA step still missing

Current [PlayOn channel listings](https://www.playon.tv/whats-on) include Prime Video and Peacock but no standalone NBA channel. Its old FAQ still mentions NBA, Fox Soccer and NFL Game Rewind in a live-sports answer; that stale paragraph is not evidence of current standalone NBA support.

[PlayOn Cloud documentation](https://www.playon.tv/cloud) describes playback on a virtual PC, recording in real time, and downloading an MP4 to a computer. It lists SD, HD and 1080p options, seven days of complimentary cloud retention, and manual or scheduled local downloading. This is a genuine portable-file product description, not an app-only download. It remains a vendor claim for supported content, not a tested NBA result.

[PlayOn Home's current features](https://www.playon.tv/features) describe a Windows recording app, scheduling, and series subscriptions. NBA games may not be represented as episodes; automatic game coverage is unverified. [The FAQ](https://www.playon.tv/faq?tab=cloud) says Home Free is limited to ad-supported SD; paid Home enables HD/FHD and other features. The unsupported old PlayOn Desktop product should not be confused with Home. Cloud uses one credit for SD/720p or three for 1080p; a Cloud recording cannot be cancelled after it starts. Therefore do not promise a cancellable 30-second Cloud trial. A vendor-provided short demonstration or a small supported item can establish basic output, but only the actual NBA item establishes NBA compatibility.

At retrieval, the [Cloud credit store](https://www.playon.tv/offers/cloud/) offered 50 credits for $7.50 and a promotional 300 for $34.99. At the 50-credit rate, one 1080p recording uses $0.45 of credits, **if** a full game is one supported item; initial purchase, streaming subscription and bandwidth are additional. A current Home price did not appear in the parsed [Home plan page](https://www.playon.tv/offers/upgrade/), so no price is invented. Recording a full replay consumes approximately its playback duration; downstream file downloading adds transfer time.

A [December 2025 PlayOn user discussion](https://www.reddit.com/r/PlayOn/comments/1pfie7u/any_idea_where_amazon_channels_went/) reports missing/partial Amazon channel navigation and search workarounds, plus poor-size recordings in some cases. This is unverified first-person evidence of catalog/rendering fragility, not NBA success. Before spending on a plan, the exact unresolved checks are: NBA add-on enumeration, target replay presence, complete video rendering, real frame cadence and output resolution, and the availability of a second and third game. Generic Amazon support is insufficient.

### Audials and Replay Video Capture

[Audials' recorder guide](https://audials.com/how-to/en/how-to-record-videos-from-any-video-streaming-service/) lists several streaming services and a generic source recorder. Its [video-recording product page](https://audials.com/en/i-want-to/record-films) advertises standard media formats and frame-rate handling. [Replay Video Capture](https://applian.com/replay-video-capture/) advertises browser/tab and screen recording. These are vendor claims about broad recording capability; no current primary NBA-specific success or exact-game export was found. A refund promise or generic “record what you watch” slogan is not a technical test. Neither was installed or tried.

### StreamFab, KeepStreams, FlixPal and similar downloaders

[StreamFab Amazon Downloader](https://streamfab.com/amazon-downloader.htm) advertises Prime/add-on downloads to MP4/MKV and a limited trial. Its quoted marketing prices at retrieval were $54.99/month or $99.99 lifetime; this is a snapshot, not a recommendation to purchase. Its [Peacock product page](https://streamfab.com/peacock-downloader.htm) markets high-resolution local files, but the same vendor's [Peacock limitations article](https://streamfab.com/peacock-download-options-explained) limits support to on-demand content rather than live/linear channels. A replay must exist as supported VOD first. Some product text had stale Peacock prices and inconsistent trial claims, reducing confidence in generic copy.

The most specific practical report found was [a January 19, 2026 DVDFab forum thread](https://forum.dvdfab.cn/d/470727-cant-download-from-nba-league-pass-by-amazon): a user says League Pass games through Amazon downloaded weeks earlier, then stopped triggering download analysis. The retrieved discussion did not establish a resolution. This supports historical possibility and fragility, not present compatibility. [Release notes](https://streamfab.com/downloader-new.htm) describe general Amazon/Peacock fixes but do not verify this NBA case.

StreamFab's [own technical explanation](https://streamfab.com/user-guide/top-questions.htm) describes DRM decryption in its download mode. No DRM decryption was attempted; this route was investigated through public documentation. [KeepStreams Amazon](https://keepstreams.com/amazon-prime-downloader) and [FlixPal Peacock](https://flixpal.us/peacock-downloader) likewise advertise local export products, but no independent current NBA-specific success was established. Their presence in a search result is not a substitute for exact-game support, current compatibility, or a verified file.

## OBS, Windows capture and HDMI hardware

Ryan's recorded evidence is specific: NBA browser playback works, while OBS Chrome Window Capture showed a black video region. It does not prove that every browser/API/source combination fails, but it rules out claiming the attempted setup succeeded. Preserve that evidence rather than cycling through arbitrary settings without a new hypothesis.

[Microsoft's Desktop Duplication structure documentation](https://learn.microsoft.com/en-us/windows/win32/api/dxgi1_2/ns-dxgi1_2-dxgi_outdupl_frame_info) explicitly includes a protected-content-masked flag and explains that protected pixels may already be blacked out. That establishes a real capture limitation; simply switching from Window Capture to Display Capture is not a guaranteed solution. [OBS forum reports](https://obsproject.com/forum/threads/black-video-drm.150404/) and a [2023 League Pass user report](https://www.reddit.com/r/nba/comments/10zedko) describe browser-dependent outcomes, including old Firefox successes. These are historical anecdotes, not evidence that current NBA playback will record today. A bounded ordinary supported-browser compatibility test could be considered later, with explicit success/failure evidence; none was performed here.

[Elgato's HDCP documentation](https://help.elgato.com/hc/en-us/articles/360040482032-HDCP-and-Elgato-Game-Capture-devices) states that protected HDMI cannot be recorded by its capture devices. [Its PlayStation guidance](https://help.elgato.com/hc/en-us/articles/360028236371-Turn-off-HDCP-to-use-PlayStation-4-with-Elgato-Game-Capture-HD60-S) distinguishes unprotected gameplay from protected media apps. A Fire TV/console and capture card are therefore not an evidence-backed fix for NBA streaming. No capture-card purchase or HDCP-removal hardware is proposed.

Filming a display with a camera would create a recording of visible pixels but adds perspective, refresh/shutter aliasing, glare and compression, and is not an established quality input for this project. This is an engineering inference, not a tested workaround. It should not displace a direct file route without a deliberate quality tradeoff.

## Future broadcast recording: practical, but a different requirement

An antenna plus compatible tuner can produce local recordings of future unencrypted broadcasts. [Plex's official DVR FAQ](https://support.plex.tv/articles/226463767-frequently-asked-questions-dvr-live-tv/) requires a tuner/antenna and Plex Pass for recording and excludes DRM channels. [Silicondust](https://www.silicondust.com/hdhomerun/) lists tuners from $109.99 to $199.99, local USB/PC/NAS recording, and restrictions on encrypted ATSC 3.0 channels. These are hardware-only snapshots; antenna, storage and software costs are extra. [Its Windows DVR instructions](https://info.hdhomerun.com/info/dvr%3Awindows) describe local disk storage and estimate roughly 6 GB/hour for HD broadcasts.

This could provide repeatable files for selected future ABC/NBC or locally televised games, subject to Ryan's actual reception and rights schedule. It cannot retroactively supply the February Peacock game and does not cover every NBA game. A future inquiry should name actual receivable channels and games before buying hardware. CableCARD/TV Everywhere and IPTV tools inherit channel authorization and encryption constraints; no generic claim of access to all NBA footage is justified.

## Open-source tools: names are not working League Pass support

The public [yt-dlp NBA classic-game issue #6042](https://github.com/yt-dlp/yt-dlp/issues/6042) remains open and is labeled DRM. Existing [youtube-dl NBA extractor code](https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/nba.py) contains older highlight/team cases, not proof of current League Pass full-game acquisition.

Public GitHub repository metadata was inspected without cloning or executing software. Results included:

| Repository | What it actually represents | Recency observed |
|---|---|---|
| [solyst/NBA-Downloader](https://github.com/solyst/NBA-Downloader) | Play-by-play/data tooling | Last push April 2018 |
| [devd-99/nba_downloader](https://github.com/devd-99/nba_downloader) | Play/event-oriented video tooling | Last push April 2024 |
| [yo1995/Ultimate-NBA-Downloader](https://github.com/yo1995/Ultimate-NBA-Downloader) | Photo collection, not full-game film | Archived, last push September 2018 |
| [maxgalbu/xbmc.plugin.video.nba](https://github.com/maxgalbu/xbmc.plugin.video.nba) | Historical Kodi viewing plugin | Last push December 2020 |
| [russholio/kodi-nba-league-pass](https://github.com/russholio/kodi-nba-league-pass) | Historical Kodi viewing plugin | Last push March 2016 |
| [ozgurkaplan/nba-league-pass-addons](https://github.com/ozgurkaplan/nba-league-pass-addons) | Historical add-on tooling | Last push November 2022 |
| [JGJP/nba-dl](https://github.com/JGJP/nba-dl) | Full-game highlights, not full games | Last push June 2021 |

The [mtthai NBA API client](https://github.com/mtthai/nba-api-client) documents an old event-video method with a later-season limitation. [nba_api VideoEvents](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/videoevents.md) is event video, not a full-game API. Such clips can be useful research sources but do not silently satisfy continuous-possession/full-game needs. The [main report](nba_footage_access.md) records the completed [choucisan/nba_games](https://github.com/choucisan/nba_games) investigation: 189 metadata records were parsed, but example YouTube video retrieval remained unverified.

No maintained, openly documented, tested current NBA League Pass full-game downloader was established in this scope. This is a search result, not a proof that no tool exists anywhere. Old repository timestamps alone do not prove failure; they identify the absence of current compatibility evidence.

## Professional footage services and licensing

### Synergy: strongest documented file workflow, material eligibility/use restriction

Official [Video Express download documentation](https://support.synergysports.com/support/solutions/articles/77000570462-downloading-games) describes selecting season, league, team and game, then raw or Synergy full-game video. Official [local-file instructions](https://support.synergysports.com/support/solutions/articles/77000570464-video-express-for-basketball-how-to-access-downloaded-raw-and-synergy-full-game-video) place downloaded videos under `Documents/Video Express/Download`, in dated away-at-home folders, and describe use for editing. This establishes ordinary accessible video files, unlike consumer app downloads. The inspected article does not establish the exact output codec/container/frame rate for NBA; accepted upload formats must not be misread as export formats.

Separate [scheduling instructions](https://support.synergysports.com/support/solutions/articles/77000570463-scheduling-game-downloads) queue a selected game to download when available and resume interruptions. [Installation documentation](https://support.synergysports.com/support/solutions/articles/77000570453-installation-links-) supports PC and Mac. This is a credible repeatable workflow, conditional on account entitlement and game availability, not an acquisition performed here.

[Current high-school packages](https://sportradar.com/synergy-basketball-for-high-school/?lang=en-us) list NBA/WNBA library access in Pro Film Room (four licenses), with NBA/WNBA add-ons for other bundles, and a twelve-month non-prorated contract. These packages target coaches; the page does not establish Ryan's eligibility as an independent researcher, a current price, inclusion of 2025–26 history, or raw NBA export rights. The FAQ about logging a customer's prior-season games should not be misread as a definitive statement about historical NBA library availability. Historical Reddit prices and competitor comparison pages are not quotes.

The current official [Synergy terms](https://developer.sportradar.com/sportradar-updates/page/synergy-sports-system-and-synergy-sports-portal-terms-of-use), especially section 4.3, restrict automated collection and use of content to build datasets/analytics or train/test ML unless expressly permitted in writing. Section 9 adds AI/IP restrictions. Thus a normal subscription plus a download button is **not** enough to establish authorization for Player Defense Score. The applicable negotiated agreement would need to address this use explicitly; no agreement was accepted or legal determination made here.

The [sales/contact route](https://sportradar.com/contact/?lang=en-us) is live, though the parsed page did not expose a completed specific inquiry form. Support articles list +1 (800) 411-1627. A search-index extract of a [public university procurement record](https://www.procurement.msstate.edu/procurement/bids/245-51.pdf) quoted $18,500 for a broad team database/editing/exchange bundle, but the direct URL subsequently returned 404. Its date was not verified; this is a historical price lead, **not Ryan's likely quote, minimum price or current offer**. No current individual research price was verified. An October 7 [announced sale of Synergy coaching/scouting to Teamworks](https://investors.sportradar.com/news-releases/news-release-details/sportradar-announces-agreement-divestiture-coaching-and-scouting) was an agreement expected to close later, not proof the transfer had completed. Confirm the contracting entity in any quote.

### Hudl Instat / Sportscode

[Hudl's current Instat FAQ](https://www.hudl.com/products/instat/faqs) describes basketball coverage across 900+ competitions, historical data for major leagues, official rights agreements, and integration with Sportscode. It does not identify the target game or explicitly establish NBA full-game export for this account/use. [Sportscode release notes](https://instat.hudl.com/releases/sportscode) describe basketball Instat database integration and downloaded-game handling, including continuous-video improvements. This supports technical film workflows, not a blanket NBA entitlement. Sportscode's desktop requirements and any separate license must be confirmed for Ryan's Windows environment. Current individual price, exact-game coverage, portable raw video, and ML permission remain unanswered. Ask for a sample and scope-specific quote, not a generic demo of tagged clips.

### NBA, broadcaster and archive licensing

[NBA League Pass support](https://support.watch.nba.com/hc/en-us/requests/new?ticket_form_id=114093964473) and the [NBA general contact form](https://contact.nba.com/contact-nba/) provide inquiry channels. Neither page promises a small research footage license. Direct NBA/Peacock or authorized distributor inquiries should explicitly request ordinary files and recurring historical/future game access. Playback troubleshooting alone will not answer the question.

[IMG Video Archive](https://imgvideoarchive.com/solutions) and [Reuters Connect](https://reutersconnect.com/about-us) market professional licensed sports footage. Their existence does not establish complete NBA broadcast rights or the target game. Reuters' [sports offering](https://reutersagency.com/license-sports-visuals-that-move-audiences) and [2026 event calendar](https://reutersagency.com/hubfs/Reuters%20Major%20Sports%20Events%20Calendar%20-%20By%20Sport%20-%202026-1.pdf) distinguish news/highlight coverage from full broadcasts. Archive clips, NBA photographs, and press-conference footage are not full-game substitutes. Pricing and ML use would require a specific quote.

## Official free full-game viewing

NBA's [classic-game help](https://support.watch.nba.com/hc/en-us/articles/28006218859415-Classic-Games-and-Original-NBA-Content?hidenav=true) describes hundreds of games available with an NBA ID, including historical Finals and team selections. This is a source of alternative NBA viewing, not verified export or the chosen 2026 game. The [main report](nba_footage_access.md) records full-game YouTube metadata; example video retrieval remained unverified. A public page containing an HLS URL can also be a press conference or highlight; the NBA MediaDay “play-in games” search result was such a false lead and was not counted as a game source.

### Tencent / Migu regional route

The unofficial-source lane found public Tencent links labeled as the exact game's Mandarin and original-audio full replays, plus separate quarters; see its `unofficial/tencent_exact_game_links.json`. Examples are the [Mandarin full-replay page](https://v.qq.com/x/cover/mzc00200z9n8cnk/u3192rehd0s.html) and [original-audio full-replay page](https://v.qq.com/x/cover/mzc00200z9n8cnk/z4101d4cnwo.html). This subtask's web reader returned internal errors for both; that is a reader failure, not proof of inaccessible playback. The other lane reports HTTP 200 page access, not verified media playback.

NBA's current [China access help](https://support.watch.nba.com/hc/en-us/articles/115000586373-Accessing-NBA-League-Pass-in-China) identifies Tencent Sports and Migu for games and archives in China. A [primary listed-company annual report](https://www1.hkexnews.hk/listedco/listconews/sehk/2025/0423/2025042300432_c.pdf) records Tencent's 2024 renewal through 2027. This makes Tencent a real regional distribution route, but does not establish US access, current authentication requirements or portable file export for Ryan. The [yt-dlp Tencent extractor](https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/tencent.py) exists; its presence does not prove compatibility with these NBA items. No extractor, regional workaround, account login or download was attempted. Given the separately verified exact-game samples, overseas capture/account work is not the immediate next action.

## Next checks, in practical order

1. The [main report](nba_footage_access.md) now incorporates decoded exact-game samples. Follow that source with full acquisition and continuity checking before spending on a speculative new platform. Complete-game coverage and repeatability still need separate evidence.
2. For a consumer fallback, inspect whether Ryan already has the target replay in an eligible Prime/Peacock catalog. NBA-direct-to-Prime linking is a concrete documented option, but requires an account action that was not executed in this research. Keep existing subscription provenance and avoid duplicate billing.
3. Before installing/paying for PlayOn, obtain exact current NBA-through-Amazon or exact Peacock-replay compatibility information, or perform an authorized bounded evaluation with clear cancellation/credit behavior. Do not re-run the already failed Chrome OBS setup merely to resume. Require actual playable local output, not a product-logo match.
4. For a durable licensed source, use the prepared Synergy inquiry below; ask Hudl the same file/coverage/use questions. Only a written answer and representative downloadable sample resolve suitability. A blanket yearly plan should not be bought first.
5. Consider OTA recording only if a deliberate future-games scope is acceptable; it does not solve this historical target.

No labeling or training is recommended on the basis of these vendor claims alone. The three pending motion-comparison human reviews remain pending and all completed work remains completed.

## Prepared inquiries — drafts only, not sent

### Synergy / Hudl

I am an independent software researcher building a transparent basketball computer-vision pipeline, Player Defense Score. I need the complete February 23, 2026 San Antonio Spurs at Detroit Pistons game, NBA ID 0022500828, and a repeatable way to obtain additional complete NBA games. I need actual video files on a Windows PC for local frame decoding, annotation, player/ball tracking, evaluation and potentially model training, rather than app-only offline viewing or isolated tagged highlights.

Can you provide this exact game and confirm whether an individual researcher can obtain an appropriate license? Please identify the package, minimum contract and total price, NBA historical/future coverage, raw/full-game download entitlement, container/codec, resolution/frame rate, camera/feed options, completeness, download limits, and whether file access persists after subscription expiry. Please explicitly address written permission for datasets, derived coordinates/labels, computer-vision evaluation and model training, and any restrictions on publishing research results or showing limited review clips. Before purchase, could you provide an authorized representative sample file and confirm the exact game's availability? I am requesting information only, not accepting a subscription or agreement.

### PlayOn

I already have NBA League Pass and need a normal MP4 of the February 23, 2026 Spurs at Pistons full-game replay, NBA game ID 0022500828. NBA now documents linking an existing NBA-direct League Pass subscription to Amazon Prime Video. Do current PlayOn Home or Cloud versions support NBA League Pass replay items inside Amazon, including linked subscriptions? Alternatively, can they record this game's Peacock replay if it remains in the catalog? Please distinguish current tested support from generic Prime/Peacock support, identify any live-versus-replay limitation, maximum resolution and real frame rate, game-duration limits, and how to evaluate one NBA item before purchasing a plan. I know Cloud recordings cannot be cancelled after starting; please state the expected credits and failure/refund behavior. I am requesting information only.

## Evidence and failure accounting

- Prior failed Chrome/OBS capture, the historical NFHS provenance uncertainty (now resolved in the main report) and absence of a verified NBA file at handoff are preserved; no retrospective success is claimed.
- No new capture attempt or paid download occurred in this subtask. Network use was documentation/search responses and small public GitHub metadata/README requests. Exact aggregate transferred bytes were not metered; do not invent a total.
- Some guessed URLs failed (an initial Peacock article path and a PlayOn Desktop path); corrected official links were found. These were page-lookup failures, not evidence the services or game are unavailable.
- The Mississippi State procurement PDF appeared in search with a price excerpt but returned 404 on direct retrieval; no current quote or date is inferred from it. Both exact Tencent pages returned web-reader internal errors here; the other lane's HTTP 200 page observation is separate.
- Some broad search responses truncated. Conclusions rely on subsequently inspected named primary pages or explicitly limited search/API results, not on unseen output.
- Search-date/cache conflicts occurred on NBA's Amazon help; the direct current page showed October 15, 2026 and takes precedence over an earlier October 7 search snapshot.
- The report does not reproduce paywalled articles, credentials, protected manifests, keys, or video bodies. Public source URLs and concise paraphrases are recorded in the sibling source ledger.
- Every source remains subject to change. A successfully downloaded full game would still require provenance, checksum, duration/quarter coverage, actual decoded frames, dimensions, timestamps/cadence, and dropped/duplicated-frame checks before labeling or model work. That acceptance plan is not a claim such checks ran here.
