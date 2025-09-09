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
    get_productivity_periods, get_user_metrics, save_day_plan, save_improvement_suggestions,
    update_user_iaf
)
from .utils import parse_metrics_file, build_prompt_for_llm
from .llm_client import analyze_metrics

DOWNLOAD_DIR = Path(settings.DOWNLOADS_DIR)
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Состояния пользователей
user_states = {}

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начальная команда - показывает экран приветствия"""
    tg_id = update.effective_user.id
    name = update.effective_user.full_name
    
    # Создаем пользователя в БД
    async with AsyncSessionLocal() as session:
        await get_or_create_user(session, telegram_id=tg_id, name=name)
    
    # Сбрасываем состояние пользователя
    user_states[tg_id] = "welcome"
    
    # Создаем клавиатуру с кнопкой "Введи свои IAF"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Введи свои IAF", callback_data="input_iaf")]
    ])
    
    await update.message.reply_text(
        "Привет! Я помогу составить для тебя время продуктивности и отдыха",
        reply_markup=keyboard
    )

async def cb_input_iaf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия кнопки 'Введи свои IAF'"""
    query = update.callback_query
    await query.answer()
    
    tg_id = query.from_user.id
    user_states[tg_id] = "waiting_iaf"
    
    await query.edit_message_text(
        "Пожалуйста, введи свою индивидуальную альфа-частоту (IAF) в Гц.\n"
        "Например: 10.5 или 11.2\n\n"
        "Просто напиши число в следующем сообщении."
    )

async def handle_iaf_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода IAF пользователем"""
    if not update.message or not update.message.text:
        return
    
    tg_id = update.effective_user.id
    
    # Проверяем, что пользователь в состоянии ожидания IAF
    if user_states.get(tg_id) != "waiting_iaf":
        return
    
    try:
        iaf = float(update.message.text.replace(',', '.'))
        if iaf < 7.0 or iaf > 14.0:
            await update.message.reply_text(
                "IAF должен быть в диапазоне 7-14 Гц. Попробуй еще раз."
            )
            return
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введи число. Например: 10.5"
        )
        return
    
    # Сохраняем IAF в БД
    async with AsyncSessionLocal() as session:
        await update_user_iaf(session, tg_id, iaf)
    
    # Меняем состояние и показываем кнопку загрузки файла
    user_states[tg_id] = "ready_for_file"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Загрузи файл с метриками", callback_data="upload_file")]
    ])
    
    await update.message.reply_text(
        f"Отлично! Твой IAF: {iaf} Гц\n\n"
        "Теперь загрузи файл с метриками (CSV или XLSX)",
        reply_markup=keyboard
    )

async def cb_upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия кнопки 'Загрузи файл с метриками' или 'Прикрепить файл'"""
    query = update.callback_query
    await query.answer()
    
    tg_id = query.from_user.id
    user_states[tg_id] = "waiting_file"
    
    await query.edit_message_text(
        "Прикрепи файл с метриками (CSV или XLSX).\n\n"
        "Файл должен содержать колонки:\n"
        "• timestamp - время измерения\n"
        "• cognitive_score - когнитивный скор\n"
        "• focus - концентрация\n"
        "• chill - расслабление\n"
        "• stress - стресс\n"
        "• и другие метрики..."
    )

