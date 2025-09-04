#это основной код бота. Он принимает файл, парсит, сохраняет в БД, вызывает LLM (или мок) и отдаёт пользователю результаты с кнопками
import json
from pathlib import Path
from datetime import datetime
import pandas as pd

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
)

from .config import settings
from .database import AsyncSessionLocal
from .crud import (
    get_or_create_user, save_metrics_bulk, save_productivity_periods,
    get_productivity_periods, get_user_metrics, save_day_plan, save_improvement_suggestions
)
from .utils import parse_metrics_file, build_prompt_for_llm
from .llm_client import analyze_metrics

DOWNLOAD_DIR = Path(settings.DOWNLOADS_DIR)
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    name = update.effective_user.full_name
    async with AsyncSessionLocal() as session:
        await get_or_create_user(session, telegram_id=tg_id, name=name)
    await update.message.reply_text("Привет! Пришли CSV/XLSX с колонкой 'timestamp' и метриками.")

async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.document:
        return
    doc = update.message.document
    tg_id = update.effective_user.id
    name = update.effective_user.full_name
    saved_path = DOWNLOAD_DIR / f"{tg_id}_{doc.file_name}"
    file = await doc.get_file()
    await file.download_to_drive(str(saved_path))
    await update.message.reply_text("Файл получен. Парсю...")

    try:
        rows = parse_metrics_file(str(saved_path))
        if not rows:
            await update.message.reply_text("В файле нет данных или отсутствуют нужные колонки.")
            return
    except Exception as e:
        await update.message.reply_text(f"Ошибка парсинга: {e}")
        return

    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, telegram_id=tg_id, name=name)
        n = await save_metrics_bulk(session, user.user_id, rows)

    await update.message.reply_text(f"Сохранено {n} строк метрик. Запускаю анализ...")

    prompt = build_prompt_for_llm(user_name=name, metrics_rows=rows,
                                 instruction="Identify hourly productivity and rest periods. Suggest a daily plan. Return strict JSON.")
    try:
        raw = await analyze_metrics(prompt)
        data = json.loads(raw)
    except Exception as e:
        await update.message.reply_text("LLM вернул невалидный ответ. Сырой текст:\n" + str(raw))
        return

    periods = data.get("productivity_periods", []) or []
    day_plan = data.get("day_plan", "") or ""
    suggestions = data.get("improvement_suggestions", []) or []

    async with AsyncSessionLocal() as session:
        await save_productivity_periods(session, user.user_id, periods)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Скачать таблицу периодов", callback_data="csv")],
        [InlineKeyboardButton("🧭 Режим дня (LLM)", callback_data="plan")],
        [InlineKeyboardButton("⚡ Улучшить режим дня", callback_data="improve")],
    ])

    preview = "\n".join([f"{p.get('start_time','?')}–{p.get('end_time','?')}: {p.get('recommended_activity','')}" for p in periods[:5]]) or "LLM не нашёл явных периодов."
    msg = f"Готово! Нашёл {len(periods)} периодов.\n\nПревью:\n{preview}"
    if day_plan:
        msg += f"\n\nDay plan:\n{day_plan}"
    if suggestions:
        msg += "\n\nПример советов:\n- " + "\n- ".join(suggestions[:3])

    await update.message.reply_text(msg, reply_markup=kb)

async def cb_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tg_id = query.from_user.id
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, telegram_id=tg_id, name=query.from_user.full_name)
        periods = await get_productivity_periods(session, user.user_id)
    if not periods:
        await query.edit_message_text("Нет сохранённых периодов. Пришлите файл с метриками сначала.")
        return
    df = pd.DataFrame([{
        "start_time": p.start_time.strftime("%H:%M") if p.start_time else "",
        "end_time": p.end_time.strftime("%H:%M") if p.end_time else "",
        "recommended_activity": p.recommended_activity or ""
    } for p in periods])
    out_path = DOWNLOAD_DIR / f"{tg_id}_periods.csv"
    df.to_csv(out_path, index=False)
    # отправляем файл
    with open(out_path, "rb") as f:
        await context.bot.send_document(chat_id=tg_id, document=f)

async def cb_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tg_id = query.from_user.id
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, telegram_id=tg_id, name=query.from_user.full_name)
        metrics = await get_user_metrics(session, user.user_id)
    if not metrics:
        await query.edit_message_text("Нет метрик. Пришлите файл сначала.")
        return
    rows = []
    for m in metrics[:120]:
        rows.append({
            "timestamp": m.timestamp,
            "cognitive_score": m.cognitive_score,
            "focus": m.focus,
            "chill": m.chill,
            "stress": m.stress,
            "self_control": m.self_control,
            "anger": m.anger,
            "relaxation_index": m.relaxation_index,
            "concentration_index": m.concentration_index,
            "fatique_score": m.fatique_score,
            "reverse_fatique": m.reverse_fatique,
            "alpha_gravity": m.alpha_gravity,
            "heart_rate": m.heart_rate,
        })
    prompt = build_prompt_for_llm(user_name=query.from_user.full_name, metrics_rows=rows,
                                 instruction="Return ONLY JSON with key 'day_plan' (string).")
    try:
        raw = await analyze_metrics(prompt)
        data = json.loads(raw)
    except Exception as e:
        await query.edit_message_text(f"Ошибка LLM: {e}\nОтвет:\n{raw}")
        return
    day_plan = data.get("day_plan", "(нет)")
    async with AsyncSessionLocal() as session:
        await save_day_plan(session, user.user_id, day_plan)
    await query.message.reply_text(f"Режим дня:\n{day_plan}")

async def cb_improve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tg_id = query.from_user.id
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, telegram_id=tg_id, name=query.from_user.full_name)
        metrics = await get_user_metrics(session, user.user_id)
    rows = []
    for m in metrics[:120]:
        rows.append({
            "timestamp": m.timestamp,
            "cognitive_score": m.cognitive_score,
            "focus": m.focus,
            "chill": m.chill,
            "stress": m.stress,
            "self_control": m.self_control,
            "anger": m.anger,
            "relaxation_index": m.relaxation_index,
            "concentration_index": m.concentration_index,
            "fatique_score": m.fatique_score,
            "reverse_fatique": m.reverse_fatique,
            "alpha_gravity": m.alpha_gravity,
            "heart_rate": m.heart_rate,
        })
    prompt = build_prompt_for_llm(user_name=query.from_user.full_name, metrics_rows=rows,
                                 instruction="Return ONLY JSON with key 'improvement_suggestions' (array of strings).")
    try:
        raw = await analyze_metrics(prompt)
        data = json.loads(raw)
    except Exception as e:
        await query.edit_message_text(f"Ошибка LLM: {e}\nОтвет:\n{raw}")
        return
    tips = data.get("improvement_suggestions", []) or []
    if tips:
        async with AsyncSessionLocal() as session:
            await save_improvement_suggestions(session, user.user_id, tips)
        text = "Советы по улучшению режима:\n" + "\n".join(f"• {t}" for t in tips)
    else:
        text = "Советов нет."
    await query.message.reply_text(text)

def main():
    app = Application.builder().token(settings.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))
    app.add_handler(CallbackQueryHandler(cb_csv, pattern="^csv$"))
    app.add_handler(CallbackQueryHandler(cb_plan, pattern="^plan$"))
    app.add_handler(CallbackQueryHandler(cb_improve, pattern="^improve$"))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
