#!/usr/bin/env bash

get_vol() {
    local mute vol icon
    mute=$(pamixer --get-mute 2>/dev/null || echo "false")
    vol=$(pamixer --get-volume 2>/dev/null || echo "0")
    if [ "$mute" = "true" ]; then
        printf '{"muted":true,"volume":0,"icon":"","text":" Muted"}\n'
    else
        if [ "$vol" -lt 50 ]; then
            icon=""
        else
            icon=""
        fi
        printf '{"muted":false,"volume":%d,"icon":"%s","text":"%s %d%%"}\n' "$vol" "$icon" "$icon" "$vol"
    fi
}

get_vol
