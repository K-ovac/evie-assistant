#!/usr/bin/env python3
"""check_llm.py — проверка локальных серверов llama.cpp для Иви: чат, вызов инструмента, эмбеддинги.
Запуск:  python3 check_llm.py   (нужен пакет requests; по умолчанию порты 8081 и 8082)"""
import argparse
import math
import sys
import time

import requests

QUERY_PREFIX = "task: search result | query: "
DOC_PREFIX = "title: none | text: "

TIME_TOOL = {
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": "Возвращает текущие дату и время.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}

results = []


def report(name, passed, detail=""):
    results.append(passed)
    print(f"[{'OK ' if passed else 'ОШИБКА'}] {name}" + (f": {detail}" if detail else ""))


def post(url, payload, timeout=120):
    t0 = time.time()
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json(), time.time() - t0


def check_models(base, expected, label):
    try:
        data = requests.get(f"{base}/v1/models", timeout=10).json()
        names = [m.get("id") for m in data.get("data", [])]
        report(f"{label}: сервер отвечает", True, ", ".join(map(str, names)))
        if expected not in names:
            print(f"        (внимание: имя '{expected}' не найдено среди моделей; используй из списка выше)")
    except Exception as e:
        report(f"{label}: сервер отвечает", False, str(e))
        return False
    return True


def check_chat(base, model):
    try:
        data, wall = post(f"{base}/v1/chat/completions", {
            "model": model, "temperature": 0.3, "max_tokens": 60,
            "messages": [{"role": "user", "content": "Ответь одним словом: привет."}],
        })
        msg = data["choices"][0]["message"]
        text = (msg.get("content") or "").strip()
        usage = data.get("usage", {})
        timings = data.get("timings", {})
        speed = timings.get("predicted_per_second")
        detail = f"{wall:.1f} с, токенов: {usage.get('completion_tokens', '?')}"
        if speed:
            detail += f", генерация {speed:.0f} ток/с"
        report("чат: ответ получен", bool(text), f"«{text[:60]}», {detail}")
        if any(m in text for m in ("<|channel>", "<think>", "<|think|>")):
            print("        (внимание: в ответе виден блок размышлений, его нужно вырезать)")
    except Exception as e:
        report("чат: ответ получен", False, str(e))


def check_tools(base, model):
    try:
        data, wall = post(f"{base}/v1/chat/completions", {
            "model": model, "temperature": 0.2, "tools": [TIME_TOOL],
            "messages": [{"role": "user", "content": "Который сейчас час? Используй инструмент."}],
        })
        msg = data["choices"][0]["message"]
        calls = msg.get("tool_calls") or []
        name = calls[0]["function"]["name"] if calls else None
        report("инструменты: модель вызвала get_current_time", name == "get_current_time",
               f"{wall:.1f} с" if calls else "вызова нет (проверь флаг --jinja и шаблон модели)")
    except Exception as e:
        report("инструменты: модель вызвала get_current_time", False, str(e))


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def check_embeddings(base, model, dim):
    texts = [
        QUERY_PREFIX + "как мне открыть браузер",
        DOC_PREFIX + "Максим открывает браузер Firefox для работы",
        DOC_PREFIX + "Рецепт борща с говядиной и свёклой",
    ]
    try:
        data, wall = post(f"{base}/v1/embeddings", {"model": model, "input": texts, "encoding_format": "float"})
        vecs = [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
        report("эмбеддинги: сервер ответил", len(vecs) == 3, f"{wall * 1000:.0f} мс на 3 текста")
        report("эмбеддинги: размерность", all(len(v) == dim for v in vecs), f"получено {len(vecs[0])}, ожидалось {dim}")
        finite = all(math.isfinite(x) for v in vecs for x in v)
        report("эмбеддинги: все числа конечные (нет NaN)", finite)
        norms = [math.sqrt(sum(x * x for x in v)) for v in vecs]
        report("эмбеддинги: векторы нормализованы", all(abs(n - 1) < 0.05 for n in norms),
               ", ".join(f"{n:.3f}" for n in norms))
        good, bad = cosine(vecs[0], vecs[1]), cosine(vecs[0], vecs[2])
        report("эмбеддинги: релевантный документ ближе нерелевантного", good > bad,
               f"{good:.3f} против {bad:.3f}")
    except Exception as e:
        report("эмбеддинги", False, str(e))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat", default="http://127.0.0.1:8081")
    ap.add_argument("--embed", default="http://127.0.0.1:8082")
    ap.add_argument("--chat-model", default="gemma4-e4b")
    ap.add_argument("--embed-model", default="embeddinggemma2")
    ap.add_argument("--dim", type=int, default=768)
    args = ap.parse_args()

    if check_models(args.chat, args.chat_model, "чат"):
        check_chat(args.chat, args.chat_model)
        check_tools(args.chat, args.chat_model)
    if check_models(args.embed, args.embed_model, "эмбеддинги"):
        check_embeddings(args.embed, args.embed_model, args.dim)

    print(f"\nИтог: {sum(results)} из {len(results)} проверок пройдено.")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
