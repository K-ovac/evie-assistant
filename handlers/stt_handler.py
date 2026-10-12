# stt_handler.py
import logging

import whisper

from data.config import (
    WHISPER_MODEL, 
    WHISPER_LANGUAGE
)

logger = logging.getLogger(__name__)

print("Загрузка модели Whisper...")
logger.info("Загрузка модели Whisper...")
model = whisper.load_model(WHISPER_MODEL)

# Whisper любит «галлюцинировать» эти фразы на шуме и тишине
HALLUCINATIONS = (
    "продолжение следует", "субтитры", "спасибо за просмотр",
    "редактор субтитров", "корректор", "подписывайтесь на канал",
)


def transcribe_audio(audio):
    """audio — путь к файлу ИЛИ numpy float32 массив 16 кГц."""
    logger.info("Распознавание речи...")
    result = model.transcribe(
        audio,
        language=WHISPER_LANGUAGE,
        fp16=False,
        condition_on_previous_text=False,
    )

    segments = result.get("segments", [])
    if segments and all(s["no_speech_prob"] > 0.6 and s["avg_logprob"] < -1.0 for s in segments):
        return ""

    text = result["text"].strip()
    if any(h in text.lower() for h in HALLUCINATIONS):
        return ""
    return text