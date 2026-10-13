# text_normalizer.py — подготовка текста для Silero TTS:
# цифры, даты, годы, единицы, символы и латиницу превращаем в русские слова (с падежами).
# Нужны: pip install num2words, и файл ru_numbers.py рядом.
import re

try:  # запуск из проекта (python3 main.py)
    from handlers.ru_numbers import (
        MONTHS, YEAR_NOUN, cardinal, ordinal, date_words,
        detect_case, case_after_prep, guess_gender, PREP_PREP, GEN_PREP,
    )
except ImportError:  # прямой запуск файла (python3 handlers/text_normalizer.py)
    from ru_numbers import (
        MONTHS, YEAR_NOUN, cardinal, ordinal, date_words,
        detect_case, case_after_prep, guess_gender, PREP_PREP, GEN_PREP,
    )

# ───────────────────────── НАСТРОЙКИ (редактируй под себя) ─────────────────────────

# Единицы после числа. Формы: (1 — «один», 2-4 — «два», 5+ — «пять»[, род: "f" или "n"]).
# Первая форма — именительный, вторая — родительный ед. числа, третья — родительный мн. числа.
# Регистр ключа не важен. Падежи (до 5 ГБ, к 5 ГБ, с 5 ГБ) строятся автоматически.
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
    "мс": ("миллисекунда", "миллисекунды", "миллисекунд", "f"),
    "ms": ("миллисекунда", "миллисекунды", "миллисекунд", "f"),
    "мин": ("минута", "минуты", "минут", "f"),
    "сек": ("секунда", "секунды", "секунд", "f"),
    "км/ч": ("километр в час", "километра в час", "километров в час"),
    "м/с": ("метр в секунду", "метра в секунду", "метров в секунду"),
    "₽": ("рубль", "рубля", "рублей"),
    "руб": ("рубль", "рубля", "рублей"),
    "$": ("доллар", "доллара", "долларов"),
    "€": ("евро", "евро", "евро"),
    "btc": ("биткоин", "биткоина", "биткоинов"),
}

# Латинские слова и аббревиатуры -> как их читать. Ключи в нижнем регистре.
WORDS = {
    "cpu": "си-пи-юю", "gpu": "джи-пи-ю", "ram": "рэм", "ssd": "эс-эс-ди", "hdd": "эйч-ди-ди",
    "usb": "юэс-би", "ip": "ай-пи", "dns": "ди-эн-эс", "vpn": "ви-пи-эн", "api": "эй-пи-ай",
    "ai": "эй-ай", "pc": "пи-си", "os": "о-эс", "ok": "окей", "chatgpt": "чат-джи-пи-ти", "gpt": "джи-пи-ти",
    "linux": "линукс", "ubuntu": "убунту", "windows": "виндоус", "python": "пайтон",
    "github": "гитхаб", "telegram": "телеграм", "google": "гугл", "bluetooth": "блютус",
    "iphone": "айфон", "android": "андроид", "htop": "эйч-топ", "btop": "би-топ", "top": "топ",
    "wifi": "вай-фай", "hacker": "хакер", "developer": "разработчик", "programmer": "программист", 
    "manager": "менеджер", "designer": "дизайнер", "dev": "дев", "frontend": "фронтенд", 
    "backend": "бэкенд", "fullstack": "фулстек", "nvme": "эн-вэ-эм-е", "docker": "докер", 
    "kubernetes": "кубернетис", "ai": "эй-ай", "efi": "и-эф-ай", "bios": "би-о-эс", "uefi": "ю-и-эф-ай", 
    "lshw": "эл-эч-вэ-блю", "lsusb": "эл-эс-ю-эс-би", "lspci": "эл-эс-пи-си-ай", "bios/uefi": "би-о-эс-ю-и-эф-ай",
    "ssh": "эс-эс-эйч", "telnet": "телнет", "ftp": "эф-ти-пи", "http": "эйч-ти-ти-пи", "https": "эйч-ти-ти-пи-эс",
    "py": "пай", "js": "джей-эс", "ts": "ти-эс", "html": "эйч-ти-эм-эл", "css": "си-эс-эс", 
    "certificate": "сертификат", "ssl": "эс-эс-эл", "tls": "ти-эл-эс", "json": "джей-сон", "letsencrypt": "летс-энкрипт",
    "openssl": "опен-эс-эс-эль", "nginx": "эн-джи-эн-икс", "apache": "апачи", "postgresql": "постгрес-кью-эль", 
    "sudo": "су-до", "sudoers": "су-до-эрс", "bash": "бэш", "zsh": "зэш", "fish": "фиш", 
    "amd": "а-эм-дэ", "ryzen": "райзен", "intel": "интел", "arm": "арм", "nvidia": "эн-ви-ди-а", 
    "amd64": "а-эм-дэ-шестьдесятчетыре", "x86": "икс-восемьдесятшесть", "x86_64": "икс-восемьдесятшесть-шестьдесятчетыре", 
    "rx": "эр-икс", "rtx": "эр-ти-икс", "gtx": "джи-ти-икс", "gpt": "джи-пи-ти", "x": "икс", "y": "вай", "z": "зет", 
    "update": "апдейт", "upgrade": "апгрейд", "download": "даунлоад", "upload": "аплоад",
    "libx": "либ-икс", "libc": "либ-си", "libssl": "либ-эс-эс-эль", "libcrypto": "либ-крипто", "libcurl": "либ-кёрл", 
    "trust": "траст", "key": "кей", "cert": "серт", "config": "конфиг", "desktop": "дэсктоп", "laptop": "лаптоп", 
    "notebook": "ноутбук", "server": "сервер", "client": "клиент", "run": "ран", "table": "тейбл",
    "firefox": "фаерфокс", "chrome": "хром", "edge": "эдж", "safari": "сафари", "opera": "опера", 
    "gigabytes": "гигабайт", "megabytes": "мегабайт", "kilobytes": "килобайт", "bytes": "байт",
}

