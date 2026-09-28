#!/bin/bash

DIR="$HOME/Pictures/Screenshots"
mkdir -p "$DIR"

DATE=$(date +%Y%m%d-%H%M%S)

copy_clipboard() {
    # Используем CopyQ для безопасной передачи изображения в буфер X11
    copyq write image/png - < "$1" && copyq select 0
}

get_monitor_geom() {
    X=$(xdotool getmouselocation --shell | awk -F= '/X=/{print $2}')
    Y=$(xdotool getmouselocation --shell | awk -F= '/Y=/{print $2}')

    xrandr --query | grep " connected" | grep -oP '\d+x\d+\+\d+\+\d+' | while read -r line; do
        W=$(echo "$line" | cut -dx -f1)
        H=$(echo "$line" | cut -dx -f2 | cut -d+ -f1)
        OX=$(echo "$line" | cut -d+ -f2)
        OY=$(echo "$line" | cut -d+ -f3)

        if [ "$X" -ge "$OX" ] && [ "$X" -lt "$((OX + W))" ] && [ "$Y" -ge "$OY" ] && [ "$Y" -lt "$((OY + H))" ]; then
            echo "$line"
            return
        fi
    done
}

case "$1" in

active)
    GEOM=$(get_monitor_geom)

    if [ -z "$GEOM" ]; then
        FNAME="full-$DATE.png"
        FILE="$DIR/$FNAME"
        maim "$FILE"
    else
        FNAME="monitor-$DATE.png"
        FILE="$DIR/$FNAME"
        maim -g "$GEOM" "$FILE"
    fi

    copy_clipboard "$FILE"
;;

area)
    GEOM=$(slop -b 2 -c 0.3,0.4,0.6,0.4 2>/dev/null)
    [ -z "$GEOM" ] && exit 0

    FNAME="area-$DATE.png"
    FILE="$DIR/$FNAME"

    maim -g "$GEOM" "$FILE"
    copy_clipboard "$FILE"
;;

*)
    notify-send "Screenshot" "Unknown mode"
    exit 1
;;

esac


if [ ! -s "$FILE" ]; then
    rm -f "$FILE"
    notify-send "Ошибка скриншота" "Файл оказался пустым" -u critical
else
    notify-send "Скриншот готов" "$FNAME сохранён и скопирован" -i camera-photo -t 2000
fi