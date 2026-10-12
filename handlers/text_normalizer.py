# text_normalizer.py — подготовка текста для Silero TTS:
# цифры, единицы, символы и латиницу превращаем в русские слова, иначе Silero их пропускает.
# Нужен: pip install num2words
import re

from num2words import num2words

# ───────────────────────── НАСТРОЙКИ (редактируй под себя) ─────────────────────────

# Единицы после числа. Формы: (1 — «один», 2-4 — «два», 5+ — «пять»).
# Регистр не важен. Для дробей («1,5 процента») берётся вторая форма.
UNITS = {
    "%": ("процент", "процента", "процентов"),
    "°C": ("градус Цельсия", "градуса Цельсия", "градусов Цельсия"),
    "°С": ("градус Цельсия", "градуса Цельсия", "градусов Цельсия"),  # с русской «С»
    "°": ("градус", "градуса", "градусов"),
    "ТБ": ("терабайт", "терабайта", "терабайт"),
    "TB": ("терабайт", "терабайта", "терабайт"),
    "ГБ": ("гигабайт", "гигабайта", "гигабайт"),
    "GB": ("гигабайт", "гигабайта", "гигабайт"),
    "МБ": ("мегабайт", "мегабайта", "мегабайт"),
    "MB": ("мегабайт", "мегабайта", "мегабайт"),
    "КБ": ("килобайт", "килобайта", "килобайт"),
    "KB": ("килобайт", "килобайта", "килобайт"),
    "ГГц": ("гигагерц", "гигагерца", "гигагерц"),
    "GHz": ("гигагерц", "гигагерца", "гигагерц"),
    "МГц": ("мегагерц", "мегагерца", "мегагерц"),
    "MHz": ("мегагерц", "мегагерца", "мегагерц"),
    "Гц": ("герц", "герца", "герц"),
    "Hz": ("герц", "герца", "герц"),
    "Вт": ("ватт", "ватта", "ватт"),
    "мс": ("миллисекунда", "миллисекунды", "миллисекунд"),
    "ms": ("миллисекунда", "миллисекунды", "миллисекунд"),
    "км/ч": ("километр в час", "километра в час", "километров в час"),
    "₽": ("рубль", "рубля", "рублей"),
    "руб": ("рубль", "рубля", "рублей"),
    "$": ("доллар", "доллара", "долларов"),
    "€": ("евро", "евро", "евро"),
}

# Латинские слова и аббревиатуры -> как их читать. Ключи в нижнем регистре.
WORDS = {
    "cpu": "си-пи-ю", "gpu": "джи-пи-ю", "ram": "рэм", "ssd": "эс-эс-ди", "hdd": "эйч-ди-ди",
    "usb": "юэс-би", "ip": "ай-пи", "dns": "ди-эн-эс", "vpn": "ви-пи-эн", "api": "эй-пи-ай",
    "ai": "эй-ай", "pc": "пи-си", "os": "о-эс", "ok": "окей",
    "linux": "линукс", "ubuntu": "убунту", "windows": "виндоус", "python": "пайтон",
    "github": "гитхаб", "telegram": "телеграм", "google": "гугл", "bluetooth": "блютус",
    "iphone": "айфон", "android": "андроид", "htop": "эйч-топ", "btop": "би-топ", "top": "топ",
    "wifi": "вай-фай", "binance": "бинанс", "okx": "о-кэ-икс", "chatgpt": "чат-джи-пи-ти", "whisper": "виспер", 
    "silero": "силеро", "piper": "пайпер", "lm studio": "эл-эм студио", "evie": "иви",
    "telegram bot": "телеграм бот", "lm": "эл-эм", "llm": "эл-эл-эм", "tts": "ти-ти-эс", 
    "asr": "эй-эс-ар", "vad": "ви-эй-ди", "api key": "апи кей", "api token": "апи токен",
    "openai": "опен-ай", "antivirus": "анти-вирус", "silero tts": "силеро ти-ти-эс",
}

# ───────────────────────── Числа ─────────────────────────

DENOMS = {
    1: ("десятая", "десятых"), 2: ("сотая", "сотых"), 3: ("тысячная", "тысячных"), 4: ("десятитысячная", "десятитысячных"), 5: ("стотысячная", "стотысячных"), 
    6: ("миллионная", "миллионных"), 7: ("десятимиллионная", "десятимиллионных"), 8: ("стомиллионная", "стомиллионных"), 9: ("миллиардная", "миллиардных"), 10: ("десятимиллиардная", "десятимиллиардных"), 
    }
FEM = {"один": "одна", "два": "две"}

UNITS_LC = {k.lower(): v for k, v in UNITS.items()}


def _int_words(n, feminine=False):
    words = num2words(int(n), lang="ru")
    if feminine:
        parts = words.split()
        parts[-1] = FEM.get(parts[-1], parts[-1])
        words = " ".join(parts)
    return words


