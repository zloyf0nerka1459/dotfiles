#!/usr/bin/env bash

# Папка с обоями
WALLPAPER_DIR="$HOME/Pictures/Wallpapers"

# Берём список файлов (jpg/png), рекурсивно
mapfile -t WALLPAPERS < <(find "$WALLPAPER_DIR" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | sort)

# Если нет файлов — выходим
if [ ${#WALLPAPERS[@]} -eq 0 ]; then
    notify-send "Wallpaper Menu" "Не найдено обоев в $WALLPAPER_DIR"
    exit 1
fi

# Формируем список для Rofi: показываем путь ОТНОСИТЕЛЬНО папки с обоями,
# чтобы не терять подпапки и не путать одинаковые имена файлов
CHOICE=$(printf "%s\n" "${WALLPAPERS[@]#"$WALLPAPER_DIR"/}" \
         | rofi -dmenu -i -p "Обои:" \
                -theme-str 'window {width: 40%;} listview {lines: 12;}')

# Если отменили — выходим
[ -z "$CHOICE" ] && exit 0

# Восстанавливаем полный путь
SELECTED="$WALLPAPER_DIR/$CHOICE"

# Проверяем файл
if [ ! -f "$SELECTED" ]; then
    notify-send "Wallpaper Menu" "Файл не найден: $SELECTED"
    exit 1
fi

# 1. Генерируем и ПРИМЕНЯЕМ цветовую схему через wpg
#    (-n = не ставить обои, их поставит feh; -s = set, а не просто import)
wpg -ns "$SELECTED"

# 2. Устанавливаем обои (через feh)
feh --bg-scale "$SELECTED"

# 3. Обновляем Xresources (merge, чтобы не затирать остальные настройки)
xrdb -merge "$HOME/.cache/wal/colors.Xresources"

# 4. Перезапускаем xsettingsd, чтобы GTK2/3 приложения подхватили новую тему
killall xsettingsd 2>/dev/null
xsettingsd &

# 5. Установка обоев для лок-скрина (в фоне, долго генерируется)
betterlockscreen -u "$SELECTED" &

# 6. Обновляем EWW цветами
"$HOME/.config/eww/launch.sh" >/dev/null 2>&1

# 7. Обновляем фон Rofi новыми обоями
"$HOME/.config/rofi/update-blur.sh" "$SELECTED" &

# === ПЕРЕЗАПУСК DUNST (Polybar отключен в пользу EWW) ===
# "$HOME/.config/polybar/launch.sh" >/dev/null 2>&1

# Перезапускаем Dunst с сгенерированным конфигом цветов.
# ВАЖНО: файл colors-dunst.dunstrc pywal НЕ создаёт сам —
# нужен шаблон в ~/.config/wal/templates/colors-dunst.dunstrc
DUNST_CONF="$HOME/.cache/wal/colors-dunst.dunstrc"

killall dunst 2>/dev/null
sleep 0.3  # даём dunst время умереть, иначе новый может не стартовать

if [ -f "$DUNST_CONF" ]; then
    dunst -config "$DUNST_CONF" >/dev/null 2>&1 &
else
    dunst >/dev/null 2>&1 &
    notify-send "Wallpaper Menu" "Нет шаблона dunst: создай ~/.config/wal/templates/colors-dunst.dunstrc"
fi
# ==================================

sleep 0.3  # ждём, пока dunst поднимется, чтобы уведомление не потерялось

# Отправляем уведомление уже с новыми цветами
notify-send "Обои применены" "$CHOICE"
