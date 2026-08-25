# Publishing YoutubeAccessPro to the NVDA Add-on Store - step by step

This folder (`GitHub-Upload/`) is the git repository content. It does **not** contain the built `.nvda-addon` file - that stays as a separate step (a GitHub Release asset, not something committed to git). The current built file is:

```
YoutubeAccessPro-2026.08.25.nvda-addon   (in the parent folder, ~111.7 MB)
```

**Current publishing status as of 2026-08-25** (read this before following the steps below):

- The GitHub repo is public and has **three commits pushed to `origin/main`** so far:
  - `b3d68b0` - initial `v2026.07.19` source release
  - `5665e71` - `v2026.08.18` (yt-dlp update, live-broadcast/browser-opening behavior, Live search type)
  - `454b3d2` - `v2026.08.20` (yt-dlp updater checks every startup, self-diagnostic warning if an update doesn't take effect, bundled yt-dlp bumped to 2026.08.19)

  **A fourth commit for this `2026.08.25` build has NOT been made or pushed yet** - the working tree here has real uncommitted changes (`git status`) beyond `454b3d2`: the MP4 download fix (format selector now requests best video and best audio separately and muxes them with the bundled ffmpeg, instead of only matching a pre-muxed combined format that YouTube increasingly doesn't offer) plus the matching doc/changelog/version updates. Commit and push before relying on any of the steps below:
  ```
  git add .
  git commit -m "2026.08.25: fix MP4 downloads failing by muxing best video + best audio streams instead of requiring a pre-combined format"
  git push origin main
  ```
- GitHub Releases that already exist: `v2026.07.19`, `v2026.08.18`, and `v2026.08.20` (all published, all with their `.nvda-addon` asset attached correctly). Leave all three in place as history - **do not edit or delete them.**
- NVDA Add-on Store submissions filed so far:
  - **issue #10320** - original `v2026.07.19` submission (this add-on's name and `sharetoyouaccess` as a submitter were approved from this one)
  - **issue #10897** - the `v2026.08.18` update (hit the same VirIT/Win95.Marburg VirusTotal false positive as the first submission; non-blocking historically)
  - **issue #10940** - the `v2026.08.20` update (already submitted and pushed through)

  **A new issue for the `v2026.08.25` update has NOT been filed yet.** File it only after the release below exists.

## 1. Create the GitHub repository

(Already done - skip this. Only relevant if starting this add-on's Store presence completely from scratch on a different repository.)

## 2. Push this folder's contents

(Already done for the first three versions - see the status note above. For this and future updates, just commit and push as shown in that note.)

Because `globalPlugins/lib/ffmpeg/` and `globalPlugins/lib/mpv/` are never copied into this folder (see `.gitignore` and the README's "Repository contents" section), each push stays small and won't hit GitHub's 100 MB per-file limit.

## 3. Create a GitHub Release and attach the built .nvda-addon

1. On the repo page, go to **Releases -> Draft a new release**.
2. Tag: `v2026.08.25` (matches the `version` field in `manifest.ini`). Leave the existing `v2026.07.19`, `v2026.08.18`, and `v2026.08.20` releases/tags in place as history - create this as a new, separate release, not an edit of any of those.
3. **Before creating the tag**, make sure "Target" is set to `main` and that the `2026.08.25` commit (step above) has actually been pushed - creating a version-named tag against stale source would be misleading.
4. Title: `YouTube Access Pro 2026.08.25`.
5. Attach the file `YoutubeAccessPro-2026.08.25.nvda-addon` (the one in the parent folder, not this one - and make sure it is the latest build, not an earlier same-named or differently-named build from an older round; see this repo's `DEV_NOTES.md` for the round history if unsure which file is current) as a release asset by dragging it into the release form. 111 MB is well under GitHub's 2 GB per-file release asset limit, so no Git LFS is needed for this - LFS only matters for files committed to the git history itself, and this file is deliberately never committed.
6. Publish the release.
7. Copy the asset's direct download link. It will look like:
   ```
   https://github.com/sharetoyouaccess/YoutubeAccessPro/releases/download/v2026.08.25/YoutubeAccessPro-2026.08.25.nvda-addon
   ```
   You can get this exact URL by right-clicking the asset link on the release page and copying the link address.

## 4. Submit the add-on update to the Store

This add-on's name and submitter status are already approved (see the status note above), so this is a routine update, not a first-time registration - it still goes through the same `registerAddon.yml` issue form, which auto-generates a pull request adding a new dated JSON file (this time `addons/YoutubeAccessPro/2026.8.25.json`) rather than needing any manual reviewer approval step.

1. Open the registration form: https://github.com/nvaccess/addon-datastore/issues/new?template=registerAddon.yml
2. Fill it out with:

   | Field | Value |
   |---|---|
   | Download URL | `https://github.com/sharetoyouaccess/YoutubeAccessPro/releases/download/v2026.08.25/YoutubeAccessPro-2026.08.25.nvda-addon` |
   | Source URL | `https://github.com/sharetoyouaccess/YoutubeAccessPro` |
   | Publisher | `Peem Narkkhwan` (or your preferred public name) |
   | Channel | `stable` |
   | License Name | `GPL v2` (form default) |
   | License URL | `https://www.gnu.org/licenses/gpl-2.0.html` (form default) |

3. Submit the issue. This auto-generates a pull request against `nvaccess/addon-datastore`.
4. Automated checks run against the pull request (VirusTotal scan of the binary, manifest validation, URL validation). If the same VirIT/Marburg false positive shows up again (it did for all three prior submissions), that alone should not block a routine update the way it can gate a first-time submitter approval - but it's still worth watching the issue for an actual NV Access comment either way.
5. Once checks pass (or a reviewer clears the false positive), the pull request merges automatically and the add-on updates in the Store.

## Things worth double-checking before you submit

- **Do not submit this update until real-machine MP4 download testing has confirmed the fix actually works on a real NVDA install.** This build has not yet been tested outside the development sandbox (which cannot reach YouTube to test downloads directly).
- **`minimumNVDAVersion` / `lastTestedNVDAVersion`**: currently `2025.3` and `2026.1` in `manifest.ini`, unchanged since the last three submissions (already accepted). These must match entries in the Store's `nvdaAPIVersions.json` (https://github.com/nvaccess/addon-datastore/blob/master/transform/nvdaAPIVersions.json) if either value ever changes.
- **`url` field in `manifest.ini`**: present (`url = "https://github.com/sharetoyouaccess/YoutubeAccessPro"`) and baked into every build produced by `scripts/build_addon.py` from round 21 onward, including this `2026.08.25` file.
- You are not required to have a Windows/NVDA machine to complete steps 1-4 above; nothing in this process runs the add-on.
