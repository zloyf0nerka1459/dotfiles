#!/usr/bin/env python3
# ==============================================================================
# i3wm / X11 System Control Center (Параметры системы в стиле KDE Plasma)
# ==============================================================================

import json
import os
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk

HOME = Path.home()
CONFIG_HOME = HOME / ".config"
I3_CONFIG_PATH = CONFIG_HOME / "i3" / "config"
AUTOSTART_DIR = CONFIG_HOME / "autostart"
DATA_DIR = CONFIG_HOME / "system-control-center"
BACKUPS_DIR = DATA_DIR / "backups"
INPUT_PROFILE_PATH = DATA_DIR / "input-profiles.json"
INPUT_SCRIPT_PATH = DATA_DIR / "apply-input-settings.sh"
LAUNCHER_SCRIPT_PATH = DATA_DIR / "launch.sh"
THEMES_DIR = CONFIG_HOME / "themes"
XRESOURCES_PATH = HOME / ".Xresources"

APPLICATION_DIRS = [
    HOME / ".local" / "share" / "applications",
    Path("/usr/local/share/applications"),
    Path("/usr/share/applications"),
]

BACKUP_TARGETS = [
    "i3",
    "autostart",
    "picom",
    "dunst",
    "rofi",
    "gtk-3.0",
    "xsettingsd",
    "themes",
    "wal",
    "system-control-center",
]

# ==============================================================================
# CSS Styling (KDE Breeze Dark / Plasma 6 Aesthetic)
# ==============================================================================
APP_CSS = """
window.control-center-window {
    background-color: #16181d;
    color: #e3e6ea;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", "Noto Sans", sans-serif;
}

.sidebar {
    background-color: #121418;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
    padding: 12px 10px;
}

.sidebar-title {
    font-size: 17px;
    font-weight: 800;
    color: #ffffff;
    margin-left: 8px;
    margin-top: 4px;
}

.sidebar-subtitle {
    font-size: 11px;
    color: #8b929c;
    margin-left: 8px;
    margin-bottom: 12px;
}

.sidebar-category {
    font-size: 11px;
    font-weight: 700;
    color: #64748b;
    padding: 10px 10px 4px 10px;
}

.sidebar-item {
    padding: 8px 12px;
    border-radius: 8px;
    color: #cbd5e1;
    font-size: 13px;
    font-weight: 500;
    transition: all 120ms ease;
    border: 1px solid transparent;
}

.sidebar-item:hover {
    background-color: rgba(255, 255, 255, 0.05);
    color: #f8fafc;
}

.sidebar-item.active {
    background-color: rgba(61, 174, 233, 0.18);
    color: #3daee9;
    font-weight: 700;
    border: 1px solid rgba(61, 174, 233, 0.35);
}

.content-area {
    padding: 24px 30px;
    background-color: #181b20;
}

.page-header {
    margin-bottom: 20px;
}

.page-title {
    font-size: 22px;
    font-weight: 800;
    color: #ffffff;
}

.page-subtitle {
    font-size: 13px;
    color: #94a3b8;
    margin-top: 2px;
}

.card {
    background-color: #20242a;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 16px;
}

.card-title {
    font-size: 15px;
    font-weight: 700;
    color: #f1f5f9;
}

.card-subtitle {
    font-size: 12px;
    color: #94a3b8;
    margin-top: 2px;
    margin-bottom: 12px;
}

.card-row {
    padding: 8px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.card-row:last-child {
    border-bottom: none;
}

.badge-tag {
    background-color: rgba(61, 174, 233, 0.15);
    color: #3daee9;
    border: 1px solid rgba(61, 174, 233, 0.3);
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 700;
}

.badge-green {
    background-color: rgba(34, 197, 94, 0.15);
    color: #22c55e;
    border: 1px solid rgba(34, 197, 94, 0.3);
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 700;
}

.badge-amber {
    background-color: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.3);
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 700;
}

.test-pad {
    background-color: #14161a;
    border: 2px dashed rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    padding: 24px;
    transition: all 150ms ease;
}

.test-pad:hover {
    border-color: rgba(61, 174, 233, 0.4);
    background-color: #16181d;
}

.mouse-btn-indicator {
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
    background-color: rgba(255, 255, 255, 0.06);
    color: #94a3b8;
    border: 1px solid rgba(255, 255, 255, 0.08);
}

.mouse-btn-indicator.active {
    background-color: #3daee9;
    color: #ffffff;
    border-color: #3daee9;
    box-shadow: 0 0 12px rgba(61, 174, 233, 0.5);
}

.status-bar {
    background-color: #121418;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    padding: 10px 20px;
}

button.suggested-action {
    background: linear-gradient(135deg, #3daee9 0%, #2980b9 100%);
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 700;
}

button.suggested-action:hover {
    background: linear-gradient(135deg, #4fb8ee 0%, #3498db 100%);
}

button {
    border-radius: 8px;
    padding: 6px 14px;
}

entry, spinbutton {
    border-radius: 8px;
    padding: 6px 10px;
}
"""

def add_class(widget: Gtk.Widget, *classes: str) -> Gtk.Widget:
    style_context = widget.get_style_context()
    for item in classes:
        style_context.add_class(item)
    return widget

def remove_class(widget: Gtk.Widget, *classes: str) -> Gtk.Widget:
    style_context = widget.get_style_context()
    for item in classes:
        style_context.remove_class(item)
    return widget

