"""Minimal fake yt-dlp for tests. The real yt-dlp is a Windows-bundled
library the actual add-on carries in lib/yt_dlp - it is not installed on
this Linux test machine, and no test in this suite needs real network
extraction from YouTube. Tests configure canned responses via
set_fake_playlist() before calling into globalPlugins/init.py.
"""

_fake_playlists = {}  # url -> list of entry dicts
_fake_video_info = {}  # url -> single-video info dict (no 'entries' wrapper)


def set_fake_playlist(url, entries):
    _fake_playlists[url] = entries


def set_fake_video_info(url, info):
    """Configure extract_info(url) to return `info` verbatim (no 'entries'
    wrapper), simulating a single-video lookup like _resolve_playable_stream
    does - as opposed to set_fake_playlist(), which simulates a
    playlist/channel listing."""
    _fake_video_info[url] = info


def reset():
    _fake_playlists.clear()
    _fake_video_info.clear()


class _FakeVersionModule:
    __version__ = '2026.01.01'


version = _FakeVersionModule()


class YoutubeDL:
    def __init__(self, opts=None):
        self.opts = opts or {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def extract_info(self, url, download=False):
        if url in _fake_video_info:
            return _fake_video_info[url]
        entries = list(_fake_playlists.get(url, []))
        limit = self.opts.get('playlistend')
        if limit:
            entries = entries[:limit]
        return {'title': 'Fake Playlist', 'entries': entries}

    def download(self, urls):
        return 0
