# Publishing YoutubeAccessPro to the NVDA Add-on Store - step by step

This folder (`GitHub-Upload/`) is the git repository content. It does **not** contain the built `.nvda-addon` file - that stays as a separate step (a GitHub Release asset, not something committed to git). The current built file is:

```
YoutubeAccessPro-2026.08.18.nvda-addon   (in the parent folder, ~111.7 MB)
```

**Important - repository is out of date with this file as of 2026-08-18**: this folder's git history has exactly one commit (`git log`), `"Initial public source release, v2026.07.19"`, already pushed to `origin/main`. Every fix made since then (the yt-dlp update, the live-broadcast/browser-opening behavior, the Live search type, and this documentation pass) exists only as uncommitted local changes in this working copy - it has **not** been committed or pushed again. If this add-on was already submitted to the NVDA Add-on Store using that first commit, the reviewed/published source does not match what actually ships in the current `.nvda-addon` file. Before relying on this guide for a fresh submission, or if you need the Store listing to reflect the current version, commit and push the current changes first:

```
git add .
git commit -m "2026.08.18: yt-dlp update, live broadcasts open in browser, Live search type"
git push origin main
```

## 1. Create the GitHub repository

(Skip this section if the repository already exists - see the note above; only needed the first time.)

1. Sign in to GitHub as **sharetoyouaccess**.
2. Create a new **public** repository named `YoutubeAccessPro` (must be public - the Store needs to be able to review the source).
3. Do not initialize it with a README/license/gitignore on GitHub's side - this folder already has all of that.

## 2. Push this folder's contents

(Skip this section if the repository already exists - see the note above; only needed the first time. For updates after that, just commit and push as shown in the note above.)

From inside this `GitHub-Upload` folder:

```
git init
git add .
git commit -m "Initial public source release, v2026.07.19"
git branch -M main
git remote add origin https://github.com/sharetoyouaccess/YoutubeAccessPro.git
git push -u origin main
```

Because `globalPlugins/lib/ffmpeg/` and `globalPlugins/lib/mpv/` were never copied into this folder (see `.gitignore` and the README's "Repository contents" section), this push will be small (~13 MB) and won't hit GitHub's 100 MB per-file limit.

## 3. Create a GitHub Release and attach the built .nvda-addon

1. On the repo page, go to **Releases -> Draft a new release**.
2. Tag: `v2026.08.18` (matches the `version` field in `manifest.ini`). If a `v2026.07.19` release/tag from the first submission already exists, leave it in place as history and create this as a new, separate release rather than editing the old one.
3. Title: `YouTube Access Pro 2026.08.18`.
4. Attach the file `YoutubeAccessPro-2026.08.18.nvda-addon` (the one in the parent folder, not this one - and make sure it is the latest build, not an earlier same-named or differently-named build from an older round; see this repo's `DEV_NOTES.md` for the round history if unsure which file is current) as a release asset by dragging it into the release form. 111 MB is well under GitHub's 2 GB per-file release asset limit, so no Git LFS is needed for this - LFS only matters for files committed to the git history itself, and this file is deliberately never committed.
5. Publish the release.
6. Copy the asset's direct download link. It will look like:
   ```
   https://github.com/sharetoyouaccess/YoutubeAccessPro/releases/download/v2026.08.18/YoutubeAccessPro-2026.08.18.nvda-addon
   ```
   You can get this exact URL by right-clicking the asset link on the release page and copying the link address.

## 4. Submit the add-on to the Store

If this add-on has never been submitted before, follow steps 1-2 below as a new submission. If it was already submitted using the original `v2026.07.19` release and you are updating it to `v2026.08.18`, the Store's update process is different from a first-time registration (typically a pull request against the existing entry in `nvaccess/addon-datastore` rather than the `registerAddon.yml` issue form below, which is for first submissions) - check the current guidance at https://github.com/nvaccess/addon-datastore before proceeding, since this process can change over time.

1. Open the registration form: https://github.com/nvaccess/addon-datastore/issues/new?template=registerAddon.yml
2. Fill it out with:

   | Field | Value |
   |---|---|
   | Download URL | `https://github.com/sharetoyouaccess/YoutubeAccessPro/releases/download/v2026.08.18/YoutubeAccessPro-2026.08.18.nvda-addon` |
   | Source URL | `https://github.com/sharetoyouaccess/YoutubeAccessPro` |
   | Publisher | `Peem Narkkhwan` (or your preferred public name) |
   | Channel | `stable` |
   | License Name | `GPL v2` (form default) |
   | License URL | `https://www.gnu.org/licenses/gpl-2.0.html` (form default) |

3. Submit the issue. This auto-generates a pull request against `nvaccess/addon-datastore`.
4. Since this is the first submission of this add-on, an NV Access reviewer needs to manually approve you as a submitter for it - this can take up to 2 weeks. You don't need to do anything else while waiting.
5. Automated checks then run against the pull request (VirusTotal scan of the binary, manifest validation, URL validation). If anything fails, a comment is added to the issue explaining what - fix it and resubmit the form.
6. Once checks pass, the pull request merges automatically and the add-on appears in the Store.

## Things worth double-checking before you submit

- **Add-on name uniqueness**: `DEV_NOTES.md` records that `name = "YoutubeAccessPro"` was checked against the Store's submitter list on 2026-07-20 with no exact match found. If time has passed since then, it's worth a quick re-check against the current list at https://github.com/nvaccess/addon-datastore/blob/master/submitters.json before submitting, in case someone else registered the same name in the meantime.
- **`minimumNVDAVersion` / `lastTestedNVDAVersion`**: currently `2025.3` and `2026.1` in `manifest.ini`. These must match entries in the Store's `nvdaAPIVersions.json` (https://github.com/nvaccess/addon-datastore/blob/master/transform/nvdaAPIVersions.json). If `lastTestedNVDAVersion` refers to a release that's still in beta/alpha at submission time, the `channel` field must be `beta` or `dev` instead of `stable`.
- **`url` field in `manifest.ini`**: present in this repo's `manifest.ini` (`url = "https://github.com/sharetoyouaccess/YoutubeAccessPro"`) and baked into every build produced by `scripts/build_addon.py` from round 21 onward, including the current `YoutubeAccessPro-2026.08.18.nvda-addon`. Only the very first `YoutubeAccessPro-2026.07.19.nvda-addon` build predates this and lacks it - not relevant if you are submitting/updating with the current file.
- You are not required to have a Windows/NVDA machine to complete steps 1-4 above; nothing in this process runs the add-on.
