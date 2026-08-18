# YouTube Access Pro for NVDA
# Author  Peem Narkkhwan <sharetoyouaccess@gmail.com>
# Version  2026.07.19
# Description  Global plugin for searching, downloading and playing YouTube videos and audio using yt-dlp

import globalPluginHandler
import addonHandler
import wx
import threading
import os
import sys
import json
import subprocess
import webbrowser
import gui
import ui
import tones

addonHandler.initTranslation()

try:
    import globalVars
except Exception:
    globalVars = None


class _AppState:
    """Single container for this add-on's mutable runtime state.

    Every piece of state that used to live as a separate module-level
    global (player/download status, session-only playback memory, the
    playlist-content cache, search-result memory, the sleep timer, and a
    few small runtime flags - about 38 variables in total) is now an
    attribute of this one object instead, created once below as `state`.
    This is a mechanical reorganization only: every attribute is still
    initialized at exactly the place in the file it always was (look for
    the same "# --- ... STATE ---" comment headers further down), just as
    `state.name = value` instead of a bare module-level `name = value`.
    Nothing about *when* or *what* gets initialized has changed - only
    that reading or writing this state from any function no longer needs
    a `global` declaration, since it is now an attribute of an object
    referenced by the single module-level name `state`, not a rebinding
    of a module-level name itself. This removes an entire recurring class
    of risk in this file: a function that reads one of these values
    without knowing it needs `global` to also *write* it silently created
    a same-named local variable instead of touching the real state - the
    attribute form makes that mistake impossible.
    """
    pass


state = _AppState()


def _is_secure_mode():
    """Return True when NVDA is running on a secure desktop / lock screen.

    Add-ons should avoid performing sensitive actions (opening a browser,
    launching external processes, writing files) while NVDA is running in
    secure mode.
    """
    try:
        return bool(globalVars and globalVars.appArgs.secure)
    except Exception:
        return False


# --- IN-ADDON THAI / ENGLISH TRANSLATION ---
# This is deliberately independent of NVDA's own gettext-based translation
# (addonHandler.initTranslation() above), which follows whatever language
# NVDA itself is configured for. Ctrl+T lets the user flip the language
# used by *this add-on's own interface and spoken messages* on the fly,
# regardless of what language NVDA is set to. TH_STRINGS is populated
# further down in this file.

TH_STRINGS = {
    '1 link downloading': 'กำลังดาวน์โหลด 1 ลิงก์',
    '1080p  Full HD': '1080p  ฟูลเอชดี',
    '128 kbps  Low': '128 กิโลบิตต่อวินาที  ต่ำ',
    '192 kbps  Standard': '192 กิโลบิตต่อวินาที  มาตรฐาน',
    '320 kbps  High': '320 กิโลบิตต่อวินาที  สูง',
    '480p  SD': '480p  เอสดี',
    '720p  HD': '720p  เอชดี',
    'Add to playlist': 'เพิ่มลงเพลย์ลิสต์',
    'Already checking for an update': 'กำลังตรวจสอบอัปเดตอยู่แล้ว',
    'Announce download status  F3': 'แจ้งสถานะการดาวน์โหลด  F3',
    'Announce player hotkeys': 'แจ้งปุ่มลัดของเครื่องเล่น',
    'Audio quality  bitrate': 'คุณภาพเสียง  บิตเรต',
    'Automatically check for yt-dlp updates': 'ตรวจสอบอัปเดต yt-dlp โดยอัตโนมัติ',
    'Back': 'ย้อนกลับ',
    'Back  press Enter or Backspace': 'ย้อนกลับ  กด Enter หรือ Backspace',
    'Best  automatic': 'ดีที่สุด  อัตโนมัติ',
    'Canceled': 'ยกเลิกแล้ว',
    'Cannot create playlist file': 'ไม่สามารถสร้างไฟล์เพลย์ลิสต์ได้',
    'Cannot open browser': 'ไม่สามารถเปิดเบราว์เซอร์ได้',
    'Cannot play last item': 'ไม่สามารถเล่นรายการล่าสุดได้',
    'Cannot set speed': 'ไม่สามารถตั้งความเร็วได้',
    'Cannot start player  opening in browser': 'ไม่สามารถเริ่มเครื่องเล่นได้  กำลังเปิดในเบราว์เซอร์',
    'Check for update now': 'ตรวจสอบอัปเดตตอนนี้',
    'Checking for yt-dlp update': 'กำลังตรวจสอบอัปเดต yt-dlp',
    'Clear search field': 'ล้างช่องค้นหา',
    'Cleared': 'ล้างแล้ว',
    'Confirm': 'ยืนยัน',
    'Confirm exit': 'ยืนยันการออก',
    'Contents': 'รายการภายใน',
    'Copied playlist link': 'คัดลอกลิงก์เพลย์ลิสต์แล้ว',
    'Copied video link': 'คัดลอกลิงก์วิดีโอแล้ว',
    'Copy failed': 'คัดลอกไม่สำเร็จ',
    'Copy channel link': 'คัดลอกลิงก์ช่อง',
    'Copy playlist link': 'คัดลอกลิงก์เพลย์ลิสต์',
    'Copy video link': 'คัดลอกลิงก์วิดีโอ',
    'Could not check for updates  no connection to PyPI': 'ไม่สามารถตรวจสอบอัปเดตได้  ไม่มีการเชื่อมต่อไปยัง PyPI',
    'Create new playlist': 'สร้างเพลย์ลิสต์ใหม่',
    'Delete  Del': 'ลบ  Del',
    'Delete this playlist': 'ลบเพลย์ลิสต์นี้',
    'Download as audio  F1': 'ดาวน์โหลดเป็นเสียง  F1',
    'Download as video  F2': 'ดาวน์โหลดเป็นวิดีโอ  F2',
    'Download': 'ดาวน์โหลด',
    'Download error': 'ดาวน์โหลดผิดพลาด',
    'Download folder': 'โฟลเดอร์ดาวน์โหลด',
    'Download latest videos as audio  F1': 'ดาวน์โหลดคลิปล่าสุดเป็นเสียง  F1',
    'Download latest videos as video  F2': 'ดาวน์โหลดคลิปล่าสุดเป็นวิดีโอ  F2',
    'Download playlist': 'ดาวน์โหลดเพลย์ลิสต์',
    'Download playlist as audio  F1': 'ดาวน์โหลดเพลย์ลิสต์เป็นเสียง  F1',
    'Download playlist as video  F2': 'ดาวน์โหลดเพลย์ลิสต์เป็นวิดีโอ  F2',
    'Downloads in progress': 'กำลังดาวน์โหลดอยู่',
    'Enable global player hotkeys outside this window': 'เปิดใช้ปุ่มลัดเครื่องเล่นทั่วทั้งระบบแม้ไม่ได้อยู่ในหน้าต่างนี้',
    'English': 'อังกฤษ',
    'Error': 'ข้อผิดพลาด',
    'Error in search': 'เกิดข้อผิดพลาดในการค้นหา',
    'Error opening download folder': 'เกิดข้อผิดพลาดขณะเปิดโฟลเดอร์ดาวน์โหลด',
    'Error opening item': 'เกิดข้อผิดพลาดขณะเปิดรายการ',
    'Exit': 'ออก',
    'Export failed': 'ส่งออกไม่สำเร็จ',
    'Export subscriptions': 'ส่งออกรายชื่อช่องที่ติดตาม',
    'Import failed': 'นำเข้าไม่สำเร็จ',
    'Import subscriptions': 'นำเข้ารายชื่อช่องที่ติดตาม',
    'Exited': 'ออกแล้ว',
    'FFmpeg is missing': 'ไม่พบ FFmpeg',
    'Fast forward': 'กรอไปข้างหน้า',
    'Fast forward 30 seconds': 'กรอไปข้างหน้า 30 วินาที',
    'Fetching playlist items': 'กำลังดึงรายการในเพลย์ลิสต์',
    'First track': 'เพลงแรก',
    'Global player next track when mpv is running': 'เพลงถัดไปทั่วทั้งระบบขณะที่ mpv กำลังทำงาน',
    'Global player pause resume when mpv is running': 'หยุดชั่วคราวหรือเล่นต่อทั่วทั้งระบบขณะที่ mpv กำลังทำงาน',
    'Global player previous track when mpv is running': 'เพลงก่อนหน้าทั่วทั้งระบบขณะที่ mpv กำลังทำงาน',
    'Global player seek backward 30 seconds when mpv is running': 'ถอยหลัง 30 วินาทีทั่วทั้งระบบขณะที่ mpv กำลังทำงาน',
    'Global player seek forward 30 seconds when mpv is running': 'กรอไปข้างหน้า 30 วินาทีทั่วทั้งระบบขณะที่ mpv กำลังทำงาน',
    'Global player speed down when mpv is running': 'ลดความเร็วทั่วทั้งระบบขณะที่ mpv กำลังทำงาน',
    'Global player speed up when mpv is running': 'เพิ่มความเร็วทั่วทั้งระบบขณะที่ mpv กำลังทำงาน',
    'Global player stop when mpv is running': 'หยุดทั่วทั้งระบบขณะที่ mpv กำลังทำงาน',
    'Global player volume down when mpv is running': 'ลดเสียงทั่วทั้งระบบขณะที่ mpv กำลังทำงาน',
    'Global player volume up when mpv is running': 'เพิ่มเสียงทั่วทั้งระบบขณะที่ mpv กำลังทำงาน',
    'Last track': 'เพลงสุดท้าย',
    'Name': 'ชื่อ',
    'New name': 'ชื่อใหม่',
    'New playlist': 'เพลย์ลิสต์ใหม่',
    'No downloadable items': 'ไม่มีรายการที่ดาวน์โหลดได้',
    'No downloads for this playlist': 'ไม่มีการดาวน์โหลดสำหรับเพลย์ลิสต์นี้',
    'No downloads running': 'ไม่มีการดาวน์โหลดที่กำลังทำงาน',
    'No item selected': 'ไม่ได้เลือกรายการ',
    'No items found': 'ไม่พบรายการ',
    'No items in this playlist': 'ไม่มีรายการในเพลย์ลิสต์นี้',
    'No last item to play': 'ไม่มีรายการล่าสุดให้เล่น',
    'No link': 'ไม่มีลิงก์',
    'No playlist selected': 'ไม่ได้เลือกเพลย์ลิสต์',
    'No playlist url': 'ไม่มีลิงก์เพลย์ลิสต์',
    'No previous list': 'ไม่มีรายการก่อนหน้า',
    'No results found': 'ไม่พบผลการค้นหา',
    'No track list': 'ไม่มีรายการเพลง',
    'No valid url to play': 'ไม่มีลิงก์ที่ใช้เล่นได้',
    'Normal speed': 'ความเร็วปกติ',
    'Not a playlist': 'ไม่ใช่เพลย์ลิสต์',
    'Not downloading': 'ไม่ได้กำลังดาวน์โหลด',
    'Only available for videos': 'ใช้ได้เฉพาะกับวิดีโอเท่านั้น',
    'Only videos can be added': 'เพิ่มได้เฉพาะวิดีโอเท่านั้น',
    'Only videos can be added to playlist': 'เพิ่มลงเพลย์ลิสต์ได้เฉพาะวิดีโอเท่านั้น',
    'Open YouTube Access Pro window': 'เปิดหน้าต่าง YouTube Access Pro',
    'Open in browser': 'เปิดในเบราว์เซอร์',
    'Open channel contents  Enter': 'เปิดดูรายการของช่อง  Enter',
    'Open playlist contents  Enter': 'เปิดดูรายการในเพลย์ลิสต์  Enter',
    'Open playlist contents to download items': 'เปิดดูรายการในเพลย์ลิสต์เพื่อดาวน์โหลด',
    'Open the interface': 'เปิดหน้าต่างโปรแกรม',
    'Opening download folder': 'กำลังเปิดโฟลเดอร์ดาวน์โหลด',
    'Paused': 'หยุดชั่วคราว',
    'Play  F7': 'เล่น  F7',
    'Play playlist from beginning': 'เล่นเพลย์ลิสต์จากเพลงแรก',
    'Playback ended': 'เล่นจบแล้ว',
    'Player not available  opening in browser': 'ไม่มีเครื่องเล่น  กำลังเปิดในเบราว์เซอร์',
    'Playlist': 'เพลย์ลิสต์',
    'Playlists': 'เพลย์ลิสต์',
    'Processing': 'กำลังประมวลผล',
    'Quality options': 'ตัวเลือกคุณภาพ',
    'Remove from playlist  Del': 'ลบออกจากเพลย์ลิสต์  Del',
    'Remove this link from this playlist': 'ลบลิงก์นี้ออกจากเพลย์ลิสต์',
    'Removed': 'ลบแล้ว',
    'Rename  r': 'เปลี่ยนชื่อ  r',
    'Results': 'ผลการค้นหา',
    'Resumed': 'เล่นต่อแล้ว',
    'Rewind': 'ถอยหลัง',
    'Rewind 30 seconds': 'ถอยหลัง 30 วินาที',
    'Save': 'บันทึก',
    'Save as M3U': 'บันทึกเป็น M3U',
    'Save settings': 'บันทึกการตั้งค่า',
    'Saved': 'บันทึกแล้ว',
    'Search and Download': 'ค้นหาและดาวน์โหลด',
    'Search or open link': 'ค้นหาหรือเปิดลิงก์',
    'Search result limit': 'จำนวนผลการค้นหาสูงสุด',
    'Search text or paste a link': 'พิมพ์คำค้นหาหรือวางลิงก์',
    'Search type': 'ประเภทการค้นหา',
    'Settings': 'ตั้งค่า',
    'Settings saved': 'บันทึกการตั้งค่าแล้ว',
    'Speed at maximum': 'ความเร็วสูงสุดแล้ว',
    'Speed at minimum': 'ความเร็วต่ำสุดแล้ว',
    'Speed reset': 'รีเซ็ตความเร็วแล้ว',
    'Stop': 'หยุด',
    'Stopped': 'หยุดแล้ว',
    'Tab changed': 'เปลี่ยนแท็บแล้ว',
    'Thai': 'ไทย',
    'This playlist is empty': 'เพลย์ลิสต์นี้ว่างเปล่า',
    'Unknown playlist': 'ไม่ทราบชื่อเพลย์ลิสต์',
    'Unknown title': 'ไม่ทราบชื่อเรื่อง',
    'Video': 'วิดีโอ',
    'Video resolution': 'ความละเอียดวิดีโอ',
    'Videos': 'วิดีโอ',
    'Shorts': 'Shorts',
    'Volume at maximum': 'เสียงดังสุดแล้ว',
    'Volume muted': 'ปิดเสียงแล้ว',
    'Warning': 'คำเตือน',
    'YouTube Access Pro already open': 'เปิด YouTube Access Pro อยู่แล้ว',
    'playlist link': 'ลิงก์เพลย์ลิสต์',
    'restart NVDA to use it': 'รีสตาร์ต NVDA เพื่อใช้งาน',
    'unknown': 'ไม่ทราบ',
    'video link': 'ลิงก์วิดีโอ',
    'yt dlp error': 'yt-dlp ผิดพลาด',
    'yt-dlp library': 'ไลบรารี yt-dlp',
    '  {} of {}': '  {} จาก {}',
    ' ({})': ' ({})',
    ' - {}': ' - {}',
    'Added to {} playlist': 'เพิ่มลงเพลย์ลิสต์ {} แล้ว',
    'Already downloading {} for this link': 'กำลังดาวน์โหลด {} สำหรับลิงก์นี้อยู่แล้ว',
    'Already in {} playlist': 'มีอยู่ในเพลย์ลิสต์ {} แล้ว',
    'Canceled and removed {} files': 'ยกเลิกและลบไฟล์ไปแล้ว {} ไฟล์',
    'Copied {}': 'คัดลอก {} แล้ว',
    'Current version: {}': 'เวอร์ชันปัจจุบัน: {}',
    'Current version: {} ({})': 'เวอร์ชันปัจจุบัน: {} ({})',
    'Download completed  {}  {}': 'ดาวน์โหลดเสร็จแล้ว  {}  {}',
    'Download queued  {} items': 'อยู่ในคิวดาวน์โหลด  {} รายการ',
    'Download starting  {}  {}': 'เริ่มดาวน์โหลด  {}  {}',
    'FFmpeg is missing:\n{}': 'ไม่พบ FFmpeg:\n{}',
    'MP3  {} {}  MP4  {} {}': 'MP3  {} {}  MP4  {} {}',
    'Next  {}': 'ถัดไป  {}',
    'Now playing  {}': 'กำลังเล่น  {}',
    'Playing  {}': 'กำลังเล่น  {}',
    'Playlist  {}': 'เพลย์ลิสต์  {}',
    'Playlist  {}  1 of 1': 'เพลย์ลิสต์  {}  1 จาก 1',
    'Playlist  {}  {} items': 'เพลย์ลิสต์  {}  {} รายการ',
    'Playlist downloading  MP3  {}  MP4  {}': 'กำลังดาวน์โหลดเพลย์ลิสต์  MP3  {}  MP4  {}',
    'Previous  {}': 'ก่อนหน้า  {}',
    'Remove  {}  from this playlist': 'ลบ  {}  ออกจากเพลย์ลิสต์นี้',
    'Speed  {}': 'ความเร็ว  {}',
    'Volume  {}': 'เสียง  {}',
    'YouTube Access Pro  Now playing  {}': 'YouTube Access Pro  กำลังเล่น  {}',
    'yt-dlp error:\n{}': 'yt-dlp ผิดพลาด:\n{}',
    'yt-dlp update failed: {}': 'อัปเดต yt-dlp ไม่สำเร็จ: {}',
    'yt-dlp updated to {}. Restart NVDA to use it.': 'อัปเดต yt-dlp เป็น {} แล้ว รีสตาร์ต NVDA เพื่อใช้งาน',
    'yt-dlp {} is already up to date': 'yt-dlp {} เป็นเวอร์ชันล่าสุดอยู่แล้ว',
    '{}  tab': '{}  แท็บ',
    '{} ({})': '{} ({})',
    '{} - {} [{}]': '{} - {} [{}]',
    '{} [{}]': '{} [{}]',
    '{} links downloading': 'กำลังดาวน์โหลด {} ลิงก์',
    '{} {} in progress. Exit and cancel all downloads?': '{} {} กำลังดำเนินการอยู่ ต้องการออกและยกเลิกการดาวน์โหลดทั้งหมดหรือไม่',
    'download': 'การดาวน์โหลด',
    'downloads': 'การดาวน์โหลด',
    'item': 'รายการ',
    'items': 'รายการ',
    'Switched the interface menu to {}': 'เปลี่ยนเมนูการใช้งานเป็นภาษา{}',
    'Playlists help. This tab has two lists: your saved playlists, and the songs inside the one you have selected. Press Tab to move between them. Use the arrow keys to move around, and press Enter or F7 to play. On the playlist list: F1 and F2 download the whole playlist as audio or video, F3 announces its download status, F4 announces how many downloads are running, F5 opens the download folder, R renames the playlist, Delete removes it after asking you to confirm. On the song list: F7 plays from that song onward, Space pauses or resumes, F1 and F2 download the selected song as audio or video, F3 announces its download status, Delete removes it from the playlist after asking you to confirm, Control+C copies its link. F9 and F10 go to the previous or next track, F11 and F12 turn the volume down or up. Press Control+F1 again on any tab to hear its own help.': 'วิธีใช้หน้าเพลย์ลิสต์ แท็บนี้มีสองรายการ คือเพลย์ลิสต์ที่บันทึกไว้ และเพลงภายในเพลย์ลิสต์ที่เลือก กด Tab เพื่อสลับไปมาระหว่างสองรายการนี้ ใช้ปุ่มลูกศรเลื่อนดู แล้วกด Enter หรือ F7 เพื่อเล่น ในรายการเพลย์ลิสต์ F1 และ F2 ดาวน์โหลดทั้งเพลย์ลิสต์เป็นเสียงหรือวิดีโอ F3 แจ้งสถานะการดาวน์โหลด F4 แจ้งจำนวนการดาวน์โหลดที่กำลังทำงาน F5 เปิดโฟลเดอร์ดาวน์โหลด R เปลี่ยนชื่อเพลย์ลิสต์ Delete ลบเพลย์ลิสต์หลังจากถามยืนยันก่อน ในรายการเพลง F7 เล่นต่อจากเพลงนั้น Space หยุดชั่วคราวหรือเล่นต่อ F1 และ F2 ดาวน์โหลดเพลงที่เลือกเป็นเสียงหรือวิดีโอ F3 แจ้งสถานะการดาวน์โหลด Delete ลบออกจากเพลย์ลิสต์หลังจากถามยืนยันก่อน Control+C คัดลอกลิงก์ F9 และ F10 ไปยังเพลงก่อนหน้าหรือถัดไป F11 และ F12 ลดหรือเพิ่มเสียง กด Control+F1 อีกครั้งในแท็บใดก็ได้เพื่อฟังวิธีใช้ของแท็บนั้น',
    '  {} subscribers': '  ผู้ติดตาม {} คน',
    'Already subscribed to {}': 'ติดตามช่อง {} อยู่แล้ว',
    'Automatically play the next item when the current one ends': 'เล่นรายการถัดไปโดยอัตโนมัติเมื่อรายการปัจจุบันจบ',
    'Cannot find channel information for this item': 'ไม่พบข้อมูลช่องของรายการนี้',
    'Channel': 'ช่อง',
    'Channel  {}': 'ช่อง  {}',
    'Channel content': 'เนื้อหาของช่อง',
    'Channel downloading  MP3  {}  MP4  {}': 'ช่องกำลังดาวน์โหลด  MP3  {}  MP4  {}',
    'Global player announce sleep timer remaining time when mpv is running': 'แจ้งเวลาที่เหลือของตัวจับเวลาปิดทั่วทั้งระบบขณะที่ mpv กำลังทำงาน',
    'Global player sleep timer decrease when mpv is running': 'ลดเวลาของตัวจับเวลาปิดทั่วทั้งระบบขณะที่ mpv กำลังทำงาน',
    'Global player sleep timer increase when mpv is running': 'เพิ่มเวลาของตัวจับเวลาปิดทั่วทั้งระบบขณะที่ mpv กำลังทำงาน',
    'Live': 'ถ่ายทอดสด',
    'Live stream  opening in your browser for stable playback': 'ถ่ายทอดสด  กำลังเปิดในเบราว์เซอร์เพื่อความเสถียร',
    'No channel selected': 'ไม่ได้เลือกช่อง',
    'No downloads for this channel': 'ไม่มีการดาวน์โหลดสำหรับช่องนี้',
    'No subscribed channels': 'ยังไม่ได้ติดตามช่องใดเลย',
    'Open channel contents to download items': 'เปิดดูรายการของช่องก่อนเพื่อดาวน์โหลด',
    'Play advance warnings before the sleep timer stops playback': 'เตือนล่วงหน้าก่อนตัวจับเวลาปิดจะหยุดเล่นเพลง',
    'Playback will stop in 1 minute': 'จะหยุดเล่นเพลงในอีก 1 นาที',
    'Reached the end of the list': 'ถึงรายการสุดท้ายแล้ว',
    'Sleep timer at maximum': 'ตั้งเวลาปิดสูงสุดแล้ว',
    'Sleep timer off': 'ปิดตัวจับเวลาแล้ว',
    'Sleep timer reached  stopped playback': 'ถึงเวลาปิดแล้ว หยุดเล่นเพลง',
    'Sleep timer set to {} minutes': 'ตั้งเวลาปิดใน {} นาที',
    'Subscribed channels': 'ช่องที่ติดตาม',
    'Subscribed to {}': 'ติดตามช่อง {} แล้ว',
    'Subscriptions': 'ติดตาม',
    'Subscriptions backup': 'สำรองรายชื่อช่องที่ติดตาม',
    'Unknown channel': 'ไม่ทราบชื่อช่อง',
    'Unsubscribe  Del': 'เลิกติดตาม  Del',
    'Unsubscribe from {}': 'เลิกติดตามช่อง {} ใช่หรือไม่',
    'Unsubscribed from {}': 'เลิกติดตามช่อง {} แล้ว',
    'channel link': 'ลิงก์ช่อง',
    'Exported {} channels': 'ส่งออกช่อง {} ช่องแล้ว',
    'Imported {} new channels': 'นำเข้าช่องใหม่ {} ช่องแล้ว',
    '{} minutes {} seconds left on the sleep timer': 'เหลือเวลา {} นาที {} วินาที ก่อนตัวจับเวลาปิดจะทำงาน',
    '{} minutes left on the sleep timer': 'เหลือเวลา {} นาที ก่อนตัวจับเวลาปิดจะทำงาน',
    '{} seconds left on the sleep timer': 'เหลือเวลา {} วินาที ก่อนตัวจับเวลาปิดจะทำงาน',
    'Search and Download help. Type text or paste a link in the search box, then press Enter. Press Tab to reach the search type control, and choose Video, Playlist, or Channel. Use the arrow keys to move through results, and press Enter to open or play the selected item; opening a playlist or a channel shows its videos in the same list. Press Backspace to go back after opening a playlist or a channel. F1 downloads the selected item as audio, F2 downloads it as video. F3 announces its download status, F4 announces how many downloads are running, F5 opens the download folder. F6 increases the sleep timer by 5 minutes, which stops playback automatically after a set time; Shift+F6 decreases it by 5 minutes, and Control+F6 announces exactly how much time is left. F7 plays or stops, F8 pauses or resumes, F9 and F10 go to the previous or next track, F11 and F12 turn the volume down or up. Shift+F7 replays the last item, Shift+F9 and Shift+F10 seek 30 seconds back or forward, Shift+F11 and Shift+F12 change the playback speed. Control+C copies the link, Control+B opens it in your browser, Control+P adds it to a playlist, Control+S subscribes to the channel of the selected item. Control+Tab switches between tabs. Press Control+F1 again on any tab to hear its own help.': 'วิธีใช้หน้าค้นหาและดาวน์โหลด พิมพ์ข้อความหรือวางลิงก์ในช่องค้นหา แล้วกด Enter กด Tab เพื่อไปที่ช่องประเภทการค้นหา แล้วเลือกวิดีโอ เพลย์ลิสต์ หรือช่อง ใช้ปุ่มลูกศรเลื่อนดูผลการค้นหา แล้วกด Enter เพื่อเปิดหรือเล่นรายการที่เลือก การเปิดเพลย์ลิสต์หรือช่องจะแสดงคลิปของมันในรายการเดียวกันนี้ กด Backspace เพื่อย้อนกลับหลังจากเปิดเพลย์ลิสต์หรือช่อง F1 ดาวน์โหลดรายการที่เลือกเป็นเสียง F2 ดาวน์โหลดเป็นวิดีโอ F3 แจ้งสถานะการดาวน์โหลด F4 แจ้งจำนวนการดาวน์โหลดที่กำลังทำงาน F5 เปิดโฟลเดอร์ดาวน์โหลด F6 เพิ่มเวลาของตัวจับเวลาปิดทีละ 5 นาที ซึ่งจะหยุดเล่นเพลงเองเมื่อครบเวลาที่ตั้งไว้ Shift+F6 ลดเวลานั้นลงทีละ 5 นาที และ Control+F6 แจ้งเวลาที่เหลืออยู่อย่างแม่นยำ F7 เล่นหรือหยุด F8 หยุดชั่วคราวหรือเล่นต่อ F9 และ F10 ไปยังเพลงก่อนหน้าหรือถัดไป F11 และ F12 ลดหรือเพิ่มเสียง Shift+F7 เล่นรายการล่าสุดซ้ำ Shift+F9 และ Shift+F10 กรอถอยหลังหรือไปข้างหน้า 30 วินาที Shift+F11 และ Shift+F12 เปลี่ยนความเร็วการเล่น Control+C คัดลอกลิงก์ Control+B เปิดในเบราว์เซอร์ Control+P เพิ่มลงเพลย์ลิสต์ Control+S ติดตามช่องของรายการที่เลือก Control+Tab สลับระหว่างแท็บ กด Control+F1 อีกครั้งในแท็บใดก็ได้เพื่อฟังวิธีใช้ของแท็บนั้น',
    'Settings help. Choose your download folder, then set video resolution and audio quality; both lists now read from lowest to highest quality. Choose how many search results to fetch. The checkboxes control whether player hotkeys are announced, whether they still work when this window does not have focus while something is playing, whether the next item in the list plays automatically when the current one ends, and whether you get advance warnings before the sleep timer stops playback  a spoken notice at 1 minute left and a short beep once per second for the last 10 seconds; turning this off leaves only the announcement and one longer confirmation beep the moment playback actually stops, which always happen. Export subscriptions saves your followed channels to a file you choose, and Import subscriptions adds channels from a previously exported file into your current list without removing any you already follow - useful when moving to a new computer or reinstalling NVDA. The yt-dlp library section shows the version in use, lets you turn automatic update checks on or off, and has a button to check for an update right now. Remember to press Save settings after making changes for them to take effect.': 'วิธีใช้หน้าตั้งค่า เลือกโฟลเดอร์ดาวน์โหลด จากนั้นตั้งค่าความละเอียดวิดีโอและคุณภาพเสียง ทั้งสองรายการเรียงจากคุณภาพต่ำสุดไปสูงสุด เลือกจำนวนผลการค้นหาที่ต้องการดึงมา ช่องกาเครื่องหมายควบคุมว่าจะแจ้งปุ่มลัดของเครื่องเล่นหรือไม่ ปุ่มลัดเหล่านั้นจะยังทำงานได้หรือไม่เมื่อหน้าต่างนี้ไม่ได้โฟกัสในขณะที่กำลังเล่นอยู่ จะเล่นรายการถัดไปอัตโนมัติเมื่อรายการปัจจุบันจบหรือไม่ และจะมีการเตือนล่วงหน้าก่อนตัวจับเวลาปิดจะหยุดเล่นเพลงหรือไม่ ซึ่งได้แก่เสียงพูดแจ้งเมื่อเหลือเวลา 1 นาที และเสียงบี๊บสั้นนับถอยหลังทีละวินาทีในช่วง 10 วินาทีสุดท้าย หากปิดตัวเลือกนี้จะเหลือเพียงการแจ้งเตือนด้วยเสียงพูดและเสียงบี๊บยาวหนึ่งครั้งตอนที่หยุดเล่นเพลงจริง ซึ่งจะมีเสมอไม่ว่าจะตั้งค่านี้ไว้อย่างไร ปุ่มส่งออกรายชื่อช่องที่ติดตามจะบันทึกช่องที่คุณติดตามไว้เป็นไฟล์ที่คุณเลือก ส่วนปุ่มนำเข้ารายชื่อช่องที่ติดตามจะเพิ่มช่องจากไฟล์ที่เคยส่งออกไว้เข้าไปในรายการปัจจุบันโดยไม่ลบช่องที่ติดตามอยู่แล้ว มีประโยชน์เมื่อย้ายเครื่องหรือติดตั้ง NVDA ใหม่ ส่วนไลบรารี yt-dlp แสดงเวอร์ชันที่ใช้งานอยู่ เปิดหรือปิดการตรวจสอบอัปเดตอัตโนมัติได้ และมีปุ่มสำหรับตรวจสอบอัปเดตทันที อย่าลืมกดบันทึกการตั้งค่าหลังจากเปลี่ยนแปลงเพื่อให้มีผล',
    "Subscriptions help. The channel list holds channels you have subscribed to. Press Tab to move to the right-hand list. On the channel list: press Enter to browse that channel, F1 and F2 download all of its latest videos as audio or video, F3 announces its download status, Delete unsubscribes after asking you to confirm. The right-hand list browses a selected channel the same way YouTube itself does: selecting a channel first shows its Videos, Shorts, Live, and Playlists sections - press Enter on one to open it. Opening Videos, Shorts, or Live shows that section's videos directly; opening Playlists shows the channel's own playlists, and pressing Enter on one of those opens its videos. Press Backspace to go back up one level at any point. Once a video is shown: F7 plays or stops, F8 pauses or resumes, F9 and F10 go to the previous or next track, F11 and F12 turn the volume down or up. Space also pauses or resumes, and Home and End turn the volume up or down. F1 and F2 download the selected video as audio or video, F3 announces its download status, F4 announces how many downloads are running, F5 opens the download folder, Control+C copies its link. To subscribe to a channel in the first place, find one of its videos on the Search and Download tab and press Control+S there. Press Control+F1 again on any tab to hear its own help.": 'วิธีใช้หน้าติดตาม รายการช่องเก็บช่องที่คุณติดตามไว้ กด Tab เพื่อไปที่รายการทางขวา ในรายการช่อง กด Enter เพื่อดูเนื้อหาของช่องนั้น F1 และ F2 ดาวน์โหลดคลิปล่าสุดทั้งหมดของช่องนั้นเป็นเสียงหรือวิดีโอ F3 แจ้งสถานะการดาวน์โหลดของช่องนั้น Delete เลิกติดตามหลังจากถามยืนยันก่อน รายการทางขวาเรียกดูช่องที่เลือกเหมือนกับ YouTube เอง เมื่อเลือกช่องจะเห็นหมวด Videos, Shorts, Live และ Playlists ก่อน กด Enter บนหมวดใดเพื่อเปิดดู การเปิด Videos, Shorts หรือ Live จะแสดงคลิปของหมวดนั้นโดยตรง ส่วนการเปิด Playlists จะแสดงเพลย์ลิสต์ของช่องนั้น กด Enter บนเพลย์ลิสต์ใดเพื่อเปิดดูคลิปในเพลย์ลิสต์นั้น กด Backspace เพื่อย้อนกลับขึ้นไปหนึ่งชั้นได้ทุกเมื่อ เมื่อเห็นคลิปแล้ว F7 เล่นหรือหยุด F8 หยุดชั่วคราวหรือเล่นต่อ F9 และ F10 ไปยังเพลงก่อนหน้าหรือถัดไป F11 และ F12 ลดหรือเพิ่มเสียง Space หยุดชั่วคราวหรือเล่นต่อได้เช่นกัน ส่วน Home และ End เพิ่มหรือลดเสียง F1 และ F2 ดาวน์โหลดคลิปที่เลือกเป็นเสียงหรือวิดีโอ F3 แจ้งสถานะการดาวน์โหลด F4 แจ้งจำนวนการดาวน์โหลดที่กำลังทำงาน F5 เปิดโฟลเดอร์ดาวน์โหลด Control+C คัดลอกลิงก์ ส่วนวิธีติดตามช่องในตอนแรก ให้ไปหาคลิปของช่องนั้นในแท็บค้นหาและดาวน์โหลด แล้วกด Control+S ที่คลิปนั้น กด Control+F1 อีกครั้งในแท็บใดก็ได้เพื่อฟังวิธีใช้ของแท็บนั้น',
    'YouTube Access Pro': 'YouTube Access Pro',
}

