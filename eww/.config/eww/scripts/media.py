#!/usr/bin/env python3
import subprocess
import json
import sys
import os
import re
import urllib.request
import hashlib
from pathlib import Path

CACHE_DIR = Path('/tmp/eww_media_cache')
DEFAULT_COVER = os.path.expanduser('~/.config/eww/assets/default_cover.png')

CACHE_DIR.mkdir(parents=True, exist_ok=True)

def run_cmd(args):
    try:
        res = subprocess.run(args, capture_output=True, text=True, check=False)
        return res.stdout.strip(), res.returncode
    except Exception:
        return "", 1

def format_time(seconds):
    if seconds is None or seconds < 0:
        return "00:00"
    seconds = int(seconds)
    mins = seconds // 60
    secs = seconds % 60
    hours = mins // 60
    if hours > 0:
        mins = mins % 60
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

def extract_youtube_thumb(url):
    m = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})(?:[&?]|$)', url)
    if not m:
        return ""
    yt_id = m.group(1)
    target = CACHE_DIR / f"yt_{yt_id}.jpg"
    if target.exists() and target.stat().st_size > 0:
        return str(target)
    
    # Try fetching thumbnail
    for quality in ['hqdefault.jpg', 'mqdefault.jpg']:
        img_url = f"https://img.youtube.com/vi/{yt_id}/{quality}"
        try:
            req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = resp.read()
                if len(data) > 1000:
                    with open(target, 'wb') as f:
                        f.write(data)
                    return str(target)
        except Exception:
            continue
    return ""

def resolve_cover_art(art_url, web_url):
    if art_url:
        if art_url.startswith("file://"):
            local_path = urllib.parse.unquote(art_url[7:])
            if os.path.exists(local_path):
                return local_path
        elif art_url.startswith("http://") or art_url.startswith("https://"):
            h = hashlib.md5(art_url.encode('utf-8')).hexdigest()
            target = CACHE_DIR / f"art_{h}.jpg"
            if target.exists() and target.stat().st_size > 0:
                return str(target)
            try:
                req = urllib.request.Request(art_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    with open(target, 'wb') as f:
                        f.write(resp.read())
                return str(target)
            except Exception:
                pass

    if web_url and ("youtube.com" in web_url or "youtu.be" in web_url):
        yt_art = extract_youtube_thumb(web_url)
        if yt_art:
            return yt_art

    return DEFAULT_COVER if os.path.exists(DEFAULT_COVER) else ""

def get_media_data():
    raw, code = run_cmd([
        'playerctl', 'metadata', '--format',
        '{{status}}|||{{xesam:title}}|||{{xesam:artist}}|||{{xesam:album}}|||{{mpris:artUrl}}|||{{mpris:length}}|||{{xesam:url}}'
    ])
    
    if code != 0 or not raw:
        return {
            "status": "Stopped",
            "status_icon": "",
            "is_playing": False,
            "title": "Нет трека",
            "artist": "Воспроизведение остановлено",
            "album": "",
            "cover_art": DEFAULT_COVER if os.path.exists(DEFAULT_COVER) else "",
            "position": 0,
            "position_str": "00:00",
            "length": 0,
            "length_str": "00:00",
            "progress": 0
        }

    parts = raw.split("|||")
    status = parts[0] if len(parts) > 0 and parts[0] else "Paused"
    title = parts[1] if len(parts) > 1 and parts[1] else "Неизвестный трек"
    artist = parts[2] if len(parts) > 2 and parts[2] else "Неизвестный исполнитель"
    album = parts[3] if len(parts) > 3 else ""
    art_url = parts[4] if len(parts) > 4 else ""
    raw_length = parts[5] if len(parts) > 5 else ""
    web_url = parts[6] if len(parts) > 6 else ""

    # Length in seconds
    length_sec = 0.0
    if raw_length:
        try:
            # mpris:length is in microseconds
            length_sec = float(raw_length) / 1000000.0
        except Exception:
            pass

    # Position in seconds
    pos_raw, _ = run_cmd(['playerctl', 'position'])
    pos_sec = 0.0
    if pos_raw:
        try:
            pos_sec = float(pos_raw)
        except Exception:
            pass

    # Progress %
    progress = 0
    if length_sec > 0:
        progress = max(0, min(100, int((pos_sec / length_sec) * 100)))
    elif pos_sec > 0:
        # If length is unknown, keep progress at 0 or estimated
        progress = 0

    cover_art = resolve_cover_art(art_url, web_url)
    is_playing = (status.lower() == "playing")

    # Shorten long titles gracefully if needed
    clean_title = title
    if len(clean_title) > 38:
        clean_title = clean_title[:36] + "…"

    clean_artist = artist
    if len(clean_artist) > 32:
        clean_artist = clean_artist[:30] + "…"

    return {
        "status": status,
        "status_icon": "" if is_playing else "",
        "is_playing": is_playing,
        "title": clean_title,
        "full_title": title,
        "artist": clean_artist,
        "album": album,
        "cover_art": cover_art,
        "position": round(pos_sec, 1),
        "position_str": format_time(pos_sec),
        "length": round(length_sec, 1),
        "length_str": format_time(length_sec) if length_sec > 0 else "--:--",
        "progress": progress
    }

def handle_seek_pct(pct_str):
    try:
        pct = float(pct_str)
        # Get total length
        raw, code = run_cmd(['playerctl', 'metadata', '--format', '{{mpris:length}}'])
        if code == 0 and raw:
            total_sec = float(raw) / 1000000.0
            target_sec = (pct / 100.0) * total_sec
            run_cmd(['playerctl', 'position', str(round(target_sec, 1))])
            return
        # Fallback: if length unknown, ignore or treat as raw
    except Exception:
        pass

def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == '--toggle':
            run_cmd(['playerctl', 'play-pause'])
        elif cmd == '--next':
            run_cmd(['playerctl', 'next'])
        elif cmd == '--prev':
            run_cmd(['playerctl', 'previous'])
        elif cmd == '--forward':
            sec = sys.argv[2] if len(sys.argv) > 2 else "10"
            run_cmd(['playerctl', 'position', f"{sec}+"])
        elif cmd == '--rewind':
            sec = sys.argv[2] if len(sys.argv) > 2 else "10"
            run_cmd(['playerctl', 'position', f"{sec}-"])
        elif cmd == '--seek-pct' and len(sys.argv) > 2:
            handle_seek_pct(sys.argv[2])
        elif cmd == '--seek' and len(sys.argv) > 2:
            run_cmd(['playerctl', 'position', sys.argv[2]])
        elif cmd == '--status':
            print(json.dumps(get_media_data(), ensure_ascii=False))
        return

    print(json.dumps(get_media_data(), ensure_ascii=False))

if __name__ == '__main__':
    main()