async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка загруженного файла"""
    if not update.message or not update.message.document:
        return
    
    tg_id = update.effective_user.id
    
    # Проверяем, что пользователь в состоянии ожидания файла
    if user_states.get(tg_id) != "waiting_file":
        await update.message.reply_text("Сначала нажми 'Загрузи файл с метриками'")
        return
    
    doc = update.message.document
    name = update.effective_user.full_name
    
    # Проверяем расширение файла
    if not doc.file_name.lower().endswith(('.csv', '.xlsx')):
        await update.message.reply_text("Поддерживаются только файлы CSV и XLSX")
        return
    
    # Проверяем размер файла (максимум 20MB)
    if doc.file_size and doc.file_size > 20 * 1024 * 1024:
        await update.message.reply_text(
            "❌ Файл слишком большой\n\n"
            "Максимальный размер файла: 20MB\n"
            f"Размер вашего файла: {doc.file_size / (1024*1024):.1f}MB\n\n"
            "Попробуйте уменьшить размер файла или разделить на части."
        )
        return
    
    # Сохраняем файл с обработкой таймаута
    saved_path = DOWNLOAD_DIR / f"{tg_id}_{doc.file_name}"
    try:
        await update.message.reply_text("📥 Скачиваю файл...")
        file = await doc.get_file()
        
        # Пробуем скачать через прямую ссылку (быстрее для больших файлов)
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(file.file_path) as response:
                    if response.status == 200:
                        with open(saved_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        await update.message.reply_text("✅ Файл скачан успешно")
                    else:
                        raise Exception(f"HTTP {response.status}")
        except Exception:
            # Если не получилось через aiohttp, используем стандартный метод
            await file.download_to_drive(str(saved_path))
            await update.message.reply_text("✅ Файл скачан успешно")
            
    except Exception as e:
        error_msg = str(e)
        if "Timed out" in error_msg or "timeout" in error_msg.lower():
            await update.message.reply_text(
                f"⏰ Таймаут загрузки файла\n\n"
                f"Файл слишком большой или медленное соединение.\n"
                f"Попробуйте:\n"
                f"• Уменьшить размер файла (максимум 20MB)\n"
                f"• Проверить интернет-соединение\n"
                f"• Попробовать позже\n\n"
                f"Размер файла: {doc.file_size / (1024*1024):.1f}MB" if doc.file_size else "Размер неизвестен"
            )
        else:
            await update.message.reply_text(
                f"❌ Ошибка загрузки файла\n\n"
                f"Не удалось скачать файл с серверов Telegram.\n"
                f"Попробуйте:\n"
                f"• Проверить интернет-соединение\n"
                f"• Загрузить файл меньшего размера\n"
                f"• Попробовать позже\n\n"
                f"Техническая ошибка: {error_msg}"
            )
        return
    
    await update.message.reply_text("Файл получен. Парсю...")

    try:
        rows, status = parse_metrics_file(str(saved_path))
        
        # Обрабатываем ошибки
        if status.startswith("file_error"):
            error_msg = status.split(": ", 1)[1] if ": " in status else "Неизвестная ошибка"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Start (переход на начало)", callback_data="restart")]
            ])
            await update.message.reply_text(
                f"❌ Ошибка загрузки файла\n\n"
                f"Причина: {error_msg}\n\n"
                f"Таблица продуктивных часов не может быть сформирована",
                reply_markup=keyboard
            )
            return
            
        elif status.startswith("incomplete_data"):
            error_msg = status.split(": ", 1)[1] if ": " in status else "Неполные данные"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📎 Прикрепить файл", callback_data="upload_file")]
            ])
            await update.message.reply_text(
                f"⚠️ Неполные данные\n\n"
                f"Проверьте файл:\n"
                f"• временные интервалы\n"
                f"• обязательные метрики\n\n"
                f"Исправьте и попробуйте еще раз",
                reply_markup=keyboard
            )
            return
            
        elif status != "success":
            await update.message.reply_text(f"Неизвестная ошибка: {status}")
            return
            
    except Exception as e:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Start (переход на начало)", callback_data="restart")]
        ])
        await update.message.reply_text(
            f"❌ Ошибка загрузки файла\n\n"
            f"Причина: {str(e)}\n\n"
            f"Таблица продуктивных часов не может быть сформирована",
            reply_markup=keyboard
        )
        return

    # Сохраняем метрики в БД
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, telegram_id=tg_id, name=name)
        n = await save_metrics_bulk(session, user.user_id, rows)

    await update.message.reply_text(f"Сохранено {n} строк метрик. Запускаю анализ...")

    # Анализируем метрики через LLM (DeepSeek)
    expert_instruction = """
Ты — эксперт в области нейрофизиологии человека и нейропсихофизиологии, 
специализируешься на анализе BCI/ЭЭГ данных и работе с когнитивными паттернами. 
Используй подходы доказательной медицины и результаты исследований 
(Базановой Ольги Михайловны, Pfurtscheller, Klimesch и др.) для построения точного и индивидуализированного 
профиля нейрофизиологического состояния.

Требуется:
1. Проанализировать данные с учётом двух типов активности и временной разнородности сессий.  
2. Выявить оптимальные показатели работоспособности и текущее состояние.  
3. С высокой точностью определить:  
   • Лучшие часы дня для выполнения сложной работы.  
   • Окна перегрузки и падения фокуса.  

