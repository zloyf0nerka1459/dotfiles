#!/usr/bin/env python3
import os
import json

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
active = special.get("cursor", colors.get("color4", "#ac9960"))

replacements = {f"{{color{i}}}": colors.get(f"color{i}", "") for i in range(16)}
replacements["{active}"] = active
replacements["{background}"] = special.get("background", colors.get("color0", "#1f1312"))
replacements["{foreground}"] = special.get("foreground", colors.get("color15", "#c7c4c3"))

# Search in both ~/.local/share/themes and ~/.themes
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