state._current_ui_language = 'en'


def set_ui_language(lang):
    if lang not in ('en', 'th'):
        lang = 'en'
    state._current_ui_language = lang


def toggle_ui_language():
    set_ui_language('th' if state._current_ui_language == 'en' else 'en')
    return state._current_ui_language


def _translate_text(text):
    """Look up a static string's Thai translation. Falls back to the
    original English text if no translation is available yet, so a
    missing dictionary entry never results in blank or broken text."""
    if state._current_ui_language == 'th':
        return TH_STRINGS.get(text, text)
    return text


# Shadowing the addonHandler-injected builtin `_` with a module-level `_`
# makes every existing _('...') call site in this file toggle-aware
# automatically, without needing to change any of them individually.
_ = _translate_text


def _tr(template, *args, **kwargs):
    """Translate a template string (using {} placeholders) and format it
    with the given values. Falls back to formatting the original English
    template if the translated one has mismatched placeholders."""
    translated = _translate_text(template)
    try:
        return translated.format(*args, **kwargs)
    except Exception:
        try:
            return template.format(*args, **kwargs)
        except Exception:
            return template


def _plural(count, singular, plural):
    """Return the translated singular or plural word for count."""
    return _translate_text(singular) if count == 1 else _translate_text(plural)


# safe _ui_message wrapper for main thread vs worker thread
_ui_message_orig = getattr(ui, 'message', None)


def _ui_message(msg):
    try:
        if _ui_message_orig is None:
            return
        if threading.current_thread() is threading.main_thread():
            _ui_message_orig(msg)
        else:
            wx.CallAfter(_ui_message_orig, msg)
    except Exception:
        try:
            if _ui_message_orig is not None:
                _ui_message_orig(str(msg))
        except Exception:
            pass


def _ui_message_later(msg, delay_ms=200):
    try:
        if _ui_message_orig is None:
            return
        d = int(delay_ms) if delay_ms is not None else 200
        if d < 0:
            d = 0

        def _do():
            try:
                _ui_message_orig(msg)
            except Exception:
                pass

        if threading.current_thread() is threading.main_thread():
            try:
                wx.CallLater(d, _do)
            except Exception:
                wx.CallAfter(_do)
        else:
            wx.CallAfter(lambda: wx.CallLater(d, _do))
    except Exception:
        try:
            _ui_message(msg)
        except Exception:
            pass


import traceback
import time
import re
import tempfile
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs, quote_plus
import urllib.request
import urllib.error
import shutil
import zipfile
from logHandler import log

# --- PATHS AND FIXED SETTINGS ---
addon_dir = os.path.dirname(__file__)
lib_path = os.path.join(addon_dir, 'lib')
ffmpeg_folder = os.path.join(lib_path, 'ffmpeg')
ffmpeg_exe = os.path.join(ffmpeg_folder, 'ffmpeg.exe')
config_file = os.path.join(addon_dir, 'config.json')

# renamed to avoid confusion with mpv playlist file argument name
playlists_json_path = os.path.join(addon_dir, 'playlists.json')
subscriptions_json_path = os.path.join(addon_dir, 'subscriptions.json')

# mpv paths
mpv_folder = os.path.join(lib_path, 'mpv')
mpv_exe = os.path.join(mpv_folder, 'mpv.exe')

# Fixed path for mpv's own diagnostic log (see _start_playback_now(), which
# clears this before every playback attempt and passes it to mpv via
# --log-file so a real reason for any unexpected stop is available to read
# afterward, instead of only ever seeing this add-on's own "Playback ended"
# message with no insight into why mpv itself exited).
_MPV_LOG_PATH = os.path.join(tempfile.gettempdir(), 'ytdlp_addon_mpv_log.txt')

if lib_path not in sys.path:
    sys.path.insert(0, lib_path)


# --- STANDARD LIBRARY SHIMS ---
# NVDA's bundled Python does not include every standard library module
# (fileinput.py and optparse.py alongside this file exist for the same
# reason). Rather than relying on a plain file sitting on sys.path -
# which some restricted/frozen Python builds do not consult for names
# that look like standard-library modules - the replacement is registered
# directly in sys.modules. Python always checks sys.modules first, before
# any finder runs, so this works regardless of how the missing module was
# excluded.

def _install_stdlib_shim(name, populate):
    if name in sys.modules:
        return
    try:
        __import__(name)
        return
    except Exception:
        pass
    try:
        import types
        module = types.ModuleType(name)
        populate(module.__dict__)
        sys.modules[name] = module
    except Exception as e:
        log.error(f'Failed to install {name} shim: {e}')


def _populate_secrets_shim(ns):
    import base64
    import binascii
    from hmac import compare_digest
    from random import SystemRandom

    sysrand = SystemRandom()

    def randbelow(exclusive_upper_bound):
        if exclusive_upper_bound <= 0:
            raise ValueError('Upper bound must be positive.')
        return sysrand._randbelow(exclusive_upper_bound)

    def token_bytes(nbytes=None):
        if nbytes is None:
            nbytes = 32
        return os.urandom(nbytes)

    def token_hex(nbytes=None):
        return binascii.hexlify(token_bytes(nbytes)).decode('ascii')

    def token_urlsafe(nbytes=None):
        tok = token_bytes(nbytes)
        return base64.urlsafe_b64encode(tok).rstrip(b'=').decode('ascii')

    ns.update({
        '__all__': ['choice', 'randbelow', 'randbits', 'SystemRandom',
                     'token_bytes', 'token_hex', 'token_urlsafe', 'compare_digest'],
        'SystemRandom': SystemRandom,
        'compare_digest': compare_digest,
        'randbits': sysrand.getrandbits,
        'choice': sysrand.choice,
        'randbelow': randbelow,
        'DEFAULT_ENTROPY': 32,
        'token_bytes': token_bytes,
        'token_hex': token_hex,
        'token_urlsafe': token_urlsafe,
    })


_install_stdlib_shim('secrets', _populate_secrets_shim)

# yt-dlp import
yt_dlp = None
library_error = None
try:
    import yt_dlp
except Exception as e:
    library_error = str(e)
    log.error(f'Library error: {library_error}')


# --- YT-DLP LIBRARY AUTO-UPDATE ---
# YouTube regularly changes how it serves pages, which is the single most
# common reason a downloader stops working. yt-dlp publishes fixes for this
# very frequently. Rather than requiring the user to manually replace the
# bundled library, this checks PyPI (yt-dlp's official release channel) and
# can download and install a newer copy directly into this add-on.
#
# The update only replaces files inside lib/yt_dlp on disk; because Python
# has already loaded the previous copy into memory, the new version takes
# effect the next time NVDA is restarted (the user is told this).

YTDLP_UPDATE_CHECK_URL = 'https://pypi.org/pypi/yt-dlp/json'
YTDLP_UPDATE_CHECK_TIMEOUT = 20
YTDLP_UPDATE_DOWNLOAD_TIMEOUT = 180
YTDLP_UPDATE_CHECK_INTERVAL_SEC = 24 * 60 * 60  # at most once a day automatically
YTDLP_UPDATE_USER_AGENT = 'YouTubeProDownloaderNVDA-Updater/1.0'

state._ytdlp_update_lock = threading.Lock()
state._ytdlp_update_in_progress = False


def _get_bundled_ytdlp_version():
    try:
        return str(yt_dlp.version.__version__)
    except Exception:
        return None


def _normalize_version_str(value):
    """Normalize a dotted version string for comparison.

    yt-dlp's own version.py uses zero-padded date segments (e.g.
    "2026.07.04"), while PyPI reports the PEP 440 canonical form with
    leading zeros stripped (e.g. "2026.7.4"). Both mean the same release,
    so comparisons must normalize both sides the same way rather than
    comparing the raw strings.
    """
    try:
        parts = str(value).split('.')
        normalized = []
        for part in parts:
            digits = ''
            for ch in part:
                if ch.isdigit():
                    digits += ch
                else:
                    break
            normalized.append(str(int(digits)) if digits else part)
        return '.'.join(normalized)
    except Exception:
        return str(value)


def _fetch_latest_ytdlp_release():
    """Ask PyPI for the latest published yt-dlp version, its wheel URL, and
    the sha256 digest PyPI publishes for that exact file.

    Returns (version, wheel_url, sha256_hex) or (None, None, None) on any
    failure (offline, PyPI unreachable, unexpected response, etc). Never
    raises. sha256_hex may be None even when a version/URL is found, if
    PyPI's response happens not to include a digest for that file - callers
    should treat that as "cannot verify" rather than "definitely bad".
    """
    try:
        req = urllib.request.Request(
            YTDLP_UPDATE_CHECK_URL,
            headers={'User-Agent': YTDLP_UPDATE_USER_AGENT},
        )
        with urllib.request.urlopen(req, timeout=YTDLP_UPDATE_CHECK_TIMEOUT) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        latest_version = data.get('info', {}).get('version')
        if not latest_version:
            return None, None, None
        files = data.get('releases', {}).get(latest_version, []) or []
        wheel_url = None
        sha256_hex = None
        for f in files:
            fname = str(f.get('filename', ''))
            if f.get('packagetype') == 'bdist_wheel' and fname.endswith('-py3-none-any.whl'):
                wheel_url = f.get('url')
                sha256_hex = (f.get('digests') or {}).get('sha256')
                break
        return latest_version, wheel_url, sha256_hex
    except Exception as e:
        log.error(f'yt-dlp update check failed: {e}')
        return None, None, None


def _download_and_install_ytdlp(wheel_url, expected_sha256=None):
    """Download a yt-dlp wheel and atomically replace lib/yt_dlp with it.

    If expected_sha256 is provided (PyPI's own published digest for this
    exact file), the downloaded bytes are hashed and compared before the
    archive is ever opened or extracted; a mismatch aborts the install
    without touching the existing working copy. This guards against a
    corrupted download or a tampered response, since the update otherwise
    replaces code that runs inside the NVDA process.

    Returns (True, None) on success or (False, error_message) on failure.
    On failure the previously working copy is left in place untouched.
    """
    tmp_whl = None
    staging_dir = None
    try:
        fd, tmp_whl = tempfile.mkstemp(prefix='ytdlp_update_', suffix='.whl')
        os.close(fd)

        req = urllib.request.Request(wheel_url, headers={'User-Agent': YTDLP_UPDATE_USER_AGENT})
        hasher = hashlib.sha256()
        with urllib.request.urlopen(req, timeout=YTDLP_UPDATE_DOWNLOAD_TIMEOUT) as resp, open(tmp_whl, 'wb') as out:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                hasher.update(chunk)
                out.write(chunk)

        if expected_sha256:
            actual = hasher.hexdigest()
            if actual.lower() != str(expected_sha256).lower():
                log.error(f'yt-dlp update sha256 mismatch: expected {expected_sha256}, got {actual}')
                return False, 'Downloaded file failed integrity check (sha256 mismatch)'

        staging_dir = tempfile.mkdtemp(prefix='ytdlp_staging_')
        with zipfile.ZipFile(tmp_whl) as z:
            members = [n for n in z.namelist() if n.startswith('yt_dlp/')]
            if not members:
                return False, 'Downloaded package did not contain yt_dlp'
            z.extractall(staging_dir, members=members)

        extracted_pkg = os.path.join(staging_dir, 'yt_dlp')
        for required in ('version.py', 'YoutubeDL.py', '__init__.py'):
            if not os.path.isfile(os.path.join(extracted_pkg, required)):
                return False, f'Downloaded package is missing {required}'

        target = os.path.join(lib_path, 'yt_dlp')
        backup = os.path.join(lib_path, f'yt_dlp.bak_{int(time.time())}')

        if os.path.isdir(target):
            os.rename(target, backup)
        try:
            shutil.move(extracted_pkg, target)
        except Exception:
            if os.path.isdir(backup) and not os.path.isdir(target):
                os.rename(backup, target)
            raise

        if os.path.isdir(backup):
            shutil.rmtree(backup, ignore_errors=True)

        return True, None
    except Exception as e:
        log.error(f'yt-dlp update install failed: {e}')
        return False, str(e)
    finally:
        try:
            if tmp_whl and os.path.exists(tmp_whl):
                os.remove(tmp_whl)
        except Exception:
            pass
        try:
            if staging_dir and os.path.isdir(staging_dir):
                shutil.rmtree(staging_dir, ignore_errors=True)
        except Exception:
            pass


def check_for_ytdlp_update(manual=False, on_done=None):
    """Check PyPI for a newer yt-dlp and install it if one is found.

    Always runs the network work on a background thread. Safe to call from
    the UI thread. `on_done(found_update, message)` is invoked on the main
    thread when finished if provided (used to update the Settings tab).
    """

    with state._ytdlp_update_lock:
        if state._ytdlp_update_in_progress:
            if manual:
                _ui_message(_('Already checking for an update'))
            return
        state._ytdlp_update_in_progress = True

    if manual:
        _ui_message(_('Checking for yt-dlp update'))

    def _finish(found_update, message):
        with state._ytdlp_update_lock:
            state._ytdlp_update_in_progress = False
        try:
            settings = load_settings()
            settings['last_ytdlp_update_check'] = time.time()
            save_settings(settings)
        except Exception:
            pass
        if manual:
            _ui_message(message)
        if on_done:
            try:
                on_done(found_update, message)
            except Exception:
                pass

    def _worker():
        current = _get_bundled_ytdlp_version()
        latest, wheel_url, sha256_hex = _fetch_latest_ytdlp_release()

        if not latest:
            wx.CallAfter(_finish, False, _('Could not check for updates  no connection to PyPI'))
            return

        if not wheel_url or _normalize_version_str(latest) == _normalize_version_str(current):
            wx.CallAfter(_finish, False, _tr('yt-dlp {} is already up to date', current or '?'))
            return

        ok, err = _download_and_install_ytdlp(wheel_url, expected_sha256=sha256_hex)
        if ok:
            msg = _tr('yt-dlp updated to {}. Restart NVDA to use it.', latest)
            wx.CallAfter(_finish, True, msg)
        else:
            wx.CallAfter(_finish, False, _tr('yt-dlp update failed: {}', err))

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def maybe_auto_check_for_ytdlp_update():
    """Run the update check automatically at most once a day, only if the
    user has not disabled it in Settings, and never on a secure desktop."""
    if _is_secure_mode():
        return
    try:
        settings = load_settings()
        if not settings.get('auto_update_ytdlp', True):
            return
        last_check = float(settings.get('last_ytdlp_update_check') or 0)
    except Exception:
        return
    if (time.time() - last_check) < YTDLP_UPDATE_CHECK_INTERVAL_SEC:
        return
    check_for_ytdlp_update(manual=False)


# --- DOWNLOAD STATE ---
state.active_downloads = {}
state.download_lock = threading.Lock()

# --- PLAYER STATE ---
state.player_proc = None
state.player_lock = threading.Lock()
state.player_paused = False
state.mpv_ipc_path = None

# session-only volume memory
state.current_volume = None
state.current_playing_url = None

# session-only playback speed memory
SPEED_VALUES = [
    0.50, 0.60, 0.70, 0.80, 0.90, 1.00, 1.10, 1.20, 1.30, 1.40, 1.50, 1.60, 1.70, 1.80, 1.90, 2.00,
]
# keep selected speed for the whole NVDA session until Exit or NVDA closes
state.current_speed_index = SPEED_VALUES.index(1.0)

# track current playlist temp file for mpv
state.current_playlist_file = None

# identify playlist origin currently playing
state.current_playlist_origin_url = None

# remember playlist start url for single key behavior
state.current_playlist_start_url = None

# remember last play request for Shift+F7
state.last_play_request = None

# track list for prev/next navigation (search results or playlist)
state.current_track_items = []   # list of {url, title, ...}
state.current_track_index = -1   # current position in state.current_track_items

# runtime settings cache
state.runtime_announce_player_keys = True
state.runtime_global_player_hotkeys = False
state.runtime_auto_continue_playback = False
state.runtime_sleep_timer_beep_warning = True

# player watchdog
state._player_watchdog_started = False
state._player_watchdog_stop_event = threading.Event()

# --- SEARCH STATE PERSISTENCE ---
state.last_search_items = []
state.last_search_video_data = []
state.last_search_selected_index = None
state.last_search_query = ''

# --- PLAYLIST CONTENT CACHE ---
state._playlist_lock = threading.Lock()
state._playlist_cache = {}
state._playlist_waiters = {}
state._playlist_inflight = set()

# cache policy
PLAYLIST_CACHE_MAX = 50
PLAYLIST_CACHE_TTL_SEC = 7200


def _format_duration_seconds(sec):
    try:
        sec = int(sec)
    except Exception:
        return ''
    if sec < 0:
        return ''
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if h > 0:
        return f'{h}:{m:02d}:{s:02d}'
    return f'{m}:{s:02d}'


def _extract_playlist_id(url):
    try:
        u = urlparse(url)
        qs = parse_qs(u.query or '')
        lst = qs.get('list')
        if lst and lst[0]:
            return lst[0]
    except Exception:
        return None
    return None


def _is_playlist_id_candidate(pid):
    try:
        pid = (pid or '').strip()
    except Exception:
        return False
    if not pid:
        return False
    # exclude common non-user playlists and mixes
    bad = ('RD', 'UL', 'WL', 'LL', 'ML', 'PU')
    for b in bad:
        if pid.startswith(b):
            return False
    # accept common playlist id prefixes
    good = ('PL', 'OLAK', 'UU', 'FL')
    if pid.startswith(good):
        return True
    # fallback for unknown but plausible ids
    return len(pid) >= 10



def _normalize_playlist_url(url):
    pid = _extract_playlist_id(url)
    if pid:
        return f'https://www.youtube.com/playlist?list={pid}'
    return url


def _is_probably_playlist_url(url):
    try:
        pid = _extract_playlist_id(url)
        if pid:
            return True
        u = urlparse(url)
        if 'playlist' in (u.path or ''):
            return True
    except Exception:
        return False
    return False


def _is_probably_channel_url(url):
    try:
        u = urlparse(url)
        path = (u.path or '').strip('/')
        if not path:
            return False
        if path.startswith('channel/') or path.startswith('c/') or path.startswith('user/'):
            return True
        if path.startswith('@'):
            return True
    except Exception:
        return False
    return False


def _normalize_channel_url(url):
    try:
        u = urlparse(url)
        path = (u.path or '').rstrip('/')
        if path:
            return f'https://www.youtube.com{path}'
    except Exception:
        pass
    return url


_CHANNEL_TAB_NAMES = frozenset(('videos', 'streams', 'shorts', 'playlists', 'community', 'about', 'featured'))


def _channel_tab_url(channel_url, tab_name):
    """Point at a specific tab of a channel (e.g. 'videos', 'shorts',
    'streams' for Live, 'playlists') instead of its bare URL. A bare
    channel URL (e.g. https://www.youtube.com/@name) resolves to the
    channel's Home tab, which YouTube lets the channel owner curate and
    reorder by hand - it is not reliably sorted newest-first and can
    leave out content entirely, so every place that browses a specific
    section of a subscribed channel needs the actual tab URL, not Home."""
    try:
        u = (channel_url or '').rstrip('/')
        if not u:
            return channel_url
        last_seg = u.rsplit('/', 1)[-1].lower()
        if last_seg in _CHANNEL_TAB_NAMES:
            u = u.rsplit('/', 1)[0]
        return u + '/' + tab_name
    except Exception:
        return channel_url


def _channel_videos_tab_url(channel_url):
    return _channel_tab_url(channel_url, 'videos')


def _channel_shorts_tab_url(channel_url):
    return _channel_tab_url(channel_url, 'shorts')


def _channel_live_tab_url(channel_url):
    return _channel_tab_url(channel_url, 'streams')


def _channel_playlists_tab_url(channel_url):
    return _channel_tab_url(channel_url, 'playlists')


def _build_watch_url_from_id(v_id):
    if not v_id:
        return ''
    return f'https://www.youtube.com/watch?v={v_id}'


def _extract_channel_url(vid):
    """Best-effort extraction of a channel/uploader URL from a yt-dlp
    flat search-result dict, used for the Ctrl+S subscribe action.
    Field availability can vary by extractor version, so several known
    field names are tried in order before giving up."""
    try:
        for key in ('channel_url', 'uploader_url'):
            v = vid.get(key)
            if v:
                return v
        cid = vid.get('channel_id')
        if cid:
            return f'https://www.youtube.com/channel/{cid}'
        uid = vid.get('uploader_id')
        if uid:
            if isinstance(uid, str) and uid.startswith('@'):
                return f'https://www.youtube.com/{uid}'
            return f'https://www.youtube.com/channel/{uid}'
    except Exception:
        pass
    return None


def _build_playlist_url_from_entry(entry):
    webpage = entry.get('webpage_url') or entry.get('original_url') or ''
    if webpage and 'list=' in webpage:
        return _normalize_playlist_url(webpage)

    u = entry.get('url') or ''
    if u and 'list=' in u:
        return _normalize_playlist_url(u)

    pid = entry.get('id') or ''
    if pid and (pid.startswith('PL') or pid.startswith('OLAK') or pid.startswith('RD') or pid.startswith('UU')):
        return f'https://www.youtube.com/playlist?list={pid}'

    if u and (u.startswith('http://') or u.startswith('https://')):
        if 'playlist' in u or 'list=' in u:
            return _normalize_playlist_url(u)

    if u and not (u.startswith('http://') or u.startswith('https://')):
        if u.startswith('PL') or u.startswith('OLAK') or u.startswith('RD') or u.startswith('UU'):
            return f'https://www.youtube.com/playlist?list={u}'

    return webpage or u


def _safe_write_text(path, text):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        return True
    except Exception:
        return False


