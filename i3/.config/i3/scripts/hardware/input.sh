#!/usr/bin/env bash
# ==============================================================================
# Xorg Input & Latency Optimization Script
# ==============================================================================
# Применяет твики ввода:
# 1. Мгновенный отклик клавиатуры (xset r rate)
# 2. Отключение тайм-аута гашения экрана (xset s off -dpms)
# 3. Переключение раскладок (us,ru через Win+Space)
# 4. Raw 1:1 Flat-профиль мыши для libinput (отключение акселерации)
# ==============================================================================

set -u

[ -n "${DISPLAY:-}" ] || exit 0

# 1. Быстрый и отзывчивый отклик клавиатуры
# Задержка перед повтором 280мс, скорость 40 повторов в секунду
if command -v xset >/dev/null 2>&1; then
    xset r rate 280 40 2>/dev/null || true
    # Отключение автоматического гашения экрана и энергосбережения монитора во время работы/игр
    xset s off -dpms 2>/dev/null || true
fi

# 2. Раскладка клавиатуры
if [ -f "$HOME/.config/system-control-center/apply-input-settings.sh" ]; then
    "$HOME/.config/system-control-center/apply-input-settings.sh" 2>/dev/null || true
elif command -v setxkbmap >/dev/null 2>&1; then
    setxkbmap -layout "us,ru" -option "grp:win_space_toggle" 2>/dev/null || true
fi

# 3. Отключение акселерации мыши (Flat Profile / Raw Input 1:1 для точного прицеливания)
if command -v xinput >/dev/null 2>&1; then
    while IFS= read -r dev_id; do
        [ -n "$dev_id" ] || continue
        if xinput list-props "$dev_id" 2>/dev/null | grep -q "libinput Accel Profile Enabled"; then
            # 0, 1, 0 = Flat profile (Adaptive=0, Flat=1, Custom=0)
            xinput set-prop "$dev_id" "libinput Accel Profile Enabled" 0 1 0 2>/dev/null || true
            xinput set-prop "$dev_id" "libinput Accel Speed" 0 2>/dev/null || true
        fi
    done < <(xinput list --id-only 2>/dev/null || true)
fi

# 4. Системный курсор мыши (X11 root window)
if command -v xsetroot >/dev/null 2>&1; then
    xsetroot -cursor_name left_ptr 2>/dev/null || true
fi
