#!/usr/bin/env bash

set -e

# Stop polybar if running
killall -q polybar 2>/dev/null || true

# Restart flag handling
if [ "${1:-}" = "--restart" ] || [ "${1:-}" = "-r" ]; then
    killall -q eww 2>/dev/null || true
    while pgrep -u "$UID" -x eww >/dev/null; do sleep 0.2; done
fi

# Ensure Pywal colors file exists and is symlinked
if [ -f "$HOME/.cache/wal/colors-eww.scss" ]; then
    ln -sf "$HOME/.cache/wal/colors-eww.scss" "$HOME/.config/eww/colors.scss"
elif [ -f "$HOME/.cache/wal/colors.scss" ]; then
    ln -sf "$HOME/.cache/wal/colors.scss" "$HOME/.config/eww/colors.scss"
fi

# Start daemon if not running
if ! pgrep -u "$UID" -x eww >/dev/null; then
    eww daemon &
    sleep 0.5
fi

# Reload CSS and configurations to pick up any changes or new pywal colors
eww reload 2>/dev/null || true

# Open top and bottom bars if they are not already open
active_windows=$(eww active-windows 2>/dev/null || true)

if ! echo "$active_windows" | grep -q "bar_top"; then
    eww open bar_top
fi

if ! echo "$active_windows" | grep -q "bar_bottom"; then
    eww open bar_bottom
fi