SYMBOLS = {
    "+": " плюс ", 
    "=": " равно ", 
    "&": " и ", 
    "№": " номер ", 
    "/": "разделить", 
    "×": " умножить на "
    }

# ───────────────────────── Контекст вокруг числа ─────────────────────────

_PREV_RE = re.compile(r"([А-Яа-яЁё-]+)\s*$")
_NEXT_RE = re.compile(r"\s*([А-Яа-яЁё]+)")


def _prev_word(text, pos):
    head = text[:pos]
    m = _PREV_RE.search(head)
    if m and m.group(1).lower() == "минус":  # «от минус 5» -> смотрим на «от»
        m = _PREV_RE.search(head[:m.start()])
    return m.group(1).lower() if m else ""


def _next_word(text, pos):
    m = _NEXT_RE.match(text[pos:])
    return m.group(1).lower() if m else ""


def _is_one(n):
    return n % 10 == 1 and n % 100 != 11


# ───────────────────────── Числа ─────────────────────────

DENOMS = {1: ("десятая", "десятых", "десятой"), 2: ("сотая", "сотых", "сотой"),
          3: ("тысячная", "тысячных", "тысячной")}


def _decimal_words(whole, frac, case="nom"):
    """1,5 -> «одна целая пять десятых»; в родительном — «одной целой пяти десятых»."""
    w, f = int(whole), int(frac)
    if case != "gen":
        case = "nom"
    den = DENOMS[len(frac)]
    if case == "nom":
        whole_word = "целая" if _is_one(w) else "целых"
        den_word = den[0] if _is_one(f) else den[1]
    else:
        whole_word = "целой" if _is_one(w) else "целых"
        den_word = den[2] if _is_one(f) else den[1]
    return f"{cardinal(w, case, 'f')} {whole_word} {cardinal(f, case, 'f')} {den_word}"


def _number_words(s, case="nom", gender="m"):
    """Число-строка -> слова в нужном падеже. Длинные дроби и коды читаем по цифрам."""
    s = s.replace(",", ".")
    if "." in s:
        whole, frac = s.split(".", 1)
        if 1 <= len(frac) <= 3:
            return _decimal_words(whole, frac, case)
        return f"{cardinal(whole)} запятая " + " ".join(cardinal(c) for c in frac)
    if len(s) > 15:
        return " ".join(cardinal(c) for c in s)
    return cardinal(int(s), case, gender)


# ───────────────────────── Единицы ─────────────────────────

UNITS_LC = {k.lower(): v for k, v in UNITS.items()}


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


