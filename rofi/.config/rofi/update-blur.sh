#!/usr/bin/env bash
# Generates a blurred and optimized wallpaper banner for Rofi inputbar

WALLPAPER="${1:-}"

if [ -z "$WALLPAPER" ] || [ ! -f "$WALLPAPER" ]; then
    if [ -f "$HOME/.cache/wal/wal" ]; then
        WALLPAPER=$(cat "$HOME/.cache/wal/wal" 2>/dev/null)
    fi
fi

if [ -z "$WALLPAPER" ] || [ ! -f "$WALLPAPER" ]; then
    if [ -f "$HOME/.fehbg" ]; then
        WALLPAPER=$(grep -o "'.*'" "$HOME/.fehbg" | tr -d "'" | head -n 1)
    fi
fi

if [ -z "$WALLPAPER" ] || [ ! -f "$WALLPAPER" ]; then
    exit 0
fi

mkdir -p "$HOME/.cache/rofi"
TARGET="$HOME/.cache/rofi/current-wallpaper-blur.png"

# Use python Pillow for high speed (<0.15s), fallback to magick
python3 -c "
import sys, os
from PIL import Image, ImageFilter

src = sys.argv[1]
dst = sys.argv[2]
try:
    with Image.open(src) as im:
        w = 720
        h = max(int(im.height * (w / im.width)), 120)
        im = im.resize((w, h), Image.Resampling.BILINEAR)
        blurred = im.filter(ImageFilter.GaussianBlur(radius=8))
        blurred.save(dst, 'PNG')
except Exception as e:
    sys.exit(1)
" "$WALLPAPER" "$TARGET" 2>/dev/null || magick "$WALLPAPER" -resize 720x -blur 0x8 "$TARGET" 2>/dev/null
