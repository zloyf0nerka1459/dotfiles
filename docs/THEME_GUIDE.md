# 🎨 Руководство по темам оформления и кастомизации EWW

> В этом руководстве подробно описано, как устроена система тем в рисовом окружении Arch Linux (i3 + EWW + Picom + Pywal), как создать свою собственную тему и как привязать к ней индивидуальный стиль панелей EWW.

---

## 📂 1. Структура темы

Все темы располагаются в директории `~/.config/themes/<theme-slug>/`:

```text
~/.config/themes/my-awesome-theme/
├── theme.conf         # Метаданные темы
├── wall.jpg           # Обои рабочего стола (1080p, 1440p, 4K)
├── thumb.png          # Миниатюра 16:9 (320x180) со скругленными углами для Rofi
└── theme-eww.scss     # (Опционально) Индивидуальные стили панелей и виджетов EWW
```

### Файл `theme.conf`
Содержит базовую конфигурацию темы:
```ini
name="🌸 Сакура"
description="Весенняя тема в пастельных тонах"
wallpaper="wall.jpg"
author="fonera"
created_at="2026-09-30 15:00:00"
```

---

## ⚡ 2. Быстрое создание темы из картинки

Вы можете превратить любую картинку в готовую тему всего одной командой:

```bash
theme-create ~/Downloads/cyberpunk.jpg "🌆 Cyberpunk 2077"
```

Инструмент автоматически:
1. Создаст папку темы `~/.config/themes/cyberpunk-2077`.
2. Скопирует обои и бережно сгенерирует закругленную миниатюру 16:9 (`thumb.png`).
3. Создаст метаданные `theme.conf`.
4. Создаст готовый шаблон `theme-eww.scss`.
5. Тема мгновенно появится в графическом селекторе по нажатию **`Mod + T`**!

---

## 🖌️ 3. Привязка стилей EWW (`theme-eww.scss`)

### Как это работает под капотом:
1. При переключении темы (`theme-apply.sh`, селектор `Mod+T` или `dots theme <имя>`) скрипт проверяет наличие `theme-eww.scss`.
2. Если файл найден, он копируется в `~/.config/eww/theme-override.scss`.
3. Базовый `~/.config/eww/eww.scss` импортирует `theme-override.scss` в самом конце, переопределяя внешний вид панелей.
4. Вызывается `eww reload`, и панели обновляются мгновенно и бесшовно без перезагрузки системы.

### Доступные динамические переменные цветов (Pywal):
Все цвета генерируются автоматически на основе палитры обоев:
- `$background`, `$foreground` — основной фон и цвет текста
- `$color0`..`$color15` — 16 терминальных цветов палитры
- `$accent` — ключевой динамический акцентный цвет

---

## 📐 4. Основные SCSS-классы для кастомизации

| Селектор | Описание элемента |
| :--- | :--- |
| `.bar-container` | Основной фон верхней и нижней полосы панелей |
| `.top-bar` | Верхняя панель (граница снизу, отступы) |
| `.bottom-bar` | Нижняя панель задач (граница сверху, отступы) |
| `.chip` | Виджеты-чипы (часы, громкость, раскладка, сеть) |
| `.chip:hover` | Состояние чипа при наведении курсора |
| `.ws-btn` | Кнопка рабочего стола (воркспейса) |
| `.ws-btn.focused` | **Активный (текущий) рабочий стол** |
| `.ws-btn.occupied` | Рабочий стол, на котором есть запущенные окна |
| `.taskbar` | Контейнер запущенных окон на нижней панели |
| `.task-btn` | Кнопка запущенного окна в панели задач |
| `.task-btn.active` | Окно в активном фокусе |
| `.power-chip` | Кнопка питания справа вверху |
| `.date-chip` | Центральный блок даты и часов |
| `.dashboard-card` | Всплывающее меню календаря и погоды |
| `.net-card` | Всплывающая карточка управления сетью и Wi-Fi |

---

## 💡 5. Готовые примеры и рецепты

### Пример 1: Пастельные закругленные пилюли (Стиль Anime / Aruko)
```scss
.bar-container {
  background-color: rgba($color0, 0.94);
  border-bottom: 2px solid rgba($color4, 0.6);
}
.chip {
  border-radius: 12px;
  background-color: rgba($color8, 0.25);
  border: 1px solid rgba($color4, 0.4);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
}
.ws-btn.focused {
  background-color: $color4;
  color: $color0;
  border-radius: 10px;
  font-weight: 800;
  box-shadow: 0 0 8px rgba($color4, 0.6);
}
```

### Пример 2: Киберпанк и Неоновое свечение (Стиль Tokyo Cyber)
```scss
.bar-container {
  background-color: rgba(#0a0b10, 0.96);
  border-bottom: 2px solid #00f0ff;
  box-shadow: 0 0 12px rgba(0, 240, 255, 0.35);
}
.bottom-bar {
  border-top: 2px solid #ff007f;
  box-shadow: 0 0 12px rgba(255, 0, 127, 0.35);
}
.chip {
  border-radius: 2px;
  background-color: rgba(#161824, 0.85);
  border: 1px solid rgba(#00f0ff, 0.5);
}
.ws-btn.focused {
  background-color: #00f0ff;
  color: #000000;
  font-weight: 900;
  box-shadow: 0 0 10px #00f0ff;
}
.ws-btn.occupied {
  color: #ff007f;
}
```

### Пример 3: Скандинавский минимализм (Стиль Nord)
```scss
.bar-container {
  background-color: rgba(#2e3440, 0.96);
  border-bottom: 1px solid #4c566a;
}
.chip {
  border-radius: 4px;
  background-color: rgba(#3b4252, 0.8);
  border: 1px solid #4c566a;
  color: #eceff4;
}
.ws-btn.focused {
  background-color: #88c0d0;
  color: #2e3440;
  border-radius: 4px;
  font-weight: bold;
}
```

---

## 🛠️ 6. Полезные консольные команды

- **`theme-create <картинка> [Название]`** — создать новую тему из файла.
- **`theme-select`** (или **`Mod + T`**) — открыть карточную галерею тем.
- **`theme-apply ~/.config/themes/<название>`** — применить тему вручную.
- **`dots theme <название>`** — переключить тему через утилиту `dots`.
- **`dots reload`** — мгновенно перезагрузить i3, EWW и тему без моргания.
- **`dots sync`** — синхронизировать созданные темы в репозиторий `~/dotfiles`.
- **`dots commit "сообщение"`** — зафиксировать изменения в Git.
- **`dots push`** — выгрузить обновленные темы на GitHub.
