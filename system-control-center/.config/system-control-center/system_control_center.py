#!/usr/bin/env python3
# ==============================================================================
# System Control Center — Google Material Design 3 (M3)
# Specification: https://m3.material.io/
# ==============================================================================

import colorsys
import configparser
import grp
import io
import json
import os
import platform
import pwd
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageOps

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

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
CURRENT_USER = os.environ.get("USER") or "fonera"
USER_ADMIN_HELPER_PATH = DATA_DIR / "user-admin-helper.sh"
AVATAR_SOURCE_PATH = DATA_DIR / "avatar_source.png"

# ==============================================================================
# Material Design 3 (M3) — Material You Dynamic Theming System
# Specification: https://m3.material.io/styles/color/roles
# ==============================================================================

def hex_to_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore

def rgb_to_hex(r: float, g: float, b: float) -> str:
    return f"#{int(round(max(0.0, min(1.0, r)) * 255)):02x}{int(round(max(0.0, min(1.0, g)) * 255)):02x}{int(round(max(0.0, min(1.0, b)) * 255)):02x}"

def hex_to_hsl(h: str) -> tuple[float, float, float]:
    r, g, b = hex_to_rgb(h)
    return colorsys.rgb_to_hls(r, g, b)

def hsl_to_hex(h: float, l: float, s: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h, max(0.0, min(1.0, l)), max(0.0, min(1.0, s)))
    return rgb_to_hex(r, g, b)

def get_m3_dynamic_palette() -> dict[str, Any]:
    """Generates canonical Google Material Design 3 (Material You) tokens from the wallpaper / Pywal palette."""
    wal_path = Path.home() / ".cache" / "wal" / "colors.json"
    data: dict[str, Any] = {}
    if wal_path.exists():
        try:
            with open(wal_path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

    colors = data.get("colors", {})
    special = data.get("special", {})

    bg_hex = special.get("background", colors.get("color0", "#111318"))
    fg_hex = special.get("foreground", colors.get("color15", "#e2e2e9"))

    # Choose best accent color from candidate palette
    candidate_keys = ["color4", "color2", "color5", "color1", "color6", "color3"]
    best_accent = "#a8c7fa"
    best_score = -1.0
    for k in candidate_keys:
        val = colors.get(k)
        if not val or not val.startswith("#") or len(val) < 7:
            continue
        h, l, s = hex_to_hsl(val)
        score = s * 1.5 + (0.5 - abs(l - 0.5))
        if score > best_score:
            best_score = score
            best_accent = val

    bg_h, bg_l, bg_s = hex_to_hsl(bg_hex)
    acc_h, acc_l, acc_s = hex_to_hsl(best_accent)

    sec_accent = colors.get("color2", colors.get("color5", best_accent))
    sec_h, sec_l, sec_s = hex_to_hsl(sec_accent)

    # In M3 dark theme, Primary has tone ~80% (lightness 0.78-0.82) for clear WCAG contrast
    primary = hsl_to_hex(acc_h, 0.80, max(acc_s, 0.65))
    on_primary = hsl_to_hex(acc_h, 0.14, max(acc_s, 0.65))
    primary_hover = hsl_to_hex(acc_h, 0.86, max(acc_s, 0.65))

    p_r, p_g, p_b = hex_to_rgb(primary)

    palette = {
        "surface": hsl_to_hex(bg_h, 0.08, min(bg_s, 0.18)),
        "surface_container_lowest": hsl_to_hex(bg_h, 0.05, min(bg_s, 0.18)),
        "surface_container_low": hsl_to_hex(bg_h, 0.11, min(bg_s, 0.18)),
        "surface_container": hsl_to_hex(bg_h, 0.14, min(bg_s, 0.16)),
        "surface_container_high": hsl_to_hex(bg_h, 0.17, min(bg_s, 0.16)),
        "surface_container_highest": hsl_to_hex(bg_h, 0.21, min(bg_s, 0.14)),

        "primary": primary,
        "on_primary": on_primary,
        "primary_hover": primary_hover,
        "primary_rgb": f"{int(p_r*255)}, {int(p_g*255)}, {int(p_b*255)}",

        "primary_container": hsl_to_hex(acc_h, 0.28, max(acc_s, 0.45)),
        "on_primary_container": hsl_to_hex(acc_h, 0.90, max(acc_s, 0.45)),

        "secondary": hsl_to_hex(sec_h, 0.76, min(sec_s, 0.50)),
        "secondary_container": hsl_to_hex(acc_h, 0.25, min(acc_s * 0.65, 0.35)),
        "on_secondary_container": hsl_to_hex(acc_h, 0.92, min(acc_s * 0.4, 0.25)),

        "on_surface": hsl_to_hex(bg_h, 0.92, min(bg_s * 0.2, 0.10)),
        "on_surface_variant": hsl_to_hex(bg_h, 0.68, min(bg_s * 0.3, 0.15)),
        "outline": hsl_to_hex(bg_h, 0.40, min(bg_s * 0.3, 0.15)),
        "outline_variant": hsl_to_hex(bg_h, 0.22, min(bg_s * 0.3, 0.12)),

        "error": "#f2b8b5",
        "on_error": "#601410",
        "error_container": "#8c1d18",
        "on_error_container": "#f9dedc",

        "seed_accent": best_accent,
        "wallpaper": data.get("wallpaper", "")
    }
    return palette

def generate_m3_css(p: dict[str, Any]) -> str:
    """Generates full Gtk3 CSS adhering strictly to Google Material Design 3 and Material You Dynamic Tokens."""
    return f"""
/* Material Design 3 (Google M3) Dynamic Material You Theme */
window.control-center-window {{
    background-color: {p['surface']};
    color: {p['on_surface']};
    font-family: "Roboto", "Noto Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}

/* Base widget reset to eliminate GTK default theme artifacts */
list,
list row,
list row:selected,
list row:selected:focus,
list row:selected:hover {{
    background-color: transparent;
    border: none;
    box-shadow: none;
    outline: none;
}}

scrolledwindow,
viewport {{
    background-color: {p['surface']};
    border: none;
    box-shadow: none;
    outline: none;
}}

.m3-nav-drawer scrolledwindow,
.m3-nav-drawer viewport {{
    background-color: transparent;
    border: none;
}}

/* --- M3 Navigation Drawer (Sidebar) --- */
.m3-nav-drawer {{
    background-color: {p['surface_container_low']};
    border-right: 1px solid rgba(255, 255, 255, 0.05);
    padding: 24px 16px;
}}

.m3-app-icon {{
    color: {p['primary']};
    margin-left: 4px;
}}

.m3-app-title {{
    font-size: 22px;
    font-weight: 700;
    color: {p['on_surface']};
    letter-spacing: -0.2px;
}}

.m3-app-subtitle {{
    font-size: 12px;
    color: {p['on_surface_variant']};
    margin-bottom: 20px;
}}

/* M3 Search Bar (surface-container-high) */
.m3-search {{
    background-color: {p['surface_container_high']};
    color: {p['on_surface']};
    border-radius: 9999px;
    border: 1px solid {p['outline_variant']};
    padding: 10px 16px;
    font-size: 13px;
    margin-bottom: 18px;
    box-shadow: none;
}}

.m3-search:focus {{
    background-color: {p['surface_container_highest']};
    border-color: {p['primary']};
    box-shadow: 0 0 0 1px {p['primary']};
}}

.m3-search image,
.m3-search image.left {{
    margin-right: 12px;
    margin-left: 2px;
}}

/* M3 Drawer Category Section Headers (Overlines) */
.m3-drawer-category {{
    font-size: 11px;
    font-weight: 700;
    color: {p['primary']};
    letter-spacing: 0.6px;
    padding: 16px 14px 6px 14px;
}}

/* M3 Navigation Pill */
.m3-drawer-item {{
    padding: 12px 18px;
    border-radius: 9999px;
    color: {p['on_surface_variant']};
    font-size: 14px;
    font-weight: 500;
    margin: 2px 0;
    background-color: transparent;
    transition: background-color 150ms ease, color 150ms ease;
}}

.m3-drawer-item image {{
    color: {p['on_surface_variant']};
}}

.m3-drawer-item:hover {{
    background-color: rgba(255, 255, 255, 0.08);
    color: {p['on_surface']};
}}

.m3-drawer-item:hover image {{
    color: {p['on_surface']};
}}

.m3-drawer-item.active,
.m3-drawer-item.active:selected,
.m3-drawer-item.active:focus {{
    background-color: {p['secondary_container']};
    color: {p['on_secondary_container']};
    font-weight: 600;
}}

.m3-drawer-item.active image,
.m3-drawer-item.active:selected image,
.m3-drawer-item.active:focus image {{
    color: {p['on_secondary_container']};
}}

/* --- M3 Content Surface --- */
.content-area {{
    padding: 36px 44px;
    background-color: {p['surface']};
}}

.page-header {{
    margin-bottom: 28px;
}}

.page-title {{
    font-size: 30px;
    font-weight: 700;
    color: {p['on_surface']};
    letter-spacing: -0.3px;
}}

.page-subtitle {{
    font-size: 14px;
    color: {p['on_surface_variant']};
    margin-top: 6px;
}}

/* --- M3 Section Header (Overline) --- */
.section-header-label {{
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: {p['primary']};
    margin-left: 8px;
    margin-bottom: 10px;
    margin-top: 14px;
}}

/* --- M3 Cards (Surface Container) --- */
.card {{
    background-color: {p['surface_container']};
    border-radius: 24px;
    border: 1px solid {p['outline_variant']};
    padding: 24px 28px;
    margin-bottom: 22px;
}}

.card-title {{
    font-size: 16px;
    font-weight: 600;
    color: {p['on_surface']};
}}

.card-subtitle {{
    font-size: 13px;
    color: {p['on_surface_variant']};
    margin-top: 4px;
    margin-bottom: 18px;
}}

.card-row {{
    padding: 14px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}}

.card-row:last-child {{
    border-bottom: none;
}}

separator.card-divider {{
    background-color: {p['outline_variant']};
    min-height: 1px;
    margin: 18px 0;
    border: none;
}}

.card-row-title {{
    font-size: 15px;
    font-weight: 500;
    color: {p['on_surface']};
}}

.card-row-subtitle {{
    font-size: 13px;
    color: {p['on_surface_variant']};
    margin-top: 3px;
}}

/* --- M3 Segmented Button --- */
.m3-segmented-box {{
    background-color: {p['surface_container_low']};
    border: 1px solid {p['outline_variant']};
    border-radius: 9999px;
    padding: 4px;
}}

.m3-segment-btn {{
    border-radius: 9999px;
    padding: 9px 26px;
    font-size: 13px;
    font-weight: 500;
    color: {p['on_surface_variant']};
    background-color: transparent;
    border: none;
    box-shadow: none;
    transition: all 150ms ease;
}}

.m3-segment-btn:hover {{
    background-color: rgba(255, 255, 255, 0.08);
    color: {p['on_surface']};
}}

.m3-segment-btn.active {{
    background-color: {p['secondary_container']};
    color: {p['on_secondary_container']};
    font-weight: 600;
}}

/* --- M3 Canonical Buttons --- */
button.suggested-action,
.btn-primary {{
    background-color: {p['primary']};
    color: {p['on_primary']};
    font-weight: 600;
    font-size: 13px;
    border-radius: 9999px;
    padding: 10px 24px;
    border: none;
    box-shadow: none;
}}

button.suggested-action:hover,
.btn-primary:hover {{
    background-color: {p['primary_hover']};
    color: {p['on_primary']};
}}

button,
.btn-tonal {{
    background-color: {p['surface_container_high']};
    color: {p['on_surface']};
    font-weight: 500;
    font-size: 13px;
    border-radius: 9999px;
    padding: 9px 20px;
    border: 1px solid {p['outline_variant']};
    box-shadow: none;
}}

button:hover,
.btn-tonal:hover {{
    background-color: {p['surface_container_highest']};
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.16);
}}

.btn-outlined {{
    background-color: transparent;
    color: {p['primary']};
    font-weight: 500;
    font-size: 13px;
    border-radius: 9999px;
    padding: 8px 20px;
    border: 1px solid {p['outline']};
    box-shadow: none;
}}

.btn-outlined:hover {{
    background-color: rgba({p['primary_rgb']}, 0.08);
    border-color: {p['primary']};
}}

/* --- Destructive Action / Danger Button --- */
button.destructive-action,
.btn-danger {{
    background-color: #ba1a1a;
    color: #ffffff;
    font-weight: 600;
    font-size: 13px;
    border-radius: 9999px;
    padding: 8px 18px;
    border: none;
    box-shadow: none;
}}

button.destructive-action:hover,
.btn-danger:hover {{
    background-color: #de3730;
    color: #ffffff;
}}

/* --- M3 Chips & Badges --- */
.badge-tag,
.m3-chip {{
    background-color: {p['surface_container_high']};
    border: 1px solid {p['outline_variant']};
    color: {p['primary']};
    border-radius: 9999px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 600;
}}

.badge-green,
.m3-chip-success {{
    background-color: rgba(76, 175, 80, 0.14);
    border: 1px solid rgba(76, 175, 80, 0.35);
    color: #81c784;
    border-radius: 9999px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 600;
}}

.badge-amber,
.m3-chip-warning {{
    background-color: rgba(255, 152, 0, 0.14);
    border: 1px solid rgba(255, 152, 0, 0.35);
    color: #ffb74d;
    border-radius: 9999px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 600;
}}

.m3-chip-error {{
    background-color: rgba(242, 184, 181, 0.14);
    border: 1px solid rgba(242, 184, 181, 0.35);
    color: #f2b8b5;
    border-radius: 9999px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 600;
}}

/* --- M3 Avatar Frame & Interactive Button --- */
.avatar-frame {{
    border-radius: 9999px;
    border: 2px solid {p['outline_variant']};
    padding: 3px;
    background-color: {p['surface_container_high']};
}}

button.avatar-btn {{
    background: transparent;
    background-color: transparent;
    border-radius: 9999px;
    padding: 2px;
    border: none;
    box-shadow: none;
    transition: all 180ms ease;
}}

button.avatar-btn:hover {{
    background: transparent;
    background-color: transparent;
    box-shadow: 0 0 0 4px rgba({p['primary_rgb']}, 0.25);
}}

button.avatar-btn:active {{
    box-shadow: 0 0 0 6px rgba({p['primary_rgb']}, 0.40);
}}

.avatar-edit-badge {{
    background-color: {p['primary']};
    color: {p['on_primary']};
    border-radius: 9999px;
    padding: 6px;
    border: 2px solid {p['surface_container']};
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
}}

button.avatar-btn:hover .avatar-edit-badge {{
    background-color: {p['primary_hover']};
}}

/* --- M3 Controls & Inputs --- */
entry {{
    background-color: {p['surface_container_highest']};
    color: {p['on_surface']};
    border-radius: 12px;
    border: 1px solid {p['outline_variant']};
    padding: 9px 16px;
    box-shadow: none;
}}

entry:focus {{
    border-color: {p['primary']};
    background-color: {p['surface_container_highest']};
    box-shadow: 0 0 0 1px {p['primary']};
}}

combobox button.combo {{
    background-color: {p['surface_container_high']};
    color: {p['on_surface']};
    border-radius: 12px;
    border: 1px solid {p['outline_variant']};
    padding: 8px 16px;
    box-shadow: none;
}}

combobox button.combo:hover {{
    border-color: {p['outline']};
    background-color: {p['surface_container_highest']};
}}

/* --- M3 Switch --- */
switch {{
    border-radius: 9999px;
    background-color: {p['surface_container_highest']};
    border: 1px solid {p['outline']};
    min-width: 52px;
    min-height: 28px;
    padding: 2px;
    box-shadow: none;
}}

switch:checked {{
    background-color: {p['primary']};
    border-color: {p['primary']};
}}

switch slider {{
    border-radius: 9999px;
    background-color: {p['outline']};
    min-width: 18px;
    min-height: 18px;
    margin: 3px;
    box-shadow: none;
}}

switch:checked slider {{
    background-color: {p['on_primary']};
    min-width: 22px;
    min-height: 22px;
    margin: 1px;
}}

/* --- M3 Sliders --- */
scale trough {{
    background-color: {p['surface_container_highest']};
    border-radius: 9999px;
    min-height: 8px;
    border: none;
    box-shadow: none;
}}

scale highlight {{
    background-color: {p['primary']};
    border-radius: 9999px;
    min-height: 8px;
    border: none;
    box-shadow: none;
}}

scale slider {{
    background-color: {p['primary']};
    background-image: none;
    border-radius: 9999px;
    border: none;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.45);
    min-width: 20px;
    min-height: 20px;
    margin: -6px 0;
}}

scale slider:hover {{
    background-color: {p['primary_hover']};
    box-shadow: 0 0 0 6px rgba({p['primary_rgb']}, 0.18);
}}

/* --- M3 Test Pad --- */
.test-pad {{
    background-color: {p['surface_container_low']};
    border: 1px solid {p['outline_variant']};
    border-radius: 18px;
    padding: 24px;
}}

.test-pad:hover {{
    border-color: {p['outline']};
    background-color: {p['surface_container']};
}}

.mouse-btn-indicator {{
    padding: 7px 18px;
    border-radius: 9999px;
    font-size: 13px;
    font-weight: 600;
    background-color: {p['surface_container_high']};
    border: 1px solid {p['outline_variant']};
    color: {p['on_surface_variant']};
}}

.mouse-btn-indicator.active {{
    background-color: {p['primary']};
    border-color: {p['primary']};
    color: {p['on_primary']};
    font-weight: 700;
}}

/* Status Bar */
.status-bar {{
    background-color: {p['surface_container_low']};
    border-top: 1px solid {p['outline_variant']};
    padding: 12px 32px;
}}
"""

CURRENT_CSS_PROVIDER: Gtk.CssProvider | None = None
CURRENT_PALETTE: dict[str, Any] = {}

def apply_m3_theme() -> dict[str, Any]:
    """Applies dynamic Material Design 3 tokens to the active GTK style provider."""
    global CURRENT_CSS_PROVIDER, CURRENT_PALETTE
    CURRENT_PALETTE = get_m3_dynamic_palette()
    css_content = generate_m3_css(CURRENT_PALETTE)
    if CURRENT_CSS_PROVIDER is None:
        CURRENT_CSS_PROVIDER = Gtk.CssProvider()
        screen = Gdk.Screen.get_default()
        if screen:
            Gtk.StyleContext.add_provider_for_screen(
                screen,
                CURRENT_CSS_PROVIDER,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
    CURRENT_CSS_PROVIDER.load_from_data(css_content.encode("utf-8"))
    return CURRENT_PALETTE

def load_css() -> None:
    apply_m3_theme()

def add_class(widget: Gtk.Widget, *classes: str) -> Gtk.Widget:
    ctx = widget.get_style_context()
    for c in classes:
        ctx.add_class(c)
    return widget

def remove_class(widget: Gtk.Widget, *classes: str) -> Gtk.Widget:
    ctx = widget.get_style_context()
    for c in classes:
        ctx.remove_class(c)
    return widget

def ensure_dirs() -> None:
    for path in (CONFIG_HOME, DATA_DIR, BACKUPS_DIR, AUTOSTART_DIR):
        path.mkdir(parents=True, exist_ok=True)

def create_app_icon_widget(icon_name_or_path: str, size: int = 24) -> Gtk.Widget:
    if icon_name_or_path:
        p = Path(icon_name_or_path)
        if p.is_file():
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(p), size, size, True)
                return Gtk.Image.new_from_pixbuf(pixbuf)
            except Exception:
                pass
        for ext in ["", ".png", ".svg", ".xpm"]:
            pix_p = Path("/usr/share/pixmaps") / f"{icon_name_or_path}{ext}"
            if pix_p.is_file():
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(pix_p), size, size, True)
                    return Gtk.Image.new_from_pixbuf(pixbuf)
                except Exception:
                    pass
        clean_name = icon_name_or_path.removesuffix(".png").removesuffix(".svg")
        theme = Gtk.IconTheme.get_default()
        if clean_name and theme.has_icon(clean_name):
            return Gtk.Image.new_from_icon_name(clean_name, Gtk.IconSize.LARGE_TOOLBAR)
    return Gtk.Image.new_from_icon_name("application-x-executable-symbolic", Gtk.IconSize.LARGE_TOOLBAR)

