#!/bin/bash

DIR="$HOME/Pictures/Screenshots"
mkdir -p "$DIR"
DATE=$(date +%Y%m%d-%H%M%S)

case "$1" in
    active)
        # Получаем координаты мыши
        X=$(xdotool getmouselocation --shell | grep X= | cut -d= -f2)
        Y=$(xdotool getmouselocation --shell | grep Y= | cut -d= -f2)

        # Находим геометрию монитора, в котором находится мышь
        GEOM=$(xrandr --query | grep " connected" | grep -oP '\d+x\d+\+\d+\+\d+' | while read -r line; do
            W=$(echo $line | cut -dx -f1)
            H=$(echo $line | cut -dx -f2 | cut -d+ -f1)
            OX=$(echo $line | cut -d+ -f2)
            OY=$(echo $line | cut -d+ -f3)
            if [ "$X" -ge "$OX" ] && [ "$X" -lt "$((OX + W))" ] && [ "$Y" -ge "$OY" ] && [ "$Y" -lt "$((OY + H))" ]; then
                echo "$line"
                break
            fi
        done)

        # Если координаты найти не удалось, делаем полный скрин (запасной вариант)
        if [ -z "$GEOM" ]; then
            FNAME="full-$DATE.png"
            maim | tee "$DIR/$FNAME" | xclip -selection clipboard -t image/png
        else
            FNAME="monitor-$DATE.png"
            maim -g "$GEOM" | tee "$DIR/$FNAME" | xclip -selection clipboard -t image/png
        fi
        ;;
    area)
        FNAME="area-$DATE.png"
        maim -s | tee "$DIR/$FNAME" | xclip -selection clipboard -t image/png
        ;;
esac

# Проверка: если файл пустой (0 байт), удаляем его и шлем ошибку
if [ ! -s "$DIR/$FNAME" ]; then
    rm -f "$DIR/$FNAME"
    notify-send "Ошибка скриншота" "Файл оказался пустым. Проверь maim и xdotool." -u critical
else
    notify-send "Скриншот готов" "Сохранено: $FNAME" -i camera-photo -t 2000
fi
