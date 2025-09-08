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

# Все внутренние колонки, которые будут сохраняться
ALL_COLS = ["timestamp"] + list(NUMERIC_MAP.keys())

# Маппинг заголовков CSV → внутренние ключи
CSV_MAP = {
    "cognitive score": "cognitive_score",
    "self-control": "self_control",
    "relaxation index": "relaxation_index",
    "concentration index": "concentration_index",
    "fatique score": "fatique_score",
    "reverse fatique": "reverse_fatique",
    "alpha gravity": "alpha_gravity",
    "heart rate": "heart_rate",
    "focus": "focus",
    "chill": "chill",
    "stress": "stress",
    "anger": "anger"
}

def parse_metrics_file(path: str) -> tuple[List[Dict], str]:
    """
    Парсит CSV/XLSX с метриками и возвращает (данные, статус)
    Конвертирует 'time'/'timestamp' в datetime (offset-naive, UTC).
    Поддерживает CSV с пробелами/дефисами в названиях колонок.
    """
    try:
        if path.lower().endswith(".csv"):
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)
    except Exception as e:
        return [], f"file_error: Ошибка чтения файла: {str(e)}"

    # Нормализуем заголовки
    def _norm(col: str) -> str:
        raw = str(col).replace("\ufeff", "").strip().lower()
        raw = raw.replace("_", " ").replace("-", " ")
        raw = " ".join(raw.split())
        return raw

    normalized_columns = {_norm(c): c for c in df.columns}
    df = df.rename(columns={v: k for k, v in normalized_columns.items()})

    if "timestamp" not in df.columns and "time" in df.columns:
        df = df.rename(columns={"time": "timestamp"})

    if "timestamp" not in df.columns:
        return [], "file_error: Отсутствует колонка 'timestamp' или 'time'"

    if len(df) == 0:
        return [], "file_error: Файл пустой"

    # Парсим timestamp и приводим к offset-naive UTC
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True, infer_datetime_format=True)
    df["timestamp"] = df["timestamp"].dt.tz_convert(None)  # убираем tzinfo, становится naive
    valid_timestamps = df.dropna(subset=["timestamp"])
    if len(valid_timestamps) == 0:
        return [], "file_error: Нет корректных временных меток"

    # Проверка обязательных метрик
    required_metrics = ["cognitive_score", "focus", "chill", "stress"]
    present_metrics = [CSV_MAP.get(col, col) for col in df.columns if CSV_MAP.get(col, col) in NUMERIC_MAP]
    missing_metrics = [metric for metric in required_metrics if metric not in present_metrics]
    if missing_metrics:
        return [], f"incomplete_data: Отсутствуют обязательные метрики: {', '.join(missing_metrics)}"

    if valid_timestamps["timestamp"].nunique() < 2:
        return [], "incomplete_data: Недостаточно временных интервалов (минимум 2)"

    total_cells = len(valid_timestamps) * len(required_metrics)
    filled_cells = sum(valid_timestamps[col].notna().sum() for col in df.columns if CSV_MAP.get(col, col) in required_metrics)
    if filled_cells / total_cells < 0.5:
        return [], "incomplete_data: Слишком много пустых значений в метриках"

    # Формируем итоговые строки
    rows = []
    for _, r in df.iterrows():
        ts_naive = r["timestamp"]  # теперь offset-naive
        item = {"timestamp": ts_naive}
        for csv_col, key in CSV_MAP.items():
            if csv_col in df.columns:
                val = r[csv_col]
                if pd.isna(val):
                    item[key] = None
                else:
                    try:
                        item[key] = NUMERIC_MAP[key](val)
                    except Exception:
                        try:
                            item[key] = NUMERIC_MAP[key](float(val))
                        except Exception:
                            item[key] = None
            else:
                item[key] = None
        rows.append(item)

    return rows, "success"


def build_prompt_for_llm(user_name: str, metrics_rows: list, instruction: str, display_utc: bool = False) -> str:
    """
    Формирует текст-подсказку для LLM на основе всех метрик пользователя.
    display_utc: если True — выводит UTC, иначе локальное время.
    """
    lines = []

    for m in metrics_rows:
        ts: datetime = m["timestamp"]
        t = ts.strftime("%Y-%m-%d %H:%M UTC") if display_utc else ts.astimezone().strftime("%Y-%m-%d %H:%M")
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