Формат ответа — строгий JSON:  
{
  "productivity_periods": [
    {"start_time": "HH:MM", "end_time": "HH:MM", "recommended_activity": "string"}
  ],
  "day_plan": "string",
  "improvement_suggestions": ["string", "string"]
}
"""

    prompt = build_prompt_for_llm(
        user_name=name,
        metrics_rows=rows,
        instruction=expert_instruction
    )

    try:
        raw = await analyze_metrics(prompt)
        

        
        # Очищаем ответ от лишних символов и форматирования
        cleaned_raw = raw.strip()
        
        # Убираем markdown блоки ```json и ```
        if cleaned_raw.startswith("```json"):
            cleaned_raw = cleaned_raw[7:]  # убираем ```json
        if cleaned_raw.startswith("```"):
            cleaned_raw = cleaned_raw[3:]   # убираем ```
        if cleaned_raw.endswith("```"):
            cleaned_raw = cleaned_raw[:-3]  # убираем ```
        
        cleaned_raw = cleaned_raw.strip()
        
        # Дополнительная очистка - убираем возможные лишние символы в начале
        if not cleaned_raw.startswith("{"):
            # Ищем первую открывающую скобку
            start_idx = cleaned_raw.find("{")
            if start_idx != -1:
                cleaned_raw = cleaned_raw[start_idx:]
        
        # Убираем возможные лишние символы в конце
        if not cleaned_raw.endswith("}"):
            # Ищем последнюю закрывающую скобку
            end_idx = cleaned_raw.rfind("}")
            if end_idx != -1:
                cleaned_raw = cleaned_raw[:end_idx + 1]
        
        data = json.loads(cleaned_raw)
    except json.JSONDecodeError as e:
        await update.message.reply_text(
            f"❌ Ошибка парсинга JSON от модели\n\n"
            f"Модель вернула некорректный JSON.\n"
            f"Попробуйте загрузить файл еще раз.\n\n"
            f"Ответ модели:\n{raw[:500]}...\n\n"
            f"Ошибка: {str(e)}"
        )
        return
    except Exception as e:
        # Если произошла ошибка до определения raw, показываем текст ошибки
        err_text = str(e)
        try:
            fallback = raw  # может не существовать
        except Exception:
            fallback = "<нет ответа от модели>"
        await update.message.reply_text(
            "Ошибка при анализе через LLM. "
            + ("\nОтвет модели:\n" + str(fallback) if fallback else "")
            + ("\nТехническая ошибка: " + err_text if err_text else "")
        )
        return

    periods = data.get("productivity_periods", []) or []
    day_plan = data.get("day_plan", "") or ""
    suggestions = data.get("improvement_suggestions", []) or []

    # Сохраняем периоды продуктивности в БД
    async with AsyncSessionLocal() as session:
        await save_productivity_periods(session, user.user_id, periods)

    # Меняем состояние
    user_states[tg_id] = "analysis_complete"
    
    # Показываем результаты и кнопки
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Загрузить файл", callback_data="download_csv")],
        [InlineKeyboardButton("Получить рекомендации по режиму дня", callback_data="get_recommendations")],
        [InlineKeyboardButton("🔄 Start (переход на начало)", callback_data="restart")]
    ])

    preview = "\n".join([f"{p.get('start_time','?')}–{p.get('end_time','?')}: {p.get('recommended_activity','')}" for p in periods[:5]]) or "LLM не нашёл явных периодов."
    msg = f"Анализ завершен! Найдено {len(periods)} периодов.\n\nПревью:\n{preview}"
    if day_plan:
        msg += f"\n\nПлан дня:\n{day_plan}"
    if suggestions:
        msg += "\n\nПример советов:\n- " + "\n- ".join(suggestions[:3])

    await update.message.reply_text(msg, reply_markup=keyboard)

async def cb_download_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопки 'Загрузить файл'"""
    query = update.callback_query
    await query.answer()
    
    tg_id = query.from_user.id
    
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, telegram_id=tg_id, name=query.from_user.full_name)
        periods = await get_productivity_periods(session, user.user_id)
    
    if not periods:
        await query.edit_message_text("Нет сохранённых периодов. Пришлите файл с метриками сначала.")
        return
    
    # Создаем CSV файл
    df = pd.DataFrame([{
        "start_time": p.start_time.strftime("%H:%M") if p.start_time else "",
        "end_time": p.end_time.strftime("%H:%M") if p.end_time else "",
        "recommended_activity": p.recommended_activity or ""
    } for p in periods])
    
    out_path = DOWNLOAD_DIR / f"{tg_id}_periods.csv"
    df.to_csv(out_path, index=False)
    
    # Отправляем файл с обработкой таймаута
    try:
        with open(out_path, "rb") as f:
            await context.bot.send_document(chat_id=tg_id, document=f)
    except Exception as e:
        await query.edit_message_text(
            f"❌ Ошибка отправки файла\n\n"
            f"Не удалось отправить CSV файл.\n"
            f"Попробуйте позже или обратитесь к администратору.\n\n"
            f"Ошибка: {str(e)}"
        )
        return
    
    # Показываем кнопки для следующего шага
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Получить рекомендации по режиму дня", callback_data="get_recommendations")],
        [InlineKeyboardButton("🔄 Start (переход на начало)", callback_data="restart")]
    ])
    
    await query.message.reply_text(
        "Файл отправлен! Теперь можешь получить рекомендации по режиму дня.",
        reply_markup=keyboard
    )

