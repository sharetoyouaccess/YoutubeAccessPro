# YouTube Pro Downloader — Logic Test Suite

Mock-based tests for `globalPlugins/init.py` that run on any machine with
plain Python 3 — no NVDA, no wxPython, no Windows required. This is a dev
artifact, not part of the shipped `.nvda-addon` file.

## Why this exists

Every fix made to this add-on across rounds 9–11 of its development was
verified by reading the code by hand, because nothing about it could
actually be run and checked outside of a real NVDA/Windows session. This
suite covers the slice of the code that genuinely does not need wx/NVDA to
execute — URL normalization, folder-name sanitization, settings merging,
and the playlist-cache key logic — so that slice can be checked
automatically from now on instead of by inspection alone.

It intentionally does **not** try to test any `wx.Panel`-derived class
(the four tab classes) or `GlobalPlugin` itself — convincingly mocking a
real UI toolkit and NVDA runtime well enough to trust the result is exactly
the kind of "verified without ever really running it" risk this project
has been burned by before (see `MainWindow.catch_key`'s history of
silently-broken key routing). Those still need a real, live test pass on
actual NVDA/Windows, which nothing here replaces.

## Running

```
python3 test_addon_logic.py
```

No third-party test framework needed (plain `assert`/print style, matching
the existing test harness used for the GhostReader add-on). Exits non-zero
if anything fails.

This folder finds `globalPlugins/init.py` to test automatically, in order:
1. the `YTDLP_ADDON_INIT_PY` environment variable, if set to an explicit path;
2. a sibling `../only4/globalPlugins/init.py` (the dev source-tree layout);
3. any `*.nvda-addon` file sitting next to this folder - the layout you
   have if this was delivered alongside the built add-on file, in which
   case `init.py` is extracted straight from inside the zip.

## What's covered

- `_normalize_playlist_url`, `_channel_videos_tab_url`, `_is_playlist_id_candidate`
- `_channel_shorts_tab_url`, `_channel_live_tab_url`, `_channel_playlists_tab_url` -
  the round-17 sibling helpers used to browse a subscribed channel's Shorts,
  Live, and Playlists sections; also covers switching away from whatever
  tab suffix a stored channel URL already ends in
- `_extract_channel_url` (all of its fallback fields, and the "nothing
  usable" case that shows up to users as "Cannot find channel information
  for this item")
- `_sanitize_folder_name` (Windows-specific rules are forced on via a
  `sys.platform` override during the test, since this suite normally runs
  on Linux and the add-on only ever actually runs on Windows)
- `load_settings()` / `save_settings()` merge behavior — guards against the
  round-7 class of bug where Save silently reset background-only fields
- `normalize_search_limit`
- `request_playlist_items()`'s cache-key isolation between different
  `limit` values for the same URL, and `force_refresh` actually bypassing
  a fresh cache entry — this is a direct regression test for the round-10
  caching bug. It was verified against a deliberately reverted copy of the
  old (URL-only) cache-key logic and confirmed to fail there, so it is
  known to actually catch that bug if it were ever reintroduced.
- `_cleanup_temp_artifacts_for_url`'s `aggressive=True` mode - a
  round-15-follow-up regression test using real temp-directory files,
  confirming a canceled/errored job's own leftover raw file (an ordinary
  extension like `.webm`/`.m4a`, not just `.part`/`.ytdl`/`.temp`/`.tmp`)
  actually gets deleted, that a sibling format's still-active file for the
  same URL is never touched, and that the non-aggressive (success-path)
  default still leaves ordinary tracked files alone

## How the mocking works

`mocks/` contains stand-ins for `wx`, `gui`, `ui`, `tones`,
`globalPluginHandler`, `addonHandler`, `logHandler`, and `yt_dlp`, inserted
at the front of `sys.path` before `globalPlugins/init.py` is imported by
path (via `importlib.util.spec_from_file_location`, under a fresh unique
module name per test so mutable module-level state like the playlist
cache never leaks between tests).

`mocks/wx.py` defines only what's needed for the module to *import*
cleanly (`wx.Frame`/`wx.Panel` as real base classes, `wx.CallAfter`/
`wx.CallLater` running synchronously so background-thread callbacks are
testable) and falls back to a generic dummy object for everything else via
a module-level `__getattr__` — safe because this suite never calls a
method that would actually use a real wx widget or constant.

`mocks/yt_dlp.py` is a fake `YoutubeDL` whose `extract_info()` returns
canned entries set up per-test via `set_fake_playlist(url, entries)`,
instead of hitting the real network.
