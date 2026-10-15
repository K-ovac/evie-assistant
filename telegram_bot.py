# telegram_bot.py — общение с Иви через Telegram
# Запуск: python telegram_bot.py   (отдельный процесс, можно параллельно с main.py)
# Зависимость: pip install "python-telegram-bot>=21"
import asyncio
import logging
import uuid

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    ContextTypes, MessageHandler, filters,
)

from log.logger_setup import setup_logger
logger = setup_logger()

from data.config import TG_BOT_TOKEN, TG_ALLOWED_IDS, TG_PROXY, AI_NAME
from handlers.llm_handler import get_ai_response

histories = {}  # chat_id -> история диалога
pending = {}    # key -> Future с ответом на подтверждение


def is_allowed(update: Update) -> bool:
    user = update.effective_user
    return bool(user and user.id in TG_ALLOWED_IDS)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await update.message.reply_text(f"Твой id: {update.effective_user.id}")  # чтобы вписать в TG_ALLOWED_IDS
        return
    await update.message.reply_text(f"{AI_NAME} на связи. Пиши что угодно. /reset — очистить диалог.")


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_allowed(update):
        histories.pop(update.effective_chat.id, None)
        await update.message.reply_text("Диалог очищен.")


async def ask_confirm(context, chat_id, description) -> bool:
    key = uuid.uuid4().hex[:8]
    future = asyncio.get_running_loop().create_future()
    pending[key] = future
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Выполнить", callback_data=f"ok:{key}"),
        InlineKeyboardButton("❌ Отмена", callback_data=f"no:{key}"),
    ]])
    await context.bot.send_message(chat_id, f"⚠️ Разрешить действие?\n\n{description}", reply_markup=keyboard)
    try:
        return await asyncio.wait_for(future, timeout=120)
    except asyncio.TimeoutError:
        return False
    finally:
        pending.pop(key, None)


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in TG_ALLOWED_IDS:
        await query.answer("Нет доступа", show_alert=True)
        return
    action, key = query.data.split(":", 1)
    future = pending.get(key)
    await query.answer()
    if future and not future.done():
        future.set_result(action == "ok")
    verdict = "✅ Разрешено" if action == "ok" else "❌ Отклонено"
    await query.edit_message_text(f"{query.message.text}\n\n{verdict}")


async def process(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    chat_id = update.effective_chat.id
    history = histories.setdefault(chat_id, [])
    loop = asyncio.get_running_loop()

    # get_ai_response синхронный и идёт в отдельном потоке,
    # поэтому подтверждение из него отправляем обратно в event loop
    def confirm(description: str) -> bool:
        future = asyncio.run_coroutine_threadsafe(ask_confirm(context, chat_id, description), loop)
        try:
            return future.result(timeout=130)
        except Exception:
            return False

    await context.bot.send_chat_action(chat_id, "typing")
    answer = await asyncio.to_thread(get_ai_response, text, history, confirm, "owner", "telegram")
    await update.message.reply_text(answer[:4096])  # лимит Telegram на сообщение


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    await process(update, context, update.message.text)


async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_allowed(update):
        await update.message.reply_text("Голосовые не принимаю, напиши текстом.")


def main():
    if not TG_BOT_TOKEN:
        raise SystemExit("Не задан TG_BOT_TOKEN")
    if not TG_ALLOWED_IDS:
        logger.warning("TG_ALLOWED_IDS пуст — бот никому не отвечает. Напиши /start, чтобы узнать свой id.")

    builder = Application.builder().token(TG_BOT_TOKEN).concurrent_updates(True)  # без этого кнопки подтверждения зависнут
    if TG_PROXY:
        builder = builder.proxy(TG_PROXY).get_updates_proxy(TG_PROXY)
    app = builder.build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, on_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    logger.info(f"{AI_NAME}: Telegram-бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()