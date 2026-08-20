"""Mock-based logic tests for YouTube Pro Downloader's globalPlugins/init.py.

These do NOT need NVDA, wxPython, or Windows - they run on any machine
with plain Python 3. That is the whole point: every bug found and fixed
across rounds 9-11 of this add-on's development was verified purely by
reading the code by hand, because nothing in the project could actually be
executed and checked outside of a real NVDA/Windows session. This suite
covers the functions that genuinely do not need wx/NVDA to run (URL
normalization, folder-name sanitization, settings merging, and the
playlist-cache key logic whose bug was the headline fix of round 10), so at
least this slice of the add-on's behavior can be verified automatically on
any machine, including this one.

Run with:  python3 test_addon_logic.py
No third-party test framework is required (matches the plain assert/print
style already used by this project's other test harness, for the
GhostReader add-on, so both are consistent to run).

Scope note: this suite does NOT exercise any wx.Panel-derived class
(SearchAndDownloadTab, PlaylistTab, SubscriptionsTab, SettingsTab,
MainWindow) or the GlobalPlugin class itself - those need a real UI toolkit
and NVDA runtime to behave meaningfully, and mocking them convincingly
enough to be trustworthy is exactly the kind of "verified without ever
running it" risk this project has been burned by before. The mocks/
package here provides just enough of wx/gui/ui/tones/addonHandler/
globalPluginHandler/logHandler/yt_dlp to import init.py and call its plain
functions - see mocks/wx.py's docstring for the design reasoning.
"""

import os
import sys
import glob
import shutil
import tempfile
import threading
import zipfile
import importlib.util
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
MOCKS_DIR = os.path.join(HERE, 'mocks')

if MOCKS_DIR not in sys.path:
    sys.path.insert(0, MOCKS_DIR)


def _find_init_py():
    """Locate globalPlugins/init.py to test against. Tries, in order:

    1. YTDLP_ADDON_INIT_PY environment variable, if set (an explicit path).
    2. The dev source tree layout (../only4/globalPlugins/init.py next to
       this tests/ folder) - what a developer working from the unpacked
       source has.
    3. The public GitHub repo layout (../globalPlugins/init.py next to
       this tests/ folder, i.e. dev-tests/ sitting at the repo root
       alongside globalPlugins/) - what someone gets from cloning
       https://github.com/sharetoyouaccess/YoutubeAccessPro. init.py is
       copied to an isolated temp file (not read in place) because the
       repo checkout has a real globalPlugins/lib/yt_dlp package sitting
       next to it, and init.py inserts that lib/ folder onto sys.path
       ahead of this tests/mocks/ folder - importing it in place would
       make the tests below exercise the real yt-dlp library instead of
       the mocks/yt_dlp.py test double they're written against.
    4. Any *.nvda-addon file sitting next to this tests/ folder - what a
       user has when this folder is delivered alongside the built add-on.
       init.py is extracted from inside the zip to a temp file.

    Raises FileNotFoundError with a clear message if none of these work.
    """
    env_path = os.environ.get('YTDLP_ADDON_INIT_PY')
    if env_path and os.path.isfile(env_path):
        return env_path, None

    dev_path = os.path.normpath(os.path.join(HERE, '..', 'only4', 'globalPlugins', 'init.py'))
    if os.path.isfile(dev_path):
        return dev_path, None

    repo_path = os.path.normpath(os.path.join(HERE, '..', 'globalPlugins', 'init.py'))
    if os.path.isfile(repo_path):
        tmp_dir = tempfile.mkdtemp(prefix='ytdlp_addon_test_src_')
        tmp_path = os.path.join(tmp_dir, 'init.py')
        with open(repo_path, 'rb') as src, open(tmp_path, 'wb') as dst:
            dst.write(src.read())
        return tmp_path, tmp_dir

    parent = os.path.normpath(os.path.join(HERE, '..'))
    # Newest file first (by modification time), not alphabetical - a
    # folder can hold several old builds side by side, and alphabetical
    # order does not reliably match "most recent" for this project's
    # filenames (e.g. a " (Hardened)" suffix sorts before a plain version
    # number because a space sorts before a period).
    candidates = sorted(
        glob.glob(os.path.join(parent, '*.nvda-addon')),
        key=os.path.getmtime,
        reverse=True,
    )
    for addon_zip in candidates:
        try:
            with zipfile.ZipFile(addon_zip) as z:
                data = z.read('globalPlugins/init.py')
        except Exception:
            continue
        tmp_dir = tempfile.mkdtemp(prefix='ytdlp_addon_test_src_')
        tmp_path = os.path.join(tmp_dir, 'init.py')
        with open(tmp_path, 'wb') as f:
            f.write(data)
        return tmp_path, tmp_dir

    raise FileNotFoundError(
        'Could not find globalPlugins/init.py to test. Set the '
        'YTDLP_ADDON_INIT_PY environment variable to its path, run this '
        'from the dev source tree, or place this tests/ folder next to a '
        '*.nvda-addon file.'
    )


