#!/usr/bin/env bash
# ==============================================================================
# Universal Multi-Monitor & GPU Display Manager for i3
# ==============================================================================
set -euo pipefail

# 1. Detect connected outputs
CONNECTED_MONITORS=($(xrandr --query | awk '/ connected/{print $1}'))
MON_COUNT=${#CONNECTED_MONITORS[@]}

HAS_NVIDIA=false
if command -v nvidia-settings >/dev/null 2>&1 && (lspci 2>/dev/null | grep -qiE 'vga.*nvidia|3d.*nvidia'); then
    HAS_NVIDIA=true
fi

# 2. Check for autorandr profile first
if command -v autorandr >/dev/null 2>&1 && autorandr --load default >/dev/null 2>&1; then
    echo "Loaded autorandr profile."
elif [[ " ${CONNECTED_MONITORS[*]} " =~ " DP-0 " && " ${CONNECTED_MONITORS[*]} " =~ " DVI-D-0 " && " ${CONNECTED_MONITORS[*]} " =~ " HDMI-0 " ]]; then
    # Custom Triple-Monitor workstation layout (144Hz primary DP-0 + DVI-D-0 + HDMI-0)
    xrandr \
      --output DP-0 --primary --mode 1920x1080 --rate 144.00 --pos 1360x0 \
      --output DVI-D-0 --mode 1360x768 --pos 0x312 \
      --output HDMI-0 --mode 1920x1080 --rate 74.97 --pos 3280x0 \
      --output DP-1 --off || true

    sleep 1

    if [ "$HAS_NVIDIA" = "true" ]; then
        nvidia-settings --assign CurrentMetaMode="DP-0: 1920x1080_144 +1360+0 {ForceCompositionPipeline=Off, ForceFullCompositionPipeline=Off}, DVI-D-0: 1360x768_60 +0+312 {ForceCompositionPipeline=Off, ForceFullCompositionPipeline=Off}, HDMI-0: 1920x1080_75 +3280+0 {ForceCompositionPipeline=Off, ForceFullCompositionPipeline=Off}" >/dev/null 2>&1 || true
        nvidia-settings --load-config-only >/dev/null 2>&1 || true
        nvidia-settings --assign 0/XVideoSyncToDisplayID=DP-0 --assign 0/SyncToVBlank=1 >/dev/null 2>&1 || true
    fi
elif [ "$MON_COUNT" -eq 1 ]; then
    # Single monitor or laptop screen (eDP-1, HDMI-1, DP-1, etc.)
    PRIMARY="${CONNECTED_MONITORS[0]}"
    xrandr --output "$PRIMARY" --auto --primary || true
    if [ "$HAS_NVIDIA" = "true" ]; then
        nvidia-settings --load-config-only >/dev/null 2>&1 || true
    fi
else
    # Generic multi-monitor fallback (arrange side-by-side)
    POS_X=0
    for mon in "${CONNECTED_MONITORS[@]}"; do
        xrandr --output "$mon" --auto --pos "${POS_X}x0" || true
        W=$(xrandr --query | grep -A1 "^$mon connected" | tail -n1 | awk '{print $1}' | cut -dx -f1 || echo 1920)
        POS_X=$((POS_X + W))
    done
    if [ "$HAS_NVIDIA" = "true" ]; then
        nvidia-settings --load-config-only >/dev/null 2>&1 || true
    fi
fi