async def cb_get_recommendations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопки 'Получить рекомендации по режиму дня'"""
    query = update.callback_query
    await query.answer()
    
    tg_id = query.from_user.id
    
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, telegram_id=tg_id, name=query.from_user.full_name)
        metrics = await get_user_metrics(session, user.user_id)
    
    if not metrics:
        await query.edit_message_text("Нет метрик. Пришлите файл сначала.")
        return
    
    # Подготавливаем данные для LLM
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
    
    # Получаем рекомендации от LLM
    prompt = build_prompt_for_llm(
        user_name=query.from_user.full_name, 
        metrics_rows=rows,
        instruction = """
Ты — эксперт в области нейрофизиологии человека. 
Используя анализ BCI/ЭЭГ-метрик и знания о циркадных ритмах, составь персональное расписание дня (day_plan). 
В расписании должны быть:
- Часы максимальной продуктивности (для сложных задач).
- Времена отдыха/релаксации.
- Оптимальное время для сна.

Ответ верни строго в JSON с ключом "day_plan".
"""

    )
    
    try:
        raw = await analyze_metrics(prompt)
        
        # Очищаем ответ от лишних символов и форматирования
        cleaned_raw = raw.strip()
        
        # Убираем markdown блоки ```json и ```
        if cleaned_raw.startswith("```json"):
            cleaned_raw = cleaned_raw[7:]  # убираем ```json
        if cleaned_raw.startswith("```"):
            cleaned_raw = cleaned_raw[3:]   # убираем ```
        if cleaned_raw.endswith("```"):
            cleaned_raw = cleaned_raw[:-3]  # убираем ```
        
        cleaned_raw = cleaned_raw.strip()
        
        # Дополнительная очистка - убираем возможные лишние символы в начале
        if not cleaned_raw.startswith("{"):
            # Ищем первую открывающую скобку
            start_idx = cleaned_raw.find("{")
            if start_idx != -1:
                cleaned_raw = cleaned_raw[start_idx:]
        
        # Убираем возможные лишние символы в конце
        if not cleaned_raw.endswith("}"):
            # Ищем последнюю закрывающую скобку
            end_idx = cleaned_raw.rfind("}")
            if end_idx != -1:
                cleaned_raw = cleaned_raw[:end_idx + 1]
        
        data = json.loads(cleaned_raw)
    except json.JSONDecodeError as e:
        await query.edit_message_text(
            f"❌ Ошибка парсинга JSON от модели\n\n"
            f"Модель вернула некорректный JSON.\n"
            f"Попробуйте загрузить файл еще раз.\n\n"
            f"Ответ модели:\n{raw[:500]}...\n\n"
            f"Ошибка: {str(e)}"
        )
        return
    except Exception as e:
        await query.edit_message_text(f"Ошибка LLM: {e}\nОтвет:\n{raw}")
        return
    
    day_plan = data.get("day_plan", "(нет)")
    
    # Сохраняем рекомендации в БД
    try:
        async with AsyncSessionLocal() as session:
            await save_day_plan(session, user.user_id, day_plan)
    except Exception as e:
        await query.edit_message_text(
            f"❌ Ошибка сохранения в базу данных\n\n"
            f"Не удалось сохранить рекомендации.\n"
            f"Попробуйте позже.\n\n"
            f"Ошибка: {str(e)}"
        )
        return
    
    # Показываем рекомендации и кнопки для следующего шага
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Улучшить режим дня", callback_data="improve_schedule")],
        [InlineKeyboardButton("🔄 Start (переход на начало)", callback_data="restart")]
    ])
    
    await query.message.reply_text(
        f"📅 Рекомендации по режиму дня:\n\n{day_plan}",
        reply_markup=keyboard
    )

async def cb_improve_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопки 'Улучшить режим дня'"""
    query = update.callback_query
    await query.answer()
    
    tg_id = query.from_user.id
    
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, telegram_id=tg_id, name=query.from_user.full_name)
        metrics = await get_user_metrics(session, user.user_id)
    
    # Подготавливаем данные для LLM
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
    
    # Получаем улучшения от LLM
    prompt = build_prompt_for_llm(
        user_name=query.from_user.full_name, 
        metrics_rows=rows,
        instruction = """
Ты — эксперт в области нейропсихофизиологии. 
На основе анализа когнитивных паттернов и текущего расписания пользователя предложи конкретные шаги по улучшению режима дня. 
Фокусируйся на:
- Точечных изменениях, повышающих продуктивность.
- Снижение утомляемости.
- Методы восстановления ресурсов.

Ответ верни строго в JSON с ключом "improvement_suggestions" (массив строк).
"""

    )
    
    try:
        raw = await analyze_metrics(prompt)
        
        # Очищаем ответ от лишних символов и форматирования
        cleaned_raw = raw.strip()
        
        # Убираем markdown блоки ```json и ```
        if cleaned_raw.startswith("```json"):
            cleaned_raw = cleaned_raw[7:]  # убираем ```json
        if cleaned_raw.startswith("```"):
            cleaned_raw = cleaned_raw[3:]   # убираем ```
        if cleaned_raw.endswith("```"):
            cleaned_raw = cleaned_raw[:-3]  # убираем ```
        
        cleaned_raw = cleaned_raw.strip()
        
        # Дополнительная очистка - убираем возможные лишние символы в начале
        if not cleaned_raw.startswith("{"):
            # Ищем первую открывающую скобку
            start_idx = cleaned_raw.find("{")
            if start_idx != -1:
                cleaned_raw = cleaned_raw[start_idx:]
        
        # Убираем возможные лишние символы в конце
        if not cleaned_raw.endswith("}"):
            # Ищем последнюю закрывающую скобку
            end_idx = cleaned_raw.rfind("}")
            if end_idx != -1:
                cleaned_raw = cleaned_raw[:end_idx + 1]
        
        data = json.loads(cleaned_raw)
    except json.JSONDecodeError as e:
        await query.edit_message_text(
            f"❌ Ошибка парсинга JSON от модели\n\n"
            f"Модель вернула некорректный JSON.\n"
            f"Попробуйте загрузить файл еще раз.\n\n"
            f"Ответ модели:\n{raw[:500]}...\n\n"
            f"Ошибка: {str(e)}"
        )
        return
    except Exception as e:
        await query.edit_message_text(f"Ошибка LLM: {e}\nОтвет:\n{raw}")
        return
    
    tips = data.get("improvement_suggestions", []) or []
    
    if tips:
        # Сохраняем улучшения в БД
        try:
            async with AsyncSessionLocal() as session:
                await save_improvement_suggestions(session, user.user_id, tips)
        except Exception as e:
            await query.edit_message_text(
                f"❌ Ошибка сохранения в базу данных\n\n"
                f"Не удалось сохранить советы.\n"
                f"Попробуйте позже.\n\n"
                f"Ошибка: {str(e)}"
            )
            return
        
        text = "💡 Советы по улучшению режима дня:\n\n" + "\n".join(f"• {t}" for t in tips)
    else:
        text = "Советов по улучшению нет."
    
    # Показываем финальные кнопки
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Start (переход на начало)", callback_data="restart")]
    ])
    
    await query.message.reply_text(text, reply_markup=keyboard)