def _plural(n, forms):
    n = abs(int(n)) % 100
    if 11 <= n <= 14:
        return forms[2]
    n %= 10
    if n == 1:
        return forms[0]
    if 2 <= n <= 4:
        return forms[1]
    return forms[2]


def _number_to_words(s, unit_forms=None):
    s = s.replace(",", ".")
    if "." in s:
        whole, frac = s.split(".", 1)
        if 1 <= len(frac) <= 3:
            w, f = int(whole), int(frac)
            whole_word = "целая" if w % 10 == 1 and w % 100 != 11 else "целых"
            denom = DENOMS[len(frac)]
            denom_word = denom[0] if f % 10 == 1 and f % 100 != 11 else denom[1]
            result = f"{_int_words(w, True)} {whole_word} {_int_words(f, True)} {denom_word}"
        else:  # длинная дробь — читаем цифры по одной
            result = f"{_int_words(whole)} запятая " + " ".join(_int_words(c) for c in frac)
        unit = unit_forms[1] if unit_forms else ""
    else:
        if len(s) > 15:  # номера, длинные коды — по цифрам
            result = " ".join(_int_words(c) for c in s)
        else:
            result = _int_words(s)
        unit = _plural(s, unit_forms) if unit_forms and len(s) <= 15 else (unit_forms[2] if unit_forms else "")
    return f"{result} {unit}".strip()


_UNIT_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*("
    + "|".join(re.escape(k) for k in sorted(UNITS_LC, key=len, reverse=True))
    + r")(?!\w)",
    re.IGNORECASE,
)
_TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})\b")
_NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _time_sub(m):
    hours, minutes = int(m.group(1)), m.group(2)
    if minutes == "00":
        tail = "ровно"
    elif minutes.startswith("0"):
        tail = "ноль " + _int_words(minutes)
    else:
        tail = _int_words(minutes)
    return f" {_int_words(hours)} {tail} "


# ───────────────────────── Латиница ─────────────────────────

LETTER_NAMES = {
    "a": "эй", "b": "би", "c": "си", "d": "ди", "e": "и", "f": "эф", "g": "джи", "h": "эйч",
    "i": "ай", "j": "джей", "k": "кей", "l": "эл", "m": "эм", "n": "эн", "o": "оу", "p": "пи",
    "q": "кью", "r": "ар", "s": "эс", "t": "ти", "u": "ю", "v": "ви", "w": "дабл-ю", "x": "экс",
    "y": "вай", "z": "зет",
}
_DIGRAPHS = [("sch", "ск"), ("sh", "ш"), ("ch", "ч"), ("zh", "ж"), ("th", "т"), ("ph", "ф"),
             ("ck", "к"), ("kh", "х"), ("ee", "и"), ("oo", "у"), ("ts", "ц"), ("qu", "кв"),
             ("ya", "я"), ("yu", "ю"), ("yo", "ё")]
_LETTERS = dict(zip(
    "abcdefghijklmnopqrstuvwxyz",
    ["а", "б", "к", "д", "е", "ф", "г", "х", "и", "дж", "к", "л", "м", "н", "о", "п", "к",
     "р", "с", "т", "у", "в", "в", "кс", "и", "з"],
))


def _translit(word):
    for lat, ru in _DIGRAPHS:
        word = word.replace(lat, ru)
    return "".join(_LETTERS.get(ch, ch) for ch in word)


def _latin_sub(m):
    token = m.group(0)
    low = token.lower()
    if low in WORDS:
        return WORDS[low]
    if token.isupper() and 2 <= len(token) <= 5:  # неизвестная аббревиатура — читаем по буквам
        return "-".join(LETTER_NAMES[c] for c in low)
    return _translit(low)  # запасной вариант: грубая транслитерация


# ───────────────────────── Главная функция ─────────────────────────

SYMBOLS = {"+": " плюс ", "=": " равно ", "&": " и ", "№": " номер ", "/": " ", "×": " умножить на "}


def normalize_for_tts(text: str) -> str:
    text = re.sub(r"(?i)\bwi-?fi\b", "вай-фай", text)
    text = _TIME_RE.sub(_time_sub, text)
    text = _UNIT_RE.sub(lambda m: f" {_number_to_words(m.group(1), UNITS_LC[m.group(2).lower()])} ", text)
    text = re.sub(r"(?<!\w)-(?=\d)", " минус ", text)
    text = _NUM_RE.sub(lambda m: f" {_number_to_words(m.group(0))} ", text)
    for sym, spoken in SYMBOLS.items():
        text = text.replace(sym, spoken)
    text = re.sub(r"[A-Za-z]+", _latin_sub, text)

    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)
    return text.strip()


if __name__ == "__main__":
    print(normalize_for_tts(
        "Загрузка CPU 1,1%, свободно 16 ГБ RAM, температура 45°C. "
        "Запустил htop в Linux, Wi-Fi 5 ГГц, сейчас 09:40, итого -3 и 2+2=4."
    ))