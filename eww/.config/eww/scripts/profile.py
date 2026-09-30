#!/usr/bin/env python3
import os
import json
import time
import pwd
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
    
    # Load custom greetings config
    cfg = {}
    if os.path.exists(GREETINGS_FILE):
        try:
            with open(GREETINGS_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
        except Exception:
            pass

    display_name = cfg.get("user_name") or current_user
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
        messages = cfg.get("messages", {}).get(period, [f"Привет, {display_name}!"])
        if not messages:
            messages = [f"Привет, {display_name}!"]
        # Stable pick per minute/hour or cyclic
        idx = (int(time.time() // 120)) % len(messages)
        greeting = messages[idx].replace("{user}", display_name)

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

    return {
        "user": display_name,
        "title": f"Привет, {display_name}!",
        "greeting": greeting,
        "avatar_path": avatar_path,
        "uptime": get_uptime_str(),
        "os": "Arch Linux",
        "wm": "i3wm"
    }

if __name__ == "__main__":
    print(json.dumps(get_profile_data(), ensure_ascii=False))