def run_command(command: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=check)

# ==============================================================================
# Device Models & State
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

    profile_str = props.get("libinput Accel Profile Enabled", "1, 0, 0")
    is_flat = profile_str.startswith("0, 1") or profile_str == "0 1 0"
    profile = "flat" if is_flat else "adaptive"
    supports_profiles = "libinput Accel Profiles Available" in props

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
    if dev.supports_profiles:
        profile_vals = ["0", "1", "0"] if dev.accel_profile == "flat" else ["1", "0", "0"]
        run_command(["xinput", "set-prop", str(dev.id), "libinput Accel Profile Enabled"] + profile_vals)
    run_command(["xinput", "set-prop", str(dev.id), "libinput Accel Speed", f"{dev.accel_speed:.2f}"])
    run_command(["xinput", "set-prop", str(dev.id), "libinput Natural Scrolling Enabled", "1" if dev.natural_scrolling else "0"])
    run_command(["xinput", "set-prop", str(dev.id), "libinput Left Handed Enabled", "1" if dev.left_handed else "0"])
    run_command(["xinput", "set-prop", str(dev.id), "libinput Middle Emulation Enabled", "1" if dev.middle_emulation else "0"])

def save_all_input_settings(devices: list[PointerDevice], layouts: str, switch_option: str, repeat_delay: int, repeat_rate: int) -> None:
    ensure_dirs()
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

    lines = [
        "#!/usr/bin/env bash",
        "# ==============================================================================",
        "# Auto-generated by System Control Center (Google Material Design 3)",
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
    specs["os"] = "Arch Linux x86_64"
    specs["kernel"] = platform.release()
    try:
        specs["uptime"] = run_command(["uptime", "-p"]).stdout.replace("up ", "").strip()
    except Exception:
        specs["uptime"] = "Неизвестно"

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

    wm_str = "i3-wm"
    try:
        res = run_command(["i3", "--version"])
        if res.returncode == 0:
            m = re.search(r"i3 version ([\d.]+)", res.stdout)
            if m:
                wm_str = f"i3-wm v{m.group(1)}"
            else:
                wm_str = "i3-wm"
    except Exception:
        pass

    display_server = "X11"
    try:
        if os.environ.get("WAYLAND_DISPLAY"):
            display_server = "Wayland"
        else:
            res = run_command(["pacman", "-Q", "xlibre-xserver"])
            if res.returncode == 0:
                display_server = "XLibre X11 Server"
            else:
                res2 = run_command(["pacman", "-Q", "xorg-server"])
                if res2.returncode == 0:
                    display_server = "Xorg X11 Server"
    except Exception:
        pass

    specs["wm"] = f"{wm_str} ({display_server})"
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
            for line in current_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("NAME="):
                    val = line.split("=", 1)[1].strip("\"' ")
                    clean = re.sub(r"^[^\w\s]+\s*", "", val).strip()
                    return clean or val
                if line.startswith("WALLPAPER="):
                    p = Path(line.split("=", 1)[1].strip("\"' "))
                    return p.parent.name
        except Exception:
            pass
    return "ghibli-serenity"

# ==============================================================================
# Unified Systemwide Cursor Management Backend
# ==============================================================================

def get_installed_cursor_themes() -> list[dict[str, str]]:
    """Scan system and user icon directories for installed X11/Wayland cursor themes."""
    search_dirs = [
        Path("/usr/share/icons"),
        HOME / ".local" / "share" / "icons",
        HOME / ".icons",
    ]
    seen = set()
    themes: list[dict[str, str]] = []
    
    priority_order = {
        "Bibata-Modern-Classic": 10,
        "Bibata-Modern-Ice": 20,
        "Bibata-Modern-Amber": 30,
        "Bibata-Original-Classic": 40,
        "Nordzy-cursors": 50,
        "capitaine-cursors": 60,
        "Vimix-cursors": 70,
        "breeze_cursors": 80,
    }

    for sdir in search_dirs:
        if not sdir.exists():
            continue
        try:
            for p in sorted(sdir.iterdir()):
                if not p.is_dir() or p.name in seen or p.name == "default":
                    continue
                cursors_dir = p / "cursors"
                if cursors_dir.is_dir():
                    seen.add(p.name)
                    title = p.name
                    comment = ""
                    index_file = p / "index.theme"
                    if index_file.exists():
                        try:
                            for line in index_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                                if line.startswith("Name=") and title == p.name:
                                    title = line.split("=", 1)[1].strip()
                                elif line.startswith("Comment=") and not comment:
                                    comment = line.split("=", 1)[1].strip()
                        except Exception:
                            pass
                    themes.append({
                        "id": p.name,
                        "name": title,
                        "comment": comment,
                        "path": str(p),
                    })
        except Exception:
            pass

    return sorted(themes, key=lambda x: (priority_order.get(x["id"], 100), x["name"].lower()))

def get_current_cursor_settings() -> tuple[str, int]:
    """Detect current system cursor theme and size."""
    theme = "Bibata-Modern-Classic"
    size = 24

    # 1. Check GSettings
    try:
        res = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", "cursor-theme"],
                             stdout=subprocess.PIPE, text=True, check=False)
        if res.returncode == 0:
            val = res.stdout.strip().strip("'\"")
            if val and val != "default":
                theme = val
    except Exception:
        pass

    try:
        res_sz = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", "cursor-size"],
                                stdout=subprocess.PIPE, text=True, check=False)
        if res_sz.returncode == 0:
            val_sz = int(res_sz.stdout.strip())
            if val_sz in (16, 24, 32, 48):
                size = val_sz
    except Exception:
        pass

    # 2. Check Xresources fallback
    if theme == "Bibata-Modern-Classic" and XRESOURCES_PATH.exists():
        try:
            for line in XRESOURCES_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.strip().startswith("Xcursor.theme:"):
                    val = line.split(":", 1)[1].strip()
                    if val:
                        theme = val
                elif line.strip().startswith("Xcursor.size:"):
                    try:
                        sz = int(line.split(":", 1)[1].strip())
                        if sz in (16, 24, 32, 48):
                            size = sz
                    except Exception:
                        pass
        except Exception:
            pass

    return theme, size

def apply_cursor_theme_systemwide(theme_id: str, size: int) -> tuple[bool, str]:
    """
    Atomically apply and synchronize cursor theme and size across all system components:
    X11 root, ~/.icons/default, ~/.local/share/icons/default, Xresources, GTK 2/3/4,
    GSettings, xsettingsd, environment variables, and systemd/dbus activation environments.
    """
    try:
        # 1. ~/.icons/default/index.theme
        p_icons = HOME / ".icons" / "default"
        p_icons.mkdir(parents=True, exist_ok=True)
        (p_icons / "index.theme").write_text(
            f"[Icon Theme]\nName=Default\nComment=Default Cursor Theme\nInherits={theme_id}\n",
            encoding="utf-8"
        )

        # 2. ~/.local/share/icons/default/index.theme
        p_local = HOME / ".local" / "share" / "icons" / "default"
        p_local.mkdir(parents=True, exist_ok=True)
        (p_local / "index.theme").write_text(
            f"[Icon Theme]\nName=Default\nComment=Default Cursor Theme\nInherits={theme_id}\n",
            encoding="utf-8"
        )

        # 3. ~/.Xresources
        if XRESOURCES_PATH.exists():
            lines = XRESOURCES_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
        else:
            lines = [
                "! === Xft Font Rendering Tweaks ===",
                "Xft.autohint:   0",
                "Xft.antialias:  1",
                "Xft.hinting:    1",
                "Xft.hintstyle:  hintslight",
                "Xft.rgba:       rgb",
                "Xft.lcdfilter:  lcddefault",
                "Xft.dpi:        96",
            ]
        new_lines = []
        found_theme = False
        found_size = False
        found_core = False
        for line in lines:
            sline = line.strip()
            if sline.startswith("Xcursor.theme:"):
                new_lines.append(f"Xcursor.theme:      {theme_id}")
                found_theme = True
            elif sline.startswith("Xcursor.size:"):
                new_lines.append(f"Xcursor.size:       {size}")
                found_size = True
            elif sline.startswith("Xcursor.theme_core:"):
                new_lines.append("Xcursor.theme_core: true")
                found_core = True
            else:
                new_lines.append(line)
        if not found_theme:
            new_lines.append(f"Xcursor.theme:      {theme_id}")
        if not found_size:
            new_lines.append(f"Xcursor.size:       {size}")
        if not found_core:
            new_lines.append("Xcursor.theme_core: true")
        XRESOURCES_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

        # 4. ~/.config/gtk-3.0/settings.ini and ~/.config/gtk-4.0/settings.ini
        def update_gtk_ini(path: Path) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            ini_lines = []
            if path.exists():
                ini_lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            out_lines = []
            has_theme = False
            has_size = False
            in_settings = False
            for l in ini_lines:
                sl = l.strip()
                if sl == "[Settings]":
                    in_settings = True
                    out_lines.append(l)
                    continue
                if sl.startswith("gtk-cursor-theme-name"):
                    out_lines.append(f"gtk-cursor-theme-name={theme_id}")
                    has_theme = True
                elif sl.startswith("gtk-cursor-theme-size"):
                    out_lines.append(f"gtk-cursor-theme-size={size}")
                    has_size = True
                else:
                    out_lines.append(l)
            if not in_settings:
                out_lines.insert(0, "[Settings]")
            if not has_theme:
                out_lines.append(f"gtk-cursor-theme-name={theme_id}")
            if not has_size:
                out_lines.append(f"gtk-cursor-theme-size={size}")
            path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

        update_gtk_ini(CONFIG_HOME / "gtk-3.0" / "settings.ini")
        update_gtk_ini(CONFIG_HOME / "gtk-4.0" / "settings.ini")

        # 5. ~/.gtkrc-2.0
        gtk2_path = HOME / ".gtkrc-2.0"
        gtk2_lines = []
        if gtk2_path.exists():
            gtk2_lines = gtk2_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        out_gtk2 = []
        has_t2 = False
        has_s2 = False
        for l in gtk2_lines:
            if "gtk-cursor-theme-name" in l:
                out_gtk2.append(f'gtk-cursor-theme-name="{theme_id}"')
                has_t2 = True
            elif "gtk-cursor-theme-size" in l:
                out_gtk2.append(f"gtk-cursor-theme-size={size}")
                has_s2 = True
            else:
                out_gtk2.append(l)
        if not has_t2:
            out_gtk2.append(f'gtk-cursor-theme-name="{theme_id}"')
        if not has_s2:
            out_gtk2.append(f"gtk-cursor-theme-size={size}")
        gtk2_path.write_text("\n".join(out_gtk2) + "\n", encoding="utf-8")

        # 6. ~/.config/xsettingsd/xsettingsd.conf
        xset_path = CONFIG_HOME / "xsettingsd" / "xsettingsd.conf"
        if xset_path.exists():
            xlines = xset_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            out_x = []
            has_ct = False
            has_cs = False
            for l in xlines:
                sl = l.strip()
                if sl.startswith("Gtk/CursorThemeName"):
                    out_x.append(f'Gtk/CursorThemeName "{theme_id}"')
                    has_ct = True
                elif sl.startswith("Gtk/CursorThemeSize"):
                    out_x.append(f"Gtk/CursorThemeSize {size}")
                    has_cs = True
                else:
                    out_x.append(l)
            if not has_ct:
                out_x.append(f'Gtk/CursorThemeName "{theme_id}"')
            if not has_cs:
                out_x.append(f"Gtk/CursorThemeSize {size}")
            xset_path.write_text("\n".join(out_x) + "\n", encoding="utf-8")

        # 7. ~/.xprofile
        xprof = HOME / ".xprofile"
        prof_lines = []
        if xprof.exists():
            prof_lines = xprof.read_text(encoding="utf-8", errors="ignore").splitlines()
        out_prof = []
        for l in prof_lines:
            if not l.startswith("export XCURSOR_THEME=") and not l.startswith("export XCURSOR_SIZE="):
                out_prof.append(l)
        out_prof.append(f'export XCURSOR_THEME="{theme_id}"')
        out_prof.append(f'export XCURSOR_SIZE="{size}"')
        xprof.write_text("\n".join(out_prof) + "\n", encoding="utf-8")

        # 8. Qt & KDE globals (~/.config/kdeglobals and ~/.config/kcminputrc)
        def update_kde_mouse(ini_path: Path) -> None:
            ini_path.parent.mkdir(parents=True, exist_ok=True)
            kcp = configparser.ConfigParser(interpolation=None)
            kcp.optionxform = str
            if ini_path.exists():
                try:
                    kcp.read(ini_path, encoding="utf-8")
                except Exception:
                    pass
            if "Mouse" not in kcp:
                kcp["Mouse"] = {}
            kcp["Mouse"]["cursorTheme"] = theme_id
            kcp["Mouse"]["cursorSize"] = str(size)
            try:
                with open(ini_path, "w", encoding="utf-8") as f:
                    kcp.write(f, space_around_delimiters=False)
            except Exception:
                pass

        update_kde_mouse(CONFIG_HOME / "kdeglobals")
        update_kde_mouse(CONFIG_HOME / "kcminputrc")

        # 9. Systemd User Environment (~/.config/environment.d/10-cursor.conf)
        env_d = CONFIG_HOME / "environment.d"
        env_d.mkdir(parents=True, exist_ok=True)
        try:
            (env_d / "10-cursor.conf").write_text(
                f"XCURSOR_THEME={theme_id}\nXCURSOR_SIZE={size}\n",
                encoding="utf-8"
            )
        except Exception:
            pass

        # 10. Environment & Live X11/D-Bus updates
        os.environ["XCURSOR_THEME"] = theme_id
        os.environ["XCURSOR_SIZE"] = str(size)

        subprocess.run(["gsettings", "set", "org.gnome.desktop.interface", "cursor-theme", theme_id], check=False)
        subprocess.run(["gsettings", "set", "org.gnome.desktop.interface", "cursor-size", str(size)], check=False)
        subprocess.run(["xrdb", "-merge", str(XRESOURCES_PATH)], check=False)
        subprocess.run(["xsetroot", "-cursor_name", "left_ptr"], check=False)
        subprocess.run(["killall", "-HUP", "xsettingsd"], check=False)
        subprocess.run(["systemctl", "--user", "import-environment", "XCURSOR_THEME", "XCURSOR_SIZE"], check=False)
        subprocess.run(["dbus-update-activation-environment", "--systemd", "XCURSOR_THEME", "XCURSOR_SIZE"], check=False)

        return True, f"Курсор «{theme_id}» ({size}px) успешно применён во всей системе"
    except Exception as e:
        return False, f"Ошибка применения курсора: {e}"

# ==============================================================================
# Autostart Manager Backend (Apps, i3 Session Scripts, Systemd User Services)
# ==============================================================================

SESSION_SCRIPTS: list[dict[str, str]] = [
    {
        "id": "monitor",
        "title": "Настройка дисплеев (monitor.sh)",
        "desc": "Автоматическое определение разрешения, ориентации и высокой частоты (144Hz)",
        "pattern": "scripts/hardware/monitor.sh",
        "cmd": str(HOME / ".config/i3/scripts/hardware/monitor.sh"),
        "proc": "monitor.sh",
        "icon": "video-display-symbolic",
    },
    {
        "id": "input",
        "title": "Настройка устройств ввода (input.sh)",
        "desc": "Оптимизация задержки, скорость автоповтора (280/40) и плоский профиль мыши",
        "pattern": "scripts/hardware/input.sh",
        "cmd": str(HOME / ".config/i3/scripts/hardware/input.sh"),
        "proc": "input.sh",
        "icon": "input-mouse-symbolic",
    },
    {
        "id": "polkit",
        "title": "Polkit агент аутентификации (polkit-agent.sh)",
        "desc": "Графические диалоговые окна запроса прав администратора (root)",
        "pattern": "scripts/software/polkit-agent.sh",
        "cmd": str(HOME / ".config/i3/scripts/software/polkit-agent.sh"),
        "proc": "polkit-kde-authentication-agent-1",
        "icon": "dialog-password-symbolic",
    },
    {
        "id": "theme",
        "title": "Применение темы оформления (theme-apply.sh)",
        "desc": "Установка обоев рабочего стола, генерация палитры Pywal и темы GTK",
        "pattern": "scripts/software/theme-apply.sh",
        "cmd": f"{HOME}/.config/i3/scripts/software/theme-apply.sh {HOME}/.config/themes/aruko",
        "proc": "theme-apply.sh",
        "icon": "preferences-desktop-appearance-symbolic",
    },
    {
        "id": "picom",
        "title": "Композитор окон (picom)",
        "desc": "Аппаратное сглаживание, тени, размытие и прозрачность окон",
        "pattern": "picom --config",
        "cmd": f"picom --config {HOME}/.config/picom/picom.conf -b",
        "proc": "picom",
        "icon": "applications-games-symbolic",
    },
    {
        "id": "eww",
        "title": "Панели рабочего стола (EWW)",
        "desc": "Верхняя и нижняя панели рабочего стола с индикаторами системы",
        "pattern": "eww/launch.sh",
        "cmd": f"{HOME}/.config/eww/launch.sh --restart",
        "proc": "eww",
        "icon": "view-paged-symbolic",
    },
    {
        "id": "autotiling",
        "title": "Автоматический тайлинг (autotiling)",
        "desc": "Умное чередование вертикального и горизонтального разделения окон",
        "pattern": "autotiling",
        "cmd": "autotiling",
        "proc": "autotiling",
        "icon": "view-grid-symbolic",
    },
    {
        "id": "dunst",
        "title": "Служба уведомлений (dunst)",
        "desc": "Всплывающие уведомления в стиле Material Design 3",
        "pattern": "exec --no-startup-id dunst",
        "cmd": "dunst",
        "proc": "dunst",
        "icon": "preferences-system-notifications-symbolic",
    },
    {
        "id": "copyq",
        "title": "Менеджер буфера обмена (copyq)",
        "desc": "История буфера обмена с поддержкой поиска и изображений (Mod+C)",
        "pattern": "exec --no-startup-id copyq",
        "cmd": "copyq",
        "proc": "copyq",
        "icon": "edit-paste-symbolic",
    },
    {
        "id": "nm-applet",
        "title": "Сетевой апплет NetworkManager",
        "desc": "Индикатор подключений Wi-Fi и проводной сети в системном лотке",
        "pattern": "exec --no-startup-id nm-applet",
        "cmd": "nm-applet",
        "proc": "nm-applet",
        "icon": "network-wired-symbolic",
    },
]

SYSTEMD_SERVICES: list[dict[str, str]] = [
    {
        "id": "gamemoded.service",
        "title": "GameMode Daemon (gamemoded)",
        "desc": "Оптимизация приоритета CPU, I/O и видеокарты при запуске игр",
        "icon": "applications-games-symbolic",
    },
    {
        "id": "reaper-discord-rpc.service",
        "title": "Reaper Discord Rich Presence",
        "desc": "Трансляция активного проекта Reaper DAW в статус профиля Discord",
        "icon": "audio-x-generic-symbolic",
    },
    {
        "id": "pipewire.service",
        "title": "PipeWire Audio Server",
        "desc": "Основной низколатентный мультимедийный сервер звука и видео",
        "icon": "audio-card-symbolic",
    },
    {
        "id": "wireplumber.service",
        "title": "WirePlumber Session Manager",
        "desc": "Модульный менеджер сессий и аудиоустройств PipeWire",
        "icon": "audio-volume-high-symbolic",
    },
    {
        "id": "pipewire-pulse.service",
        "title": "PipeWire PulseAudio Emulation",
        "desc": "Слой совместимости со старыми играми и приложениями PulseAudio",
        "icon": "audio-speakers-symbolic",
    },
    {
        "id": "telegraph-studio.service",
        "title": "Telegraph Studio Service",
        "desc": "Фоновая локальная служба публикации статей Telegraph",
        "icon": "text-html-symbolic",
    },
    {
        "id": "beszel-tunnel.service",
        "title": "Beszel Monitoring Tunnel",
        "desc": "Безопасный сетевой туннель мониторинга аппаратных ресурсов",
        "icon": "network-workgroup-symbolic",
    },
    {
        "id": "gemini-tunnel.service",
        "title": "Gemini HTTP Proxy Tunnel",
        "desc": "Локальный сетевой туннель прокси для LLM-инструментов",
        "icon": "system-search-symbolic",
    },
    {
        "id": "wivrn.service",
        "title": "WiVRn OpenXR Server",
        "desc": "Беспроводной OpenXR драйвер и сервис потоковой передачи для VR",
        "icon": "input-gaming-symbolic",
    },
]