def _oblique_noun(forms, case):
    """Множественное число существительного-единицы в дательном/творительном/предложном падеже."""
    first, _, rest = forms[1].partition(" ")  # «градуса Цельсия»: склоняем только первое слово
    last = first[-1]
    if last in "аы" or (last == "и" and first[-2] in "гкхжшчщц"):
        endings = {"dat": "ам", "ins": "ами", "prep": "ах"}
    elif last in "яи":
        endings = {"dat": "ям", "ins": "ями", "prep": "ях"}
    else:
        return forms[1]  # несклоняемое («евро»)
    return (first[:-1] + endings[case] + (" " + rest if rest else "")).strip()


def _number_with_unit(s, forms, case):
    s = s.replace(",", ".")
    gender = forms[3] if len(forms) > 3 else "m"
    if "." in s:  # дроби: единица в родительном падеже ед. числа
        return f"{_number_words(s, case)} {forms[1]}"
    n = int(s) if len(s) <= 15 else None
    if n is None:
        return f"{_number_words(s)} {forms[2]}"
    if case in ("nom", "acc"):
        return f"{cardinal(n, 'nom', gender)} {_plural(n, forms[:3])}"
    words = cardinal(n, case, gender)
    if case == "gen":
        noun = forms[1] if _is_one(n) else forms[2]
    else:
        noun = _oblique_noun(forms, case)
    return f"{words} {noun}"


_UNIT_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*("
    + "|".join(re.escape(k) for k in sorted(UNITS_LC, key=len, reverse=True))
    + r")(?!\w)",
    re.IGNORECASE,
)


def _unit_sub(m):
    case = detect_case(_prev_word(m.string, m.start()), None)
    forms = UNITS_LC[m.group(2).lower()]
    return f" {_number_with_unit(m.group(1), forms, case)} "


# ───────────────────────── Годы, даты, порядковые ─────────────────────────

_YEAR_NOUNS = ("год", "года", "году", "годом", "годе")
_YEAR_RE = re.compile(r"(?<![\d.,])(\d{4})(?!\d)\s*(год[а-яё]*|г\.)(?![а-яёa-z])", re.IGNORECASE)


def _year_sub(m):
    year, noun = int(m.group(1)), m.group(2).lower()
    if not 1000 <= year <= 2999 or (noun != "г." and noun not in _YEAR_NOUNS):
        return m.group(0)
    prev = _prev_word(m.string, m.start())
    tail = ""
    if noun == "г.":  # «в 2026 г.» — падеж по предлогу
        case = case_after_prep(prev)
        noun = YEAR_NOUN[case]
        after = m.string[m.end():].lstrip()
        if not after or after[0].isupper():  # точка в «г.» была концом предложения
            tail = "."
    else:
        case = {"год": "nom", "года": "gen", "году": "prep", "годом": "ins", "годе": "prep"}[noun]
        if noun == "году" and detect_case(prev, None) == "dat":
            case = "dat"
    return f" {ordinal(year, case)} {noun}{tail} "


_MONTHS_RE = "|".join(MONTHS)
_DATE_TEXT_RE = re.compile(rf"(?<![\d.,])(\d{{1,2}})\s+({_MONTHS_RE})(?![а-яё])", re.IGNORECASE)
_DATE_NUM_RE = re.compile(r"(?<![\d.])(\d{1,2})\.(\d{1,2})\.(\d{4})(?!\d|\.\d)")


def _date_text_sub(m):
    day = int(m.group(1))
    if not 1 <= day <= 31:
        return m.group(0)
    case = detect_case(_prev_word(m.string, m.start()), None)
    month = MONTHS.index(m.group(2).lower()) + 1
    return f" {date_words(day, month, case)} "


def _date_num_sub(m):
    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1 <= day <= 31 and 1 <= month <= 12):
        return m.group(0)
    case = detect_case(_prev_word(m.string, m.start()), None)
    return f" {date_words(day, month, case)} {ordinal(year, 'gen')} года "


# «3-й этаж», «на 5-м этаже», «к 3-му числу», «в 90-х»
_SUFFIX_RE = re.compile(r"(?<![\d.,])(\d+)-(ый|ой|ая|ое|ую|ым|ом|ых|й|я|е|го|му|м|ю|х)(?![а-яёa-z])", re.IGNORECASE)


