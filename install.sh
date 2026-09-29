#!/usr/bin/env bash
# ==============================================================================
# Universal Installer for Arch Linux i3 + EWW + Picom Rice
# ==============================================================================
set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$HOME/.config_backup_$(date +%Y%m%d_%H%M%S)"

# Colors
C_RESET='\033[0m'
C_BOLD='\033[1m'
C_CYAN='\033[0;36m'
C_GREEN='\033[0;32m'
C_YELLOW='\033[0;33m'
C_RED='\033[0;31m'

log()   { printf "${C_GREEN}[+]${C_RESET} %s\n" "$*"; }
warn()  { printf "${C_YELLOW}[!]${C_RESET} %s\n" "$*" >&2; }
error() { printf "${C_RED}[x]${C_RESET} %s\n" "$*" >&2; exit 1; }
title() { printf "\n${C_BOLD}${C_CYAN}=== %s ===${C_RESET}\n" "$*"; }

# 1. Verification
title "Проверка окружения"
if [ ! -f /etc/arch-release ]; then
    error "Этот установщик предназначен исключительно для Arch Linux и производных (EndeavourOS, CachyOS, Manjaro)."
fi

# Detect AUR helper
AUR_HELPER=""
if command -v yay >/dev/null 2>&1; then
    AUR_HELPER="yay"
elif command -v paru >/dev/null 2>&1; then
    AUR_HELPER="paru"
else
    warn "AUR-хелпер не найден. Попытка установить yay-bin..."
    sudo pacman -S --needed --noconfirm git base-devel
    git clone https://aur.archlinux.org/yay-bin.git /tmp/yay-bin
    (cd /tmp/yay-bin && makepkg -si --noconfirm)
    rm -rf /tmp/yay-bin
    AUR_HELPER="yay"
fi
log "Используется AUR-хелпер: $AUR_HELPER"

# 2. Package Installation
title "Установка официальных пакетов (Pacman)"
PACMAN_PACKAGES=(
    i3-wm
    xorg-server
    xorg-xinit
    xorg-xrandr
    xorg-xprop
    xorg-xinput
    feh
    kitty
    rofi
    dunst
    pamixer
    maim
    slop
    xdotool
    copyq
    jq
    imagemagick
    python
    python-gobject
    python-pillow
    ttf-jetbrains-mono-nerd
    noto-fonts-emoji
    papirus-icon-theme
    stow
    starship
    networkmanager
    network-manager-applet
    nm-connection-editor
    polkit-kde-agent
    xsettingsd
    spice-vdagent
    fastfetch
    fish
    eza
    fzf
)

log "Проверка и установка зависимостей..."
sudo pacman -S --needed --noconfirm "${PACMAN_PACKAGES[@]}"
sudo systemctl enable --now spice-vdagentd 2>/dev/null || true

title "Установка AUR пакетов"
AUR_PACKAGES=(
    python-pywal16
    eww
    picom-pijulius-git
    autotiling
    xkblayout-state-git
)

for pkg in "${AUR_PACKAGES[@]}"; do
    if ! pacman -Qi "$pkg" >/dev/null 2>&1; then
        log "Установка $pkg из AUR..."
        $AUR_HELPER -S --needed --noconfirm "$pkg" || warn "Не удалось установить $pkg. Возможно, требуется ручная сборка."
    else
        log "$pkg уже установлен"
    fi
done

# 3. Backup existing configs
title "Резервное копирование существующих конфигураций"
STOW_PACKAGES=(i3 eww picom kitty rofi dunst themes wal starship gtk fastfetch fish bin xorg system-control-center)
mkdir -p "$BACKUP_DIR"

backup_if_needed() {
    local target="$1"
    if [ -e "$target" ] && [ ! -L "$target" ]; then
        log "Бэкап: $target -> $BACKUP_DIR/"
        mv "$target" "$BACKUP_DIR/"
    fi
}

backup_if_needed "$HOME/.config/i3"
backup_if_needed "$HOME/.config/eww"
backup_if_needed "$HOME/.config/picom"
backup_if_needed "$HOME/.config/kitty"
backup_if_needed "$HOME/.config/rofi"
backup_if_needed "$HOME/.config/dunst"
backup_if_needed "$HOME/.config/themes"
backup_if_needed "$HOME/.config/wal"
backup_if_needed "$HOME/.config/starship.toml"
backup_if_needed "$HOME/.config/gtk-3.0"
backup_if_needed "$HOME/.config/xsettingsd"
backup_if_needed "$HOME/.config/fastfetch"
backup_if_needed "$HOME/.config/fish"
backup_if_needed "$HOME/.Xresources"
backup_if_needed "$HOME/.config/system-control-center"

# 4. Deploy via GNU Stow
title "Связывание конфигураций через GNU Stow"
cd "$DOTFILES_DIR"
for pkg in "${STOW_PACKAGES[@]}"; do
    if [ -d "$DOTFILES_DIR/$pkg" ]; then
        stow -v --adopt -R -t "$HOME" "$pkg" || stow -v -R -t "$HOME" "$pkg" || warn "Внимание при связывании $pkg"
        log "Связано: $pkg"
    fi
done

# Ensure executable permissions on all scripts
chmod +x "$HOME/.config/i3/scripts/software/"* 2>/dev/null || true
chmod +x "$HOME/.config/i3/scripts/hardware/"* 2>/dev/null || true
chmod +x "$HOME/.config/eww/launch.sh" 2>/dev/null || true
chmod +x "$HOME/.config/eww/scripts/"* 2>/dev/null || true
chmod +x "$HOME/.local/bin/"* 2>/dev/null || true
chmod +x "$HOME/.config/system-control-center/"* 2>/dev/null || true

# 5. Xorg System Tweaks
title "Применение системных настроек Xorg"
if [ -d "/etc/X11/xorg.conf.d" ]; then
    log "Установка Xorg твиков (Flat mouse acceleration, предотвращение гашения экрана)..."
    sudo cp -n "$DOTFILES_DIR/system/xorg/"*.conf /etc/X11/xorg.conf.d/ 2>/dev/null || warn "Не удалось скопировать конфиги в /etc/X11/xorg.conf.d. Конфиги сохранены в dotfiles/system/xorg/."
fi

# 6. Initialize theme
title "Инициализация дефолтной темы оформления"
DEFAULT_THEME="$HOME/.config/themes/ghibli-serenity"
if [ -d "$DEFAULT_THEME" ]; then
    log "Применение стартовой темы: Ghibli Serenity..."
    "$HOME/.config/i3/scripts/software/theme-apply.sh" "$DEFAULT_THEME" || warn "Не удалось автоматически применить тему. Запустите вручную через Mod+T."
fi

title "Установка завершена!"
printf "${C_GREEN}${C_BOLD}%s${C_RESET}\n" "Система успешно сконфигурирована!"
printf "Горячие клавиши:\n"
printf "  ${C_CYAN}Mod + Enter${C_RESET}       - Kitty Terminal\n"
printf "  ${C_CYAN}Mod + d${C_RESET}           - Rofi App Launcher\n"
printf "  ${C_CYAN}Mod + t${C_RESET}           - Выбор темы (Hyprdots Theme Switcher)\n"
printf "  ${C_CYAN}Mod + b${C_RESET}           - Браузер\n"
printf "  ${C_CYAN}Mod + p${C_RESET}           - Игровой режим (вкл/выкл Picom)\n"
printf "  ${C_CYAN}Print / Shift+Print${C_RESET} - Скриншоты экрана / области\n"
printf "  ${C_CYAN}Mod + Shift + r${C_RESET}   - Перезагрузка i3\n"
