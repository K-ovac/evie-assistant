#!/usr/bin/env python3
# tray.py — значок в трее для управления Иви (голос и Telegram-бот).
# Сам ничего не распознаёт и не озвучивает: только запускает/останавливает systemd-сервисы
# evie-voice и evie-telegram, поэтому падение трея не затрагивает ассистента.
#
# Зависимости (системные, Debian/Ubuntu/Mint):
#   sudo apt install python3-pystray python3-pil python3-gi gir1.2-ayatanaappindicator3-0.1
# В GNOME нужно расширение «AppIndicator and KStatusNotifierItem Support» (в Ubuntu включено по умолчанию).
import subprocess
import sys
import threading
from pathlib import Path

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("Нужны pystray и Pillow: sudo apt install python3-pystray python3-pil python3-gi "
             "gir1.2-ayatanaappindicator3-0.1")

SERVICES = {  # ключ: (имя systemd-сервиса, название в меню)
    "voice": ("evie-voice", "Голос"),
    "telegram": ("evie-telegram", "Telegram-бот"),
}
LOG_FILE = Path(__file__).resolve().parent / "log" / "assistant.log"
POLL_SEC = 3

STATE = {unit: "inactive" for unit, _ in SERVICES.values()}
stop_event = threading.Event()

STATUS_RU = {
    "active": "работает", "inactive": "остановлен", "failed": "ошибка",
    "activating": "запускается", "deactivating": "останавливается",
}
GREEN, AMBER, RED, GREY = "#3fb950", "#d29922", "#f85149", "#8b949e"


def systemctl(*args):
    return subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True)


def read_states():
    return {unit: systemctl("is-active", unit).stdout.strip() or "inactive"
            for unit, _ in SERVICES.values()}


def make_icon(color):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, 60, 60), fill=color)
    d.rounded_rectangle((26, 14, 38, 36), radius=6, fill="white")  # микрофон
    d.arc((19, 24, 45, 46), 0, 180, fill="white", width=3)
    d.line((32, 46, 32, 53), fill="white", width=3)
    return img


def overall_color(states):
    values = list(states.values())
    if "failed" in values:
        return RED
    active = sum(v in ("active", "activating") for v in values)
    if active == len(values):
        return GREEN
    return AMBER if active else GREY


def run_action(verb, units):
    def handler(icon, item):
        for unit in units:
            systemctl(verb, unit)
        refresh(icon)
    return handler


def open_log(icon, item):
    subprocess.Popen(["xdg-open", str(LOG_FILE)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def quit_tray(icon, item):
    stop_event.set()
    icon.stop()  # сервисы продолжают работать


def build_menu():
    items = []
    for unit, title in SERVICES.values():
        items += [
            pystray.MenuItem(lambda item, u=unit, t=title: f"{t}: {STATUS_RU.get(STATE[u], STATE[u])}",
                             None, enabled=False),
            pystray.MenuItem("   Запустить", run_action("start", [unit])),
            pystray.MenuItem("   Перезапустить", run_action("restart", [unit])),
            pystray.MenuItem("   Остановить", run_action("stop", [unit])),
            pystray.Menu.SEPARATOR,
        ]
    all_units = [unit for unit, _ in SERVICES.values()]
    items += [
        pystray.MenuItem("Перезапустить всё", run_action("restart", all_units)),
        pystray.MenuItem("Остановить всё", run_action("stop", all_units)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Открыть лог", open_log),
        pystray.MenuItem("Выйти из трея", quit_tray),
    ]
    return pystray.Menu(*items)


def refresh(icon):
    new = read_states()
    if new != STATE:
        STATE.update(new)
        icon.icon = make_icon(overall_color(STATE))
        icon.title = "Иви: " + ", ".join(f"{t} — {STATUS_RU.get(STATE[u], STATE[u])}"
                                          for u, t in SERVICES.values())
    icon.update_menu()


def poll(icon):
    icon.visible = True
    STATE.update(read_states())
    icon.icon = make_icon(overall_color(STATE))
    while not stop_event.wait(POLL_SEC):
        refresh(icon)


def main():
    STATE.update(read_states())
    icon = pystray.Icon("evie", make_icon(overall_color(STATE)), "Иви", build_menu())
    icon.run(setup=lambda ic: threading.Thread(target=poll, args=(ic,), daemon=True).start())


if __name__ == "__main__":
    main()