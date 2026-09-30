#!/usr/bin/env python3
import subprocess
import json
import sys
import os
import re
import time
import base64
import urllib.request
import urllib.parse
import hashlib
from pathlib import Path

CACHE_DIR = Path('/tmp/eww_media_cache')
DEFAULT_COVER = os.path.expanduser('~/.config/eww/assets/default_cover.png')
SEEK_LOCK_FILE = CACHE_DIR / 'seek_lock.json'
LENGTH_CACHE_FILE = CACHE_DIR / 'last_length.txt'

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
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = resp.read()
                if len(data) > 1000:
                    with open(target, 'wb') as f:
                        f.write(data)
                    return str(target)
        except Exception:
            continue
    return ""

def fetch_online_cover_worker(artist, title, target_path):
    lock_file = target_path.with_suffix('.lock')
    try:
        query = f"{artist} {title}".strip()
        
        # 1. Deezer API (Fastest and best matching)
        try:
            url = f"https://api.deezer.com/search?q={urllib.parse.quote(query)}&limit=1"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                if data.get('data'):
                    album_obj = data['data'][0].get('album', {})
                    img_url = album_obj.get('cover_big') or album_obj.get('cover_medium')
                    if img_url:
                        req_img = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req_img, timeout=3) as img_resp:
                            img_data = img_resp.read()
                            if len(img_data) > 1000:
                                target_path.write_bytes(img_data)
                                return
        except Exception:
            pass

        # 2. iTunes API fallback
        try:
            url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&media=music&entity=song&limit=1"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                if data.get('resultCount', 0) > 0:
                    raw_art = data['results'][0].get('artworkUrl100', '')
                    if raw_art:
                        art_high = raw_art.replace('100x100bb', '512x512bb')
                        req_img = urllib.request.Request(art_high, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req_img, timeout=3) as img_resp:
                            img_data = img_resp.read()
                            if len(img_data) > 1000:
                                target_path.write_bytes(img_data)
                                return
        except Exception:
            pass
    finally:
        try:
            if lock_file.exists():
                lock_file.unlink()
        except Exception:
            pass

