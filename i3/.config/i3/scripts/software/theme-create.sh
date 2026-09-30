#!/usr/bin/env bash
# ==============================================================================
# Helper to create a new theme package from an image file
# Usage: theme-create <image_path> [Theme Display Name]
# ==============================================================================
set -euo pipefail

IMAGE_PATH="${1:-}"
THEME_NAME="${2:-}"

if [ -z "$IMAGE_PATH" ] || [ ! -f "$IMAGE_PATH" ]; then
    echo "Использование: theme-create <путь_к_картинке> [Отображаемое Имя]"
    echo "Пример: theme-create ~/Downloads/cyber.jpg '🌆 Cyber City'"
    exit 1
fi

REAL_IMG=$(readlink -f "$IMAGE_PATH")
BASE_NAME=$(basename "$REAL_IMG")
NAME_NO_EXT="${BASE_NAME%.*}"

# If no theme name provided, generate a clean one
if [ -z "$THEME_NAME" ]; then
    CLEAN=$(echo "$NAME_NO_EXT" | tr '_-' ' ' | awk '{for(i=1;i<=NF;i++)sub(/./,toupper(substr($i,1,1)),$i)}1')
    THEME_NAME="🎨 $CLEAN"
fi

# Generate folder ID (lowercase, alphanumeric + dashes)
SLUG=$(echo "$NAME_NO_EXT" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//;s/-$//')
TARGET_DIR="$HOME/.config/themes/$SLUG"

mkdir -p "$TARGET_DIR"

# 1. Copy image into theme dir
EXT="${BASE_NAME##*.}"
cp "$REAL_IMG" "$TARGET_DIR/wall.$EXT"

# 2. Generate high-quality 16:9 rounded thumbnail
python3 -c "
from PIL import Image, ImageOps, ImageDraw
src = '$TARGET_DIR/wall.$EXT'
dst = '$TARGET_DIR/thumb.png'
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
"

# 3. Create theme.conf
cat << EOF > "$TARGET_DIR/theme.conf"
# Theme configuration
name="$THEME_NAME"
description="Пользовательская тема $NAME_NO_EXT"
wallpaper="wall.$EXT"
author="$(whoami)"
created_at="$(date '+%Y-%m-%d %H:%M:%S')"
EOF

# 4. Create starter theme-eww.scss template
cat << 'EOF' > "$TARGET_DIR/theme-eww.scss"
/* ==============================================================================
 * Custom EWW Style for this Theme
 * You can customize top and bottom bars, chips, and workspaces!
 * Available colors: $background, $foreground, $color0..$color15, $accent
 * ============================================================================== */
.bar-container {
  background-color: rgba($color0, 0.94);
  border-bottom: 2px solid rgba($color4, 0.5);
}
.bottom-bar {
  border-top: 2px solid rgba($color4, 0.5);
}
.chip {
  border-radius: 8px;
  background-color: rgba($color8, 0.22);
  border: 1px solid rgba($color4, 0.35);
}
.chip:hover {
  background-color: rgba($color4, 0.25);
  border-color: $color4;
}
.ws-btn.focused {
  background-color: $color4;
  color: $color0;
  border-radius: 6px;
  font-weight: bold;
}
.task-btn.active {
  background-color: rgba($color4, 0.3);
  border-bottom: 2px solid $color4;
}
EOF

echo "✅ Тема успешно создана: $TARGET_DIR"
echo "   Название: $THEME_NAME"
echo "   Обои: $TARGET_DIR/wall.$EXT"
echo "   Миниатюра: $TARGET_DIR/thumb.png"

if command -v dunstify >/dev/null 2>&1; then
    dunstify -I "$TARGET_DIR/thumb.png" -a "Theme Creator" "✅ Новая тема создана" "<b>$THEME_NAME</b>\nДобавлена в селектор тем (\$mod+t)" || true
fi
