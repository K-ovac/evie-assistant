#!/usr/bin/env bash
# setup_llm.sh — собирает llama.cpp (Vulkan), скачивает модели и ставит user-сервисы systemd для Иви:
#   evie-llm   (чат, Gemma 4 E4B, порт 8081)
#   evie-embed (эмбеддинги, EmbeddingGemma 2, порт 8082)
#
# Запуск:                  bash setup_llm.sh      (попросит sudo для apt)
# Проверка без установки:  DRY_RUN=1 bash setup_llm.sh
# Переменные: CHAT_QUANT (по умолчанию Q4_K_M; можно Q5_K_M, Q6_K, Q8_0), CTX (контекст, 8192),
#             LLAMA_DIR (~/llama.cpp), MODELS_DIR (~/models).
set -euo pipefail

LLAMA_DIR="${LLAMA_DIR:-$HOME/llama.cpp}"
MODELS_DIR="${MODELS_DIR:-$HOME/models}"
CHAT_QUANT="${CHAT_QUANT:-Q4_K_M}"
CTX="${CTX:-8192}"
DRY_RUN="${DRY_RUN:-0}"

CHAT_FILE="google_gemma-4-E4B-it-${CHAT_QUANT}.gguf"
CHAT_URL="https://huggingface.co/bartowski/google_gemma-4-E4B-it-GGUF/resolve/main/${CHAT_FILE}"
EMBED_FILE="embeddinggemma-2-UD-Q4_K_XL.gguf"
EMBED_URL="https://huggingface.co/unsloth/embeddinggemma-2-GGUF/resolve/main/${EMBED_FILE}"
CHAT_PORT=8081
EMBED_PORT=8082
SERVER="$LLAMA_DIR/build/bin/llama-server"
UNIT_DIR="$HOME/.config/systemd/user"

run() { if [ "$DRY_RUN" = 1 ]; then echo "[dry-run] $*"; else "$@"; fi; }

# ── 1. Пакеты для сборки ──
echo "==> Установка пакетов (нужен sudo)"
run sudo apt install -y build-essential cmake git curl libvulkan-dev glslc spirv-headers \
    mesa-vulkan-drivers vulkan-tools libcurl4-openssl-dev libssl-dev

if [ "$DRY_RUN" != 1 ] && command -v vulkaninfo >/dev/null; then
  echo "==> Vulkan видит устройства:"
  vulkaninfo --summary 2>/dev/null | grep -i "deviceName" || echo "   (не нашёл deviceName: проверь драйвер Mesa)"
fi

# ── 2. llama.cpp: свежие исходники (нужны для Gemma 4 и EmbeddingGemma 2) ──
echo "==> llama.cpp"
if [ -d "$LLAMA_DIR/.git" ]; then
  run git -C "$LLAMA_DIR" pull --ff-only
else
  run git clone --depth 1 https://github.com/ggml-org/llama.cpp.git "$LLAMA_DIR"
fi
run cmake -S "$LLAMA_DIR" -B "$LLAMA_DIR/build" -DGGML_VULKAN=ON -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release
run cmake --build "$LLAMA_DIR/build" --config Release -j "$(nproc)" --target llama-server llama-bench

if [ "$DRY_RUN" != 1 ]; then
  for flag in --jinja --pooling --parallel --embeddings --alias; do
    "$SERVER" --help 2>&1 | grep -q -- "$flag" || echo "ВНИМАНИЕ: в этой сборке llama-server нет флага $flag (сверься с --help)"
  done
fi

# ── 3. Модели (докачка поддерживается; для прокси задай https_proxy) ──
echo "==> Модели в $MODELS_DIR"
mkdir -p "$MODELS_DIR"
download() {  # $1 url, $2 файл
  if [ -f "$MODELS_DIR/$2" ]; then echo "   уже есть: $2"; return; fi
  run curl -L --fail -C - -o "$MODELS_DIR/$2.part" "$1"
  run mv "$MODELS_DIR/$2.part" "$MODELS_DIR/$2"
}
download "$CHAT_URL" "$CHAT_FILE"
download "$EMBED_URL" "$EMBED_FILE"

# ── 4. Сервисы systemd (user) ──
echo "==> Сервисы systemd"
mkdir -p "$UNIT_DIR"

write_unit() {  # $1 имя, $2 описание, $3 аргументы llama-server
  cat > "$UNIT_DIR/$1.service" <<EOF
[Unit]
Description=$2

[Service]
Type=simple
ExecStart=$SERVER $3
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
}

write_unit evie-llm "Иви - LLM (llama.cpp, Gemma 4 E4B)" \
  "-m $MODELS_DIR/$CHAT_FILE --alias gemma4-e4b --host 127.0.0.1 --port $CHAT_PORT -ngl 99 -c $CTX -np 1 --jinja"

write_unit evie-embed "Иви - эмбеддинги (llama.cpp, EmbeddingGemma 2)" \
  "-m $MODELS_DIR/$EMBED_FILE --alias embeddinggemma2 --host 127.0.0.1 --port $EMBED_PORT --embeddings --pooling mean -c 2048 -b 2048 -ub 2048 -np 1 -ngl 0"

# Ассистент должен стартовать после чат-сервера и дождаться, пока модель загрузится
for svc in evie-voice evie-telegram; do
  if [ -f "$UNIT_DIR/$svc.service" ]; then
    mkdir -p "$UNIT_DIR/$svc.service.d"
    cat > "$UNIT_DIR/$svc.service.d/10-llm.conf" <<EOF
[Unit]
Wants=evie-llm.service evie-embed.service
After=evie-llm.service evie-embed.service

[Service]
TimeoutStartSec=150
ExecStartPre=/usr/bin/curl -sf --retry 120 --retry-delay 1 --retry-connrefused --retry-all-errors -o /dev/null http://127.0.0.1:$CHAT_PORT/health
EOF
    echo "   зависимость от evie-llm добавлена для $svc"
  fi
done

run systemctl --user daemon-reload

cat <<EOF

Готово. Что дальше:
  1) Запусти чат вручную и проверь:   systemctl --user start evie-llm evie-embed
     python3 check_llm.py             (чат, вызов инструмента, эмбеддинги)
     журнал:                          journalctl --user -u evie-llm -f
  2) В data/config.py:
       LM_STUDIO_URL = "http://127.0.0.1:$CHAT_PORT/v1/chat/completions"
       LM_MODEL = "gemma4-e4b"
  3) Автозапуск при входе:            systemctl --user enable evie-llm evie-embed
  4) Закрой LM Studio, чтобы он не занимал видеопамять.
EOF
