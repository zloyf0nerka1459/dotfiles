#!/usr/bin/env bash
# Universal Polkit Authentication Agent Launcher
set -euo pipefail

POLKIT_AGENTS=(
    "/usr/lib/polkit-kde-authentication-agent-1"
    "/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1"
    "/usr/lib/xfce-polkit/xfce-polkit"
    "/usr/lib/lxpolkit/lxpolkit"
    "/usr/lib/mate-polkit/polkit-mate-authentication-agent-1"
    "/usr/lib/polkit-1-pantheon/io.elementary.desktop.agent-polkit"
)

for agent in "${POLKIT_AGENTS[@]}"; do
    if [ -x "$agent" ]; then
        exec "$agent"
    fi
done

echo "No polkit agent found. Please install polkit-kde-agent or polkit-gnome." >&2
exit 1
