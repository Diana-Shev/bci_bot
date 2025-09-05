#парсим файл в строки и собираем текст-промпт для LLM
import pandas as pd
from datetime import datetime, timezone
from typing import List, Dict

NUMERIC_MAP = {
    "cognitive_score": int,
    "focus": int,
    "chill": int,
    "stress": int,
    "self_control": int,
    "anger": int,
    "relaxation_index": float,
    "concentration_index": float,
    "fatique_score": float,        
    "reverse_fatique": float,      
    "alpha_gravity": float,
    "heart_rate": int,
}

ALL_COLS = ["timestamp"] + list(NUMERIC_MAP.keys())

def parse_metrics_file(path: str) -> tuple[List[Dict], str]:
    """
    Парсит файл с метриками и возвращает (данные, статус)
    Статусы: 'success', 'file_error', 'incomplete_data'
    """
    try:
        # Пытаемся прочитать файл
        if path.lower().endswith(".csv"):
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)
    except Exception as e:
        return [], f"file_error: Ошибка чтения файла: {str(e)}"

    # Проверяем наличие колонки timestamp
    if "timestamp" not in df.columns and "time" in df.columns:
        df = df.rename(columns={"time": "timestamp"})

    if "timestamp" not in df.columns:
        return [], "file_error: Отсутствует колонка 'timestamp' или 'time'"

    # Проверяем размер файла
    if len(df) == 0:
        return [], "file_error: Файл пустой"

    # Парсим timestamp
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    valid_timestamps = df.dropna(subset=["timestamp"])
    
    if len(valid_timestamps) == 0:
        return [], "file_error: Нет корректных временных меток"

    # Проверяем наличие обязательных метрик
    required_metrics = ["cognitive_score", "focus", "chill", "stress"]
    missing_metrics = [metric for metric in required_metrics if metric not in df.columns]
    
    if missing_metrics:
        return [], f"incomplete_data: Отсутствуют обязательные метрики: {', '.join(missing_metrics)}"

    # Проверяем временные интервалы (должно быть минимум 2 записи с разными временами)
    unique_times = valid_timestamps["timestamp"].nunique()
    if unique_times < 2:
        return [], "incomplete_data: Недостаточно временных интервалов (минимум 2)"

    # Проверяем качество данных - должно быть минимум 50% заполненных метрик
    total_cells = len(valid_timestamps) * len(required_metrics)
    filled_cells = 0
    for metric in required_metrics:
        filled_cells += valid_timestamps[metric].notna().sum()
    
    fill_ratio = filled_cells / total_cells if total_cells > 0 else 0
    if fill_ratio < 0.5:
        return [], "incomplete_data: Слишком много пустых значений в метриках"

    # Если все проверки пройдены, обрабатываем данные
    existing = [c for c in ALL_COLS if c in df.columns]
    df = df[existing].copy()

    rows = []
    for _, r in df.iterrows():
        item = {"timestamp": pd.to_datetime(r["timestamp"]).to_pydatetime()}
        for key, ptype in NUMERIC_MAP.items():
            if key in df.columns:
                val = r[key]
                if pd.isna(val):
                    item[key] = None
                else:
                    try:
                        item[key] = ptype(val)
                    except Exception:
                        item[key] = None
            else:
                item[key] = None
        rows.append(item)
    
    return rows, "success"

def build_prompt_for_llm(user_name: str, metrics_rows: list, instruction: str) -> str:
    sample = metrics_rows[:120]
    lines = []
    for m in sample:
        t = m["timestamp"].strftime("%Y-%m-%d %H:%M")
        pairs = [f"{k}:{m.get(k)}" for k in NUMERIC_MAP.keys()]
        lines.append(f"{t} | " + ", ".join(pairs))
    table_text = "\n".join(lines)
    prompt = f"""
You analyze EEG/BCI metrics and produce actionable schedules.
User: {user_name}

Metrics (time | key:value):
{table_text}

{instruction}

Return ONLY valid JSON like:
{{
  "productivity_periods":[{{"start_time":"11:00","end_time":"12:00","recommended_activity":"complex tasks"}}],
  "day_plan":"11:00-12:00 complex tasks; 14:00-14:30 rest; sleep before 23:00",
  "improvement_suggestions":["30min breaks each hour in the morning","10min meditation after lunch"]
}}
"""
    return prompt
