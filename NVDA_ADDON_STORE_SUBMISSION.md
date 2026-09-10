# Publishing YoutubeAccessPro to the NVDA Add-on Store - step by step

This folder (`GitHub-Upload/`) is the git repository content. It does **not** contain the built `.nvda-addon` file - that stays as a separate step (a GitHub Release asset, not something committed to git). The current built file is:

```
YoutubeAccessPro-2026.09.11.nvda-addon   (in the parent folder, ~111.7 MB)
```

**Current publishing status** (read this before following the steps below):

- The GitHub repo is public and has **five commits pushed to `origin/main`** so far:
  - `b3d68b0` - initial `v2026.07.19` source release
  - `5665e71` - `v2026.08.18` (yt-dlp update, live-broadcast/browser-opening behavior, Live search type)
  - `454b3d2` - `v2026.08.20` (yt-dlp updater checks every startup, self-diagnostic warning if an update doesn't take effect, bundled yt-dlp bumped to 2026.08.19)
  - `d0eb41e` - `v2026.08.25` (fixed MP4 downloads failing by muxing best video + best audio streams)
  - `cb7a774` - `v2026.09.02` (confirmed NVDA 2026.2 compatibility, bumped lastTestedNVDAVersion)

  **A sixth commit for this `2026.09.11` build has NOT been made or pushed yet** - the working tree here has real uncommitted changes beyond `cb7a774`:
  - Fixed every way of playing a playlist (saved playlists, one opened from search results, one opened from a followed channel) announcing "Playback ended" instead of playing - the root cause was mpv's own ancient bundled `youtube-dl.exe` helper failing to resolve raw YouTube URLs handed to it via mpv's `ytdl_hook`. Playlists are now resolved through this add-on's own bundled yt-dlp instead. Fixed replaying the last item (Shift+F7) afterward too.
  - **Follow-up fix, found after a user reported it on a large playlist**: the fix above initially resolved every item in a playlist up front before starting playback, which made a playlist with many items (or one opened from search results) take a very long time to actually start playing. Now only the first playable item is resolved before playback starts - as fast as playing a single video - and the rest of the playlist is resolved one item at a time as it's reached, the same reliable way F9/F10 already worked. The playlist still plays straight through automatically, the same as before.
  - Moved saved settings, playlists, and subscriptions out of this add-on's own installed folder (which NVDA's installer replaces on every update) into NVDA's own per-user config folder, so they survive add-on updates and reinstalls. A best-effort migration copies data left behind by an older version the first time this runs.
  - Added Shorts as a fifth Search and Download search type (Video/Playlist/Channel/Live/Shorts), fixed it initially returning no results, and fixed the search type dropdown occasionally losing Live (and Shorts) after switching interface language with Control+T.
  - Corrected the Control+F1 shortcut-summary help text on the Search and Download and Playlists tabs, which had fallen out of date.
  - A followed channel's own playlists (Subscriptions tab -> a channel -> Playlists -> one playlist) are now recognized as real playlists the same way saved playlists (Playlists tab) and a playlist opened from Search and Download's own results already are - playing a video from inside one is resolved through this add-on's own yt-dlp the same way, and toggle play/stop detection and Shift+F7's "replay the last item" now recognize it correctly too. Previously it played like a plain single video with none of that.
  - **"Automatically play the next item when the current one ends" now applies consistently everywhere**, at the user's explicit request: turned on, every kind of list continues on its own to the next item when the current one ends - search results, a followed channel's lists, and every kind of playlist alike. Turned off, nothing continues automatically, not even a real playlist - only the item you actually selected plays, then stops (manually moving with F9/F10 still always works either way). Previously a real playlist always continued regardless of this setting, which the user found inconsistent with how they wanted the setting to behave.
  - Export subscriptions / Import subscriptions are no longer grouped on the Settings tab - they are now their own buttons directly on the Subscriptions tab (reached by pressing Tab from the channel list). Export playlists / Import playlists are a new equivalent feature, added as their own buttons directly on the Playlists tab (reached by pressing Tab from the playlist list) - this is a new bulk backup/restore for every saved playlist at once, alongside the existing per-playlist "Save as .m3u" export.

  All dev-tests pass: **129/129** (`cd dev-tests && python3 test_addon_logic.py`).

  **User has smoke-tested the build up through the search-type/Control+F1 fixes on a real machine and confirmed it working**, including the playlist playback fixes (no more "Playback ended", and playlists now start quickly even with many items) and Shorts search. Everything from "A followed channel's own playlists..." onward above has not yet been smoke-tested on a real machine - do that before submitting, specifically: with the setting OFF, that a real playlist (saved, from search results, or from a followed channel) now plays only the selected item and stops instead of continuing on its own; with the setting ON, that a plain list (search results, a channel's Videos/Shorts/Live) now continues automatically the same as a playlist does; that the Export/Import subscriptions buttons on the Subscriptions tab and the new Export/Import playlists buttons on the Playlists tab actually open a file picker and round-trip a file correctly. Also still worth double-checking from before: that an *existing* install's playlists/subscriptions/settings actually carried over after updating to this version from an older one (the migration can only run once the new code is already active - see the code comments on `_migrate_legacy_data_files()` for the one update this cannot help with), and that the search type dropdown still shows Live/Shorts correctly after switching language.

  Commit and push once ready:
  ```
  git add .
  git commit -m "2026.09.11: fix playlists sending raw urls through mpv's ytdl_hook (Playback ended bug) and fix replay-last-item afterward, fix playlists taking a long time to start playing on large lists, move saved settings/playlists/subscriptions outside the add-on's own folder so updates no longer erase them, add Shorts search type, fix search-type dropdown losing Live/Shorts after language switch, correct Control+F1 help text, recognize a followed channel's own playlists as real playlists, make Automatically play the next item apply consistently to every kind of list including playlists, move Export/Import subscriptions onto the Subscriptions tab and add a new Export/Import playlists feature on the Playlists tab"
  git push origin main
  ```
- GitHub Releases that already exist: `v2026.07.19`, `v2026.08.18`, `v2026.08.20`, `v2026.08.25`, and `v2026.09.02` (all published, all with their `.nvda-addon` asset attached correctly). Leave all five in place as history - **do not edit or delete them.** This round will become the sixth: `v2026.09.11`.
- NVDA Add-on Store submissions filed so far:
  - **issue #10320** - original `v2026.07.19` submission (this add-on's name and `sharetoyouaccess` as a submitter were approved from this one)
  - **issue #10897** - the `v2026.08.18` update (hit the same VirIT/Win95.Marburg VirusTotal false positive as the first submission; non-blocking historically)
  - **issue #10940** - the `v2026.08.20` update (submitted and pushed through)
  - **issue #11101** - the `v2026.08.25` update (submitted; last checked it was still open/unmerged - check current status before assuming it has merged; this is expected to resolve on its own and does not block anything newer)
  - **issue #11309** - the `v2026.09.02` update (submitted, merged - confirmed live in the Store's data source)

  **A new issue for the `v2026.09.11` update has NOT been filed yet.** File it only after the release below exists. Submitting it does not require `v2026.08.25`'s submission (#11101) to have merged first - each version is its own independent PR against a new dated JSON file, not a replacement of the previous one.

## 1. Create the GitHub repository

(Already done - skip this. Only relevant if starting this add-on's Store presence completely from scratch on a different repository.)

## 2. Push this folder's contents

(Already done for the first five versions - see the status note above. For this and future updates, just commit and push as shown in that note.)

Because `globalPlugins/lib/ffmpeg/` and `globalPlugins/lib/mpv/` are never copied into this folder (see `.gitignore` and the README's "Repository contents" section), each push stays small and won't hit GitHub's 100 MB per-file limit.

## 3. Create a GitHub Release and attach the built .nvda-addon

1. On the repo page, go to **Releases -> Draft a new release**.
2. Tag: `v2026.09.11` (matches the `version` field in `manifest.ini`). Leave the existing `v2026.07.19`, `v2026.08.18`, `v2026.08.20`, `v2026.08.25`, and `v2026.09.02` releases/tags in place as history - create this as a new, separate release, not an edit of any of those.
3. **Before creating the tag**, make sure "Target" is set to `main` and that the `2026.09.11` commit (step above) has actually been pushed - creating a version-named tag against stale source would be misleading.
4. Title: `YouTube Access Pro 2026.09.11`.
5. Attach the file `YoutubeAccessPro-2026.09.11.nvda-addon` (the one in the parent folder, not this one - and make sure it is the latest build, not an earlier same-named or differently-named build from an older round; see this repo's `DEV_NOTES.md` for the round history if unsure which file is current) as a release asset by dragging it into the release form. 111 MB is well under GitHub's 2 GB per-file release asset limit, so no Git LFS is needed for this - LFS only matters for files committed to the git history itself, and this file is deliberately never committed.
6. Publish the release.
7. Copy the asset's direct download link. It will look like:
   ```
   https://github.com/sharetoyouaccess/YoutubeAccessPro/releases/download/v2026.09.11/YoutubeAccessPro-2026.09.11.nvda-addon
   ```
   You can get this exact URL by right-clicking the asset link on the release page and copying the link address.

## 4. Submit the add-on update to the Store

This add-on's name and submitter status are already approved (see the status note above), so this is a routine update, not a first-time registration - it still goes through the same `registerAddon.yml` issue form, which auto-generates a pull request adding a new dated JSON file (this time `addons/YoutubeAccessPro/2026.9.11.json`) rather than needing any manual reviewer approval step.

1. Open the registration form: https://github.com/nvaccess/addon-datastore/issues/new?template=registerAddon.yml
2. Fill it out with:

   | Field | Value |
   |---|---|
   | Download URL | `https://github.com/sharetoyouaccess/YoutubeAccessPro/releases/download/v2026.09.11/YoutubeAccessPro-2026.09.11.nvda-addon` |
   | Source URL | `https://github.com/sharetoyouaccess/YoutubeAccessPro` |
   | Publisher | `Peem Narkkhwan` (or your preferred public name) |
   | Channel | `stable` |
   | License Name | `GPL v2` (form default) |
   | License URL | `https://www.gnu.org/licenses/gpl-2.0.html` (form default) |

3. Submit the issue. This auto-generates a pull request against `nvaccess/addon-datastore`. A "potential duplicates" warning pointing at earlier submissions (e.g. #11101, #11309) is expected and not a problem - dismiss it and submit anyway.
4. Automated checks run against the pull request (VirusTotal scan of the binary, manifest validation, URL validation, CodeQL). If the same VirIT/Marburg false positive shows up again (it did for several prior submissions), that alone should not block a routine update the way it can gate a first-time submitter approval - but it's still worth watching the issue for an actual NV Access comment either way.
5. Once checks pass (or a reviewer clears the false positive), the pull request merges automatically and the add-on updates in the Store. You can confirm this yourself once the PR shows "Merged" by fetching `https://raw.githubusercontent.com/nvaccess/addon-datastore/master/addons/YoutubeAccessPro/2026.9.11.json` - if that returns the submitted data, it is live in the Store's data source (the Store client app or web listing may lag a little behind that).

## Things worth double-checking before you submit

- **`minimumNVDAVersion` / `lastTestedNVDAVersion`**: `2025.3` and `2026.2` in `manifest.ini`, unchanged since the `2026.09.02` release. Both values are confirmed present in the Store's `nvdaAPIVersions.json` (https://github.com/nvaccess/addon-datastore/blob/master/transform/nvdaAPIVersions.json) as of the last check - re-verify if either value changes again in the future.
- **`url` field in `manifest.ini`**: present (`url = "https://github.com/sharetoyouaccess/YoutubeAccessPro"`) and baked into every build produced by `scripts/build_addon.py` from round 21 onward, including this `2026.09.11` file.
- **Real-machine testing**: this `2026.09.11` build has real behavior changes - see the status note above for what has already been confirmed working and the one migration edge case still worth a specific look before publishing.
