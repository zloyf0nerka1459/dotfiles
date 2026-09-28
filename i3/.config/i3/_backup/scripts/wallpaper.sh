#!/usr/bin/env bash

# Папка с обоями
WALLPAPER_DIR="$HOME/Pictures/Wallpapers"

# Берём список файлов (jpg/png)
mapfile -t WALLPAPERS < <(find "$WALLPAPER_DIR" -type f \( -iname "*.jpg" -o -iname "*.png" \) | sort)

# Если нет файлов — выходим
if [ ${#WALLPAPERS[@]} -eq 0 ]; then
    notify-send "Wallpaper Menu" "Не найдено обоев в $WALLPAPER_DIR"
    exit 1
fi

# Формируем список для Rofi
CHOICE=$(printf "%s\n" "${WALLPAPERS[@]##*/}" \
         | rofi -dmenu -i -p "Обои:" -width 40 -lines 12)

# Если отменили — выходим
[ -z "$CHOICE" ] && exit 0

# Находим выбранный полный путь
SELECTED="$WALLPAPER_DIR/$CHOICE"

# Проверяем файл
if [ ! -f "$SELECTED" ]; then
    notify-send "Wallpaper Menu" "Файл не найден: $SELECTED"
    exit 1
fi

# Устанавливаем обои (через feh)
feh --bg-scale "$SELECTED"

# Генерируем цвета через pywal
wal -i "$SELECTED"

# Обновляем Xresources
xrdb ~/.cache/wal/colors.Xresources

# Перезапускаем Polybar
polybar-msg cmd restart 2> /dev/null

# Перезапускаем Dunst уведомления
pkill dunst
dunst &

# (Опционально) обновляем i3
i3-msg reload >/dev/null 2>&1
notify-send "Обои применены" "$CHOICE"
