#!/usr/bin/env python3
import os
import json
import time
import socket
import platform
from pathlib import Path

GREETINGS_FILE = os.path.expanduser('~/.config/eww/greetings.json')

def get_uptime_str():
    try:
        with open('/proc/uptime', 'r') as f:
            total_seconds = float(f.readline().split()[0])
        days = int(total_seconds // 86400)
        hours = int((total_seconds % 86400) // 3600)
        mins = int((total_seconds % 3600) // 60)
        
        if days > 0:
            return f"{days}д {hours}ч"
        if hours > 0:
            return f"{hours}ч {mins}м"
        return f"{mins} мин"
    except Exception:
        return "онлайн"

def get_profile_data():
    current_user = os.environ.get("USER", "fonera")
    
    cfg = {}
    if os.path.exists(GREETINGS_FILE):
        try:
            with open(GREETINGS_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
        except Exception:
            pass

    display_name = cfg.get("user_name") or current_user
    title = f"Привет, {display_name}!"
    custom_msg = cfg.get("custom_message", "").strip()

    # Determine time of day
    hour = time.localtime().tm_hour
    if 5 <= hour < 12:
        period = "morning"
    elif 12 <= hour < 18:
        period = "day"
    elif 18 <= hour < 23:
        period = "evening"
    else:
        period = "night"

    if custom_msg:
        greeting = custom_msg.replace("{user}", display_name)
    else:
        messages = cfg.get("messages", {}).get(period, ["Всё работает как часы!"])
        # Filter out anything that repeats title
        valid_msgs = [m.replace("{user}", display_name) for m in messages if m.replace("{user}", display_name) != title]
        if not valid_msgs:
            valid_msgs = ["Всё работает как часы!"]
        idx = (int(time.time() // 120)) % len(valid_msgs)
        greeting = valid_msgs[idx]

    # Avatar path check
    avatar_path = ""
    for candidate in [
        os.path.expanduser("~/.face"),
        os.path.expanduser("~/.config/system-control-center/avatar.png"),
        os.path.expanduser("~/.face.icon")
    ]:
        if os.path.exists(candidate) and os.path.getsize(candidate) > 0:
            avatar_path = candidate
            break

    # Short kernel
    k_rel = platform.release()
    if '-' in k_rel:
        k_short = k_rel.split('-')[0]
    else:
        k_short = k_rel[:6]

    return {
        "user": display_name,
        "title": title,
        "greeting": greeting,
        "avatar_path": avatar_path,
        "uptime": get_uptime_str(),
        "os": "Arch Linux",
        "wm": "i3wm",
        "kernel": k_short,
        "host": socket.gethostname()
    }

if __name__ == "__main__":
    print(json.dumps(get_profile_data(), ensure_ascii=False))