def resolve_cover_art(art_url, web_url, artist="", title=""):
    if art_url:
        if art_url.startswith("data:image/"):
            try:
                header, b64_data = art_url.split(",", 1)
                ext = "png" if "png" in header else "jpg"
                img_bytes = base64.b64decode(b64_data)
                h = hashlib.md5(img_bytes).hexdigest()
                target = CACHE_DIR / f"art_{h}.{ext}"
                if not target.exists() or target.stat().st_size == 0:
                    with open(target, "wb") as f:
                        f.write(img_bytes)
                return str(target)
            except Exception:
                pass
        elif art_url.startswith("file://"):
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
                with urllib.request.urlopen(req, timeout=2) as resp:
                    with open(target, 'wb') as f:
                        f.write(resp.read())
                return str(target)
            except Exception:
                pass
        elif len(art_url) > 100 and not art_url.startswith("/"):
            # Raw base64 fallback
            try:
                img_bytes = base64.b64decode(art_url)
                if len(img_bytes) > 100:
                    ext = "png" if img_bytes.startswith(b'\x89PNG') else "jpg"
                    h = hashlib.md5(img_bytes).hexdigest()
                    target = CACHE_DIR / f"art_{h}.{ext}"
                    if not target.exists() or target.stat().st_size == 0:
                        with open(target, "wb") as f:
                            f.write(img_bytes)
                    return str(target)
            except Exception:
                pass

    if web_url and ("youtube.com" in web_url or "youtu.be" in web_url):
        yt_art = extract_youtube_thumb(web_url)
        if yt_art:
            return yt_art

    # Online cover lookup fallback when player provides no artUrl
    if artist and title and title not in ("Нет трека", "Неизвестный трек"):
        clean_q = f"{artist.lower().strip()}_{title.lower().strip()}"
        h = hashlib.md5(clean_q.encode('utf-8')).hexdigest()
        online_target = CACHE_DIR / f"online_{h}.jpg"
        if online_target.exists() and online_target.stat().st_size > 0:
            return str(online_target)
        else:
            lock_file = online_target.with_suffix('.lock')
            if not lock_file.exists():
                try:
                    lock_file.touch()
                    subprocess.Popen(
                        [sys.executable, os.path.abspath(__file__), '--fetch-cover', artist, title, str(online_target)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except Exception:
                    pass

    return DEFAULT_COVER if os.path.exists(DEFAULT_COVER) else ""

def get_media_data():
    raw, code = run_cmd([
        'playerctl', 'metadata', '--format',
        '{{status}}|||{{xesam:title}}|||{{xesam:artist}}|||{{xesam:album}}|||{{mpris:artUrl}}|||{{mpris:length}}|||{{xesam:url}}|||{{playerName}}'
    ])
    
    if code != 0 or not raw:
        return {
            "status": "Stopped",
            "status_icon": "󰐊",
            "is_playing": False,
            "title": "Нет трека",
            "full_title": "Воспроизведение остановлено",
            "artist": "Запустите плеер",
            "album": "",
            "player_name": "",
            "player_icon": "󰝚",
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
    player_raw = parts[7] if len(parts) > 7 else ""

    player_name = ""
    player_icon = "󰝚"
    p_lower = player_raw.lower()
    if "forkgram" in p_lower or "telegram" in p_lower:
        player_name = "Telegram"
        player_icon = "󰀰"
    elif "firefox" in p_lower or "zen" in p_lower:
        player_name = "Zen Browser"
        player_icon = "󰈹"
    elif "spotify" in p_lower:
        player_name = "Spotify"
        player_icon = "󰓇"
    elif "mpv" in p_lower:
        player_name = "MPV"
        player_icon = "󰕼"
    elif "chromium" in p_lower or "chrome" in p_lower:
        player_name = "Chrome"
        player_icon = "󰊯"
    elif player_raw:
        player_name = player_raw.split('.')[0].capitalize()

    # Length in seconds
    length_sec = 0.0
    if raw_length:
        try:
            # mpris:length is in microseconds
            length_sec = float(raw_length) / 1000000.0
            LENGTH_CACHE_FILE.write_text(str(length_sec))
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

    # Check if user recently dragged timeline (seek debounce / anti-rubberbanding)
    if SEEK_LOCK_FILE.exists() and length_sec > 0:
        try:
            lock_data = json.loads(SEEK_LOCK_FILE.read_text())
            time_diff = time.time() - float(lock_data.get("time", 0))
            if time_diff < 1.5:
                seek_pct = float(lock_data.get("target_pct", progress))
                progress = max(0, min(100, int(seek_pct)))
                pos_sec = (seek_pct / 100.0) * length_sec
        except Exception:
            pass

    cover_art = resolve_cover_art(art_url, web_url, artist, title)
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
        "status_icon": "󰏤" if is_playing else "󰐊",
        "is_playing": is_playing,
        "title": clean_title,
        "full_title": title,
        "artist": clean_artist,
        "album": album,
        "player_name": player_name,
        "player_icon": player_icon,
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
        pct = max(0.0, min(100.0, pct))
        
        # 1. Immediately record seek lock with timestamp
        SEEK_LOCK_FILE.write_text(json.dumps({"target_pct": pct, "time": time.time()}))
        
        # 2. Get total length (from cache or playerctl)
        total_sec = 0.0
        if LENGTH_CACHE_FILE.exists():
            try:
                total_sec = float(LENGTH_CACHE_FILE.read_text().strip())
            except Exception:
                pass
                
        if total_sec <= 0:
            raw, code = run_cmd(['playerctl', 'metadata', '--format', '{{mpris:length}}'])
            if code == 0 and raw:
                try:
                    total_sec = float(raw) / 1000000.0
                    LENGTH_CACHE_FILE.write_text(str(total_sec))
                except Exception:
                    pass
                    
        if total_sec > 0:
            target_sec = (pct / 100.0) * total_sec
            run_cmd(['playerctl', 'position', str(round(target_sec, 1))])
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
        elif cmd == '--fetch-cover' and len(sys.argv) > 4:
            fetch_online_cover_worker(sys.argv[2], sys.argv[3], Path(sys.argv[4]))
        elif cmd == '--status':
            print(json.dumps(get_media_data(), ensure_ascii=False))
        return

    print(json.dumps(get_media_data(), ensure_ascii=False))

if __name__ == '__main__':
    main()
