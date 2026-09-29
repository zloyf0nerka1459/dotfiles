#!/usr/bin/env python3

from __future__ import annotations

import html
import os
import shutil
import subprocess
from pathlib import Path

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk

from system_control_center import INPUT_SCRIPT_PATH, generate_input_script, load_input_profiles, write_text


HOME = Path.home()
CONFIG_HOME = HOME / ".config"
STATE_ROOT = HOME / ".local" / "state" / "fonera-dots"
MARKER_PATH = STATE_ROOT / "postinstall-wizard-pending"
INSTALL_STATE_PATH = STATE_ROOT / "install-state.env"
ENV_DIR = CONFIG_HOME / "environment.d"
ENV_FILE = ENV_DIR / "90-fonera-dots-locale.conf"

APP_CSS = """
window.postinstall-wizard {
    background-image: linear-gradient(155deg, #050b14 0%, #101827 48%, #18263a 100%);
    color: #e5edf6;
}

.wizard-root {
    padding: 18px;
}

.hero {
    background-image: linear-gradient(135deg, rgba(34, 197, 94, 0.14), rgba(56, 189, 248, 0.08) 42%, rgba(9, 13, 20, 0.92) 100%);
    border: 1px solid rgba(148, 163, 184, 0.24);
    border-radius: 26px;
    padding: 22px 24px;
    box-shadow: 0 20px 44px rgba(2, 6, 23, 0.44);
}

.hero-title {
    color: #f8fafc;
    font-size: 27px;
    font-weight: 800;
}

.hero-subtitle {
    color: rgba(203, 213, 225, 0.92);
    font-size: 13px;
}

.card {
    background-color: rgba(15, 23, 42, 0.78);
    border: 1px solid rgba(71, 85, 105, 0.42);
    border-radius: 22px;
    padding: 18px 20px;
}

.card-title {
    color: #f8fafc;
    font-size: 17px;
    font-weight: 800;
}

.card-subtitle {
    color: #94a3b8;
    font-size: 12px;
}

.muted {
    color: #94a3b8;
    font-size: 12px;
}

entry,
combobox,
button {
    border-radius: 14px;
}

entry,
combobox {
    background-color: rgba(15, 23, 42, 0.9);
    color: #f8fafc;
    border: 1px solid rgba(71, 85, 105, 0.62);
    padding: 10px 12px;
}

button {
    background-image: none;
    background-color: rgba(30, 41, 59, 0.96);
    color: #e2e8f0;
    border: 1px solid rgba(71, 85, 105, 0.58);
    padding: 11px 18px;
}

button:hover {
    background-color: rgba(51, 65, 85, 0.96);
}

button.suggested-action {
    background-color: #38bdf8;
    border-color: #7dd3fc;
    color: #082f49;
}
"""


def add_class(widget: Gtk.Widget, *classes: str) -> Gtk.Widget:
    context = widget.get_style_context()
    for class_name in classes:
        context.add_class(class_name)
    return widget


def load_css() -> None:
    provider = Gtk.CssProvider()
    provider.load_from_data(APP_CSS.encode("utf-8"))
    screen = Gdk.Screen.get_default()
    if screen is not None:
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, text=True, capture_output=True, check=False)
    except FileNotFoundError as error:
        return subprocess.CompletedProcess(command, 127, "", str(error))


def read_install_state() -> dict[str, str]:
    data: dict[str, str] = {}
    if not INSTALL_STATE_PATH.exists():
        return data

    for raw_line in INSTALL_STATE_PATH.read_text(encoding="utf-8").splitlines():
        if not raw_line or "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def read_current_timezone() -> str:
    output = run(["timedatectl", "show", "--property=Timezone", "--value"])
    return output.stdout.strip() or "UTC"


def read_current_locale() -> str:
    return os.environ.get("LANG", "en_US.UTF-8")


def read_keyboard_settings() -> tuple[str, str]:
    layouts = "us,ru"
    option = "grp:win_space_toggle"

    if not INPUT_SCRIPT_PATH.exists():
        return layouts, option

    for line in INPUT_SCRIPT_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("# SCC_KEYBOARD_LAYOUTS="):
            layouts = line.split("=", 1)[1].strip() or layouts
        elif line.startswith("# SCC_KEYBOARD_OPTION="):
            option = line.split("=", 1)[1].strip()

    return layouts, option


def locale_choices() -> list[str]:
    output = run(["locale", "-a"])
    candidates = {item.strip().replace(".utf8", ".UTF-8") for item in output.stdout.splitlines() if item.strip()}
    choices = sorted(item for item in candidates if "UTF-8" in item)
    for fallback in ("en_US.UTF-8", "ru_RU.UTF-8"):
        if fallback not in choices:
            choices.insert(0, fallback)
    return choices


