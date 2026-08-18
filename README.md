# YouTube Access Pro

An [NVDA](https://www.nvaccess.org/) add-on that provides full keyboard-only access to YouTube: search, play, and download videos, playlists, and channels, entirely from NVDA, without needing a browser. (The one exception: currently-live broadcasts open in the default browser instead, since the browser's native YouTube player handles live playback more reliably than the bundled offline media player.)

- Search or paste a link to play/download videos, playlists, or channels directly, including a dedicated search type for currently-live broadcasts
- Full playback shortcuts: play/pause, seek, volume, speed, automatic continuous playback
- Built-in sleep timer
- Personal playlist management
- Subscriptions tab that browses a followed channel's Videos, Shorts, Live, and Playlists the way YouTube itself organizes them
- Download to MP3 or MP4 with selectable quality, auto-sorted into folders by playlist or channel
- Full Thai/English interface, switch instantly with `Ctrl+T`
- Open the window from anywhere with `NVDA+Y`; hear a shortcut summary for the current tab with `Ctrl+F1`

A full user guide with complete shortcut details ships with the add-on (`doc/en/readme.html`, opened from NVDA's Add-ons Manager / Help menu).

## Repository contents

This repository holds the add-on's **source code only**. The large third-party binaries it depends on at runtime (ffmpeg, ffprobe, mpv, youtube-dl — see [Third-party components](#third-party-components) below) are intentionally **not** committed to git, since several of them individually exceed GitHub's 100 MB per-file limit and none of them are this project's own code.

```
globalPlugins/
  init.py            - all add-on logic
  lib/
    fileinput.py       - Python stdlib shim (yt-dlp imports this; not always present in NVDA's Python)
    optparse.py         - Python stdlib shim (same reason)
    yt_dlp/              - bundled yt-dlp library (pure Python, MIT/Unlicense)
manifest.ini          - add-on metadata (name, version, description, changelog, url)
doc/en/readme.html    - full bilingual (Thai/English) user guide
COPYING.txt           - this add-on's own license (GPL v2)
THIRD_PARTY_NOTICES.txt - licenses of bundled third-party binaries
dev-tests/            - mock-based automated test suite (no NVDA/Windows needed to run it)
scripts/build_addon.py - assembles a distributable .nvda-addon from this source tree
```

## Building the .nvda-addon package

The packaged `.nvda-addon` file NVDA actually loads also needs the third-party binaries below, which live only in `globalPlugins/lib/ffmpeg/` and `globalPlugins/lib/mpv/` inside a built package, never in this git history.

`scripts/build_addon.py` builds a new `.nvda-addon` by taking those binaries from an existing, already-verified-working `.nvda-addon` build (the "vendor source") and overlaying this repository's source files (`globalPlugins/init.py`, `manifest.ini`, `doc/en/readme.html`, `COPYING.txt`, `THIRD_PARTY_NOTICES.txt`, and the `globalPlugins/lib/yt_dlp` / `fileinput.py` / `optparse.py` tree) on top. See the comments at the top of that script for why it works this way instead of re-downloading the binaries from the internet on every build.

```
python3 scripts/build_addon.py --vendor path/to/YoutubeAccessPro-2026.07.19.nvda-addon --out YoutubeAccessPro-2026.07.19.nvda-addon
```

Run the automated test suite first (no NVDA/Windows required):

```
cd dev-tests
python3 test_addon_logic.py
```

## Third-party components

Bundled at runtime in `globalPlugins/lib/` of the built `.nvda-addon` (not in this repository):

| Component | Version | License | Source |
|---|---|---|---|
| yt-dlp | 2026.08.17.073947.dev0 (pre-release) | Unlicense (public domain) | https://github.com/yt-dlp/yt-dlp |
| ffmpeg / ffprobe | "essentials" build, gyan.dev, git 2025-08-25 | GPL v3+ | https://www.gyan.dev/ffmpeg/builds/ / https://ffmpeg.org |
| mpv | 0.28.0 | LGPL | https://mpv.io |
| youtube-dl | (bundled with the mpv build above) | Unlicense (public domain) | https://github.com/ytdl-org/youtube-dl |
| d3dcompiler_43.dll | - | Microsoft redistributable | DirectX End-User Runtime |

Full details, including exactly why each one is needed, are in `THIRD_PARTY_NOTICES.txt`.

## License

This add-on's own source code is released under the GNU General Public License v2 (or later), as required for all NVDA add-ons. See `LICENSE` / `COPYING.txt`.

Bundled third-party binaries remain under their own upstream licenses (see above) - redistributing them alongside this add-on does not change the license of this add-on's own code.

## Author

Peem Narkkhwan <sharetoyouaccess@gmail.com>