def _safe_write_json(path, data, encoding='utf-8', indent=4, ensure_ascii=True):
    tmp = path + '.tmp'
    bak = path + '.bak'
    try:
        folder = os.path.dirname(path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        with open(tmp, 'w', encoding=encoding) as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass

        if os.path.exists(path):
            try:
                os.replace(path, bak)
            except Exception:
                try:
                    import shutil
                    shutil.copy2(path, bak)
                except Exception:
                    pass

        os.replace(tmp, path)
        return True
    except Exception as e:
        try:
            log.error(f'JSON write error: {e}  path: {path}')
        except Exception:
            pass
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return False


def _safe_load_json_dict(path, encoding='utf-8'):
    try:
        if not path or not os.path.exists(path):
            return None
        with open(path, 'r', encoding=encoding) as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception as e:
        try:
            log.error(f'JSON load error: {e}  path: {path}')
        except Exception:
            pass
    return None


def _create_temp_m3u(items, title=''):
    fd = None
    path = None
    try:
        fd, path = tempfile.mkstemp(prefix='ytdlp_', suffix='.m3u', dir=tempfile.gettempdir(), text=True)
        os.close(fd)
        lines = ['#EXTM3U\n']
        for it in items:
            u = (it.get('url') or '').strip()
            if not u:
                continue
            t = (it.get('title') or '').strip()
            dur = it.get('duration') or ''
            dur_sec = -1
            try:
                if isinstance(dur, int):
                    dur_sec = dur
            except Exception:
                dur_sec = -1
            lines.append(f'#EXTINF:{dur_sec},{t}\n')
            lines.append(u + '\n')
        ok = _safe_write_text(path, ''.join(lines))
        if not ok:
            try:
                os.remove(path)
            except Exception:
                pass
            return None
        return path
    except Exception:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        return None


def _set_runtime_from_settings(settings):
    try:
        state.runtime_announce_player_keys = bool(settings.get('announce_player_keys', True))
    except Exception:
        state.runtime_announce_player_keys = True
    try:
        state.runtime_global_player_hotkeys = bool(settings.get('global_player_hotkeys', False))
    except Exception:
        state.runtime_global_player_hotkeys = False
    try:
        state.runtime_auto_continue_playback = bool(settings.get('auto_continue_playback', False))
    except Exception:
        state.runtime_auto_continue_playback = False
    try:
        state.runtime_sleep_timer_beep_warning = bool(settings.get('sleep_timer_beep_warning', True))
    except Exception:
        state.runtime_sleep_timer_beep_warning = True
    try:
        set_ui_language(settings.get('ui_language', 'en'))
    except Exception:
        pass


def _get_runtime_announce():
    try:
        return bool(state.runtime_announce_player_keys)
    except Exception:
        return True


def _get_runtime_global_hotkeys():
    try:
        return bool(state.runtime_global_player_hotkeys)
    except Exception:
        return False


def _get_runtime_auto_continue():
    try:
        return bool(state.runtime_auto_continue_playback)
    except Exception:
        return False


def _get_runtime_sleep_beep_warning():
    try:
        return bool(state.runtime_sleep_timer_beep_warning)
    except Exception:
        return True


def request_playlist_items(playlist_url, callback, limit=200, force_refresh=False, item_kind='video'):
    """Fetch a playlist's (or channel tab's) items, using a short-lived
    in-memory cache to avoid re-hitting yt-dlp for repeat requests.

    `limit` is part of the cache key: a request for a small number of items
    must never be served from - or silently overwrite - a cached fetch that
    used a different limit for the same URL (or vice versa). `force_refresh=True`
    skips serving from the cache (still updating it with the fresh result
    afterward) for callers where stale data would defeat the point of the call.

    `item_kind='playlist'` is for fetching a channel's Playlists tab, where
    each entry is itself a playlist rather than a video - it switches the
    per-entry URL building to `_build_playlist_url_from_entry()` (the same
    logic Search and Download's own playlist search results use) instead of
    building a `/watch?v=` URL from the entry's `id`, which for a playlist
    entry is a playlist ID and would silently produce a broken link.
    """
    if not playlist_url or yt_dlp is None:
        try:
            wx.CallAfter(callback, None)
        except Exception:
            pass
        return

    pl_url = _normalize_playlist_url(playlist_url)
    cache_key = f'{pl_url}::{int(limit) if limit else 0}::{item_kind}'

    with state._playlist_lock:
        cached = None if force_refresh else state._playlist_cache.get(cache_key)
        if cached and isinstance(cached, dict) and cached.get('items'):
            try:
                ts = float(cached.get('ts') or 0)
            except Exception:
                ts = 0
            if ts and (time.time() - ts) <= PLAYLIST_CACHE_TTL_SEC:
                try:
                    cached['ts'] = time.time()
                    state._playlist_cache[cache_key] = cached
                except Exception:
                    pass
                try:
                    wx.CallAfter(callback, dict(cached))
                except Exception:
                    pass
                return
            else:
                try:
                    del state._playlist_cache[cache_key]
                except Exception:
                    pass

        if cache_key in state._playlist_inflight:
            state._playlist_waiters.setdefault(cache_key, []).append(callback)
            return

        state._playlist_inflight.add(cache_key)
        state._playlist_waiters.setdefault(cache_key, []).append(callback)

    def _worker():
        data = None
        try:
            opts = {
                'quiet': True,
                'extract_flat': 'in_playlist',
                'ignoreerrors': True,
                'no_warnings': True,
            }
            if limit and isinstance(limit, int) and limit > 0:
                opts['playlistend'] = int(limit)

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(pl_url, download=False)

            if not info:
                data = None
            else:
                pl_title = info.get('title') or ''
                entries = list(info.get('entries', []) or [])
                items = []
                for v in entries:
                    if not v:
                        continue
                    title = v.get('title') or v.get('id') or _('Unknown title')
                    uploader = v.get('uploader') or v.get('channel') or ''

                    if item_kind == 'playlist':
                        # Each entry here is itself a playlist (e.g. a
                        # channel's Playlists tab), not a video - building a
                        # /watch?v= URL from its id would be wrong, since
                        # that id is a playlist id. Use the same helper
                        # Search and Download's own playlist results use.
                        full_url = _build_playlist_url_from_entry(v)
                        count = v.get('video_count') or v.get('playlist_count') or v.get('n_entries') or ''
                        items.append({
                            'kind': 'playlist',
                            'title': title,
                            'url': full_url,
                            'duration': '',
                            'count': str(count) if count else '',
                            'uploader': uploader,
                            'subfolder_title': pl_title,
                            'channel_url': _extract_channel_url(v),
                        })
                        continue

                    dur_str = v.get('duration_string') or _format_duration_seconds(v.get('duration'))
                    webpage = v.get('webpage_url') or v.get('original_url')
                    v_id = v.get('id')
                    direct = v.get('url')

                    if webpage:
                        full_url = webpage
                    elif v_id:
                        full_url = _build_watch_url_from_id(v_id)
                    else:
                        full_url = direct

                    items.append({
                        'kind': 'video',
                        'title': title,
                        'url': full_url,
                        'duration': dur_str or '',
                        'uploader': uploader,
                        'subfolder_title': pl_title,
                        # Needed so Ctrl+S (subscribe) works on items inside an
                        # opened playlist, not just on the playlist's own row.
                        'channel_url': _extract_channel_url(v),
                    })

                data = {
                    'title': pl_title,
                    'url': pl_url,
                    'items': items,
                    'ts': time.time(),
                }
        except Exception as e:
            # A failed fetch here surfaces to the user only as "No items
            # found" with no further detail, which has made every past
            # investigation of Subscriptions/playlist-loading issues start
            # from a blind code read instead of the log. Logged at debug
            # level (this is expected to fire sometimes, e.g. on a network
            # hiccup, so it should not be log.error noise).
            log.debug(f'request_playlist_items: fetch failed for {pl_url}: {e}')
            data = None

        callbacks = []
        with state._playlist_lock:
            if data:
                state._playlist_cache[cache_key] = dict(data)
                try:
                    while len(state._playlist_cache) > PLAYLIST_CACHE_MAX:
                        oldest_key = None
                        oldest_ts = None
                        for k, v in state._playlist_cache.items():
                            try:
                                tsv = float(v.get('ts') or 0)
                            except Exception:
                                tsv = 0
                            if oldest_ts is None or tsv < oldest_ts:
                                oldest_ts = tsv
                                oldest_key = k
                        if oldest_key is None or oldest_key == cache_key:
                            break
                        try:
                            del state._playlist_cache[oldest_key]
                        except Exception:
                            break
                except Exception:
                    pass
            callbacks = list(state._playlist_waiters.get(cache_key, []))
            try:
                del state._playlist_waiters[cache_key]
            except Exception:
                pass
            try:
                state._playlist_inflight.discard(cache_key)
            except Exception:
                pass

        for cb in callbacks:
            try:
                wx.CallAfter(cb, dict(data) if data else None)
            except Exception:
                pass

    t = threading.Thread(target=_worker)
    t.daemon = True
    t.start()


# --- DEFAULT SETTINGS ---
default_settings = {
    'download_folder': os.path.join(os.path.expanduser('~'), 'Downloads'),
    'search_result_limit': 25,
    'video_quality_idx': 3,  # index of 'Best  automatic' in VIDEO_QUALITY_MAP below
    'audio_quality_idx': 1,
    'announce_player_keys': True,
    'global_player_hotkeys': False,
    'auto_update_ytdlp': True,
    'last_ytdlp_update_check': 0,
    'ui_language': 'en',
    'auto_continue_playback': False,
    'last_volume': 100,
    'sleep_timer_beep_warning': True,
}

VIDEO_QUALITY_MAP = [480, 720, 1080, None]  # low to high, matches the on-screen order
AUDIO_QUALITY_MAP = ['128', '192', '320']  # low to high, matches the on-screen order
SEARCH_LIMIT_CHOICES = [25, 50, 100]


def normalize_search_limit(val):
    try:
        v = int(val)
    except Exception:
        return 25
    if v <= 25:
        return 25
    if v <= 50:
        return 50
    return 100


def _sanitize_folder_name(name, max_len=80):
    try:
        if not name:
            return ''
        n = str(name).strip()
        if not n:
            return ''

        n = re.sub(r'[\x00-\x1f]', '', n)
        n = n.replace('/', ' ').replace('\\', ' ')

        if sys.platform == 'win32':
            n = re.sub(r'[<>:"|?*]', ' ', n)
        n = n.rstrip(' .')

        n = re.sub(r'\s+', ' ', n).strip()

        if not n:
            return ''

        if sys.platform == 'win32':
            reserved = {
                'CON', 'PRN', 'AUX', 'NUL',
                'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
            }
            base = n.split('.')[0].upper()
            if base in reserved:
                n = n + '_'

        if max_len and len(n) > max_len:
            n = n[:max_len].rstrip(' .')

        return n
    except Exception:
        return ''


def load_settings():
    settings = default_settings.copy()

    loaded = _safe_load_json_dict(config_file, encoding='utf-8')
    if loaded is None:
        loaded = _safe_load_json_dict(config_file + '.bak', encoding='utf-8')
        if loaded is not None:
            _safe_write_json(config_file, loaded, encoding='utf-8', indent=4, ensure_ascii=True)

    if isinstance(loaded, dict):
        settings.update(loaded)

    settings['search_result_limit'] = normalize_search_limit(
        settings.get('search_result_limit', 25)
    )

    if 'global_player_hotkeys' not in settings:
        settings['global_player_hotkeys'] = False
    if 'video_quality_idx' not in settings:
        settings['video_quality_idx'] = 3
    if 'audio_quality_idx' not in settings:
        settings['audio_quality_idx'] = 1
    if 'auto_update_ytdlp' not in settings:
        settings['auto_update_ytdlp'] = True
    if 'last_ytdlp_update_check' not in settings:
        settings['last_ytdlp_update_check'] = 0
    if 'ui_language' not in settings or settings.get('ui_language') not in ('en', 'th'):
        settings['ui_language'] = 'en'
    if 'auto_continue_playback' not in settings:
        settings['auto_continue_playback'] = False
    if 'last_volume' not in settings:
        settings['last_volume'] = 100
    else:
        settings['last_volume'] = _clamp_volume(settings.get('last_volume', 100))
    if 'sleep_timer_beep_warning' not in settings:
        settings['sleep_timer_beep_warning'] = True

    _set_runtime_from_settings(settings)
    return settings


def save_settings(settings):
    try:
        settings = dict(settings)
        settings['search_result_limit'] = normalize_search_limit(
            settings.get('search_result_limit', 25)
        )
        if 'global_player_hotkeys' not in settings:
            settings['global_player_hotkeys'] = False

        ok = _safe_write_json(config_file, settings, encoding='utf-8', indent=4, ensure_ascii=True)
        if ok:
            _set_runtime_from_settings(settings)
        else:
            log.error('Settings save error: safe write failed')
    except Exception as e:
        log.error(f'Settings save error: {e}')


def load_playlists():
    data = _safe_load_json_dict(playlists_json_path, encoding='utf-8')
    if data is None:
        data = _safe_load_json_dict(playlists_json_path + '.bak', encoding='utf-8')
        if data is not None:
            _safe_write_json(playlists_json_path, data, encoding='utf-8', indent=4, ensure_ascii=False)
    if isinstance(data, dict):
        return data
    return {}


def save_playlists(data):
    try:
        _safe_write_json(playlists_json_path, data, encoding='utf-8', indent=4, ensure_ascii=False)
    except Exception:
        pass


def load_subscriptions():
    """Subscriptions are stored as a dict keyed by normalized channel
    URL, mirroring the playlists.json pattern (dict keys naturally
    de-duplicate by channel)."""
    data = _safe_load_json_dict(subscriptions_json_path, encoding='utf-8')
    if data is None:
        data = _safe_load_json_dict(subscriptions_json_path + '.bak', encoding='utf-8')
        if data is not None:
            _safe_write_json(subscriptions_json_path, data, encoding='utf-8', indent=4, ensure_ascii=False)
    if isinstance(data, dict):
        return data
    return {}


def save_subscriptions(data):
    try:
        _safe_write_json(subscriptions_json_path, data, encoding='utf-8', indent=4, ensure_ascii=False)
    except Exception:
        pass


def subscribe_to_channel(channel_url, channel_name):
    """Add a channel to the subscriptions list. Returns (ok, message)."""
    if not channel_url:
        return False, _('Cannot find channel information for this item')

    key = _normalize_channel_url(channel_url)
    name = (channel_name or '').strip() or key

    subs = load_subscriptions()
    if key in subs:
        existing_name = subs[key].get('channel_name') or name
        return False, _tr('Already subscribed to {}', existing_name)

    subs[key] = {
        'channel_name': name,
    }
    save_subscriptions(subs)
    return True, _tr('Subscribed to {}', name)


def open_in_system(path_or_url):
    try:
        if sys.platform == 'win32':
            os.startfile(path_or_url)
        else:
            subprocess.Popen(['xdg-open', path_or_url])
    except Exception as e:
        _ui_message(_('Error opening item'))
        wx.MessageBox(str(e), _('Error'))


def open_in_browser(url):
    webbrowser.open(url)


def copy_to_clipboard(text):
    try:
        if not text:
            return False
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
                wx.TheClipboard.Flush()
            finally:
                wx.TheClipboard.Close()
            return True
    except Exception:
        pass
    return False


def open_in_browser_background(url):
    try:
        if sys.platform == 'win32':
            subprocess.Popen(['cmd', '/c', 'start', '', '/min', url], shell=False)
        else:
            webbrowser.open(url)
    except Exception as e:
        log.error(f'Browser open error: {e}')
        _ui_message(_('Cannot open browser'))


# --- SMALL SHARED HELPERS FOR UI HOTKEYS ---

def _count_active_download_links():
    with state.download_lock:
        return sum(1 for u, fmt_map in state.active_downloads.items() if fmt_map)


def speak_downloads_running_count():
    running = _count_active_download_links()
    if running <= 0:
        _ui_message(_('No downloads running'))
    elif running == 1:
        _ui_message(_('1 link downloading'))
    else:
        _ui_message(_tr('{} links downloading', running))


def _resolve_download_folder(base_folder, subfolder_title=None):
    folder = base_folder
    try:
        safe_sub = _sanitize_folder_name(subfolder_title) if subfolder_title else ''
        if safe_sub:
            folder2 = os.path.join(base_folder, safe_sub)
            if os.path.exists(folder2):
                folder = folder2
    except Exception:
        folder = base_folder
    return folder


def open_download_folder_if_idle(base_folder, subfolder_title=None):
    running = _count_active_download_links()
    if running > 0:
        _ui_message(_('Downloads in progress'))
        return False

    folder = _resolve_download_folder(base_folder, subfolder_title=subfolder_title)
    try:
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        _ui_message(_('Opening download folder'))
        wx.CallLater(350, lambda: open_in_system(folder))
        return True
    except Exception as e:
        _ui_message(_('Error opening download folder'))
        wx.MessageBox(str(e), _('Error'))
        return False


# --- MPV PLAYER CONTROL ---

def is_player_available():
    return os.path.exists(mpv_exe)


def is_player_running():
    with state.player_lock:
        return state.player_proc is not None and state.player_proc.poll() is None


def _send_mpv_command(cmd_list):

    with state.player_lock:
        if state.player_proc is None or state.player_proc.poll() is not None:
            state.player_proc = None
            state.mpv_ipc_path = None
            return False

    # Captured into a local once, rather than re-reading state.mpv_ipc_path
    # on every retry-loop iteration below - a concurrent _cleanup_player()
    # call on another thread (e.g. the watchdog's auto-restart-on-live-exit
    # logic, or a track switch landing mid-retry) sets state.mpv_ipc_path
    # to None, and re-reading the global inside the loop let a later
    # iteration pass None straight to open(), crashing with "expected str,
    # bytes or os.PathLike object, not NoneType" instead of the intended
    # clean False return - spotted in a real NVDA log from a user testing
    # the mpv 0.41.0 upgrade (see DEV_NOTES.md round 37).
    ipc_path = state.mpv_ipc_path
    if not ipc_path:
        return False

    payload = json.dumps({'command': cmd_list}).encode('utf-8') + b'\n'

    # Open a fresh connection per command and close it right after writing.
    # A round-12 change tried reusing one persistent connection to reduce
    # per-keystroke latency, but mpv's JSON IPC protocol writes a reply for
    # every command back through the same pipe; since that reply was never
    # read, replies piled up unread in the pipe's buffer and eventually
    # stalled mpv's own command processing (surfaced as seeking working
    # briefly, then stopping under rapid Left/Right presses). Reverted back
    # to this simpler, always-reconnect approach, proven reliable across
    # every prior round - a reply written to a connection that's already
    # been closed is just dropped, so nothing accumulates.
    last_error = None
    for _ in range(30):
        try:
            with open(ipc_path, 'wb', buffering=0) as handle:
                handle.write(payload)
            last_error = None
            break
        except Exception as e:
            last_error = e
            time.sleep(0.05)

    if last_error is not None:
        log.error(f'Error sending IPC command to mpv: {last_error}')
        return False

    return True


def _mpv_set_property(prop, value):
    return _send_mpv_command(['set_property', prop, value])


# Resolving direct stream URLs ourselves (below) means single-track and
# next/previous playback always uses the bundled, up-to-date yt-dlp library
# instead of depending on mpv's own bundled youtube-dl helper to be current.
state._play_generation = 0
state._play_generation_lock = threading.Lock()


def _next_play_generation():
    with state._play_generation_lock:
        state._play_generation += 1
        return state._play_generation


def _resolve_playable_stream(url):
    """Resolve a video webpage URL to a direct, playable audio stream URL
    using the bundled yt-dlp library.

    Returns a (stream_url, is_live) tuple. stream_url is None if it could
    not be resolved (the caller should fall back to handing the original
    URL to the player, which will still try to resolve it internally), and
    is always None for a currently-live broadcast specifically - see below.
    is_live is True whenever the video is a currently-airing broadcast.

    Live streams are not resolved to a playable URL at all here - as of
    round 40, start_playback() checks is_live and opens the original
    webpage URL in the user's browser instead of ever calling this add-on's
    own mpv-based player for it (see DEV_NOTES.md round 40). Earlier
    rounds (32-34) tried several approaches to play live broadcasts inside
    mpv itself - pinning a resolved URL, picking the HLS manifest,
    auto-restarting mpv when it exited mid-broadcast - each closed one gap
    without ever reaching fully stable playback, particularly with the
    older bundled mpv 0.28.0. The browser's own native YouTube player has
    full first-party support for live playback with none of those
    limitations, so this function no longer needs to resolve anything for
    the live case at all - it only needs to report is_live=True so the
    caller can route to the browser instead.
    """
    if not url or yt_dlp is None:
        return None, False
    if not (url.startswith('http://') or url.startswith('https://')):
        return None, False
    try:
        opts = {
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            # TLS certificate verification is intentionally left at yt-dlp's
            # secure default (previously disabled here unconditionally,
            # which allowed a man-in-the-middle to serve an altered stream).
            'format': 'bestaudio/best',
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            return None, False
        if info.get('entries'):
            for e in info['entries']:
                if e:
                    info = e
                    break
        # A currently-airing live broadcast (as opposed to a finished
        # stream's VOD replay, where is_live is False/None and was_live
        # may be True) is never resolved to a URL here - see the docstring
        # above. The caller routes it to the browser instead.
        if info.get('is_live'):
            return None, True
        stream_url = info.get('url')
        if not stream_url:
            for f in (info.get('requested_formats') or []):
                if f.get('url'):
                    stream_url = f['url']
                    break
        return stream_url or None, False
    except Exception as e:
        log.error(f'Stream resolve error for {url}: {e}')
        return None, False


def start_playback(url, title, announce=True, playing_url_hint=None, playlist_file=None, playlist_origin_url=None):
    """Public entry point used throughout the add-on to start playback.

    For a single item (no playlist_file), the webpage URL is resolved to a
    direct stream URL in a background thread first, so the UI thread is
    never blocked and playback always uses the current yt-dlp resolution
    logic. Playlist files are handed to mpv unchanged, exactly as before,
    since mpv advances through them on its own.
    """

    state.last_play_request = {
        'url': url,
        'title': title,
        'playing_url_hint': playing_url_hint,
        'playlist_file': playlist_file,
        'playlist_origin_url': playlist_origin_url,
    }

    if not is_player_available():
        if announce:
            _ui_message(_('Player not available  opening in browser'))
        open_in_browser_background(url)
        return

    needs_resolve = (
        bool(url)
        and not playlist_file
        and (url.startswith('http://') or url.startswith('https://'))
    )

    if not needs_resolve:
        # Not a resolvable single-item webpage URL (a playlist file, or an
        # already-direct URL). A playlist file needs mpv's own ytdl_hook to
        # resolve each raw webpage URL it contains (see DEV_NOTES.md round
        # 29), so needs_ytdl_hook stays True here.
        _start_playback_now(url, title, announce=announce, playing_url_hint=playing_url_hint,
                             playlist_file=playlist_file, playlist_origin_url=playlist_origin_url,
                             browser_fallback_url=url, needs_ytdl_hook=True)
        return

    gen = _next_play_generation()

    def _worker():
        resolved, is_live = _resolve_playable_stream(url)

        if is_live:
            # Currently-airing live broadcasts are deliberately NOT played
            # in-app through mpv at all as of round 40 - the browser's own
            # native YouTube player has full first-party support for live
            # playback that mpv could never reliably match here (see
            # DEV_NOTES.md round 40, and _resolve_playable_stream()'s
            # docstring for the history of what was tried before this).
            # Everything else (regular videos, playlists, downloads) is
            # unaffected and still plays in-app through mpv exactly as
            # before.
            def _apply_live_browser():
                if gen != state._play_generation:
                    return
                # Stop whatever might already be playing in-app - the user
                # is switching to this live stream, which will now play in
                # the browser instead, not silently keep whatever was
                # playing before running in the background.
                _cleanup_player(silent=True)
                if announce:
                    _ui_message(_('Live stream  opening in your browser for stable playback'))
                open_in_browser_background(url)

            wx.CallAfter(_apply_live_browser)
            return

        target = resolved or url
        # True only when _resolve_playable_stream() could not produce a
        # usable direct/manifest URL and target had to fall back to the
        # raw webpage url - in that case mpv's own ytdl_hook is needed to
        # resolve it. When resolved is a real direct/manifest URL, ytdl_hook
        # must stay disabled for it - see needs_ytdl_hook's definition on
        # _start_playback_now() for why this matters with the mpv 0.41.0
        # upgrade specifically.
        needs_ytdl_hook = not bool(resolved)

        def _apply():
            if gen != state._play_generation:
                return
            _start_playback_now(target, title, announce=announce, playing_url_hint=playing_url_hint or url,
                                 playlist_file=playlist_file, playlist_origin_url=playlist_origin_url,
                                 browser_fallback_url=url, needs_ytdl_hook=needs_ytdl_hook)

        wx.CallAfter(_apply)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def _start_playback_now(url, title, announce=True, playing_url_hint=None, playlist_file=None,
                         playlist_origin_url=None, browser_fallback_url=None, needs_ytdl_hook=True):
    """needs_ytdl_hook controls whether mpv's own built-in ytdl_hook script
    (and, through it, the bundled youtube-dl.exe helper) is left enabled
    for this playback - see DEV_NOTES.md round 38 for why this parameter
    was added and defaults to True (matching every call site's behavior
    before this parameter existed).

    Pass True (or omit) for a playlist file, or any raw webpage URL that
    still needs mpv to resolve it itself (the round 32-33 live fallback
    when this add-on's own resolution came up empty). Pass False when url
    is already a direct/manifest URL this add-on resolved itself via the
    bundled yt-dlp library (the normal single-item case, and a
    successfully-resolved live HLS manifest) - ytdl_hook has no reason to
    touch an already-resolved URL, and with the mpv 0.41.0 upgrade (round
    35) doing so was found to be the actual cause of a new "Playback
    ended" regression on ordinary (non-live) videos: this newer mpv's
    ytdl_hook still fires on these URLs (visible in an mpv --log-file a
    user captured, showing "Running hook: ytdl_hook/on_load" for an
    already-direct googlevideo.com link) and hands them to the ancient,
    unrelated-to-this-add-on's-own-code bundled youtube-dl.exe helper
    (2017), which does not know what to do with a raw resolved media URL
    the way it does with an actual YouTube watch-page URL - interfering
    with playback that this add-on had already fully resolved on its own.
    """

    fallback_url = browser_fallback_url if browser_fallback_url is not None else url

    state.mpv_ipc_path = r'\\.\pipe\ytdlp_mpv_ipc'

    try:
        with state.player_lock:
            if state.player_proc is not None and state.player_proc.poll() is not None:
                state.player_proc = None

            if state.player_proc is not None and state.player_proc.poll() is None:
                try:
                    state.player_proc.terminate()
                    # Wait briefly for the old mpv process to actually exit
                    # before starting a new one on the same fixed named-pipe
                    # path (state.mpv_ipc_path never changes) - without this, the
                    # new process could try to create its IPC server while
                    # the old one still holds it, occasionally causing a
                    # track switch to silently fail to connect. A short
                    # timeout keeps track-switching responsive even if the
                    # old process is slow to exit.
                    try:
                        state.player_proc.wait(timeout=0.5)
                    except subprocess.TimeoutExpired:
                        try:
                            state.player_proc.kill()
                            state.player_proc.wait(timeout=0.5)
                        except Exception:
                            pass
                except Exception as e:
                    log.error(f'Error terminating previous player: {e}')

            # Best-effort: clear out last session's mpv log before this one
            # starts, so _MPV_LOG_PATH never grows unbounded across many
            # play sessions and always reflects only the current/most
            # recent playback attempt - see the mpv invocation below.
            try:
                if os.path.exists(_MPV_LOG_PATH):
                    os.remove(_MPV_LOG_PATH)
            except Exception:
                pass

            mpv_args = [
                mpv_exe,
                '--no-config',
                '--no-terminal',
                '--force-window=no',
                '--idle=no',
                '--vid=no',
            ]
            if not needs_ytdl_hook:
                # See needs_ytdl_hook's docstring above - disable mpv's own
                # built-in ytdl_hook script (and the ancient bundled
                # youtube-dl.exe helper it would otherwise hand this
                # already-resolved URL to) for URLs this add-on has
                # already resolved to a direct/manifest link itself.
                mpv_args.append('--ytdl=no')
            mpv_args.extend([
                    # The following two options were added alongside the
                    # mpv 0.41.0 upgrade (see DEV_NOTES.md round 36): a user
                    # reported that even normal (non-live) video playback
                    # now stops early mid-video with "Playback ended",
                    # something the old bundled mpv 0.28.0 did not do.
                    # mpv itself does not automatically reconnect a dropped
                    # HTTP connection to a network stream unless told to -
                    # ffmpeg's http protocol (which mpv's demuxer uses for
                    # the direct googlevideo.com URLs this add-on resolves
                    # videos to) only reconnects when explicitly asked via
                    # these reconnect_* options. It is plausible the old
                    # 2017-era ffmpeg statically built into the old mpv
                    # binary happened to behave more leniently here (by
                    # accident or a different internal default), while this
                    # much newer build follows the documented ffmpeg
                    # default of not reconnecting at all - so a connection
                    # YouTube's CDN drops partway through (a well-documented,
                    # common occurrence for these direct media links,
                    # unrelated to this add-on's own code) would end
                    # playback outright instead of resuming.
                    '--stream-lavf-o=reconnect=1,reconnect_streamed=1,reconnect_at_eof=1,reconnect_delay_max=5',
                    '--cache=yes',
                    # Write mpv's own diagnostic log to a fixed, known path
                    # (cleared before each playback above) so if a report
                    # like this comes in again, the actual reason mpv gave
                    # for stopping can be read from the log instead of
                    # guessing blind - see _MPV_LOG_PATH's definition.
                    f'--log-file={_MPV_LOG_PATH}',
                    '--msg-level=all=warn,demux=v,stream=v,ffmpeg=v',
                    f'--input-ipc-server={state.mpv_ipc_path}',
                    url,
            ])

            state.player_proc = subprocess.Popen(
                mpv_args,
                cwd=mpv_folder,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            state.player_paused = False
            if state.current_volume is None:
                # Restore the last volume the user set, instead of always
                # restarting at 100, so it survives Stop/Exit and a new search.
                state.current_volume = _get_last_volume()

            state.current_playing_url = playing_url_hint or url
            state.current_playlist_file = playlist_file
            state.current_playlist_origin_url = playlist_origin_url
            state.current_playlist_start_url = state.current_playing_url

        def _init_vol():
            for _ in range(25):
                time.sleep(0.08)
                okv = False
                oks = False
                try:
                    okv = _mpv_set_property('volume', int(state.current_volume))
                except Exception:
                    okv = False
                try:
                    s = float(SPEED_VALUES[int(state.current_speed_index)])
                except Exception:
                    s = 1.0
                try:
                    oks = _mpv_set_property('speed', s)
                except Exception:
                    oks = False
                if okv or oks:
                    return

        threading.Thread(target=_init_vol, daemon=True).start()

        if announce:
            _ui_message(_tr('Playing  {}', title))

    except Exception as e:
        log.error(f'Error starting player: {e}')
        if announce:
            _ui_message(_('Cannot start player  opening in browser'))
        state.mpv_ipc_path = None
        state.current_playing_url = None
        state.current_playlist_file = None
        state.current_playlist_origin_url = None
        state.current_playlist_start_url = None
        open_in_browser_background(fallback_url)


def _cleanup_player(silent=False, preserve_volume=False, preserve_playlist_file=False):
    with state.player_lock:
        try:
            if state.player_proc is not None and state.player_proc.poll() is None:
                try:
                    state.player_proc.terminate()
                except Exception as e:
                    log.error(f'Error terminating player: {e}')
        finally:
            state.player_proc = None
            state.player_paused = False
            state.mpv_ipc_path = None
            state.current_playing_url = None
            state.current_playlist_origin_url = None
            state.current_playlist_start_url = None
            if not preserve_volume:
                state.current_volume = None

    if not preserve_playlist_file:
        try:
            if state.current_playlist_file:
                p = os.path.abspath(state.current_playlist_file)
                # Temp playlist files are created by _create_temp_m3u() in
                # the OS temp directory (not addon_dir - a previous version
                # of this check compared against addon_dir, which never
                # matched, so these files were silently never cleaned up).
                # Matching the temp directory plus the 'ytdlp_' prefix this
                # add-on always uses keeps the deletion scoped to files this
                # add-on actually created.
                tmp_dir = os.path.abspath(tempfile.gettempdir())
                fname = os.path.basename(p)
                if (p.startswith(tmp_dir) and fname.startswith('ytdlp_')
                        and fname.lower().endswith('.m3u') and os.path.exists(p)):
                    os.remove(p)
        except Exception:
            pass
    state.current_playlist_file = None

    if not silent:
        _ui_message(_('Stopped'))


def stop_playback(announce=True, preserve_volume=False, preserve_playlist_file=False):
    if announce:
        _cleanup_player(silent=False, preserve_volume=preserve_volume, preserve_playlist_file=preserve_playlist_file)
    else:
        _cleanup_player(silent=True, preserve_volume=preserve_volume, preserve_playlist_file=preserve_playlist_file)


def _player_watchdog_loop():
    last_seen_pid = None
    while not state._player_watchdog_stop_event.is_set():
        # Polled at 0.1s instead of the previous 0.4s specifically so the
        # sleep timer's once-per-second beep countdown fires close enough
        # to each exact second that it is not noticeably late.
        time.sleep(0.1)

        try:
            _check_sleep_timer()
        except Exception as e:
            log.error(f'Sleep timer check error: {e}')

        with state.player_lock:
            proc = state.player_proc
            if proc is None:
                last_seen_pid = None
                continue
            try:
                pid = proc.pid
            except Exception:
                pid = None
            try:
                alive = proc.poll() is None
            except Exception:
                alive = False

        if alive:
            last_seen_pid = pid
            continue

        if pid is not None and last_seen_pid is not None and pid != last_seen_pid:
            last_seen_pid = None

        def _on_end():
            _cleanup_player(silent=True, preserve_volume=True)

            if (_get_runtime_auto_continue()
                    and state.current_track_items
                    and 0 <= state.current_track_index < len(state.current_track_items)):
                next_idx = state.current_track_index + 1
                if next_idx < len(state.current_track_items):
                    # The player process that just ended has already been
                    # cleaned up above, so is_player_running() is False here
                    # by design - require_running=False so that check does
                    # not block starting the next item.
                    if track_next(announce=_get_runtime_announce(), require_running=False):
                        return
                else:
                    if _get_runtime_announce():
                        _ui_message(_('Reached the end of the list'))
                    return

            if _get_runtime_announce():
                _ui_message(_('Playback ended'))

        try:
            wx.CallAfter(_on_end)
        except Exception:
            try:
                _on_end()
            except Exception:
                pass

        last_seen_pid = None


def start_player_watchdog():
    if state._player_watchdog_started:
        return
    state._player_watchdog_started = True
    state._player_watchdog_stop_event.clear()
    t = threading.Thread(target=_player_watchdog_loop, daemon=True)
    t.start()


def stop_player_watchdog():
    state._player_watchdog_stop_event.set()


# --- MPV IPC CONTROL PAUSE SEEK VOLUME ---

SEEK_STEP_SECONDS = 3
SEEK_STEP_LARGE_SECONDS = 30
VOLUME_STEP = 5
VOLUME_MIN = 0
VOLUME_MAX = 130


def toggle_pause(announce=True):

    with state.player_lock:
        if state.player_proc is None or state.player_proc.poll() is not None:
            state.player_proc = None
            state.player_paused = False
            return False

    ok = _send_mpv_command(['cycle', 'pause'])
    if not ok:
        return False

    state.player_paused = not state.player_paused

    if announce:
        if state.player_paused:
            _ui_message(_('Paused'))
        else:
            _ui_message(_('Resumed'))
    return True


def seek_forward(announce=True):
    _send_mpv_command(['seek', SEEK_STEP_SECONDS, 'relative'])
    if announce:
        _ui_message(_('Fast forward'))


def seek_backward(announce=True):
    _send_mpv_command(['seek', -SEEK_STEP_SECONDS, 'relative'])
    if announce:
        _ui_message(_('Rewind'))


def seek_forward_large(announce=True):
    _send_mpv_command(['seek', SEEK_STEP_LARGE_SECONDS, 'relative'])
    if announce:
        _ui_message(_('Fast forward 30 seconds'))


def seek_backward_large(announce=True):
    _send_mpv_command(['seek', -SEEK_STEP_LARGE_SECONDS, 'relative'])
    if announce:
        _ui_message(_('Rewind 30 seconds'))


def _clamp_volume(v):
    if v < VOLUME_MIN:
        return VOLUME_MIN
    if v > VOLUME_MAX:
        return VOLUME_MAX
    return v


def _persist_last_volume(vol):
    """Remember the volume level in config.json so it survives Stop/Exit
    and is restored instead of always restarting at 100 on the next play."""
    try:
        s = _safe_load_json_dict(config_file, encoding='utf-8')
        if not isinstance(s, dict):
            s = dict(default_settings)
        s['last_volume'] = int(_clamp_volume(vol))
        _safe_write_json(config_file, s, encoding='utf-8', indent=4, ensure_ascii=True)
    except Exception:
        pass


def _get_last_volume():
    try:
        s = _safe_load_json_dict(config_file, encoding='utf-8')
        if isinstance(s, dict) and 'last_volume' in s:
            return _clamp_volume(int(s.get('last_volume')))
    except Exception:
        pass
    return 100


def volume_up(announce=True):

    if state.current_volume is None:
        state.current_volume = _get_last_volume()

    if state.current_volume >= VOLUME_MAX:
        state.current_volume = VOLUME_MAX
        _mpv_set_property('volume', state.current_volume)
        _persist_last_volume(state.current_volume)
        if announce:
            _ui_message(_('Volume at maximum'))
        return

    state.current_volume = _clamp_volume(state.current_volume + VOLUME_STEP)
    _mpv_set_property('volume', state.current_volume)
    _persist_last_volume(state.current_volume)

    if not announce:
        return

    if state.current_volume == VOLUME_MAX:
        _ui_message(_('Volume at maximum'))
    elif state.current_volume == VOLUME_MIN:
        _ui_message(_('Volume muted'))
    else:
        _ui_message(_tr('Volume  {}', state.current_volume))


def volume_down(announce=True):

    if state.current_volume is None:
        state.current_volume = _get_last_volume()

    if state.current_volume <= VOLUME_MIN:
        state.current_volume = VOLUME_MIN
        _mpv_set_property('volume', state.current_volume)
        _persist_last_volume(state.current_volume)
        if announce:
            _ui_message(_('Volume muted'))
        return

    state.current_volume = _clamp_volume(state.current_volume - VOLUME_STEP)
    _mpv_set_property('volume', state.current_volume)
    _persist_last_volume(state.current_volume)

    if not announce:
        return

    if state.current_volume == VOLUME_MIN:
        _ui_message(_('Volume muted'))
    elif state.current_volume == VOLUME_MAX:
        _ui_message(_('Volume at maximum'))
    else:
        _ui_message(_tr('Volume  {}', state.current_volume))


# --- MPV SPEED CONTROL ---

def _apply_speed(announce=True, force_value=None):
    """Apply current speed to mpv if possible.

    Keeps the selected speed for the whole NVDA session.
    If mpv is running, attempts to set speed (float then str fallback).
    """
    try:
        speed = float(force_value) if force_value is not None else float(SPEED_VALUES[int(state.current_speed_index)])
    except Exception:
        speed = 1.0

    ok = False
    try:
        if is_player_running():
            ok = _send_mpv_command(['set_property', 'speed', speed])
            if not ok:
                ok = _send_mpv_command(['set_property', 'speed', str(speed)])
    except Exception:
        ok = False

    if announce and is_player_running() and not ok:
        _ui_message(_('Cannot set speed'))

    return ok



def speed_up(announce=True):
    if state.current_speed_index < len(SPEED_VALUES) - 1:
        state.current_speed_index += 1
        ok = _apply_speed(announce=False)
        if not announce:
            return
        if is_player_running() and not ok:
            _ui_message(_('Cannot set speed'))
            return
        try:
            sp = float(SPEED_VALUES[int(state.current_speed_index)])
        except Exception:
            sp = 1.0
        if abs(sp - 1.0) < 0.0001:
            _ui_message(_('Normal speed'))
        else:
            _ui_message(_tr('Speed  {}', f'{sp:.2f}'))
    else:
        if announce:
            _ui_message(_('Speed at maximum'))


def speed_down(announce=True):
    if state.current_speed_index > 0:
        state.current_speed_index -= 1
        ok = _apply_speed(announce=False)
        if not announce:
            return
        if is_player_running() and not ok:
            _ui_message(_('Cannot set speed'))
            return
        try:
            sp = float(SPEED_VALUES[int(state.current_speed_index)])
        except Exception:
            sp = 1.0
        if abs(sp - 1.0) < 0.0001:
            _ui_message(_('Normal speed'))
        else:
            _ui_message(_tr('Speed  {}', f'{sp:.2f}'))
    else:
        if announce:
            _ui_message(_('Speed at minimum'))


def reset_speed_session(announce=False):
    try:
        state.current_speed_index = SPEED_VALUES.index(1.0)
    except Exception:
        state.current_speed_index = 0
    try:
        if is_player_running():
            _mpv_set_property('speed', 1.0)
    except Exception:
        pass
    if announce:
        _ui_message(_('Speed reset'))


# --- REPLAY AND TRACK NAVIGATION ---

def play_last_request(announce=True):
    if not state.last_play_request:
        if announce:
            _ui_message(_('No last item to play'))
        return False

    try:
        start_playback(
            state.last_play_request.get('url'),
            state.last_play_request.get('title') or 'Last item',
            announce=announce,
            playing_url_hint=state.last_play_request.get('playing_url_hint'),
            playlist_file=state.last_play_request.get('playlist_file'),
            playlist_origin_url=state.last_play_request.get('playlist_origin_url'),
        )
        return True
    except Exception as e:
        log.error(f'Error playing last request: {e}')
        if announce:
            _ui_message(_('Cannot play last item'))
        return False


def _set_track_context(items, index):
    """Store an ordered track list and current position for prev/next navigation."""
    state.current_track_items = [v for v in (items or []) if v.get('url')]
    state.current_track_index = max(0, index) if state.current_track_items else -1


def track_next(announce=True, require_running=True):
    """Play the next track in the current track list and announce its title.

    require_running=False is used when advancing automatically right after
    the previous item has already finished and its player process has been
    cleaned up (see _on_end in the watchdog loop below) - at that point
    is_player_running() is correctly False, but that must not block moving
    on to the next item.
    """
    if require_running and not is_player_running():
        return False
    if not state.current_track_items or state.current_track_index < 0:
        if announce:
            _ui_message(_('No track list'))
        return False
    next_idx = state.current_track_index + 1
    if next_idx >= len(state.current_track_items):
        if announce:
            _ui_message(_('Last track'))
        return False
    entry = state.current_track_items[next_idx]
    url = entry.get('url')
    title = entry.get('title') or ''
    if not url:
        if announce:
            _ui_message(_('No link'))
        return False
    state.current_track_index = next_idx
    stop_playback(announce=False, preserve_volume=True)
    start_playback(url, title, announce=False, playing_url_hint=url)
    if announce:
        _ui_message(_tr('Next  {}', title))
    return True


def track_prev(announce=True, require_running=True):
    """Play the previous track in the current track list and announce its title."""
    if require_running and not is_player_running():
        return False
    if not state.current_track_items or state.current_track_index < 0:
        if announce:
            _ui_message(_('No track list'))
        return False
    prev_idx = state.current_track_index - 1
    if prev_idx < 0:
        if announce:
            _ui_message(_('First track'))
        return False
    entry = state.current_track_items[prev_idx]
    url = entry.get('url')
    title = entry.get('title') or ''
    if not url:
        if announce:
            _ui_message(_('No link'))
        return False
    state.current_track_index = prev_idx
    stop_playback(announce=False, preserve_volume=True)
    start_playback(url, title, announce=False, playing_url_hint=url)
    if announce:
        _ui_message(_tr('Previous  {}', title))
    return True


# --- SLEEP TIMER ---
# A simple wall-clock countdown, independent of whether something is
# actively playing when it is set. When it reaches zero it stops
# playback (if anything is playing) and announces. Not persisted across
# sessions - always starts at "off" when the window is (re)opened.
#
# The deadline is computed once, exactly when the time is set (F6/Shift+F6),
# as time.time() + minutes * 60. It is only ever recomputed when the time is
# changed again; simply letting it run, or checking the remaining time with
# Control+F6, never touches or resets it, so it always matches real time.
SLEEP_TIMER_STEP_MIN = 5
SLEEP_TIMER_MAX_MIN = 240  # 4 hours ceiling
SLEEP_TIMER_BEEP_LEAD_SECONDS = 10
state._sleep_timer_minutes = 0  # 0 = off
state._sleep_timer_deadline = 0
state._sleep_timer_warned_1min = False
# Tracks the last "N seconds left" value already beeped, so the countdown
# beeps exactly once per second for the last 10 seconds (10, 9, 8, ... 1)
# instead of repeating or skipping as _check_sleep_timer polls every ~0.4s.
state._sleep_timer_last_beep_second = None


def _sleep_timer_apply(minutes, announce=True):
    minutes = max(0, min(int(minutes), SLEEP_TIMER_MAX_MIN))
    state._sleep_timer_minutes = minutes
    state._sleep_timer_warned_1min = False
    state._sleep_timer_last_beep_second = None
    if minutes <= 0:
        state._sleep_timer_deadline = 0
        if announce:
            _ui_message(_('Sleep timer off'))
    else:
        state._sleep_timer_deadline = time.time() + minutes * 60
        if announce:
            _ui_message(_tr('Sleep timer set to {} minutes', minutes))


def sleep_timer_increase(announce=True):
    if state._sleep_timer_minutes >= SLEEP_TIMER_MAX_MIN:
        if announce:
            _ui_message(_('Sleep timer at maximum'))
        return
    _sleep_timer_apply(state._sleep_timer_minutes + SLEEP_TIMER_STEP_MIN, announce=announce)


def sleep_timer_decrease(announce=True):
    if state._sleep_timer_minutes <= 0:
        if announce:
            _ui_message(_('Sleep timer off'))
        return
    _sleep_timer_apply(state._sleep_timer_minutes - SLEEP_TIMER_STEP_MIN, announce=announce)


def announce_sleep_timer_remaining():
    """Control+F6: speak exactly how much time is left before the sleep
    timer stops playback, computed fresh from the stored deadline so it
    always matches real elapsed time."""
    deadline = state._sleep_timer_deadline
    if not deadline or state._sleep_timer_minutes <= 0:
        _ui_message(_('Sleep timer off'))
        return
    remaining = deadline - time.time()
    if remaining <= 0:
        _ui_message(_('Sleep timer off'))
        return
    total_seconds = int(round(remaining))
    mins, secs = divmod(total_seconds, 60)
    if mins > 0 and secs > 0:
        _ui_message(_tr('{} minutes {} seconds left on the sleep timer', mins, secs))
    elif mins > 0:
        _ui_message(_tr('{} minutes left on the sleep timer', mins))
    else:
        _ui_message(_tr('{} seconds left on the sleep timer', secs))


def _check_sleep_timer():
    """Called periodically (about every 0.1 seconds) from the player
    watchdog thread (background thread, not the UI thread) to fire the
    sleep timer when its deadline passes, and - only while the "Play
    advance warnings..." setting is on - to give a one-minute spoken
    warning and a once-per-second beep countdown for the last 10 seconds
    beforehand. The final "stopped playback" announcement and long
    confirmation beep, when the timer actually fires, always happen
    regardless of that setting - the same reasoning as F6 always
    announcing: there would otherwise be no way to know it worked."""

    deadline = state._sleep_timer_deadline
    if not deadline:
        return

    remaining = deadline - time.time()

    if remaining <= 0:
        state._sleep_timer_deadline = 0
        state._sleep_timer_minutes = 0
        state._sleep_timer_warned_1min = False
        state._sleep_timer_last_beep_second = None

        def _fire():
            try:
                if is_player_running():
                    stop_playback(announce=False, preserve_volume=True)
            except Exception:
                pass
            # Always announced - unlike volume or seeking, there is no
            # other way to know the sleep timer actually stopped playback.
            _ui_message(_('Sleep timer reached  stopped playback'))
            try:
                tones.beep(880, 700)
            except Exception:
                pass

        try:
            wx.CallAfter(_fire)
        except Exception:
            try:
                _fire()
            except Exception:
                pass
        return

    if not _get_runtime_sleep_beep_warning():
        return

    if not state._sleep_timer_warned_1min and remaining <= 60:
        state._sleep_timer_warned_1min = True

        def _warn():
            if _get_runtime_announce():
                _ui_message(_('Playback will stop in 1 minute'))

        try:
            wx.CallAfter(_warn)
        except Exception:
            try:
                _warn()
            except Exception:
                pass

    if remaining <= SLEEP_TIMER_BEEP_LEAD_SECONDS:
        # Ceiling of remaining seconds, e.g. 9.3 -> 10, 9.0 -> 9, so this
        # steps through 10, 9, 8, ... 1 exactly once each as remaining
        # counts down, giving one beep per second for the last 10 seconds.
        whole = int(remaining)
        seconds_left = whole if remaining == whole else whole + 1
        seconds_left = max(1, min(seconds_left, SLEEP_TIMER_BEEP_LEAD_SECONDS))

        if seconds_left != state._sleep_timer_last_beep_second:
            state._sleep_timer_last_beep_second = seconds_left

            def _beep():
                try:
                    tones.beep(880, 150)
                except Exception:
                    pass

            try:
                wx.CallAfter(_beep)
            except Exception:
                try:
                    _beep()
                except Exception:
                    pass


def stop_all_activity(plugin=None, announce=True):

    try:
        with state.download_lock:
            for u, fmt_map in list(state.active_downloads.items()):
                try:
                    for fmt_code, ad in fmt_map.items():
                        try:
                            ad['cancel'] = True
                            ad['status'] = 'Canceling'
                        except Exception:
                            pass
                except Exception:
                    pass
    except Exception:
        pass

    try:
        _cleanup_player(silent=True, preserve_volume=False)
    except Exception:
        pass

    try:
        reset_speed_session(announce=False)
    except Exception:
        pass

    state.last_search_items = []
    state.last_search_video_data = []
    state.last_search_selected_index = None
    state.last_search_query = ''

    try:
        if plugin and getattr(plugin, 'window', None):
            try:
                plugin.window.Destroy()
            except Exception:
                pass
            plugin.window = None
    except Exception:
        pass

    try:
        if plugin:
            plugin._opening = False
    except Exception:
        pass

    if announce:
        _ui_message(_('Exited'))


# --- DOWNLOAD LOGIC ---

def _safe_delete_file(path, base_folder):
    try:
        if not path:
            return False
        p = os.path.abspath(path)
        b = os.path.abspath(base_folder)
        if not p.startswith(b):
            return False
        if os.path.exists(p):
            os.remove(p)
            return True
    except Exception:
        return False
    return False


def _predict_possible_paths(folder, title, fmt_code):
    res = set()
    try:
        if not title:
            return res
        if fmt_code == 1:
            res.add(os.path.join(folder, f'{title}.mp3'))
        else:
            res.add(os.path.join(folder, f'{title}.mp4'))
    except Exception:
        pass
    return res


def _gather_files_for_url(url, folder, title=None, fmt_code=0):
    candidates = set()
    with state.download_lock:
        fmt_map = state.active_downloads.get(url)
        if fmt_map:
            for ad in fmt_map.values():
                if ad and ad.get('files'):
                    candidates |= set(ad['files'])
            if not title:
                for ad in fmt_map.values():
                    if not ad:
                        continue
                    t = ad.get('title')
                    if t:
                        title = t
                        break

    candidates |= _predict_possible_paths(folder, title, fmt_code)

    existing = set()
    for p in candidates:
        try:
            if p and os.path.exists(p):
                existing.add(p)
        except Exception:
            pass
    return existing


def _cleanup_temp_artifacts_for_url(url, folder, title=None, fmt_code=0, aggressive=False):
    # aggressive=True is for a job that is known to have NOT completed
    # successfully (canceled, or any other error) - never for the success
    # path. In that case every path this specific (url, fmt_code) job ever
    # reported through its progress hook is a leftover of a job that never
    # finished, not just the ones ending in temp_suffixes below. Without
    # this, a job canceled after its raw source stream(s) finished
    # downloading but before FFmpeg converted them (or merged separate
    # video/audio streams) left that raw file behind - it has an ordinary
    # extension like .webm/.m4a, not .part/.ytdl/.temp/.tmp, so the
    # temp-suffix-only check below never caught it. This was reported as
    # "cancel now stops the download, but a leftover file still remains in
    # the destination folder" right after the KeyboardInterrupt cancel fix
    # made cancellation itself actually take effect.
    try:
        temp_suffixes = ('.part', '.ytdl', '.temp', '.tmp')
        temp_paths = set()

        with state.download_lock:
            fmt_map = state.active_downloads.get(url)
            if fmt_map:
                for ad in fmt_map.values():
                    if ad and ad.get('files'):
                        for f in list(ad['files']):
                            try:
                                if f and str(f).lower().endswith(temp_suffixes):
                                    temp_paths.add(f)
                            except Exception:
                                pass

                if aggressive:
                    # Scoped to only this job's own fmt_code entry (not
                    # sibling entries for the same url) so a concurrent
                    # download of the same video in another format is
                    # never touched.
                    ad_self = fmt_map.get(fmt_code)
                    if ad_self and ad_self.get('files'):
                        for f in list(ad_self['files']):
                            if f:
                                temp_paths.add(f)

        base_paths = _gather_files_for_url(url, folder, title=title, fmt_code=fmt_code)
        for p in list(base_paths):
            try:
                root, _ext = os.path.splitext(p)
                for suff in temp_suffixes:
                    cand = root + suff
                    if os.path.exists(cand):
                        temp_paths.add(cand)
            except Exception:
                continue

        deleted = 0
        for p in list(temp_paths):
            if _safe_delete_file(p, folder):
                deleted += 1
        return deleted
    except Exception as e:
        log.error(f'Error cleaning temp artifacts: {e}')
        return 0


def _make_progress_hook(target_url, target_fmt_code):
    def _hook(d):
        status = d.get('status')
        filename = d.get('filename')
        p = (d.get('_percent_str') or '').strip()
        s = (d.get('_speed_str') or '').strip()

        if s:
            s = s.replace('KiB', 'KB').replace('MiB', 'MB').replace('GiB', 'GB')

        with state.download_lock:
            fmt_map = state.active_downloads.get(target_url)
            if not fmt_map:
                return
            ad = fmt_map.get(target_fmt_code)
            if not ad:
                return

            if ad.get('cancel'):
                # KeyboardInterrupt (not a plain Exception) on purpose: this
                # download runs with 'ignoreerrors': True so a per-item
                # download/postprocessing failure does not abort an entire
                # playlist job - but that same setting means a plain
                # Exception raised here to signal "the user canceled" was
                # being treated as just another per-item failure and
                # silently swallowed, letting the download carry on
                # regardless (reported as "cancel doesn't take effect and
                # leftover files remain"). KeyboardInterrupt does not
                # inherit from Exception, so it cannot be caught by
                # ignoreerrors-style `except Exception`/`except
                # DownloadError` handling anywhere in yt-dlp's own download
                # loop, and is yt-dlp's documented way for a progress/
                # postprocessor hook to abort a download outright. The
                # outer except clause in bg_download() below is updated to
                # also catch KeyboardInterrupt so this add-on's own cleanup
                # and "Canceled" messaging still runs.
                raise KeyboardInterrupt('UserCancel')

            if status == 'downloading':
                if p:
                    ad['last_percent'] = p
                if s:
                    ad['last_speed'] = s
                if p or s:
                    ad['status'] = f'Downloading  {p}  {s}' if s else f'Downloading  {p}'
                else:
                    ad['status'] = 'Downloading'

            elif status == 'finished':
                ad['status'] = 'Download finished  processing file  please wait'

            elif status == 'error':
                ad['status'] = 'Download error'

            if filename:
                try:
                    ad['files'].add(filename)
                except Exception:
                    pass

    return _hook


def _make_postprocessor_hook(target_url, target_fmt_code):
    def _hook(d):
        status = d.get('status')
        pp = d.get('postprocessor') or ''

        with state.download_lock:
            fmt_map = state.active_downloads.get(target_url)
            if not fmt_map:
                return
            ad = fmt_map.get(target_fmt_code)
            if not ad:
                return

            if ad.get('cancel'):
                # KeyboardInterrupt, not Exception - see the matching
                # comment in _make_progress_hook() above for why.
                raise KeyboardInterrupt('UserCancel')

            stage_msg = None

            if status == 'started':
                if 'FFmpegExtractAudio' in pp:
                    stage_msg = 'Processing audio file  please wait'
                elif 'FFmpegVideoRemuxer' in pp or 'FFmpegMetadata' in pp:
                    stage_msg = 'Processing video file  please wait'
                else:
                    stage_msg = 'Processing file  please wait'
            elif status == 'finished':
                if 'FFmpegExtractAudio' in pp:
                    stage_msg = 'Audio file ready  finalizing  please wait'
                elif 'FFmpegVideoRemuxer' in pp or 'FFmpegMetadata' in pp:
                    stage_msg = 'Video file ready  finalizing  please wait'
                else:
                    stage_msg = 'Processing finished  please wait'

            if stage_msg:
                ad['status'] = stage_msg

            # update playlist item counters for playlist jobs
            try:
                if ad.get('is_playlist_job'):
                    idict = d.get('info_dict') or {}
                    filename = d.get('filename') or idict.get('filepath') or ''

                    entry_key = None
                    if idict:
                        entry_key = idict.get('id') or idict.get('filename') or idict.get('title')
                    if not entry_key and filename:
                        entry_key = filename

                    # expected items from n_entries or playlist count
                    n_entries = None
                    for k in ('n_entries', 'playlist_count'):
                        if k in idict and idict.get(k) is not None:
                            try:
                                val = int(idict.get(k))
                            except Exception:
                                val = None
                            if val and val > 0:
                                n_entries = val
                                break
                    if n_entries and n_entries > 0:
                        cur = ad.get('expected_items')
                        if not isinstance(cur, int) or cur < n_entries:
                            ad['expected_items'] = n_entries

                    # also track from playlist_index if available
                    pi_val = idict.get('playlist_index')
                    try:
                        pi_int = int(pi_val) if pi_val is not None else None
                    except Exception:
                        pi_int = None
                    if pi_int and (not isinstance(ad.get('expected_items'), int) or ad.get('expected_items') < pi_int):
                        ad['expected_items'] = pi_int

                    # count completed items when postprocessing finished
                    if status == 'finished':
                        seen = ad.get('seen_entries')
                        if not isinstance(seen, set):
                            try:
                                seen = set(seen or [])
                            except Exception:
                                seen = set()
                            ad['seen_entries'] = seen
                        if entry_key and entry_key not in seen:
                            seen.add(entry_key)
                            try:
                                ad['completed_items'] = int(ad.get('completed_items') or 0) + 1
                            except Exception:
                                ad['completed_items'] = 1
            except Exception:
                pass

    return _hook


def _get_single_url_download_counts(url):
    if not url:
        return 0, 0
    mp3_items = 0
    mp4_items = 0
    with state.download_lock:
        fmt_map = state.active_downloads.get(url)
        if not fmt_map:
            return 0, 0
        for fmt_code, ad in fmt_map.items():
            if not ad or ad.get('cancel'):
                continue
            if fmt_code == 1:
                mp3_items += 1
            else:
                mp4_items += 1
    return mp3_items, mp4_items


def _get_playlist_download_counts_for_source(source_id):
    if not source_id:
        return 0, 0
    mp3_items = 0
    mp4_items = 0
    with state.download_lock:
        for _url, fmt_map in state.active_downloads.items():
            if not fmt_map:
                continue
            for fmt_code, ad in fmt_map.items():
                if not ad or ad.get('cancel'):
                    continue
                sp = ad.get('source_playlist')
                if not sp or sp != source_id:
                    continue
                remaining = 0
                if ad.get('is_playlist_job'):
                    exp = ad.get('expected_items')
                    try:
                        comp = int(ad.get('completed_items') or 0)
                    except Exception:
                        comp = 0
                    if isinstance(exp, int) and exp > 0:
                        remaining = exp - comp
                        if remaining < 0:
                            remaining = 0
                    else:
                        remaining = 1
                else:
                    remaining = 1
                if remaining <= 0:
                    continue
                if fmt_code == 1:
                    mp3_items += remaining
                else:
                    mp4_items += remaining
    return mp3_items, mp4_items


def speak_single_url_download_counts(url):
    mp3_items, mp4_items = _get_single_url_download_counts(url)
    if mp3_items <= 0 and mp4_items <= 0:
        _ui_message(_('Not downloading'))
        return
    mp3_word = _plural(mp3_items, 'item', 'items')
    mp4_word = _plural(mp4_items, 'item', 'items')
    _ui_message(_tr('MP3  {} {}  MP4  {} {}', mp3_items, mp3_word, mp4_items, mp4_word))


def speak_playlist_download_counts(source_id):
    mp3_items, mp4_items = _get_playlist_download_counts_for_source(source_id)
    if mp3_items <= 0 and mp4_items <= 0:
        _ui_message(_('No downloads for this playlist'))
        return
    # keep it short and consistent with other status phrases
    _ui_message(_tr('Playlist downloading  MP3  {}  MP4  {}', mp3_items, mp4_items))


def speak_channel_download_counts(source_id):
    mp3_items, mp4_items = _get_playlist_download_counts_for_source(source_id)
    if mp3_items <= 0 and mp4_items <= 0:
        _ui_message(_('No downloads for this channel'))
        return
    # keep it short and consistent with other status phrases
    _ui_message(_tr('Channel downloading  MP3  {}  MP4  {}', mp3_items, mp4_items))


def start_download(window, url, title, format_override=0, source_playlist=None, subfolder_title=None, is_playlist_job=False):
    settings = window.current_settings
    fmt_code = format_override
    type_str = 'MP3' if fmt_code == 1 else 'MP4'

    with state.download_lock:
        fmt_map = state.active_downloads.get(url)
        if fmt_map is None:
            fmt_map = {}
            state.active_downloads[url] = fmt_map

        existing = fmt_map.get(fmt_code)
        if existing and not existing.get('cancel'):
            _ui_message(_tr('Already downloading {} for this link', type_str))
            return False

        fmt_map[fmt_code] = {
            'status': 'Starting',
            'cancel': False,
            'title': title,
            'fmt': fmt_code,
            'source_playlist': source_playlist,
            'subfolder_title': subfolder_title,
            'is_playlist_job': bool(is_playlist_job),
            'files': set(),
            'last_speed': '',
            'last_percent': '',
            'expected_items': None,
            'completed_items': 0,
            'seen_entries': set(),
        }

    _ui_message(_tr('Download starting  {}  {}', title, type_str))

    t = threading.Thread(target=bg_download, args=(url, settings, fmt_code, title))
    t.daemon = True
    t.start()
    return True


def start_download_playlist(window, playlist_url, playlist_title, format_override=0):
    pl_url = _normalize_playlist_url(playlist_url)
    title = playlist_title or 'Playlist'
    return start_download(
        window,
        pl_url,
        title,
        format_override=format_override,
        source_playlist=pl_url,
        subfolder_title=title,
        is_playlist_job=True,
    )


def bg_download(url, settings, fmt_code, title):
    source_playlist = None
    subfolder_title = None
    is_playlist_job = False
    try:
        base_folder = settings.get('download_folder') or default_settings['download_folder']
    except Exception:
        base_folder = default_settings['download_folder']

    folder = base_folder

    try:
        with state.download_lock:
            fmt_map = state.active_downloads.get(url)
            if fmt_map:
                ad = fmt_map.get(fmt_code)
                if ad:
                    source_playlist = ad.get('source_playlist')
                    subfolder_title = ad.get('subfolder_title')
                    is_playlist_job = bool(ad.get('is_playlist_job'))
                    if ad.get('cancel'):
                        # KeyboardInterrupt, not Exception - see the
                        # matching comment in _make_progress_hook() for why.
                        raise KeyboardInterrupt('UserCancel')

        safe_sub = _sanitize_folder_name(subfolder_title) if subfolder_title else ''
        if safe_sub:
            folder = os.path.join(base_folder, safe_sub)

        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        current_path = os.environ.get('PATH', '')
        if ffmpeg_folder not in current_path:
            os.environ['PATH'] = current_path + os.pathsep + ffmpeg_folder

        if not os.path.exists(ffmpeg_exe):
            raise Exception('FFmpeg missing')

        vid_idx = settings.get('video_quality_idx', 0)
        aud_idx = settings.get('audio_quality_idx', 1)

        vid_height = VIDEO_QUALITY_MAP[vid_idx]
        aud_bitrate = AUDIO_QUALITY_MAP[aud_idx]

        if is_playlist_job:
            out_path = os.path.join(folder, '%(playlist_index)s - %(title)s.%(ext)s')
        else:
            out_path = os.path.join(folder, '%(title)s.%(ext)s')

        opts = {
            'outtmpl': out_path,
            'noplaylist': False if is_playlist_job else True,
            # TLS certificate verification left at yt-dlp's secure default -
            # see the matching comment in _resolve_playable_stream().
            'quiet': True,
            'progress_hooks': [_make_progress_hook(url, fmt_code)],
            'postprocessor_hooks': [_make_postprocessor_hook(url, fmt_code)],
            'retries': 10,
            'fragment_retries': 10,
            'continuedl': True,
            'ffmpeg_location': ffmpeg_folder,
            'restrictfilenames': False,
            'windowsfilenames': True,
            'ignoreerrors': True,
            'no_warnings': True,
        }

        if fmt_code == 1:
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': aud_bitrate,
                }],
                'postprocessor_args': [
                    '-b:a', f'{aud_bitrate}k',
                ],
            })
        else:
            if vid_height is None:
                format_str = 'best[ext=mp4]/best'
            else:
                format_str = (
                    f'best[height<={vid_height}][ext=mp4]/'
                    f'best[height<={vid_height}]/best'
                )
            opts['format'] = format_str

        # pre probe playlist size when downloading whole playlist
        if is_playlist_job:
            try:
                probe_opts = {
                    'quiet': True,
                    'extract_flat': 'in_playlist',
                    'ignoreerrors': True,
                    'no_warnings': True,
                    'noplaylist': False,
                }
                total_entries = 0
                with yt_dlp.YoutubeDL(probe_opts) as ydl_probe:
                    info_pl = ydl_probe.extract_info(url, download=False)
                if info_pl and isinstance(info_pl, dict):
                    entries = info_pl.get('entries') or []
                    try:
                        total_entries = len([e for e in entries if e])
                    except Exception:
                        total_entries = len(entries or [])
                if total_entries > 0:
                    with state.download_lock:
                        fmt_map2 = state.active_downloads.get(url)
                        if fmt_map2:
                            ad2 = fmt_map2.get(fmt_code)
                            if ad2 and not ad2.get('cancel'):
                                ad2['expected_items'] = total_entries
                                if not isinstance(ad2.get('seen_entries'), set):
                                    try:
                                        ad2['seen_entries'] = set(ad2.get('seen_entries') or [])
                                    except Exception:
                                        ad2['seen_entries'] = set()
                                try:
                                    ad2['completed_items'] = int(ad2.get('completed_items') or 0)
                                except Exception:
                                    ad2['completed_items'] = 0
            except Exception as e:
                log.error(f'Error probing playlist entries for url {url}: {e}')

        with state.download_lock:
            fmt_map = state.active_downloads.get(url)
            if fmt_map:
                ad = fmt_map.get(fmt_code)
                if ad and ad.get('cancel'):
                    # KeyboardInterrupt, not Exception - see the matching
                    # comment in _make_progress_hook() for why.
                    raise KeyboardInterrupt('UserCancel')

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        try:
            _cleanup_temp_artifacts_for_url(url, folder, title=title, fmt_code=fmt_code)
        except Exception:
            pass

        type_str = 'MP3' if fmt_code == 1 else 'MP4'
        wx.CallAfter(_ui_message, _tr('Download completed  {}  {}', type_str, title))

    except (Exception, KeyboardInterrupt) as e:
        # KeyboardInterrupt is caught here too (not just Exception) because
        # the cancel signal raised in _make_progress_hook()/
        # _make_postprocessor_hook() and above in this function uses
        # KeyboardInterrupt on purpose, specifically so it cannot be
        # silently absorbed by yt-dlp's own 'ignoreerrors': True handling
        # partway through - see the comment at the first raise site for the
        # full reasoning. This add-on's own cleanup/messaging below must
        # still run for that case exactly as it does for any other error.
        if 'UserCancel' in str(e):
            try:
                deleted = _cleanup_temp_artifacts_for_url(url, folder, title=title, fmt_code=fmt_code, aggressive=True)
                if deleted > 0:
                    wx.CallAfter(_ui_message, _tr('Canceled and removed {} files', deleted))
                else:
                    wx.CallAfter(_ui_message, _('Canceled'))
            except Exception:
                wx.CallAfter(_ui_message, _('Canceled'))
        else:
            log.error('Download error in bg_download')
            log.error(f'URL: {url}')
            log.error(f'Title: {title}')
            try:
                log.error(f'Folder: {folder}')
            except Exception:
                pass
            log.error(f'Settings: {settings}')
            log.error(f'Exception: {e}')
            log.error(traceback.format_exc())
            try:
                _cleanup_temp_artifacts_for_url(url, folder, title=title, fmt_code=fmt_code, aggressive=True)
            except Exception:
                pass

            wx.CallAfter(_ui_message, _('Download error'))

    finally:
        with state.download_lock:
            fmt_map = state.active_downloads.get(url)
            if fmt_map:
                ad = fmt_map.get(fmt_code)
                if ad:
                    try:
                        del fmt_map[fmt_code]
                    except Exception:
                        pass

                if not fmt_map:
                    try:
                        del state.active_downloads[url]
                    except Exception:
                        pass


