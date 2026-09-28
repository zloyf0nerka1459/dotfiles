#!/usr/bin/env python3
import json
import os
import subprocess

colors_file = os.path.expanduser("~/.cache/wal/colors.json")
if not os.path.exists(colors_file):
    exit(0)

try:
    with open(colors_file) as f:
        data = json.load(f)
except Exception:
    exit(0)

colors = data.get("colors", {})
special = data.get("special", {})
bg = special.get("background", colors.get("color0", "#1f1312"))
fg = special.get("foreground", colors.get("color15", "#c7c4c3"))
accent = colors.get("color4", colors.get("color2", "#ac9960"))
active = special.get("cursor", accent)

replacements = {f"{{color{i}}}": colors.get(f"color{i}", "") for i in range(16)}
replacements["{active}"] = active
replacements["{background}"] = bg
replacements["{foreground}"] = fg

# 1. Update FlatColor in ~/.local/share/themes and ~/.themes
search_paths = [
    os.path.expanduser("~/.local/share/themes/FlatColor"),
    os.path.expanduser("~/.themes/FlatColor"),
]

for flatcolor_dir in search_paths:
    if not os.path.isdir(flatcolor_dir):
        continue
    for sub in ["gtk-2.0", "gtk-3.0", "gtk-3.20"]:
        sub_dir = os.path.join(flatcolor_dir, sub)
        if not os.path.isdir(sub_dir):
            continue
        for fname in os.listdir(sub_dir):
            if fname.endswith(".base"):
                base_path = os.path.join(sub_dir, fname)
                target_path = os.path.join(sub_dir, fname[:-5])
                try:
                    with open(base_path, "r", encoding="utf-8") as bf:
                        content = bf.read()
                    for k, v in replacements.items():
                        if v:
                            content = content.replace(k, v)
                    with open(target_path, "w", encoding="utf-8") as tf:
                        tf.write(content)
                except Exception:
                    pass

# 2. Write dynamic GTK 3.0 CSS in ~/.config/gtk-3.0/gtk.css
gtk3_dir = os.path.expanduser("~/.config/gtk-3.0")
os.makedirs(gtk3_dir, exist_ok=True)
gtk3_css_path = os.path.join(gtk3_dir, "gtk.css")
gtk3_css_content = f"""/* Dynamic GTK3 Theme Variables generated from Pywal */
@define-color theme_bg_color {bg};
@define-color theme_fg_color {fg};
@define-color theme_base_color {bg};
@define-color theme_text_color {fg};
@define-color theme_selected_bg_color {accent};
@define-color theme_selected_fg_color #ffffff;
@define-color theme_tooltip_bg_color {bg};
@define-color theme_tooltip_fg_color {fg};

@define-color bg_color {bg};
@define-color fg_color {fg};
@define-color base_color {bg};
@define-color text_color {fg};
@define-color selected_bg_color {accent};
@define-color selected_fg_color #ffffff;
@define-color tooltip_bg_color {bg};
@define-color tooltip_fg_color {fg};
"""
try:
    with open(gtk3_css_path, "w", encoding="utf-8") as f:
        f.write(gtk3_css_content)
except Exception:
    pass

# 3. Synchronize GSettings so all GTK apps respect FlatColor & dark mode
try:
    subprocess.run(["gsettings", "set", "org.gnome.desktop.interface", "gtk-theme", "FlatColor"], check=False)
    subprocess.run(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", "prefer-dark"], check=False)
except Exception:
    pass
