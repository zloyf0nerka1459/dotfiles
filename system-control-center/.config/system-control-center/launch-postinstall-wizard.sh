#!/usr/bin/env bash

set -euo pipefail

STATE_ROOT="${HOME}/.local/state/fonera-dots"
MARKER="${STATE_ROOT}/postinstall-wizard-pending"
WIZARD="${HOME}/.config/system-control-center/postinstall_wizard.py"

[ -n "${DISPLAY:-}" ] || exit 0
[ -f "${MARKER}" ] || exit 0
[ -f "${WIZARD}" ] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

if pgrep -f "postinstall_wizard.py" >/dev/null 2>&1; then
    exit 0
fi

python3 "${WIZARD}" >/dev/null 2>&1 &