# --- GLOBAL PLUGIN ---

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = _("YouTube Access Pro")

    __gestures = {
        'kb:NVDA+y': 'openInterface',
        'kb:f6': 'playerF6',
        'kb:shift+f6': 'playerShiftF6',
        'kb:control+f6': 'playerCtrlF6',
        'kb:f7': 'playerF7',
        'kb:shift+f7': 'playerShiftF7',
        'kb:f8': 'playerF8',
        'kb:f9': 'playerF9',
        'kb:shift+f9': 'playerShiftF9',
        'kb:f10': 'playerF10',
        'kb:shift+f10': 'playerShiftF10',
        'kb:f11': 'playerF11',
        'kb:f12': 'playerF12',
        'kb:shift+f11': 'playerShiftF11',
        'kb:shift+f12': 'playerShiftF12',
    }

    def __init__(self):
        super().__init__()
        self.window = None
        self._opening = False
        self.menu_item = None

        if _is_secure_mode():
            # Do not create UI, start background processes or register
            # menu items while NVDA is running on a secure desktop.
            return

        start_player_watchdog()

        self.menu_item = gui.mainFrame.sysTrayIcon.toolsMenu.Append(
            wx.ID_ANY, _('YouTube Access Pro'), _('Open the interface')
        )
        gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.on_menu_click, self.menu_item)

        # Give NVDA a little time to finish starting up before doing any
        # network work in the background.
        wx.CallLater(15000, maybe_auto_check_for_ytdlp_update)

    def on_menu_click(self, event):
        self.script_openInterface(None)

    def script_openInterface(self, gesture):
        fromShortcut = gesture is not None
        wx.CallAfter(self._openInterfaceGui, fromShortcut)

    def _is_focus_in_window(self):
        try:
            if not self.window:
                return False
            focus = wx.Window.FindFocus()
            if not focus:
                return False
            w = focus
            while w:
                if w == self.window:
                    return True
                w = w.GetParent()
        except Exception:
            return False
        return False

    def _window_is_alive(self):
        try:
            return self.window is not None
        except Exception:
            return False

    def script_playerF6(self, gesture):
        # The sleep timer is a wall-clock countdown that is deliberately
        # independent of whether something is actively playing (see the
        # comment above the sleep timer section) - the in-window F6 handler
        # never requires playback either. Uses the "allow stopped" guard
        # (like Shift+F7) instead of the regular one so the global shortcut
        # matches that same behavior instead of silently doing nothing
        # whenever nothing happens to be playing yet.
        if not self._global_player_guard_allow_stopped(gesture):
            return
        # Always announced, regardless of "Announce player hotkeys": unlike
        # volume or seeking, there is no other way to tell what value the
        # sleep timer was just set to.
        sleep_timer_increase(announce=True)

    def script_playerShiftF6(self, gesture):
        if not self._global_player_guard_allow_stopped(gesture):
            return
        sleep_timer_decrease(announce=True)

    def script_playerCtrlF6(self, gesture):
        if not self._global_player_guard_allow_stopped(gesture):
            return
        announce_sleep_timer_remaining()

    def _global_player_guard(self, gesture):
        if _is_secure_mode():
            try:
                gesture.send()
            except Exception:
                pass
            return False

        if self._window_is_alive() and self._is_focus_in_window():
            try:
                gesture.send()
            except Exception:
                pass
            return False

        if not _get_runtime_global_hotkeys():
            try:
                gesture.send()
            except Exception:
                pass
            return False

        if not is_player_running():
            try:
                gesture.send()
            except Exception:
                pass
            return False

        return True


    def _global_player_guard_allow_stopped(self, gesture):
        if _is_secure_mode():
            try:
                gesture.send()
            except Exception:
                pass
            return False

        if self._window_is_alive() and self._is_focus_in_window():
            try:
                gesture.send()
            except Exception:
                pass
            return False

        if not _get_runtime_global_hotkeys():
            try:
                gesture.send()
            except Exception:
                pass
            return False

        return True

    def script_playerShiftF7(self, gesture):
        if not self._global_player_guard_allow_stopped(gesture):
            return
        play_last_request(announce=_get_runtime_announce())

    def script_playerShiftF9(self, gesture):
        if not self._global_player_guard(gesture):
            return
        seek_backward_large(announce=_get_runtime_announce())

    def script_playerShiftF10(self, gesture):
        if not self._global_player_guard(gesture):
            return
        seek_forward_large(announce=_get_runtime_announce())


    def script_playerShiftF11(self, gesture):
        if not self._global_player_guard(gesture):
            return
        speed_down(announce=_get_runtime_announce())

    def script_playerShiftF12(self, gesture):
        if not self._global_player_guard(gesture):
            return
        speed_up(announce=_get_runtime_announce())

    def script_playerF7(self, gesture):
        if not self._global_player_guard(gesture):
            return
        stop_playback(announce=_get_runtime_announce(), preserve_volume=True, preserve_playlist_file=True)

    def script_playerF8(self, gesture):
        if not self._global_player_guard(gesture):
            return
        toggle_pause(announce=_get_runtime_announce())

    def script_playerF9(self, gesture):
        if not self._global_player_guard(gesture):
            return
        track_prev(announce=_get_runtime_announce())

    def script_playerF10(self, gesture):
        if not self._global_player_guard(gesture):
            return
        track_next(announce=_get_runtime_announce())

    def script_playerF11(self, gesture):
        if not self._global_player_guard(gesture):
            return
        volume_down(announce=_get_runtime_announce())

    def script_playerF12(self, gesture):
        if not self._global_player_guard(gesture):
            return
        volume_up(announce=_get_runtime_announce())

    script_playerF6.__doc__ = _('Global player sleep timer increase when mpv is running')
    script_playerShiftF6.__doc__ = _('Global player sleep timer decrease when mpv is running')
    script_playerCtrlF6.__doc__ = _('Global player announce sleep timer remaining time when mpv is running')
    script_playerF7.__doc__ = _('Global player stop when mpv is running')
    script_playerF8.__doc__ = _('Global player pause resume when mpv is running')
    script_playerF9.__doc__ = _('Global player previous track when mpv is running')
    script_playerF10.__doc__ = _('Global player next track when mpv is running')
    script_playerF11.__doc__ = _('Global player volume down when mpv is running')
    script_playerF12.__doc__ = _('Global player volume up when mpv is running')
    script_playerShiftF9.__doc__ = _('Global player seek backward 30 seconds when mpv is running')
    script_playerShiftF10.__doc__ = _('Global player seek forward 30 seconds when mpv is running')
    script_playerShiftF11.__doc__ = _('Global player speed down when mpv is running')
    script_playerShiftF12.__doc__ = _('Global player speed up when mpv is running')

    def _openInterfaceGui(self, fromShortcut=True):
        if _is_secure_mode():
            return
        if self._opening:
            return
        self._opening = True

        try:
            if yt_dlp is None:
                _ui_message(_('yt dlp error'))
                wx.MessageBox(_tr('yt-dlp error:\n{}', library_error), _('Error'))
                return
            if not os.path.exists(ffmpeg_exe):
                _ui_message(_('FFmpeg is missing'))
                wx.MessageBox(_tr('FFmpeg is missing:\n{}', ffmpeg_folder), _('Warning'))

            if self._window_is_alive():
                if self._is_focus_in_window():
                    if fromShortcut:
                        _ui_message(_('YouTube Access Pro already open'))
                    return
                try:
                    if self.window.IsIconized():
                        self.window.Restore()
                    self.window.Show(True)
                    self.window.Raise()
                    try:
                        self.window.restore_focus_on_reopen()
                    except Exception:
                        pass
                    if fromShortcut:
                        if is_player_running() and state.last_play_request and state.last_play_request.get('title'):
                            _ui_message(_tr('YouTube Access Pro  Now playing  {}', state.last_play_request.get("title", "")))
                        else:
                            _ui_message(_('YouTube Access Pro'))
                    return
                except Exception:
                    self.window = None

            self.window = MainWindow(self)
            try:
                self.window.Show(True)
                self.window.Raise()
                if is_player_running() and state.last_play_request and state.last_play_request.get('title'):
                    _ui_message_later(_tr('Now playing  {}', state.last_play_request.get("title", "")), delay_ms=600)
            except Exception:
                pass

        finally:
            self._opening = False

    script_openInterface.__doc__ = _('Open YouTube Access Pro window')

    def terminate(self):
        try:
            stop_all_activity(plugin=self, announce=False)
        except Exception:
            pass
        try:
            stop_player_watchdog()
        except Exception:
            pass
        if self.menu_item is not None:
            try:
                gui.mainFrame.sysTrayIcon.toolsMenu.RemoveItem(self.menu_item)
            except Exception:
                pass
        super().terminate()


