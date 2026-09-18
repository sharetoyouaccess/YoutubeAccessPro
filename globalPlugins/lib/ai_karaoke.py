"""
AI Vocal Separation Engine for YouTube Access Pro.
Uses bundled 6_HP-Karaoke-UVR ONNX neural network and ffmpeg to isolate accompaniment in the background.
"""

import hashlib
import os
import subprocess
import tempfile
import threading
import time


_CACHE_DIR = os.path.join(tempfile.gettempdir(), 'ytdlp_ai_karaoke')
os.makedirs(_CACHE_DIR, exist_ok=True)

_current_proc = None
_proc_lock = threading.Lock()


def get_cache_key(url: str) -> str:
    return hashlib.md5(url.encode('utf-8', errors='ignore')).hexdigest()


def get_cached_accompaniment(url: str):
    key = get_cache_key(url)
    cached = os.path.join(_CACHE_DIR, f'{key}_acc.wav')
    if os.path.isfile(cached) and os.path.getsize(cached) > 1024:
        return cached
    return None


def is_ai_available(lib_path: str) -> bool:
    uvr_exe = os.path.join(lib_path, 'uvr', 'uvr-karaoke-separate.exe')
    model = os.path.join(lib_path, 'uvr', 'models', '6_HP-Karaoke-UVR.onnx')
    ffmpeg_exe = os.path.join(lib_path, 'ffmpeg', 'ffmpeg.exe')
    return (
        os.path.isfile(uvr_exe)
        and os.path.isfile(model)
        and os.path.isfile(ffmpeg_exe)
    )


def cancel_current_separation():
    global _current_proc
    with _proc_lock:
        if _current_proc is not None:
            try:
                _current_proc.kill()
            except Exception:
                pass
            _current_proc = None


def _run_cancelable_cmd(cmd, cancel_callback=None):
    flags = 0x08000000  # CREATE_NO_WINDOW
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags
    )
    try:
        while True:
            if cancel_callback and cancel_callback():
                try:
                    proc.kill()
                    proc.wait(timeout=1.0)
                except Exception:
                    pass
                raise KeyboardInterrupt('UserCancel')
            ret = proc.poll()
            if ret is not None:
                return ret
            time.sleep(0.1)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
        raise


def process_karaoke_download(
    input_audio_path: str,
    output_mp3_path: str,
    lib_path: str,
    cancel_callback=None,
    status_callback=None,
    num_threads: int = 6
) -> str:
    """
    Takes an input audio file (MP3/M4A/etc.), isolates accompaniment using 6_HP-Karaoke-UVR,
    and encodes the accompaniment into highest-quality 320 kbps MP3 at output_mp3_path.
    Cleans up all intermediate files automatically.
    """
    if cancel_callback and cancel_callback():
        raise KeyboardInterrupt('UserCancel')

    ffmpeg_exe = os.path.join(lib_path, 'ffmpeg', 'ffmpeg.exe')
    uvr_exe = os.path.join(lib_path, 'uvr', 'uvr-karaoke-separate.exe')
    model = os.path.join(lib_path, 'uvr', 'models', '6_HP-Karaoke-UVR.onnx')

    if not (os.path.isfile(ffmpeg_exe) and os.path.isfile(uvr_exe) and os.path.isfile(model)):
        raise RuntimeError('Karaoke engine components are missing')

    temp_dir = tempfile.gettempdir()
    base_id = hashlib.md5(input_audio_path.encode('utf-8', errors='ignore')).hexdigest()[:12]
    temp_raw = os.path.join(temp_dir, f'karaoke_raw_{base_id}.wav')
    temp_acc = os.path.join(temp_dir, f'karaoke_acc_{base_id}.wav')

    try:
        # Step 1: Extract 44.1kHz 16-bit stereo WAV from source
        if status_callback:
            status_callback('Processing audio file  please wait')

        cmd_extract = [
            ffmpeg_exe,
            '-y',
            '-i', input_audio_path,
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', '44100',
            '-ac', '2',
            temp_raw
        ]
        ret1 = _run_cancelable_cmd(cmd_extract, cancel_callback=cancel_callback)
        if ret1 != 0 or not os.path.isfile(temp_raw) or os.path.getsize(temp_raw) < 1024:
            raise RuntimeError(f'Audio extraction failed (code {ret1})')

        # Step 2: Separate with 6_HP-Karaoke-UVR ONNX model
        if status_callback:
            status_callback('Processing karaoke vocal cut  please wait')

        cmd_uvr = [
            uvr_exe,
            '--input', temp_raw,
            '--output-accompaniment', temp_acc,
            '--model', model,
            '--num-threads', str(num_threads)
        ]
        ret2 = _run_cancelable_cmd(cmd_uvr, cancel_callback=cancel_callback)
        if ret2 != 0 or not os.path.isfile(temp_acc) or os.path.getsize(temp_acc) < 1024:
            raise RuntimeError(f'Karaoke processing failed (code {ret2})')

        # Step 3: Encode accompaniment to highest-quality 320 kbps MP3
        if status_callback:
            status_callback('Encoding 320k MP3  please wait')

        out_dir = os.path.dirname(output_mp3_path)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        cmd_encode = [
            ffmpeg_exe,
            '-y',
            '-i', temp_acc,
            '-vn',
            '-codec:a', 'libmp3lame',
            '-b:a', '320k',
            output_mp3_path
        ]
        ret3 = _run_cancelable_cmd(cmd_encode, cancel_callback=cancel_callback)
        if ret3 != 0 or not os.path.isfile(output_mp3_path) or os.path.getsize(output_mp3_path) < 1024:
            raise RuntimeError(f'MP3 encoding failed (code {ret3})')

        return output_mp3_path

    except Exception:
        # On error or cancellation, clean up target file if partially written
        try:
            if os.path.isfile(output_mp3_path):
                os.remove(output_mp3_path)
        except Exception:
            pass
        raise

    finally:
        # Clean up temporary WAV files
        for f in (temp_raw, temp_acc):
            try:
                if os.path.isfile(f):
                    os.remove(f)
            except Exception:
                pass