INIT_PY_PATH, _INIT_PY_TMP_DIR = _find_init_py()


def _load_addon():
    """Import a fresh copy of init.py under a unique module name, so tests
    that mutate module-level state (the playlist cache, settings file
    paths, sys.platform) never leak into each other."""
    name = f'addon_init_{uuid.uuid4().hex}'
    spec = importlib.util.spec_from_file_location(name, INIT_PY_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_addon_with_temp_storage():
    """Like _load_addon(), but also redirects its settings/playlists/
    subscriptions JSON file paths into a throwaway temp directory, so
    tests that call load_settings()/save_settings() etc. never touch the
    real addon source tree."""
    addon = _load_addon()
    tmp_dir = tempfile.mkdtemp(prefix='ytdlp_addon_test_')
    addon.config_file = os.path.join(tmp_dir, 'config.json')
    addon.playlists_json_path = os.path.join(tmp_dir, 'playlists.json')
    addon.subscriptions_json_path = os.path.join(tmp_dir, 'subscriptions.json')
    return addon, tmp_dir


_passed = 0
_failed = []


def check(label, condition):
    global _passed
    if condition:
        _passed += 1
    else:
        _failed.append(label)
        print(f'FAIL: {label}')


# ---------------------------------------------------------------------
# URL normalization
# ---------------------------------------------------------------------

def test_normalize_playlist_url():
    addon = _load_addon()
    check(
        'watch-url-with-list-param becomes canonical playlist url',
        addon._normalize_playlist_url('https://www.youtube.com/watch?v=abc&list=PLxyz')
        == 'https://www.youtube.com/playlist?list=PLxyz',
    )
    check(
        'already-canonical playlist url is unchanged',
        addon._normalize_playlist_url('https://www.youtube.com/playlist?list=PLxyz')
        == 'https://www.youtube.com/playlist?list=PLxyz',
    )
    check(
        'url with no list param passes through unchanged',
        addon._normalize_playlist_url('https://www.youtube.com/@channel/videos')
        == 'https://www.youtube.com/@channel/videos',
    )
    once = addon._normalize_playlist_url('https://www.youtube.com/watch?v=abc&list=PLxyz')
    twice = addon._normalize_playlist_url(once)
    check('normalization is idempotent', once == twice)
    # A "mix"/radio pseudo-playlist id (RD...) must NOT be treated as a
    # real playlist for caching purposes the same way a saved playlist is.
    check(
        'RD (radio/mix) ids are excluded from playlist-id detection',
        addon._is_playlist_id_candidate('RDabcdefghij') is False,
    )
    check(
        'PL-prefixed ids are accepted',
        addon._is_playlist_id_candidate('PLabc123') is True,
    )


def test_channel_videos_tab_url():
    addon = _load_addon()
    check(
        'bare channel url gets /videos appended',
        addon._channel_videos_tab_url('https://www.youtube.com/@name')
        == 'https://www.youtube.com/@name/videos',
    )
    check(
        'already on the videos tab is left alone (not doubled)',
        addon._channel_videos_tab_url('https://www.youtube.com/@name/videos')
        == 'https://www.youtube.com/@name/videos',
    )
    check(
        'a URL already on a different known tab is switched to /videos, not left alone - '
        'needed so the Shorts/Live/Playlists sibling helpers below can reliably force their '
        'own tab regardless of what tab a stored channel URL happens to already end in',
        addon._channel_videos_tab_url('https://www.youtube.com/@name/streams')
        == 'https://www.youtube.com/@name/videos',
    )
    check(
        'trailing slash does not break tab detection',
        addon._channel_videos_tab_url('https://www.youtube.com/@name/videos/')
        == 'https://www.youtube.com/@name/videos',
    )


def test_channel_section_tab_urls():
    addon = _load_addon()
    check(
        'shorts tab helper',
        addon._channel_shorts_tab_url('https://www.youtube.com/@name')
        == 'https://www.youtube.com/@name/shorts',
    )
    check(
        'live tab helper points at the streams URL segment',
        addon._channel_live_tab_url('https://www.youtube.com/@name')
        == 'https://www.youtube.com/@name/streams',
    )
    check(
        'playlists tab helper',
        addon._channel_playlists_tab_url('https://www.youtube.com/@name')
        == 'https://www.youtube.com/@name/playlists',
    )
    check(
        'each helper switches away from whatever tab is already on the url, not just bare urls',
        addon._channel_shorts_tab_url('https://www.youtube.com/@name/playlists')
        == 'https://www.youtube.com/@name/shorts',
    )


# ---------------------------------------------------------------------
# Channel URL extraction (Ctrl+S subscribe) - flat-extraction fallbacks
# ---------------------------------------------------------------------

def test_extract_channel_url_field_fallback_order():
    addon = _load_addon()
    check(
        'prefers channel_url when present',
        addon._extract_channel_url({'channel_url': 'https://www.youtube.com/channel/UC1'})
        == 'https://www.youtube.com/channel/UC1',
    )
    check(
        'falls back to uploader_url',
        addon._extract_channel_url({'uploader_url': 'https://www.youtube.com/@name'})
        == 'https://www.youtube.com/@name',
    )
    check(
        'falls back to channel_id',
        addon._extract_channel_url({'channel_id': 'UC2'})
        == 'https://www.youtube.com/channel/UC2',
    )
    check(
        'falls back to a handle-style uploader_id',
        addon._extract_channel_url({'uploader_id': '@handle'})
        == 'https://www.youtube.com/@handle',
    )
    check(
        'falls back to a plain uploader_id treated as a channel id',
        addon._extract_channel_url({'uploader_id': 'UC3'})
        == 'https://www.youtube.com/channel/UC3',
    )
    check(
        'returns None (not an exception) when nothing usable is present -'
        ' this is the exact "Cannot find channel information" scenario'
        ' flagged in the improvement proposal for flat-extracted entries',
        addon._extract_channel_url({'title': 'no channel fields at all'}) is None,
    )
    check(
        'does not crash on a non-dict input',
        addon._extract_channel_url(None) is None,
    )


# ---------------------------------------------------------------------
# Folder-name sanitization (download subfolder naming)
# ---------------------------------------------------------------------

def test_sanitize_folder_name_windows_rules():
    addon = _load_addon()
    original_platform = addon.sys.platform
    addon.sys.platform = 'win32'  # the add-on only ever actually runs on Windows
    try:
        check(
            'illegal Windows filename characters are replaced with spaces',
            addon._sanitize_folder_name('My<Cool>Channel:Name') == 'My Cool Channel Name',
        )
        check(
            'slashes are replaced, not left to be interpreted as path separators',
            addon._sanitize_folder_name('a/b\\c') == 'a b c',
        )
        check(
            'a bare reserved Windows device name gets a safe suffix',
            addon._sanitize_folder_name('CON') == 'CON_',
        )
        check(
            'surrounding whitespace and trailing dots are trimmed',
            addon._sanitize_folder_name('  spaced out.  ') == 'spaced out',
        )
        check('empty input returns empty string, not an exception', addon._sanitize_folder_name('') == '')
        check('None input returns empty string, not an exception', addon._sanitize_folder_name(None) == '')
        long_name = 'x' * 200
        check('overly long names are truncated to max_len', len(addon._sanitize_folder_name(long_name)) == 80)
    finally:
        addon.sys.platform = original_platform


# ---------------------------------------------------------------------
# Settings merge behavior (SettingsTab.save()'s "start from full current
# settings" pattern - the round-7 bug this guards against was Save
# silently resetting background-only fields like last_ytdlp_update_check)
# ---------------------------------------------------------------------

def test_settings_save_preserves_background_only_fields():
    addon, tmp_dir = _load_addon_with_temp_storage()
    try:
        s = addon.load_settings()
        s['last_ytdlp_update_check'] = 123456.0
        s['last_subscriptions_check_ts'] = 654321.0
        addon.save_settings(s)

        # Mirror what SettingsTab.save() does: start from the full,
        # current settings dict, then overlay only the fields that are
        # actually shown as controls on the Settings tab.
        new_settings = dict(addon.load_settings())
        new_settings.update({'download_folder': '/tmp/somewhere-else'})
        addon.save_settings(new_settings)

        reloaded = addon.load_settings()
        check(
            'the field actually being changed took effect',
            reloaded['download_folder'] == '/tmp/somewhere-else',
        )
        check(
            'a background-only field not shown on the tab survived the save',
            reloaded['last_ytdlp_update_check'] == 123456.0,
        )
        check(
            'a second background-only field also survived the save',
            reloaded['last_subscriptions_check_ts'] == 654321.0,
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_normalize_search_limit_snaps_to_known_choices():
    addon = _load_addon()
    check('values <=25 snap to 25', addon.normalize_search_limit(10) == 25)
    check('values in (25,50] snap to 50', addon.normalize_search_limit(50) == 50)
    check('values above 50 snap to 100', addon.normalize_search_limit(9999) == 100)
    check('non-numeric input falls back to the default of 25', addon.normalize_search_limit('not a number') == 25)


# ---------------------------------------------------------------------
# Playlist-items cache key isolation - regression test for the round-10
# bug where a cache key built from the URL alone (ignoring `limit`) let a
# limit=5 baseline fetch and a limit=20 regular check for the same channel
# silently clobber each other. This test fails against the pre-round-10
# behavior (single URL-only key) and passes against the current code.
# ---------------------------------------------------------------------

def test_playlist_cache_key_is_limit_aware():
    addon = _load_addon()
    addon.yt_dlp.reset()
    url = 'https://www.youtube.com/@somechannel/videos'

    small_entries = [
        {'title': f'video {i}', 'id': f'id{i}', 'url': f'https://youtu.be/id{i}'} for i in range(5)
    ]
    large_entries = [
        {'title': f'video {i}', 'id': f'id{i}', 'url': f'https://youtu.be/id{i}'} for i in range(20)
    ]
    addon.yt_dlp.set_fake_playlist(url, large_entries)

    results = {}

    def _fetch(limit, key, force_refresh=False):
        done = threading.Event()

        def _cb(data):
            results[key] = data
            done.set()

        addon.request_playlist_items(url, _cb, limit=limit, force_refresh=force_refresh)
        ok = done.wait(timeout=5)
        check(f'fetch for {key} completed within timeout', ok)

    # Baseline-style fetch (small limit), then a regular-check-style fetch
    # (larger limit) for the very same channel URL, then the baseline size
    # again - this ordering is exactly what happens in real usage:
    # Subscriptions establishes a limit=5 baseline when you first
    # subscribe, then does limit=20 checks afterward for the same channel.
    _fetch(5, 'baseline_1')
    check('baseline fetch (limit=5) returns exactly 5 items', len(results['baseline_1']['items']) == 5)

    _fetch(20, 'regular_check', force_refresh=True)
    check('regular check (limit=20) returns exactly 20 items', len(results['regular_check']['items']) == 20)

    # The critical regression check: repeating the limit=5 fetch must
    # still come back with 5 items from ITS OWN cache entry, not the
    # 20-item result the limit=20 fetch just cached for the same URL.
    _fetch(5, 'baseline_2')
    check(
        'a repeated limit=5 fetch is not clobbered by the intervening'
        ' limit=20 fetch for the same URL (the round-10 regression)',
        len(results['baseline_2']['items']) == 5,
    )


def test_playlist_cache_force_refresh_bypasses_stale_cache():
    addon = _load_addon()
    addon.yt_dlp.reset()
    url = 'https://www.youtube.com/@anotherchannel/videos'
    addon.yt_dlp.set_fake_playlist(url, [{'title': 'old', 'id': 'a', 'url': 'https://youtu.be/a'}])

    results = {}

    def _fetch(key, force_refresh):
        done = threading.Event()

        def _cb(data):
            results[key] = data
            done.set()

        addon.request_playlist_items(url, _cb, limit=20, force_refresh=force_refresh)
        done.wait(timeout=5)

    _fetch('first', force_refresh=False)
    check('initial fetch sees the one seeded item', len(results['first']['items']) == 1)

    # Simulate a new upload appearing on the channel between checks.
    addon.yt_dlp.set_fake_playlist(url, [
        {'title': 'new', 'id': 'b', 'url': 'https://youtu.be/b'},
        {'title': 'old', 'id': 'a', 'url': 'https://youtu.be/a'},
    ])

    _fetch('cached', force_refresh=False)
    check(
        'without force_refresh, a fresh call within the TTL is served from cache (still 1 item)',
        len(results['cached']['items']) == 1,
    )

    _fetch('forced', force_refresh=True)
    check(
        'force_refresh=True bypasses the cache and sees the new upload',
        len(results['forced']['items']) == 2,
    )


def test_cleanup_removes_canceled_jobs_leftover_raw_file():
    """Regression test for a round-15 follow-up bug: canceling a download
    stopped it, but a leftover file remained in the destination folder.

    Root cause: the download's raw source stream (e.g. a .webm/.m4a file
    that finished downloading but was never converted/merged because the
    user canceled before FFmpeg ran) was tracked in the job's own 'files'
    set by the progress hook, but the cleanup routine only ever deleted
    paths ending in .part/.ytdl/.temp/.tmp - an ordinary-looking raw file
    like "Title.f140.m4a" matched none of those suffixes and was silently
    left behind forever. Fixed by adding an aggressive=True cleanup mode,
    used only for canceled/errored jobs (never a successful completion),
    that deletes every path the job itself ever reported - scoped strictly
    to that job's own (url, format) entry so a sibling download of the same
    video in a different format, running at the same time, is never
    touched.
    """
    addon = _load_addon()
    with tempfile.TemporaryDirectory() as folder:
        url = 'https://youtu.be/leftover-test'

        raw_file = os.path.join(folder, 'My Title.f140.m4a')
        sibling_file = os.path.join(folder, 'My Title.mp4')
        with open(raw_file, 'w') as f:
            f.write('raw')
        with open(sibling_file, 'w') as f:
            f.write('sibling')

        addon.state.active_downloads[url] = {
            1: {'files': {raw_file}, 'cancel': True, 'title': 'My Title'},
            0: {'files': {sibling_file}, 'cancel': False, 'title': 'My Title'},
        }

        deleted = addon._cleanup_temp_artifacts_for_url(
            url, folder, title='My Title', fmt_code=1, aggressive=True,
        )
        check('aggressive cleanup reports exactly one file removed', deleted == 1)
        check(
            "a canceled job's own leftover raw file is actually deleted from disk",
            not os.path.exists(raw_file),
        )
        check(
            "a sibling format's own active-download file is never touched by another job's cleanup",
            os.path.exists(sibling_file),
        )

    with tempfile.TemporaryDirectory() as folder2:
        url2 = 'https://youtu.be/no-aggressive-test'
        raw_file2 = os.path.join(folder2, 'Other Title.f140.m4a')
        with open(raw_file2, 'w') as f:
            f.write('raw')

        addon.state.active_downloads[url2] = {
            0: {'files': {raw_file2}, 'cancel': False, 'title': 'Other Title'},
        }

        deleted2 = addon._cleanup_temp_artifacts_for_url(
            url2, folder2, title='Other Title', fmt_code=0,
        )
        check(
            'without aggressive=True (the success-path default), an ordinary tracked file is left alone',
            deleted2 == 0 and os.path.exists(raw_file2),
        )


def test_playlist_items_item_kind_builds_playlist_urls():
    """Regression test for a round-18 bug: opening a channel's Playlists
    section in Subscriptions, then opening one of the playlists shown
    there, showed no videos at all.

    Root cause: request_playlist_items() always treated every entry it
    fetched as a video, building a /watch?v=<id> URL from the entry's
    'id' field whenever no webpage_url was present - which is exactly the
    case for yt-dlp's flat extraction of a channel's Playlists tab. Each
    entry there is itself a playlist, so 'id' is a playlist id (e.g.
    "PLxxxx"), and a /watch?v=PLxxxx URL is not a real video - fetching
    it back returned no items, which is why the playlist appeared to
    contain nothing.

    Fixed by adding an item_kind='playlist' mode that builds URLs with
    _build_playlist_url_from_entry() instead (the same helper Search and
    Download's own playlist search results already use successfully).
    This test fails against the old id-always-means-video logic and
    passes against the fix.
    """
    addon = _load_addon()
    addon.yt_dlp.reset()
    url = 'https://www.youtube.com/@somechannel/playlists'

    # Shaped like yt-dlp's real flat extraction of a channel's Playlists
    # tab: each entry is a playlist - no webpage_url/original_url (flat
    # mode omits those), an 'id' that is a playlist id, and a 'url' that
    # already points at the real playlist page.
    addon.yt_dlp.set_fake_playlist(url, [
        {
            'title': 'My Uploads',
            'id': 'PLabc123',
            'url': 'https://www.youtube.com/playlist?list=PLabc123',
            'uploader': 'Some Channel',
            'video_count': 12,
        },
        {
            'title': 'Favorites',
            'id': 'PLdef456',
            'url': 'https://www.youtube.com/playlist?list=PLdef456',
            'uploader': 'Some Channel',
        },
    ])

    results = {}
    done = threading.Event()

    def _cb(data):
        results['data'] = data
        done.set()

    addon.request_playlist_items(url, _cb, limit=20, item_kind='playlist')
    ok = done.wait(timeout=5)
    check('fetch completed within timeout', ok)

    items = results['data']['items']
    check('both playlist entries came back', len(items) == 2)

    for it in items:
        check(f"item {it['title']!r} is tagged kind='playlist'", it.get('kind') == 'playlist')
        check(
            f"item {it['title']!r} got a real playlist URL, not a broken /watch?v= URL built from its playlist id",
            'list=' in (it.get('url') or '') and '/watch?v=PL' not in (it.get('url') or ''),
        )

    check(
        'video_count on the first entry is carried through as the item count',
        items[0].get('count') == '12',
    )

    # Default item_kind (used everywhere else - Videos/Shorts/Live
    # sections, an opened playlist's own contents, search results) must
    # be completely unaffected by this new mode.
    addon.yt_dlp.reset()
    video_url = 'https://www.youtube.com/@somechannel/videos'
    addon.yt_dlp.set_fake_playlist(video_url, [
        {'title': 'A video', 'id': 'abc123xyz', 'uploader': 'Some Channel', 'duration': 90},
    ])
    results2 = {}
    done2 = threading.Event()

    def _cb2(data):
        results2['data'] = data
        done2.set()

    addon.request_playlist_items(video_url, _cb2, limit=20)
    done2.wait(timeout=5)
    video_item = results2['data']['items'][0]
    check("default item_kind still tags entries kind='video'", video_item.get('kind') == 'video')
    check(
        'default item_kind still builds a normal /watch?v= URL from a video id',
        video_item.get('url') == 'https://www.youtube.com/watch?v=abc123xyz',
    )


def test_live_stream_resolution_reports_is_live_without_resolving_url():
    """_resolve_playable_stream() returns a (stream_url, is_live) tuple.
    As of round 40, a currently-airing live stream is never resolved to a
    playable URL at all - stream_url always comes back None for it, and
    is_live comes back True so the caller (start_playback()) knows to open
    the video in the browser instead of ever starting mpv for it. This is
    a deliberate simplification: rounds 32-34 tried playing live broadcasts
    inside mpv itself (pinning a resolved URL, picking the HLS manifest, an
    auto-restart watchdog for when mpv exited mid-broadcast) and never
    reached fully stable playback, so this add-on stopped trying to play
    live content in-app at all rather than continuing to work around mpv's
    limitations for it - see DEV_NOTES.md round 40."""
    addon = _load_addon()
    addon.yt_dlp.reset()

    live_url = 'https://www.youtube.com/watch?v=live123'
    addon.yt_dlp.set_fake_video_info(live_url, {
        'is_live': True,
        'url': 'https://dash-direct.googlevideo.com/videoplayback?id=live123-dash',
    })
    resolved_live, is_live_1 = addon._resolve_playable_stream(live_url)
    check(
        'a currently-live stream is never resolved to a playable url',
        resolved_live is None,
    )
    check('is_live is True for a currently-live stream', is_live_1 is True)

    vod_url = 'https://www.youtube.com/watch?v=vod456'
    addon.yt_dlp.set_fake_video_info(vod_url, {
        'is_live': False,
        'url': 'https://rr-vod.googlevideo.com/videoplayback?id=vod456',
    })
    resolved_vod, is_live_vod = addon._resolve_playable_stream(vod_url)
    check(
        'a normal (non-live) video is still resolved to its direct stream url, unaffected by the live check',
        resolved_vod == 'https://rr-vod.googlevideo.com/videoplayback?id=vod456',
    )
    check('is_live is False for a normal video', is_live_vod is False)

    # A finished stream's VOD replay (was_live=True, is_live False/absent)
    # is a fixed-length file like any other video, not a live manifest -
    # it must still be resolved normally, not skipped.
    replay_url = 'https://www.youtube.com/watch?v=replay789'
    addon.yt_dlp.set_fake_video_info(replay_url, {
        'was_live': True,
        'url': 'https://rr-vod.googlevideo.com/videoplayback?id=replay789',
    })
    resolved_replay, is_live_replay = addon._resolve_playable_stream(replay_url)
    check(
        "a finished stream's VOD replay (was_live, not currently live) is still resolved normally",
        resolved_replay == 'https://rr-vod.googlevideo.com/videoplayback?id=replay789',
    )
    check('is_live is False for a finished stream\'s VOD replay', is_live_replay is False)

    # requested_formats fallback path (used when 'url' isn't set directly)
    # must still work for non-live videos too.
    fmt_url = 'https://www.youtube.com/watch?v=fmt999'
    addon.yt_dlp.set_fake_video_info(fmt_url, {
        'is_live': False,
        'requested_formats': [{'url': 'https://rr-vod.googlevideo.com/videoplayback?id=fmt999-audio'}],
    })
    resolved_fmt, is_live_fmt = addon._resolve_playable_stream(fmt_url)
    check(
        'requested_formats fallback still works for non-live videos',
        resolved_fmt == 'https://rr-vod.googlevideo.com/videoplayback?id=fmt999-audio',
    )
    check('is_live is False for the requested_formats fallback case too', is_live_fmt is False)


def test_ytdlp_update_verification_and_startup_gate():
    """Round-47 regression coverage for the yt-dlp updater bug report
    (user tested 2026-08-20: auto-update checkbox on but not checking, and
    a manual update + restart still showing the old version).

    Two behavior changes are covered here:

    1. maybe_auto_check_for_ytdlp_update() used to skip entirely unless
       more than 24h had passed since last_ytdlp_update_check, which could
       make automatic updates look broken if the user had already tested
       earlier the same day. It now only looks at the auto_update_ytdlp
       setting (and secure-desktop), and always proceeds to
       check_for_ytdlp_update() otherwise - verified here by stubbing
       check_for_ytdlp_update() and confirming it is invoked even with a
       last_ytdlp_update_check timestamp of "just now".

    2. check_ytdlp_update_took_effect() is new: it compares a pending
       "we just installed this version" marker (written by
       check_for_ytdlp_update() on success) against the version actually
       running after a real restart, and warns the user if they don't
       match - covering the case (confirmed reproducible against the real
       update code, but only outside of NVDA/Windows in this project's own
       testing - see DEV_NOTES.md round 47) where something on the user's
       machine reverts the newly-written files between install and
       restart."""
    # NOTE: use addon.ui / addon.log (the mock module objects init.py
    # itself imported into its own namespace via `import ui` / `from
    # logHandler import log`) rather than `from mocks import ui`/etc here.
    # `import ui` (with mocks/ on sys.path directly) and `from mocks
    # import ui` register as two *different* entries in sys.modules
    # ('ui' vs 'mocks.ui'), each holding its own separate mocks/ui.py
    # module instance with its own separate `messages` list - asserting
    # against a freshly-`from mocks import`-ed copy would silently watch
    # the wrong list and never see what init.py actually recorded.

    # --- check_ytdlp_update_took_effect() ---

    # No pending marker at all: must be a no-op (no message, nothing to warn about).
    addon, _tmp = _load_addon_with_temp_storage()
    before = len(addon.ui.messages)
    addon.check_ytdlp_update_took_effect()
    check(
        'no pending update marker means no message is spoken',
        len(addon.ui.messages) == before,
    )

    # Pending marker matches what's actually running (mocks/yt_dlp.py
    # reports '2026.01.01'): the update genuinely took effect, so this
    # should clear the marker silently, not warn.
    addon, _tmp = _load_addon_with_temp_storage()
    settings = addon.load_settings()
    settings['ytdlp_update_pending_version'] = '2026.01.01'
    settings['ytdlp_update_pending_since'] = 12345.0
    addon.save_settings(settings)
    before = len(addon.ui.messages)
    addon.check_ytdlp_update_took_effect()
    check(
        'matching pending/actual version speaks no warning',
        len(addon.ui.messages) == before,
    )
    reloaded = addon.load_settings()
    check(
        'matching pending/actual version still clears the pending marker',
        reloaded.get('ytdlp_update_pending_version') is None,
    )

    # Pending marker does NOT match what's actually running: the update
    # was reported successful but did not stick - this must speak a
    # warning, log an error, and clear the marker so it does not repeat
    # forever.
    addon, _tmp = _load_addon_with_temp_storage()
    settings = addon.load_settings()
    settings['ytdlp_update_pending_version'] = '2026.08.19'
    settings['ytdlp_update_pending_since'] = 12345.0
    addon.save_settings(settings)
    before_msgs = len(addon.ui.messages)
    before_errs = len(addon.log.records)
    addon.check_ytdlp_update_took_effect()
    check(
        'mismatched pending/actual version speaks a warning',
        len(addon.ui.messages) == before_msgs + 1,
    )
    spoken = addon.ui.messages[-1]
    check('the warning mentions the version that was supposed to install', '2026.08.19' in spoken)
    check('the warning mentions the version actually running', '2026.01.01' in spoken)
    check(
        'mismatched pending/actual version logs an error for diagnosis',
        len(addon.log.records) == before_errs + 1,
    )
    reloaded = addon.load_settings()
    check(
        'mismatched pending/actual version still clears the pending marker (does not repeat every startup)',
        reloaded.get('ytdlp_update_pending_version') is None,
    )

    # --- maybe_auto_check_for_ytdlp_update() no longer throttled to once/day ---

    addon, _tmp = _load_addon_with_temp_storage()
    calls = []
    addon.check_for_ytdlp_update = lambda manual=False, on_done=None: calls.append(manual)

    settings = addon.load_settings()
    settings['auto_update_ytdlp'] = True
    settings['last_ytdlp_update_check'] = addon.time.time()  # "just checked, right now"
    addon.save_settings(settings)
    addon.maybe_auto_check_for_ytdlp_update()
    check(
        'auto-check runs on every startup even if last check was seconds ago',
        calls == [False],
    )

    calls.clear()
    settings = addon.load_settings()
    settings['auto_update_ytdlp'] = False
    addon.save_settings(settings)
    addon.maybe_auto_check_for_ytdlp_update()
    check(
        'auto-check still respects the user disabling it in Settings',
        calls == [],
    )


def run_all():
    tests = [
        test_normalize_playlist_url,
        test_channel_videos_tab_url,
        test_channel_section_tab_urls,
        test_extract_channel_url_field_fallback_order,
        test_sanitize_folder_name_windows_rules,
        test_settings_save_preserves_background_only_fields,
        test_normalize_search_limit_snaps_to_known_choices,
        test_playlist_cache_key_is_limit_aware,
        test_playlist_cache_force_refresh_bypasses_stale_cache,
        test_playlist_items_item_kind_builds_playlist_urls,
        test_cleanup_removes_canceled_jobs_leftover_raw_file,
        test_live_stream_resolution_reports_is_live_without_resolving_url,
        test_ytdlp_update_verification_and_startup_gate,
    ]
    for t in tests:
        print(f'--- {t.__name__} ---')
        t()

    print()
    print(f'{_passed} check(s) passed, {len(_failed)} failed.')
    if _failed:
        print('Failed checks:')
        for f in _failed:
            print(f'  - {f}')
        sys.exit(1)
    print('ALL TESTS PASSED')


if __name__ == '__main__':
    run_all()