def is_process_running(pattern: str) -> bool:
    try:
        r = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True, check=False)
        return r.returncode == 0
    except Exception:
        return False

def get_autostart_desktop_apps() -> list[dict[str, Any]]:
    apps: list[dict[str, Any]] = []
    if AUTOSTART_DIR.is_dir():
        for p in sorted(AUTOSTART_DIR.glob("*.desktop")):
            try:
                cp = configparser.ConfigParser(interpolation=None)
                cp.optionxform = str
                cp.read(p, encoding="utf-8")
                sec_name = "Desktop Entry"
                if sec_name not in cp:
                    for s in cp.sections():
                        if s.lower() == "desktop entry":
                            sec_name = s
                            break
                if sec_name in cp:
                    sec = cp[sec_name]
                    name = sec.get("Name") or sec.get("name") or p.stem
                    cmd = sec.get("Exec") or sec.get("exec") or ""
                    icon = sec.get("Icon") or sec.get("icon") or ""
                    comment = sec.get("Comment") or sec.get("comment") or ""
                    hidden = False
                    for hk in ["Hidden", "hidden"]:
                        if hk in sec:
                            hidden = sec.getboolean(hk, fallback=False)
                            break
                    gnome = True
                    for gk in ["X-GNOME-Autostart-enabled", "x-gnome-autostart-enabled"]:
                        if gk in sec:
                            gnome = sec.getboolean(gk, fallback=True)
                            break
                    enabled = (not hidden) and gnome
                    proc_key = cmd.split()[0] if cmd else name
                    proc_key = Path(proc_key).name
                    running = is_process_running(proc_key)
                    apps.append({
                        "path": p,
                        "name": name,
                        "exec": cmd,
                        "icon": icon,
                        "comment": comment,
                        "enabled": enabled,
                        "running": running,
                        "proc_key": proc_key,
                    })
            except Exception:
                pass
    return apps

def set_autostart_desktop_app_enabled(path: Path, enabled: bool) -> None:
    try:
        cp = configparser.ConfigParser(interpolation=None)
        cp.optionxform = str
        cp.read(path, encoding="utf-8")
        sec_name = "Desktop Entry"
        if sec_name not in cp:
            for s in cp.sections():
                if s.lower() == "desktop entry":
                    sec_name = s
                    break
        if sec_name not in cp:
            cp[sec_name] = {}

        # Normalize key casing to comply with Desktop Entry Specification
        if "Type" not in cp[sec_name] and "type" in cp[sec_name]:
            cp[sec_name]["Type"] = cp[sec_name].pop("type")
        elif "Type" not in cp[sec_name]:
            cp[sec_name]["Type"] = "Application"
        if "Name" not in cp[sec_name] and "name" in cp[sec_name]:
            cp[sec_name]["Name"] = cp[sec_name].pop("name")
        if "Exec" not in cp[sec_name] and "exec" in cp[sec_name]:
            cp[sec_name]["Exec"] = cp[sec_name].pop("exec")
        if "Icon" not in cp[sec_name] and "icon" in cp[sec_name]:
            cp[sec_name]["Icon"] = cp[sec_name].pop("icon")

        cp[sec_name]["Hidden"] = "false" if enabled else "true"
        cp[sec_name]["X-GNOME-Autostart-enabled"] = "true" if enabled else "false"
        if "hidden" in cp[sec_name]:
            del cp[sec_name]["hidden"]
        if "x-gnome-autostart-enabled" in cp[sec_name]:
            del cp[sec_name]["x-gnome-autostart-enabled"]

        with open(path, "w", encoding="utf-8") as f:
            cp.write(f, space_around_delimiters=False)
    except Exception:
        pass

def delete_autostart_desktop_app(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass

def add_autostart_desktop_app(name: str, exec_cmd: str, comment: str = "", icon: str = "") -> Path | None:
    AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^\w\-]+", "_", name.lower()).strip("_") or "custom_app"
    target = AUTOSTART_DIR / f"{slug}.desktop"
    idx = 1
    while target.exists():
        target = AUTOSTART_DIR / f"{slug}_{idx}.desktop"
        idx += 1
    icon_line = f"Icon={icon}\n" if icon else "Icon=application-x-executable\n"
    content = f"""[Desktop Entry]
Type=Application
Name={name}
Comment={comment or name}
Exec={exec_cmd}
{icon_line}Hidden=false
Terminal=false
X-GNOME-Autostart-enabled=true
"""
    try:
        target.write_text(content, encoding="utf-8")
        return target
    except Exception:
        return None

def list_installed_system_apps() -> list[dict[str, str]]:
    apps: list[dict[str, str]] = []
    seen: set[str] = set()
    search_dirs = [
        HOME / ".local/share/applications",
        Path("/usr/local/share/applications"),
        Path("/usr/share/applications"),
        Path("/var/lib/flatpak/exports/share/applications"),
        HOME / ".local/share/flatpak/exports/share/applications",
    ]
    for d in search_dirs:
        if d.is_dir():
            for p in sorted(d.glob("*.desktop")):
                try:
                    cp = configparser.ConfigParser(interpolation=None)
                    cp.optionxform = str
                    cp.read(p, encoding="utf-8")
                    sec_name = "Desktop Entry"
                    if sec_name not in cp:
                        for s in cp.sections():
                            if s.lower() == "desktop entry":
                                sec_name = s
                                break
                    if sec_name in cp:
                        sec = cp[sec_name]
                        nodisplay = False
                        for nd_key in ["NoDisplay", "nodisplay"]:
                            if nd_key in sec:
                                nodisplay = sec.getboolean(nd_key, fallback=False)
                                break
                        if nodisplay:
                            continue

                        name = sec.get("Name") or sec.get("name")
                        cmd = sec.get("Exec") or sec.get("exec")
                        icon = sec.get("Icon") or sec.get("icon") or "application-x-executable"
                        comment = sec.get("Comment") or sec.get("comment") or sec.get("GenericName") or sec.get("genericname") or ""

                        if name and cmd and name.strip() not in seen:
                            clean_name = name.strip()
                            seen.add(clean_name)
                            clean_cmd = " ".join([arg for arg in cmd.split() if not (arg.startswith("%") and len(arg) == 2)])
                            apps.append({
                                "name": clean_name,
                                "exec": clean_cmd,
                                "icon": icon.strip(),
                                "comment": comment.strip(),
                                "id": p.stem,
                            })
                except Exception:
                    pass
    return sorted(apps, key=lambda x: x["name"].lower())

def get_i3_autostart_status(pattern: str) -> bool:
    if not I3_CONFIG_PATH.exists():
        return False
    try:
        lines = I3_CONFIG_PATH.read_text(encoding="utf-8").splitlines()
        regex = re.compile(r"^\s*(#\s*)?(exec|exec_always)\b.*" + pattern)
        for l in lines:
            m = regex.match(l)
            if m:
                is_commented = bool(m.group(1))
                return not is_commented
    except Exception:
        pass
    return False

def set_i3_autostart_status(pattern: str, enabled: bool) -> bool:
    if not I3_CONFIG_PATH.exists():
        return False
    try:
        lines = I3_CONFIG_PATH.read_text(encoding="utf-8").splitlines()
        regex = re.compile(r"^(\s*)(#\s*)?((exec|exec_always)\b.*" + pattern + r".*)$")
        changed = False
        new_lines = []
        for l in lines:
            m = regex.match(l)
            if m:
                indent = m.group(1)
                is_commented = bool(m.group(2))
                exec_part = m.group(3)
                if enabled and is_commented:
                    new_lines.append(f"{indent}{exec_part}")
                    changed = True
                elif not enabled and not is_commented:
                    new_lines.append(f"{indent}# {exec_part}")
                    changed = True
                else:
                    new_lines.append(l)
            else:
                new_lines.append(l)
        if changed:
            I3_CONFIG_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            subprocess.run(["i3-msg", "reload"], check=False)
            dotfiles_i3 = HOME / "dotfiles" / "i3" / ".config" / "i3" / "config"
            if dotfiles_i3.exists():
                shutil.copy2(I3_CONFIG_PATH, dotfiles_i3)
        return changed
    except Exception:
        return False

def get_systemd_user_service_status(service_name: str) -> tuple[bool, bool]:
    is_enabled = False
    is_active = False
    try:
        r_en = subprocess.run(["systemctl", "--user", "is-enabled", service_name], capture_output=True, text=True, check=False)
        is_enabled = r_en.stdout.strip() == "enabled"
        r_act = subprocess.run(["systemctl", "--user", "is-active", service_name], capture_output=True, text=True, check=False)
        is_active = r_act.stdout.strip() == "active"
    except Exception:
        pass
    return is_enabled, is_active

def set_systemd_user_service_enabled(service_name: str, enabled: bool) -> None:
    action = "enable" if enabled else "disable"
    subprocess.run(["systemctl", "--user", action, service_name], check=False)

def set_systemd_user_service_active(service_name: str, start: bool) -> None:
    action = "start" if start else "stop"
    subprocess.run(["systemctl", "--user", action, service_name], check=False)

# ==============================================================================
# Profile & User Management Helpers
# ==============================================================================

def get_circular_avatar_pixbuf(path_str: str | Path | None, size: int = 96) -> GdkPixbuf.Pixbuf | None:
    """Creates a circular-cropped GdkPixbuf from an image file path with smooth anti-aliased edges."""
    if not path_str:
        return None
    p = Path(path_str).expanduser()
    if not p.is_file():
        return None
    try:
        im = Image.open(p).convert("RGBA")
        w, h = im.size
        min_dim = min(w, h)
        left = (w - min_dim) // 2
        top = (h - min_dim) // 2
        im = im.crop((left, top, left + min_dim, top + min_dim))
        im = im.resize((size, size), Image.Resampling.LANCZOS)

        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        im.putalpha(mask)

        bio = io.BytesIO()
        im.save(bio, format="PNG")
        data = bio.getvalue()

        loader = GdkPixbuf.PixbufLoader.new_with_type("png")
        loader.write(data)
        loader.close()
        return loader.get_pixbuf()
    except Exception:
        return None

def crop_and_mask_avatar(im: Image.Image, zoom: float = 1.0, offset_x: float = 0.0, offset_y: float = 0.0, size: int = 512) -> Image.Image:
    """Crops an image into a circle with specified zoom and offset factors."""
    im = im.convert("RGBA")
    w, h = im.size
    min_dim = min(w, h)
    side = min_dim / max(1.0, float(zoom))

    max_dx = (w - side) / 2.0
    max_dy = (h - side) / 2.0

    cx = (w / 2.0) + (float(offset_x) * max_dx)
    cy = (h / 2.0) + (float(offset_y) * max_dy)

    left = max(0.0, min(float(w - side), cx - side / 2.0))
    top = max(0.0, min(float(h - side), cy - side / 2.0))
    right = left + side
    bottom = top + side

    cropped = im.crop((int(round(left)), int(round(top)), int(round(right)), int(round(bottom))))
    cropped = cropped.resize((size, size), Image.Resampling.LANCZOS)

    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    cropped.putalpha(mask)
    return cropped

def render_cropped_pixbuf(im: Image.Image, zoom: float = 1.0, offset_x: float = 0.0, offset_y: float = 0.0, target_size: int = 180) -> GdkPixbuf.Pixbuf | None:
    """Renders a circular cropped GdkPixbuf for live preview."""
    try:
        masked = crop_and_mask_avatar(im, zoom, offset_x, offset_y, target_size)
        bio = io.BytesIO()
        masked.save(bio, format="PNG")
        loader = GdkPixbuf.PixbufLoader.new_with_type("png")
        loader.write(bio.getvalue())
        loader.close()
        return loader.get_pixbuf()
    except Exception:
        return None

def save_custom_cropped_avatar(im: Image.Image, zoom: float = 1.0, offset_x: float = 0.0, offset_y: float = 0.0, target_user: str = CURRENT_USER) -> bool:
    """Saves avatar cropped with user parameters to ~/.face, ~/.face.icon, and data dir."""
    try:
        cropped_highres = crop_and_mask_avatar(im, zoom, offset_x, offset_y, size=512)

        user_info = pwd.getpwnam(target_user)
        user_dir = Path(user_info.pw_dir)
        face_path = user_dir / ".face"
        face_icon_path = user_dir / ".face.icon"
        scc_avatar = DATA_DIR / "avatar.png"

        cropped_highres.save(face_path, format="PNG")
        cropped_highres.save(face_icon_path, format="PNG")
        cropped_highres.save(scc_avatar, format="PNG")

        face_path.chmod(0o644)
        face_icon_path.chmod(0o644)
        scc_avatar.chmod(0o644)
        return True
    except Exception:
        return False

def save_user_avatar(source_image_path: str | Path, target_user: str = CURRENT_USER) -> bool:
    """Crops an image into a high-res square and saves it as ~/.face, ~/.face.icon and app cache."""
    try:
        src = Path(source_image_path).expanduser()
        if not src.is_file():
            return False
        im = Image.open(src).convert("RGBA")
        return save_custom_cropped_avatar(im, zoom=1.0, offset_x=0.0, offset_y=0.0, target_user=target_user)
    except Exception:
        return False

def remove_user_avatar(target_user: str = CURRENT_USER) -> bool:
    """Removes avatar files for the given user."""
    try:
        user_info = pwd.getpwnam(target_user)
        user_dir = Path(user_info.pw_dir)
        for p in (user_dir / ".face", user_dir / ".face.icon", DATA_DIR / "avatar.png", AVATAR_SOURCE_PATH):
            if p.exists():
                p.unlink()
        return True
    except Exception:
        return False

def get_system_users() -> list[dict[str, Any]]:
    """Returns list of real human system user accounts (UID >= 1000)."""
    users: list[dict[str, Any]] = []
    wheel_members: set[str] = set()
    try:
        wheel_members = set(grp.getgrnam("wheel").gr_mem)
    except KeyError:
        pass
    try:
        sudo_members = set(grp.getgrnam("sudo").gr_mem)
        wheel_members.update(sudo_members)
    except KeyError:
        pass

    for u in pwd.getpwall():
        if u.pw_uid >= 1000 and u.pw_name != "nobody":
            is_admin = (u.pw_name in wheel_members) or (u.pw_name == CURRENT_USER)
            face_path = Path(u.pw_dir) / ".face"
            users.append({
                "name": u.pw_name,
                "uid": u.pw_uid,
                "gid": u.pw_gid,
                "gecos": u.pw_gecos,
                "dir": u.pw_dir,
                "shell": u.pw_shell,
                "is_admin": is_admin,
                "has_avatar": face_path.exists(),
                "avatar_path": str(face_path) if face_path.exists() else None,
            })
    return sorted(users, key=lambda x: (0 if x["name"] == CURRENT_USER else 1, x["uid"]))

def run_user_admin_cmd(*args: str) -> tuple[bool, str]:
    """Runs administrative user operations using pkexec and user-admin-helper.sh."""
    if not USER_ADMIN_HELPER_PATH.exists():
        return False, f"Файл {USER_ADMIN_HELPER_PATH} не найден"
    cmd = ["pkexec", str(USER_ADMIN_HELPER_PATH)] + list(args)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            return True, proc.stdout.strip()
        err = proc.stderr.strip() or proc.stdout.strip()
        if not err and proc.returncode in (126, 127):
            err = "Операция отменена пользователем (Polkit)"
        return False, err or f"Код ошибки {proc.returncode}"
    except Exception as e:
        return False, str(e)

