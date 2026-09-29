#!/bin/bash

# Папка с твоими обоями (темами)
WALL_DIR="$HOME/Pictures/Wallpapers"
# Скрипт обновления темы, который мы делали ранее
UPDATE_SCRIPT="$HOME/.local/bin/update-theme.sh"

# 1. Получаем список картинок
# find ищет файлы, basename оставляет только имя для красоты в меню
# Но нам нужен полный путь для иконки.
# Rofi принимает формат: "Текст\0icon\x1fПуть_к_картинке"

# Генерируем список для Rofi
# Формат вывода для Rofi с иконками:
# Имя_файла\0icon\x1f/путь/к/файлу
list_themes() {
    find "$WALL_DIR" -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.png" -o -iname "*.jpeg" \) | while read -r filepath; do
        filename=$(basename "$filepath")
        # Экранируем, чтобы Rofi понял, что это иконка
        echo -en "${filename}\0icon\x1f${filepath}\n"
    done
}

# 2. Запускаем Rofi
# -dmenu: режим меню
# -theme: путь к нашему дизайну справа
# -p: подсказка в поиске
SELECTED=$(list_themes | rofi -dmenu -i -p "Theme" -theme ~/.config/rofi/sidebar.rasi)

# 3. Если что-то выбрали — применяем
if [ -n "$SELECTED" ]; then
    FULL_PATH="$WALL_DIR/$SELECTED"
    # Запускаем твой скрипт обновления
    "$UPDATE_SCRIPT" "$FULL_PATH"
fi
