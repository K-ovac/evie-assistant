# farewell.py — определяет, что пользователь прощается, а не просто сказал слово «пока» в предложении
import re

# слова, которые могут стоять рядом с прощанием: «ну всё, пока», «спасибо, пока», «пока, Иви»
FILLERS = r"(?:ну|ладно|всё|все|тогда|давай|спасибо|иви)"
FAREWELLS = r"(?:пока|до свидания|до встречи|отключись|выключайся|выход)"
_FAREWELL_RE = re.compile(rf"^(?:{FILLERS}\s+)*{FAREWELLS}(?:\s+{FILLERS})*$")


def is_farewell(text: str) -> bool:
    """True, если ПОСЛЕДНЯЯ часть фразы (после знака препинания) — это прощание."""
    clauses = [c.strip() for c in re.split(r"[.,!?…;:]+", text.lower()) if c.strip()]
    if not clauses:
        return False
    last = " ".join(clauses[-1].split())
    return bool(_FAREWELL_RE.match(last))


if __name__ == "__main__":
    tests = {
        "Пока!": True,
        "Иви, пока.": True,
        "Ну всё, спасибо. Пока.": True,
        "Да нет, не обязательно. Спасибо, я понял. Ладно, всё, спасибо. Пока.": True,
        "Отключись": True,
        "Давай пока проверим, если флатпак на системе или нет.": False,
        "Пока что всё работает. Давай проверим память.": False,
        "Покажи почту": False,
    }
    for phrase, expected in tests.items():
        result = is_farewell(phrase)
        print("OK " if result == expected else "FAIL", result, "|", phrase)