def load_css() -> None:
    provider = Gtk.CssProvider()
    provider.load_from_data(APP_CSS.encode("utf-8"))
    screen = Gdk.Screen.get_default()
    if screen:
        Gtk.StyleContext.add_provider_for_screen(
            screen,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

def ensure_dirs() -> None:
    for path in (CONFIG_HOME, DATA_DIR, BACKUPS_DIR, AUTOSTART_DIR):
        path.mkdir(parents=True, exist_ok=True)

def run_command(command: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=check)

# ==============================================================================
# Data Models & System Inspect
# ==============================================================================
@dataclass
class PointerDevice:
    id: int
    name: str
    accel_profile: str  # "flat" or "adaptive"
    accel_speed: float  # -1.0 to 1.0
    natural_scrolling: bool
    left_handed: bool
    middle_emulation: bool
    supports_profiles: bool = True

def list_pointer_devices() -> list[PointerDevice]:
    pointers: list[PointerDevice] = []
    try:
        out = run_command(["xinput", "list"]).stdout
    except Exception:
        return pointers

    in_pointers = False
    for line in out.splitlines():
        if "Virtual core pointer" in line:
            in_pointers = True
            continue
        if "Virtual core keyboard" in line:
            in_pointers = False
            continue
        if in_pointers:
            m = re.search(r"↳\s+(.+?)\s+id=(\d+)\s+\[slave\s+pointer", line)
            if m:
                name = m.group(1).strip()
                dev_id = int(m.group(2))
                if any(bad in name.lower() for bad in ["xtest", "consumer control", "system control"]):
                    continue
                dev = get_pointer_device(dev_id, name)
                if dev:
                    pointers.append(dev)
    return pointers

def get_pointer_device(dev_id: int, name: str) -> PointerDevice | None:
    try:
        out = run_command(["xinput", "list-props", str(dev_id)]).stdout
    except Exception:
        return None

    props: dict[str, str] = {}
    for line in out.splitlines():
        m = re.match(r"^\s*(.+?)\s+\((\d+)\):\s+(.+)$", line)
        if m:
            props[m.group(1).strip()] = m.group(3).strip()

    if "libinput Accel Speed" not in props and "libinput Natural Scrolling Enabled" not in props:
        return None

    # Acceleration profile
    profile_str = props.get("libinput Accel Profile Enabled", "1, 0, 0")
    # 0, 1, 0 -> Flat. 1, 0, 0 -> Adaptive.
    is_flat = profile_str.startswith("0, 1") or profile_str == "0 1 0"
    profile = "flat" if is_flat else "adaptive"

    supports_profiles = "libinput Accel Profiles Available" in props

    # Accel speed
    speed = 0.0
    try:
        speed = float(props.get("libinput Accel Speed", "0.0").split()[0])
    except Exception:
        pass

    natural = props.get("libinput Natural Scrolling Enabled", "0") == "1"
    left_handed = props.get("libinput Left Handed Enabled", "0") == "1"
    middle_emu = props.get("libinput Middle Emulation Enabled", "0") == "1"

    return PointerDevice(
        id=dev_id,
        name=name,
        accel_profile=profile,
        accel_speed=speed,
        natural_scrolling=natural,
        left_handed=left_handed,
        middle_emulation=middle_emu,
        supports_profiles=supports_profiles,
    )

def apply_pointer_device(dev: PointerDevice) -> None:
    # 1. Profile
    if dev.supports_profiles:
        profile_vals = ["0", "1", "0"] if dev.accel_profile == "flat" else ["1", "0", "0"]
        run_command(["xinput", "set-prop", str(dev.id), "libinput Accel Profile Enabled"] + profile_vals)
    # 2. Speed
    run_command(["xinput", "set-prop", str(dev.id), "libinput Accel Speed", f"{dev.accel_speed:.2f}"])
    # 3. Natural scrolling
    run_command(["xinput", "set-prop", str(dev.id), "libinput Natural Scrolling Enabled", "1" if dev.natural_scrolling else "0"])
    # 4. Left handed
    run_command(["xinput", "set-prop", str(dev.id), "libinput Left Handed Enabled", "1" if dev.left_handed else "0"])
    # 5. Middle emulation
    run_command(["xinput", "set-prop", str(dev.id), "libinput Middle Emulation Enabled", "1" if dev.middle_emulation else "0"])

def save_all_input_settings(devices: list[PointerDevice], layouts: str, switch_option: str, repeat_delay: int, repeat_rate: int) -> None:
    ensure_dirs()
    # Save JSON profiles
    data = {
        "devices": [
            {
                "name": d.name,
                "accel_profile": d.accel_profile,
                "accel_speed": round(d.accel_speed, 2),
                "natural_scrolling": d.natural_scrolling,
                "left_handed": d.left_handed,
                "middle_emulation": d.middle_emulation,
            }
            for d in devices
        ],
        "keyboard": {
            "layouts": layouts,
            "switch_option": switch_option,
            "repeat_delay": repeat_delay,
            "repeat_rate": repeat_rate,
        }
    }
    INPUT_PROFILE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Generate apply-input-settings.sh
    lines = [
        "#!/usr/bin/env bash",
        "# ==============================================================================",
        "# Auto-generated by System Control Center",
        "# ==============================================================================",
        "set -u",
        '[ -n "${DISPLAY:-}" ] || exit 0',
        "",
        "# 1. Keyboard Repeat Rate & Screen Blanking",
        "if command -v xset >/dev/null 2>&1; then",
        f"    xset r rate {repeat_delay} {repeat_rate} 2>/dev/null || true",
        "    xset s off -dpms 2>/dev/null || true",
        "fi",
        "",
        "# 2. Keyboard Layout",
        "if command -v setxkbmap >/dev/null 2>&1; then",
        "    setxkbmap -option '' >/dev/null 2>&1 || true",
        f'    setxkbmap -layout "{layouts}" -option "{switch_option}" >/dev/null 2>&1 || true',
        "fi",
        "",
        "# 3. Pointer Devices (libinput)",
        "command -v xinput >/dev/null 2>&1 || exit 0",
        "",
        "apply_prop() {",
        '    local device_name="$1"',
        '    local property_name="$2"',
        "    shift 2",
        "    while IFS= read -r dev_id; do",
        '        [ -n "$dev_id" ] || continue',
        '        xinput list-props "$dev_id" 2>/dev/null | grep -Fq "$property_name" || continue',
        '        xinput set-prop "$dev_id" "$property_name" "$@" >/dev/null 2>&1 || true',
        '    done < <(xinput list --id-only "$device_name" 2>/dev/null || true)',
        "}",
        "",
    ]

    for d in devices:
        safe_name = f'"{d.name}"'
        lines.append(f"# {d.name}")
        if d.supports_profiles:
            prof_args = "0 1 0" if d.accel_profile == "flat" else "1 0 0"
            lines.append(f"apply_prop {safe_name} 'libinput Accel Profile Enabled' {prof_args}")
        lines.append(f"apply_prop {safe_name} 'libinput Accel Speed' {d.accel_speed:.2f}")
        lines.append(f"apply_prop {safe_name} 'libinput Natural Scrolling Enabled' {'1' if d.natural_scrolling else '0'}")
        lines.append(f"apply_prop {safe_name} 'libinput Left Handed Enabled' {'1' if d.left_handed else '0'}")
        lines.append(f"apply_prop {safe_name} 'libinput Middle Emulation Enabled' {'1' if d.middle_emulation else '0'}")
        lines.append("")

    INPUT_SCRIPT_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    INPUT_SCRIPT_PATH.chmod(0o755)

def get_system_specs() -> dict[str, str]:
    specs: dict[str, str] = {}
    # OS
    specs["os"] = "Arch Linux x86_64"
    # Kernel
    specs["kernel"] = platform.release()
    # Uptime
    try:
        specs["uptime"] = run_command(["uptime", "-p"]).stdout.replace("up ", "").strip()
    except Exception:
        specs["uptime"] = "Неизвестно"
    # CPU
    cpu_name = "Intel Core i5-10400F CPU @ 2.90GHz"
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if "model name" in line:
                    cpu_name = line.split(":", 1)[1].strip()
                    break
    except Exception:
        pass
    specs["cpu"] = cpu_name
    # RAM
    ram_str = "16 GB"
    try:
        with open("/proc/meminfo") as f:
            mem = {}
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    mem[parts[0].strip()] = int(parts[1].split()[0])
            if "MemTotal" in mem:
                total_gb = mem["MemTotal"] / (1024 * 1024)
                avail_gb = mem.get("MemAvailable", 0) / (1024 * 1024)
                used_gb = total_gb - avail_gb
                ram_str = f"{used_gb:.1f} GB / {total_gb:.1f} GB ({int(used_gb/total_gb*100)}%)"
    except Exception:
        pass
    specs["ram"] = ram_str
    # GPU
    gpu_str = "NVIDIA GeForce GTX 1660 SUPER"
    try:
        out = run_command(["lspci"]).stdout
        for line in out.splitlines():
            if "VGA" in line or "3D" in line:
                gpu_str = line.split(":", 2)[-1].strip()
                break
    except Exception:
        pass
    specs["gpu"] = gpu_str
    # Desktop
    specs["wm"] = "i3-gaps (XLibre X11 Server)"
    return specs

def get_connected_displays() -> list[dict[str, Any]]:
    displays: list[dict[str, Any]] = []
    try:
        out = run_command(["xrandr", "--query"]).stdout
    except Exception:
        return displays

    current_disp: dict[str, Any] | None = None
    for line in out.splitlines():
        m = re.match(r"^(\S+)\s+(connected|disconnected)\s+(primary\s+)?(\d+x\d+\+\d+\+\d+)?.*$", line)
        if m:
            name, status, primary, geom = m.group(1), m.group(2), bool(m.group(3)), m.group(4)
            if status == "connected":
                current_disp = {
                    "name": name,
                    "primary": primary,
                    "geom": geom or "Auto",
                    "rate": "60 Hz",
                }
                displays.append(current_disp)
            else:
                current_disp = None
            continue

        if current_disp and "*" in line:
            # e.g. 1920x1080 60.00 + 144.00*
            parts = line.split()
            for p in parts:
                if "*" in p:
                    current_disp["rate"] = p.replace("*", "").replace("+", "") + " Hz"
                    break

    return displays

def list_themes() -> list[str]:
    if not THEMES_DIR.exists():
        return []
    themes = []
    for p in sorted(THEMES_DIR.iterdir()):
        if p.is_dir() and not p.name.startswith("."):
            themes.append(p.name)
    return themes

def get_current_theme() -> str:
    current_file = THEMES_DIR / "current.theme"
    if current_file.exists():
        try:
            return current_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    return "ghibli-serenity"

# ==============================================================================
# Main Application Window
# ==============================================================================
class ControlCenterWindow(Gtk.Window):
    def __init__(self) -> None:
        super().__init__(title="Параметры системы")
        ensure_dirs()
        add_class(self, "control-center-window")
        self.set_default_size(1140, 760)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_wmclass("system-control-center", "System-control-center")
        self.connect("destroy", Gtk.main_quit)

        # State
        self.devices: list[PointerDevice] = list_pointer_devices()
        self.current_device_idx: int = 0
        self.keyboard_layouts: str = "us,ru"
        self.keyboard_switch_option: str = "grp:win_space_toggle"
        self.keyboard_repeat_delay: int = 280
        self.keyboard_repeat_rate: int = 40
        self.picom_active: bool = False
        self.loading: bool = True
        self.status_lbl = Gtk.Label(label="Готово", xalign=0)

        # Load saved profile if exists
        self.load_saved_profile()

        # Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_box)

        content_panes = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        main_box.pack_start(content_panes, True, True, 0)

        # Left Sidebar
        self.sidebar_box = self.build_sidebar()
        content_panes.pack_start(self.sidebar_box, False, False, 0)

        # Right Stack Content
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(150)
        content_panes.pack_start(self.stack, True, True, 0)

        # Build Pages
        self.page_mouse = self.build_mouse_page()
        self.page_keyboard = self.build_keyboard_page()
        self.page_displays = self.build_displays_page()
        self.page_appearance = self.build_appearance_page()
        self.page_gaming = self.build_gaming_page()
        self.page_autostart = self.build_autostart_page()
        self.page_shortcuts = self.build_shortcuts_page()
        self.page_about = self.build_about_page()

        self.stack.add_named(self.page_mouse, "mouse")
        self.stack.add_named(self.page_keyboard, "keyboard")
        self.stack.add_named(self.page_displays, "displays")
        self.stack.add_named(self.page_appearance, "appearance")
        self.stack.add_named(self.page_gaming, "gaming")
        self.stack.add_named(self.page_autostart, "autostart")
        self.stack.add_named(self.page_shortcuts, "shortcuts")
        self.stack.add_named(self.page_about, "about")

        # Bottom status bar
        self.status_bar = self.build_status_bar()
        main_box.pack_end(self.status_bar, False, False, 0)

        self.loading = False

        # Set default active page
        self.select_page("mouse")

    def load_saved_profile(self) -> None:
        if INPUT_PROFILE_PATH.exists():
            try:
                data = json.loads(INPUT_PROFILE_PATH.read_text(encoding="utf-8"))
                kb = data.get("keyboard", {})
                self.keyboard_layouts = kb.get("layouts", "us,ru")
                self.keyboard_switch_option = kb.get("switch_option", "grp:win_space_toggle")
                self.keyboard_repeat_delay = kb.get("repeat_delay", 280)
                self.keyboard_repeat_rate = kb.get("repeat_rate", 40)
            except Exception:
                pass

    # --------------------------------------------------------------------------
    # Sidebar
    # --------------------------------------------------------------------------
    def build_sidebar(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        add_class(box, "sidebar")
        box.set_size_request(240, -1)

        # Header Title
        title = Gtk.Label(label="Параметры", xalign=0)
        add_class(title, "sidebar-title")
        box.pack_start(title, False, False, 0)

        subtitle = Gtk.Label(label="Центр управления системой i3wm", xalign=0)
        add_class(subtitle, "sidebar-subtitle")
        box.pack_start(subtitle, False, False, 0)

        # Search bar
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Поиск параметров...")
        self.search_entry.set_margin_bottom(12)
        self.search_entry.connect("search-changed", self.on_search_changed)
        box.pack_start(self.search_entry, False, False, 0)

        # Items ListBox
        self.sidebar_list = Gtk.ListBox()
        self.sidebar_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.sidebar_list.connect("row-selected", self.on_sidebar_row_selected)

        self.sidebar_items = [
            ("HEADER", "Устройства ввода", None),
            ("ITEM", "🖱️  Мышь и тачпад", "mouse"),
            ("ITEM", "⌨️  Клавиатура", "keyboard"),
            ("HEADER", "Оборудование и экран", None),
            ("ITEM", "🖥️  Экраны и дисплеи", "displays"),
            ("ITEM", "⚡  Игровой режим & Picom", "gaming"),
            ("HEADER", "Персонализация", None),
            ("ITEM", "🎨  Внешний вид и темы", "appearance"),
            ("HEADER", "Рабочая среда", None),
            ("ITEM", "🚀  Автозапуск", "autostart"),
            ("ITEM", "⌨️  Горячие клавиши", "shortcuts"),
            ("HEADER", "Система", None),
            ("ITEM", "ℹ️  О системе", "about"),
        ]

        self.sidebar_rows: dict[str, Gtk.ListBoxRow] = {}

        for item_type, label, page_name in self.sidebar_items:
            if item_type == "HEADER":
                h_label = Gtk.Label(label=label, xalign=0)
                add_class(h_label, "sidebar-category")
                row = Gtk.ListBoxRow()
                row.set_selectable(False)
                row.set_activatable(False)
                row.add(h_label)
                self.sidebar_list.add(row)
            else:
                row = Gtk.ListBoxRow()
                add_class(row, "sidebar-item")
                row.page_name = page_name  # type: ignore
                i_label = Gtk.Label(label=label, xalign=0)
                row.add(i_label)
                self.sidebar_list.add(row)
                if page_name:
                    self.sidebar_rows[page_name] = row

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.sidebar_list)
        box.pack_start(scrolled, True, True, 0)

        return box

    def on_sidebar_row_selected(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if row and hasattr(row, "page_name"):
            self.select_page(row.page_name)

    def select_page(self, page_name: str) -> None:
        self.stack.set_visible_child_name(page_name)
        if page_name in self.sidebar_rows:
            self.sidebar_list.select_row(self.sidebar_rows[page_name])

    def on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        text = entry.get_text().lower().strip()
        for page_name, row in self.sidebar_rows.items():
            child = row.get_child()
            if isinstance(child, Gtk.Label):
                visible = text in child.get_text().lower() or text in page_name
                row.set_visible(visible)

    # --------------------------------------------------------------------------
    # Page 1: Mouse & Touchpad (В стиле KDE Mouse KCM)
    # --------------------------------------------------------------------------
    def build_mouse_page(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        add_class(root, "content-area")
        scrolled.add(root)

        # Page Header
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        add_class(header, "page-header")
        title = Gtk.Label(label="Мышь и сенсорная панель", xalign=0)
        add_class(title, "page-title")
        subtitle = Gtk.Label(label="Настройка ускорения, скорости курсора, кнопок и прокрутки", xalign=0)
        add_class(subtitle, "page-subtitle")
        header.pack_start(title, False, False, 0)
        header.pack_start(subtitle, False, False, 0)
        root.pack_start(header, False, False, 0)

        # Card 1: Device Selector
        dev_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        add_class(dev_card, "card")
        root.pack_start(dev_card, False, False, 0)

        dev_title = Gtk.Label(label="Устройство указателя", xalign=0)
        add_class(dev_title, "card-title")
        dev_card.pack_start(dev_title, False, False, 0)

        dev_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.device_combo = Gtk.ComboBoxText()
        for dev in self.devices:
            self.device_combo.append_text(f"{dev.name} (id={dev.id})")
        if self.devices:
            self.device_combo.set_active(0)
        self.device_combo.connect("changed", self.on_mouse_device_selected)
        dev_row.pack_start(self.device_combo, True, True, 0)

        refresh_btn = Gtk.Button(label="🔄 Обновить список")
        refresh_btn.connect("clicked", self.on_refresh_mouse_devices)
        dev_row.pack_end(refresh_btn, False, False, 0)
        dev_card.pack_start(dev_row, False, False, 0)

        # Card 2: Acceleration Profile (Flat vs Adaptive)
        accel_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        add_class(accel_card, "card")
        root.pack_start(accel_card, False, False, 0)

        accel_title = Gtk.Label(label="Профиль ускорения курсора", xalign=0)
        add_class(accel_title, "card-title")
        accel_sub = Gtk.Label(label="Реакция скорости курсора на ускорение руки", xalign=0)
        add_class(accel_sub, "card-subtitle")
        accel_card.pack_start(accel_title, False, False, 0)
        accel_card.pack_start(accel_sub, False, False, 0)

        # Radio buttons
        self.accel_flat_radio = Gtk.RadioButton.new_with_label_from_widget(
            None,
            "Плоский профиль (Flat / Raw 1:1) — Рекомендуется для игр (CS2, шутеры)"
        )
        self.accel_flat_desc = Gtk.Label(
            label="       Отключает искусственную акселерацию. Мышь двигается ровно на физическое расстояние.",
            xalign=0
        )
        add_class(self.accel_flat_desc, "card-subtitle")

        self.accel_adaptive_radio = Gtk.RadioButton.new_with_label_from_widget(
            self.accel_flat_radio,
            "Адаптивный профиль (Adaptive) — Стандартное ускорение"
        )
        self.accel_adaptive_desc = Gtk.Label(
            label="       Курсор ускоряется при резких взмахах рукой. Привычно для офисной работы.",
            xalign=0
        )
        add_class(self.accel_adaptive_desc, "card-subtitle")

        self.accel_flat_radio.connect("toggled", self.on_accel_profile_toggled)

        accel_card.pack_start(self.accel_flat_radio, False, False, 0)
        accel_card.pack_start(self.accel_flat_desc, False, False, 0)
        accel_card.pack_start(self.accel_adaptive_radio, False, False, 0)
        accel_card.pack_start(self.accel_adaptive_desc, False, False, 0)

        # Card 3: Pointer Speed
        speed_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        add_class(speed_card, "card")
        root.pack_start(speed_card, False, False, 0)

        speed_title = Gtk.Label(label="Скорость указателя (Чувствительность)", xalign=0)
        add_class(speed_title, "card-title")
        speed_sub = Gtk.Label(label="Базовая скорость перемещения курсора (от -1.0 до +1.0)", xalign=0)
        add_class(speed_sub, "card-subtitle")
        speed_card.pack_start(speed_title, False, False, 0)
        speed_card.pack_start(speed_sub, False, False, 0)

        speed_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self.speed_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, -1.0, 1.0, 0.05)
        self.speed_scale.set_value(0.0)
        self.speed_scale.set_digits(2)
        self.speed_scale.set_hexpand(True)
        self.speed_scale.connect("value-changed", self.on_speed_scale_changed)

        self.speed_val_label = Gtk.Label(label="0.00")
        add_class(self.speed_val_label, "badge-tag")

        reset_speed_btn = Gtk.Button(label="Сброс в 0.0")
        reset_speed_btn.connect("clicked", lambda _: self.speed_scale.set_value(0.0))

        speed_row.pack_start(self.speed_scale, True, True, 0)
        speed_row.pack_start(self.speed_val_label, False, False, 0)
        speed_row.pack_start(reset_speed_btn, False, False, 0)
        speed_card.pack_start(speed_row, False, False, 0)

        # Card 4: Scrolling & Buttons
        buttons_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        add_class(buttons_card, "card")
        root.pack_start(buttons_card, False, False, 0)

        btn_title = Gtk.Label(label="Прокрутка и кнопки", xalign=0)
        add_class(btn_title, "card-title")
        buttons_card.pack_start(btn_title, False, False, 0)

        # Natural scrolling
        row_natural = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        add_class(row_natural, "card-row")
        nat_lbl = Gtk.Label(label="Естественная прокрутка (инверсия направления колесика)", xalign=0)
        self.switch_natural = Gtk.Switch()
        self.switch_natural.connect("notify::active", self.on_mouse_setting_changed)
        row_natural.pack_start(nat_lbl, True, True, 0)
        row_natural.pack_end(self.switch_natural, False, False, 0)
        buttons_card.pack_start(row_natural, False, False, 0)

        # Left handed
        row_left = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        add_class(row_left, "card-row")
        left_lbl = Gtk.Label(label="Режим для левши (поменять ЛКМ и ПКМ местами)", xalign=0)
        self.switch_left = Gtk.Switch()
        self.switch_left.connect("notify::active", self.on_mouse_setting_changed)
        row_left.pack_start(left_lbl, True, True, 0)
        row_left.pack_end(self.switch_left, False, False, 0)
        buttons_card.pack_start(row_left, False, False, 0)

        # Middle emulation
        row_mid = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        add_class(row_mid, "card-row")
        mid_lbl = Gtk.Label(label="Эмуляция средней кнопки (одновременное нажатие ЛКМ + ПКМ)", xalign=0)
        self.switch_middle = Gtk.Switch()
        self.switch_middle.connect("notify::active", self.on_mouse_setting_changed)
        row_mid.pack_start(mid_lbl, True, True, 0)
        row_mid.pack_end(self.switch_middle, False, False, 0)
        buttons_card.pack_start(row_mid, False, False, 0)

        # Card 5: Interactive Test Area (🎯 Как в KDE Plasma!)
        test_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        add_class(test_card, "card")
        root.pack_start(test_card, False, False, 0)

        test_title = Gtk.Label(label="🎯 Зона проверки мыши (Интерактивный тест)", xalign=0)
        add_class(test_title, "card-title")
        test_sub = Gtk.Label(label="Подвигайте курсор, покликайте кнопками и покрутите колесико для проверки чувствительности", xalign=0)
        add_class(test_sub, "card-subtitle")
        test_card.pack_start(test_title, False, False, 0)
        test_card.pack_start(test_sub, False, False, 0)

        # Indicators bar
        indicators_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.lbl_btn1 = Gtk.Label(label="Левая (ЛКМ)")
        add_class(self.lbl_btn1, "mouse-btn-indicator")
        self.lbl_btn2 = Gtk.Label(label="Колесико (СКМ)")
        add_class(self.lbl_btn2, "mouse-btn-indicator")
        self.lbl_btn3 = Gtk.Label(label="Правая (ПКМ)")
        add_class(self.lbl_btn3, "mouse-btn-indicator")
        self.lbl_scroll = Gtk.Label(label="Скролл")
        add_class(self.lbl_scroll, "mouse-btn-indicator")

        self.click_count = 0
        self.lbl_click_count = Gtk.Label(label="Всего кликов: 0")
        add_class(self.lbl_click_count, "badge-tag")

        indicators_box.pack_start(self.lbl_btn1, False, False, 0)
        indicators_box.pack_start(self.lbl_btn2, False, False, 0)
        indicators_box.pack_start(self.lbl_btn3, False, False, 0)
        indicators_box.pack_start(self.lbl_scroll, False, False, 0)
        indicators_box.pack_end(self.lbl_click_count, False, False, 0)
        test_card.pack_start(indicators_box, False, False, 0)

        # Interactive EventBox
        self.test_event_box = Gtk.EventBox()
        add_class(self.test_event_box, "test-pad")
        self.test_event_box.set_size_request(-1, 100)
        self.test_event_box.set_above_child(True)
        self.test_event_box.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.SCROLL_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
        )

        test_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        test_inner_lbl = Gtk.Label(label="Кликайте и прокручивайте колесико в этой области...")
        test_inner_lbl.set_opacity(0.7)
        test_inner.pack_start(test_inner_lbl, True, True, 0)
        self.test_event_box.add(test_inner)

        self.test_event_box.connect("button-press-event", self.on_test_button_press)
        self.test_event_box.connect("button-release-event", self.on_test_button_release)
        self.test_event_box.connect("scroll-event", self.on_test_scroll)
        test_card.pack_start(self.test_event_box, False, False, 0)

        # Initial form population
        self.update_mouse_form()
        return scrolled

    def on_mouse_device_selected(self, combo: Gtk.ComboBoxText) -> None:
        idx = combo.get_active()
        if idx >= 0 and idx < len(self.devices):
            self.current_device_idx = idx
            self.update_mouse_form()

    def on_refresh_mouse_devices(self, _btn: Gtk.Button) -> None:
        self.devices = list_pointer_devices()
        self.device_combo.remove_all()
        for dev in self.devices:
            self.device_combo.append_text(f"{dev.name} (id={dev.id})")
        if self.devices:
            self.device_combo.set_active(0)
        self.update_mouse_form()
        self.set_status("Список устройств ввода обновлён")

    def update_mouse_form(self) -> None:
        if not self.devices or self.current_device_idx >= len(self.devices):
            return
        dev = self.devices[self.current_device_idx]

        # Profile
        if dev.accel_profile == "flat":
            self.accel_flat_radio.set_active(True)
        else:
            self.accel_adaptive_radio.set_active(True)

        # Speed
        self.speed_scale.set_value(dev.accel_speed)
        self.speed_val_label.set_text(f"{dev.accel_speed:+.2f}")

        # Toggles
        self.switch_natural.set_active(dev.natural_scrolling)
        self.switch_left.set_active(dev.left_handed)
        self.switch_middle.set_active(dev.middle_emulation)

    def on_accel_profile_toggled(self, radio: Gtk.RadioButton) -> None:
        if getattr(self, "loading", False):
            return
        if not self.devices or self.current_device_idx >= len(self.devices):
            return
        dev = self.devices[self.current_device_idx]
        dev.accel_profile = "flat" if self.accel_flat_radio.get_active() else "adaptive"
        self.apply_current_mouse()

    def on_speed_scale_changed(self, scale: Gtk.Scale) -> None:
        val = scale.get_value()
        self.speed_val_label.set_text(f"{val:+.2f}")
        if getattr(self, "loading", False):
            return
        if self.devices and self.current_device_idx < len(self.devices):
            self.devices[self.current_device_idx].accel_speed = val
            self.apply_current_mouse()

    def on_mouse_setting_changed(self, switch: Gtk.Switch, _pspec: Any) -> None:
        if getattr(self, "loading", False):
            return
        if not self.devices or self.current_device_idx >= len(self.devices):
            return
        dev = self.devices[self.current_device_idx]
        dev.natural_scrolling = self.switch_natural.get_active()
        dev.left_handed = self.switch_left.get_active()
        dev.middle_emulation = self.switch_middle.get_active()
        self.apply_current_mouse()

    def apply_current_mouse(self) -> None:
        if not self.devices or self.current_device_idx >= len(self.devices):
            return
        dev = self.devices[self.current_device_idx]
        apply_pointer_device(dev)
        save_all_input_settings(
            self.devices,
            self.keyboard_layouts,
            self.keyboard_switch_option,
            self.keyboard_repeat_delay,
            self.keyboard_repeat_rate,
        )
        self.set_status(f"Настройки для «{dev.name}» применены мгновенно")

    # Mouse Test Pad Events
    def on_test_button_press(self, _widget: Gtk.Widget, event: Gdk.EventButton) -> bool:
        self.click_count += 1
        self.lbl_click_count.set_text(f"Всего кликов: {self.click_count}")
        if event.button == 1:
            add_class(self.lbl_btn1, "active")
        elif event.button == 2:
            add_class(self.lbl_btn2, "active")
        elif event.button == 3:
            add_class(self.lbl_btn3, "active")
        return True

    def on_test_button_release(self, _widget: Gtk.Widget, event: Gdk.EventButton) -> bool:
        if event.button == 1:
            remove_class(self.lbl_btn1, "active")
        elif event.button == 2:
            remove_class(self.lbl_btn2, "active")
        elif event.button == 3:
            remove_class(self.lbl_btn3, "active")
        return True

    def on_test_scroll(self, _widget: Gtk.Widget, event: Gdk.EventScroll) -> bool:
        dir_text = "Скролл ↑" if event.direction == Gdk.ScrollDirection.UP else "Скролл ↓"
        self.lbl_scroll.set_text(dir_text)
        add_class(self.lbl_scroll, "active")
        GLib.timeout_add(150, lambda: remove_class(self.lbl_scroll, "active"))
        return True

    # --------------------------------------------------------------------------
    # Page 2: Keyboard (Клавиатура и раскладки)
    # --------------------------------------------------------------------------
    def build_keyboard_page(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        add_class(root, "content-area")
        scrolled.add(root)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        add_class(header, "page-header")
        title = Gtk.Label(label="Клавиатура", xalign=0)
        add_class(title, "page-title")
        subtitle = Gtk.Label(label="Раскладки ввода, клавиша переключения и скорость повтора", xalign=0)
        add_class(subtitle, "page-subtitle")
        header.pack_start(title, False, False, 0)
        header.pack_start(subtitle, False, False, 0)
        root.pack_start(header, False, False, 0)

        # Card 1: Layouts & Switching
        layout_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        add_class(layout_card, "card")
        root.pack_start(layout_card, False, False, 0)

        l_title = Gtk.Label(label="Раскладки и переключение", xalign=0)
        add_class(l_title, "card-title")
        layout_card.pack_start(l_title, False, False, 0)

        # Layouts entry
        l_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        l_lbl = Gtk.Label(label="Активные раскладки:", xalign=0)
        self.entry_layouts = Gtk.Entry()
        self.entry_layouts.set_text(self.keyboard_layouts)
        l_box.pack_start(l_lbl, False, False, 0)
        l_box.pack_start(self.entry_layouts, True, True, 0)
        layout_card.pack_start(l_box, False, False, 0)

        # Presets
        presets_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        p_lbl = Gtk.Label(label="Быстрые пресеты:")
        presets_box.pack_start(p_lbl, False, False, 0)

        def set_preset(text: str) -> None:
            self.entry_layouts.set_text(text)

        for p_name, p_val in [("US + RU", "us,ru"), ("US + UA", "us,ua"), ("US + KZ", "us,kz"), ("US Only", "us")]:
            btn = Gtk.Button(label=p_name)
            btn.connect("clicked", lambda _, val=p_val: set_preset(val))
            presets_box.pack_start(btn, False, False, 0)
        layout_card.pack_start(presets_box, False, False, 0)

        # Switch key combo
        switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        sw_lbl = Gtk.Label(label="Комбинация для смены языка:", xalign=0)
        self.switch_combo = Gtk.ComboBoxText()
        self.switch_options = [
            ("grp:win_space_toggle", "Win + Space (По умолчанию)"),
            ("grp:alt_shift_toggle", "Alt + Shift"),
            ("grp:ctrl_shift_toggle", "Ctrl + Shift"),
            ("grp:caps_toggle", "Caps Lock"),
        ]
        active_idx = 0
        for idx, (opt, desc) in enumerate(self.switch_options):
            self.switch_combo.append_text(desc)
            if opt == self.keyboard_switch_option:
                active_idx = idx
        self.switch_combo.set_active(active_idx)
        switch_box.pack_start(sw_lbl, False, False, 0)
        switch_box.pack_start(self.switch_combo, True, True, 0)
        layout_card.pack_start(switch_box, False, False, 0)

        # Card 2: Key Repeat & Latency
        repeat_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        add_class(repeat_card, "card")
        root.pack_start(repeat_card, False, False, 0)

        r_title = Gtk.Label(label="Отклик клавиатуры и автоповтор (xset rate)", xalign=0)
        add_class(r_title, "card-title")
        r_sub = Gtk.Label(label="Оптимизация задержки нажатия клавиш для быстрой печати и игр", xalign=0)
        add_class(r_sub, "card-subtitle")
        repeat_card.pack_start(r_title, False, False, 0)
        repeat_card.pack_start(r_sub, False, False, 0)

        # Delay
        delay_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        delay_lbl = Gtk.Label(label="Задержка перед повтором (Delay):", xalign=0)
        delay_lbl.set_size_request(240, -1)
        self.delay_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 150, 600, 10)
        self.delay_scale.set_value(self.keyboard_repeat_delay)
        self.delay_scale.set_hexpand(True)
        self.delay_val_lbl = Gtk.Label(label=f"{self.keyboard_repeat_delay} ms")
        add_class(self.delay_val_lbl, "badge-tag")
        self.delay_scale.connect("value-changed", lambda s: self.delay_val_lbl.set_text(f"{int(s.get_value())} ms"))

        delay_box.pack_start(delay_lbl, False, False, 0)
        delay_box.pack_start(self.delay_scale, True, True, 0)
        delay_box.pack_start(self.delay_val_lbl, False, False, 0)
        repeat_card.pack_start(delay_box, False, False, 0)

        # Rate
        rate_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        rate_lbl = Gtk.Label(label="Частота повтора (Repeat Rate):", xalign=0)
        rate_lbl.set_size_request(240, -1)
        self.rate_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 15, 60, 5)
        self.rate_scale.set_value(self.keyboard_repeat_rate)
        self.rate_scale.set_hexpand(True)
        self.rate_val_lbl = Gtk.Label(label=f"{self.keyboard_repeat_rate} cps")
        add_class(self.rate_val_lbl, "badge-tag")
        self.rate_scale.connect("value-changed", lambda s: self.rate_val_lbl.set_text(f"{int(s.get_value())} cps"))

        rate_box.pack_start(rate_lbl, False, False, 0)
        rate_box.pack_start(self.rate_scale, True, True, 0)
        rate_box.pack_start(self.rate_val_lbl, False, False, 0)
        repeat_card.pack_start(rate_box, False, False, 0)

        # Preset Gaming Button
        preset_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        opt_btn = Gtk.Button(label="⚡ Пресет сверх-быстрого отклика (280ms / 40cps)")
        opt_btn.connect("clicked", lambda _: (self.delay_scale.set_value(280), self.rate_scale.set_value(40)))
        preset_row.pack_start(opt_btn, False, False, 0)
        repeat_card.pack_start(preset_row, False, False, 0)

        # Test entry
        test_entry_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        test_entry_lbl = Gtk.Label(label="Тестовое поле для проверки скорости ввода:", xalign=0)
        add_class(test_entry_lbl, "card-subtitle")
        test_entry = Gtk.Entry()
        test_entry.set_placeholder_text("Зажмите любую клавишу здесь для проверки скорости повтора...")
        test_entry_box.pack_start(test_entry_lbl, False, False, 0)
        test_entry_box.pack_start(test_entry, False, False, 0)
        repeat_card.pack_start(test_entry_box, False, False, 0)

        # Apply button
        apply_kb_btn = Gtk.Button(label="Применить настройки клавиатуры")
        add_class(apply_kb_btn, "suggested-action")
        apply_kb_btn.connect("clicked", self.on_apply_keyboard_clicked)
        root.pack_start(apply_kb_btn, False, False, 0)

        return scrolled

    def on_apply_keyboard_clicked(self, _btn: Gtk.Button) -> None:
        layouts = self.entry_layouts.get_text().strip() or "us,ru"
        switch_idx = self.switch_combo.get_active()
        switch_opt = self.switch_options[switch_idx][0] if switch_idx >= 0 else "grp:win_space_toggle"
        delay = int(self.delay_scale.get_value())
        rate = int(self.rate_scale.get_value())

        self.keyboard_layouts = layouts
        self.keyboard_switch_option = switch_opt
        self.keyboard_repeat_delay = delay
        self.keyboard_repeat_rate = rate

        # Live apply
        run_command(["setxkbmap", "-layout", layouts, "-option", switch_opt])
        run_command(["xset", "r", "rate", str(delay), str(rate)])

        save_all_input_settings(self.devices, layouts, switch_opt, delay, rate)
        self.set_status("Настройки клавиатуры успешно применены и сохранены")

    # --------------------------------------------------------------------------
    # Page 3: Displays (Экраны и мониторы)
    # --------------------------------------------------------------------------
    def build_displays_page(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        add_class(root, "content-area")
        scrolled.add(root)

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        add_class(header, "page-header")
        title = Gtk.Label(label="Экраны и дисплеи", xalign=0)
        add_class(title, "page-title")
        subtitle = Gtk.Label(label="Подключенные мониторы, частота обновления и расположение", xalign=0)
        add_class(subtitle, "page-subtitle")
        header.pack_start(title, False, False, 0)
        header.pack_start(subtitle, False, False, 0)
        root.pack_start(header, False, False, 0)

        # Monitors Cards
        displays = get_connected_displays()
        for disp in displays:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            add_class(card, "card")

            top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            name_lbl = Gtk.Label(label=f"🖥️  {disp['name']}", xalign=0)
            add_class(name_lbl, "card-title")
            top_row.pack_start(name_lbl, False, False, 0)

            if disp["primary"]:
                prim_badge = Gtk.Label(label="Основной экран")
                add_class(prim_badge, "badge-green")
                top_row.pack_start(prim_badge, False, False, 0)

            rate_badge = Gtk.Label(label=disp["rate"])
            add_class(rate_badge, "badge-tag")
            top_row.pack_end(rate_badge, False, False, 0)
            card.pack_start(top_row, False, False, 0)

            geom_lbl = Gtk.Label(label=f"Геометрия и позиция: {disp['geom']}", xalign=0)
            add_class(geom_lbl, "card-subtitle")
            card.pack_start(geom_lbl, False, False, 0)

            root.pack_start(card, False, False, 0)

        # Action Buttons
        actions_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        add_class(actions_card, "card")
        root.pack_start(actions_card, False, False, 0)

        a_title = Gtk.Label(label="Управление конфигурацией экранов", xalign=0)
        add_class(a_title, "card-title")
        actions_card.pack_start(a_title, False, False, 0)

        btns_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        arandr_btn = Gtk.Button(label="🖥️ Открыть графический редактор экранов (ARandR)")
        arandr_btn.connect("clicked", lambda _: subprocess.Popen(["arandr"]))
        btns_box.pack_start(arandr_btn, False, False, 0)

        monitor_sh_btn = Gtk.Button(label="⚡ Переприменить авто-мониторы (monitor.sh)")
        monitor_sh_btn.connect("clicked", self.on_run_monitor_sh)
        btns_box.pack_start(monitor_sh_btn, False, False, 0)

        actions_card.pack_start(btns_box, False, False, 0)

        return scrolled

    def on_run_monitor_sh(self, _btn: Gtk.Button) -> None:
        script = HOME / ".config" / "i3" / "scripts" / "hardware" / "monitor.sh"
        if script.exists():
            run_command(["bash", str(script)])
            self.set_status("Скрипт monitor.sh успешно выполнен")

    # --------------------------------------------------------------------------
    # Page 4: Appearance & Themes (Внешний вид)
    # --------------------------------------------------------------------------
    def build_appearance_page(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        add_class(root, "content-area")
        scrolled.add(root)

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        add_class(header, "page-header")
        title = Gtk.Label(label="Внешний вид и темы", xalign=0)
        add_class(title, "page-title")
        subtitle = Gtk.Label(label="Управление темами оформления, курсорами и шрифтами", xalign=0)
        add_class(subtitle, "page-subtitle")
        header.pack_start(title, False, False, 0)
        header.pack_start(subtitle, False, False, 0)
        root.pack_start(header, False, False, 0)

        # Card 1: Themes
        theme_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        add_class(theme_card, "card")
        root.pack_start(theme_card, False, False, 0)

        t_title = Gtk.Label(label="Темы оформления (Hyprdots Rice)", xalign=0)
        add_class(t_title, "card-title")
        theme_card.pack_start(t_title, False, False, 0)

        cur_theme = get_current_theme()
        cur_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        cur_lbl = Gtk.Label(label="Текущая тема:", xalign=0)
        self.cur_theme_badge = Gtk.Label(label=cur_theme)
        add_class(self.cur_theme_badge, "badge-tag")
        cur_row.pack_start(cur_lbl, False, False, 0)
        cur_row.pack_start(self.cur_theme_badge, False, False, 0)
        theme_card.pack_start(cur_row, False, False, 0)

        themes_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.themes_combo = Gtk.ComboBoxText()
        all_themes = list_themes()
        active_t_idx = 0
        for idx, th in enumerate(all_themes):
            self.themes_combo.append_text(th)
            if th == cur_theme:
                active_t_idx = idx
        if all_themes:
            self.themes_combo.set_active(active_t_idx)
        themes_row.pack_start(self.themes_combo, True, True, 0)

        apply_t_btn = Gtk.Button(label="Применить тему")
        apply_t_btn.connect("clicked", self.on_apply_theme_clicked)
        themes_row.pack_start(apply_t_btn, False, False, 0)

        open_selector_btn = Gtk.Button(label="🎨 Галерея тем (Mod+T)")
        open_selector_btn.connect("clicked", lambda _: subprocess.Popen([str(HOME / ".config/i3/scripts/software/theme-select.sh")]))
        themes_row.pack_end(open_selector_btn, False, False, 0)
        theme_card.pack_start(themes_row, False, False, 0)

        # Card 2: Mouse Cursor
        cursor_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        add_class(cursor_card, "card")
        root.pack_start(cursor_card, False, False, 0)

        c_title = Gtk.Label(label="Курсор мыши", xalign=0)
        add_class(c_title, "card-title")
        cursor_card.pack_start(c_title, False, False, 0)

        c_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        c_lbl = Gtk.Label(label="Тема курсора:", xalign=0)
        self.cursor_entry = Gtk.Entry()
        self.cursor_entry.set_text("clay-dark-cursors")

        size_lbl = Gtk.Label(label="Размер:", xalign=0)
        self.cursor_size_combo = Gtk.ComboBoxText()
        for s in ["16", "24", "32", "48"]:
            self.cursor_size_combo.append_text(s)
        self.cursor_size_combo.set_active(1)  # 24

        c_row.pack_start(c_lbl, False, False, 0)
        c_row.pack_start(self.cursor_entry, True, True, 0)
        c_row.pack_start(size_lbl, False, False, 0)
        c_row.pack_start(self.cursor_size_combo, False, False, 0)
        cursor_card.pack_start(c_row, False, False, 0)

        save_cursor_btn = Gtk.Button(label="Сохранить настройки курсора в ~/.Xresources")
        save_cursor_btn.connect("clicked", self.on_save_cursor_clicked)
        cursor_card.pack_start(save_cursor_btn, False, False, 0)

        return scrolled

    def on_apply_theme_clicked(self, _btn: Gtk.Button) -> None:
        th = self.themes_combo.get_active_text()
        if th:
            script = HOME / ".config" / "i3" / "scripts" / "software" / "theme-apply.sh"
            theme_path = THEMES_DIR / th
            if script.exists() and theme_path.exists():
                subprocess.Popen([str(script), str(theme_path)])
                self.cur_theme_badge.set_text(th)
                self.set_status(f"Тема «{th}» применяется...")

    def on_save_cursor_clicked(self, _btn: Gtk.Button) -> None:
        th = self.cursor_entry.get_text().strip() or "clay-dark-cursors"
        sz = self.cursor_size_combo.get_active_text() or "24"
        lines = [
            "! === Xft Font Rendering Tweaks ===",
            "Xft.autohint:   0",
            "Xft.antialias:  1",
            "Xft.hinting:    1",
            "Xft.hintstyle:  hintslight",
            "Xft.rgba:       rgb",
            "Xft.lcdfilter:  lcddefault",
            "Xft.dpi:        96",
            "",
            "! === Xcursor Settings ===",
            f"Xcursor.theme:      {th}",
            f"Xcursor.size:       {sz}",
            "Xcursor.theme_core: true",
        ]
        XRESOURCES_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        run_command(["xrdb", "-merge", str(XRESOURCES_PATH)])
        self.set_status(f"Курсор {th} ({sz}px) сохранён и применён")

    # --------------------------------------------------------------------------
    # Page 5: Gaming & Compositor (Игровой режим & Picom)
    # --------------------------------------------------------------------------
    def build_gaming_page(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        add_class(root, "content-area")
        scrolled.add(root)

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        add_class(header, "page-header")
        title = Gtk.Label(label="Игровой режим и производительность", xalign=0)
        add_class(title, "page-title")
        subtitle = Gtk.Label(label="Управление задержками ввода (Input Lag) и композитором Picom", xalign=0)
        add_class(subtitle, "page-subtitle")
        header.pack_start(title, False, False, 0)
        header.pack_start(subtitle, False, False, 0)
        root.pack_start(header, False, False, 0)

        # Card 1: Picom
        p_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        add_class(p_card, "card")
        root.pack_start(p_card, False, False, 0)

        picom_running = run_command(["pgrep", "-x", "picom"]).returncode == 0
        self.picom_active = picom_running

        p_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        p_title = Gtk.Label(label="Композитор Picom (Тени, блюр, закругления):", xalign=0)
        add_class(p_title, "card-title")
        self.picom_badge = Gtk.Label(label="Включен" if picom_running else "Отключен")
        add_class(self.picom_badge, "badge-green" if picom_running else "badge-amber")

        self.switch_picom = Gtk.Switch()
        self.switch_picom.set_active(picom_running)
        self.switch_picom.connect("notify::active", self.on_picom_toggled)

        p_row.pack_start(p_title, False, False, 0)
        p_row.pack_start(self.picom_badge, False, False, 0)
        p_row.pack_end(self.switch_picom, False, False, 0)
        p_card.pack_start(p_row, False, False, 0)

        p_desc = Gtk.Label(
            label="💡 В соревновательных играх (CS2, Left 4 Dead 2, Apex) рекомендуется ОТКЛЮЧАТЬ Picom.\n"
                  "Это убирает наложение кадрового буфера композитора и снижает задержку ввода до чистого 0.\n"
                  "Быстрое переключение в любой момент: Mod + P.",
            xalign=0
        )
        add_class(p_desc, "card-subtitle")
        p_card.pack_start(p_desc, False, False, 0)

        # Card 2: Low-Latency Tweaks
        t_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        add_class(t_card, "card")
        root.pack_start(t_card, False, False, 0)

        t_title = Gtk.Label(label="Активные киберспортивные твики Xorg", xalign=0)
        add_class(t_title, "card-title")
        t_card.pack_start(t_title, False, False, 0)

        items = [
            ("Flat Mouse Acceleration (Raw 1:1)", "Включено", "Аппаратная акселерация мыши полностью отключена"),
            ("Отключение DPMS & Screen Blanking", "Включено", "Экраны не засыпают посреди игр или видео"),
            ("Быстрый отклик клавиатуры (280ms / 40cps)", "Включено", "Мгновенное срабатывание при зажатии клавиш"),
        ]
        for name, status, desc in items:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            add_class(row, "card-row")
            lbl_name = Gtk.Label(label=name, xalign=0)
            lbl_badge = Gtk.Label(label=status)
            add_class(lbl_badge, "badge-green")
            lbl_desc = Gtk.Label(label=f"— {desc}", xalign=0)
            add_class(lbl_desc, "card-subtitle")

            row.pack_start(lbl_name, False, False, 0)
            row.pack_start(lbl_badge, False, False, 0)
            row.pack_start(lbl_desc, False, False, 0)
            t_card.pack_start(row, False, False, 0)

        return scrolled

    def on_picom_toggled(self, switch: Gtk.Switch, _pspec: Any) -> None:
        active = switch.get_active()
        script = HOME / ".config" / "i3" / "scripts" / "software" / "toggle-picom.sh"
        if script.exists():
            subprocess.Popen([str(script)])
            self.picom_badge.set_text("Включен" if active else "Отключен")
            if active:
                remove_class(self.picom_badge, "badge-amber")
                add_class(self.picom_badge, "badge-green")
            else:
                remove_class(self.picom_badge, "badge-green")
                add_class(self.picom_badge, "badge-amber")
            self.set_status(f"Picom {'запущен' if active else 'остановлен (игровой режим)'}")

    # --------------------------------------------------------------------------
    # Page 6: Autostart (Автозапуск)
    # --------------------------------------------------------------------------
    def build_autostart_page(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        add_class(root, "content-area")
        scrolled.add(root)

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        add_class(header, "page-header")
        title = Gtk.Label(label="Автозапуск приложений", xalign=0)
        add_class(title, "page-title")
        subtitle = Gtk.Label(label="Программы и скрипты, запускаемые при старте сессии i3", xalign=0)
        add_class(subtitle, "page-subtitle")
        header.pack_start(title, False, False, 0)
        header.pack_start(subtitle, False, False, 0)
        root.pack_start(header, False, False, 0)

        # Parse i3 config autostarts
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        add_class(card, "card")
        root.pack_start(card, False, False, 0)

        c_title = Gtk.Label(label="Службы i3wm (~/.config/i3/config)", xalign=0)
        add_class(c_title, "card-title")
        card.pack_start(c_title, False, False, 0)

        autostart_items = [
            ("monitor.sh", "Автоматическая настройка мониторов и частоты обновления"),
            ("input.sh", "Оптимизация ввода, скорости мыши и клавиатуры"),
            ("polkit-agent.sh", "Агент аутентификации Polkit KDE"),
            ("dunst", "Сервис всплывающих уведомлений"),
            ("copyq", "Менеджер буфера обмена"),
            ("spice-vdagent", "Агент общего буфера обмена для виртуальных машин"),
            ("nm-applet", "Индикатор сети NetworkManager в трее"),
            ("theme-apply.sh", "Применение темы обоев, палитры Pywal и GTK"),
            ("autotiling", "Автоматическое чередование тайлинга окон i3"),
            ("launch.sh (eww)", "Верхняя и нижняя панели виджетов EWW"),
            ("picom", "Композитор эффектов и прозрачности"),
        ]

        for name, desc in autostart_items:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            add_class(row, "card-row")
            lbl_name = Gtk.Label(label=f"<b>{name}</b>", xalign=0)
            lbl_name.set_use_markup(True)
            lbl_desc = Gtk.Label(label=desc, xalign=0)
            add_class(lbl_desc, "card-subtitle")

            sw = Gtk.Switch()
            sw.set_active(True)
            sw.set_sensitive(False)  # Managed by i3 config

            row.pack_start(lbl_name, False, False, 0)
            row.pack_start(lbl_desc, True, True, 0)
            row.pack_end(sw, False, False, 0)
            card.pack_start(row, False, False, 0)

        return scrolled

    # --------------------------------------------------------------------------
    # Page 7: Shortcuts (Горячие клавиши)
    # --------------------------------------------------------------------------
    def build_shortcuts_page(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        add_class(root, "content-area")
        scrolled.add(root)

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        add_class(header, "page-header")
        title = Gtk.Label(label="Комбинации клавиш (i3 Keybindings)", xalign=0)
        add_class(title, "page-title")
        subtitle = Gtk.Label(label="Список основных хоткеев управления рабочим столом ($mod = Win/Super)", xalign=0)
        add_class(subtitle, "page-subtitle")
        header.pack_start(title, False, False, 0)
        header.pack_start(subtitle, False, False, 0)
        root.pack_start(header, False, False, 0)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        add_class(card, "card")
        root.pack_start(card, False, False, 0)

        shortcuts = [
            ("Mod + Return", "Открыть терминал Kitty"),
            ("Mod + D", "Меню запуска приложений Rofi"),
            ("Mod + T", "Выбор темы оформления (Hyprdots Selector)"),
            ("Mod + ,", "Параметры системы (Центр управления)"),
            ("Mod + B", "Запустить браузер (Zen Browser)"),
            ("Mod + C", "Менеджер буфера обмена CopyQ"),
            ("Mod + P", "Игровой режим (вкл/выкл Picom)"),
            ("Mod + Space", "Переключение языка клавиатуры (US / RU)"),
            ("Print", "Скриншот экрана в буфер и файл"),
            ("Shift + Print", "Скриншот выделенной области"),
            ("Mod + Shift + Q", "Закрыть активное окно"),
            ("Mod + Shift + R", "Перезагрузить i3 на лету"),
            ("Mod + 1..0", "Переключение на рабочий стол 1–10"),
            ("Mod + Shift + 1..0", "Перенос окна на рабочий стол 1–10"),
        ]

        for keys, action in shortcuts:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
            add_class(row, "card-row")
            lbl_key = Gtk.Label(label=keys, xalign=0)
            add_class(lbl_key, "badge-tag")
            lbl_key.set_size_request(160, -1)

            lbl_act = Gtk.Label(label=action, xalign=0)

            row.pack_start(lbl_key, False, False, 0)
            row.pack_start(lbl_act, True, True, 0)
            card.pack_start(row, False, False, 0)

        return scrolled

    # --------------------------------------------------------------------------
    # Page 8: About System (О системе - В стиле KDE Info Center)
    # --------------------------------------------------------------------------
    def build_about_page(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        add_class(root, "content-area")
        scrolled.add(root)

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        add_class(header, "page-header")
        title = Gtk.Label(label="О системе", xalign=0)
        add_class(title, "page-title")
        subtitle = Gtk.Label(label="Сведения об аппаратном и программном обеспечении", xalign=0)
        add_class(subtitle, "page-subtitle")
        header.pack_start(title, False, False, 0)
        header.pack_start(subtitle, False, False, 0)
        root.pack_start(header, False, False, 0)

        # Specs Card
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        add_class(card, "card")
        root.pack_start(card, False, False, 0)

        specs = get_system_specs()

        spec_items = [
            ("Операционная система", specs["os"]),
            ("Оконный менеджер", specs["wm"]),
            ("Ядро Linux", specs["kernel"]),
            ("Процессор (CPU)", specs["cpu"]),
            ("Видеокарта (GPU)", specs["gpu"]),
            ("Оперативная память (RAM)", specs["ram"]),
            ("Время работы (Uptime)", specs["uptime"]),
        ]

        for title_str, val_str in spec_items:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
            add_class(row, "card-row")
            lbl_t = Gtk.Label(label=f"<b>{title_str}</b>", xalign=0)
            lbl_t.set_use_markup(True)
            lbl_t.set_size_request(220, -1)

            lbl_v = Gtk.Label(label=val_str, xalign=0)
            lbl_v.set_selectable(True)

            row.pack_start(lbl_t, False, False, 0)
            row.pack_start(lbl_v, True, True, 0)
            card.pack_start(row, False, False, 0)

        # Rice Info Card
        rice_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        add_class(rice_card, "card")
        root.pack_start(rice_card, False, False, 0)

        r_title = Gtk.Label(label="🌌 Arch Linux Rice: i3-gaps + EWW + Picom", xalign=0)
        add_class(r_title, "card-title")
        r_sub = Gtk.Label(
            label="Конфигурация оптимизирована для сверхнизкого инпут-лага, киберспортивных шутеров и плавной работы.\n"
                  "Полная поддержка GNU Stow, автоматический инсталлятор и менеджер тем в стиле Hyprdots.",
            xalign=0
        )
        add_class(r_sub, "card-subtitle")
        rice_card.pack_start(r_title, False, False, 0)
        rice_card.pack_start(r_sub, False, False, 0)

        return scrolled

    # --------------------------------------------------------------------------
    # Status Bar
    # --------------------------------------------------------------------------
    def build_status_bar(self) -> Gtk.Box:
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        add_class(bar, "status-bar")

        bar.pack_start(self.status_lbl, True, True, 0)

        hint_lbl = Gtk.Label(label="Быстрый запуск: Mod+,")
        add_class(hint_lbl, "card-subtitle")
        bar.pack_end(hint_lbl, False, False, 0)

        return bar

    def set_status(self, text: str) -> None:
        self.status_lbl.set_text(text)


def main() -> None:
    load_css()
    win = ControlCenterWindow()
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