async def cb_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопки 'Start (переход на начало)'"""
    query = update.callback_query
    await query.answer()
    
    # Сбрасываем состояние и возвращаемся к началу
    tg_id = query.from_user.id
    user_states[tg_id] = "welcome"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Введи свои IAF", callback_data="input_iaf")]
    ])
    
    await query.edit_message_text(
        "Привет! Я помогу составить для тебя время продуктивности и отдыха",
        reply_markup=keyboard
    )

def main():
    app = Application.builder().token(settings.BOT_TOKEN).build()
    
    # Увеличиваем таймауты для загрузки файлов
    app.bot.request.timeout = 300  # 5 минут для больших файлов
    app.bot.request.connect_timeout = 60  # 1 минута на подключение
    
    # Обработчики команд
    app.add_handler(CommandHandler("start", cmd_start))
    
    # Обработчики кнопок
    app.add_handler(CallbackQueryHandler(cb_input_iaf, pattern="^input_iaf$"))
    app.add_handler(CallbackQueryHandler(cb_upload_file, pattern="^upload_file$"))
    app.add_handler(CallbackQueryHandler(cb_download_csv, pattern="^download_csv$"))
    app.add_handler(CallbackQueryHandler(cb_get_recommendations, pattern="^get_recommendations$"))
    app.add_handler(CallbackQueryHandler(cb_improve_schedule, pattern="^improve_schedule$"))
    app.add_handler(CallbackQueryHandler(cb_restart, pattern="^restart$"))
    
    # Обработчики сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_iaf_input))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
