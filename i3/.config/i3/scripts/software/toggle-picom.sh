#!/usr/bin/env bash

if pgrep -x "picom" > /dev/null; then
    killall -9 picom
    if command -v dunstify >/dev/null 2>&1; then
        dunstify -u normal -h string:x-dunst-stack-tag:picom -t 2000 "🎮 Игровой режим" "Композитор Picom ОТКЛЮЧЕН (максимальная плавность, 0 задержек)"
    elif command -v notify-send >/dev/null 2>&1; then
        notify-send -t 2000 "🎮 Игровой режим" "Композитор Picom ОТКЛЮЧЕН (максимальная плавность, 0 задержек)"
    fi
else
    picom --config "$HOME/.config/picom/picom.conf" -b
    if command -v dunstify >/dev/null 2>&1; then
        dunstify -u normal -h string:x-dunst-stack-tag:picom -t 2000 "✨ Обычный режим" "Композитор Picom ВКЛЮЧЕН (эффекты и анимации активны)"
    elif command -v notify-send >/dev/null 2>&1; then
        notify-send -t 2000 "✨ Обычный режим" "Композитор Picom ВКЛЮЧЕН (эффекты и анимации активны)"
    fi
fi
