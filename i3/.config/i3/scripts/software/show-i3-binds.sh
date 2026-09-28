#!/usr/bin/env bash
# Show i3 keybindings in a searchable rofi window
set -euo pipefail
CONFIG="$HOME/.config/i3/config"
grep -E '^[[:space:]]*bindsym' "$CONFIG" \
  | sed -E 's/^[[:space:]]*bindsym[[:space:]]+(--[a-z-]+[[:space:]]+)*//; s/[[:space:]]+exec[[:space:]]+(--no-startup-id[[:space:]]+)?/   =>   /; s/\$mod/Mod/g' \
  | rofi -dmenu -i -p "i3 keys" >/dev/null || true