# --- UI ---

class MainWindow(wx.Frame):
    def __init__(self, plugin):
        super().__init__(parent=gui.mainFrame, title='YouTube Access Pro', size=(700, 600))
        self.plugin = plugin
        self.current_settings = load_settings()
        self.playlists = load_playlists()

        self.panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook = wx.Notebook(self.panel)

        self.tab_search = SearchAndDownloadTab(self.notebook, self)
        self.tab_playlist = PlaylistTab(self.notebook, self)
        self.tab_subscriptions = SubscriptionsTab(self.notebook, self)
        self.tab_settings = SettingsTab(self.notebook, self)

        self.notebook.AddPage(self.tab_search, _('Search and Download'))
        self.notebook.AddPage(self.tab_playlist, _('Playlists'))
        self.notebook.AddPage(self.tab_subscriptions, _('Subscriptions'))
        self.notebook.AddPage(self.tab_settings, _('Settings'))

        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_tab_changed)
        self.last_tab_index = self.notebook.GetSelection()

        main_sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)

        self.Bind(wx.EVT_CLOSE, self.close)
        self.Bind(wx.EVT_CHAR_HOOK, self.catch_key)

        self.panel.SetSizer(main_sizer)
        self.Center()
        self.Show()

        try:
            wx.CallAfter(self.tab_search.focus_default)
        except Exception:
            pass

    def on_tab_changed(self, event):
        try:
            self.last_tab_index = self.notebook.GetSelection()
        except Exception:
            self.last_tab_index = 0
        event.Skip()

    def refresh_language(self):
        try:
            self.notebook.SetPageText(0, _('Search and Download'))
            self.notebook.SetPageText(1, _('Playlists'))
            self.notebook.SetPageText(2, _('Subscriptions'))
            self.notebook.SetPageText(3, _('Settings'))
        except Exception as e:
            log.error(f'Error refreshing notebook tab titles: {e}')

        for tab in (getattr(self, 'tab_search', None), getattr(self, 'tab_playlist', None),
                    getattr(self, 'tab_subscriptions', None),
                    getattr(self, 'tab_settings', None)):
            if tab is not None and hasattr(tab, 'refresh_language'):
                try:
                    tab.refresh_language()
                except Exception as e:
                    log.error(f'Error refreshing language on a tab: {e}')

    def on_toggle_language(self):
        new_lang = toggle_ui_language()
        try:
            settings = dict(load_settings())
            settings['ui_language'] = new_lang
            save_settings(settings)
            self.current_settings = load_settings()
        except Exception as e:
            log.error(f'Error saving language preference: {e}')

        self.refresh_language()

        lang_name = _('Thai') if new_lang == 'th' else _('English')
        _ui_message(_tr('Switched the interface menu to {}', lang_name))

    def restore_focus_on_reopen(self):
        try:
            if not state.current_playing_url:
                return
            idx = getattr(self, 'last_tab_index', None)
            if idx == 1 and hasattr(self, 'tab_playlist') and self.tab_playlist:
                self.tab_playlist.focus_playing()
            elif idx == 0 and hasattr(self, 'tab_search') and self.tab_search:
                self.tab_search.focus_playing()
            elif idx == 2 and hasattr(self, 'tab_subscriptions') and self.tab_subscriptions:
                self.tab_subscriptions.focus_playing()
        except Exception as e:
            log.error(f'Error restoring focus on reopen: {e}')

    def exit_now(self):
        running = _count_active_download_links()
        if running > 0:
            word = _plural(running, 'download', 'downloads')
            msg = _tr('{} {} in progress. Exit and cancel all downloads?', running, word)
            if wx.MessageBox(msg, _('Confirm exit'), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION) != wx.YES:
                return
        try:
            stop_all_activity(plugin=self.plugin, announce=False)
        except Exception:
            stop_all_activity(plugin=self.plugin, announce=False)

    def _active_tab_index(self):
        try:
            return self.notebook.GetSelection()
        except Exception:
            return 0

    def _active_tab_obj(self):
        try:
            return self.notebook.GetCurrentPage()
        except Exception:
            return None

    def _cycle_notebook_tab(self, direction=1):
        try:
            count = self.notebook.GetPageCount()
            if count <= 0:
                return

            current = self.notebook.GetSelection()
            if current == wx.NOT_FOUND:
                current = 0

            new_idx = (current + direction) % count
            self.notebook.SetSelection(new_idx)

            label = ''
            try:
                label = self.notebook.GetPageText(new_idx) or ''
            except Exception:
                label = ''

            try:
                page = self.notebook.GetPage(new_idx)
                if page:
                    page.SetFocus()
                else:
                    self.notebook.SetFocus()
            except Exception:
                try:
                    self.notebook.SetFocus()
                except Exception:
                    pass

            if label:
                _ui_message(_tr('{}  tab', label))
            else:
                _ui_message(_('Tab changed'))
        except Exception:
            pass

    # --- Central key dispatch table --------------------------------
    #
    # Each _kd_* method below is one rule, extracted mechanically and in
    # the exact same order from what used to be a single ~300-line
    # catch_key method made of sequential if-blocks. Every rule is
    # checked in this exact order for every keystroke, exactly as
    # before; the only thing that changed is *where* each check lives
    # (its own named method, listed once in _KEY_DISPATCH_TABLE) rather
    # than being an anonymous block inline in one giant function. Each
    # rule returns one of three things:
    #   True    - the key was fully handled; stop, do not call event.Skip()
    #   'skip'  - the key was recognized but should still propagate
    #             normally, so call event.Skip() then stop
    #   None    - this rule does not apply to this key; try the next one
    # This consolidation directly targets the recurring bug pattern that
    # has caused three separate real, confirmed bugs across earlier
    # rounds (F5, F7-F12, and Enter each silently failing to reach a
    # tab's own key handler because some earlier check swallowed the key
    # without event.Skip()) - there is now exactly one list to read to
    # see every global shortcut this window recognizes and the order
    # they are tried in, instead of that logic being spread across many
    # inline if-blocks that were easy to reorder or shadow by accident.

    def _kd_alt_menu(self, event, code):
        if code in (wx.WXK_ALT, wx.WXK_MENU):
            return 'skip'
        return None

    def _kd_ctrl_f1_help(self, event, code):
        # Ctrl+F1: speak a quick shortcut summary for whichever tab is
        # active. Plain F1 is left untouched (download as audio).
        if code == wx.WXK_F1 and event.ControlDown() and not event.ShiftDown() and not event.AltDown():
            page = self._active_tab_obj()
            if page is not None and hasattr(page, 'speak_help'):
                page.speak_help()
            return True
        return None

    def _kd_ctrl_t_language(self, event, code):
        # Ctrl+T: toggle this add-on's own interface language between
        # English and Thai, independent of NVDA's own configured language.
        if code == ord('T') and event.ControlDown() and not event.ShiftDown() and not event.AltDown():
            self.on_toggle_language()
            return True
        return None

    def _kd_ctrl_tab_cycle(self, event, code):
        try:
            if code == wx.WXK_TAB and event.ControlDown():
                direction = -1 if event.ShiftDown() else 1
                self._cycle_notebook_tab(direction=direction)
                return True
        except Exception:
            pass
        return None

    def _kd_ctrl_number_jump_tab(self, event, code):
        # Ctrl+1 through Ctrl+9 jump straight to that tab by position, as
        # a faster alternative to repeatedly pressing Ctrl+Tab /
        # Ctrl+Shift+Tab to cycle through them one at a time - added once
        # a fifth tab (Downloads) made cycling noticeably slower to reach
        # tabs near the end. Reads the number of tabs from the notebook
        # itself and does nothing if that position does not exist, so it
        # keeps working correctly however many tabs the window ends up
        # with in the future without needing to change this method.
        if event.ControlDown() and not event.AltDown() and not event.ShiftDown():
            if ord('1') <= code <= ord('9'):
                idx = code - ord('1')
                try:
                    if 0 <= idx < self.notebook.GetPageCount():
                        self.notebook.SetSelection(idx)
                        label = ''
                        try:
                            label = self.notebook.GetPageText(idx) or ''
                        except Exception:
                            pass
                        try:
                            page = self.notebook.GetPage(idx)
                            if page:
                                page.SetFocus()
                            else:
                                self.notebook.SetFocus()
                        except Exception:
                            try:
                                self.notebook.SetFocus()
                            except Exception:
                                pass
                        _ui_message(_tr('{}  tab', label) if label else _('Tab changed'))
                        return True
                except Exception:
                    pass
        return None

    def _kd_tab_wrap_guard(self, event, code):
        # Tab must not wrap around within a tab: pressing Tab while on the
        # last control (Exit) does nothing instead of cycling back to the
        # first control. Shift+Tab is left to wx's normal backward
        # traversal, which already stops at the first control without
        # wrapping.
        if code == wx.WXK_TAB and not event.ShiftDown() and not event.ControlDown():
            try:
                page = self._active_tab_obj()
                last_ctrl = getattr(page, 'last_focus_ctrl', None) if page is not None else None
                focus = wx.Window.FindFocus()
                if focus is not None and last_ctrl is not None and focus is last_ctrl:
                    return True
                if focus is not None and isinstance(focus, wx.Button) and focus.GetLabel() == _('Exit'):
                    return True
            except Exception:
                pass
        return None

    def _kd_enter_backspace_tab_dispatch(self, event, code):
        if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_BACK):
            idx = self._active_tab_index()
            page = self._active_tab_obj()
            if idx != 2 and isinstance(page, SearchAndDownloadTab):
                try:
                    focus = wx.Window.FindFocus()
                    if focus == page.listbox:
                        if code == wx.WXK_BACK:
                            if page.handle_backspace_key():
                                return True
                        else:
                            if page.activate_selected_item():
                                return True
                except Exception as e:
                    # This dispatch block is exactly the class of thing that
                    # has silently broken before (see the Enter/F5/F7-F12
                    # bugs found across rounds 9-11): log at debug level so
                    # a future failure here is diagnosable from the NVDA log
                    # instead of requiring another manual code audit.
                    log.debug(f'catch_key: Search and Download Enter/Backspace dispatch failed: {e}')
            elif isinstance(page, SubscriptionsTab):
                # Mirror the Search and Download tab above: handle Enter and
                # Backspace on the right-hand list here directly instead of
                # only relying on them falling through (via event.Skip()) to
                # lb_videos' own EVT_KEY_DOWN handler. That fallback path is
                # not reliably reached once this top-level EVT_CHAR_HOOK
                # handler has already seen the key, which is exactly why
                # Search and Download does the same thing for its own
                # Enter/Backspace handling. This list drills down through
                # channel sections (Videos/Shorts/Live/Playlists) and, for
                # Playlists, into one playlist's own videos - Enter opens
                # whatever is selected (a section, a playlist, or plays a
                # video), Backspace goes back up one level.
                try:
                    focus = wx.Window.FindFocus()
                    if focus == page.lb_videos:
                        if code == wx.WXK_BACK:
                            if page.handle_backspace():
                                return True
                        else:
                            page.activate_selected()
                            return True
                except Exception as e:
                    log.debug(f'catch_key: Subscriptions Enter/Backspace dispatch failed: {e}')
            elif isinstance(page, PlaylistTab) and code != wx.WXK_BACK:
                # Same reliability fix as the Subscriptions tab above,
                # applied to the Playlists tab's song list: key_right()
                # already handles Enter itself, but that path is not
                # reliably reached once this handler has already seen the
                # key, so it is also handled directly here. Enter on the
                # playlist-name list (lb_left) also plays the whole
                # playlist, the same as F7 - renaming already has its own
                # dedicated key (R), so Enter is not needed for that and
                # should not be ambiguous with it.
                try:
                    focus = wx.Window.FindFocus()
                    if focus == page.lb_right or focus == page.lb_left:
                        page.play(None)
                        return True
                except Exception as e:
                    log.debug(f'catch_key: Playlists Enter dispatch failed: {e}')
        return None

    def _kd_enter_search_type_dropdown(self, event, code):
        if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            try:
                page = self._active_tab_obj()
                if isinstance(page, SearchAndDownloadTab):
                    focus = wx.Window.FindFocus()
                    if focus == page.ch_search_type:
                        page.start_search(None)
                        return True
            except Exception:
                pass
        return None

    def _kd_escape_hide(self, event, code):
        if code == wx.WXK_ESCAPE:
            try:
                self.Hide()
            except Exception:
                try:
                    self.Close()
                except Exception:
                    pass
            return True
        return None

    def _kd_f6_sleep_increase(self, event, code):
        # Sleep timer: F6 increases (by 5 minutes), Shift+F6 decreases,
        # Control+F6 announces exactly how much time is left. Works the
        # same whether or not something is currently playing.
        if code == wx.WXK_F6 and not event.ShiftDown() and not event.ControlDown():
            # Always announced, regardless of "Announce player hotkeys":
            # unlike volume or seeking, there is no other way to tell what
            # value the sleep timer was just set to.
            sleep_timer_increase(announce=True)
            return True
        return None

    def _kd_ctrl_f6_sleep_announce(self, event, code):
        if code == wx.WXK_F6 and event.ControlDown() and not event.ShiftDown():
            # Purely informational (like F3/F4), so it always speaks
            # regardless of the "Announce player hotkeys" setting - there
            # is nothing else this key does.
            announce_sleep_timer_remaining()
            return True
        return None

    def _kd_shift_player_keys(self, event, code):
        if event.ShiftDown():
            announce_player = self.current_settings.get('announce_player_keys', True)
            if code == wx.WXK_F6:
                sleep_timer_decrease(announce=True)
                return True
            if code == wx.WXK_F7:
                play_last_request(announce=announce_player)
                return True
            if code == wx.WXK_F9:
                seek_backward_large(announce=announce_player)
                return True
            if code == wx.WXK_F10:
                seek_forward_large(announce=announce_player)
                return True
            if code == wx.WXK_F11:
                speed_down(announce=announce_player)
                return True
            if code == wx.WXK_F12:
                speed_up(announce=announce_player)
                return True
        return None

    def _kd_f7_f12_player_keys(self, event, code):
        if code in (
            wx.WXK_F7, wx.WXK_F8, wx.WXK_F9,
            wx.WXK_F10, wx.WXK_F11, wx.WXK_F12
        ):
            page = self._active_tab_obj()

            # Settings has no player-key handling of its own; let these
            # keys fall through to default behavior there. Checked by
            # tab type rather than a fixed index so this keeps working
            # if tabs are ever reordered or added.
            if isinstance(page, SettingsTab):
                return 'skip'

            try:
                if isinstance(page, SearchAndDownloadTab):
                    if page.handle_player_key(code):
                        return True
                elif isinstance(page, PlaylistTab):
                    if page.handle_player_key(code):
                        return True
                elif isinstance(page, SubscriptionsTab):
                    if page.handle_player_key(code):
                        return True
            except Exception as e:
                # F7-F12 dispatch: the exact kind of path that went silently
                # unhandled for Subscriptions in an earlier round. Logged at
                # debug level so a regression here shows up in the NVDA log.
                log.debug(f'catch_key: F7-F12 handle_player_key dispatch failed: {e}')
        return None

    def _kd_ctrl_f_focus_search(self, event, code):
        # Global shortcut even when focus is not on the results list
        try:
            if event.ControlDown() and not event.AltDown():
                if code in (ord('F'), ord('f')):
                    try:
                        self.notebook.SetSelection(0)
                    except Exception:
                        pass
                    try:
                        self.tab_search.txt_search.SetFocus()
                        try:
                            self.tab_search.txt_search.SetSelection(-1, -1)
                        except Exception:
                            pass
                    except Exception:
                        pass
                    return True
        except Exception:
            pass
        return None

    def _kd_f4_downloads_count(self, event, code):
        if code == wx.WXK_F4:
            if event.AltDown():
                self.exit_now()
                return True
            speak_downloads_running_count()
            return True
        return None

    def _kd_f5_download_folder(self, event, code):
        if code == wx.WXK_F5:
            try:
                base = self.current_settings.get('download_folder') or default_settings['download_folder']
            except Exception:
                base = default_settings['download_folder']
            sub = None
            try:
                page = self._active_tab_obj()
                if isinstance(page, PlaylistTab):
                    sub = page.lb_left.GetStringSelection() or None
                elif isinstance(page, SearchAndDownloadTab):
                    try:
                        if getattr(page, '_results_kind', '') == 'items' and getattr(page, '_playlist_view_title', None):
                            sub = page._playlist_view_title
                        else:
                            sub = None
                    except Exception:
                        sub = None
                elif isinstance(page, SubscriptionsTab):
                    try:
                        sub = page._current_channel_name_for_folder()
                    except Exception:
                        sub = None
            except Exception:
                sub = None
            open_download_folder_if_idle(base, subfolder_title=sub)
            return True
        return None

    def _kd_f3_status(self, event, code):
        if code == wx.WXK_F3:
            try:
                page = self._active_tab_obj()
                if isinstance(page, PlaylistTab):
                    page.speak_status_anywhere()
                    return True
                if isinstance(page, SearchAndDownloadTab):
                    page.speak_status_anywhere()
                    return True
                if isinstance(page, SubscriptionsTab):
                    page.speak_status_anywhere()
                    return True
            except Exception:
                pass
        return None

    def _kd_left_right_seek(self, event, code):
        if code in (wx.WXK_LEFT, wx.WXK_RIGHT):
            try:
                focus = wx.Window.FindFocus()
                if not isinstance(focus, wx.TextCtrl) and is_player_running():
                    announce_seek = self.current_settings.get('announce_player_keys', True)
                    if event.ControlDown():
                        if code == wx.WXK_LEFT:
                            seek_backward_large(announce=announce_seek)
                        else:
                            seek_forward_large(announce=announce_seek)
                    else:
                        if code == wx.WXK_LEFT:
                            seek_backward(announce=announce_seek)
                        else:
                            seek_forward(announce=announce_seek)
                    return True
            except Exception:
                pass
        return None

    # The table itself: one ordered list of every rule above, checked in
    # exactly this order for every keystroke. This is the single place to
    # look to see (or extend) every global keyboard shortcut this window
    # recognizes.
    _KEY_DISPATCH_TABLE = [
        _kd_alt_menu,
        _kd_ctrl_f1_help,
        _kd_ctrl_t_language,
        _kd_ctrl_tab_cycle,
        _kd_ctrl_number_jump_tab,
        _kd_tab_wrap_guard,
        _kd_enter_backspace_tab_dispatch,
        _kd_enter_search_type_dropdown,
        _kd_escape_hide,
        _kd_f6_sleep_increase,
        _kd_ctrl_f6_sleep_announce,
        _kd_shift_player_keys,
        _kd_f7_f12_player_keys,
        _kd_ctrl_f_focus_search,
        _kd_f4_downloads_count,
        _kd_f5_download_folder,
        _kd_f3_status,
        _kd_left_right_seek,
    ]

    def catch_key(self, event):
        code = event.GetKeyCode()
        for rule in self._KEY_DISPATCH_TABLE:
            result = rule(self, event, code)
            if result == 'skip':
                event.Skip()
                return
            if result:
                return
        event.Skip()

    def close(self, event):
        # Route all close events (Alt+F4, X button) through exit_now
        # so download confirmation and cleanup always run
        self.exit_now()


# --- 1 SEARCH AND DOWNLOAD ---

