#!/usr/bin/env bash
# ==============================================================================
# XDG Autostart Runner for i3wm
# Launches enabled applications from ~/.config/autostart/
# ==============================================================================
AUTOSTART_DIR="$HOME/.config/autostart"
[ -d "$AUTOSTART_DIR" ] || exit 0

python3 - << 'EOF'
import os
import shlex
import subprocess
import configparser
from pathlib import Path

autostart_dir = Path.home() / ".config" / "autostart"
if not autostart_dir.is_dir():
    exit(0)

for p in sorted(autostart_dir.glob("*.desktop")):
    try:
        cp = configparser.ConfigParser(interpolation=None)
        cp.read(p, encoding="utf-8")
        if "Desktop Entry" in cp:
            sec = cp["Desktop Entry"]
            hidden = sec.getboolean("Hidden", fallback=False)
            gnome_enabled = sec.getboolean("X-GNOME-Autostart-enabled", fallback=True)
            if not hidden and gnome_enabled:
                cmd = sec.get("Exec", "")
                if cmd:
                    # Strip standard desktop field codes (%f, %F, %u, %U, %i, %c, %k)
                    clean_args = [arg for arg in cmd.split() if not (arg.startswith("%") and len(arg) == 2)]
                    if clean_args:
                        subprocess.Popen(clean_args, start_new_session=True)
    except Exception:
        pass
EOF
