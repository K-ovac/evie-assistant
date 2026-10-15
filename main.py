# main.py — голосовой диалог без нажатия кнопок
import re
import time

from log.logger_setup import setup_logger
logger = setup_logger()
from handlers.farewell import is_farewell
from handlers.audio_handler import get_listener
from handlers.stt_handler import transcribe_audio
from handlers.llm_handler import get_ai_response, clean_text_for_tts
from handlers.tts_handler import speak
from data.config import (
    AI_NAME, 
    USE_WAKE_WORD, 
    WAKE_WORDS, 
    CONVERSATION_TIMEOUT
)

YES_RE = re.compile(r"\b(да|давай|выполняй|подтверждаю|разрешаю|окей|ок|хорошо|угу|ага)\b")
NO_RE = re.compile(r"\b(нет|не надо|отмена|стоп)\b")


def strip_wake_word(text):
    """Возвращает (услышала_имя, остаток_фразы)."""
    low = text.lower()
    for word in WAKE_WORDS:
        m = re.search(rf"\b{word}\b[\s,.!?:-]*", low)
        if m:
            return True, text[m.end():].strip()
    return False, text


def voice_confirm(description, spoken=None):
    """Подтверждение опасных действий голосом."""
    listener = get_listener()
    print(f"\n⚠️  Требуется подтверждение: {description}")
    speak(f"{spoken} Скажи да или нет." if spoken else "Нужно подтверждение. Выполнить? Скажи да или нет.")
    audio = listener.listen(wait_timeout=10)
    if audio is None:
        return False
    answer = transcribe_audio(audio).lower()
    print(f"Ответ: {answer}")
    return bool(YES_RE.search(answer)) and not NO_RE.search(answer)


def main():
    listener = get_listener()
    history = []
    interrupted = False        # пользователь перебил Иви — его фраза уже частично записана
    conversation_until = 0.0   # до этого момента имя говорить не нужно

    print(f"{AI_NAME} готова к работе.")
    logger.info(f"{AI_NAME} готова к работе.")
    speak(f"{AI_NAME} готова к работе.")

    while True:
        in_conversation = (not USE_WAKE_WORD) or time.time() < conversation_until
        wait = None
        if USE_WAKE_WORD and in_conversation:
            wait = max(0.0, conversation_until - time.time())

        print("🎙  Слушаю..." if in_conversation else f"💤 Жду обращения «{AI_NAME}»...")
        audio = listener.listen(wait_timeout=wait, use_recent=interrupted)
        interrupted = False
        if audio is None:  # в режиме диалога никто не заговорил — возвращаемся к ожиданию имени
            continue

        user_text = transcribe_audio(audio)
        if not user_text:
            continue
        print(f"Ты сказал: {user_text}")
        logger.info(f"Ты сказал: {user_text}")

        if USE_WAKE_WORD and not in_conversation:
            woke, user_text = strip_wake_word(user_text)
            if not woke:
                continue  # это не нам
            if not user_text:  # просто позвали по имени
                speak("Слушаю.")
                conversation_until = time.time() + CONVERSATION_TIMEOUT
                continue

        if is_farewell(user_text):
            print("До свидания!")
            speak("До свидания!")
            break

        ai_text = get_ai_response(user_text, history, confirm=voice_confirm)
        ai_text = clean_text_for_tts(ai_text)
        logger.info(f"Ответ {AI_NAME}: {ai_text}")
        print(f"Ответ {AI_NAME}: {ai_text}")

        interrupted = bool(speak(ai_text))
        conversation_until = time.time() + CONVERSATION_TIMEOUT


if __name__ == "__main__":
    import signal, sys
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    main()