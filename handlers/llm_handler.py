# llm_handler.py — общение с LM Studio + цикл вызова инструментов
import json
import logging
import re

import requests

from handlers import agent_tools as tools
from data.config import (
    LM_STUDIO_URL, 
    LM_MODEL, 
    SYSTEM_PROMPT_FILE, 
    AI_NAME, 
    MAX_TOOL_STEPS
)
from handlers.text_normalizer import normalize_for_tts

logger = logging.getLogger(__name__)


def _load_system_prompt():
    try:
        with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.warning(f"Файл {SYSTEM_PROMPT_FILE} не найден. Использую дефолтный промпт.")
        return f"Ты — полезный голосовой ассистент {AI_NAME}. Отвечай ТОЛЬКО на русском языке."


def console_confirm(description: str) -> bool:
    """Подтверждение опасных действий в голосовом режиме (через консоль)."""
    answer = input(f"\n⚠️  Разрешить действие?\n{description}\n[y/N]: ")
    return answer.strip().lower() in ("y", "yes", "д", "да")


def _trim_history(history, keep=30):
    """Обрезаем историю, но так, чтобы она всегда начиналась с сообщения пользователя."""
    if len(history) > keep:
        del history[:-keep]
    while history and history[0].get("role") != "user":
        history.pop(0)


def _strip_thinking(text: str) -> str:
    # Некоторые модели (Qwen3, DeepSeek) выводят <think>...</think>
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()


def get_ai_response(prompt, history=None, confirm=None):
    """
    prompt  — текст пользователя
    history — список сообщений диалога (изменяется на месте, хранится снаружи)
    confirm — функция confirm(description) -> bool для опасных инструментов
    """
    print("Думаю...")
    logger.info("Думаю...")

    confirm = confirm or console_confirm
    history = history if history is not None else []
    history.append({"role": "user", "content": prompt})
    system = {"role": "system", "content": _load_system_prompt()}

    for _ in range(MAX_TOOL_STEPS):
        payload = {
            "model": LM_MODEL,
            "messages": [system] + history,
            "tools": tools.get_schemas(),
            "temperature": 0.7,
            # "chat_template_kwargs": {
            #     "enable_thinking": False,  # включаем <think>...</think> для моделей, которые поддерживают
            # }
        }
        try:
            response = requests.post(LM_STUDIO_URL, json=payload, timeout=180)
            response.raise_for_status()
            message = response.json()["choices"][0]["message"]
        except Exception as e:
            logger.exception(f"Ошибка сервера: {e}")
            print(f"Ошибка сервера: {e}")
            history.pop()  # откатываем последнее сообщение пользователя
            return "Извините, не могу ответить."

        history.append(message)
        calls = message.get("tool_calls")

        if not calls:  # модель дала финальный ответ
            answer = _strip_thinking(message.get("content"))
            _trim_history(history)
            return answer or "Готово."

        for call in calls:
            name = call["function"]["name"]
            try:
                args = json.loads(call["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            logger.info(f"Вызов инструмента: {name}({args})")
            print(f"🔧 {name}({args})")

            result = tools.execute(name, args, confirm)
            logger.info(f"Результат {name}: {result[:200]}")
            history.append({
                "role": "tool",
                "tool_call_id": call.get("id", name),
                "content": result,
            })

    _trim_history(history)
    return "Не получилось завершить задачу: слишком много шагов."


def clean_text_for_tts(text: str) -> str:
    text = re.sub(r'[*#_~`>]', '', text)
    text = re.sub(r'http\S+', '', text)
    return normalize_for_tts(text).strip()