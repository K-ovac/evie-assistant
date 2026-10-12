# tts_handler.py
import logging
import os
import re

import numpy as np
import soundfile as sf
import torch

from data.config import OUTPUT_FILE, SILERO_SPEAKER, SILERO_SAMPLE_RATE, BARGE_IN
from handlers.audio_handler import play_audio

logger = logging.getLogger(__name__)

# Silero не переваривает длинные тексты (ошибка "probably it's too long"),
# поэтому режем ответ на куски и склеиваем звук.
MAX_CHARS = 350
PAUSE_SEC = 0.15

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

logger.info("Загрузка модели Silero TTS...")
model, _ = torch.hub.load(
    repo_or_dir='snakers4/silero-models',
    model='silero_tts',
    language='ru',
    speaker='v4_ru'
)
model.to(device)


def split_text(text, limit=MAX_CHARS):
    """Режет текст по предложениям на куски не длиннее limit символов."""
    parts = []
    for sentence in re.split(r"(?<=[.!?…])\s+", text.strip()):
        while len(sentence) > limit:  # очень длинное предложение — режем по запятой или пробелу
            cut = max(sentence.rfind(",", 0, limit), sentence.rfind(" ", 0, limit))
            cut = cut if cut > 0 else limit
            parts.append(sentence[:cut + 1].strip())
            sentence = sentence[cut + 1:].strip()
        if sentence:
            parts.append(sentence)

    chunks, current = [], ""
    for part in parts:
        if current and len(current) + len(part) + 1 > limit:
            chunks.append(current)
            current = part
        else:
            current = f"{current} {part}".strip()
    if current:
        chunks.append(current)
    return chunks


def speak(text):
    if not text or not text.strip():
        return

    output_dir = os.path.dirname(OUTPUT_FILE)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    pause = np.zeros(int(SILERO_SAMPLE_RATE * PAUSE_SEC), dtype=np.float32)
    audio_parts = []

    for chunk in split_text(text):
        try:
            tensor = model.apply_tts(
                text=chunk,
                speaker=SILERO_SPEAKER,
                sample_rate=SILERO_SAMPLE_RATE,
            )
            audio_parts += [tensor.cpu().numpy(), pause]
        except Exception as e:  # один плохой кусок не должен ломать весь ответ
            logger.error(f"Silero не смог озвучить кусок ({len(chunk)} симв.): {e!s:.120}")
            print(f"Ошибка Silero TTS на куске: {chunk[:60]}...")

    if not audio_parts:
        return

    try:
        sf.write(OUTPUT_FILE, np.concatenate(audio_parts), SILERO_SAMPLE_RATE)
        return play_audio(OUTPUT_FILE, interruptible=BARGE_IN)
    except Exception as e:
        logger.exception(f"Ошибка воспроизведения: {e}")
        print(f"Ошибка воспроизведения: {e}")