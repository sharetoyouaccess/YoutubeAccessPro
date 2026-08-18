#!/usr/bin/env python3
"""
Build a distributable YoutubeAccessPro .nvda-addon from this repository's
source tree.

Why this doesn't just download ffmpeg/mpv/youtube-dl from the internet
every time
-----------------------------------------------------------------------
The add-on bundles a handful of third-party binaries (ffmpeg.exe,
ffprobe.exe, mpv.exe, d3dcompiler_43.dll, youtube-dl.exe - see
THIRD_PARTY_NOTICES.txt for exact versions and why each is needed). Those
specific historical builds (e.g. mpv 0.28.0 from 2017, a particular
gyan.dev "essentials" snapshot of ffmpeg) are not guaranteed to still be
available at a stable URL, and this project has already had a real
regression once (see DEV_NOTES.md, round 29) from an unrelated binary
being removed and silently breaking a feature that depended on it
indirectly. Re-fetching "the latest version" of each binary on every
build risks re-introducing that kind of bug without a real NVDA/Windows
test pass to catch it.

So instead, this script takes the binaries from a *known-good* existing
.nvda-addon build (the "vendor" file - normally the most recent file you
already have in this project's folder that you've tested and confirmed
works) and overlays this repository's own source files on top of it.
Only touch/upgrade the vendor binaries deliberately, in their own change,
with real testing - not as a side effect of running this script.

Usage
-----
    python3 scripts/build_addon.py --vendor /path/to/known-good.nvda-addon --out YoutubeAccessPro-<version>.nvda-addon

What gets taken from the repo (always fresh from this working tree):
    manifest.ini
    globalPlugins/init.py
    doc/en/readme.html
    COPYING.txt
    THIRD_PARTY_NOTICES.txt
    globalPlugins/lib/yt_dlp/**           (entire tree, replaces vendor's copy)
    globalPlugins/lib/fileinput.py
    globalPlugins/lib/optparse.py

Everything else in the vendor .nvda-addon (globalPlugins/lib/ffmpeg/**,
globalPlugins/lib/mpv/**, and anything else not listed above) is copied
through byte-for-byte, unchanged.

Deliberately overriding one specific vendor binary (--override)
-----------------------------------------------------------------------
For the rare, deliberate case where one specific vendor binary needs to
be upgraded on purpose (with real reasoning and its own test pass - see
DEV_NOTES.md round 35 for the mpv.exe upgrade this flag was added for),
pass one or more --override ARCNAME=PATH options. Each named arcname is
taken from the given local file instead of the vendor archive (and
instead of the repo tree, if it happens to also be repo-managed - this
takes priority over both). Example:

    python3 scripts/build_addon.py --vendor old.nvda-addon --out new.nvda-addon \
        --override globalPlugins/lib/mpv/mpv.exe=/path/to/new_mpv_build/mpv.exe \
        --override globalPlugins/lib/mpv/d3dcompiler_43.dll=/path/to/new_mpv_build/d3dcompiler_43.dll
"""

import argparse
import os
import sys
import zipfile

REPO_MANAGED_FILES = {
    "manifest.ini",
    "globalPlugins/init.py",
    "doc/en/readme.html",
    "COPYING.txt",
    "THIRD_PARTY_NOTICES.txt",
    "globalPlugins/lib/fileinput.py",
    "globalPlugins/lib/optparse.py",
}
REPO_MANAGED_PREFIXES = (
    "globalPlugins/lib/yt_dlp/",
)


def is_repo_managed(arcname: str) -> bool:
    if arcname in REPO_MANAGED_FILES:
        return True
    return any(arcname.startswith(p) for p in REPO_MANAGED_PREFIXES)


def repo_source_files(repo_root: str):
    """Yield (arcname, absolute_path) for every file this repo should
    contribute to the built package."""
    for rel in sorted(REPO_MANAGED_FILES):
        abs_path = os.path.join(repo_root, rel.replace("/", os.sep))
        if not os.path.isfile(abs_path):
            print(f"WARNING: expected source file missing: {rel}", file=sys.stderr)
            continue
        yield rel, abs_path

    ytdlp_dir = os.path.join(repo_root, "globalPlugins", "lib", "yt_dlp")
    if not os.path.isdir(ytdlp_dir):
        print("WARNING: globalPlugins/lib/yt_dlp not found in repo", file=sys.stderr)
        return
    for dirpath, _dirnames, filenames in os.walk(ytdlp_dir):
        for fn in filenames:
            abs_path = os.path.join(dirpath, fn)
            rel = os.path.relpath(abs_path, repo_root).replace(os.sep, "/")
            yield rel, abs_path


def build(vendor_path: str, repo_root: str, out_path: str, overrides: dict = None) -> None:
    overrides = overrides or {}
    if not os.path.isfile(vendor_path):
        raise SystemExit(f"Vendor .nvda-addon not found: {vendor_path}")
    for arcname, abs_path in overrides.items():
        if not os.path.isfile(abs_path):
            raise SystemExit(f"--override file not found for {arcname}: {abs_path}")

    with zipfile.ZipFile(vendor_path, "r") as vendor_zip:
        bad = vendor_zip.testzip()
        if bad is not None:
            raise SystemExit(f"Vendor archive is corrupt at entry: {bad}")

        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as out_zip:
            copied_from_vendor = 0
            for info in vendor_zip.infolist():
                if info.is_dir():
                    continue
                if info.filename in overrides:
                    continue  # will be added fresh from --override below
                if is_repo_managed(info.filename):
                    continue  # will be added fresh from the repo below
                data = vendor_zip.read(info.filename)
                out_zip.writestr(info, data)
                copied_from_vendor += 1

            added_from_repo = 0
            for arcname, abs_path in repo_source_files(repo_root):
                if arcname in overrides:
                    continue  # --override takes priority even over repo-managed files
                out_zip.write(abs_path, arcname)
                added_from_repo += 1

            for arcname, abs_path in overrides.items():
                out_zip.write(abs_path, arcname)

    with zipfile.ZipFile(out_path, "r") as check:
        bad = check.testzip()
        if bad is not None:
            raise SystemExit(f"Built archive is corrupt at entry: {bad}")
        total = len(check.namelist())

    size = os.path.getsize(out_path)
    print(f"Built {out_path}")
    print(f"  {copied_from_vendor} files copied unchanged from vendor (binaries etc.)")
    print(f"  {added_from_repo} files added fresh from this repo")
    if overrides:
        print(f"  {len(overrides)} file(s) deliberately overridden: {', '.join(sorted(overrides))}")
    print(f"  {total} files total, {size:,} bytes")
    print("  testzip(): OK, no corrupt entries")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vendor", required=True, help="Path to an existing, known-good .nvda-addon to source binaries from")
    parser.add_argument("--out", required=True, help="Path to write the new .nvda-addon to")
    parser.add_argument("--repo-root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         help="Path to the repo root (default: parent of this script's directory)")
    parser.add_argument("--override", action="append", default=[], metavar="ARCNAME=PATH",
                         help="Deliberately source one specific archive path from a local file instead of "
                              "the vendor archive or repo tree. Repeatable. See the module docstring.")
    args = parser.parse_args()

    overrides = {}
    for entry in args.override:
        if "=" not in entry:
            raise SystemExit(f"--override must be ARCNAME=PATH, got: {entry}")
        arcname, abs_path = entry.split("=", 1)
        overrides[arcname] = abs_path

    build(args.vendor, args.repo_root, args.out, overrides)


if __name__ == "__main__":
    main()
