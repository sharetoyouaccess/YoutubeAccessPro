# Publishing YoutubeAccessPro to the NVDA Add-on Store - step by step

This folder (`GitHub-Upload/`) is the git repository content. It does **not** contain the built `.nvda-addon` file - that stays as a separate step (a GitHub Release asset, not something committed to git). The current built file is:

```
YoutubeAccessPro-2026.09.10.nvda-addon   (in the parent folder, ~111.7 MB)
```

**Current publishing status as of 2026-09-10** (read this before following the steps below):

- The GitHub repo is public and has **five commits pushed to `origin/main`** so far:
  - `b3d68b0` - initial `v2026.07.19` source release
  - `5665e71` - `v2026.08.18` (yt-dlp update, live-broadcast/browser-opening behavior, Live search type)
  - `454b3d2` - `v2026.08.20` (yt-dlp updater checks every startup, self-diagnostic warning if an update doesn't take effect, bundled yt-dlp bumped to 2026.08.19)
  - `d0eb41e` - `v2026.08.25` (fixed MP4 downloads failing by muxing best video + best audio streams)
  - `cb7a774` - `v2026.09.02` (confirmed NVDA 2026.2 compatibility, bumped lastTestedNVDAVersion)

  **A sixth commit for this `2026.09.10` build has NOT been made or pushed yet** - the working tree here has real uncommitted changes (`git status`) beyond `cb7a774`:
  - **Fixed the real cause of the "Playback ended" bug affecting every way of playing a playlist**, reported after testing a 3-item saved playlist on the Playlists tab: pressing Enter or F7 announced "Playback ended" almost immediately, while F9/F10 played the same items normally, and a second Enter/F7 afterward said "Playing". Root cause: playing a playlist built an m3u file of the raw YouTube webpage URLs and handed it to `start_playback()`, which hardcodes `needs_ytdl_hook=True` for any playlist file - leaving mpv's own built-in `ytdl_hook` script enabled, which falls back to mpv's ancient bundled `youtube-dl.exe` (2017) to resolve each URL itself. That old helper cannot reliably extract current YouTube pages, so mpv exited almost immediately and the watchdog announced "Playback ended" moments later. F9/F10 (`track_next`/`track_prev`) bypass the m3u entirely and resolve a single URL through this add-on's own up-to-date bundled yt-dlp first - exactly why they worked and Enter/F7 did not. Fixed by adding `start_resolved_playlist_playback()`, which resolves every playlist item through this add-on's own yt-dlp up front, builds the m3u from the resolved direct-stream URLs, and disables `ytdl_hook` for it (`needs_ytdl_hook=False`). Initially applied only to `PlaylistTab.play()` (the reported case); **the user then tested the other two places in the code that built a playlist m3u the same way and confirmed the identical failure there too** - opening a YouTube playlist from search results, and opening one from a followed channel's Playlists section (`SearchAndDownloadTab._open_playlist_contents_in_list()`'s auto-play branch and `_play_playlist_from_selection()`) - both were switched to the same fix. While fixing this, also found and fixed a related gap: `state.last_play_request` (used by the global "replay last item" F7/Shift+F7 hotkey) was only ever set by `start_playback()`, which `start_resolved_playlist_playback()` deliberately bypasses - left alone, replaying the last item after playing any playlist would have failed or replayed something stale. `play_last_request()` now recognizes a playlist played this way and re-resolves it fresh instead. Covered by four new dev-tests.
  - **Moved saved settings, playlists, and subscriptions out of this add-on's own installed folder**, in response to a user asking directly whether an update would erase them - it would have: `config.json`/`playlists.json`/`subscriptions.json` used to live under `globalPlugins/` inside the add-on's own installed directory, and NVDA's add-on installer replaces that entire directory when applying an update (confirmed against the NVDA Add-on Development Guide's own recommendation to use `globalVars.appArgs.configPath` for exactly this, and `addonHandler`'s `.pendingInstall` extract-then-replace mechanism). These three files now live under `globalVars.appArgs.configPath/YoutubeAccessPro/` instead, which an update never touches. A best-effort one-time migration copies any data left behind by an older version into the new location if it's still there when this version first runs - **note this cannot protect data through the specific act of updating to this version**, since NVDA typically removes the old installed folder before the new code ever loads; it protects every update from this version onward. A troubleshooting entry was added to the user guide explaining this. Covered by a new dev-test.
  - Added Shorts as a fifth Search and Download search type (Video/Playlist/Channel/Live/Shorts). **Fixed a bug found right after this shipped**: the first version filtered a plain ytsearch pool by duration alone (<= 60 seconds) and returned zero results for every query - the bundled yt-dlp's own YouTube extractor frequently leaves duration unset for a Short in search results (YouTube's search UI doesn't show a duration badge for Shorts), so duration-only filtering silently dropped every genuine Short. Now uses the same signal yt-dlp itself uses to build the channel Shorts tab's URLs - an entry whose url is already .../shorts/<id> (YouTube's own classification) is treated as a Short, with duration kept only as a fallback. Covered by a new dev-test (`test_is_short_entry_prefers_shorts_url_over_duration`).
  - Fixed the search type dropdown silently losing the Live option (and it would have lost Shorts too) after switching interface language with Control+T - `refresh_language()` was rebuilding the dropdown's choice list from an older, shorter hardcoded list than the one built in `__init__`.
  - Corrected the Control+F1 shortcut-summary help text on the Search and Download tab (search type list) and Playlists tab (song list was missing F8/F4/F5), which had fallen out of date.

  All dev-tests pass: **119/119** (`cd dev-tests && python3 test_addon_logic.py`).

  **This build includes real behavior changes. The playlist-playback and Shorts-search fixes have already been smoke-tested by the user on a real machine and confirmed working**: (1) a saved playlist on the Playlists tab plays correctly with Enter and F7 (not "Playback ended"), and F9/F10 still work afterward; (2) opening a YouTube playlist from search results and from a followed channel's Playlists section also play correctly now; (3) searching with the search type set to Shorts returns results. **The settings/playlists/subscriptions storage-location change has NOT been tested on a real NVDA install yet** - before publishing, verify on a real machine that: existing playlists/subscriptions/settings are still there after updating to this version (per the note above, this specific update may not carry them over - check whether they came through, and if not, be ready to recreate them once, after which every future update will preserve them); a brand-new install (no prior version) creates the new storage folder and saves/loads correctly; and the search type dropdown still shows Live/Shorts after switching language with Control+T, and the global "replay last item" hotkey (Shift+F7, or F7 outside a list) still resumes a playlist correctly.

  Commit and push once ready:
  ```
  git add .
  git commit -m "2026.09.10: move saved settings/playlists/subscriptions outside the add-on's own folder so updates no longer erase them, fix all three ways of playing a playlist sending raw urls through mpv's ytdl_hook (Playback ended bug), fix replay-last-item after a playlist plays this way, add Shorts search type, fix search-type dropdown losing Live/Shorts after language switch, correct Control+F1 help text"
  git push origin main
  ```
- GitHub Releases that already exist: `v2026.07.19`, `v2026.08.18`, `v2026.08.20`, `v2026.08.25`, and `v2026.09.02` (all published, all with their `.nvda-addon` asset attached correctly). Leave all five in place as history - **do not edit or delete them.**
- NVDA Add-on Store submissions filed so far:
  - **issue #10320** - original `v2026.07.19` submission (this add-on's name and `sharetoyouaccess` as a submitter were approved from this one)
  - **issue #10897** - the `v2026.08.18` update (hit the same VirIT/Win95.Marburg VirusTotal false positive as the first submission; non-blocking historically)
  - **issue #10940** - the `v2026.08.20` update (submitted and pushed through)
  - **issue #11101** - the `v2026.08.25` update (submitted; last checked it was still open/unmerged - check current status before assuming it has merged; this is expected to resolve on its own and does not block anything newer)
  - **issue #11309** - the `v2026.09.02` update (submitted, merged - confirmed live in the Store's data source)

  **A new issue for the `v2026.09.10` update has NOT been filed yet.** File it only after the release below exists. Submitting it does not require `v2026.08.25`'s submission (#11101) to have merged first - each version is its own independent PR against a new dated JSON file, not a replacement of the previous one.

## 1. Create the GitHub repository

(Already done - skip this. Only relevant if starting this add-on's Store presence completely from scratch on a different repository.)

## 2. Push this folder's contents

(Already done for the first five versions - see the status note above. For this and future updates, just commit and push as shown in that note.)

Because `globalPlugins/lib/ffmpeg/` and `globalPlugins/lib/mpv/` are never copied into this folder (see `.gitignore` and the README's "Repository contents" section), each push stays small and won't hit GitHub's 100 MB per-file limit.

## 3. Create a GitHub Release and attach the built .nvda-addon

1. On the repo page, go to **Releases -> Draft a new release**.
2. Tag: `v2026.09.10` (matches the `version` field in `manifest.ini`). Leave the existing `v2026.07.19`, `v2026.08.18`, `v2026.08.20`, `v2026.08.25`, and `v2026.09.02` releases/tags in place as history - create this as a new, separate release, not an edit of any of those.
3. **Before creating the tag**, make sure "Target" is set to `main` and that the `2026.09.10` commit (step above) has actually been pushed - creating a version-named tag against stale source would be misleading.
4. Title: `YouTube Access Pro 2026.09.10`.
5. Attach the file `YoutubeAccessPro-2026.09.10.nvda-addon` (the one in the parent folder, not this one - and make sure it is the latest build, not an earlier same-named or differently-named build from an older round; see this repo's `DEV_NOTES.md` for the round history if unsure which file is current) as a release asset by dragging it into the release form. 111 MB is well under GitHub's 2 GB per-file release asset limit, so no Git LFS is needed for this - LFS only matters for files committed to the git history itself, and this file is deliberately never committed.
6. Publish the release.
7. Copy the asset's direct download link. It will look like:
   ```
   https://github.com/sharetoyouaccess/YoutubeAccessPro/releases/download/v2026.09.10/YoutubeAccessPro-2026.09.10.nvda-addon
   ```
   You can get this exact URL by right-clicking the asset link on the release page and copying the link address.

## 4. Submit the add-on update to the Store

This add-on's name and submitter status are already approved (see the status note above), so this is a routine update, not a first-time registration - it still goes through the same `registerAddon.yml` issue form, which auto-generates a pull request adding a new dated JSON file (this time `addons/YoutubeAccessPro/2026.9.10.json`) rather than needing any manual reviewer approval step.

1. Open the registration form: https://github.com/nvaccess/addon-datastore/issues/new?template=registerAddon.yml
2. Fill it out with:

   | Field | Value |
   |---|---|
   | Download URL | `https://github.com/sharetoyouaccess/YoutubeAccessPro/releases/download/v2026.09.10/YoutubeAccessPro-2026.09.10.nvda-addon` |
   | Source URL | `https://github.com/sharetoyouaccess/YoutubeAccessPro` |
   | Publisher | `Peem Narkkhwan` (or your preferred public name) |
   | Channel | `stable` |
   | License Name | `GPL v2` (form default) |
   | License URL | `https://www.gnu.org/licenses/gpl-2.0.html` (form default) |

3. Submit the issue. This auto-generates a pull request against `nvaccess/addon-datastore`. A "potential duplicates" warning pointing at earlier submissions (e.g. #11101, #11309) is expected and not a problem - dismiss it and submit anyway.
4. Automated checks run against the pull request (VirusTotal scan of the binary, manifest validation, URL validation, CodeQL). If the same VirIT/Marburg false positive shows up again (it did for several prior submissions), that alone should not block a routine update the way it can gate a first-time submitter approval - but it's still worth watching the issue for an actual NV Access comment either way.
5. Once checks pass (or a reviewer clears the false positive), the pull request merges automatically and the add-on updates in the Store. You can confirm this yourself once the PR shows "Merged" by fetching `https://raw.githubusercontent.com/nvaccess/addon-datastore/master/addons/YoutubeAccessPro/2026.9.10.json` - if that returns the submitted data, it is live in the Store's data source (the Store client app or web listing may lag a little behind that).

## Things worth double-checking before you submit

- **`minimumNVDAVersion` / `lastTestedNVDAVersion`**: `2025.3` and `2026.2` in `manifest.ini`, unchanged since the `2026.09.02` release. Both values are confirmed present in the Store's `nvdaAPIVersions.json` (https://github.com/nvaccess/addon-datastore/blob/master/transform/nvdaAPIVersions.json) as of the last check - re-verify if either value changes again in the future.
- **`url` field in `manifest.ini`**: present (`url = "https://github.com/sharetoyouaccess/YoutubeAccessPro"`) and baked into every build produced by `scripts/build_addon.py` from round 21 onward, including this `2026.09.10` file.
- **Real-machine testing**: unlike the `2026.09.02` release (metadata-only, no code changes), this `2026.09.10` build has real behavior changes, most importantly a real fix (not just hardening) for the Playlists tab Enter/F7 bug - see the status note above for exactly what to smoke-test before publishing.