def separate_track_ai(
    url: str,
    lib_path: str,
    on_complete,
    on_error=None,
    num_threads: int = 6
):
    """
    Separates vocal and accompaniment for the given URL or local file in a background thread.
    Calls on_complete(acc_path) on success, or on_error(err_str) on failure.
    """
    cached = get_cached_accompaniment(url)
    if cached:
        on_complete(cached)
        return

    def _worker():
        global _current_proc
        key = get_cache_key(url)
        temp_raw = os.path.join(_CACHE_DIR, f'{key}_raw.wav')
        temp_acc = os.path.join(_CACHE_DIR, f'{key}_acc.wav')

        ffmpeg_exe = os.path.join(lib_path, 'ffmpeg', 'ffmpeg.exe')
        uvr_exe = os.path.join(lib_path, 'uvr', 'uvr-karaoke-separate.exe')
        model = os.path.join(lib_path, 'uvr', 'models', '6_HP-Karaoke-UVR.onnx')

        flags = 0x08000000  # CREATE_NO_WINDOW

        try:
            # Step 1: Extract 44.1kHz 16-bit stereo WAV from source URL
            cmd_ffmpeg = [
                ffmpeg_exe,
                '-y',
                '-i', url,
                '-vn',
                '-acodec', 'pcm_s16le',
                '-ar', '44100',
                '-ac', '2',
                temp_raw
            ]
            with _proc_lock:
                _current_proc = subprocess.Popen(
                    cmd_ffmpeg,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=flags
                )
            ret1 = _current_proc.wait()
            with _proc_lock:
                _current_proc = None

            if ret1 != 0 or not os.path.isfile(temp_raw):
                if on_error:
                    on_error('FFmpeg extraction failed')
                return

            # Step 2: Separate with 6_HP-Karaoke-UVR
            cmd_uvr = [
                uvr_exe,
                '--input', temp_raw,
                '--output-accompaniment', temp_acc,
                '--model', model,
                '--num-threads', str(num_threads)
            ]
            with _proc_lock:
                _current_proc = subprocess.Popen(
                    cmd_uvr,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=flags
                )
            ret2 = _current_proc.wait()
            with _proc_lock:
                _current_proc = None

            # Clean up intermediate raw file to save disk space
            try:
                if os.path.isfile(temp_raw):
                    os.remove(temp_raw)
            except Exception:
                pass

            if ret2 == 0 and os.path.isfile(temp_acc) and os.path.getsize(temp_acc) > 1024:
                on_complete(temp_acc)
            else:
                if on_error:
                    on_error(f'AI separation failed with code {ret2}')

        except Exception as ex:
            if on_error:
                on_error(str(ex))
        finally:
            with _proc_lock:
                _current_proc = None

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
