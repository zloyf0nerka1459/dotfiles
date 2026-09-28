#!/usr/bin/env bash
# Toggle floating btop window

if i3-msg -t get_tree | grep -q '"class":"btop-floating"'; then
    i3-msg '[class="(?i)btop-floating"] kill' >/dev/null 2>&1
else
    kitty --class btop-floating -T "btop" -e btop >/dev/null 2>&1 &
fi
