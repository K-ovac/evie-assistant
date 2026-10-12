#!/usr/bin/env bash
# install_services.sh — ставит Иви как user-сервисы systemd + автозапуск значка в трее.
#
# Запуск (из любой папки):
#   bash install_services.sh /путь/к/Evie_Project/scripts [/путь/к/python] [/путь/к/python-для-трея]
# По умолчанию: python = <scripts>/myenv/bin/python, трей = /usr/bin/python3 (там python3-pystray из apt).
set -euo pipefail

PROJECT_DIR="$(realpath "${1:-$(pwd)}")"
PYTHON="${2:-$PROJECT_DIR/myenv/bin/python}"
TRAY_PYTHON="${3:-/usr/bin/python3}"

UNIT_DIR="$HOME/.config/systemd/user"
ENV_DIR="$HOME/.config/evie"
ENV_FILE="$ENV_DIR/env"
AUTOSTART_DIR="$HOME/.config/autostart"

[ -f "$PROJECT_DIR/main.py" ] || { echo "Не найден $PROJECT_DIR/main.py"; exit 1; }
[ -f "$PROJECT_DIR/telegram_bot.py" ] || { echo "Не найден $PROJECT_DIR/telegram_bot.py"; exit 1; }
[ -x "$PYTHON" ] || { echo "Не найден python: $PYTHON"; exit 1; }

mkdir -p "$UNIT_DIR" "$ENV_DIR" "$AUTOSTART_DIR"

# --- файл с секретами (вместо export в терминале) ---
if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" <<'EOF'
# Секреты для сервисов. Формат KEY=value, без кавычек и без export.
TG_BOT_TOKEN=
TG_ALLOWED_IDS=
TG_PROXY=
EMAIL_USER=
EMAIL_PASSWORD=
EOF
  chmod 600 "$ENV_FILE"
  echo "Создан $ENV_FILE — впиши туда токен бота и остальное."
fi

# --- unit-файлы ---
write_unit() {  # $1 имя, $2 описание, $3 скрипт
  cat > "$UNIT_DIR/$1.service" <<EOF
[Unit]
Description=$2
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$ENV_FILE
Environment=PYTHONUNBUFFERED=1
ExecStart=$PYTHON $PROJECT_DIR/$3
Restart=on-failure
RestartSec=5
TimeoutStopSec=10

[Install]
WantedBy=graphical-session.target
EOF
}
write_unit evie-voice "Иви - голосовой ассистент" main.py
write_unit evie-telegram "Иви - Telegram-бот" telegram_bot.py

# --- автозапуск трея ---
if [ -f "$PROJECT_DIR/tray.py" ]; then
  cat > "$AUTOSTART_DIR/evie-tray.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Иви (трей)
Exec=$TRAY_PYTHON $PROJECT_DIR/tray.py
Icon=audio-input-microphone
X-GNOME-Autostart-enabled=true
EOF
else
  echo "tray.py не найден рядом с main.py — автозапуск трея пропущен."
fi

systemctl --user daemon-reload || echo "Предупреждение: systemctl --user недоступен (нет сессии?)."

# --- автозапуск сервисов при входе в систему ---
systemctl --user enable evie-voice || true
if grep -qE '^TG_BOT_TOKEN=.+' "$ENV_FILE"; then
  systemctl --user enable evie-telegram || true
else
  echo "TG_BOT_TOKEN пуст — автозапуск Telegram-бота не включён. После заполнения: systemctl --user enable --now evie-telegram"
fi

cat <<EOF

Готово. Полезные команды:
  systemctl --user start|stop|restart evie-voice
  systemctl --user start|stop|restart evie-telegram
  systemctl --user status evie-voice
  journalctl --user -u evie-voice -f        # лог в реальном времени
Сервисам нужны DISPLAY/WAYLAND_DISPLAY (для окон). Проверка:
  systemctl --user show-environment | grep -E 'DISPLAY|WAYLAND'
Если пусто, добавь в автозапуск сессии:
  systemctl --user import-environment DISPLAY WAYLAND_DISPLAY XAUTHORITY
EOF