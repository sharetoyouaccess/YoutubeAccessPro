# Publishing YoutubeAccessPro to the NVDA Add-on Store - step by step

This folder (`GitHub-Upload/`) is the git repository content. It does **not** contain the built `.nvda-addon` file - that stays as a separate step (a GitHub Release asset, not something committed to git). The current built file is:

```
YoutubeAccessPro-2026.08.20.nvda-addon   (in the parent folder, ~111.7 MB)
```

**Current publishing status as of 2026-08-20** (read this before following the steps below):

- The GitHub repo is public and has **two commits pushed to `origin/main`** so far: the initial `v2026.07.19` source and a second commit for `v2026.08.18` (yt-dlp update, live-broadcast/browser-opening behavior, Live search type). **A third commit for this `2026.08.20` build has NOT been made or pushed yet** - the working tree here has real uncommitted changes (`git status`) beyond that second commit: the yt-dlp auto-updater fix (checks every NVDA startup instead of once/day, plus a self-diagnostic warning if an update doesn't take effect after restart) and a bump of the bundled yt-dlp library itself to 2026.08.19. Commit and push before relying on any of the steps below:
  ```
  git add .
  git commit -m "2026.08.20: yt-dlp updater checks every startup, warns if an update doesn't take effect, bundled yt-dlp bumped to 2026.08.19"
  git push origin main
  ```
- GitHub Releases that already exist: `v2026.07.19` and `v2026.08.18` (both published, both with their `.nvda-addon` asset attached correctly). Leave both in place as history - **do not edit or delete them.**
- NVDA Add-on Store submissions filed so far: **issue #10320** (original `v2026.07.19` submission - this add-on's name and `sharetoyouaccess` as a submitter were already approved from this one) and **issue #10897** (the `v2026.08.18` update - as of the last check, this was still open, blocked on a single VirusTotal engine ("VirIT") flagging the bundle as `Win95.Marburg`, almost certainly a false positive given only 1 of ~74 engines flagged it and the exact same false positive already occurred and was cleared for the `v2026.07.19` submission). **Check the current status of issue #10897 at https://github.com/nvaccess/addon-datastore/issues/10897 before submitting a new `v2026.08.20` update issue** - if #10897 has not merged yet, submitting another update on top of it is likely fine (each submission is its own PR against a new dated JSON file) but worth being aware two updates could be in flight/reviewed at once.

## 1. Create the GitHub repository

(Already done - skip this. Only relevant if starting this add-on's Store presence completely from scratch on a different repository.)

## 2. Push this folder's contents

(Already done for the first two versions - see the status note above. For this and future updates, just commit and push as shown in that note.)

Because `globalPlugins/lib/ffmpeg/` and `globalPlugins/lib/mpv/` are never copied into this folder (see `.gitignore` and the README's "Repository contents" section), each push stays small and won't hit GitHub's 100 MB per-file limit.

## 3. Create a GitHub Release and attach the built .nvda-addon

1. On the repo page, go to **Releases -> Draft a new release**.
2. Tag: `v2026.08.20` (matches the `version` field in `manifest.ini`). Leave the existing `v2026.07.19` and `v2026.08.18` releases/tags in place as history - create this as a new, separate release, not an edit of either of those.
3. **Before creating the tag**, make sure "Target" is set to `main` and that the `2026.08.20` commit (step above) has actually been pushed - creating a version-named tag against stale source would be misleading.
4. Title: `YouTube Access Pro 2026.08.20`.
5. Attach the file `YoutubeAccessPro-2026.08.20.nvda-addon` (the one in the parent folder, not this one - and make sure it is the latest build, not an earlier same-named or differently-named build from an older round; see this repo's `DEV_NOTES.md` for the round history if unsure which file is current) as a release asset by dragging it into the release form. 111 MB is well under GitHub's 2 GB per-file release asset limit, so no Git LFS is needed for this - LFS only matters for files committed to the git history itself, and this file is deliberately never committed.
6. Publish the release.
7. Copy the asset's direct download link. It will look like:
   ```
   https://github.com/sharetoyouaccess/YoutubeAccessPro/releases/download/v2026.08.20/YoutubeAccessPro-2026.08.20.nvda-addon
   ```
   You can get this exact URL by right-clicking the asset link on the release page and copying the link address.

## 4. Submit the add-on update to the Store

This add-on's name and submitter status are already approved (see the status note above), so this is a routine update, not a first-time registration - it still goes through the same `registerAddon.yml` issue form, which auto-generates a pull request adding a new dated JSON file (this time `addons/YoutubeAccessPro/2026.8.20.json`) rather than needing any manual reviewer approval step.

1. Open the registration form: https://github.com/nvaccess/addon-datastore/issues/new?template=registerAddon.yml
2. Fill it out with:

   | Field | Value |
   |---|---|
   | Download URL | `https://github.com/sharetoyouaccess/YoutubeAccessPro/releases/download/v2026.08.20/YoutubeAccessPro-2026.08.20.nvda-addon` |
   | Source URL | `https://github.com/sharetoyouaccess/YoutubeAccessPro` |
   | Publisher | `Peem Narkkhwan` (or your preferred public name) |
   | Channel | `stable` |
   | License Name | `GPL v2` (form default) |
   | License URL | `https://www.gnu.org/licenses/gpl-2.0.html` (form default) |

3. Submit the issue. This auto-generates a pull request against `nvaccess/addon-datastore`.
4. Automated checks run against the pull request (VirusTotal scan of the binary, manifest validation, URL validation). If the same VirIT/Marburg false positive shows up again (it did for both prior submissions), that alone should not block a routine update the way it can gate a first-time submitter approval - but it's still worth watching the issue for an actual NV Access comment either way.
5. Once checks pass (or a reviewer clears the false positive), the pull request merges automatically and the add-on updates in the Store.

## Things worth double-checking before you submit

- **`minimumNVDAVersion` / `lastTestedNVDAVersion`**: currently `2025.3` and `2026.1` in `manifest.ini`, unchanged since the last two submissions (already accepted). These must match entries in the Store's `nvdaAPIVersions.json` (https://github.com/nvaccess/addon-datastore/blob/master/transform/nvdaAPIVersions.json) if either value ever changes.
- **`url` field in `manifest.ini`**: present (`url = "https://github.com/sharetoyouaccess/YoutubeAccessPro"`) and baked into every build produced by `scripts/build_addon.py` from round 21 onward, including this `2026.08.20` file.
- You are not required to have a Windows/NVDA machine to complete steps 1-4 above; nothing in this process runs the add-on.