class SearchAndDownloadTab(wx.Panel):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.search_mode = 'search'
        self.last_query_local = ''
        self.last_search_type_local = None
        self.last_source_playlist_title = None
        self._results_total = 0
        self._results_kind = 'video'
        self._search_token = 0

        self._playlist_root_items = None
        self._playlist_root_video_data = None
        self._playlist_root_selected = 0
        self._playlist_view_origin_url = None
        self._playlist_view_title = None

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.lbl_search_prompt = wx.StaticText(self, label=_('Search text or paste a link'))
        sizer.Add(self.lbl_search_prompt, 0, wx.TOP | wx.LEFT, 10)

        self.txt_search = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.txt_search.Bind(wx.EVT_TEXT_ENTER, self.start_search)
        self.txt_search.Bind(wx.EVT_TEXT, self.on_search_text_change)
        sizer.Add(self.txt_search, 0, wx.EXPAND | wx.ALL, 10)

        self.lbl_search_type = wx.StaticText(self, label=_('Search type'))
        sizer.Add(self.lbl_search_type, 0, wx.LEFT, 10)
        self.ch_search_type = wx.Choice(self, choices=[_('Video'), _('Playlist'), _('Channel'), _('Live')])
        self.ch_search_type.SetSelection(0)
        try:
            self.ch_search_type.Bind(wx.EVT_CHOICE, self.on_search_type_choice)
        except Exception:
            pass
        sizer.Add(self.ch_search_type, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.btn_search = wx.Button(self, label=_('Search or open link'))
        self.btn_search.Bind(wx.EVT_BUTTON, self.on_search_button)
        sizer.Add(self.btn_search, 0, wx.ALL, 5)

        self.lbl_results = wx.StaticText(self, label=_('Results'))
        sizer.Add(self.lbl_results, 0, wx.LEFT | wx.TOP, 10)

        self.listbox = wx.ListBox(self, style=wx.LB_SINGLE)
        self.listbox.Bind(wx.EVT_CONTEXT_MENU, self.open_context_menu)
        self.listbox.Bind(wx.EVT_KEY_DOWN, self.keyboard_shortcuts)
        self.listbox.Bind(wx.EVT_LISTBOX, self.on_select)
        sizer.Add(self.listbox, 1, wx.EXPAND | wx.ALL, 10)

        self.btn_add_to_playlist = wx.Button(self, label=_('Add to playlist'))
        self.btn_add_to_playlist.Bind(wx.EVT_BUTTON, self.on_add_to_playlist_button)
        sizer.Add(self.btn_add_to_playlist, 0, wx.ALIGN_RIGHT | wx.ALL, 4)

        self.btn_exit = wx.Button(self, label=_('Exit'))
        self.btn_exit.Bind(wx.EVT_BUTTON, self.on_exit)
        sizer.Add(self.btn_exit, 0, wx.ALIGN_RIGHT | wx.ALL, 8)

        self.video_data = []
        self.SetSizer(sizer)

        self.lbl_results.Hide()
        self.listbox.Hide()

        # Used by MainWindow.catch_key to detect the last control on
        # this tab, so Tab does not wrap past it.
        self.last_focus_ctrl = self.btn_exit

        self.restore_state()
        self.update_search_button_mode()

    def focus_default(self):
        try:
            self.txt_search.SetFocus()
        except Exception:
            pass

    def focus_playing(self):
        if not state.current_playing_url:
            return
        try:
            for i, v in enumerate(self.video_data):
                if v.get('url') == state.current_playing_url:
                    self._ensure_results_visible()
                    if 0 <= i < self.listbox.GetCount():
                        self.listbox.SetSelection(i)
                    self.listbox.SetFocus()
                    break
        except Exception as e:
            log.error(f'Error focusing playing item in search tab: {e}')

    def _rebuild_listbox_labels(self):
        try:
            if not self.video_data:
                return
            sel = self.listbox.GetSelection()
            data = self.video_data
            has_back = bool(data) and (data[0].get('kind') == 'back')
            video_entries_count = sum(1 for e in data if e.get('kind') != 'back')
            new_items = []
            vid_idx = 0
            pl_idx = 0
            ch_idx = 0
            for entry in data:
                kind = entry.get('kind') or 'video'
                if kind == 'back':
                    new_items.append(self._build_item_label(entry, 0, 0))
                elif kind == 'playlist':
                    total = self._results_total or video_entries_count
                    new_items.append(self._build_item_label(entry, pl_idx, total))
                    pl_idx += 1
                elif kind == 'channel':
                    total = self._results_total or video_entries_count
                    new_items.append(self._build_item_label(entry, ch_idx, total))
                    ch_idx += 1
                else:
                    if has_back:
                        new_items.append(self._build_item_label(entry, vid_idx, video_entries_count, total_override=video_entries_count))
                    else:
                        total = self._results_total or video_entries_count
                        new_items.append(self._build_item_label(entry, vid_idx, total))
                    vid_idx += 1
            self.listbox.Set(new_items)
            if sel != wx.NOT_FOUND and 0 <= sel < len(new_items):
                self.listbox.SetSelection(sel)
        except Exception as e:
            log.error(f'Error rebuilding listbox labels for language switch: {e}')

    def refresh_language(self):
        try:
            self.lbl_search_prompt.SetLabel(_('Search text or paste a link'))
            self.lbl_search_type.SetLabel(_('Search type'))
            sel = self.ch_search_type.GetSelection()
            self.ch_search_type.Set([_('Video'), _('Playlist'), _('Channel')])
            if sel != wx.NOT_FOUND:
                self.ch_search_type.SetSelection(sel)
            self.lbl_results.SetLabel(_('Results'))
            self.btn_add_to_playlist.SetLabel(_('Add to playlist'))
            self.btn_exit.SetLabel(_('Exit'))
            self.update_search_button_mode()
            self._rebuild_listbox_labels()
            self.Layout()
        except Exception as e:
            log.error(f'Error refreshing language on search tab: {e}')

    def on_exit(self, event):
        self.main_window.exit_now()

    def speak_help(self):
        _ui_message(_(
            'Search and Download help. '
            'Type text or paste a link in the search box, then press Enter. '
            'Press Tab to reach the search type control, and choose Video, Playlist, or Channel. '
            'Use the arrow keys to move through results, and press Enter to open or play the selected item; '
            'opening a playlist or a channel shows its videos in the same list. '
            'Press Backspace to go back after opening a playlist or a channel. '
            'F1 downloads the selected item as audio, F2 downloads it as video. '
            'F3 announces its download status, F4 announces how many downloads are running, '
            'F5 opens the download folder. '
            'F6 increases the sleep timer by 5 minutes, which stops playback automatically after a set time; '
            'Shift+F6 decreases it by 5 minutes, and Control+F6 announces exactly how much time is left. '
            'F7 plays or stops, F8 pauses or resumes, F9 and F10 go to the previous or next track, '
            'F11 and F12 turn the volume down or up. '
            'Shift+F7 replays the last item, Shift+F9 and Shift+F10 seek 30 seconds back or forward, '
            'Shift+F11 and Shift+F12 change the playback speed. '
            'Control+C copies the link, Control+B opens it in your browser, Control+P adds it to a playlist, '
            'Control+S subscribes to the channel of the selected item. '
            'Control+Tab switches between tabs. '
            'Press Control+F1 again on any tab to hear its own help.'
        ))

    def _ensure_results_visible(self):
        try:
            if not self.lbl_results.IsShown():
                self.lbl_results.Show()
            if not self.listbox.IsShown():
                self.listbox.Show()
            self.Layout()
        except Exception:
            pass

    def _hide_results(self):
        try:
            self.lbl_results.Hide()
            self.listbox.Hide()
            self.Layout()
        except Exception:
            pass

    def on_search_text_change(self, event):
        try:
            self.update_search_button_mode()
        except Exception:
            pass
        event.Skip()

    def update_search_button_mode(self):
        try:
            txt = (self.txt_search.GetValue() or '').strip()
            has_results = bool(self.video_data) and self.listbox.GetCount() > 0
            cur_mode = self._selected_search_type()
            same_query = bool(txt) and (txt == (self.last_query_local or ''))
            same_type = (self.last_search_type_local is None) or (cur_mode == self.last_search_type_local)
            if has_results and same_query and same_type:
                self.search_mode = 'clear'
                self.btn_search.SetLabel(_('Clear search field'))
            else:
                self.search_mode = 'search'
                self.btn_search.SetLabel(_('Search or open link'))
        except Exception:
            self.search_mode = 'search'
            try:
                self.btn_search.SetLabel(_('Search or open link'))
            except Exception:
                pass

    def on_search_button(self, event):
        if self.search_mode == 'clear':
            self.clear_search_field()
        else:
            self.start_search(event)

    def _reset_playlist_view_state(self):
        self._playlist_root_items = None
        self._playlist_root_video_data = None
        self._playlist_root_selected = 0
        self._playlist_view_origin_url = None
        self._playlist_view_title = None

    def clear_search_field(self):

        try:
            self.txt_search.SetValue('')
        except Exception:
            pass

        self.video_data = []
        self._results_total = 0
        self._results_kind = 'video'
        self.last_source_playlist_title = None
        self._reset_playlist_view_state()

        try:
            self.listbox.Clear()
        except Exception:
            pass

        state.last_search_items = []
        state.last_search_video_data = []
        state.last_search_selected_index = None
        state.last_search_query = ''
        self.last_query_local = ''
        self.last_search_type_local = None

        self._hide_results()
        self.search_mode = 'search'
        try:
            self.btn_search.SetLabel(_('Search or open link'))
        except Exception:
            pass

        try:
            self.txt_search.SetFocus()
        except Exception:
            pass

        _ui_message(_('Cleared'))

    def restore_state(self):

        if not state.last_search_items or not state.last_search_video_data:
            if state.last_search_query:
                try:
                    self.txt_search.SetValue(state.last_search_query)
                    self.last_query_local = state.last_search_query
                except Exception:
                    pass
            return

        try:
            self._ensure_results_visible()

            self.video_data = list(state.last_search_video_data)
            self._results_total = len(self.video_data)
            self.listbox.Set(state.last_search_items)

            if state.last_search_query:
                try:
                    self.txt_search.SetValue(state.last_search_query)
                    self.last_query_local = state.last_search_query
                except Exception:
                    pass

            sel = None

            if state.current_playing_url:
                for i, v in enumerate(self.video_data):
                    try:
                        if v.get('url') == state.current_playing_url:
                            sel = i
                            break
                    except Exception:
                        continue

            if sel is None and state.last_search_selected_index is not None:
                if 0 <= state.last_search_selected_index < len(self.video_data):
                    sel = state.last_search_selected_index

            if sel is None and self.video_data:
                sel = 0

            if sel is not None and self.video_data:
                self.listbox.SetSelection(sel)

            self.update_search_button_mode()

        except Exception as e:
            log.error(f'Error restoring search state: {e}')

    def on_select(self, event):
        try:
            idx = self.listbox.GetSelection()
            if idx != wx.NOT_FOUND:
                state.last_search_selected_index = idx
        except Exception:
            pass
        event.Skip()

    # Fixed, language-independent identifiers matching the on-screen
    # order of the search-type dropdown (Video, Playlist, Channel).
    # Using GetString() here would return the currently displayed
    # (possibly Thai-translated) label instead of a stable value, which
    # broke Playlist-mode searches whenever the interface language was
    # switched to Thai - the search type is now read from the fixed
    # index instead, independent of the current display language.
    _SEARCH_TYPE_KEYS = ('Video', 'Playlist', 'Channel', 'Live')

    def _selected_search_type(self):
        try:
            idx = self.ch_search_type.GetSelection()
            if idx == wx.NOT_FOUND or idx < 0 or idx >= len(self._SEARCH_TYPE_KEYS):
                return 'Video'
            return self._SEARCH_TYPE_KEYS[idx]
        except Exception:
            return 'Video'

    def on_search_type_choice(self, event):
        try:
            self.update_search_button_mode()
        except Exception:
            pass
        event.Skip()

    def start_search(self, event):

        query = self.txt_search.GetValue().strip()
        if not query:
            return

        self.last_query_local = query
        state.last_search_query = query

        _ui_message(_('Processing'))

        self._ensure_results_visible()
        self.btn_search.Disable()
        self.listbox.Clear()
        self.video_data = []
        self._results_total = 0
        self._results_kind = 'video'
        self.last_source_playlist_title = None
        self._reset_playlist_view_state()

        self._search_token += 1
        token = self._search_token

        mode = self._selected_search_type()
        self.last_search_type_local = mode

        if query.startswith('http'):
            t = threading.Thread(target=self.bg_url, args=(query, mode, token))
        else:
            limit = self.main_window.current_settings.get('search_result_limit', 25)
            if mode == 'Playlist':
                t = threading.Thread(target=self.bg_search_playlists, args=(query, limit, token))
            elif mode == 'Channel':
                t = threading.Thread(target=self.bg_search_channels, args=(query, limit, token))
            elif mode == 'Live':
                t = threading.Thread(target=self.bg_search_live, args=(query, limit, token))
            else:
                t = threading.Thread(target=self.bg_search, args=(query, limit, token))
        t.daemon = True
        t.start()

    def bg_search(self, query, limit, token=0):
        try:
            opts = {'quiet': True, 'extract_flat': True, 'noplaylist': True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f'ytsearch{limit}:{query}', download=False)
                entries = [] if info is None else info.get('entries', [])
            if token != self._search_token:
                return
            wx.CallAfter(self.show_results, entries, None, 'video', None)
        except Exception as e:
            if token != self._search_token:
                return
            wx.CallAfter(self.error, str(e))

    def bg_search_playlists(self, query, limit, token=0):
        try:
            # YouTube search result filters can change, so we try a couple encodings
            sp_candidates = ['EgIQAw%253D%253D', 'EgIQAw%3D%3D']
            entries = []

            opts = {'quiet': True, 'extract_flat': True, 'ignoreerrors': True, 'no_warnings': True}
            if limit and isinstance(limit, int) and limit > 0:
                opts['playlistend'] = int(limit)

            for sp in sp_candidates:
                search_url = f'https://www.youtube.com/results?search_query={quote_plus(query)}&sp={sp}'
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(search_url, download=False)
                    entries = [] if info is None else list(info.get('entries', []) or [])
                if entries:
                    break

            # last resort without filter then we will strictly validate playlist ids
            if not entries:
                search_url = f'https://www.youtube.com/results?search_query={quote_plus(query)}'
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(search_url, download=False)
                    entries = [] if info is None else list(info.get('entries', []) or [])

            cleaned = []
            seen = set()

            for e in entries:
                if not e or not isinstance(e, dict):
                    continue

                url = e.get('webpage_url') or e.get('url') or e.get('id')
                if not url:
                    continue

                if isinstance(url, str) and not (url.startswith('http://') or url.startswith('https://')):
                    # yt-dlp sometimes returns an id-like string
                    url = _normalize_playlist_url(url) if _is_probably_playlist_url(url) else url

                pid = _extract_playlist_id(url) if isinstance(url, str) else None
                if not pid:
                    continue
                if not _is_playlist_id_candidate(pid):
                    continue
                if pid in seen:
                    continue
                seen.add(pid)

                try:
                    e['webpage_url'] = _normalize_playlist_url(url)
                    e['url'] = e['webpage_url']
                except Exception:
                    pass

                cleaned.append(e)

            # optional quick verification to avoid false positives like videos slipping in
            verified = []
            verify_limit = 20
            verify_opts = {
                'quiet': True,
                'extract_flat': 'in_playlist',
                'playlistend': 1,
                'ignoreerrors': True,
                'no_warnings': True,
            }

            def _verify_one(entry):
                pl_url = entry.get('webpage_url') or entry.get('url')
                if not pl_url:
                    return None
                try:
                    with yt_dlp.YoutubeDL(dict(verify_opts)) as ydl:
                        info = ydl.extract_info(pl_url, download=False)
                    if info and (info.get('_type') == 'playlist' or isinstance(info.get('entries'), list)):
                        return entry
                except Exception:
                    pass
                return None

            candidates = cleaned[:verify_limit]
            try:
                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = {executor.submit(_verify_one, e): e for e in candidates}
                    for future in as_completed(futures):
                        if token != self._search_token:
                            executor.shutdown(wait=False, cancel_futures=True)
                            return
                        result = future.result()
                        if result is not None:
                            verified.append(result)
            except Exception:
                verified = []

            final_entries = verified if verified else cleaned

            if token != self._search_token:
                return
            wx.CallAfter(self.show_results, final_entries, None, 'playlist', None)
        except Exception as e:
            if token != self._search_token:
                return
            wx.CallAfter(self.error, str(e))

    def bg_search_channels(self, query, limit, token=0):
        try:
            # sp= is YouTube's own search-result-type filter, encoded the
            # same way the existing Playlist search above already uses
            # (just a different filter value, for Channel instead of
            # Playlist results). Two encodings are tried since YouTube
            # has changed how it accepts this parameter before.
            sp_candidates = ['EgIQAg%253D%253D', 'EgIQAg%3D%3D']
            entries = []

            opts = {'quiet': True, 'extract_flat': True, 'ignoreerrors': True, 'no_warnings': True}

            for sp in sp_candidates:
                search_url = f'https://www.youtube.com/results?search_query={quote_plus(query)}&sp={sp}'
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(search_url, download=False)
                    entries = [] if info is None else list(info.get('entries', []) or [])
                if entries:
                    break

            cleaned = []
            seen = set()

            for e in entries:
                if not e or not isinstance(e, dict):
                    continue

                url = e.get('channel_url') or e.get('url') or e.get('webpage_url')
                if not url:
                    continue

                if isinstance(url, str) and not (url.startswith('http://') or url.startswith('https://')):
                    continue

                if not _is_probably_channel_url(url):
                    continue

                url = _normalize_channel_url(url)
                if url in seen:
                    continue
                seen.add(url)

                try:
                    e = dict(e)
                    e['channel_url'] = url
                except Exception:
                    pass

                cleaned.append(e)

                if limit and isinstance(limit, int) and len(cleaned) >= limit:
                    break

            if token != self._search_token:
                return
            wx.CallAfter(self.show_results, cleaned, None, 'channel', None)
        except Exception as e:
            if token != self._search_token:
                return
            wx.CallAfter(self.error, str(e))

    def bg_search_live(self, query, limit, token=0):
        try:
            # yt-dlp's own YouTube extractor (extractor/youtube/_tab.py,
            # _extract_video()) already computes a 'live_status' field
            # ('is_live' / 'was_live' / 'is_upcoming' / None) for every entry
            # straight from the search results page's badges/labels - no
            # per-video page load needed - and this field is present on
            # entries even with extract_flat enabled, since it's set on the
            # flat "url"-type stub itself, not discovered by resolving each
            # entry's own page. So a single flat ytsearch call already tells
            # us which results are currently live, exactly like
            # bg_search()/bg_search_playlists() above already do for their
            # own filtering - see DEV_NOTES.md round 42/44 (an earlier
            # version of this method did a slow per-candidate real
            # extraction instead, which was unnecessary and made Live search
            # noticeably slow).
            want = limit if (limit and isinstance(limit, int) and limit > 0) else 25
            pool_size = max(want * 4, 40)

            search_opts = {'quiet': True, 'extract_flat': True, 'ignoreerrors': True, 'no_warnings': True}
            with yt_dlp.YoutubeDL(search_opts) as ydl:
                info = ydl.extract_info(f'ytsearch{pool_size}:{query}', download=False)
                entries = [] if info is None else list(info.get('entries', []) or [])

            if token != self._search_token:
                return

            saw_live_status_field = False
            live_entries = []
            seen = set()
            for e in entries:
                if not e or not isinstance(e, dict):
                    continue
                url = e.get('webpage_url') or e.get('url') or _build_watch_url_from_id(e.get('id'))
                if not url or not isinstance(url, str):
                    continue
                if url in seen:
                    continue
                if 'live_status' in e:
                    saw_live_status_field = True
                if e.get('live_status') != 'is_live':
                    continue
                seen.add(url)
                e = dict(e)
                e['webpage_url'] = url
                e['url'] = url
                live_entries.append(e)
                if len(live_entries) >= want:
                    break

            # Safety net only - if this yt-dlp version's flat search entries
            # turn out not to carry 'live_status' at all (none of the pooled
            # entries had the key), fall back to the slower but
            # unconditionally correct per-candidate verification instead of
            # silently returning zero results. Capped at a small subset since
            # this path is expensive.
            if not saw_live_status_field:
                candidates = []
                seen2 = set()
                for e in entries:
                    if not e or not isinstance(e, dict):
                        continue
                    url = e.get('webpage_url') or e.get('url') or _build_watch_url_from_id(e.get('id'))
                    if not url or not isinstance(url, str) or url in seen2:
                        continue
                    seen2.add(url)
                    e = dict(e)
                    e['webpage_url'] = url
                    e['url'] = url
                    candidates.append(e)
                candidates = candidates[:15]

                verify_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True, 'format': 'worst'}

                def _verify_one(entry):
                    vid_url = entry.get('webpage_url')
                    if not vid_url:
                        return None
                    try:
                        with yt_dlp.YoutubeDL(dict(verify_opts)) as ydl:
                            vinfo = ydl.extract_info(vid_url, download=False)
                        if vinfo and vinfo.get('is_live'):
                            return entry
                    except Exception:
                        pass
                    return None

                try:
                    with ThreadPoolExecutor(max_workers=5) as executor:
                        futures = {executor.submit(_verify_one, e): e for e in candidates}
                        for future in as_completed(futures):
                            if token != self._search_token:
                                executor.shutdown(wait=False, cancel_futures=True)
                                return
                            result = future.result()
                            if result is not None:
                                live_entries.append(result)
                except Exception:
                    pass

            final_entries = live_entries[:want]

            if token != self._search_token:
                return
            wx.CallAfter(self.show_results, final_entries, None, 'video', None)
        except Exception as e:
            if token != self._search_token:
                return
            wx.CallAfter(self.error, str(e))

    def bg_url(self, url, mode, token=0):

        try:
            opts = {
                'quiet': True,
                'extract_flat': 'in_playlist',
                'ignoreerrors': True,
                'no_warnings': True,
            }

            origin_url = url

            if mode == 'Playlist' and _is_probably_playlist_url(url):
                origin_url = _normalize_playlist_url(url)
                url = origin_url

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if info is None:
                    wx.CallAfter(self.error, 'Could not fetch data')
                    return

                if 'entries' in info:
                    entries = list(info['entries'])
                    playlist_title = info.get('title') or ''
                    playlist_origin_url = info.get('webpage_url') or origin_url
                    playlist_origin_url = _normalize_playlist_url(playlist_origin_url)
                    if token != self._search_token:
                        return
                    wx.CallAfter(self.show_results, entries, playlist_title, 'items', playlist_origin_url)
                else:
                    entries = [info]
                    if token != self._search_token:
                        return
                    wx.CallAfter(self.show_results, entries, None, 'video', None)

        except Exception as e:
            if token != self._search_token:
                return
            wx.CallAfter(self.error, str(e))

    def _build_item_label(self, entry, idx, total, total_override=None):
        kind = entry.get('kind') or 'video'

        if kind == 'back':
            return _('Back  press Enter or Backspace')

        title = entry.get('title') or _('Unknown title')
        channel = entry.get('uploader') or ''
        duration = entry.get('duration') or ''

        if kind == 'channel':
            count = entry.get('count') or ''
            base = _tr('Channel  {}', title)
            if count:
                base += _tr('  {} subscribers', count)
            base += _tr('  {} of {}', idx + 1, total)
            return base

        if kind == 'playlist':
            count = entry.get('count') or ''
            base = _tr('Playlist  {}', title)
            if channel:
                base += _tr(' - {}', channel)
            if count:
                base += _tr(' ({})', count)
            base += _tr('  {} of {}', idx + 1, total)
            return base

        show_total = total_override if isinstance(total_override, int) and total_override > 0 else total

        if duration:
            if channel:
                base = _tr('{} - {} [{}]', title, channel, duration)
            else:
                base = _tr('{} [{}]', title, duration)
        else:
            base = title
            if channel:
                base += _tr(' - {}', channel)

        base += _tr('  {} of {}', idx + 1, show_total)
        return base

    def _save_root_for_back(self):
        try:
            if self._results_kind != 'playlist':
                return
            self._playlist_root_items = list(self.listbox.GetStrings())
            self._playlist_root_video_data = list(self.video_data)
            sel = self.listbox.GetSelection()
            if sel == wx.NOT_FOUND:
                sel = 0
            self._playlist_root_selected = sel
        except Exception:
            self._playlist_root_items = None
            self._playlist_root_video_data = None
            self._playlist_root_selected = 0

    def _return_from_playlist_view(self):
        if self._playlist_root_items and self._playlist_root_video_data:
            try:
                self.video_data = list(self._playlist_root_video_data)
                self.listbox.Set(list(self._playlist_root_items))
                self._results_kind = 'playlist'
                self._results_total = len(self.video_data)
                self._playlist_view_origin_url = None
                self._playlist_view_title = None

                sel = self._playlist_root_selected
                if sel is None or sel == wx.NOT_FOUND:
                    sel = 0
                if sel < 0:
                    sel = 0
                if sel >= self.listbox.GetCount():
                    sel = 0
                if self.listbox.GetCount() > 0:
                    self.listbox.SetSelection(sel)
                    self.listbox.SetFocus()

                _ui_message(_('Back'))
                return True
            except Exception:
                pass

        _ui_message(_('No previous list'))
        return True

    def _current_playlist_items_only(self):
        items = []
        for it in self.video_data:
            if not it:
                continue
            if it.get('kind') == 'video':
                items.append(it)
        return items

    def show_results(self, entries, playlist_title=None, results_kind='video', playlist_origin_url=None):

        self.btn_search.Enable()
        self.video_data = []
        items = []
        self._results_kind = results_kind

        valid_entries = [v for v in entries if v]
        if results_kind != 'items' and not valid_entries:
            state.last_search_items = []
            state.last_search_video_data = []
            state.last_search_selected_index = None
            self.listbox.Clear()
            self.update_search_button_mode()
            _ui_message(_('No results found'))
            return

        self.last_source_playlist_title = playlist_title or None

        if results_kind == 'channel':
            total = len(valid_entries)
            self._results_total = total

            for idx, ch in enumerate(valid_entries):
                title = ch.get('title') or ch.get('channel') or ch.get('uploader') or _('Unknown channel')
                ch_url = ch.get('channel_url') or ch.get('url') or ''
                followers = ch.get('channel_follower_count') or ch.get('follower_count') or ''
                entry = {
                    'kind': 'channel',
                    'title': title,
                    'url': ch_url,
                    'uploader': title,
                    'channel_url': ch_url,
                    'duration': '',
                    'count': str(followers) if followers else '',
                    'subfolder_title': None,
                }
                self.video_data.append(entry)
                items.append(self._build_item_label(entry, idx, total))

            self._reset_playlist_view_state()

        elif results_kind == 'playlist':
            total = len(valid_entries)
            self._results_total = total

            for idx, pl in enumerate(valid_entries):
                title = pl.get('title') or pl.get('id') or _('Unknown playlist')
                channel = pl.get('uploader') or pl.get('channel') or ''
                pl_url = _build_playlist_url_from_entry(pl)
                count = pl.get('video_count') or pl.get('playlist_count') or pl.get('n_entries') or ''
                entry = {
                    'kind': 'playlist',
                    'title': title,
                    'url': pl_url,
                    'uploader': channel,
                    'channel_url': _extract_channel_url(pl),
                    'duration': '',
                    'count': str(count) if count else '',
                    'subfolder_title': None,
                }
                self.video_data.append(entry)
                items.append(self._build_item_label(entry, idx, total))

            self._reset_playlist_view_state()

        elif results_kind == 'items':
            pl_title = playlist_title or 'Playlist'
            self._playlist_view_title = pl_title
            self._playlist_view_origin_url = playlist_origin_url

            if not self._playlist_root_items or not self._playlist_root_video_data:
                if playlist_origin_url:
                    root_entry = {
                        'kind': 'playlist',
                        'title': pl_title,
                        'url': playlist_origin_url,
                        'uploader': '',
                        'duration': '',
                        'count': '',
                        'subfolder_title': None,
                    }
                    self._playlist_root_items = [_tr('Playlist  {}  1 of 1', pl_title)]
                    self._playlist_root_video_data = [root_entry]
                    self._playlist_root_selected = 0

            back_entry = {'kind': 'back', 'title': _('Back'), 'url': '', 'uploader': '', 'duration': '', 'count': '', 'subfolder_title': None}
            self.video_data.append(back_entry)
            items.append(self._build_item_label(back_entry, 0, 0))

            total_videos = len(valid_entries)
            for idx, vid in enumerate(valid_entries):
                title = vid.get('title') or vid.get('id') or _('Unknown title')
                channel = vid.get('uploader', '') or ''
                dur_str = vid.get('duration_string') or _format_duration_seconds(vid.get('duration'))
                webpage = vid.get('webpage_url') or vid.get('original_url')
                v_id = vid.get('id')
                direct = vid.get('url')

                if webpage:
                    full_url = webpage
                elif v_id:
                    full_url = _build_watch_url_from_id(v_id)
                else:
                    full_url = direct

                entry = {
                    'kind': 'video',
                    'title': title,
                    'url': full_url,
                    'duration': dur_str or '',
                    'uploader': channel,
                    'channel_url': _extract_channel_url(vid),
                    'subfolder_title': pl_title,
                    'playlist_origin_url': playlist_origin_url,
                }
                self.video_data.append(entry)
                items.append(self._build_item_label(entry, idx, total_videos, total_override=total_videos))

            self._results_total = len(self.video_data)

        else:
            total = len(valid_entries)
            self._results_total = total

            for idx, vid in enumerate(valid_entries):
                title = vid.get('title') or vid.get('id') or _('Unknown title')
                channel = vid.get('uploader', '') or ''
                dur_str = vid.get('duration_string') or _format_duration_seconds(vid.get('duration'))
                webpage = vid.get('webpage_url') or vid.get('original_url')
                v_id = vid.get('id')
                direct = vid.get('url')

                if webpage:
                    full_url = webpage
                elif v_id:
                    full_url = _build_watch_url_from_id(v_id)
                else:
                    full_url = direct

                entry = {
                    'kind': 'video',
                    'title': title,
                    'url': full_url,
                    'duration': dur_str or '',
                    'uploader': channel,
                    'channel_url': _extract_channel_url(vid),
                    'subfolder_title': None,
                }
                self.video_data.append(entry)
                items.append(self._build_item_label(entry, idx, total))

            self._reset_playlist_view_state()

        self._ensure_results_visible()
        self.listbox.Set(items)

        if items:
            sel_idx = 0
            if results_kind == 'items':
                sel_idx = 1 if len(items) > 1 else 0
            self.listbox.SetSelection(sel_idx)
            self.listbox.SetFocus()

        state.last_search_items = list(items)
        state.last_search_video_data = list(self.video_data)
        state.last_search_selected_index = self.listbox.GetSelection()

        if self.last_query_local:
            state.last_search_query = self.last_query_local

        self.update_search_button_mode()

    def _open_playlist_contents_in_list(self, playlist_entry, auto_play=False):
        pl_url = playlist_entry.get('url') or ''
        if not pl_url:
            _ui_message(_('No playlist url'))
            return
        if playlist_entry.get('kind') == 'channel':
            # A bare channel URL resolves to the channel's Home tab, which
            # is hand-curated by the channel owner and not reliably the
            # full, newest-first upload list. Point at the Videos tab so
            # browsing a channel from search results shows its actual
            # uploads, consistent with the Videos section shown in
            # Subscriptions' own channel browser.
            pl_url = _channel_videos_tab_url(pl_url)

        self._save_root_for_back()

        _ui_message(_('Fetching playlist items'))

        def _done(data):
            if not data or not data.get('items'):
                _ui_message(_('No items found'))
                return

            pl_title = data.get('title') or playlist_entry.get('title') or 'Playlist'
            pl_url2 = data.get('url') or pl_url
            items_list = list(data.get('items') or [])

            if auto_play:
                pl_file = _create_temp_m3u(items_list, title=pl_title)
                if pl_file:
                    first_url = items_list[0].get('url') if items_list else ''
                    # Set the same track context that _play_playlist_from_selection
                    # sets, so that if mpv's own (older, bundled) playlist resolver
                    # stops advancing partway through the m3u, the watchdog's
                    # auto-continue-playback fallback (which resolves each stream
                    # through the newer bundled yt-dlp library) can still pick up
                    # and keep going, and F9/F10 previous/next also work here.
                    _set_track_context(items_list, 0)
                    announce_player = self.main_window.current_settings.get('announce_player_keys', True)
                    start_playback(pl_file, pl_title, announce=announce_player, playing_url_hint=first_url, playlist_file=pl_file, playlist_origin_url=pl_url2)
                else:
                    _ui_message(_('Cannot create playlist file'))

            entries_for_show = []
            for it in items_list:
                entries_for_show.append(dict(it))

            self.show_results(entries_for_show, pl_title, 'items', pl_url2)

        request_playlist_items(pl_url, _done, limit=200)

    def activate_selected_item(self):
        sel = self.listbox.GetSelection()
        if sel == wx.NOT_FOUND:
            return False
        if sel < 0 or sel >= len(self.video_data):
            return False

        kind = self.video_data[sel].get('kind') or 'video'

        if kind == 'back':
            self._return_from_playlist_view()
            return True

        if kind == 'playlist' or kind == 'channel':
            self._open_playlist_contents_in_list(self.video_data[sel], auto_play=False)
            return True

        self.handle_player_key(wx.WXK_F7)
        return True

    def handle_backspace_key(self):
        if self._results_kind == 'items':
            self._return_from_playlist_view()
            return True
        return False

    def keyboard_shortcuts(self, event):
        code = event.GetKeyCode()
        announce_player = self.main_window.current_settings.get('announce_player_keys', True)

        if code == wx.WXK_BACK:
            if self.handle_backspace_key():
                return

        if code == wx.WXK_RETURN or code == wx.WXK_NUMPAD_ENTER:
            if self.activate_selected_item():
                return

        if code == wx.WXK_SPACE:
            if is_player_running():
                toggle_pause(announce=announce_player)
                return

        if code == wx.WXK_HOME:
            if is_player_running():
                volume_up(announce=announce_player)
                return

        if code == wx.WXK_END:
            if is_player_running():
                volume_down(announce=announce_player)
                return

        if code == wx.WXK_LEFT:
            if is_player_running():
                if event.ControlDown():
                    seek_backward_large(announce=announce_player)
                else:
                    seek_backward(announce=announce_player)
                return

        if code == wx.WXK_RIGHT:
            if is_player_running():
                if event.ControlDown():
                    seek_forward_large(announce=announce_player)
                else:
                    seek_forward(announce=announce_player)
                return

        if code == wx.WXK_F4:
            speak_downloads_running_count()
            return

        if code == wx.WXK_F5:
            base = self.main_window.current_settings.get('download_folder') or default_settings['download_folder']
            sub = None
            try:
                if self._results_kind == 'items' and self._playlist_view_title:
                    sub = self._playlist_view_title
            except Exception:
                sub = None
            open_download_folder_if_idle(base, subfolder_title=sub)
            return

        sel = self.listbox.GetSelection()
        if sel == wx.NOT_FOUND:
            event.Skip()
            return

        state.last_search_selected_index = sel

        entry_kind = ''
        try:
            entry_kind = self.video_data[sel].get('kind') or ''
        except Exception:
            entry_kind = ''

        # Ctrl+C: Copy link
        if event.ControlDown() and code == ord('C'):
            entry = self.video_data[sel]
            link = entry.get('webpage_url') or entry.get('original_url') or entry.get('url')
            if link:
                ok = copy_to_clipboard(link)
                if ok:
                    if entry_kind == 'playlist':
                        kind_label = _('playlist link')
                    elif entry_kind == 'channel':
                        kind_label = _('channel link')
                    else:
                        kind_label = _('video link')
                    _ui_message_later(_tr('Copied {}', kind_label))
                else:
                    _ui_message(_('Copy failed'))
            else:
                _ui_message(_('No link'))
            return

        # Ctrl+B: Open in browser (video only)
        if event.ControlDown() and code == ord('B'):
            if entry_kind == 'video':
                url = self.video_data[sel].get('url')
                if url:
                    open_in_browser(url)
                else:
                    _ui_message(_('No link'))
            else:
                _ui_message(_('Only available for videos'))
            return

        # Ctrl+P: Add to playlist (video only)
        if event.ControlDown() and code == ord('P'):
            if entry_kind == 'video':
                self.on_add_to_playlist_button(None)
            else:
                _ui_message(_('Only videos can be added to playlist'))
            return

        # Ctrl+S: Subscribe to this item's channel
        if event.ControlDown() and code == ord('S'):
            entry = self.video_data[sel]
            if entry_kind == 'channel':
                ch_url = entry.get('url')
                ch_name = entry.get('title')
            else:
                ch_url = entry.get('channel_url')
                ch_name = entry.get('uploader') or ''
            ok, msg = subscribe_to_channel(ch_url, ch_name)
            _ui_message(msg)
            if ok:
                try:
                    if getattr(self.main_window, 'tab_subscriptions', None):
                        self.main_window.tab_subscriptions.refresh()
                except Exception:
                    pass
            return

        if code == wx.WXK_F1:
            if entry_kind == 'channel':
                _ui_message(_('Open channel contents to download items'))
                return
            if entry_kind == 'playlist':
                start_download_playlist(self.main_window, self.video_data[sel].get('url'), self.video_data[sel].get('title'), 1)
                return
            if entry_kind == 'back':
                if self._results_kind == 'items' and self._playlist_view_origin_url:
                    start_download_playlist(self.main_window, self._playlist_view_origin_url, self._playlist_view_title or 'Playlist', 1)
                    return
                _ui_message(_('Open playlist contents to download items'))
                return
            start_download(self.main_window, self.video_data[sel].get('url'), self.video_data[sel].get('title'), 1, subfolder_title=self.video_data[sel].get('subfolder_title'))
            return

        if code == wx.WXK_F2:
            if entry_kind == 'channel':
                _ui_message(_('Open channel contents to download items'))
                return
            if entry_kind == 'playlist':
                start_download_playlist(self.main_window, self.video_data[sel].get('url'), self.video_data[sel].get('title'), 0)
                return
            if entry_kind == 'back':
                if self._results_kind == 'items' and self._playlist_view_origin_url:
                    start_download_playlist(self.main_window, self._playlist_view_origin_url, self._playlist_view_title or 'Playlist', 0)
                    return
                _ui_message(_('Open playlist contents to download items'))
                return
            start_download(self.main_window, self.video_data[sel].get('url'), self.video_data[sel].get('title'), 0, subfolder_title=self.video_data[sel].get('subfolder_title'))
            return

        if code == wx.WXK_F3:
            if entry_kind == 'playlist':
                src = self.video_data[sel].get('url') or ''
                if src:
                    src = _normalize_playlist_url(src)
                    speak_playlist_download_counts(src)
                else:
                    _ui_message(_('No downloads for this playlist'))
                return
            if entry_kind == 'back':
                src = self._playlist_view_origin_url
                if src:
                    src = _normalize_playlist_url(src)
                    speak_playlist_download_counts(src)
                else:
                    _ui_message(_('No downloads for this playlist'))
                return
            url = self.video_data[sel].get('url')
            speak_single_url_download_counts(url)
            return

        event.Skip()


    def speak_status_anywhere(self):
        try:
            sel = self.listbox.GetSelection()
        except Exception:
            sel = wx.NOT_FOUND
        if sel == wx.NOT_FOUND:
            _ui_message(_('Not downloading'))
            return

        entry = None
        try:
            entry = self.video_data[sel]
        except Exception:
            entry = None
        if not isinstance(entry, dict):
            _ui_message(_('Not downloading'))
            return

        kind = entry.get('kind') or ''
        if kind == 'playlist':
            src = entry.get('url') or ''
            if src:
                src = _normalize_playlist_url(src)
                speak_playlist_download_counts(src)
            else:
                _ui_message(_('No downloads for this playlist'))
            return

        if kind == 'back':
            src = getattr(self, '_playlist_view_origin_url', None)
            if src:
                src = _normalize_playlist_url(src)
                speak_playlist_download_counts(src)
            else:
                _ui_message(_('No downloads for this playlist'))
            return

        url = entry.get('url')
        speak_single_url_download_counts(url)


    def _play_playlist_from_selection(self, sel_idx, announce_player=True):

        if sel_idx is None or sel_idx == wx.NOT_FOUND:
            sel_idx = 1

        if sel_idx < 0 or sel_idx >= len(self.video_data):
            sel_idx = 1

        entry = self.video_data[sel_idx]
        if entry.get('kind') != 'video':
            return

        selected_url = entry.get('url') or ''

        origin = entry.get('playlist_origin_url') or self._playlist_view_origin_url
        pl_title = self._playlist_view_title or entry.get('subfolder_title') or 'Playlist'

        if not origin:
            return

        if is_player_running() and state.current_playlist_origin_url == origin and state.current_playlist_file is not None:
            if state.current_playlist_start_url and selected_url and selected_url == state.current_playlist_start_url:
                stop_playback(announce=False, preserve_volume=True, preserve_playlist_file=True)
                if announce_player:
                    _ui_message(_('Stop'))
                return
            stop_playback(announce=False, preserve_volume=True)

        items_all = self._current_playlist_items_only()
        if not items_all:
            return

        start_idx = max(0, sel_idx - 1)
        if start_idx >= len(items_all):
            start_idx = 0

        items_to_play = items_all[start_idx:]
        if not items_to_play:
            items_to_play = items_all

        pl_file = _create_temp_m3u(items_to_play, title=pl_title)
        if not pl_file:
            _ui_message(_('Cannot create playlist file'))
            return

        first_url = items_to_play[0].get('url') or ''

        _set_track_context(items_to_play, 0)

        if is_player_running():
            stop_playback(announce=False, preserve_volume=True)

        start_playback(
            pl_file,
            pl_title,
            announce=announce_player,
            playing_url_hint=first_url,
            playlist_file=pl_file,
            playlist_origin_url=origin,
        )

    def handle_player_key(self, code):
        announce_player = self.main_window.current_settings.get('announce_player_keys', True)

        sel = self.listbox.GetSelection()
        if sel == wx.NOT_FOUND or sel >= len(self.video_data):
            if code == wx.WXK_F8 and is_player_running():
                toggle_pause(announce=announce_player)
                return True
            if code == wx.WXK_F9:
                track_prev(announce=announce_player)
                return True
            if code == wx.WXK_F10:
                track_next(announce=announce_player)
                return True
            if code == wx.WXK_F11 and is_player_running():
                volume_down(announce=announce_player)
                return True
            if code == wx.WXK_F12 and is_player_running():
                volume_up(announce=announce_player)
                return True
            return False

        state.last_search_selected_index = sel

        entry = self.video_data[sel]
        kind = entry.get('kind') or 'video'

        if code == wx.WXK_F7:
            if kind == 'back':
                self._return_from_playlist_view()
                return True

            if kind == 'playlist' or kind == 'channel':
                self._open_playlist_contents_in_list(entry, auto_play=False)
                return True

            if self._results_kind == 'items':
                self._play_playlist_from_selection(sel, announce_player=announce_player)
                return True

            url = entry.get('url')
            title = entry.get('title')

            # Build track context from all videos in current search results
            try:
                videos_only = [v for v in self.video_data if v.get('kind', 'video') == 'video']
                track_idx = next((i for i, v in enumerate(videos_only) if v.get('url') == url), 0)
                _set_track_context(videos_only, track_idx)
            except Exception:
                pass

            if is_player_running():
                if state.current_playing_url and state.current_playing_url == url and state.current_playlist_file is None:
                    stop_playback(announce=False, preserve_volume=True)
                    if announce_player:
                        _ui_message(_('Stop'))
                else:
                    stop_playback(announce=False, preserve_volume=True)
                    start_playback(url, title, announce=announce_player, playing_url_hint=url, playlist_file=None, playlist_origin_url=None)
            else:
                start_playback(url, title, announce=announce_player, playing_url_hint=url, playlist_file=None, playlist_origin_url=None)

            return True

        if code == wx.WXK_F8:
            if is_player_running():
                toggle_pause(announce=announce_player)
            return True
        if code == wx.WXK_F9:
            track_prev(announce=announce_player)
            return True
        if code == wx.WXK_F10:
            track_next(announce=announce_player)
            return True
        if code == wx.WXK_F11:
            if is_player_running():
                volume_down(announce=announce_player)
            return True
        if code == wx.WXK_F12:
            if is_player_running():
                volume_up(announce=announce_player)
            return True

        return False

    def on_add_to_playlist_button(self, event):
        sel = self.listbox.GetSelection()
        if sel == wx.NOT_FOUND or sel >= len(self.video_data):
            _ui_message(_('No item selected'))
            return

        if self.video_data[sel].get('kind') in ('playlist', 'back', 'channel'):
            _ui_message(_('Only videos can be added'))
            return

        menu = wx.Menu()
        menu.Append(1, _('Create new playlist'))

        if self.main_window.playlists:
            menu.AppendSeparator()
            for i, pl in enumerate(self.main_window.playlists.keys()):
                menu.Append(100 + i, pl)

        def _on_create(evt):
            self.new_playlist(sel)

        self.Bind(wx.EVT_MENU, _on_create, id=1)

        for i, pl in enumerate(self.main_window.playlists.keys()):
            self.Bind(
                wx.EVT_MENU,
                lambda e, name=pl, idx=sel: self.add_to_playlist(name, idx),
                id=100 + i,
            )

        self.PopupMenu(menu)
        menu.Destroy()
        try:
            s = self.listbox.GetSelection()
            if s != wx.NOT_FOUND:
                self.listbox.SetSelection(s)
            wx.CallAfter(self.listbox.SetFocus)
        except Exception:
            pass

    def new_playlist(self, idx):
        dlg = wx.TextEntryDialog(self, _('Name'), _('New playlist'))
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetValue().strip()
            if name:
                if name not in self.main_window.playlists:
                    self.main_window.playlists[name] = []
                self.add_to_playlist(name, idx)
        dlg.Destroy()

    def add_to_playlist(self, name, idx):
        if idx < 0 or idx >= len(self.video_data):
            return

        if self.video_data[idx].get('kind') != 'video':
            _ui_message(_('Only videos can be added'))
            return

        entry = dict(self.video_data[idx])

        if name not in self.main_window.playlists:
            self.main_window.playlists[name] = []

        exists = any(v.get('url') == entry.get('url') for v in self.main_window.playlists[name])
        if not exists:
            self.main_window.playlists[name].append(entry)
            save_playlists(self.main_window.playlists)
            try:
                if hasattr(self.main_window, 'tab_playlist') and self.main_window.tab_playlist:
                    self.main_window.tab_playlist.refresh(force_right=True)
            except Exception:
                pass
            _ui_message_later(_tr('Added to {} playlist', name))
        else:
            _ui_message_later(_tr('Already in {} playlist', name))

    def open_context_menu(self, event):
        sel = self.listbox.GetSelection()
        if sel == wx.NOT_FOUND:
            return

        entry = self.video_data[sel]
        kind = entry.get('kind') or 'video'

        menu = wx.Menu()

        def _pick_link(d):
            return d.get('webpage_url') or d.get('original_url') or d.get('url')

        def _copy_link(evt):
            link = _pick_link(entry)
            if not link:
                _ui_message(_('No link'))
                return
            ok = copy_to_clipboard(link)
            if not ok:
                _ui_message(_('Copy failed'))
                return
            if kind == 'playlist':
                _ui_message_later(_('Copied playlist link'))
            elif kind == 'channel':
                _ui_message_later(_tr('Copied {}', _('channel link')))
            else:
                _ui_message_later(_('Copied video link'))

        if kind == 'back':
            menu.Append(10, _('Back'))
            self.Bind(wx.EVT_MENU, lambda e: self._return_from_playlist_view(), id=10)

            if self._results_kind == 'items' and self._playlist_view_origin_url:
                dl_all = wx.Menu()
                dl_all.Append(20, _('Download playlist as video  F2'))
                dl_all.Append(21, _('Download playlist as audio  F1'))
                menu.AppendSubMenu(dl_all, _('Download playlist'))
                self.Bind(
                    wx.EVT_MENU,
                    lambda e: start_download_playlist(self.main_window, self._playlist_view_origin_url, self._playlist_view_title or 'Playlist', 0),
                    id=20,
                )
                self.Bind(
                    wx.EVT_MENU,
                    lambda e: start_download_playlist(self.main_window, self._playlist_view_origin_url, self._playlist_view_title or 'Playlist', 1),
                    id=21,
                )

            self.PopupMenu(menu)
            menu.Destroy()
            return

        if kind == 'playlist':
            menu.Append(10, _('Open playlist contents  Enter'))
            # Note: no "F7" in this label - on the keyboard, F7 on a playlist
            # row opens its contents (same as Enter) rather than playing it
            # immediately, so it does not actually trigger this action. This
            # menu item is the only way to jump straight to playback.
            menu.Append(11, _('Play playlist from beginning'))
            menu.AppendSeparator()

            dl_pl = wx.Menu()
            dl_pl.Append(13, _('Download playlist as video  F2'))
            dl_pl.Append(14, _('Download playlist as audio  F1'))
            menu.AppendSubMenu(dl_pl, _('Download playlist'))

            menu.Append(12, _('Copy playlist link'))
            self.Bind(wx.EVT_MENU, lambda e: self._open_playlist_contents_in_list(entry, auto_play=False), id=10)
            self.Bind(wx.EVT_MENU, lambda e: self._open_playlist_contents_in_list(entry, auto_play=True), id=11)
            self.Bind(wx.EVT_MENU, lambda e: start_download_playlist(self.main_window, entry.get('url'), entry.get('title'), 0), id=13)
            self.Bind(wx.EVT_MENU, lambda e: start_download_playlist(self.main_window, entry.get('url'), entry.get('title'), 1), id=14)
            self.Bind(wx.EVT_MENU, _copy_link, id=12)
            menu.AppendSeparator()
        elif kind == 'channel':
            # Channels intentionally have no direct-download entries here,
            # matching F1/F2 on the keyboard, which also refuse to
            # bulk-download an entire channel by accident - its contents
            # must be opened first so individual videos can be downloaded
            # from there instead.
            menu.Append(10, _('Open channel contents  Enter'))
            menu.Append(15, _('Copy channel link'))
            self.Bind(wx.EVT_MENU, lambda e: self._open_playlist_contents_in_list(entry, auto_play=False), id=10)
            self.Bind(wx.EVT_MENU, _copy_link, id=15)
            self.PopupMenu(menu)
            menu.Destroy()
            return
        else:
            menu.Append(2, _('Open in browser'))
            menu.Append(6, _('Copy video link'))
            menu.AppendSeparator()

            dl_menu = wx.Menu()
            dl_menu.Append(3, _('Download as video  F2'))
            dl_menu.Append(4, _('Download as audio  F1'))
            menu.AppendSubMenu(dl_menu, _('Download'))

            self.Bind(wx.EVT_MENU, lambda e: open_in_browser(entry.get('url')), id=2)
            self.Bind(wx.EVT_MENU, _copy_link, id=6)
            self.Bind(wx.EVT_MENU, lambda e: start_download(self.main_window, entry.get('url'), entry.get('title'), 0, subfolder_title=entry.get('subfolder_title')), id=3)
            self.Bind(wx.EVT_MENU, lambda e: start_download(self.main_window, entry.get('url'), entry.get('title'), 1, subfolder_title=entry.get('subfolder_title')), id=4)

        # "Add to playlist" only makes sense for a video row - kept out of
        # the 'playlist'/'channel'/'back' branches above (which already
        # return early for 'channel', and would otherwise offer an action
        # that add_to_playlist()/new_playlist() would just refuse anyway,
        # or - for "Create new playlist" - silently leave behind an empty
        # playlist with nothing added to it).
        if kind == 'video':
            pl_menu = wx.Menu()
            pl_menu.Append(5, _('Create new playlist'))
            if self.main_window.playlists:
                pl_menu.AppendSeparator()
                for i, pl in enumerate(self.main_window.playlists.keys()):
                    pl_menu.Append(100 + i, pl)
            menu.AppendSubMenu(pl_menu, _('Add to playlist'))

            self.Bind(wx.EVT_MENU, lambda e: self.new_playlist(sel), id=5)
            for i, pl in enumerate(self.main_window.playlists.keys()):
                self.Bind(
                    wx.EVT_MENU,
                    lambda e, name=pl, idx=sel: self.add_to_playlist(name, idx),
                    id=100 + i,
                )

        self.PopupMenu(menu)
        menu.Destroy()

    def error(self, msg):
        self.btn_search.Enable()
        _ui_message(_('Error in search'))
        wx.MessageBox(msg, _('Error'))


