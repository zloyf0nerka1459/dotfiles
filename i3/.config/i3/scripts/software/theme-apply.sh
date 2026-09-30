#!/usr/bin/env bash
# ==============================================================================
# Hyprdots-style Theme Applier for i3 + Picom + Pywal + EWW + Dunst
# ==============================================================================
set -euo pipefail

TARGET="${1:-}"

if [ -z "$TARGET" ]; then
    echo "Usage: $0 <theme_dir_or_wallpaper_path>"
    exit 1
fi

THEME_NAME=""
WALLPAPER=""
THUMB=""

if [ -d "$TARGET" ] && [ -f "$TARGET/theme.conf" ]; then
    # Load from theme directory
    # shellcheck disable=SC1090
    source "$TARGET/theme.conf"
    THEME_NAME="${name:-$(basename "$TARGET")}"
    WALLPAPER="${wallpaper:-}"
    
    # Resolve relative wallpaper path
    if [[ "$WALLPAPER" != /* ]]; then
        WALLPAPER="$TARGET/$WALLPAPER"
    fi
    
    if [ -f "$TARGET/thumb.png" ]; then
        THUMB="$TARGET/thumb.png"
    fi
elif [ -f "$TARGET" ]; then
    # Direct wallpaper file
    WALLPAPER="$TARGET"
    BASENAME="$(basename "$TARGET")"
    THEME_NAME="🖼️  ${BASENAME%.*}"
else
    echo "Error: Target not found: $TARGET"
    exit 1
fi

if [ ! -f "$WALLPAPER" ]; then
    notify-send -u critical "Ошибка темы" "Файл обоев не найден: $WALLPAPER"
    exit 1
fi

# Ensure thumbnail exists for notification
if [ -z "$THUMB" ] || [ ! -f "$THUMB" ]; then
    mkdir -p "$HOME/.cache/theme-thumbs"
    HASH=$(md5sum "$WALLPAPER" | cut -d' ' -f1)
    THUMB="$HOME/.cache/theme-thumbs/${HASH}.png"
    
    if [ ! -f "$THUMB" ]; then
        python3 -c "
import sys
from PIL import Image, ImageOps, ImageDraw
try:
    with Image.open('$WALLPAPER') as img:
        img = img.convert('RGBA')
        target_w, target_h = 320, 180
        img = ImageOps.fit(img, (target_w, target_h), Image.Resampling.LANCZOS)
        mask = Image.new('L', (target_w, target_h), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, target_w, target_h), radius=16, fill=255)
        output = Image.new('RGBA', (target_w, target_h), (0, 0, 0, 0))
        output.paste(img, (0, 0), mask)
        output.save('$THUMB', 'PNG')
except Exception:
    pass
" 2>/dev/null || true
    fi
fi

echo "Applying theme: $THEME_NAME ($WALLPAPER)"

# 1. Apply wallpaper across all monitors
feh --bg-fill "$WALLPAPER"

# Save persistent fehbg
cat << EOF > "$HOME/.fehbg"
#!/bin/sh
feh --no-fehbg --bg-fill '$WALLPAPER'
EOF
chmod +x "$HOME/.fehbg"

# 2. Generate and apply color palette via wpg / wal
if command -v wpg >/dev/null 2>&1; then
    wpg -ns "$WALLPAPER" >/dev/null 2>&1 || wal -i "$WALLPAPER" -n -q
else
    wal -i "$WALLPAPER" -n -q
fi

# 3. Merge Xresources for live X11 color propagation
if [ -f "$HOME/.cache/wal/colors.Xresources" ]; then
    xrdb -merge "$HOME/.cache/wal/colors.Xresources"
fi
if [ -f "$HOME/.Xresources" ]; then
    xrdb -merge "$HOME/.Xresources"
fi
if command -v xsetroot >/dev/null 2>&1; then
    xsetroot -cursor_name left_ptr 2>/dev/null || true
fi

# 4. Seamlessly reload i3 (updates border and accent colors without screen flicker)
if command -v i3-msg >/dev/null 2>&1; then
    i3-msg reload >/dev/null 2>&1 || true
fi

# 5. Live update all open Kitty terminal windows
if command -v kitty >/dev/null 2>&1; then
    if [ -f "$HOME/.cache/wal/colors-kitty.conf" ]; then
        kitty @ set-colors --all "$HOME/.cache/wal/colors-kitty.conf" 2>/dev/null || true
    fi
    killall -SIGUSR1 kitty 2>/dev/null || true
fi

# 6. Apply theme-specific EWW bar styles and reload widgets
THEME_DIR=""
if [ -d "$TARGET" ]; then
    THEME_DIR="$TARGET"
elif [ -f "$TARGET" ]; then
    THEME_DIR="$(dirname "$TARGET")"
fi

if [ -n "$THEME_DIR" ] && [ -f "$THEME_DIR/theme-eww.scss" ]; then
    cp -f "$THEME_DIR/theme-eww.scss" "$HOME/.config/eww/theme-override.scss"
elif [ -n "$THEME_DIR" ] && [ -f "$THEME_DIR/eww.scss" ]; then
    cp -f "$THEME_DIR/eww.scss" "$HOME/.config/eww/theme-override.scss"
else
    echo "/* Default theme - no custom EWW overrides */" > "$HOME/.config/eww/theme-override.scss"
fi

if [ -x "$HOME/.config/eww/launch.sh" ]; then
    "$HOME/.config/eww/launch.sh" >/dev/null 2>&1 &
elif command -v eww >/dev/null 2>&1; then
    eww reload >/dev/null 2>&1 || true
fi

# 7. Update GTK theme (FlatColor) with new theme colors and reload xsettingsd
if [ -x "$HOME/.config/i3/scripts/software/update-gtk-theme.py" ]; then
    "$HOME/.config/i3/scripts/software/update-gtk-theme.py" >/dev/null 2>&1 || true
fi

if command -v gsettings >/dev/null 2>&1; then
    gsettings set org.gnome.desktop.interface gtk-theme "FlatColor" 2>/dev/null || true
    gsettings set org.gnome.desktop.interface color-scheme "prefer-dark" 2>/dev/null || true
fi

if command -v xsettingsd >/dev/null 2>&1; then
    killall xsettingsd 2>/dev/null || true
    sleep 0.1
    xsettingsd >/dev/null 2>&1 &
fi

# 8. Reload Dunst notifications with new theme colors
DUNST_CONF="$HOME/.cache/wal/dunstrc"
if [ ! -f "$DUNST_CONF" ]; then
    DUNST_CONF="$HOME/.cache/wal/colors-dunst.dunstrc"
fi

# Ensure conflicting daemons cannot hijack DBus notifications
killall -9 deadd-notification-center 2>/dev/null || true
pkill -f deadd-notification-center 2>/dev/null || true
killall -9 mako swaync 2>/dev/null || true

if command -v dunst >/dev/null 2>&1; then
    killall -9 dunst 2>/dev/null || true
    sleep 0.15
    if [ -f "$DUNST_CONF" ]; then
        mkdir -p "$HOME/.config/dunst"
        cp -f "$DUNST_CONF" "$HOME/.config/dunst/dunstrc" 2>/dev/null || true
        dunst -config "$DUNST_CONF" >/dev/null 2>&1 &
    else
        dunst >/dev/null 2>&1 &
    fi
fi

# 9. Update blurred Rofi background in the background
if [ -x "$HOME/.config/rofi/update-blur.sh" ]; then
    "$HOME/.config/rofi/update-blur.sh" "$WALLPAPER" >/dev/null 2>&1 &
fi

# 10. Update lockscreen cache in the background
if command -v betterlockscreen >/dev/null 2>&1; then
    betterlockscreen -u "$WALLPAPER" >/dev/null 2>&1 &
fi

# 11. Save current active theme info
mkdir -p "$HOME/.config/themes"
cat << EOF > "$HOME/.config/themes/current.theme"
NAME="$THEME_NAME"
WALLPAPER="$WALLPAPER"
THUMB="$THUMB"
APPLIED_AT="$(date '+%Y-%m-%d %H:%M:%S')"
EOF

# 12. Display modern Dunst notification with the theme thumbnail
sleep 0.2
if command -v dunstify >/dev/null 2>&1; then
    ICON_ARG=""
    if [ -f "$THUMB" ]; then
        ICON_ARG="-I $THUMB"
    fi
    dunstify $ICON_ARG -a "Theme Switcher" -u normal -t 3500 "✨ Тема активна" "<b>${THEME_NAME}</b>\nПалитра и компоненты обновлены" || true
else
    notify-send "✨ Тема активна" "${THEME_NAME}" || true
fi

echo "Theme applied successfully."
