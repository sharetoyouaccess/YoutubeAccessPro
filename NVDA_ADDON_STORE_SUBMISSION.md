# Publishing YoutubeAccessPro to the NVDA Add-on Store - step by step

This folder (`GitHub-Upload/`) is the git repository content. It does **not** contain the built `.nvda-addon` file - that stays as a separate step (a GitHub Release asset, not something committed to git). The built file you already have is:

```
YoutubeAccessPro-2026.07.19.nvda-addon   (in the parent folder, ~111.7 MB)
```

## 1. Create the GitHub repository

1. Sign in to GitHub as **sharetoyouaccess**.
2. Create a new **public** repository named `YoutubeAccessPro` (must be public - the Store needs to be able to review the source).
3. Do not initialize it with a README/license/gitignore on GitHub's side - this folder already has all of that.

## 2. Push this folder's contents

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
2. Tag: `v2026.07.19` (matches the `version` field in `manifest.ini`).
3. Title: `YouTube Access Pro 2026.07.19`.
4. Attach the file `YoutubeAccessPro-2026.07.19.nvda-addon` (the one in the parent folder, not this one) as a release asset by dragging it into the release form. 111 MB is well under GitHub's 2 GB per-file release asset limit, so no Git LFS is needed for this - LFS only matters for files committed to the git history itself, and this file is deliberately never committed.
5. Publish the release.
6. Copy the asset's direct download link. It will look like:
   ```
   https://github.com/sharetoyouaccess/YoutubeAccessPro/releases/download/v2026.07.19/YoutubeAccessPro-2026.07.19.nvda-addon
   ```
   You can get this exact URL by right-clicking the asset link on the release page and copying the link address.

## 4. Submit the add-on to the Store

1. Open the registration form: https://github.com/nvaccess/addon-datastore/issues/new?template=registerAddon.yml
2. Fill it out with:

   | Field | Value |
   |---|---|
   | Download URL | `https://github.com/sharetoyouaccess/YoutubeAccessPro/releases/download/v2026.07.19/YoutubeAccessPro-2026.07.19.nvda-addon` |
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
- **`url` field in `manifest.ini`**: this repo's copy of `manifest.ini` has `url = "https://github.com/sharetoyouaccess/YoutubeAccessPro"` added. The already-built `YoutubeAccessPro-2026.07.19.nvda-addon` in the parent folder does **not** have this field baked in (it predates this change) - the Store doesn't require it, so this isn't a blocker, but if you want the shipped file to match exactly, rebuild it first with `scripts/build_addon.py` (see this repo's `README.md`) before creating the GitHub Release in step 3, using the current production file as `--vendor`.
- You are not required to have a Windows/NVDA machine to complete steps 1-4 above; nothing in this process runs the add-on.