# --- 2 PLAYLIST TAB ---

class PlaylistTab(wx.Panel):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        left = wx.BoxSizer(wx.VERTICAL)
        self.lbl_playlists = wx.StaticText(self, label=_('Playlists'))
        left.Add(self.lbl_playlists, 0, wx.ALL, 5)
        self.lb_left = wx.ListBox(self)
        self.lb_left.Bind(wx.EVT_LISTBOX, self.select_left)
        self.lb_left.Bind(wx.EVT_CONTEXT_MENU, self.menu_left)
        self.lb_left.Bind(wx.EVT_KEY_DOWN, self.key_left)
        left.Add(self.lb_left, 1, wx.EXPAND | wx.ALL, 5)

        right = wx.BoxSizer(wx.VERTICAL)
        self.lbl_right = wx.StaticText(self, label=_('Contents'))
        right.Add(self.lbl_right, 0, wx.ALL, 5)
        self.lb_right = wx.ListBox(self)
        self.lb_right.Bind(wx.EVT_CONTEXT_MENU, self.menu_right)
        self.lb_right.Bind(wx.EVT_KEY_DOWN, self.key_right)
        self.lb_right.Bind(wx.EVT_LISTBOX_DCLICK, self.play)
        right.Add(self.lb_right, 1, wx.EXPAND | wx.ALL, 5)

        self.btn_exit_right = wx.Button(self, label=_('Exit'))
        self.btn_exit_right.Bind(wx.EVT_BUTTON, self.on_exit)
        right.Add(self.btn_exit_right, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        sizer.Add(left, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(right, 2, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)

        # Used by MainWindow.catch_key to detect the last control on
        # this tab, so Tab does not wrap past it.
        self.last_focus_ctrl = self.btn_exit_right

        self.refresh(force_right=True)
        self.focus_playing()

    def refresh_language(self):
        try:
            self.lbl_playlists.SetLabel(_('Playlists'))
            self.btn_exit_right.SetLabel(_('Exit'))
            name = self.lb_left.GetStringSelection()
            if name:
                vids = self.main_window.playlists.get(name, [])
                self.lbl_right.SetLabel(_tr('{} ({})', name, len(vids)))
            else:
                self.lbl_right.SetLabel(_('Contents'))
            self.Layout()
        except Exception as e:
            log.error(f'Error refreshing language on playlist tab: {e}')

    def on_exit(self, event):
        self.main_window.exit_now()

    def speak_help(self):
        _ui_message(_(
            'Playlists help. '
            'This tab has two lists: your saved playlists, and the songs inside the one you have selected. Press Tab to move between them. '
            'Use the arrow keys to move around, and press Enter or F7 to play. '
            'On the playlist list: F1 and F2 download the whole playlist as audio or video, '
            'F3 announces its download status, F4 announces how many downloads are running, '
            'F5 opens the download folder, R renames the playlist, Delete removes it after asking you to confirm. '
            'On the song list: F7 plays from that song onward, Space pauses or resumes, '
            'F1 and F2 download the selected song as audio or video, F3 announces its download status, '
            'Delete removes it from the playlist after asking you to confirm, Control+C copies its link. '
            'F9 and F10 go to the previous or next track, F11 and F12 turn the volume down or up. '
            'Press Control+F1 again on any tab to hear its own help.'
        ))

    def refresh(self, force_right=False):
        sel = self.lb_left.GetStringSelection()
        items = list(self.main_window.playlists.keys())
        self.lb_left.Set(items)

        if sel in items:
            self.lb_left.SetStringSelection(sel)
            if force_right:
                self.select_left(None)
        elif items:
            self.lb_left.SetSelection(0)
            self.select_left(None)
        else:
            self.lb_right.Clear()
            self.lbl_right.SetLabel(_('Contents'))

    def focus_playing(self):
        if not state.current_playing_url:
            return

        try:
            for pl_name, vids in self.main_window.playlists.items():
                for idx, v in enumerate(vids):
                    if v.get('url') == state.current_playing_url:
                        self.lb_left.SetStringSelection(pl_name)
                        self.select_left(None)
                        if 0 <= idx < self.lb_right.GetCount():
                            self.lb_right.SetSelection(idx)
                            self.lb_right.SetFocus()
                        return
        except Exception as e:
            log.error(f'Error focusing current playing item in PlaylistTab: {e}')

    def select_left(self, event):
        name = self.lb_left.GetStringSelection()
        if not name:
            self.lb_right.Clear()
            return
        vids = self.main_window.playlists.get(name, [])
        self.lb_right.Set([f"{v.get('title','')}" for v in vids])
        self.lbl_right.SetLabel(_tr('{} ({})', name, len(vids)))
        try:
            _ui_message(_tr('Playlist  {}  {} items', name, len(vids)))
        except Exception:
            pass

    def handle_player_key(self, code):
        announce_player = self.main_window.current_settings.get('announce_player_keys', True)

        if code == wx.WXK_F8:
            if is_player_running():
                toggle_pause(announce=announce_player)
                return True
            return False
        if code == wx.WXK_F9:
            track_prev(announce=announce_player)
            return True
        if code == wx.WXK_F10:
            track_next(announce=announce_player)
            return True
        if code == wx.WXK_F11:
            if is_player_running():
                volume_down(announce=announce_player)
                return True
            return False
        if code == wx.WXK_F12:
            if is_player_running():
                volume_up(announce=announce_player)
                return True
            return False

        if code != wx.WXK_F7:
            return False

        self.play(None)
        return True

    def key_left(self, e):
        k = e.GetKeyCode()
        if k == wx.WXK_F1:
            self.download_whole_playlist(format_override=1)
            return

        if k == wx.WXK_F2:
            self.download_whole_playlist(format_override=0)
            return

        if k == wx.WXK_F3:
            name = self._get_selected_playlist_name()
            if name:
                speak_playlist_download_counts(name)
            else:
                _ui_message(_('No playlist selected'))
            return

        if k == wx.WXK_DELETE:
            self.delete_list(None)
            return

        if k == wx.WXK_F4:
            speak_downloads_running_count()
            return

        if k == wx.WXK_F5:
            base = self.main_window.current_settings.get('download_folder') or default_settings['download_folder']
            name = self.lb_left.GetStringSelection() or None
            open_download_folder_if_idle(base, subfolder_title=name)
            return

        if k == ord('R') or k == ord('r'):
            self.rename(None)
            return

        if k in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            # Play the whole playlist from the start, the same as F7 -
            # renaming already has its own dedicated key (R), so Enter
            # here should not be ambiguous with it. Normally unreachable
            # in practice since MainWindow.catch_key handles Enter for
            # this list directly first (see _kd_enter_backspace_tab_
            # dispatch) - kept here too as a fallback, matching the
            # pattern already used for lb_right in this same tab.
            self.play(None)
            return

        e.Skip()

    def download_whole_playlist(self, format_override=0):
        name = self.lb_left.GetStringSelection()
        if not name:
            _ui_message(_('No playlist selected'))
            return
        vids = list(self.main_window.playlists.get(name, []) or [])
        if not vids:
            _ui_message(_('This playlist is empty'))
            return

        count = 0
        for v in vids:
            u = v.get('url')
            t = v.get('title') or _('Unknown title')
            if not u:
                continue
            ok = start_download(self.main_window, u, t, format_override, source_playlist=name, subfolder_title=name)
            if ok:
                count += 1

        if count <= 0:
            _ui_message(_('No downloadable items'))
        else:
            _ui_message(_tr('Download queued  {} items', count))

    def key_right(self, e):
        k = e.GetKeyCode()
        announce_player = self.main_window.current_settings.get('announce_player_keys', True)

        if k in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.play(None)
            return

        if k == wx.WXK_SPACE:
            if is_player_running():
                toggle_pause(announce=announce_player)
                return

        if k == wx.WXK_HOME:
            if is_player_running():
                volume_up(announce=announce_player)
                return

        if k == wx.WXK_END:
            if is_player_running():
                volume_down(announce=announce_player)
                return

        if k == wx.WXK_LEFT:
            if is_player_running():
                if e.ControlDown():
                    seek_backward_large(announce=announce_player)
                else:
                    seek_backward(announce=announce_player)
                return

        if k == wx.WXK_RIGHT:
            if is_player_running():
                if e.ControlDown():
                    seek_forward_large(announce=announce_player)
                else:
                    seek_forward(announce=announce_player)
                return

        if e.ControlDown() and k == ord('C'):
            self.copy_selected_link()
            return

        if k == wx.WXK_DELETE:
            self.remove_video(None)
            return

        if k == wx.WXK_F7:
            self.play(None)
            return

        if k == wx.WXK_F1:
            self.download_selected(format_override=1)
            return

        if k == wx.WXK_F2:
            self.download_selected(format_override=0)
            return

        if k == wx.WXK_F3:
            self.speak_download_status()
            return

        if k == wx.WXK_F4:
            speak_downloads_running_count()
            return

        if k == wx.WXK_F5:
            base = self.main_window.current_settings.get('download_folder') or default_settings['download_folder']
            name = self.lb_left.GetStringSelection() or None
            open_download_folder_if_idle(base, subfolder_title=name)
            return

        e.Skip()
    def speak_status_anywhere(self):
        # Prefer right list selection if it exists
        try:
            vid_sel = self.lb_right.GetSelection()
        except Exception:
            vid_sel = wx.NOT_FOUND

        if vid_sel != wx.NOT_FOUND:
            try:
                list_name = self._get_selected_playlist_name()
                vids = self.main_window.playlists.get(list_name, []) if list_name else []
                if 0 <= vid_sel < len(vids):
                    url = vids[vid_sel].get('url')
                    speak_single_url_download_counts(url)
                    return
            except Exception:
                pass

        # Fallback to playlist selection status
        try:
            name = self._get_selected_playlist_name()
        except Exception:
            name = None
        if name:
            speak_playlist_download_counts(name)
            return

        # Last resort: speak global running downloads count, but keep 'Not downloading' when none
        try:
            running = _count_active_download_links()
        except Exception:
            running = 0

        if running == 1:
            _ui_message(_('1 link downloading'))
        elif running > 1:
            _ui_message(_tr('{} links downloading', running))
        else:
            _ui_message(_('Not downloading'))



    def menu_left(self, e):
        if self.lb_left.GetSelection() == wx.NOT_FOUND:
            return
        m = wx.Menu()
        m.Append(1, _('Rename  r'))
        m.Append(2, _('Delete  Del'))
        m.Append(3, _('Save as M3U'))
        m.AppendSeparator()
        m.Append(4, _('Download playlist as audio  F1'))
        m.Append(5, _('Download playlist as video  F2'))
        self.Bind(wx.EVT_MENU, self.rename, id=1)
        self.Bind(wx.EVT_MENU, self.delete_list, id=2)
        self.Bind(wx.EVT_MENU, self.save_m3u, id=3)
        self.Bind(wx.EVT_MENU, lambda evt: self.download_whole_playlist(format_override=1), id=4)
        self.Bind(wx.EVT_MENU, lambda evt: self.download_whole_playlist(format_override=0), id=5)
        self.PopupMenu(m)
        m.Destroy()

    def rename(self, e):
        sel = self.lb_left.GetSelection()
        if sel == wx.NOT_FOUND:
            return
        old = self.lb_left.GetString(sel)
        dlg = wx.TextEntryDialog(self, _('New name'), value=old)
        if dlg.ShowModal() == wx.ID_OK:
            new = dlg.GetValue().strip()
            if new and new != old:
                self.main_window.playlists[new] = self.main_window.playlists.pop(old)
                save_playlists(self.main_window.playlists)
                self.refresh(force_right=True)
                self.lb_left.SetStringSelection(new)
        dlg.Destroy()

    def delete_list(self, e):
        sel = self.lb_left.GetSelection()
        if sel == wx.NOT_FOUND:
            return
        name = self.lb_left.GetString(sel)
        if wx.MessageBox(_('Delete this playlist'), _('Confirm'), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION) == wx.YES:
            del self.main_window.playlists[name]
            save_playlists(self.main_window.playlists)
            self.refresh(force_right=True)

    def save_m3u(self, e):
        sel = self.lb_left.GetSelection()
        if sel == wx.NOT_FOUND:
            return
        name = self.lb_left.GetString(sel)
        dlg = wx.FileDialog(self, _('Save'), wildcard='M3U|*.m3u', defaultFile=name + '.m3u', style=wx.FD_SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            with open(dlg.GetPath(), 'w', encoding='utf-8') as f:
                f.write('#EXTM3U\n')
                for v in self.main_window.playlists[name]:
                    f.write(f"#EXTINF:-1,{v.get('title','')}\n{v.get('url','')}\n")
            _ui_message(_('Saved'))
        dlg.Destroy()

    def _get_selected_playlist_name(self):
        try:
            name = self.lb_left.GetStringSelection()
            return name or None
        except Exception:
            return None

    def _get_selected_video_entry(self):
        name = self._get_selected_playlist_name()
        if not name:
            return None, None
        sel = self.lb_right.GetSelection()
        if sel == wx.NOT_FOUND:
            return name, None
        vids = self.main_window.playlists.get(name, [])
        if sel < 0 or sel >= len(vids):
            return name, None
        return name, vids[sel]

    def copy_selected_link(self, event=None):
        name, v = self._get_selected_video_entry()
        if not v:
            _ui_message(_('No item selected'))
            return False
        link = v.get('webpage_url') or v.get('original_url') or v.get('url')
        if not link:
            _ui_message(_('No link'))
            return False
        ok = copy_to_clipboard(link)
        if not ok:
            _ui_message(_('Copy failed'))
            return False
        _ui_message_later(_('Copied video link'))
        return True

    def download_selected(self, format_override=0):
        name, v = self._get_selected_video_entry()
        if not v:
            _ui_message(_('No item selected'))
            return False
        url = v.get('url')
        title = v.get('title') or ''
        if not url:
            _ui_message(_('No link'))
            return False
        return start_download(self.main_window, url, title, format_override, source_playlist=name, subfolder_title=name)

    def speak_download_status(self):
        name, v = self._get_selected_video_entry()
        if not v:
            _ui_message(_('Not downloading'))
            return
        url = v.get('url')
        if not url:
            _ui_message(_('Not downloading'))
            return
        speak_single_url_download_counts(url)

    def menu_right(self, e):
        if self.lb_right.GetSelection() == wx.NOT_FOUND:
            return
        m = wx.Menu()
        m.Append(1, _('Play  F7'))
        m.Append(3, _('Copy video link'))
        m.Append(2, _('Remove from playlist  Del'))
        m.AppendSeparator()
        m.Append(10, _('Download as audio  F1'))
        m.Append(11, _('Download as video  F2'))
        self.Bind(wx.EVT_MENU, self.play, id=1)
        self.Bind(wx.EVT_MENU, self.copy_selected_link, id=3)
        self.Bind(wx.EVT_MENU, self.remove_video, id=2)
        self.Bind(wx.EVT_MENU, lambda evt: self.download_selected(format_override=1), id=10)
        self.Bind(wx.EVT_MENU, lambda evt: self.download_selected(format_override=0), id=11)
        self.PopupMenu(m)
        m.Destroy()

    def remove_video(self, e):
        list_name = self.lb_left.GetStringSelection()
        vid = self.lb_right.GetSelection()
        if not list_name or vid == wx.NOT_FOUND:
            return

        vids = self.main_window.playlists.get(list_name, [])
        if vid < 0 or vid >= len(vids):
            return

        title = vids[vid].get('title', '')
        msg = _('Remove this link from this playlist')
        if title:
            msg = _tr('Remove  {}  from this playlist', title)
        if wx.MessageBox(msg, _('Confirm'), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION) != wx.YES:
            return

        del self.main_window.playlists[list_name][vid]
        save_playlists(self.main_window.playlists)
        self.select_left(None)

        try:
            count = self.lb_right.GetCount()
            if count > 0:
                new_idx = min(vid, count - 1)
                if new_idx >= 0:
                    self.lb_right.SetSelection(new_idx)
                    self.lb_right.SetFocus()
        except Exception:
            pass

        _ui_message(_('Removed'))

    def play(self, e):
        announce_player = self.main_window.current_settings.get('announce_player_keys', True)

        list_name = self.lb_left.GetStringSelection()
        if not list_name:
            _ui_message(_('No playlist selected'))
            return

        vids = self.main_window.playlists.get(list_name, [])
        if not vids:
            _ui_message(_('No items in this playlist'))
            return

        vid = self.lb_right.GetSelection()
        if vid == wx.NOT_FOUND:
            if self.lb_right.GetCount() > 0:
                vid = 0
                self.lb_right.SetSelection(0)
            else:
                _ui_message(_('No item selected'))
                return

        if vid < 0 or vid >= len(vids):
            _ui_message(_('No item selected'))
            return

        origin = f'userplaylist::{list_name}'
        selected_url = (vids[vid].get('url') or '').strip()

        if is_player_running() and state.current_playlist_origin_url == origin and state.current_playlist_file is not None:
            if state.current_playlist_start_url and selected_url and selected_url == state.current_playlist_start_url:
                stop_playback(announce=False, preserve_volume=True, preserve_playlist_file=True)
                if announce_player:
                    _ui_message(_('Stop'))
                return
            stop_playback(announce=False, preserve_volume=True)

        items_to_play = []
        for v in vids[vid:]:
            if not v:
                continue
            u = (v.get('url') or '').strip()
            if not u:
                continue
            items_to_play.append({
                'url': u,
                'title': v.get('title') or '',
                'duration': v.get('duration') or '',
            })

        if not items_to_play:
            _ui_message(_('No valid url to play'))
            return

        pl_file = _create_temp_m3u(items_to_play, title=list_name)
        if not pl_file:
            _ui_message(_('Cannot create playlist file'))
            return

        first_url = items_to_play[0].get('url') or ''

        _set_track_context(items_to_play, 0)

        if is_player_running():
            stop_playback(announce=False, preserve_volume=True)

        start_playback(
            pl_file,
            list_name,
            announce=announce_player,
            playing_url_hint=first_url,
            playlist_file=pl_file,
            playlist_origin_url=origin,
        )


# --- 2B SUBSCRIPTIONS TAB ---

# Section keys, in the fixed order they are shown in, each mapped to the
# channel-tab URL helper that fetches it and the TH_STRINGS key for its
# label. This is what lets the right-hand list browse a subscribed
# channel the same way YouTube itself splits a channel into tabs, instead
# of only ever showing one fixed "latest videos" list.
_SUBSCRIPTIONS_SECTION_ORDER = ('videos', 'shorts', 'live', 'playlists')
_SUBSCRIPTIONS_SECTION_URL_FUNCS = {
    'videos': _channel_videos_tab_url,
    'shorts': _channel_shorts_tab_url,
    'live': _channel_live_tab_url,
    'playlists': _channel_playlists_tab_url,
}
_SUBSCRIPTIONS_SECTION_LABELS = {
    'videos': 'Videos',
    'shorts': 'Shorts',
    'live': 'Live',
    'playlists': 'Playlists',
}


class SubscriptionsTab(wx.Panel):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.channel_keys = []
        self.video_data = []
        # What the right-hand list (lb_videos) currently shows, and so what
        # Enter/Backspace/F1-F4/F7-F12/Ctrl+C on it should do:
        #   'sections'  - the 4 section rows (Videos/Shorts/Live/Playlists)
        #                 for the selected channel; Enter drills in.
        #   'items'     - actual playable videos (from a Videos/Shorts/Live
        #                 section, or from inside one specific playlist);
        #                 Enter/F7 plays, F1/F2/F3/Ctrl+C act on it.
        #   'playlists' - the selected channel's own playlists; Enter drills
        #                 into one playlist's videos.
        self._list_kind = 'sections'
        # Stack of previous (list_kind, video_data, labels, selection)
        # snapshots to restore on Backspace - at most 2 deep in practice
        # (sections -> a leaf section, or sections -> playlists -> one
        # playlist's videos), kept as a real stack rather than hardcoded
        # levels so it stays correct if a level is ever added later.
        self._nav_stack = []
        # Key and display name of whichever channel is currently loaded in
        # the right pane, kept in sync by load_channel_sections(). Used so
        # downloads started from the right pane land in a subfolder named
        # after the channel (matching how Playlists organizes downloads by
        # playlist name) and so F5/F3's per-channel behavior always matches
        # what is actually on screen.
        self._current_channel_key = None
        self._current_channel_name = None

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        left = wx.BoxSizer(wx.VERTICAL)
        self.lbl_channels = wx.StaticText(self, label=_('Subscribed channels'))
        left.Add(self.lbl_channels, 0, wx.ALL, 5)
        self.lb_channels = wx.ListBox(self)
        self.lb_channels.Bind(wx.EVT_LISTBOX, self.on_select_channel)
        self.lb_channels.Bind(wx.EVT_KEY_DOWN, self.key_channels)
        self.lb_channels.Bind(wx.EVT_CONTEXT_MENU, self.menu_channels)
        left.Add(self.lb_channels, 1, wx.EXPAND | wx.ALL, 5)

        right = wx.BoxSizer(wx.VERTICAL)
        self.lbl_videos = wx.StaticText(self, label=_('Channel content'))
        right.Add(self.lbl_videos, 0, wx.ALL, 5)
        self.lb_videos = wx.ListBox(self)
        self.lb_videos.Bind(wx.EVT_KEY_DOWN, self.key_videos)
        self.lb_videos.Bind(wx.EVT_LISTBOX_DCLICK, self.activate_selected)
        self.lb_videos.Bind(wx.EVT_CONTEXT_MENU, self.menu_videos)
        right.Add(self.lb_videos, 1, wx.EXPAND | wx.ALL, 5)

        self.btn_exit = wx.Button(self, label=_('Exit'))
        self.btn_exit.Bind(wx.EVT_BUTTON, self.on_exit)
        right.Add(self.btn_exit, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        sizer.Add(left, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(right, 2, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)

        # Used by MainWindow.catch_key to detect the last control on
        # this tab, so Tab does not wrap past it.
        self.last_focus_ctrl = self.btn_exit

        self.refresh()

    def on_exit(self, event):
        self.main_window.exit_now()

    def focus_playing(self):
        """Mirrors SearchAndDownloadTab.focus_playing() / PlaylistTab.focus_playing():
        when the window is reopened while something is still playing and
        Subscriptions was the last active tab, put focus back on the
        playing item in the video list if it is still the one currently
        loaded there (only meaningful while _list_kind == 'items' - a
        section/playlist container row never matches a real playing url)."""
        if not state.current_playing_url:
            return
        try:
            for i, v in enumerate(self.video_data):
                if v.get('url') == state.current_playing_url:
                    if 0 <= i < self.lb_videos.GetCount():
                        self.lb_videos.SetSelection(i)
                    self.lb_videos.SetFocus()
                    break
        except Exception as e:
            log.error(f'Error focusing current playing item in SubscriptionsTab: {e}')

    def refresh_language(self):
        try:
            self.lbl_channels.SetLabel(_('Subscribed channels'))
            self.lbl_videos.SetLabel(_('Channel content'))
            self.btn_exit.SetLabel(_('Exit'))
            self.refresh()
            self.Layout()
        except Exception as e:
            log.error(f'Error refreshing language on subscriptions tab: {e}')

    def speak_help(self):
        _ui_message(_(
            'Subscriptions help. '
            'The channel list holds channels you have subscribed to. Press Tab to move to the '
            'right-hand list. On the channel list: press Enter to browse that channel, F1 and F2 '
            'download all of its latest videos as audio or video, F3 announces its download status, '
            'Delete unsubscribes after asking you to confirm. '
            'The right-hand list browses a selected channel the same way YouTube itself does: '
            'selecting a channel first shows its Videos, Shorts, Live, and Playlists sections - '
            'press Enter on one to open it. Opening Videos, Shorts, or Live shows that section\'s '
            'videos directly; opening Playlists shows the channel\'s own playlists, and pressing '
            'Enter on one of those opens its videos. Press Backspace to go back up one level at '
            'any point. Once a video is shown: F7 plays or stops, F8 pauses or resumes, F9 and F10 '
            'go to the previous or next track, F11 and F12 turn the volume down or up. Space also '
            'pauses or resumes, and Home and End turn the volume up or down. F1 and F2 download the '
            'selected video as audio or video, F3 announces its download status, F4 announces how '
            'many downloads are running, F5 opens the download folder, Control+C copies its link. '
            'To subscribe to a channel in the first place, find one of its videos on the Search and '
            'Download tab and press Control+S there. '
            'Press Control+F1 again on any tab to hear its own help.'
        ))

    def refresh(self):
        subs = load_subscriptions()
        self.channel_keys = list(subs.keys())
        items = []
        for key in self.channel_keys:
            rec = subs.get(key) or {}
            items.append(rec.get('channel_name') or key)

        sel = self.lb_channels.GetSelection()
        self.lb_channels.Set(items)
        if sel != wx.NOT_FOUND and 0 <= sel < len(items):
            self.lb_channels.SetSelection(sel)

    def _selected_channel_key(self):
        idx = self.lb_channels.GetSelection()
        if idx == wx.NOT_FOUND or idx < 0 or idx >= len(self.channel_keys):
            return None
        return self.channel_keys[idx]

    def on_select_channel(self, event):
        self.load_channel_sections()

    def _channel_display_name(self, key):
        subs = load_subscriptions()
        rec = subs.get(key) or {}
        return rec.get('channel_name') or key

    def _current_channel_name_for_folder(self):
        """Subfolder name to use for F5's 'open download folder' on this
        tab: the channel currently loaded in the right pane, matching how
        the other tabs pick a subfolder for F5."""
        return self._current_channel_name

    def load_channel_sections(self):
        """Runs whenever the selected channel changes: resets the
        right-hand list back to the top-level Videos/Shorts/Live/Playlists
        section list for the newly selected channel, discarding any
        drill-down the previous channel may have been left in."""
        key = self._selected_channel_key()
        self._nav_stack = []
        if not key:
            self._current_channel_key = None
            self._current_channel_name = None
            self._list_kind = 'sections'
            self.video_data = []
            self.lb_videos.Clear()
            return

        self._current_channel_key = key
        self._current_channel_name = self._channel_display_name(key)
        self._show_sections()

    def _show_sections(self):
        self._list_kind = 'sections'
        self.video_data = [{'section_key': sk} for sk in _SUBSCRIPTIONS_SECTION_ORDER]
        labels = [_(_SUBSCRIPTIONS_SECTION_LABELS[sk]) for sk in _SUBSCRIPTIONS_SECTION_ORDER]
        self.lb_videos.Set(labels)
        if labels:
            self.lb_videos.SetSelection(0)

    def _push_nav_stack(self):
        self._nav_stack.append({
            'list_kind': self._list_kind,
            'video_data': list(self.video_data),
            'labels': list(self.lb_videos.GetStrings()),
            'selection': self.lb_videos.GetSelection(),
        })

    def handle_backspace(self):
        """Pop one level back up the channel/section/playlist drill-down.
        Returns False (so the caller can fall through to default handling)
        when there is nothing to go back to - i.e. already at the top-level
        section list."""
        if not self._nav_stack:
            return False
        prev = self._nav_stack.pop()
        self._list_kind = prev['list_kind']
        self.video_data = prev['video_data']
        self.lb_videos.Set(prev['labels'])
        sel = prev.get('selection')
        if sel is None or sel == wx.NOT_FOUND or sel < 0:
            sel = 0
        if self.lb_videos.GetCount() > 0:
            sel = min(sel, self.lb_videos.GetCount() - 1)
            self.lb_videos.SetSelection(sel)
        _ui_message(_('Back'))
        return True

    def _open_section(self, section_key):
        key = self._current_channel_key
        url_fn = _SUBSCRIPTIONS_SECTION_URL_FUNCS.get(section_key)
        if not key or not url_fn:
            return
        name = self._current_channel_name

        _ui_message(_('Fetching playlist items'))

        def _done(data):
            items = list((data or {}).get('items') or [])
            if not items:
                _ui_message(_('No items found'))
                return

            self._push_nav_stack()

            if section_key == 'playlists':
                self._list_kind = 'playlists'
                self.video_data = [dict(it) for it in items]
                total = len(self.video_data)
                labels = []
                for idx, it in enumerate(self.video_data):
                    title = it.get('title') or _('Unknown title')
                    count = it.get('count') or ''
                    base = _tr('Playlist  {}', title)
                    if count:
                        base += _tr(' ({})', count)
                    base += _tr('  {} of {}', idx + 1, total)
                    labels.append(base)
            else:
                self._list_kind = 'items'
                self.video_data = [dict(it) for it in items]
                # Tag each item with the channel it came from, so downloads
                # started from this list land in a subfolder named after
                # the channel and count toward that channel's aggregate
                # download status - the same convention the Playlists tab
                # uses for its own song list, kept the same regardless of
                # which section or nested playlist a video was found
                # through, so F3 on the channel row always aggregates
                # everything downloaded from it via this tab.
                for v in self.video_data:
                    v['subfolder_title'] = name
                    v['source_playlist'] = key
                labels = self._build_video_labels(self.video_data)

            self.lb_videos.Set(labels)
            if labels:
                self.lb_videos.SetSelection(0)

        request_playlist_items(
            url_fn(key), _done, limit=20,
            item_kind='playlist' if section_key == 'playlists' else 'video',
        )

    def _open_playlist(self, entry):
        pl_url = entry.get('url')
        if not pl_url:
            _ui_message(_('No playlist url'))
            return
        key = self._current_channel_key
        name = self._current_channel_name

        _ui_message(_('Fetching playlist items'))

        def _done(data):
            items = list((data or {}).get('items') or [])
            if not items:
                _ui_message(_('No items found'))
                return

            self._push_nav_stack()

            self._list_kind = 'items'
            self.video_data = [dict(it) for it in items]
            # Same tagging convention as _open_section() above - grouped
            # under the channel, not the individual playlist, so F3 on the
            # channel row still reflects everything downloaded from it.
            for v in self.video_data:
                v['subfolder_title'] = name
                v['source_playlist'] = key
            labels = self._build_video_labels(self.video_data)

            self.lb_videos.Set(labels)
            if labels:
                self.lb_videos.SetSelection(0)

        request_playlist_items(pl_url, _done, limit=200)

    @staticmethod
    def _build_video_labels(video_data):
        total = len(video_data)
        labels = []
        for i, v in enumerate(video_data):
            title = v.get('title') or _('Unknown title')
            dur = v.get('duration') or ''
            label = _tr('{} [{}]', title, dur) if dur else title
            label += _tr('  {} of {}', i + 1, total)
            labels.append(label)
        return labels

    def key_channels(self, event):
        code = event.GetKeyCode()
        key = self._selected_channel_key()
        announce_player = self.main_window.current_settings.get('announce_player_keys', True)

        if code == wx.WXK_DELETE:
            self._unsubscribe_channel(key)
            return

        if code == wx.WXK_SPACE:
            if is_player_running():
                toggle_pause(announce=announce_player)
                return

        if code == wx.WXK_HOME:
            if is_player_running():
                volume_up(announce=announce_player)
                return

        if code == wx.WXK_END:
            if is_player_running():
                volume_down(announce=announce_player)
                return

        if code == wx.WXK_F1:
            self.download_channel_videos(key, format_override=1)
            return

        if code == wx.WXK_F2:
            self.download_channel_videos(key, format_override=0)
            return

        if code == wx.WXK_F3:
            if key:
                speak_channel_download_counts(key)
            else:
                _ui_message(_('No channel selected'))
            return

        event.Skip()

    def _unsubscribe_channel(self, key):
        """Shared by Delete on the channel list and the right-click/Menu-key
        context menu, so both paths ask the same confirmation and update
        state identically."""
        if not key:
            return
        subs = load_subscriptions()
        if key not in subs:
            return
        name = subs[key].get('channel_name') or key
        if wx.MessageBox(_tr('Unsubscribe from {}', name), _('Confirm'), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION) == wx.YES:
            del subs[key]
            save_subscriptions(subs)
            self._nav_stack = []
            self._list_kind = 'sections'
            self.video_data = []
            self.lb_videos.Clear()
            if self._current_channel_key == key:
                self._current_channel_key = None
                self._current_channel_name = None
            self.refresh()
            _ui_message(_tr('Unsubscribed from {}', name))

    def menu_channels(self, event):
        """Right-click / Menu-key context menu for the channel list, added
        so this list has the same menu-key affordance as every other list
        in the add-on (Search and Download's results, Playlists' two
        lists). Mirrors key_channels' own shortcuts exactly."""
        key = self._selected_channel_key()
        if not key:
            return
        menu = wx.Menu()
        menu.Append(1, _('Download latest videos as audio  F1'))
        menu.Append(2, _('Download latest videos as video  F2'))
        menu.Append(3, _('Announce download status  F3'))
        menu.AppendSeparator()
        menu.Append(4, _('Unsubscribe  Del'))
        self.Bind(wx.EVT_MENU, lambda e: self.download_channel_videos(key, format_override=1), id=1)
        self.Bind(wx.EVT_MENU, lambda e: self.download_channel_videos(key, format_override=0), id=2)
        self.Bind(wx.EVT_MENU, lambda e: speak_channel_download_counts(key), id=3)
        self.Bind(wx.EVT_MENU, lambda e: self._unsubscribe_channel(key), id=4)
        self.PopupMenu(menu)
        menu.Destroy()

    def download_channel_videos(self, key, format_override=1):
        if not key:
            _ui_message(_('No channel selected'))
            return

        name = self._channel_display_name(key)

        def _done(data):
            items = list((data or {}).get('items') or [])
            if not items:
                _ui_message(_('No items found'))
                return

            count = 0
            for v in items:
                u = v.get('url')
                t = v.get('title') or _('Unknown title')
                if not u:
                    continue
                ok = start_download(self.main_window, u, t, format_override, source_playlist=key, subfolder_title=name)
                if ok:
                    count += 1

            if count <= 0:
                _ui_message(_('No downloadable items'))
            else:
                _ui_message(_tr('Download queued  {} items', count))

        _ui_message(_('Fetching playlist items'))
        request_playlist_items(_channel_videos_tab_url(key), _done, limit=20)

    def _selected_row(self):
        """Raw access to whatever row is selected in the right-hand list,
        regardless of _list_kind - used only by activate_selected() to
        decide whether to drill in or play. Everything else should use
        _selected_video() below instead."""
        idx = self.lb_videos.GetSelection()
        if idx == wx.NOT_FOUND or idx < 0 or idx >= len(self.video_data):
            return None
        return self.video_data[idx]

    def _selected_video(self):
        """Like _selected_row(), but only ever returns a real, playable/
        downloadable video entry - returns None whenever the right-hand
        list is currently showing a container level (the section list, or
        a channel's list of playlists) rather than actual videos. Every
        existing F1/F2/F3/F7-F12/Ctrl+C handler already treats "no item
        selected" as a safe no-op, so gating here means none of them need
        their own special case for container rows."""
        if self._list_kind != 'items':
            return None
        return self._selected_row()

    def activate_selected(self, event=None):
        """Enter (and double-click) on the right-hand list: drill into
        whatever is selected if it is a section or a playlist, or play it
        if it is an actual video."""
        entry = self._selected_row()
        if not entry:
            _ui_message(_('No item selected'))
            return
        if self._list_kind == 'sections':
            self._open_section(entry.get('section_key'))
            return
        if self._list_kind == 'playlists':
            self._open_playlist(entry)
            return
        self.play_selected()

    def play_selected(self, event=None):
        entry = self._selected_video()
        if not entry:
            _ui_message(_('No item selected'))
            return
        url = entry.get('url')
        title = entry.get('title') or ''
        if not url:
            _ui_message(_('No valid url to play'))
            return
        try:
            _set_track_context(self.video_data, self.lb_videos.GetSelection())
        except Exception:
            pass
        announce_player = self.main_window.current_settings.get('announce_player_keys', True)
        if is_player_running():
            if state.current_playing_url and state.current_playing_url == url and state.current_playlist_file is None:
                stop_playback(announce=False, preserve_volume=True)
                if announce_player:
                    _ui_message(_('Stop'))
                return
            stop_playback(announce=False, preserve_volume=True)
        start_playback(url, title, announce=announce_player, playing_url_hint=url)

    def speak_status_anywhere(self):
        focus = wx.Window.FindFocus()

        if focus == self.lb_channels:
            key = self._selected_channel_key()
            if key:
                speak_channel_download_counts(key)
            else:
                _ui_message(_('No channel selected'))
            return

        entry = self._selected_video()
        if entry:
            speak_single_url_download_counts(entry.get('url'))
            return

        key = self._current_channel_key
        if key:
            speak_channel_download_counts(key)
            return

        _ui_message(_('Not downloading'))

    def handle_player_key(self, code):
        announce_player = self.main_window.current_settings.get('announce_player_keys', True)

        entry = self._selected_video()
        if entry is None:
            if code == wx.WXK_F8 and is_player_running():
                toggle_pause(announce=announce_player)
                return True
            if code == wx.WXK_F9:
                track_prev(announce=announce_player)
                return True
            if code == wx.WXK_F10:
                track_next(announce=announce_player)
                return True
            if code == wx.WXK_F11 and is_player_running():
                volume_down(announce=announce_player)
                return True
            if code == wx.WXK_F12 and is_player_running():
                volume_up(announce=announce_player)
                return True
            return False

        if code == wx.WXK_F7:
            self.play_selected()
            return True
        if code == wx.WXK_F8:
            if is_player_running():
                toggle_pause(announce=announce_player)
            return True
        if code == wx.WXK_F9:
            track_prev(announce=announce_player)
            return True
        if code == wx.WXK_F10:
            track_next(announce=announce_player)
            return True
        if code == wx.WXK_F11:
            if is_player_running():
                volume_down(announce=announce_player)
            return True
        if code == wx.WXK_F12:
            if is_player_running():
                volume_up(announce=announce_player)
            return True

        return False

    def key_videos(self, event):
        code = event.GetKeyCode()
        announce_player = self.main_window.current_settings.get('announce_player_keys', True)

        if code == wx.WXK_BACK:
            # Normally unreachable in practice - MainWindow.catch_key
            # handles Backspace for this list directly first, the same
            # reliability fix already applied to Enter across every list
            # in the add-on. Kept here too as a harmless fallback.
            if self.handle_backspace():
                return

        if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.activate_selected()
            return

        if code == wx.WXK_F7:
            self.play_selected()
            return

        if code == wx.WXK_SPACE:
            if is_player_running():
                toggle_pause(announce=announce_player)
                return

        if code == wx.WXK_HOME:
            if is_player_running():
                volume_up(announce=announce_player)
                return

        if code == wx.WXK_END:
            if is_player_running():
                volume_down(announce=announce_player)
                return

        entry = self._selected_video()
        if entry is not None:
            if code == wx.WXK_F1:
                start_download(self.main_window, entry.get('url'), entry.get('title'), 1, source_playlist=entry.get('source_playlist'), subfolder_title=entry.get('subfolder_title'))
                return
            if code == wx.WXK_F2:
                start_download(self.main_window, entry.get('url'), entry.get('title'), 0, source_playlist=entry.get('source_playlist'), subfolder_title=entry.get('subfolder_title'))
                return
            if code == wx.WXK_F3:
                speak_single_url_download_counts(entry.get('url'))
                return
            if event.ControlDown() and code == ord('C'):
                self._copy_selected_video_link()
                return

        event.Skip()

    def _copy_selected_video_link(self):
        """Shared by Control+C on the video list and the "Copy video link"
        context menu item."""
        entry = self._selected_video()
        if not entry:
            _ui_message(_('No item selected'))
            return
        link = entry.get('url')
        if link:
            ok = copy_to_clipboard(link)
            _ui_message_later(_tr('Copied {}', _('video link'))) if ok else _ui_message(_('Copy failed'))
        else:
            _ui_message(_('No link'))

    def menu_videos(self, event):
        """Right-click / Menu-key context menu for the video list, added so
        this list has the same menu-key affordance as every other list in
        the add-on. Only offered for actual playable videos - _selected_video()
        already returns None for section/playlist container rows, which
        keeps this consistent with every F1/F2/F3/Ctrl+C handler above
        without its own special case."""
        entry = self._selected_video()
        if not entry:
            return
        menu = wx.Menu()
        menu.Append(1, _('Play  F7'))
        menu.Append(2, _('Copy video link'))
        menu.AppendSeparator()
        menu.Append(3, _('Download as audio  F1'))
        menu.Append(4, _('Download as video  F2'))
        menu.Append(5, _('Announce download status  F3'))
        self.Bind(wx.EVT_MENU, lambda e: self.play_selected(), id=1)
        self.Bind(wx.EVT_MENU, lambda e: self._copy_selected_video_link(), id=2)
        self.Bind(wx.EVT_MENU, lambda e: start_download(self.main_window, entry.get('url'), entry.get('title'), 1, source_playlist=entry.get('source_playlist'), subfolder_title=entry.get('subfolder_title')), id=3)
        self.Bind(wx.EVT_MENU, lambda e: start_download(self.main_window, entry.get('url'), entry.get('title'), 0, source_playlist=entry.get('source_playlist'), subfolder_title=entry.get('subfolder_title')), id=4)
        self.Bind(wx.EVT_MENU, lambda e: speak_single_url_download_counts(entry.get('url')), id=5)
        self.PopupMenu(menu)
        menu.Destroy()


# --- 3 SETTINGS TAB ---

class SettingsTab(wx.Panel):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.lbl_download_folder = wx.StaticText(self, label=_('Download folder'))
        sizer.Add(self.lbl_download_folder, 0, wx.TOP | wx.LEFT, 10)
        self.picker = wx.DirPickerCtrl(self, path=self.main_window.current_settings['download_folder'])
        sizer.Add(self.picker, 0, wx.EXPAND | wx.ALL, 10)

        self.box_quality = wx.StaticBoxSizer(wx.VERTICAL, self, _('Quality options'))

        self.lbl_video_res = wx.StaticText(self, label=_('Video resolution'))
        self.box_quality.Add(self.lbl_video_res, 0, wx.TOP, 5)
        self.ch_video = wx.Choice(self, choices=[_('480p  SD'), _('720p  HD'), _('1080p  Full HD'), _('Best  automatic')])
        self.ch_video.SetSelection(self.main_window.current_settings.get('video_quality_idx', 3))
        self.box_quality.Add(self.ch_video, 0, wx.EXPAND | wx.ALL, 5)

        self.lbl_audio_quality = wx.StaticText(self, label=_('Audio quality  bitrate'))
        self.box_quality.Add(self.lbl_audio_quality, 0, wx.TOP, 5)
        self.ch_audio = wx.Choice(self, choices=[_('128 kbps  Low'), _('192 kbps  Standard'), _('320 kbps  High')])
        self.ch_audio.SetSelection(self.main_window.current_settings.get('audio_quality_idx', 1))
        self.box_quality.Add(self.ch_audio, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(self.box_quality, 0, wx.EXPAND | wx.ALL, 10)

        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_search_limit = wx.StaticText(self, label=_('Search result limit'))
        h_sizer.Add(self.lbl_search_limit, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.ch_limit = wx.Choice(self, choices=[str(v) for v in SEARCH_LIMIT_CHOICES])
        current_limit = normalize_search_limit(self.main_window.current_settings.get('search_result_limit', 25))
        try:
            idx = SEARCH_LIMIT_CHOICES.index(current_limit)
        except Exception:
            idx = 0
        self.ch_limit.SetSelection(idx)
        h_sizer.Add(self.ch_limit, 0)
        sizer.Add(h_sizer, 0, wx.ALL, 10)

        self.chk_announce = wx.CheckBox(self, label=_('Announce player hotkeys'))
        self.chk_announce.SetValue(bool(self.main_window.current_settings.get('announce_player_keys', True)))
        sizer.Add(self.chk_announce, 0, wx.ALL, 10)

        self.chk_global = wx.CheckBox(self, label=_('Enable global player hotkeys outside this window'))
        self.chk_global.SetValue(bool(self.main_window.current_settings.get('global_player_hotkeys', False)))
        sizer.Add(self.chk_global, 0, wx.ALL, 10)

        self.chk_auto_continue = wx.CheckBox(self, label=_('Automatically play the next item when the current one ends'))
        self.chk_auto_continue.SetValue(bool(self.main_window.current_settings.get('auto_continue_playback', False)))
        sizer.Add(self.chk_auto_continue, 0, wx.ALL, 10)

        self.chk_sleep_beep = wx.CheckBox(self, label=_('Play advance warnings before the sleep timer stops playback'))
        self.chk_sleep_beep.SetValue(bool(self.main_window.current_settings.get('sleep_timer_beep_warning', True)))
        sizer.Add(self.chk_sleep_beep, 0, wx.ALL, 10)

        self.box_subs = wx.StaticBoxSizer(wx.HORIZONTAL, self, _('Subscriptions backup'))
        self.btn_export_subs = wx.Button(self, label=_('Export subscriptions'))
        self.btn_export_subs.Bind(wx.EVT_BUTTON, self.on_export_subscriptions)
        self.box_subs.Add(self.btn_export_subs, 0, wx.ALL, 5)
        self.btn_import_subs = wx.Button(self, label=_('Import subscriptions'))
        self.btn_import_subs.Bind(wx.EVT_BUTTON, self.on_import_subscriptions)
        self.box_subs.Add(self.btn_import_subs, 0, wx.ALL, 5)
        sizer.Add(self.box_subs, 0, wx.EXPAND | wx.ALL, 10)

        self.box_update = wx.StaticBoxSizer(wx.VERTICAL, self, _('yt-dlp library'))

        bundled_version = _get_bundled_ytdlp_version() or _('unknown')
        self.lbl_ytdlp_version = wx.StaticText(self, label=_tr('Current version: {}', bundled_version))
        self.box_update.Add(self.lbl_ytdlp_version, 0, wx.TOP | wx.LEFT, 5)

        self.chk_auto_update = wx.CheckBox(self, label=_('Automatically check for yt-dlp updates'))
        self.chk_auto_update.SetValue(bool(self.main_window.current_settings.get('auto_update_ytdlp', True)))
        self.box_update.Add(self.chk_auto_update, 0, wx.ALL, 5)

        self.btn_check_update = wx.Button(self, label=_('Check for update now'))
        self.btn_check_update.Bind(wx.EVT_BUTTON, self.on_check_update)
        self.box_update.Add(self.btn_check_update, 0, wx.ALL, 5)

        self.lbl_update_status = wx.StaticText(self, label='')
        self.box_update.Add(self.lbl_update_status, 0, wx.ALL, 5)

        sizer.Add(self.box_update, 0, wx.EXPAND | wx.ALL, 10)

        self.btn_save = wx.Button(self, label=_('Save settings'))
        self.btn_save.Bind(wx.EVT_BUTTON, self.save)
        sizer.Add(self.btn_save, 0, wx.ALIGN_CENTER | wx.ALL, 8)

        self.btn_exit = wx.Button(self, label=_('Exit'))
        self.btn_exit.Bind(wx.EVT_BUTTON, self.on_exit)
        sizer.Add(self.btn_exit, 0, wx.ALIGN_RIGHT | wx.ALL, 8)

        self.SetSizer(sizer)

        # Used by MainWindow.catch_key to detect the last control on
        # this tab, so Tab does not wrap past it.
        self.last_focus_ctrl = self.btn_exit

    def refresh_language(self):
        try:
            self.lbl_download_folder.SetLabel(_('Download folder'))
            try:
                self.box_quality.GetStaticBox().SetLabel(_('Quality options'))
            except Exception:
                pass
            self.lbl_video_res.SetLabel(_('Video resolution'))
            sel_v = self.ch_video.GetSelection()
            self.ch_video.Set([_('480p  SD'), _('720p  HD'), _('1080p  Full HD'), _('Best  automatic')])
            if sel_v != wx.NOT_FOUND:
                self.ch_video.SetSelection(sel_v)
            self.lbl_audio_quality.SetLabel(_('Audio quality  bitrate'))
            sel_a = self.ch_audio.GetSelection()
            self.ch_audio.Set([_('128 kbps  Low'), _('192 kbps  Standard'), _('320 kbps  High')])
            if sel_a != wx.NOT_FOUND:
                self.ch_audio.SetSelection(sel_a)
            self.lbl_search_limit.SetLabel(_('Search result limit'))
            self.chk_announce.SetLabel(_('Announce player hotkeys'))
            self.chk_global.SetLabel(_('Enable global player hotkeys outside this window'))
            self.chk_auto_continue.SetLabel(_('Automatically play the next item when the current one ends'))
            self.chk_sleep_beep.SetLabel(_('Play advance warnings before the sleep timer stops playback'))
            try:
                self.box_subs.GetStaticBox().SetLabel(_('Subscriptions backup'))
            except Exception:
                pass
            self.btn_export_subs.SetLabel(_('Export subscriptions'))
            self.btn_import_subs.SetLabel(_('Import subscriptions'))
            try:
                self.box_update.GetStaticBox().SetLabel(_('yt-dlp library'))
            except Exception:
                pass
            bundled_version = _get_bundled_ytdlp_version() or _('unknown')
            self.lbl_ytdlp_version.SetLabel(_tr('Current version: {}', bundled_version))
            self.chk_auto_update.SetLabel(_('Automatically check for yt-dlp updates'))
            self.btn_check_update.SetLabel(_('Check for update now'))
            self.btn_save.SetLabel(_('Save settings'))
            self.btn_exit.SetLabel(_('Exit'))
            self.Layout()
        except Exception as e:
            log.error(f'Error refreshing language on settings tab: {e}')

    def on_exit(self, event):
        self.main_window.exit_now()

    def speak_help(self):
        _ui_message(_(
            'Settings help. '
            'Choose your download folder, then set video resolution and audio quality; '
            'both lists now read from lowest to highest quality. '
            'Choose how many search results to fetch. '
            'The checkboxes control whether player hotkeys are announced, whether they still work '
            'when this window does not have focus while something is playing, whether the next '
            'item in the list plays automatically when the current one ends, and whether you get '
            'advance warnings before the sleep timer stops playback  a spoken notice at 1 minute left and a short '
            'beep once per second for the last 10 seconds; turning this off leaves only the '
            'announcement and one longer confirmation beep the moment playback actually stops, '
            'which always happen. '
            'Export subscriptions saves your followed channels to a file you choose, and Import '
            'subscriptions adds channels from a previously exported file into your current list '
            'without removing any you already follow - useful when moving to a new computer or '
            'reinstalling NVDA. '
            'The yt-dlp library section shows the version in use, lets you turn automatic update checks '
            'on or off, and has a button to check for an update right now. '
            'Remember to press Save settings after making changes for them to take effect.'
        ))

    def on_export_subscriptions(self, event):
        subs = load_subscriptions()
        if not subs:
            _ui_message(_('No subscribed channels'))
            return
        dlg = wx.FileDialog(
            self, _('Export subscriptions'), wildcard='JSON (*.json)|*.json',
            defaultFile='subscriptions.json', style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            ok = _safe_write_json(path, subs, encoding='utf-8', indent=4, ensure_ascii=False)
            if ok:
                _ui_message(_tr('Exported {} channels', len(subs)))
            else:
                _ui_message(_('Export failed'))
        dlg.Destroy()

    def on_import_subscriptions(self, event):
        dlg = wx.FileDialog(
            self, _('Import subscriptions'), wildcard='JSON (*.json)|*.json',
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            imported = _safe_load_json_dict(path, encoding='utf-8')
            if not imported:
                _ui_message(_('Import failed'))
                dlg.Destroy()
                return
            current = load_subscriptions()
            added = 0
            for key, rec in imported.items():
                # Merge rather than replace: importing a backup should
                # never silently remove channels the user already follows,
                # only add ones that were missing.
                if key not in current and isinstance(rec, dict):
                    current[key] = rec
                    added += 1
            if added:
                save_subscriptions(current)
                try:
                    if self.main_window.tab_subscriptions:
                        self.main_window.tab_subscriptions.refresh()
                except Exception:
                    pass
            _ui_message(_tr('Imported {} new channels', added))
        dlg.Destroy()

    def on_check_update(self, event):
        self.btn_check_update.Disable()
        try:
            self.lbl_update_status.SetLabel(_('Checking for yt-dlp update') + '...')
        except Exception:
            pass

        def _on_done(found_update, message):
            try:
                self.btn_check_update.Enable()
            except Exception:
                pass
            try:
                self.lbl_update_status.SetLabel(message or '')
            except Exception:
                pass
            if found_update:
                try:
                    self.lbl_ytdlp_version.SetLabel(
                        _tr('Current version: {} ({})', _get_bundled_ytdlp_version() or _('unknown'),
                            _('restart NVDA to use it'))
                    )
                except Exception:
                    pass

        check_for_ytdlp_update(manual=True, on_done=_on_done)

    def save(self, event):
        limit_val = SEARCH_LIMIT_CHOICES[self.ch_limit.GetSelection()] if self.ch_limit.GetSelection() != wx.NOT_FOUND else 25

        # Start from the full, current settings (not just the fields shown
        # on this tab) so background-only values such as
        # last_ytdlp_update_check are never silently dropped when saving.
        new_settings = dict(load_settings())
        new_settings.update({
            'download_folder': self.picker.GetPath(),
            'search_result_limit': limit_val,
            'video_quality_idx': self.ch_video.GetSelection(),
            'audio_quality_idx': self.ch_audio.GetSelection(),
            'announce_player_keys': self.chk_announce.GetValue(),
            'global_player_hotkeys': self.chk_global.GetValue(),
            'auto_continue_playback': self.chk_auto_continue.GetValue(),
            'auto_update_ytdlp': self.chk_auto_update.GetValue(),
            'sleep_timer_beep_warning': self.chk_sleep_beep.GetValue(),
        })
        save_settings(new_settings)
        self.main_window.current_settings = load_settings()
        _ui_message(_('Settings saved'))
