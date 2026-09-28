#!/usr/bin/env bash
# ==============================================================================
# XDG Autostart Runner for i3wm
# Launches enabled applications from ~/.config/autostart/
# ==============================================================================
AUTOSTART_DIR="$HOME/.config/autostart"
[ -d "$AUTOSTART_DIR" ] || exit 0

# Allow desktop environment (X11, Tray, Dunst, Picom, Eww) to settle
sleep 2

# Primary method: dex (official XDG autostart runner)
if command -v dex >/dev/null 2>&1; then
    exec dex -a -s "$AUTOSTART_DIR"
fi

# Fallback method in Python if dex is ever missing
python3 - << 'EOF'
import sys
import subprocess
import configparser
from pathlib import Path

autostart_dir = Path.home() / ".config" / "autostart"
if not autostart_dir.is_dir():
    sys.exit(0)

for p in sorted(autostart_dir.glob("*.desktop")):
    try:
        cp = configparser.ConfigParser(interpolation=None)
        cp.optionxform = str
        cp.read(p, encoding="utf-8")
        sec_name = "Desktop Entry"
        if sec_name not in cp:
            for s in cp.sections():
                if s.lower() == "desktop entry":
                    sec_name = s
                    break
        if sec_name in cp:
            sec = cp[sec_name]
            hidden = sec.getboolean("Hidden", fallback=False) or sec.getboolean("hidden", fallback=False)
            gnome_enabled = sec.getboolean("X-GNOME-Autostart-enabled", fallback=True) and sec.getboolean("x-gnome-autostart-enabled", fallback=True)
            if not hidden and gnome_enabled:
                cmd = sec.get("Exec") or sec.get("exec", "")
                if cmd:
                    # Strip standard desktop field codes (%f, %F, %u, %U, %i, %c, %k)
                    clean_args = [arg for arg in cmd.split() if not (arg.startswith("%") and len(arg) == 2)]
                    if clean_args:
                        subprocess.Popen(
                            clean_args,
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True
                        )
    except Exception:
        pass
EOF
