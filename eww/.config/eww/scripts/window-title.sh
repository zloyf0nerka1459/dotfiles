#!/usr/bin/env bash

get_title() {
    local title=""
    # First attempt: i3 tree focused window
    title=$(i3-msg -t get_tree 2>/dev/null | jq -r '.. | select(.focused? == true and .type? == "con" and .window? != null) | .name // empty' 2>/dev/null)
    # Second attempt: xdotool
    if [ -z "$title" ]; then
        local win_id
        win_id=$(xdotool getactivewindow 2>/dev/null || true)
        if [ -n "$win_id" ]; then
            title=$(xdotool getwindowname "$win_id" 2>/dev/null || true)
        fi
    fi

    if [ -z "$title" ] || [ "$title" = "null" ]; then
        echo ""
        return
    fi

    # Replace newlines
    title=${title//$'\n'/ }
    title=${title//$'\r'/ }

    # Truncate to 30 characters like Polybar
    if [ ${#title} -gt 30 ]; then
        printf '%s...\n' "${title:0:27}"
    else
        printf '%s\n' "$title"
    fi
}

get_title
xprop -root -spy _NET_ACTIVE_WINDOW 2>/dev/null | while read -r _; do
    get_title
done
