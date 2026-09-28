#!/usr/bin/env bash
set -euo pipefail

OUTDIR="${HOME}/Pictures"
mkdir -p "$OUTDIR"
TS="$(date +%s)"
ACTION="${1:-full}"

# Helpers
notify() {
  # краткое уведомление
  notify-send "Screenshot" "$1"
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

case "$ACTION" in
  full)
    # полный скриншот в файл
    if command_exists maim; then
      FILE="$OUTDIR/${TS}.png"
      maim "$FILE" && notify "Saved: $FILE"
    else
      notify "maim not installed"
      exit 1
    fi
    ;;
  area)
    # выбор области и копирование в буфер (требует slop и xclip)
    if ! command_exists maim; then notify "maim not installed"; exit 1; fi
    if ! command_exists slop; then notify "slop not installed (needed for selection)"; exit 1; fi
    if ! command_exists xclip; then notify "xclip not installed (needed to copy)"; exit 1; fi

    # maim -s выводит изображение в stdout, xclip читает stdin (-i)
    maim -s | xclip -selection clipboard -t image/png -i && notify "Area copied to clipboard"
    ;;
  window)
    # скрин активного окна (xdotool -> maim -i)
    if ! command_exists maim; then notify "maim not installed"; exit 1; fi
    if ! command_exists xdotool; then notify "xdotool not installed"; exit 1; fi

    WINID="$(xdotool getactivewindow 2>/dev/null || echo "")"
    if [ -z "$WINID" ]; then
      # fallback: полный скрин
      FILE="$OUTDIR/${TS}.png"
      maim "$FILE" && notify "No active window id — full saved: $FILE"
    else
      FILE="$OUTDIR/${TS}_window.png"
      maim -i "$WINID" "$FILE" && notify "Window saved: $FILE"
    fi
    ;;
  clip_full)
    # (опционально) копировать весь экран в буфер
    if command_exists maim && command_exists xclip; then
      maim | xclip -selection clipboard -t image/png -i && notify "Full screen copied to clipboard"
    else
      notify "maim/xclip missing"
      exit 1
    fi
    ;;
  *)
    echo "Usage: $0 {full|area|window|clip_full}"
    exit 2
    ;;
esac