# ==============================================================================
# Main Window (Material Design 3)
# ==============================================================================
class ControlCenterWindow(Gtk.Window):
    def __init__(self) -> None:
        super().__init__(title="Параметры системы")
        self.set_wmclass("system-control-center", "System-control-center")
        self.set_role("system-control-center")
        ensure_dirs()
        add_class(self, "control-center-window")
        self.set_default_size(1180, 780)
        self.set_position(Gtk.WindowPosition.CENTER)
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

        self.load_saved_profile()

        # Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_box)

        content_panes = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        main_box.pack_start(content_panes, True, True, 0)

        # M3 Navigation Drawer (Sidebar)
        self.sidebar_box = self.build_sidebar()
        content_panes.pack_start(self.sidebar_box, False, False, 0)

        # Right Stack Content
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(150)
        content_panes.pack_start(self.stack, True, True, 0)

        # Build Pages (Pure M3 Architecture — Symbolic Icons, No Emojis)
        self.page_mouse = self.build_mouse_page()
        self.page_keyboard = self.build_keyboard_page()
        self.page_displays = self.build_displays_page()
        self.page_gaming = self.build_gaming_page()
        self.page_appearance = self.build_appearance_page()
        self.page_autostart = self.build_autostart_page()
        self.page_shortcuts = self.build_shortcuts_page()
        self.page_profile = self.build_profile_page()
        self.page_about = self.build_about_page()

        self.stack.add_named(self.page_mouse, "mouse")
        self.stack.add_named(self.page_keyboard, "keyboard")
        self.stack.add_named(self.page_displays, "displays")
        self.stack.add_named(self.page_gaming, "gaming")
        self.stack.add_named(self.page_appearance, "appearance")
        self.stack.add_named(self.page_autostart, "autostart")
        self.stack.add_named(self.page_shortcuts, "shortcuts")
        self.stack.add_named(self.page_profile, "profile")
        self.stack.add_named(self.page_about, "about")

        # Bottom status bar
        self.status_bar = self.build_status_bar()
        main_box.pack_end(self.status_bar, False, False, 0)

        self.loading = False
        self.select_page("mouse")

        # Material You Dynamic Theming Monitor
        self.wal_colors_path = Path.home() / ".cache" / "wal" / "colors.json"
        self.last_wal_mtime = self.wal_colors_path.stat().st_mtime if self.wal_colors_path.exists() else 0.0
        GLib.timeout_add_seconds(2, self.check_wal_colors_updated)

    def check_wal_colors_updated(self) -> bool:
        if self.wal_colors_path.exists():
            try:
                mtime = self.wal_colors_path.stat().st_mtime
                if mtime > self.last_wal_mtime:
                    self.last_wal_mtime = mtime
                    self.reload_material_you_palette(notify=True)
            except Exception:
                pass
        return True

    def reload_material_you_palette(self, notify: bool = False) -> None:
        pal = apply_m3_theme()
        if hasattr(self, "m3_primary_badge") and self.m3_primary_badge:
            self.m3_primary_badge.set_text(f"Акцент: {pal['primary']}")
        if hasattr(self, "m3_surface_badge") and self.m3_surface_badge:
            self.m3_surface_badge.set_text(f"Фон: {pal['surface']}")
        if hasattr(self, "m3_wall_badge") and self.m3_wall_badge:
            wall_name = Path(pal.get("wallpaper", "")).name or "Обои рабочего стола"
            self.m3_wall_badge.set_text(wall_name)
        if hasattr(self, "cur_theme_badge") and self.cur_theme_badge:
            self.cur_theme_badge.set_text(get_current_theme())
        if notify:
            self.set_status(f"Палитра Material You синхронизирована (Акцент: {pal['primary']})")

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
    # M3 Navigation Drawer (Sidebar)
    # --------------------------------------------------------------------------
    def build_sidebar(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        add_class(box, "m3-nav-drawer")
        box.set_size_request(280, -1)

        # Header with App Icon and Titles
        head_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        head_icon = Gtk.Image.new_from_icon_name("preferences-system-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        add_class(head_icon, "m3-app-icon")

        titles_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title = Gtk.Label(label="Параметры", xalign=0)
        add_class(title, "m3-app-title")
        subtitle = Gtk.Label(label="Центр управления i3wm", xalign=0)
        add_class(subtitle, "m3-app-subtitle")
        titles_box.pack_start(title, False, False, 0)
        titles_box.pack_start(subtitle, False, False, 0)

        head_box.pack_start(head_icon, False, False, 0)
        head_box.pack_start(titles_box, True, True, 0)
        box.pack_start(head_box, False, False, 0)

        # M3 Search Bar
        self.search_entry = Gtk.SearchEntry()
        add_class(self.search_entry, "m3-search")
        self.search_entry.set_placeholder_text("  Поиск параметров...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        box.pack_start(self.search_entry, False, False, 0)

        # Items ListBox
        self.sidebar_list = Gtk.ListBox()
        self.sidebar_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.sidebar_list.connect("row-activated", self.on_sidebar_row_activated)

        # M3 Strict Navigation Structure (Icon name, Title, Page ID)
        self.sidebar_items = [
            ("HEADER", "Устройства ввода", None, None),
            ("ITEM", "Мышь и тачпад", "input-mouse-symbolic", "mouse"),
            ("ITEM", "Клавиатура", "input-keyboard-symbolic", "keyboard"),
            ("HEADER", "Оборудование и экран", None, None),
            ("ITEM", "Дисплеи", "video-display-symbolic", "displays"),
            ("ITEM", "Игровой режим и Picom", "applications-games-symbolic", "gaming"),
            ("HEADER", "Персонализация", None, None),
            ("ITEM", "Внешний вид", "preferences-desktop-appearance-symbolic", "appearance"),
            ("HEADER", "Рабочая среда", None, None),
            ("ITEM", "Автозапуск", "system-run-symbolic", "autostart"),
            ("ITEM", "Горячие клавиши", "preferences-desktop-keyboard-shortcuts-symbolic", "shortcuts"),
            ("HEADER", "Система и пользователи", None, None),
            ("ITEM", "Профиль и пользователи", "system-users-symbolic", "profile"),
            ("ITEM", "О системе", "help-about-symbolic", "about"),
        ]

        self.sidebar_rows: dict[str, Gtk.ListBoxRow] = {}

        for item_type, label, icon_name, page_name in self.sidebar_items:
            if item_type == "HEADER":
                h_label = Gtk.Label(label=label.upper(), xalign=0)
                add_class(h_label, "m3-drawer-category")
                row = Gtk.ListBoxRow()
                row.set_selectable(False)
                row.set_activatable(False)
                row.add(h_label)
                self.sidebar_list.add(row)
            else:
                row = Gtk.ListBoxRow()
                add_class(row, "m3-drawer-item")
                row.page_name = page_name  # type: ignore

                item_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
                if icon_name:
                    icon_img = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
                    item_box.pack_start(icon_img, False, False, 0)

                i_label = Gtk.Label(label=label, xalign=0)
                item_box.pack_start(i_label, True, True, 0)

                row.add(item_box)
                self.sidebar_list.add(row)
                if page_name:
                    self.sidebar_rows[page_name] = row

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.sidebar_list)
        box.pack_start(scrolled, True, True, 0)

        return box

    def on_sidebar_row_activated(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if row and hasattr(row, "page_name") and row.page_name:
            self.select_page(row.page_name)

    def select_page(self, page_name: str) -> None:
        self.stack.set_visible_child_name(page_name)
        for name, r in self.sidebar_rows.items():
            if name == page_name:
                add_class(r, "active")
            else:
                remove_class(r, "active")

    def on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        text = entry.get_text().lower().strip()
        for page_name, row in self.sidebar_rows.items():
            child = row.get_child()
            if isinstance(child, Gtk.Box):
                label_widget = child.get_children()[-1]
                if isinstance(label_widget, Gtk.Label):
                    visible = text in label_widget.get_text().lower() or text in page_name
                    row.set_visible(visible)

    # --------------------------------------------------------------------------
    # Page 1: Mouse & Touchpad (Google M3 Specifications)
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
        title = Gtk.Label(label="Мышь и тачпад", xalign=0)
        add_class(title, "page-title")
        subtitle = Gtk.Label(label="Настройка профиля ускорения, чувствительности и прокрутки", xalign=0)
        add_class(subtitle, "page-subtitle")
        header.pack_start(title, False, False, 0)
        header.pack_start(subtitle, False, False, 0)
        root.pack_start(header, False, False, 0)

        # Group 1: Core Parameters (Unified M3 Card)
        root.pack_start(self.build_section_header("Основные параметры"), False, False, 0)
        main_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        add_class(main_card, "card")
        root.pack_start(main_card, False, False, 0)

        # 1.1 Device Selector Row
        dev_title = Gtk.Label(label="Устройство указателя", xalign=0)
        add_class(dev_title, "card-title")
        main_card.pack_start(dev_title, False, False, 0)

        dev_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        dev_row.set_margin_top(8)
        self.device_combo = Gtk.ComboBoxText()
        for dev in self.devices:
            self.device_combo.append_text(f"{dev.name} (id={dev.id})")
        if self.devices:
            self.device_combo.set_active(0)
        self.device_combo.connect("changed", self.on_mouse_device_selected)
        dev_row.pack_start(self.device_combo, True, True, 0)

        refresh_btn = Gtk.Button(label="Обновить список")
        add_class(refresh_btn, "btn-tonal")
        refresh_btn.connect("clicked", self.on_refresh_mouse_devices)
        dev_row.pack_end(refresh_btn, False, False, 0)
        main_card.pack_start(dev_row, False, False, 0)

        main_card.pack_start(self.build_divider(), False, False, 0)

        # 1.2 Acceleration Profile (M3 Segmented Button)
        accel_title = Gtk.Label(label="Профиль ускорения курсора", xalign=0)
        add_class(accel_title, "card-title")
        self.accel_sub_desc = Gtk.Label(label="Выбор алгоритма реакции курсора на движение руки", xalign=0)
        add_class(self.accel_sub_desc, "card-subtitle")
        main_card.pack_start(accel_title, False, False, 0)
        main_card.pack_start(self.accel_sub_desc, False, False, 0)

        seg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        add_class(seg_box, "m3-segmented-box")

        self.btn_seg_flat = Gtk.Button(label="Без ускорения (Flat 1:1)")
        add_class(self.btn_seg_flat, "m3-segment-btn")
        self.btn_seg_flat.connect("clicked", lambda _: self.set_accel_profile("flat"))

        self.btn_seg_adaptive = Gtk.Button(label="Адаптивное (Adaptive)")
        add_class(self.btn_seg_adaptive, "m3-segment-btn")
        self.btn_seg_adaptive.connect("clicked", lambda _: self.set_accel_profile("adaptive"))

        seg_box.pack_start(self.btn_seg_flat, True, True, 0)
        seg_box.pack_start(self.btn_seg_adaptive, True, True, 0)
        main_card.pack_start(seg_box, False, False, 0)

        main_card.pack_start(self.build_divider(), False, False, 0)

        # 1.3 Pointer Speed & Sensitivity
        speed_title = Gtk.Label(label="Скорость указателя", xalign=0)
        add_class(speed_title, "card-title")
        speed_sub = Gtk.Label(label="Базовая чувствительность сенсора (от -1.00 до +1.00)", xalign=0)
        add_class(speed_sub, "card-subtitle")
        main_card.pack_start(speed_title, False, False, 0)
        main_card.pack_start(speed_sub, False, False, 0)

        speed_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        self.speed_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, -1.0, 1.0, 0.05)
        self.speed_scale.set_value(0.0)
        self.speed_scale.set_digits(2)
        self.speed_scale.set_hexpand(True)
        self.speed_scale.connect("value-changed", self.on_speed_scale_changed)

        self.speed_val_label = Gtk.Label(label="0.00")
        add_class(self.speed_val_label, "m3-chip")

        reset_speed_btn = Gtk.Button(label="Сброс")
        add_class(reset_speed_btn, "btn-tonal")
        reset_speed_btn.connect("clicked", lambda _: self.speed_scale.set_value(0.0))

        speed_row.pack_start(self.speed_scale, True, True, 0)
        speed_row.pack_start(self.speed_val_label, False, False, 0)
        speed_row.pack_start(reset_speed_btn, False, False, 0)
        main_card.pack_start(speed_row, False, False, 0)

        # Group 4: Scrolling & Buttons
        root.pack_start(self.build_section_header("Поведение и прокрутка"), False, False, 0)
        buttons_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        add_class(buttons_card, "card")
        root.pack_start(buttons_card, False, False, 0)

        # Row 1: Natural Scrolling
        row_natural = self.build_m3_switch_row(
            "Естественная прокрутка",
            "Инвертировать направление прокрутки колесика мыши",
            self.on_natural_switch_toggled,
        )
        self.switch_natural = row_natural.switch
        buttons_card.pack_start(row_natural.box, False, False, 0)

        # Row 2: Left-handed
        row_left = self.build_m3_switch_row(
            "Режим для левши",
            "Поменять местами левую и правую кнопки мыши",
            self.on_left_handed_switch_toggled,
        )
        self.switch_left = row_left.switch
        buttons_card.pack_start(row_left.box, False, False, 0)

        # Row 3: Middle Emulation
        row_mid = self.build_m3_switch_row(
            "Эмуляция средней кнопки",
            "Одновременное нажатие левой и правой кнопок работает как клик колесика",
            self.on_middle_emu_switch_toggled,
        )
        self.switch_middle = row_mid.switch
        buttons_card.pack_start(row_mid.box, False, False, 0)

        # Group 4: Cursor Theme & Size (Quick Link)
        root.pack_start(self.build_section_header("Курсор мыши во всей системе"), False, False, 0)
        mouse_cursor_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        add_class(mouse_cursor_card, "card")
        root.pack_start(mouse_cursor_card, False, False, 0)

        mc_head = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        mc_title = Gtk.Label(label="Системный указатель мыши", xalign=0)
        add_class(mc_title, "card-title")
        mc_sub = Gtk.Label(
            label="Синхронизирован один стиль и размер для рабочего стола, GTK, Chromium, Discord и Steam.",
            xalign=0,
        )
        add_class(mc_sub, "card-row-subtitle")
        mc_head.pack_start(mc_title, False, False, 0)
        mc_head.pack_start(mc_sub, False, False, 0)
        mouse_cursor_card.pack_start(mc_head, False, False, 0)

        mc_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        cur_c_th, cur_c_sz = get_current_cursor_settings()
        self.mouse_cursor_badge = Gtk.Label(label=f"Курсор: {cur_c_th} ({cur_c_sz}px)")
        add_class(self.mouse_cursor_badge, "m3-chip")
        mc_row.pack_start(self.mouse_cursor_badge, False, False, 0)

        btn_go_cursor = Gtk.Button(label="Выбрать тему и размер курсора (Внешний вид)")
        add_class(btn_go_cursor, "btn-tonal")
        btn_go_cursor.connect("clicked", lambda _: self.select_page("appearance"))
        mc_row.pack_end(btn_go_cursor, False, False, 0)
        mouse_cursor_card.pack_start(mc_row, False, False, 0)

        # Group 5: Interactive Test Area
        root.pack_start(self.build_section_header("Проверка параметров"), False, False, 0)
        test_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        add_class(test_card, "card")
        root.pack_start(test_card, False, False, 0)

        test_title = Gtk.Label(label="Тестовая область", xalign=0)
        add_class(test_title, "card-title")
        test_sub = Gtk.Label(label="Проверьте скорость движения курсора, срабатывание кнопок и прокрутку", xalign=0)
        add_class(test_sub, "card-subtitle")
        test_card.pack_start(test_title, False, False, 0)
        test_card.pack_start(test_sub, False, False, 0)

        indicators_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.lbl_btn1 = Gtk.Label(label="Левая кнопка")
        add_class(self.lbl_btn1, "mouse-btn-indicator")
        self.lbl_btn2 = Gtk.Label(label="Колесико")
        add_class(self.lbl_btn2, "mouse-btn-indicator")
        self.lbl_btn3 = Gtk.Label(label="Правая кнопка")
        add_class(self.lbl_btn3, "mouse-btn-indicator")
        self.lbl_scroll = Gtk.Label(label="Прокрутка")
        add_class(self.lbl_scroll, "mouse-btn-indicator")

        self.click_count = 0
        self.lbl_click_count = Gtk.Label(label="Кликов: 0")
        add_class(self.lbl_click_count, "m3-chip")

        indicators_box.pack_start(self.lbl_btn1, False, False, 0)
        indicators_box.pack_start(self.lbl_btn2, False, False, 0)
        indicators_box.pack_start(self.lbl_btn3, False, False, 0)
        indicators_box.pack_start(self.lbl_scroll, False, False, 0)
        indicators_box.pack_end(self.lbl_click_count, False, False, 0)
        test_card.pack_start(indicators_box, False, False, 0)

        self.test_event_box = Gtk.EventBox()
        add_class(self.test_event_box, "test-pad")
        self.test_event_box.set_size_request(-1, 90)
        self.test_event_box.set_above_child(True)
        self.test_event_box.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.SCROLL_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
        )

        test_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        test_inner_lbl = Gtk.Label(label="Кликайте и прокручивайте колесико в этой области для проверки...")
        test_inner_lbl.set_opacity(0.65)
        test_inner.pack_start(test_inner_lbl, True, True, 0)
        self.test_event_box.add(test_inner)

        self.test_event_box.connect("button-press-event", self.on_test_button_press)
        self.test_event_box.connect("button-release-event", self.on_test_button_release)
        self.test_event_box.connect("scroll-event", self.on_test_scroll)
        test_card.pack_start(self.test_event_box, False, False, 0)

        self.update_mouse_form()
        return scrolled

    def build_section_header(self, text: str) -> Gtk.Label:
        lbl = Gtk.Label(label=text, xalign=0)
        add_class(lbl, "section-header-label")
        return lbl

    def build_divider(self) -> Gtk.Separator:
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        add_class(sep, "card-divider")
        return sep

    class SwitchRow:
        def __init__(self, box: Gtk.Box, switch: Gtk.Switch) -> None:
            self.box = box
            self.switch = switch

    def build_m3_switch_row(self, title: str, subtitle: str, callback: Any) -> SwitchRow:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        add_class(row, "card-row")

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_title = Gtk.Label(label=title, xalign=0)
        add_class(lbl_title, "card-row-title")
        lbl_sub = Gtk.Label(label=subtitle, xalign=0)
        add_class(lbl_sub, "card-row-subtitle")
        lbl_sub.set_line_wrap(True)
        text_box.pack_start(lbl_title, False, False, 0)
        text_box.pack_start(lbl_sub, False, False, 0)
        row.pack_start(text_box, True, True, 0)

        sw = Gtk.Switch()
        sw.set_valign(Gtk.Align.CENTER)
        sw.connect("notify::active", callback)
        row.pack_end(sw, False, False, 0)

        return self.SwitchRow(row, sw)

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

        # M3 Segmented button with active indicator
        if dev.accel_profile == "flat":
            add_class(self.btn_seg_flat, "active")
            remove_class(self.btn_seg_adaptive, "active")
            self.btn_seg_flat.set_label("✓ Без ускорения (Flat 1:1)")
            self.btn_seg_adaptive.set_label("Адаптивное (Adaptive)")
            self.accel_sub_desc.set_text("Отключает программную акселерацию. Мышь перемещается строго пропорционально физическому сдвигу.")
        else:
            add_class(self.btn_seg_adaptive, "active")
            remove_class(self.btn_seg_flat, "active")
            self.btn_seg_flat.set_label("Без ускорения (Flat 1:1)")
            self.btn_seg_adaptive.set_label("✓ Адаптивное (Adaptive)")
            self.accel_sub_desc.set_text("Курсор динамически ускоряется при резких взмахах рукой. Привычно для офисной работы.")

        self.speed_scale.set_value(dev.accel_speed)
        self.speed_val_label.set_text(f"{dev.accel_speed:+.2f}")

        self.switch_natural.set_active(dev.natural_scrolling)
        self.switch_left.set_active(dev.left_handed)
        self.switch_middle.set_active(dev.middle_emulation)

    def set_accel_profile(self, profile: str) -> None:
        if getattr(self, "loading", False):
            return
        if not self.devices or self.current_device_idx >= len(self.devices):
            return
        dev = self.devices[self.current_device_idx]
        dev.accel_profile = profile
        if profile == "flat":
            add_class(self.btn_seg_flat, "active")
            remove_class(self.btn_seg_adaptive, "active")
            self.btn_seg_flat.set_label("✓ Без ускорения (Flat 1:1)")
            self.btn_seg_adaptive.set_label("Адаптивное (Adaptive)")
            self.accel_sub_desc.set_text("Отключает программную акселерацию. Мышь перемещается строго пропорционально физическому сдвигу.")
        else:
            add_class(self.btn_seg_adaptive, "active")
            remove_class(self.btn_seg_flat, "active")
            self.btn_seg_flat.set_label("Без ускорения (Flat 1:1)")
            self.btn_seg_adaptive.set_label("✓ Адаптивное (Adaptive)")
            self.accel_sub_desc.set_text("Курсор динамически ускоряется при резких взмахах рукой. Привычно для офисной работы.")
        self.apply_current_mouse()

    def on_speed_scale_changed(self, scale: Gtk.Scale) -> None:
        val = scale.get_value()
        self.speed_val_label.set_text(f"{val:+.2f}")
        if getattr(self, "loading", False):
            return
        if self.devices and self.current_device_idx < len(self.devices):
            self.devices[self.current_device_idx].accel_speed = val
            self.apply_current_mouse()

    def on_natural_switch_toggled(self, switch: Gtk.Switch, _pspec: Any) -> None:
        if getattr(self, "loading", False):
            return
        if not self.devices or self.current_device_idx >= len(self.devices):
            return
        self.devices[self.current_device_idx].natural_scrolling = switch.get_active()
        self.apply_current_mouse()

    def on_left_handed_switch_toggled(self, switch: Gtk.Switch, _pspec: Any) -> None:
        if getattr(self, "loading", False):
            return
        if not self.devices or self.current_device_idx >= len(self.devices):
            return
        self.devices[self.current_device_idx].left_handed = switch.get_active()
        self.apply_current_mouse()

    def on_middle_emu_switch_toggled(self, switch: Gtk.Switch, _pspec: Any) -> None:
        if getattr(self, "loading", False):
            return
        if not self.devices or self.current_device_idx >= len(self.devices):
            return
        self.devices[self.current_device_idx].middle_emulation = switch.get_active()
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
        self.set_status(f"Настройки для «{dev.name}» сохранены и применены")

    def on_test_button_press(self, _widget: Gtk.Widget, event: Gdk.EventButton) -> bool:
        self.click_count += 1
        self.lbl_click_count.set_text(f"Кликов: {self.click_count}")
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
        dir_text = "Прокрутка вверх" if event.direction == Gdk.ScrollDirection.UP else "Прокрутка вниз"
        self.lbl_scroll.set_text(dir_text)
        add_class(self.lbl_scroll, "active")
        GLib.timeout_add(150, lambda: remove_class(self.lbl_scroll, "active"))
        return True

    # --------------------------------------------------------------------------
    # Page 2: Keyboard
    # --------------------------------------------------------------------------
    def build_keyboard_page(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        add_class(root, "content-area")
        scrolled.add(root)

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        add_class(header, "page-header")
        title = Gtk.Label(label="Клавиатура", xalign=0)
        add_class(title, "page-title")
        subtitle = Gtk.Label(label="Раскладки ввода, переключение языка и параметры автоповтора", xalign=0)
        add_class(subtitle, "page-subtitle")
        header.pack_start(title, False, False, 0)
        header.pack_start(subtitle, False, False, 0)
        root.pack_start(header, False, False, 0)

        # Group 1: Layouts
        root.pack_start(self.build_section_header("Раскладки ввода"), False, False, 0)
        layout_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        add_class(layout_card, "card")
        root.pack_start(layout_card, False, False, 0)

        l_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        l_lbl = Gtk.Label(label="Активные раскладки:", xalign=0)
        self.entry_layouts = Gtk.Entry()
        self.entry_layouts.set_text(self.keyboard_layouts)
        l_box.pack_start(l_lbl, False, False, 0)
        l_box.pack_start(self.entry_layouts, True, True, 0)
        layout_card.pack_start(l_box, False, False, 0)

        presets_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        p_lbl = Gtk.Label(label="Быстрые пресеты:")
        presets_box.pack_start(p_lbl, False, False, 0)

        def set_preset(text: str) -> None:
            self.entry_layouts.set_text(text)

        for p_name, p_val in [("US, RU", "us,ru"), ("US, UA", "us,ua"), ("US, KZ", "us,kz"), ("US Only", "us")]:
            btn = Gtk.Button(label=p_name)
            add_class(btn, "btn-tonal")
            btn.connect("clicked", lambda _, val=p_val: set_preset(val))
            presets_box.pack_start(btn, False, False, 0)
        layout_card.pack_start(presets_box, False, False, 0)

        switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        sw_lbl = Gtk.Label(label="Клавиша смены языка:", xalign=0)
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

        # Group 2: Repeat & Latency
        root.pack_start(self.build_section_header("Скорость автоповтора (xset rate)"), False, False, 0)
        repeat_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        add_class(repeat_card, "card")
        root.pack_start(repeat_card, False, False, 0)

        delay_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        delay_lbl = Gtk.Label(label="Задержка перед повтором:", xalign=0)
        delay_lbl.set_size_request(220, -1)
        self.delay_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 150, 600, 10)
        self.delay_scale.set_value(self.keyboard_repeat_delay)
        self.delay_scale.set_hexpand(True)
        self.delay_val_lbl = Gtk.Label(label=f"{self.keyboard_repeat_delay} мс")
        add_class(self.delay_val_lbl, "m3-chip")
        self.delay_scale.connect("value-changed", lambda s: self.delay_val_lbl.set_text(f"{int(s.get_value())} мс"))

        delay_box.pack_start(delay_lbl, False, False, 0)
        delay_box.pack_start(self.delay_scale, True, True, 0)
        delay_box.pack_start(self.delay_val_lbl, False, False, 0)
        repeat_card.pack_start(delay_box, False, False, 0)

        rate_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        rate_lbl = Gtk.Label(label="Частота повтора:", xalign=0)
        rate_lbl.set_size_request(220, -1)
        self.rate_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 15, 60, 5)
        self.rate_scale.set_value(self.keyboard_repeat_rate)
        self.rate_scale.set_hexpand(True)
        self.rate_val_lbl = Gtk.Label(label=f"{self.keyboard_repeat_rate} симв/с")
        add_class(self.rate_val_lbl, "m3-chip")
        self.rate_scale.connect("value-changed", lambda s: self.rate_val_lbl.set_text(f"{int(s.get_value())} симв/с"))

        rate_box.pack_start(rate_lbl, False, False, 0)
        rate_box.pack_start(self.rate_scale, True, True, 0)
        rate_box.pack_start(self.rate_val_lbl, False, False, 0)
        repeat_card.pack_start(rate_box, False, False, 0)

        preset_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        opt_btn = Gtk.Button(label="Игровой пресет (280 мс / 40 симв/с)")
        add_class(opt_btn, "btn-tonal")
        opt_btn.connect("clicked", lambda _: (self.delay_scale.set_value(280), self.rate_scale.set_value(40)))
        preset_row.pack_start(opt_btn, False, False, 0)
        repeat_card.pack_start(preset_row, False, False, 0)

        test_entry_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        test_entry_lbl = Gtk.Label(label="Поле для проверки скорости повтора клавиш:", xalign=0)
        add_class(test_entry_lbl, "card-row-subtitle")
        test_entry = Gtk.Entry()
        test_entry.set_placeholder_text("Зажмите любую клавишу здесь для проверки...")
        test_entry_box.pack_start(test_entry_lbl, False, False, 0)
        test_entry_box.pack_start(test_entry, False, False, 0)
        repeat_card.pack_start(test_entry_box, False, False, 0)

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

        run_command(["setxkbmap", "-option", "", "-layout", layouts, "-option", switch_opt])
        run_command(["xset", "r", "rate", str(delay), str(rate)])

        save_all_input_settings(self.devices, layouts, switch_opt, delay, rate)
        self.set_status("Настройки клавиатуры применены и сохранены")

    # --------------------------------------------------------------------------
    # Page 3: Displays
    # --------------------------------------------------------------------------
    def build_displays_page(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        add_class(root, "content-area")
        scrolled.add(root)

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        add_class(header, "page-header")
        title = Gtk.Label(label="Дисплеи", xalign=0)
        add_class(title, "page-title")
        subtitle = Gtk.Label(label="Параметры подключенных мониторов и конфигурация вывода", xalign=0)
        add_class(subtitle, "page-subtitle")
        header.pack_start(title, False, False, 0)
        header.pack_start(subtitle, False, False, 0)
        root.pack_start(header, False, False, 0)

        root.pack_start(self.build_section_header("Подключенные мониторы"), False, False, 0)
        displays = get_connected_displays()
        for disp in displays:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            add_class(card, "card")

            top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            name_lbl = Gtk.Label(label=disp['name'], xalign=0)
            add_class(name_lbl, "card-title")
            top_row.pack_start(name_lbl, False, False, 0)

            if disp["primary"]:
                prim_badge = Gtk.Label(label="Основной дисплей")
                add_class(prim_badge, "m3-chip-success")
                top_row.pack_start(prim_badge, False, False, 0)

            rate_badge = Gtk.Label(label=disp["rate"])
            add_class(rate_badge, "m3-chip")
            top_row.pack_end(rate_badge, False, False, 0)
            card.pack_start(top_row, False, False, 0)

            geom_lbl = Gtk.Label(label=f"Разрешение и геометрия: {disp['geom']}", xalign=0)
            add_class(geom_lbl, "card-row-subtitle")
            card.pack_start(geom_lbl, False, False, 0)

            root.pack_start(card, False, False, 0)

        root.pack_start(self.build_section_header("Управление экранами"), False, False, 0)
        actions_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        add_class(actions_card, "card")
        root.pack_start(actions_card, False, False, 0)

        btns_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        arandr_btn = Gtk.Button(label="Открыть редактор ARandR")
        add_class(arandr_btn, "btn-tonal")
        arandr_btn.connect("clicked", lambda _: subprocess.Popen(["arandr"]))
        btns_box.pack_start(arandr_btn, False, False, 0)

        monitor_sh_btn = Gtk.Button(label="Применить конфигурацию monitor.sh")
        add_class(monitor_sh_btn, "btn-primary")
        monitor_sh_btn.connect("clicked", self.on_run_monitor_sh)
        btns_box.pack_start(monitor_sh_btn, False, False, 0)

        actions_card.pack_start(btns_box, False, False, 0)

        return scrolled

    def on_run_monitor_sh(self, _btn: Gtk.Button) -> None:
        script = HOME / ".config" / "i3" / "scripts" / "hardware" / "monitor.sh"
        if script.exists():
            run_command(["bash", str(script)])
            self.set_status("Конфигурация мониторов обновлена")

    # --------------------------------------------------------------------------
    # Page 4: Gaming & Picom
    # --------------------------------------------------------------------------
    def build_gaming_page(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        add_class(root, "content-area")
        scrolled.add(root)

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        add_class(header, "page-header")
        title = Gtk.Label(label="Игровой режим и Picom", xalign=0)
        add_class(title, "page-title")
        subtitle = Gtk.Label(label="Управление композитором для минимизации задержек ввода", xalign=0)
        add_class(subtitle, "page-subtitle")
        header.pack_start(title, False, False, 0)
        header.pack_start(subtitle, False, False, 0)
        root.pack_start(header, False, False, 0)

        root.pack_start(self.build_section_header("Композитор окон"), False, False, 0)
        p_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        add_class(p_card, "card")
        root.pack_start(p_card, False, False, 0)

        picom_running = run_command(["pgrep", "-x", "picom"]).returncode == 0
        self.picom_active = picom_running

        p_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        p_title = Gtk.Label(label="Композитор Picom (эффекты и прозрачность):", xalign=0)
        add_class(p_title, "card-title")
        self.picom_badge = Gtk.Label(label="Включен" if picom_running else "Отключен (игровой режим)")
        add_class(self.picom_badge, "m3-chip-success" if picom_running else "m3-chip-warning")

        self.switch_picom = Gtk.Switch()
        self.switch_picom.set_active(picom_running)
        self.switch_picom.connect("notify::active", self.on_picom_toggled)

        p_row.pack_start(p_title, False, False, 0)
        p_row.pack_start(self.picom_badge, False, False, 0)
        p_row.pack_end(self.switch_picom, False, False, 0)
        p_card.pack_start(p_row, False, False, 0)

        p_desc = Gtk.Label(
            label="В соревновательных играх (CS2, Left 4 Dead 2, Apex) рекомендуется отключать Picom.\n"
                  "Это исключает задержку кадрового буфера композитора и снижает инпут-лаг до аппаратного минимума.\n"
                  "Быстрое переключение доступно по комбинации: Mod + P.",
            xalign=0
        )
        add_class(p_desc, "card-row-subtitle")
        p_card.pack_start(p_desc, False, False, 0)

        root.pack_start(self.build_section_header("Параметры низкой задержки"), False, False, 0)
        t_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        add_class(t_card, "card")
        root.pack_start(t_card, False, False, 0)

        items = [
            ("Flat Mouse Acceleration (Raw 1:1)", "Включено", "Аппаратная акселерация мыши полностью отключена"),
            ("Отключение тайм-аута DPMS", "Включено", "Экраны не переходят в спящий режим во время игр и видео"),
            ("Быстрый автоповтор клавиатуры (280 мс)", "Включено", "Мгновенное срабатывание при зажатии клавиш"),
        ]
        for name, status, desc in items:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            add_class(row, "card-row")
            lbl_name = Gtk.Label(label=name, xalign=0)
            lbl_badge = Gtk.Label(label=status)
            add_class(lbl_badge, "m3-chip-success")
            lbl_desc = Gtk.Label(label=f"— {desc}", xalign=0)
            add_class(lbl_desc, "card-row-subtitle")

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
            self.picom_badge.set_text("Включен" if active else "Отключен (игровой режим)")
            if active:
                remove_class(self.picom_badge, "m3-chip-warning")
                add_class(self.picom_badge, "m3-chip-success")
            else:
                remove_class(self.picom_badge, "m3-chip-success")
                add_class(self.picom_badge, "m3-chip-warning")
            self.set_status(f"Композитор Picom {'запущен' if active else 'отключен'}")

    # --------------------------------------------------------------------------
    # Page 5: Appearance
    # --------------------------------------------------------------------------
    def build_appearance_page(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        add_class(root, "content-area")
        scrolled.add(root)

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        add_class(header, "page-header")
        title = Gtk.Label(label="Внешний вид", xalign=0)
        add_class(title, "page-title")
        subtitle = Gtk.Label(label="Темы оформления рабочего стола, курсор и шрифты", xalign=0)
        add_class(subtitle, "page-subtitle")
        header.pack_start(title, False, False, 0)
        header.pack_start(subtitle, False, False, 0)
        root.pack_start(header, False, False, 0)

        # Group 1: Material You Dynamic Theming
        root.pack_start(self.build_section_header("Цвета Material You"), False, False, 0)
        m3_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        add_class(m3_card, "card")
        root.pack_start(m3_card, False, False, 0)

        m3_head_row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        m3_title = Gtk.Label(label="Динамическая цветовая схема", xalign=0)
        add_class(m3_title, "card-title")
        m3_desc = Gtk.Label(
            label="Цветовые роли Material Design 3 и системная тема GTK автоматически адаптируются к текущим обоям и палитре Pywal.",
            xalign=0,
        )
        add_class(m3_desc, "card-row-subtitle")
        m3_head_row.pack_start(m3_title, False, False, 0)
        m3_head_row.pack_start(m3_desc, False, False, 0)
        m3_card.pack_start(m3_head_row, False, False, 0)

        pal = CURRENT_PALETTE or get_m3_dynamic_palette()
        wall_name = Path(pal.get("wallpaper", "")).name or "Обои рабочего стола"

        badges_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.m3_wall_badge = Gtk.Label(label=wall_name)
        add_class(self.m3_wall_badge, "m3-chip")

        self.m3_primary_badge = Gtk.Label(label=f"Акцент: {pal['primary']}")
        add_class(self.m3_primary_badge, "m3-chip")

        self.m3_surface_badge = Gtk.Label(label=f"Фон: {pal['surface']}")
        add_class(self.m3_surface_badge, "m3-chip")

        badges_row.pack_start(self.m3_wall_badge, False, False, 0)
        badges_row.pack_start(self.m3_primary_badge, False, False, 0)
        badges_row.pack_start(self.m3_surface_badge, False, False, 0)
        m3_card.pack_start(badges_row, False, False, 0)

        m3_btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        sync_m3_btn = Gtk.Button(label="Синхронизировать цвета Material You")
        add_class(sync_m3_btn, "btn-primary")
        sync_m3_btn.connect("clicked", self.on_sync_material_you_clicked)
        m3_btn_row.pack_start(sync_m3_btn, False, False, 0)
        m3_card.pack_start(m3_btn_row, False, False, 0)

        # Group 2: Themes
        root.pack_start(self.build_section_header("Темы оформления"), False, False, 0)
        theme_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        add_class(theme_card, "card")
        root.pack_start(theme_card, False, False, 0)

        cur_theme = get_current_theme()
        cur_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        cur_lbl = Gtk.Label(label="Текущая тема:", xalign=0)
        self.cur_theme_badge = Gtk.Label(label=cur_theme)
        add_class(self.cur_theme_badge, "m3-chip")
        cur_row.pack_start(cur_lbl, False, False, 0)
        cur_row.pack_start(self.cur_theme_badge, False, False, 0)
        theme_card.pack_start(cur_row, False, False, 0)

        themes_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.themes_combo = Gtk.ComboBoxText()
        all_themes = list_themes()
        active_t_idx = 0
        for idx, th in enumerate(all_themes):
            self.themes_combo.append_text(th)
            if th.lower() in cur_theme.lower() or cur_theme.lower() in th.lower():
                active_t_idx = idx
        if all_themes:
            self.themes_combo.set_active(active_t_idx)
        themes_row.pack_start(self.themes_combo, True, True, 0)

        apply_t_btn = Gtk.Button(label="Применить тему")
        add_class(apply_t_btn, "btn-primary")
        apply_t_btn.connect("clicked", self.on_apply_theme_clicked)
        themes_row.pack_start(apply_t_btn, False, False, 0)

        open_selector_btn = Gtk.Button(label="Галерея тем (Mod+T)")
        add_class(open_selector_btn, "btn-tonal")
        open_selector_btn.connect("clicked", lambda _: subprocess.Popen([str(HOME / ".config/i3/scripts/software/theme-select.sh")]))
        themes_row.pack_end(open_selector_btn, False, False, 0)
        theme_card.pack_start(themes_row, False, False, 0)

        # Group 3: Mouse Cursor (Material Design 3 Unified Cursor Manager)
        root.pack_start(self.build_section_header("Курсор мыши во всей системе"), False, False, 0)
        cursor_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        add_class(cursor_card, "card")
        root.pack_start(cursor_card, False, False, 0)

        c_head_row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        c_head_title = Gtk.Label(label="Системный указатель мыши (Курсор)", xalign=0)
        add_class(c_head_title, "card-title")
        c_head_desc = Gtk.Label(
            label="Синхронизирует один курсор для всех приложений: рабочего стола X11, GTK 2/3/4, Qt, Chromium, Discord (Electron), Steam и терминалов.",
            xalign=0,
        )
        add_class(c_head_desc, "card-row-subtitle")
        c_head_row.pack_start(c_head_title, False, False, 0)
        c_head_row.pack_start(c_head_desc, False, False, 0)
        cursor_card.pack_start(c_head_row, False, False, 0)

        # Active Badges Row
        cur_c_theme, cur_c_size = get_current_cursor_settings()
        c_badges_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        self.cursor_theme_badge = Gtk.Label(label=f"Текущая тема: {cur_c_theme}")
        add_class(self.cursor_theme_badge, "m3-chip")
        
        self.cursor_size_badge = Gtk.Label(label=f"Размер: {cur_c_size} px")
        add_class(self.cursor_size_badge, "m3-chip")

        c_badges_row.pack_start(self.cursor_theme_badge, False, False, 0)
        c_badges_row.pack_start(self.cursor_size_badge, False, False, 0)
        cursor_card.pack_start(c_badges_row, False, False, 0)

        # Controls Row: Theme Dropdown + Size Dropdown
        controls_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)

        # Theme Selector
        theme_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        theme_box_lbl = Gtk.Label(label="Тема курсора:", xalign=0)
        add_class(theme_box_lbl, "card-subtitle")
        self.cursor_theme_combo = Gtk.ComboBoxText()
        
        self.available_cursor_themes = get_installed_cursor_themes()
        active_c_idx = 0
        for idx, t in enumerate(self.available_cursor_themes):
            label = f"{t['name']}  ({t['id']})" if t['name'] != t['id'] else t['name']
            self.cursor_theme_combo.append_text(label)
            if t['id'] == cur_c_theme or t['name'] == cur_c_theme:
                active_c_idx = idx
        if self.available_cursor_themes:
            self.cursor_theme_combo.set_active(active_c_idx)
        
        theme_box.pack_start(theme_box_lbl, False, False, 0)
        theme_box.pack_start(self.cursor_theme_combo, True, True, 0)
        controls_row.pack_start(theme_box, True, True, 0)

        # Size Selector
        size_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        size_box_lbl = Gtk.Label(label="Размер указателя:", xalign=0)
        add_class(size_box_lbl, "card-subtitle")
        self.cursor_size_combo = Gtk.ComboBoxText()
        self.cursor_sizes = [16, 24, 32, 48]
        size_labels = {
            16: "16 px (Компактный)",
            24: "24 px (Стандартный)",
            32: "32 px (Крупный / 2K)",
            48: "48 px (4K / Ultra)",
        }
        active_sz_idx = 1
        for idx, s in enumerate(self.cursor_sizes):
            self.cursor_size_combo.append_text(size_labels.get(s, f"{s} px"))
            if s == cur_c_size:
                active_sz_idx = idx
        self.cursor_size_combo.set_active(active_sz_idx)
        size_box.pack_start(size_box_lbl, False, False, 0)
        size_box.pack_start(self.cursor_size_combo, False, False, 0)
        controls_row.pack_start(size_box, False, False, 0)

        cursor_card.pack_start(controls_row, False, False, 0)

        # Action Buttons Row
        actions_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        apply_c_btn = Gtk.Button(label="Применить во всей системе")
        add_class(apply_c_btn, "btn-primary")
        apply_c_btn.connect("clicked", self.on_apply_cursor_clicked)
        actions_row.pack_start(apply_c_btn, False, False, 0)

        bibata_preset_btn = Gtk.Button(label="Выбрать Bibata Modern (Рекомендовано)")
        add_class(bibata_preset_btn, "btn-tonal")
        bibata_preset_btn.connect("clicked", self.on_quick_apply_bibata_clicked)
        actions_row.pack_start(bibata_preset_btn, False, False, 0)
        cursor_card.pack_start(actions_row, False, False, 0)

        # Interactive Test Pad
        test_hover_box = Gtk.EventBox()
        add_class(test_hover_box, "test-pad")
        test_hover_box.set_size_request(-1, 55)
        test_inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        test_inner.set_halign(Gtk.Align.CENTER)
        test_inner.set_valign(Gtk.Align.CENTER)
        test_lbl = Gtk.Label(label="Наведите мышь сюда для мгновенной проверки вида и размера курсора")
        test_lbl.set_opacity(0.8)
        test_inner.pack_start(test_lbl, False, False, 0)
        test_hover_box.add(test_inner)
        cursor_card.pack_start(test_hover_box, False, False, 0)

        return scrolled

    def on_sync_material_you_clicked(self, _btn: Gtk.Button) -> None:
        update_gtk_script = HOME / ".config" / "i3" / "scripts" / "software" / "update-gtk-theme.py"
        if update_gtk_script.exists():
            subprocess.run(["python3", str(update_gtk_script)], check=False)
        self.reload_material_you_palette(notify=True)

    def on_apply_theme_clicked(self, _btn: Gtk.Button) -> None:
        th = self.themes_combo.get_active_text()
        if th:
            script = HOME / ".config" / "i3" / "scripts" / "software" / "theme-apply.sh"
            theme_path = THEMES_DIR / th
            if script.exists() and theme_path.exists():
                subprocess.Popen([str(script), str(theme_path)])
                self.cur_theme_badge.set_text(th)
                self.set_status(f"Тема «{th}» применяется...")
                GLib.timeout_add(1200, lambda: (self.reload_material_you_palette(notify=True), False)[1])

    def on_apply_cursor_clicked(self, _btn: Gtk.Button) -> None:
        idx = self.cursor_theme_combo.get_active()
        if idx >= 0 and idx < len(self.available_cursor_themes):
            theme_id = self.available_cursor_themes[idx]["id"]
        else:
            theme_id = "Bibata-Modern-Classic"

        sz_idx = self.cursor_size_combo.get_active()
        if sz_idx >= 0 and sz_idx < len(self.cursor_sizes):
            size = self.cursor_sizes[sz_idx]
        else:
            size = 24

        ok, msg = apply_cursor_theme_systemwide(theme_id, size)
        if ok:
            self.cursor_theme_badge.set_text(f"Текущая тема: {theme_id}")
            self.cursor_size_badge.set_text(f"Размер: {size} px")
            if hasattr(self, "mouse_cursor_badge"):
                self.mouse_cursor_badge.set_text(f"Курсор: {theme_id} ({size}px)")
            self.set_status(f"Указатель мыши «{theme_id}» ({size}px) применён во всей системе!")
        else:
            self.set_status(msg)

    def on_quick_apply_bibata_clicked(self, _btn: Gtk.Button) -> None:
        for idx, t in enumerate(self.available_cursor_themes):
            if t["id"] == "Bibata-Modern-Classic":
                self.cursor_theme_combo.set_active(idx)
                break
        self.cursor_size_combo.set_active(1)  # 24 px
        self.on_apply_cursor_clicked(_btn)


    # --------------------------------------------------------------------------
    # Page 6: Autostart
    # --------------------------------------------------------------------------
    def build_autostart_page(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        add_class(root, "content-area")
        scrolled.add(root)

        # Header Box with Title, Subtitle, and Add Button
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        add_class(header, "page-header")

        titles_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title = Gtk.Label(label="Автозапуск", xalign=0)
        add_class(title, "page-title")
        subtitle = Gtk.Label(label="Управление автозапуском программ, системных скриптов i3 и служб Systemd", xalign=0)
        add_class(subtitle, "page-subtitle")
        titles_box.pack_start(title, False, False, 0)
        titles_box.pack_start(subtitle, False, False, 0)
        header.pack_start(titles_box, True, True, 0)

        add_app_btn = Gtk.Button(label="+ Добавить программу")
        add_class(add_app_btn, "btn-primary")
        add_app_btn.set_valign(Gtk.Align.CENTER)
        add_app_btn.connect("clicked", self.on_add_autostart_app_clicked)
        header.pack_end(add_app_btn, False, False, 0)
        root.pack_start(header, False, False, 0)

        # Category 1: Applications (XDG Autostart)
        root.pack_start(self.build_section_header("Пользовательские приложения"), False, False, 0)
        card_apps = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        add_class(card_apps, "card")
        self.autostart_apps_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card_apps.pack_start(self.autostart_apps_box, True, True, 0)
        root.pack_start(card_apps, False, False, 0)

        # Category 2: i3 Session Scripts
        root.pack_start(self.build_section_header("Скрипты сессии i3wm"), False, False, 0)
        card_scripts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        add_class(card_scripts, "card")
        self.autostart_scripts_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card_scripts.pack_start(self.autostart_scripts_box, True, True, 0)
        root.pack_start(card_scripts, False, False, 0)

        # Category 3: Systemd User Services
        root.pack_start(self.build_section_header("Службы Systemd (User Services)"), False, False, 0)
        card_services = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        add_class(card_services, "card")
        self.autostart_services_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card_services.pack_start(self.autostart_services_box, True, True, 0)
        root.pack_start(card_services, False, False, 0)

        # Populate categories
        self.populate_autostart_apps()
        self.populate_session_scripts()
        self.populate_systemd_services()

        return scrolled

    def populate_autostart_apps(self) -> None:
        for child in self.autostart_apps_box.get_children():
            self.autostart_apps_box.remove(child)

        apps = get_autostart_desktop_apps()
        if not apps:
            empty_lbl = Gtk.Label(label="Нет добавленных приложений. Нажмите «+ Добавить программу» выше.", xalign=0)
            add_class(empty_lbl, "card-row-subtitle")
            self.autostart_apps_box.pack_start(empty_lbl, False, False, 10)
            self.autostart_apps_box.show_all()
            return

        for idx, app in enumerate(apps):
            if idx > 0:
                self.autostart_apps_box.pack_start(self.build_divider(), False, False, 0)

            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
            add_class(row, "card-row")

            icon_img = create_app_icon_widget(app.get("icon", ""), size=24)
            icon_img.set_valign(Gtk.Align.CENTER)
            row.pack_start(icon_img, False, False, 0)

            tbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            name_lbl = Gtk.Label(label=app["name"], xalign=0)
            add_class(name_lbl, "card-row-title")
            cmd_lbl = Gtk.Label(label=app["exec"], xalign=0)
            add_class(cmd_lbl, "card-row-subtitle")
            cmd_lbl.set_line_wrap(True)
            tbox.pack_start(name_lbl, False, False, 0)
            tbox.pack_start(cmd_lbl, False, False, 0)
            row.pack_start(tbox, True, True, 0)

            ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            ctrl_box.set_valign(Gtk.Align.CENTER)

            status_chip = Gtk.Label(label="Работает" if app["running"] else "Остановлено")
            add_class(status_chip, "m3-chip-success" if app["running"] else "m3-chip")
            ctrl_box.pack_start(status_chip, False, False, 0)

            act_btn = Gtk.Button(label="Остановить" if app["running"] else "Запустить")
            add_class(act_btn, "btn-tonal")
            act_btn.connect("clicked", self.on_toggle_app_process, app, status_chip)
            ctrl_box.pack_start(act_btn, False, False, 0)

            del_btn = Gtk.Button(label="Удалить")
            add_class(del_btn, "btn-outlined")
            del_btn.connect("clicked", self.on_delete_app_clicked, app)
            ctrl_box.pack_start(del_btn, False, False, 0)

            sw = Gtk.Switch()
            sw.set_valign(Gtk.Align.CENTER)
            sw.set_active(app["enabled"])
            sw.connect("state-set", self.on_toggle_app_autostart, app)
            ctrl_box.pack_start(sw, False, False, 0)

            row.pack_end(ctrl_box, False, False, 0)
            self.autostart_apps_box.pack_start(row, False, False, 0)

        self.autostart_apps_box.show_all()

    def populate_session_scripts(self) -> None:
        for child in self.autostart_scripts_box.get_children():
            self.autostart_scripts_box.remove(child)

        for idx, item in enumerate(SESSION_SCRIPTS):
            if idx > 0:
                self.autostart_scripts_box.pack_start(self.build_divider(), False, False, 0)

            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
            add_class(row, "card-row")

            icon_img = Gtk.Image.new_from_icon_name(item.get("icon", "system-run-symbolic"), Gtk.IconSize.MENU)
            row.pack_start(icon_img, False, False, 0)

            tbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            name_lbl = Gtk.Label(label=item["title"], xalign=0)
            add_class(name_lbl, "card-row-title")
            desc_lbl = Gtk.Label(label=item["desc"], xalign=0)
            add_class(desc_lbl, "card-row-subtitle")
            desc_lbl.set_line_wrap(True)
            tbox.pack_start(name_lbl, False, False, 0)
            tbox.pack_start(desc_lbl, False, False, 0)
            row.pack_start(tbox, True, True, 0)

            ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            ctrl_box.set_valign(Gtk.Align.CENTER)

            is_running = is_process_running(item["proc"])
            status_chip = Gtk.Label(label="Работает" if is_running else "Остановлен")
            add_class(status_chip, "m3-chip-success" if is_running else "m3-chip")
            ctrl_box.pack_start(status_chip, False, False, 0)

            act_btn = Gtk.Button(label="Перезапустить" if is_running else "Запустить")
            add_class(act_btn, "btn-tonal")
            act_btn.connect("clicked", self.on_action_script_clicked, item, status_chip)
            ctrl_box.pack_start(act_btn, False, False, 0)

            is_enabled = get_i3_autostart_status(item["pattern"])
            sw = Gtk.Switch()
            sw.set_valign(Gtk.Align.CENTER)
            sw.set_active(is_enabled)
            sw.connect("state-set", self.on_toggle_script_autostart, item)
            ctrl_box.pack_start(sw, False, False, 0)

            row.pack_end(ctrl_box, False, False, 0)
            self.autostart_scripts_box.pack_start(row, False, False, 0)

        self.autostart_scripts_box.show_all()

    def populate_systemd_services(self) -> None:
        for child in self.autostart_services_box.get_children():
            self.autostart_services_box.remove(child)

        for idx, srv in enumerate(SYSTEMD_SERVICES):
            if idx > 0:
                self.autostart_services_box.pack_start(self.build_divider(), False, False, 0)

            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
            add_class(row, "card-row")

            icon_img = Gtk.Image.new_from_icon_name(srv.get("icon", "preferences-system-symbolic"), Gtk.IconSize.MENU)
            row.pack_start(icon_img, False, False, 0)

            tbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            name_lbl = Gtk.Label(label=srv["title"], xalign=0)
            add_class(name_lbl, "card-row-title")
            desc_lbl = Gtk.Label(label=srv["desc"], xalign=0)
            add_class(desc_lbl, "card-row-subtitle")
            desc_lbl.set_line_wrap(True)
            tbox.pack_start(name_lbl, False, False, 0)
            tbox.pack_start(desc_lbl, False, False, 0)
            row.pack_start(tbox, True, True, 0)

            ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            ctrl_box.set_valign(Gtk.Align.CENTER)

            is_enabled, is_active = get_systemd_user_service_status(srv["id"])

            status_chip = Gtk.Label(label="Активна" if is_active else "Остановлена")
            add_class(status_chip, "m3-chip-success" if is_active else "m3-chip")
            ctrl_box.pack_start(status_chip, False, False, 0)

            act_btn = Gtk.Button(label="Стоп" if is_active else "Старт")
            add_class(act_btn, "btn-tonal")
            act_btn.connect("clicked", self.on_action_service_clicked, srv, status_chip)
            ctrl_box.pack_start(act_btn, False, False, 0)

            sw = Gtk.Switch()
            sw.set_valign(Gtk.Align.CENTER)
            sw.set_active(is_enabled)
            sw.connect("state-set", self.on_toggle_service_autostart, srv)
            ctrl_box.pack_start(sw, False, False, 0)

            row.pack_end(ctrl_box, False, False, 0)
            self.autostart_services_box.pack_start(row, False, False, 0)

        self.autostart_services_box.show_all()

    def on_toggle_app_autostart(self, sw: Gtk.Switch, state: bool, app_info: dict) -> bool:
        set_autostart_desktop_app_enabled(app_info["path"], state)
        self.set_status(f"Автозапуск «{app_info['name']}»: {'включен' if state else 'отключен'}")
        return False

    def on_toggle_app_process(self, btn: Gtk.Button, app_info: dict, status_chip: Gtk.Label) -> None:
        proc_key = app_info["proc_key"]
        if is_process_running(proc_key):
            subprocess.run(["pkill", "-f", proc_key], check=False)
            status_chip.set_text("Остановлено")
            remove_class(status_chip, "m3-chip-success")
            add_class(status_chip, "m3-chip")
            btn.set_label("Запустить")
            self.set_status(f"Процесс «{app_info['name']}» остановлен")
        else:
            subprocess.Popen(app_info["exec"], shell=True, start_new_session=True)
            status_chip.set_text("Работает")
            remove_class(status_chip, "m3-chip")
            add_class(status_chip, "m3-chip-success")
            btn.set_label("Остановить")
            self.set_status(f"Приложение «{app_info['name']}» запущено")

    def on_delete_app_clicked(self, _btn: Gtk.Button, app_info: dict) -> None:
        delete_autostart_desktop_app(app_info["path"])
        self.populate_autostart_apps()
        self.set_status(f"«{app_info['name']}» удалено из автозапуска")

    def on_toggle_script_autostart(self, sw: Gtk.Switch, state: bool, item: dict) -> bool:
        set_i3_autostart_status(item["pattern"], state)
        self.set_status(f"Автозапуск «{item['title']}»: {'включен' if state else 'отключен'}")
        return False

    def on_action_script_clicked(self, btn: Gtk.Button, item: dict, status_chip: Gtk.Label) -> None:
        cmd = item["cmd"]
        proc = item["proc"]
        if proc == "picom":
            toggle_picom = HOME / ".config/i3/scripts/software/toggle-picom.sh"
            if toggle_picom.exists():
                subprocess.run([str(toggle_picom)], check=False)
        elif proc == "dunst":
            subprocess.run(["killall", "-9", "dunst"], check=False)
            subprocess.Popen(["dunst"], start_new_session=True)
        elif proc == "eww":
            subprocess.Popen([str(HOME / ".config/eww/launch.sh"), "--restart"], start_new_session=True)
        elif proc == "copyq":
            if is_process_running("copyq"):
                subprocess.run(["killall", "copyq"], check=False)
            else:
                subprocess.Popen(["copyq"], start_new_session=True)
        else:
            subprocess.Popen(cmd, shell=True, start_new_session=True)

        GLib.timeout_add(600, lambda: (self.update_script_status(item, btn, status_chip), False)[1])
        self.set_status(f"Команда «{item['title']}» выполнена")

    def update_script_status(self, item: dict, btn: Gtk.Button, status_chip: Gtk.Label) -> None:
        running = is_process_running(item["proc"])
        status_chip.set_text("Работает" if running else "Остановлен")
        if running:
            remove_class(status_chip, "m3-chip")
            add_class(status_chip, "m3-chip-success")
            btn.set_label("Перезапустить")
        else:
            remove_class(status_chip, "m3-chip-success")
            add_class(status_chip, "m3-chip")
            btn.set_label("Запустить")

    def on_toggle_service_autostart(self, sw: Gtk.Switch, state: bool, srv: dict) -> bool:
        set_systemd_user_service_enabled(srv["id"], state)
        self.set_status(f"Служба {srv['id']}: {'включена' if state else 'отключена'}")
        return False

    def on_action_service_clicked(self, btn: Gtk.Button, srv: dict, status_chip: Gtk.Label) -> None:
        _, is_active = get_systemd_user_service_status(srv["id"])
        set_systemd_user_service_active(srv["id"], not is_active)
        new_active = not is_active
        status_chip.set_text("Активна" if new_active else "Остановлена")
        if new_active:
            remove_class(status_chip, "m3-chip")
            add_class(status_chip, "m3-chip-success")
            btn.set_label("Стоп")
        else:
            remove_class(status_chip, "m3-chip-success")
            add_class(status_chip, "m3-chip")
            btn.set_label("Старт")
        self.set_status(f"Служба {srv['id']} {'запущена' if new_active else 'остановлена'}")

    def on_add_autostart_app_clicked(self, _btn: Gtk.Button) -> None:
        dialog = Gtk.Dialog(
            title="Добавить программу в автозапуск",
            parent=self,
            modal=True,
            destroy_with_parent=True,
        )
        dialog.set_default_size(440, 480)
        add_class(dialog, "control-center-window")

        content_area = dialog.get_content_area()
        add_class(content_area, "content-area")
        content_area.set_spacing(12)

        d_title = Gtk.Label(label="Добавить программу", xalign=0)
        add_class(d_title, "page-title")
        content_area.pack_start(d_title, False, False, 0)

        d_sub = Gtk.Label(label="Выберите приложение для автозапуска или найдите его через поиск.", xalign=0)
        add_class(d_sub, "card-row-subtitle")
        d_sub.set_line_wrap(True)
        content_area.pack_start(d_sub, False, False, 0)

        # Search bar
        search_bar = Gtk.SearchEntry()
        add_class(search_bar, "m3-search")
        search_bar.set_placeholder_text("  Поиск установленных программ...")
        content_area.pack_start(search_bar, False, False, 0)

        # App List in ScrolledWindow
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(240)
        scrolled.set_max_content_height(280)
        add_class(scrolled, "card")

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        listbox.set_activate_on_single_click(True)
        scrolled.add(listbox)
        content_area.pack_start(scrolled, True, True, 0)

        installed_apps = list_installed_system_apps()

        # Populate rows
        app_rows: list[tuple[Gtk.ListBoxRow, dict[str, str]]] = []
        for app in installed_apps:
            row = Gtk.ListBoxRow()
            add_class(row, "card-row")

            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            icon_w = create_app_icon_widget(app.get("icon", ""), size=24)
            icon_w.set_valign(Gtk.Align.CENTER)
            hbox.pack_start(icon_w, False, False, 0)

            tbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            tbox.set_valign(Gtk.Align.CENTER)
            nl = Gtk.Label(label=app["name"], xalign=0)
            add_class(nl, "card-row-title")
            sub_text = app["comment"] or app["exec"]
            if len(sub_text) > 42:
                sub_text = sub_text[:39] + "..."
            sl = Gtk.Label(label=sub_text, xalign=0)
            add_class(sl, "card-row-subtitle")
            tbox.pack_start(nl, False, False, 0)
            tbox.pack_start(sl, False, False, 0)
            hbox.pack_start(tbox, True, True, 0)

            add_action_btn = Gtk.Button(label="Добавить")
            add_class(add_action_btn, "btn-tonal")
            add_action_btn.set_valign(Gtk.Align.CENTER)
            hbox.pack_end(add_action_btn, False, False, 0)

            row.add(hbox)
            listbox.add(row)
            app_rows.append((row, app))

        # Filter function
        def filter_func(row: Gtk.ListBoxRow) -> bool:
            query = search_bar.get_text().strip().lower()
            if not query:
                return True
            for r, a in app_rows:
                if r == row:
                    return query in a["name"].lower() or query in a["exec"].lower() or query in a.get("comment", "").lower()
            return True

        listbox.set_filter_func(filter_func)
        search_bar.connect("search-changed", lambda _w: listbox.invalidate_filter())

        # Manual expander
        expander = Gtk.Expander(label="Указать команду вручную...")
        manual_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        manual_box.set_margin_top(6)
        manual_box.set_margin_bottom(6)

        m_name_entry = Gtk.Entry()
        m_name_entry.set_placeholder_text("Название (например: My Custom Script)")
        m_cmd_entry = Gtk.Entry()
        m_cmd_entry.set_placeholder_text("Команда (например: ~/scripts/my-service.sh)")

        manual_box.pack_start(m_name_entry, False, False, 0)
        manual_box.pack_start(m_cmd_entry, False, False, 0)
        expander.add(manual_box)
        content_area.pack_start(expander, False, False, 0)

        # Dialog Buttons
        dialog.add_button("Закрыть", Gtk.ResponseType.CANCEL)
        manual_add_btn = dialog.add_button("Добавить команду", Gtk.ResponseType.OK)
        add_class(manual_add_btn, "btn-primary")
        manual_add_btn.set_sensitive(False)

        def on_manual_text_changed(_w: Gtk.Entry) -> None:
            can_add = bool(m_name_entry.get_text().strip() and m_cmd_entry.get_text().strip())
            manual_add_btn.set_sensitive(can_add)

        m_name_entry.connect("changed", on_manual_text_changed)
        m_cmd_entry.connect("changed", on_manual_text_changed)

        selected_app_to_add: dict[str, str] | None = None

        def add_and_close(app_data: dict[str, str]) -> None:
            nonlocal selected_app_to_add
            selected_app_to_add = app_data
            dialog.response(Gtk.ResponseType.APPLY)

        def on_row_activated(_lb: Gtk.ListBox, activated_row: Gtk.ListBoxRow) -> None:
            for r, a in app_rows:
                if r == activated_row:
                    add_and_close(a)
                    break

        listbox.connect("row-activated", on_row_activated)

        for r, a in app_rows:
            hbox = r.get_child()
            if isinstance(hbox, Gtk.Box):
                children = hbox.get_children()
                if children and isinstance(children[-1], Gtk.Button):
                    children[-1].connect("clicked", lambda _b, app_item=a: add_and_close(app_item))

        cancel_btn = dialog.get_widget_for_response(Gtk.ResponseType.CANCEL)
        if cancel_btn:
            add_class(cancel_btn, "btn-tonal")

        dialog.show_all()
        response = dialog.run()

        if response == Gtk.ResponseType.APPLY and selected_app_to_add:
            add_autostart_desktop_app(
                selected_app_to_add["name"],
                selected_app_to_add["exec"],
                selected_app_to_add.get("comment", ""),
                selected_app_to_add.get("icon", ""),
            )
            self.populate_autostart_apps()
            self.set_status(f"Приложение «{selected_app_to_add['name']}» добавлено в автозапуск")
        elif response == Gtk.ResponseType.OK:
            name = m_name_entry.get_text().strip()
            cmd = m_cmd_entry.get_text().strip()
            if name and cmd:
                add_autostart_desktop_app(name, cmd)
                self.populate_autostart_apps()
                self.set_status(f"Приложение «{name}» добавлено в автозапуск")

        dialog.destroy()

    # --------------------------------------------------------------------------
    # Page 7: Shortcuts
    # --------------------------------------------------------------------------
    def build_shortcuts_page(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        add_class(root, "content-area")
        scrolled.add(root)

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        add_class(header, "page-header")
        title = Gtk.Label(label="Горячие клавиши", xalign=0)
        add_class(title, "page-title")
        subtitle = Gtk.Label(label="Основные комбинации клавиш управления системой ($mod = Super / Win)", xalign=0)
        add_class(subtitle, "page-subtitle")
        header.pack_start(title, False, False, 0)
        header.pack_start(subtitle, False, False, 0)
        root.pack_start(header, False, False, 0)

        root.pack_start(self.build_section_header("Комбинации клавиш i3wm"), False, False, 0)
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
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
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
            add_class(row, "card-row")
            lbl_key = Gtk.Label(label=keys, xalign=0)
            add_class(lbl_key, "m3-chip")
            lbl_key.set_size_request(160, -1)

            lbl_act = Gtk.Label(label=action, xalign=0)
            add_class(lbl_act, "card-row-title")
            lbl_act.set_line_wrap(True)

            row.pack_start(lbl_key, False, False, 0)
            row.pack_start(lbl_act, True, True, 0)
            card.pack_start(row, False, False, 0)

        return scrolled

    # --------------------------------------------------------------------------
    # Page 8: Profile & User Management (Google M3 Specifications)
    # --------------------------------------------------------------------------
    def create_avatar_image(self, username: str, size: int = 96) -> Gtk.Widget:
        """Builds a circular avatar container for the given username."""
        avatar_path = None
        try:
            u_entry = pwd.getpwnam(username)
            candidate = Path(u_entry.pw_dir) / ".face"
            if candidate.is_file():
                avatar_path = candidate
        except Exception:
            pass

        pix = get_circular_avatar_pixbuf(avatar_path, size=size) if avatar_path else None
        if pix:
            img = Gtk.Image.new_from_pixbuf(pix)
        else:
            img = Gtk.Image.new_from_icon_name("avatar-default-symbolic", Gtk.IconSize.DIALOG if size > 64 else Gtk.IconSize.DND)
            img.set_pixel_size(size)

        frame = Gtk.Box()
        add_class(frame, "avatar-frame")
        frame.set_valign(Gtk.Align.CENTER)
        frame.set_halign(Gtk.Align.CENTER)
        frame.pack_start(img, False, False, 0)
        return frame

    def create_interactive_avatar_button(self, username: str, size: int = 104) -> Gtk.Widget:
        """Builds a clickable circular avatar button with edit badge and hover animation."""
        avatar_frame = self.create_avatar_image(username, size=size)

        overlay = Gtk.Overlay()
        overlay.add(avatar_frame)

        badge_box = Gtk.Box()
        add_class(badge_box, "avatar-edit-badge")
        badge_box.set_halign(Gtk.Align.END)
        badge_box.set_valign(Gtk.Align.END)
        badge_icon = Gtk.Image.new_from_icon_name("camera-photo-symbolic", Gtk.IconSize.MENU)
        badge_box.pack_start(badge_icon, False, False, 0)
        overlay.add_overlay(badge_box)

        btn = Gtk.Button()
        add_class(btn, "avatar-btn")
        btn.add(overlay)
        btn.set_tooltip_text("Нажмите на аватар, чтобы выбрать фото и настроить кадрирование")
        btn.connect("clicked", lambda _: self.on_choose_avatar_clicked(None))
        return btn

    def update_profile_avatar_display(self) -> None:
        """Refreshes the live avatar widget in the current user card."""
        for child in self.profile_avatar_box.get_children():
            self.profile_avatar_box.remove(child)
        self.profile_avatar_widget = self.create_interactive_avatar_button(CURRENT_USER, size=104)
        self.profile_avatar_box.pack_start(self.profile_avatar_widget, False, False, 0)
        self.profile_avatar_box.show_all()

    def build_profile_page(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        add_class(root, "content-area")
        scrolled.add(root)

        # Page Header
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        add_class(header, "page-header")
        title = Gtk.Label(label="Профиль и пользователи", xalign=0)
        add_class(title, "page-title")
        subtitle = Gtk.Label(label="Управление личным профилем, аватаркой и учетными записями операционной системы", xalign=0)
        add_class(subtitle, "page-subtitle")
        header.pack_start(title, False, False, 0)
        header.pack_start(subtitle, False, False, 0)
        root.pack_start(header, False, False, 0)

        # ----------------------------------------------------------------------
        # Card 1: Current User Profile
        # ----------------------------------------------------------------------
        root.pack_start(self.build_section_header("Мой профиль"), False, False, 0)
        profile_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        add_class(profile_card, "card")
        root.pack_start(profile_card, False, False, 0)

        u_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)

        # Avatar container (interactive clickable button)
        self.profile_avatar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.profile_avatar_box.set_valign(Gtk.Align.CENTER)
        self.profile_avatar_widget = self.create_interactive_avatar_button(CURRENT_USER, size=104)
        self.profile_avatar_box.pack_start(self.profile_avatar_widget, False, False, 0)
        u_top.pack_start(self.profile_avatar_box, False, False, 0)

        # Info Box
        u_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        u_info.set_valign(Gtk.Align.CENTER)

        # Username row with badges
        u_name_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        u_name_lbl = Gtk.Label(label=CURRENT_USER, xalign=0)
        u_name_lbl.set_markup(f"<span font='20' weight='bold'>{CURRENT_USER}</span>")
        u_name_row.pack_start(u_name_lbl, False, False, 0)

        badge_cur = Gtk.Label(label="Текущий сеанс")
        add_class(badge_cur, "m3-chip-success")
        u_name_row.pack_start(badge_cur, False, False, 0)

        # Admin status
        users_list = get_system_users()
        cur_is_admin = any(u["name"] == CURRENT_USER and u["is_admin"] for u in users_list)
        badge_role = Gtk.Label(label="Администратор (wheel)" if cur_is_admin else "Стандартный пользователь")
        add_class(badge_role, "m3-chip" if cur_is_admin else "m3-chip-warning")
        u_name_row.pack_start(badge_role, False, False, 0)
        u_info.pack_start(u_name_row, False, False, 0)

        # Display Name row
        fn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        fn_lbl = Gtk.Label(label="Отображаемое имя:", xalign=0)
        add_class(fn_lbl, "card-row-subtitle")
        fn_lbl.set_size_request(140, -1)
        fn_row.pack_start(fn_lbl, False, False, 0)

        cur_gecos = ""
        try:
            cur_gecos = pwd.getpwnam(CURRENT_USER).pw_gecos
        except Exception:
            pass
        self.profile_fullname_entry = Gtk.Entry()
        self.profile_fullname_entry.set_text(cur_gecos)
        self.profile_fullname_entry.set_placeholder_text("Ваше имя или псевдоним")
        self.profile_fullname_entry.set_width_chars(24)
        fn_row.pack_start(self.profile_fullname_entry, False, False, 0)

        save_fn_btn = Gtk.Button(label="Сохранить")
        add_class(save_fn_btn, "btn-tonal")
        save_fn_btn.connect("clicked", self.on_save_my_fullname)
        fn_row.pack_start(save_fn_btn, False, False, 0)
        u_info.pack_start(fn_row, False, False, 0)

        # Badges row for Shell and Home
        cur_shell = "/bin/bash"
        cur_home = str(HOME)
        cur_uid = 1000
        try:
            u_entry = pwd.getpwnam(CURRENT_USER)
            cur_shell = u_entry.pw_shell
            cur_home = u_entry.pw_dir
            cur_uid = u_entry.pw_uid
        except Exception:
            pass

        badges_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        b_home = Gtk.Label(label=f"Папка: {cur_home}")
        add_class(b_home, "m3-chip")
        b_shell = Gtk.Label(label=f"Shell: {cur_shell}")
        add_class(b_shell, "m3-chip")
        b_uid = Gtk.Label(label=f"UID: {cur_uid}")
        add_class(b_uid, "m3-chip")
        badges_row.pack_start(b_home, False, False, 0)
        badges_row.pack_start(b_shell, False, False, 0)
        badges_row.pack_start(b_uid, False, False, 0)
        u_info.pack_start(badges_row, False, False, 0)

        u_top.pack_start(u_info, True, True, 0)
        profile_card.pack_start(u_top, False, False, 0)

        # Avatar controls row
        profile_card.pack_start(self.build_divider(), False, False, 0)
        av_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        av_text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        av_title = Gtk.Label(label="Аватар профиля", xalign=0)
        add_class(av_title, "card-row-title")
        av_sub = Gtk.Label(label="Нажмите на изображение профиля выше, чтобы загрузить фото и настроить кадрирование", xalign=0)
        add_class(av_sub, "card-row-subtitle")
        av_text_box.pack_start(av_title, False, False, 0)
        av_text_box.pack_start(av_sub, False, False, 0)
        av_row.pack_start(av_text_box, True, True, 0)

        btn_crop_cur = Gtk.Button(label="Кадрировать текущий...")
        add_class(btn_crop_cur, "btn-tonal")
        btn_crop_cur.connect("clicked", self.on_crop_current_avatar_clicked)
        av_row.pack_end(btn_crop_cur, False, False, 0)

        btn_reset_av = Gtk.Button(label="Сбросить")
        add_class(btn_reset_av, "btn-tonal")
        btn_reset_av.connect("clicked", self.on_reset_avatar_clicked)
        av_row.pack_end(btn_reset_av, False, False, 0)

        profile_card.pack_start(av_row, False, False, 0)

        # Password management row
        profile_card.pack_start(self.build_divider(), False, False, 0)
        pw_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        pw_text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        pw_title = Gtk.Label(label="Пароль учетной записи", xalign=0)
        add_class(pw_title, "card-row-title")
        pw_sub = Gtk.Label(label="Сменить системный пароль для текущего профиля", xalign=0)
        add_class(pw_sub, "card-row-subtitle")
        pw_text_box.pack_start(pw_title, False, False, 0)
        pw_text_box.pack_start(pw_sub, False, False, 0)
        pw_row.pack_start(pw_text_box, True, True, 0)

        btn_change_pw = Gtk.Button(label="Сменить пароль")
        add_class(btn_change_pw, "btn-tonal")
        btn_change_pw.connect("clicked", lambda _: self.on_change_password_dialog(CURRENT_USER))
        pw_row.pack_end(btn_change_pw, False, False, 0)

        profile_card.pack_start(pw_row, False, False, 0)

        # ----------------------------------------------------------------------
        # Card 2: System User Accounts
        # ----------------------------------------------------------------------
        root.pack_start(self.build_section_header("Учетные записи системы"), False, False, 0)
        users_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        add_class(users_card, "card")
        root.pack_start(users_card, False, False, 0)

        u_header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        u_h_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        u_h_title = Gtk.Label(label="Пользователи операционной системы", xalign=0)
        add_class(u_h_title, "card-title")
        u_h_sub = Gtk.Label(label="Создавайте аккаунты без root (для гостей/членов семьи) или с правами администратора", xalign=0)
        add_class(u_h_sub, "card-subtitle")
        u_h_text.pack_start(u_h_title, False, False, 0)
        u_h_text.pack_start(u_h_sub, False, False, 0)
        u_header_row.pack_start(u_h_text, True, True, 0)

        btn_add_user = Gtk.Button(label="+ Создать пользователя")
        add_class(btn_add_user, "suggested-action")
        btn_add_user.connect("clicked", self.on_create_user_dialog)
        u_header_row.pack_end(btn_add_user, False, False, 0)

        btn_refresh_users = Gtk.Button(label="Обновить")
        add_class(btn_refresh_users, "btn-tonal")
        btn_refresh_users.connect("clicked", lambda _: self.refresh_users_list())
        u_header_row.pack_end(btn_refresh_users, False, False, 0)

        users_card.pack_start(u_header_row, False, False, 0)
        users_card.pack_start(self.build_divider(), False, False, 0)

        self.users_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        users_card.pack_start(self.users_list_box, False, False, 0)
        self.refresh_users_list()

        return scrolled

    def refresh_users_list(self) -> None:
        """Re-populates the list of system accounts."""
        if not hasattr(self, "users_list_box"):
            return
        for child in self.users_list_box.get_children():
            self.users_list_box.remove(child)

        users = get_system_users()
        for idx, u in enumerate(users):
            if idx > 0:
                self.users_list_box.pack_start(self.build_divider(), False, False, 0)

            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
            add_class(row, "card-row")

            av_widget = self.create_avatar_image(u["name"], size=46)
            row.pack_start(av_widget, False, False, 0)

            info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            info_box.set_valign(Gtk.Align.CENTER)

            top_title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            name_lbl = Gtk.Label(label=u["name"], xalign=0)
            add_class(name_lbl, "card-row-title")
            top_title_row.pack_start(name_lbl, False, False, 0)

            if u["gecos"]:
                gecos_lbl = Gtk.Label(label=f"({u['gecos']})", xalign=0)
                add_class(gecos_lbl, "card-row-subtitle")
                top_title_row.pack_start(gecos_lbl, False, False, 0)

            if u["is_admin"]:
                admin_chip = Gtk.Label(label="Администратор")
                add_class(admin_chip, "m3-chip-success")
                top_title_row.pack_start(admin_chip, False, False, 0)
            else:
                user_chip = Gtk.Label(label="Пользователь (без root)")
                add_class(user_chip, "m3-chip")
                top_title_row.pack_start(user_chip, False, False, 0)

            if u["name"] == CURRENT_USER:
                you_chip = Gtk.Label(label="Текущий сеанс")
                add_class(you_chip, "m3-chip-warning")
                top_title_row.pack_start(you_chip, False, False, 0)

            info_box.pack_start(top_title_row, False, False, 0)

            sub_lbl = Gtk.Label(label=f"UID: {u['uid']}  •  Папка: {u['dir']}  •  Shell: {u['shell']}", xalign=0)
            add_class(sub_lbl, "card-row-subtitle")
            info_box.pack_start(sub_lbl, False, False, 0)

            row.pack_start(info_box, True, True, 0)

            actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            actions_box.set_valign(Gtk.Align.CENTER)

            if u["name"] != CURRENT_USER:
                btn_adm = Gtk.Button(label="Снять root" if u["is_admin"] else "Дать root")
                add_class(btn_adm, "btn-tonal")
                btn_adm.connect("clicked", lambda _, name=u["name"], grant=not u["is_admin"]: self.on_toggle_admin(name, grant))
                actions_box.pack_start(btn_adm, False, False, 0)

                btn_pw = Gtk.Button(label="Пароль")
                add_class(btn_pw, "btn-tonal")
                btn_pw.connect("clicked", lambda _, name=u["name"]: self.on_change_password_dialog(name))
                actions_box.pack_start(btn_pw, False, False, 0)

                btn_del = Gtk.Button(label="Удалить")
                add_class(btn_del, "btn-danger")
                btn_del.connect("clicked", lambda _, name=u["name"]: self.on_delete_user_dialog(name))
                actions_box.pack_start(btn_del, False, False, 0)
            else:
                active_chip = Gtk.Label(label="Основной аккаунт")
                add_class(active_chip, "m3-chip")
                actions_box.pack_start(active_chip, False, False, 0)

            row.pack_end(actions_box, False, False, 0)
            self.users_list_box.pack_start(row, False, False, 0)

        self.users_list_box.show_all()

    def on_save_my_fullname(self, _btn: Gtk.Button) -> None:
        new_name = self.profile_fullname_entry.get_text().strip()
        ok, msg = run_user_admin_cmd("set-fullname", CURRENT_USER, new_name)
        if ok:
            self.set_status(f"Имя профиля сохранено: {new_name}")
            self.refresh_users_list()
        else:
            self.set_status(f"Ошибка сохранения имени: {msg}")

    def on_choose_avatar_clicked(self, _btn: Any = None) -> None:
        dialog = Gtk.FileChooserDialog(
            title="Выберите изображение для аватара профиля",
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_button("Отмена", Gtk.ResponseType.CANCEL)
        dialog.add_button("Выбрать", Gtk.ResponseType.OK)

        flt = Gtk.FileFilter()
        flt.set_name("Изображения (*.png, *.jpg, *.jpeg, *.webp)")
        flt.add_mime_type("image/png")
        flt.add_mime_type("image/jpeg")
        flt.add_mime_type("image/webp")
        flt.add_pattern("*.png")
        flt.add_pattern("*.jpg")
        flt.add_pattern("*.jpeg")
        flt.add_pattern("*.webp")
        dialog.add_filter(flt)

        flt_all = Gtk.FileFilter()
        flt_all.set_name("Все файлы")
        flt_all.add_pattern("*")
        dialog.add_filter(flt_all)

        response = dialog.run()
        selected_file = None
        if response == Gtk.ResponseType.OK:
            selected_file = dialog.get_filename()
        dialog.destroy()

        if selected_file and Path(selected_file).is_file():
            try:
                shutil.copy2(selected_file, AVATAR_SOURCE_PATH)
            except Exception:
                pass
            self.on_open_crop_dialog(selected_file)

    def on_crop_current_avatar_clicked(self, _btn: Any = None) -> None:
        if AVATAR_SOURCE_PATH.is_file():
            self.on_open_crop_dialog(str(AVATAR_SOURCE_PATH))
        else:
            cur_face = HOME / ".face"
            if cur_face.is_file():
                self.on_open_crop_dialog(str(cur_face))
            else:
                self.set_status("Сначала выберите изображение для аватара")
                self.on_choose_avatar_clicked(None)

    def on_open_crop_dialog(self, image_path: str | Path) -> None:
        """Opens an interactive Material Design 3 cropping and framing modal dialog."""
        try:
            src_img = Image.open(image_path).convert("RGBA")
        except Exception as e:
            self.set_status(f"Ошибка открытия файла изображения: {e}")
            return

        dialog = Gtk.Dialog(
            title="Настройка кадрирования аватара",
            parent=self,
            modal=True,
            destroy_with_parent=True,
        )
        dialog.set_default_size(480, 620)
        add_class(dialog, "control-center-window")

        content_area = dialog.get_content_area()
        add_class(content_area, "content-area")
        content_area.set_spacing(14)

        d_title = Gtk.Label(label="Кадрирование аватара", xalign=0)
        add_class(d_title, "page-title")
        content_area.pack_start(d_title, False, False, 0)

        d_sub = Gtk.Label(
            label="Настройте масштаб и положение круглой области, чтобы лицо и важные детали отображались идеально.",
            xalign=0,
        )
        add_class(d_sub, "card-row-subtitle")
        d_sub.set_line_wrap(True)
        content_area.pack_start(d_sub, False, False, 0)

        preview_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        preview_card.set_halign(Gtk.Align.CENTER)
        preview_card.set_valign(Gtk.Align.CENTER)

        preview_img = Gtk.Image()
        preview_frame = Gtk.Box()
        add_class(preview_frame, "avatar-frame")
        preview_frame.pack_start(preview_img, False, False, 0)
        preview_card.pack_start(preview_frame, False, False, 0)
        content_area.pack_start(preview_card, False, False, 0)

        controls_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        add_class(controls_card, "card")
        content_area.pack_start(controls_card, False, False, 0)

        # Zoom scale
        zoom_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        z_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        z_title = Gtk.Label(label="Масштаб (Zoom):", xalign=0)
        add_class(z_title, "card-row-title")
        z_val_lbl = Gtk.Label(label="1.00x", xalign=1)
        add_class(z_val_lbl, "card-row-subtitle")
        z_header.pack_start(z_title, True, True, 0)
        z_header.pack_end(z_val_lbl, False, False, 0)
        zoom_box.pack_start(z_header, False, False, 0)

        scale_zoom = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1.0, 3.0, 0.05)
        scale_zoom.set_value(1.0)
        scale_zoom.set_draw_value(False)
        zoom_box.pack_start(scale_zoom, False, False, 0)
        controls_card.pack_start(zoom_box, False, False, 0)

        # Offset Y (Vertical) - Key for face / portrait centering
        y_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        y_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        y_title = Gtk.Label(label="Положение по вертикали (Вверх / Вниз):", xalign=0)
        add_class(y_title, "card-row-title")
        y_val_lbl = Gtk.Label(label="0%", xalign=1)
        add_class(y_val_lbl, "card-row-subtitle")
        y_header.pack_start(y_title, True, True, 0)
        y_header.pack_end(y_val_lbl, False, False, 0)
        y_box.pack_start(y_header, False, False, 0)

        scale_y = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, -1.0, 1.0, 0.02)
        scale_y.set_value(0.0)
        scale_y.set_draw_value(False)
        y_box.pack_start(scale_y, False, False, 0)
        controls_card.pack_start(y_box, False, False, 0)

        # Offset X (Horizontal)
        x_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        x_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        x_title = Gtk.Label(label="Положение по горизонтали (Влево / Вправо):", xalign=0)
        add_class(x_title, "card-row-title")
        x_val_lbl = Gtk.Label(label="0%", xalign=1)
        add_class(x_val_lbl, "card-row-subtitle")
        x_header.pack_start(x_title, True, True, 0)
        x_header.pack_end(x_val_lbl, False, False, 0)
        x_box.pack_start(x_header, False, False, 0)

        scale_x = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, -1.0, 1.0, 0.02)
        scale_x.set_value(0.0)
        scale_x.set_draw_value(False)
        x_box.pack_start(scale_x, False, False, 0)
        controls_card.pack_start(x_box, False, False, 0)

        # Presets
        controls_card.pack_start(self.build_divider(), False, False, 0)
        presets_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        p_label = Gtk.Label(label="Пресеты:", xalign=0)
        add_class(p_label, "card-row-subtitle")
        presets_row.pack_start(p_label, False, False, 0)

        def apply_preset(z: float, ox: float, oy: float):
            scale_zoom.set_value(z)
            scale_x.set_value(ox)
            scale_y.set_value(oy)

        btn_p_center = Gtk.Button(label="По центру")
        add_class(btn_p_center, "btn-tonal")
        btn_p_center.connect("clicked", lambda _: apply_preset(1.0, 0.0, 0.0))
        presets_row.pack_start(btn_p_center, False, False, 0)

        btn_p_face = Gtk.Button(label="Фокус на лицо (верх)")
        add_class(btn_p_face, "btn-tonal")
        btn_p_face.connect("clicked", lambda _: apply_preset(1.2, 0.0, -0.4))
        presets_row.pack_start(btn_p_face, False, False, 0)

        btn_p_close = Gtk.Button(label="Крупный план")
        add_class(btn_p_close, "btn-tonal")
        btn_p_close.connect("clicked", lambda _: apply_preset(1.6, 0.0, -0.2))
        presets_row.pack_start(btn_p_close, False, False, 0)

        controls_card.pack_start(presets_row, False, False, 0)

        # Update preview handler
        def on_values_changed(_w=None):
            z = scale_zoom.get_value()
            ox = scale_x.get_value()
            oy = scale_y.get_value()
            z_val_lbl.set_text(f"{z:.2f}x")
            y_val_lbl.set_text(f"{int(oy * 100):+d}%")
            x_val_lbl.set_text(f"{int(ox * 100):+d}%")
            pix = render_cropped_pixbuf(src_img, zoom=z, offset_x=ox, offset_y=oy, target_size=180)
            if pix:
                preview_img.set_from_pixbuf(pix)

        scale_zoom.connect("value-changed", on_values_changed)
        scale_x.connect("value-changed", on_values_changed)
        scale_y.connect("value-changed", on_values_changed)

        # Initial render
        on_values_changed()

        # Dialog Buttons
        dialog.add_button("Отмена", Gtk.ResponseType.CANCEL)
        apply_btn = dialog.add_button("Сохранить аватар", Gtk.ResponseType.OK)
        add_class(apply_btn, "btn-primary")

        cancel_btn = dialog.get_widget_for_response(Gtk.ResponseType.CANCEL)
        if cancel_btn:
            add_class(cancel_btn, "btn-tonal")

        dialog.show_all()
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            z = scale_zoom.get_value()
            ox = scale_x.get_value()
            oy = scale_y.get_value()
            ok = save_custom_cropped_avatar(src_img, zoom=z, offset_x=ox, offset_y=oy, target_user=CURRENT_USER)
            if ok:
                self.update_profile_avatar_display()
                self.refresh_users_list()
                self.set_status("Аватар профиля успешно сохранен и применен")
            else:
                self.set_status("Ошибка сохранения кадрированного аватара")

        dialog.destroy()

    def on_reset_avatar_clicked(self, _btn: Gtk.Button) -> None:
        remove_user_avatar(CURRENT_USER)
        self.update_profile_avatar_display()
        self.refresh_users_list()
        self.set_status("Аватар профиля сброшен")

    def on_toggle_admin(self, username: str, grant: bool) -> None:
        ok, msg = run_user_admin_cmd("toggle-admin", username, "1" if grant else "0")
        if ok:
            self.refresh_users_list()
            self.set_status(f"Права администратора для '{username}' {'предоставлены' if grant else 'отозваны'}")
        else:
            self.set_status(f"Ошибка изменения прав: {msg}")

    def on_create_user_dialog(self, _btn: Gtk.Button | None = None) -> None:
        dialog = Gtk.Dialog(
            title="Создание нового пользователя",
            parent=self,
            modal=True,
            destroy_with_parent=True,
        )
        dialog.set_default_size(460, 480)
        add_class(dialog, "control-center-window")

        content_area = dialog.get_content_area()
        add_class(content_area, "content-area")
        content_area.set_spacing(12)

        d_title = Gtk.Label(label="Новая учетная запись", xalign=0)
        add_class(d_title, "page-title")
        content_area.pack_start(d_title, False, False, 0)

        d_sub = Gtk.Label(
            label="Создайте профиль для гостя или другого пользователя. Доступ root можно отключить.",
            xalign=0,
        )
        add_class(d_sub, "card-row-subtitle")
        d_sub.set_line_wrap(True)
        content_area.pack_start(d_sub, False, False, 0)

        form_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        add_class(form_card, "card")

        # Username
        u_lbl = Gtk.Label(label="Имя пользователя (логин латиницей):", xalign=0)
        add_class(u_lbl, "card-row-title")
        form_card.pack_start(u_lbl, False, False, 0)
        u_entry = Gtk.Entry()
        u_entry.set_placeholder_text("например: guest, alex, kids")
        form_card.pack_start(u_entry, False, False, 0)

        # Fullname
        fn_lbl = Gtk.Label(label="Отображаемое имя (ФИО / Название):", xalign=0)
        add_class(fn_lbl, "card-row-title")
        form_card.pack_start(fn_lbl, False, False, 0)
        fn_entry = Gtk.Entry()
        fn_entry.set_placeholder_text("например: Гость или Рабочий профиль")
        form_card.pack_start(fn_entry, False, False, 0)

        # Shell
        sh_lbl = Gtk.Label(label="Командная оболочка (Shell):", xalign=0)
        add_class(sh_lbl, "card-row-title")
        form_card.pack_start(sh_lbl, False, False, 0)
        sh_combo = Gtk.ComboBoxText()
        for sh in ["/bin/bash", "/usr/bin/fish", "/bin/zsh", "/bin/sh"]:
            sh_combo.append_text(sh)
        sh_combo.set_active(0)
        form_card.pack_start(sh_combo, False, False, 0)

        # Passwords
        p1_lbl = Gtk.Label(label="Пароль:", xalign=0)
        add_class(p1_lbl, "card-row-title")
        form_card.pack_start(p1_lbl, False, False, 0)
        p1_entry = Gtk.Entry()
        p1_entry.set_visibility(False)
        form_card.pack_start(p1_entry, False, False, 0)

        p2_lbl = Gtk.Label(label="Повтор пароля:", xalign=0)
        add_class(p2_lbl, "card-row-title")
        form_card.pack_start(p2_lbl, False, False, 0)
        p2_entry = Gtk.Entry()
        p2_entry.set_visibility(False)
        form_card.pack_start(p2_entry, False, False, 0)

        # Admin privilege switch
        form_card.pack_start(self.build_divider(), False, False, 0)
        adm_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        adm_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        adm_t = Gtk.Label(label="Права администратора (root/sudo)", xalign=0)
        add_class(adm_t, "card-row-title")
        adm_s = Gtk.Label(
            label="Отключите для гостя или безопасного доступа без прав изменять систему.",
            xalign=0,
        )
        add_class(adm_s, "card-row-subtitle")
        adm_s.set_line_wrap(True)
        adm_text.pack_start(adm_t, False, False, 0)
        adm_text.pack_start(adm_s, False, False, 0)
        adm_row.pack_start(adm_text, True, True, 0)

        adm_switch = Gtk.Switch()
        adm_switch.set_active(False)
        adm_switch.set_valign(Gtk.Align.CENTER)
        adm_row.pack_end(adm_switch, False, False, 0)
        form_card.pack_start(adm_row, False, False, 0)

        content_area.pack_start(form_card, False, False, 0)

        err_lbl = Gtk.Label(label="", xalign=0)
        add_class(err_lbl, "card-row-subtitle")
        err_lbl.set_line_wrap(True)
        content_area.pack_start(err_lbl, False, False, 0)

        # Buttons
        dialog.add_button("Отмена", Gtk.ResponseType.CANCEL)
        create_btn = dialog.add_button("Создать профиль", Gtk.ResponseType.OK)
        add_class(create_btn, "btn-primary")

        cancel_btn = dialog.get_widget_for_response(Gtk.ResponseType.CANCEL)
        if cancel_btn:
            add_class(cancel_btn, "btn-tonal")

        dialog.show_all()

        while True:
            response = dialog.run()
            if response != Gtk.ResponseType.OK:
                dialog.destroy()
                break

            u_name = u_entry.get_text().strip().lower()
            if not u_name:
                err_lbl.set_markup("<span color='#ff6b6b'>Имя пользователя обязательно для заполнения.</span>")
                continue
            if not re.match(r"^[a-z_][a-z0-9_-]*$", u_name):
                err_lbl.set_markup("<span color='#ff6b6b'>Имя пользователя должно состоять из строчных латинских букв, цифр и дефиса.</span>")
                continue

            p1 = p1_entry.get_text()
            p2 = p2_entry.get_text()
            if p1 != p2:
                err_lbl.set_markup("<span color='#ff6b6b'>Введенные пароли не совпадают.</span>")
                continue

            fn = fn_entry.get_text().strip()
            shell = sh_combo.get_active_text() or "/bin/bash"
            is_adm = "1" if adm_switch.get_active() else "0"

            ok, msg = run_user_admin_cmd("create", u_name, fn, shell, is_adm, p1)
            if ok:
                self.refresh_users_list()
                self.set_status(f"Пользователь '{u_name}' успешно создан")
                dialog.destroy()
                break
            else:
                err_lbl.set_markup(f"<span color='#ff6b6b'>Ошибка создания: {msg}</span>")

    def on_change_password_dialog(self, username: str) -> None:
        dialog = Gtk.Dialog(
            title=f"Смена пароля — {username}",
            parent=self,
            modal=True,
            destroy_with_parent=True,
        )
        dialog.set_default_size(400, 260)
        add_class(dialog, "control-center-window")

        content_area = dialog.get_content_area()
        add_class(content_area, "content-area")
        content_area.set_spacing(10)

        d_title = Gtk.Label(label=f"Пароль для {username}", xalign=0)
        add_class(d_title, "page-title")
        content_area.pack_start(d_title, False, False, 0)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        add_class(card, "card")

        p1_lbl = Gtk.Label(label="Новый пароль:", xalign=0)
        add_class(p1_lbl, "card-row-title")
        card.pack_start(p1_lbl, False, False, 0)
        p1_entry = Gtk.Entry()
        p1_entry.set_visibility(False)
        card.pack_start(p1_entry, False, False, 0)

        p2_lbl = Gtk.Label(label="Подтверждение пароля:", xalign=0)
        add_class(p2_lbl, "card-row-title")
        card.pack_start(p2_lbl, False, False, 0)
        p2_entry = Gtk.Entry()
        p2_entry.set_visibility(False)
        card.pack_start(p2_entry, False, False, 0)

        content_area.pack_start(card, False, False, 0)

        err_lbl = Gtk.Label(label="", xalign=0)
        content_area.pack_start(err_lbl, False, False, 0)

        dialog.add_button("Отмена", Gtk.ResponseType.CANCEL)
        save_btn = dialog.add_button("Сохранить пароль", Gtk.ResponseType.OK)
        add_class(save_btn, "btn-primary")

        cancel_btn = dialog.get_widget_for_response(Gtk.ResponseType.CANCEL)
        if cancel_btn:
            add_class(cancel_btn, "btn-tonal")

        dialog.show_all()

        while True:
            response = dialog.run()
            if response != Gtk.ResponseType.OK:
                dialog.destroy()
                break

            p1 = p1_entry.get_text()
            p2 = p2_entry.get_text()
            if not p1:
                err_lbl.set_markup("<span color='#ff6b6b'>Пароль не может быть пустым.</span>")
                continue
            if p1 != p2:
                err_lbl.set_markup("<span color='#ff6b6b'>Пароли не совпадают.</span>")
                continue

            ok, msg = run_user_admin_cmd("set-password", username, p1)
            if ok:
                self.set_status(f"Пароль для '{username}' обновлен")
                dialog.destroy()
                break
            else:
                err_lbl.set_markup(f"<span color='#ff6b6b'>Ошибка: {msg}</span>")

    def on_delete_user_dialog(self, username: str) -> None:
        dialog = Gtk.Dialog(
            title=f"Удалить пользователя {username}?",
            parent=self,
            modal=True,
            destroy_with_parent=True,
        )
        dialog.set_default_size(440, 220)
        add_class(dialog, "control-center-window")

        content_area = dialog.get_content_area()
        add_class(content_area, "content-area")
        content_area.set_spacing(12)

        d_title = Gtk.Label(label="Подтверждение удаления", xalign=0)
        add_class(d_title, "page-title")
        content_area.pack_start(d_title, False, False, 0)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        add_class(card, "card")

        msg_lbl = Gtk.Label(
            label=f"Вы действительно хотите удалить учетную запись '{username}'?",
            xalign=0,
        )
        add_class(msg_lbl, "card-row-title")
        card.pack_start(msg_lbl, False, False, 0)

        chk_del_home = Gtk.CheckButton(label=f"Удалить домашнюю папку (/home/{username}) и все файлы")
        chk_del_home.set_active(True)
        card.pack_start(chk_del_home, False, False, 0)

        content_area.pack_start(card, False, False, 0)

        dialog.add_button("Отмена", Gtk.ResponseType.CANCEL)
        del_btn = dialog.add_button("Удалить пользователя", Gtk.ResponseType.OK)
        add_class(del_btn, "btn-danger")

        cancel_btn = dialog.get_widget_for_response(Gtk.ResponseType.CANCEL)
        if cancel_btn:
            add_class(cancel_btn, "btn-tonal")

        dialog.show_all()
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            del_home = "1" if chk_del_home.get_active() else "0"
            ok, msg = run_user_admin_cmd("delete", username, del_home)
            if ok:
                self.refresh_users_list()
                self.set_status(f"Пользователь '{username}' удален")
            else:
                self.set_status(f"Ошибка удаления: {msg}")

        dialog.destroy()

    # --------------------------------------------------------------------------
    # Page 9: About System
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
        subtitle = Gtk.Label(label="Сведения об аппаратном обеспечении и операционной системе", xalign=0)
        add_class(subtitle, "page-subtitle")
        header.pack_start(title, False, False, 0)
        header.pack_start(subtitle, False, False, 0)
        root.pack_start(header, False, False, 0)

        root.pack_start(self.build_section_header("Характеристики оборудования"), False, False, 0)
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
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

            lbl_t = Gtk.Label(label=title_str, xalign=0)
            add_class(lbl_t, "card-row-title")
            lbl_t.set_size_request(220, -1)

            lbl_v = Gtk.Label(label=val_str, xalign=0)
            add_class(lbl_v, "card-row-subtitle")
            lbl_v.set_line_wrap(True)
            lbl_v.set_selectable(True)

            row.pack_start(lbl_t, False, False, 0)
            row.pack_start(lbl_v, True, True, 0)
            card.pack_start(row, False, False, 0)

        root.pack_start(self.build_section_header("Конфигурация окружения"), False, False, 0)
        rice_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        add_class(rice_card, "card")
        root.pack_start(rice_card, False, False, 0)

        r_title = Gtk.Label(label="Arch Linux i3wm Rice", xalign=0)
        add_class(r_title, "card-title")
        r_sub = Gtk.Label(
            label="Конфигурация оптимизирована для сверхнизкого инпут-лага, киберспортивных шутеров и плавной работы.\n"
                  "Интерфейс спроектирован по спецификации Material Design 3 (Google M3).",
            xalign=0
        )
        add_class(r_sub, "card-row-subtitle")
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
        add_class(hint_lbl, "card-row-subtitle")
        bar.pack_end(hint_lbl, False, False, 0)

        return bar

    def set_status(self, text: str) -> None:
        self.status_lbl.set_text(text)


def main() -> None:
    GLib.set_prgname("system-control-center")
    GLib.set_application_name("Параметры системы")
    load_css()
    win = ControlCenterWindow()
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
