import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# LLM Config
MAX_TOOL_STEPS = 5              # максимальное количество шагов, которые агент может сделать при использовании инструментов
LM_MODEL = os.getenv("LM_MODEL", "local_model")        # или точное имя модели из LM Studio
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://127.0.0.1:1234/v1/chat/completions") # URL LM Studio Server, если используется локальная модель.
PIPER_PATH = "myenv/bin/piper"                              # путь к исполняемому файлу PIPER
MODEL_PATH = "data/ru_RU-irina-medium.onnx"                 # путь к модели PIPER
AUDIO_FILE = "data/input.wav"                               # файл для входного аудио
OUTPUT_FILE = "data/output.wav"                             # файл для выходного аудио
SYSTEM_PROMPT_FILE = "data/system_prompt.txt"               # файл с системным промптом для LM Studio

# Assistant Config
AI_NAME = os.getenv("AI_NAME", "Аннигиляторная пушка")             # имя ассистента
USE_WAKE_WORD = True         # True = ассистент реагирует только на фразу-активацию, False = ассистент реагирует на любую речь
WAKE_WORDS = ["иви", "эви", "иди", "иве", "ивек", "ивы", "ивик", "ивис", "эвил", "ивей", "ивя", "эвей", "эйвей", "иби", "эби", "эйби"]   # варианты, как Whisper может расслышать имя
CONVERSATION_TIMEOUT = 30    # сколько секунд ждать следующую фразу после окончания предыдущей, прежде чем закончить разговор

# Telegram Bot Config
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")  #TG Bot Token
TG_ALLOWED_IDS = {int(x) for x in os.getenv("TG_ALLOWED_IDS", "").split(",") if x.strip()}    #TG Allowed User IDs, разделённые запятой, например "123456789,987654321"
TG_PROXY = os.getenv("TG_PROXY", "")   # например "socks5://127.0.0.1:1080", если Telegram недоступен

# Whisper Studio Config
WHISPER_LANGUAGE = "ru"      # язык распознавания речи в Whisper. "auto" = автоопределение, "ru" = русский, "en" = английский и т.д.
WHISPER_MODEL = "small"      # модель Whisper для распознавания речи. Доступные: tiny, base, small, medium, large

# Silero TTS Config
SILERO_LANGUAGE = 'ru'      # язык синтеза речи в Silero
SILERO_MODEL_ID = 'v4_ru'   # Актуальная стабильная версия v4
SILERO_SPEAKER = 'baya'     # Доступные голоса: kseniya, baya, xenia, aidar, eugene
SILERO_SAMPLE_RATE = 48000  # частота дискретизации для Silero TTS

# Audio Config
INPUT_DEVICE = None          # None = системный микрофон; индекс см. через audio_handler.list_devices()
VAD_THRESHOLD = 0.5          # выше — меньше ложных срабатываний, но хуже ловит тихую речь
SILENCE_END_SEC = 0.8        # пауза, после которой фраза считается законченной
MIN_SPEECH_SEC = 0.3         # минимальная длина фразы, чтобы не обрабатывать случайные шумы
MAX_UTTERANCE_SEC = 90       #  максимальная длина фразы, после которой она обрывается
PRE_ROLL_SEC = 0.5           # сколько секунд до начала речи сохранять в буфер, чтобы не обрезать начало фразы
DURATION = 5                # длительность записи в секундах
SAMPLE_RATE = 16000         # частота дискретизации для PIPER

# TTS Config
BARGE_IN = False             # True только в наушниках
BARGE_IN_THRESHOLD = 0.7     # выше — меньше ложных срабатываний, но хуже ловит тихую речь

# Email Config
EMAIL_IMAP_HOST = os.getenv("EMAIL_IMAP_HOST", "")   # например
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")  # пароль приложения, не основной

# Weather Config
DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Москва")     # город по умолчанию для погоды, если не указан другой

# Notes Config
NOTES_FILE = "data/notes.txt"                               # файл для заметок