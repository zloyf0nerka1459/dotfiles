#!/usr/bin/env bash
# ==============================================================================
# Hyprdots-style Visual Theme & Wallpaper Selector (Rofi Card Grid)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
THEMES_DIR="$HOME/.config/themes"
WALLPAPERS_DIR="$HOME/Pictures/Wallpapers"
CACHE_DIR="$HOME/.cache/theme-thumbs"
ROFI_THEME="$HOME/.config/rofi/theme-select.rasi"

mkdir -p "$CACHE_DIR"

# Generate menu list via python (high performance, auto-caching thumbnails)
MAP_FILE="/tmp/theme_selector_map_$$.json"

python3 -c "
import os, glob, hashlib, json, sys
from PIL import Image, ImageOps, ImageDraw

themes_dir = os.path.expanduser('$THEMES_DIR')
wallpapers_dir = os.path.expanduser('$WALLPAPERS_DIR')
cache_dir = os.path.expanduser('$CACHE_DIR')
map_file = '$MAP_FILE'

def make_thumb(src, dst):
    try:
        with Image.open(src) as img:
            img = img.convert('RGBA')
            target_w, target_h = 320, 180
            img = ImageOps.fit(img, (target_w, target_h), Image.Resampling.LANCZOS)
            mask = Image.new('L', (target_w, target_h), 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0, target_w, target_h), radius=16, fill=255)
            output = Image.new('RGBA', (target_w, target_h), (0, 0, 0, 0))
            output.paste(img, (0, 0), mask)
            output.save(dst, 'PNG')
            return True
    except Exception as e:
        return False

items = []
seen_walls = set()

# 1. Load curated themes with theme.conf
for conf in sorted(glob.glob(os.path.join(themes_dir, '*/theme.conf'))):
    tdir = os.path.dirname(conf)
    name = os.path.basename(tdir)
    wall = ''
    try:
        with open(conf, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('name='):
                    name = line.split('=', 1)[1].strip('\"\' ')
                elif line.startswith('wallpaper='):
                    wall = line.split('=', 1)[1].strip('\"\' ')
    except Exception:
        pass
    
    if not wall:
        # Check if wall.* exists in theme dir
        for ext in ['.jpg', '.jpeg', '.png', '.webp']:
            w = os.path.join(tdir, 'wall' + ext)
            if os.path.exists(w):
                wall = w
                break
    elif not os.path.isabs(wall):
        wall = os.path.join(tdir, wall)
        
    thumb = os.path.join(tdir, 'thumb.png')
    if os.path.exists(wall):
        real_wall = os.path.realpath(wall)
        seen_walls.add(real_wall)
        if not os.path.exists(thumb):
            make_thumb(wall, thumb)
        items.append({
            'title': name,
            'icon': thumb if os.path.exists(thumb) else wall,
            'target': tdir
        })

# 2. Load any extra standalone wallpapers from ~/Pictures/Wallpapers
if os.path.isdir(wallpapers_dir):
    for w in sorted(glob.glob(os.path.join(wallpapers_dir, '*'))):
        if w.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            real_w = os.path.realpath(w)
            if real_w in seen_walls:
                continue
            
            seen_walls.add(real_w)
            h = hashlib.md5(real_w.encode('utf-8')).hexdigest()[:12]
            thumb = os.path.join(cache_dir, f'thumb_{h}.png')
            if not os.path.exists(thumb):
                make_thumb(real_w, thumb)
                
            base = os.path.splitext(os.path.basename(real_w))[0]
            clean_name = base.replace('_', ' ').replace('-', ' ').title()
            if len(clean_name) > 24:
                clean_name = clean_name[:22] + '..'
                
            items.append({
                'title': f'🖼️  {clean_name}',
                'icon': thumb if os.path.exists(thumb) else real_w,
                'target': real_w
            })

# Save mapping
mapping = {item['title']: item['target'] for item in items}
with open(map_file, 'w', encoding='utf-8') as f:
    json.dump(mapping, f, ensure_ascii=False)

# Output rofi dmenu formatted lines: title\0icon\x1fthumb_path
for item in items:
    sys.stdout.write(f\"{item['title']}\\0icon\\x1f{item['icon']}\\n\")
" > "/tmp/theme_selector_rofi_$$.txt"

trap 'rm -f "$MAP_FILE" "/tmp/theme_selector_rofi_$$.txt"' EXIT

# Launch Rofi
SELECTED_TITLE=$(cat "/tmp/theme_selector_rofi_$$.txt" | rofi -dmenu -i -theme "$ROFI_THEME" -show-icons -p "Тема:")

if [ -n "$SELECTED_TITLE" ]; then
    TARGET_PATH=$(python3 -c "
import json
try:
    with open('$MAP_FILE') as f:
        m = json.load(f)
    print(m.get('''$SELECTED_TITLE''', ''))
except Exception:
    pass
")
    
    if [ -n "$TARGET_PATH" ]; then
        "$SCRIPT_DIR/theme-apply.sh" "$TARGET_PATH"
    fi
fi
