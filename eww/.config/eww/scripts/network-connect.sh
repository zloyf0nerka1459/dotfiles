#!/usr/bin/env bash
# Connect to Wi-Fi network with intelligent Rofi password prompt if secured
set -euo pipefail

SSID="${1:-}"
LOCKED="${2:-true}"

if [ -z "$SSID" ]; then
    echo "Usage: $0 <ssid> [locked:true|false]"
    exit 1
fi

notify() {
    local title="$1"
    local msg="$2"
    local icon="${3:-network-wireless}"
    local urgency="${4:-normal}"
    if command -v dunstify >/dev/null 2>&1; then
        dunstify -a "Wi-Fi" -u "$urgency" -i "$icon" "$title" "$msg"
    elif command -v notify-send >/dev/null 2>&1; then
        notify-send -u "$urgency" -i "$icon" "$title" "$msg"
    fi
}

# Check if connection profile already exists
if nmcli -t -f NAME connection show | grep -Fxq "$SSID"; then
    notify "Подключение к Wi-Fi..." "Активация сохраненного профиля '$SSID'" "network-wireless"
    if nmcli connection up "$SSID" >/dev/null 2>&1; then
        notify "✅ Подключено" "Сеть: <b>$SSID</b>" "network-wireless"
        ~/.config/eww/scripts/network.py --rescan >/dev/null 2>&1 &
        exit 0
    fi
fi

# If password is required and not saved
if [ "$LOCKED" = "true" ]; then
    PASS=$(rofi -dmenu -password -p "Пароль для '$SSID'" \
        -theme "$HOME/.config/rofi/config.rasi" \
        -theme-str 'window {width: 440px; height: 130px;} listview {lines: 0;} mainbox {children: [inputbar];}' 2>/dev/null || true)

    if [ -z "$PASS" ]; then
        exit 0
    fi

    notify "Подключение к Wi-Fi..." "Проверка учетных данных для '$SSID'..." "network-wireless"
    if nmcli dev wifi connect "$SSID" password "$PASS" >/dev/null 2>&1; then
        notify "✅ Успешно" "Подключено к <b>$SSID</b>" "network-wireless"
    else
        notify "❌ Ошибка подключения" "Не удалось подключиться к '$SSID'. Проверьте пароль." "dialog-error" "critical"
    fi
else
    # Open network
    notify "Подключение к Wi-Fi..." "Подключение к открытой сети '$SSID'..." "network-wireless"
    if nmcli dev wifi connect "$SSID" >/dev/null 2>&1; then
        notify "✅ Успешно" "Подключено к <b>$SSID</b>" "network-wireless"
    else
        notify "❌ Ошибка" "Не удалось подключиться к '$SSID'" "dialog-error" "critical"
    fi
fi

~/.config/eww/scripts/network.py --rescan >/dev/null 2>&1 &
