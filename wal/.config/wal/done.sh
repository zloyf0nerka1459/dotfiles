#!/usr/bin/env bash
# Update EWW with new wallpaper colors
"$HOME/.config/eww/launch.sh" >/dev/null 2>&1 &

# Update Rofi blurred wallpaper banner
"$HOME/.config/rofi/update-blur.sh" >/dev/null 2>&1 &
