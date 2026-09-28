#!/usr/bin/env bash

get_workspaces() {
    i3-msg -t get_workspaces 2>/dev/null | jq -c '
        [ .[] | {
            name: .name,
            num: (.num // 0),
            focused: (.focused // false),
            urgent: (.urgent // false),
            visible: (.visible // false)
        } ] | sort_by(.num)
    ' 2>/dev/null || echo "[]"
}

get_workspaces
i3-msg -t subscribe -m '[ "workspace" ]' 2>/dev/null | while read -r _; do
    get_workspaces
done
