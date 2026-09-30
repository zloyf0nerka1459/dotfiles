#!/usr/bin/env bash
# System Control Center launcher with single-instance enforcement & auto-focus

# 1. Check if window with instance or class 'system-control-center' already exists in i3
if i3-msg '[instance="(?i)system-control-center"] focus' 2>/dev/null | grep -q '"success":true'; then
    exit 0
fi

if i3-msg '[class="(?i)system-control-center"] focus' 2>/dev/null | grep -q '"success":true'; then
    exit 0
fi

# 2. Check by exact or partial window title
if i3-msg '[title="(?i)Параметры системы"] focus' 2>/dev/null | grep -q '"success":true'; then
    exit 0
fi

# 3. Fallback via xdotool if i3-msg criteria missed for any reason
WINDOW_ID=$(xdotool search --name "Параметры системы" 2>/dev/null | head -n 1)
if [ -n "$WINDOW_ID" ]; then
    xdotool windowactivate "$WINDOW_ID" 2>/dev/null && exit 0
fi

# 4. If not running, launch a new instance
exec python3 "$HOME/.config/system-control-center/system_control_center.py" "$@"