def _suffix_sub(m):
    n, suf = int(m.group(1)), m.group(2).lower()
    prev = _prev_word(m.string, m.start())
    plural = False
    if suf in ("й", "ый", "ой"):
        case, gender = "nom", "m"
        if suf == "ой":
            case, gender = (case_after_prep(prev), "f") if prev in PREP_PREP | GEN_PREP else ("nom", "m")
    elif suf in ("я", "ая"):
        case, gender = "nom", "f"
    elif suf in ("е", "ое"):
        case, gender = "nom", "n"
    elif suf == "го":
        case, gender = "gen", "m"
    elif suf == "му":
        case, gender = "dat", "m"
    elif suf in ("ю", "ую"):
        case, gender = "acc", "f"
    elif suf == "ом":
        case, gender = "prep", "m"
    elif suf == "ым":
        case, gender = "ins", "m"
    elif suf == "м":
        case, gender = ("prep" if prev in PREP_PREP else "ins"), "m"
    else:  # «х», «ых» — множественное число: «в 90-х»
        case, gender, plural = "gen", "m", True
    return f" {ordinal(n, case, gender, plural)} "


# ───────────────────────── Время и обычные числа ─────────────────────────

_TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})\b")
_NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _time_sub(m):
    hours, minutes = int(m.group(1)), m.group(2)
    if minutes == "00":
        tail = "ровно"
    elif minutes.startswith("0"):
        tail = "ноль " + cardinal(int(minutes))
    else:
        tail = cardinal(int(minutes))
    return f" {cardinal(hours)} {tail} "


def _num_sub(m):
    """Обычное число: падеж и род берём из соседних слов («до 5 минут», «21 минуту», «к 5 часам»)."""
    s = m.group(0)
    prev = _prev_word(m.string, m.start())
    nxt = _next_word(m.string, m.end())
    case = detect_case(prev, nxt)
    gender = "m"
    if re.fullmatch(r"\d{1,15}", s):
        n = int(s)
        gender = guess_gender(nxt, case, n)
        if case == "nom" and _is_one(n) and nxt.endswith(("у", "ю")) and len(nxt) > 3:
            case, gender = "acc", "f"  # «через 1 минуту» -> «одну минуту»
    return f" {_number_words(s, case, gender)} "


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

def normalize_for_tts(text: str) -> str:
    text = re.sub(r"(?i)\bwi-?fi\b", "вай-фай", text)
    text = _DATE_NUM_RE.sub(_date_num_sub, text)      # 12.10.2026
    text = _DATE_TEXT_RE.sub(_date_text_sub, text)    # 12 октября
    text = _YEAR_RE.sub(_year_sub, text)              # в 2026 году
    text = _SUFFIX_RE.sub(_suffix_sub, text)          # 3-й, 5-м, 90-х
    text = _TIME_RE.sub(_time_sub, text)              # 09:40
    text = re.sub(r"(?<!\w)-(?=\d)", " минус ", text)
    text = _UNIT_RE.sub(_unit_sub, text)              # 16 ГБ, 50%, 45°C
    text = _NUM_RE.sub(_num_sub, text)                # остальные числа
    for sym, spoken in SYMBOLS.items():
        text = text.replace(sym, spoken)
    text = re.sub(r"[A-Za-z]+", _latin_sub, text)

    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)
    text = re.sub(r"(?<=\S)-\s+", " ", text)                       # «джи-пи-ти- четыре» -> без лишнего дефиса
    text = re.sub(r"\b([Вв]) (вт[а-яё]+)", r"\1о \2", text)       # «в втором» -> «во втором»
    return text.strip()


if __name__ == "__main__":
    samples = [
        "Встреча в 2026 году, а не с 2026 года и не к 2030 году.",
        "Сегодня 12 октября 2026 года, до 12 октября осталось немного. Дата: 12.10.2026.",
        "Это было в 2000 году и в 90-х, а сейчас 2026 г.",
        "Через 21 минуту, 22 минуты, 5 минут; до 5 минут, к 5 часам, с 5 до 10 часов, перед 3 днями.",
        "Загрузка CPU 1,1%, до 50% и до 21%, от -5 до 5°C, свободно 16 ГБ, до 2500 рублей.",
        "Живу на 5-м этаже, 3-й этаж, к 3-му числу. Сейчас 09:40, Linux, Wi-Fi 5 ГГц, 2+2=4.",
    ]
    for s in samples:
        print(s)
        print("→", normalize_for_tts(s), "\n")