class SetupWizard(Gtk.Window):
    def __init__(self) -> None:
        super().__init__(title="Fonera Dots Setup")
        self.install_state = read_install_state()
        self.set_default_size(760, 620)
        self.set_position(Gtk.WindowPosition.CENTER)
        add_class(self, "postinstall-wizard")

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        add_class(root, "wizard-root")
        self.add(root)

        root.pack_start(self.build_hero(), False, False, 0)
        root.pack_start(self.build_time_card(), False, False, 0)
        root.pack_start(self.build_keyboard_card(), False, False, 0)
        root.pack_start(self.build_footer_card(), False, False, 0)
        root.pack_end(self.build_actions(), False, False, 0)

    def build_text(
        self,
        text: str = "",
        *,
        markup: str | None = None,
        xalign: float = 0.0,
        wrap: bool = False,
        classes: tuple[str, ...] = (),
    ) -> Gtk.Label:
        label = Gtk.Label()
        label.set_xalign(xalign)
        label.set_wrap(wrap)
        if markup is not None:
            label.set_markup(markup)
        else:
            label.set_text(text)
        add_class(label, *classes)
        return label

    def build_card_shell(self, title: str, subtitle: str) -> Gtk.Box:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        add_class(card, "card")
        card.pack_start(self.build_text(title, classes=("card-title",)), False, False, 0)
        card.pack_start(self.build_text(subtitle, wrap=True, classes=("card-subtitle",)), False, False, 0)
        return card

    def build_form_row(self, label_text: str, widget: Gtk.Widget) -> Gtk.Box:
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        row.pack_start(self.build_text(label_text, classes=("muted",)), False, False, 0)
        row.pack_start(widget, False, False, 0)
        return row

    def build_hero(self) -> Gtk.Widget:
        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        add_class(hero, "hero")

        monitor = self.install_state.get("INSTALL_MONITOR", "auto")
        backup_dir = self.install_state.get("INSTALL_BACKUP_DIR", "not recorded")
        safe_monitor = html.escape(monitor)
        safe_backup = html.escape(backup_dir)

        hero.pack_start(self.build_text("Добро пожаловать в Fonera Dots", classes=("hero-title",)), False, False, 0)
        hero.pack_start(
            self.build_text(
                "Финальный штрих после установки: время, язык, раскладки и X11-ввод. Потом можно спокойно перейти в advanced control center.",
                wrap=True,
                classes=("hero-subtitle",),
            ),
            False,
            False,
            0,
        )
        hero.pack_start(
            self.build_text(
                markup=(
                    f"Polybar monitor: <b>{safe_monitor}</b>\n"
                    f"Backup: <span font_desc='JetBrainsMono Nerd Font 10'>{safe_backup}</span>"
                ),
                wrap=True,
                classes=("hero-subtitle",),
            ),
            False,
            False,
            0,
        )
        return hero

    def build_time_card(self) -> Gtk.Widget:
        card = self.build_card_shell(
            "Время и язык",
            "Часовой пояс попробую отправить в systemd через polkit, а locale сразу сохраню в user environment, чтобы приложения подтянули её без ручной возни.",
        )

        self.timezone_entry = Gtk.Entry(text=read_current_timezone())
        self.locale_combo = Gtk.ComboBoxText.new_with_entry()
        for candidate in locale_choices():
            self.locale_combo.append_text(candidate)
        self.locale_combo.get_child().set_text(read_current_locale())

        grid = Gtk.Grid(column_spacing=14, row_spacing=12)
        grid.attach(self.build_form_row("Timezone", self.timezone_entry), 0, 0, 1, 1)
        grid.attach(self.build_form_row("Locale", self.locale_combo), 1, 0, 1, 1)
        card.pack_start(grid, False, False, 0)
        return card

    def build_keyboard_card(self) -> Gtk.Widget:
        card = self.build_card_shell(
            "Раскладки и X11 profile",
            "Раскладка хранится в отдельном profile-script и поднимается на старте i3. Такой путь стабильнее обычного голого setxkbmap в конфиге.",
        )

        layouts, option = read_keyboard_settings()
        self.layouts_entry = Gtk.Entry(text=layouts)
        self.option_entry = Gtk.Entry(text=option)

        grid = Gtk.Grid(column_spacing=14, row_spacing=12)
        grid.attach(self.build_form_row("Keyboard layouts", self.layouts_entry), 0, 0, 1, 1)
        grid.attach(self.build_form_row("Switch option", self.option_entry), 1, 0, 1, 1)
        card.pack_start(grid, False, False, 0)
        return card

    def build_footer_card(self) -> Gtk.Widget:
        card = self.build_card_shell(
            "Что будет после Apply",
            "Обновлю input-profile, дёрну reload i3 и оставлю всё в таком виде, чтобы это переживало следующий логин и reload без сюрпризов.",
        )
        self.status_label = self.build_text("Статус: ждёт применения.", wrap=True, classes=("muted",))
        card.pack_start(self.status_label, False, False, 0)
        return card

    def build_actions(self) -> Gtk.Widget:
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        later_button = Gtk.Button(label="Позже")
        later_button.connect("clicked", self.on_later_clicked)
        actions.pack_start(later_button, False, False, 0)

        advanced_button = Gtk.Button(label="Advanced")
        advanced_button.connect("clicked", self.on_advanced_clicked)
        actions.pack_end(advanced_button, False, False, 0)

        apply_button = Gtk.Button(label="Apply")
        add_class(apply_button, "suggested-action")
        apply_button.connect("clicked", self.on_apply_clicked)
        actions.pack_end(apply_button, False, False, 0)
        return actions

    def show_dialog(self, message_type: Gtk.MessageType, title: str, message: str) -> None:
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=message_type,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def set_status(self, message: str) -> None:
        self.status_label.set_text(f"Статус: {message}")

    def selected_locale(self) -> str:
        child = self.locale_combo.get_child()
        if isinstance(child, Gtk.Entry):
            return child.get_text().strip() or "en_US.UTF-8"
        return "en_US.UTF-8"

    def write_locale_environment(self, locale_value: str) -> None:
        ENV_DIR.mkdir(parents=True, exist_ok=True)
        write_text(ENV_FILE, f"LANG={locale_value}\nLC_TIME={locale_value}\n")
        run(["dbus-update-activation-environment", "--systemd", f"LANG={locale_value}", f"LC_TIME={locale_value}"])
        run(["systemctl", "--user", "import-environment", "LANG", "LC_TIME"])

    def apply_timezone(self, timezone: str) -> str | None:
        if not timezone:
            return "Timezone пустой, поэтому пропустил."

        direct = run(["timedatectl", "set-timezone", timezone])
        if direct.returncode == 0:
            return None

        if shutil.which("pkexec") is not None:
            via_pkexec = run(["pkexec", "timedatectl", "set-timezone", timezone])
            if via_pkexec.returncode == 0:
                return None
            return via_pkexec.stderr.strip() or direct.stderr.strip() or "Не удалось применить timezone через pkexec."

        return direct.stderr.strip() or "Не удалось применить timezone. Нет pkexec."

    def on_later_clicked(self, _button: Gtk.Button) -> None:
        self.set_status("Окно закрыто без применения. Мастер всплывёт снова на следующем входе.")
        self.close()

    def on_advanced_clicked(self, _button: Gtk.Button) -> None:
        launch_script = CONFIG_HOME / "system-control-center" / "launch.sh"
        if launch_script.exists():
            subprocess.Popen(["bash", str(launch_script)])
        self.close()

    def on_apply_clicked(self, _button: Gtk.Button) -> None:
        timezone_value = self.timezone_entry.get_text().strip()
        locale_value = self.selected_locale()
        layouts = self.layouts_entry.get_text().strip() or "us,ru"
        option = self.option_entry.get_text().strip()
        keyboard_settings = {"keyboard_layouts": layouts, "keyboard_option": option}
        warnings: list[str] = []

        try:
            profiles = load_input_profiles()
            write_text(INPUT_SCRIPT_PATH, generate_input_script(profiles, keyboard_settings))
            INPUT_SCRIPT_PATH.chmod(0o755)
            self.write_locale_environment(locale_value)

            timezone_warning = self.apply_timezone(timezone_value)
            if timezone_warning:
                warnings.append(timezone_warning)

            run(["bash", str(INPUT_SCRIPT_PATH)])
            run(["i3-msg", "reload"])

            if MARKER_PATH.exists():
                MARKER_PATH.unlink()

            if warnings:
                self.set_status("Применено, но не совсем без шероховатостей.")
                self.show_dialog(
                    Gtk.MessageType.WARNING,
                    "Настройки сохранены",
                    "Основное применилось, но есть нюанс:\n\n" + "\n".join(warnings),
                )
            else:
                self.set_status("Всё применилось аккуратно.")
                self.show_dialog(
                    Gtk.MessageType.INFO,
                    "Готово",
                    "Время, locale и раскладки сохранены. Для более тонкой доводки можно открыть advanced control center.",
                )
            self.close()
        except Exception as error:
            self.set_status("Поймал ошибку и ничего не скрываю.")
            self.show_dialog(Gtk.MessageType.ERROR, "Не удалось применить настройки", str(error))


def main() -> None:
    load_css()
    window = SetupWizard()
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
