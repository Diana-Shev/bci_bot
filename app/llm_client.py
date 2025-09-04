#если DEEPSEEK_API_KEY пустой — будет мок-ответ. Это удобно чтобы разворачивать и тестировать.
import httpx
import json
from .config import settings

DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek-chat"

async def _call_deepseek(messages: list, model: str = DEFAULT_MODEL, max_tokens: int = 800, temperature: float = 0.2) -> str:
    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(DEEPSEEK_ENDPOINT, headers=headers, json=payload)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]

async def analyze_metrics(prompt_text: str) -> str:
    if not settings.DEEPSEEK_API_KEY:
        # детерминированный мок для тестирования
        mock = {
            "productivity_periods": [
                {"start_time": "10:00", "end_time": "11:30", "recommended_activity": "Deep work: complex tasks"},
                {"start_time": "14:30", "end_time": "15:00", "recommended_activity": "Light tasks / admin"}
            ],
            "day_plan": "10:00-11:30 deep work; 12:30-13:00 lunch; 14:30-15:00 light tasks; sleep before 23:00",
            "improvement_suggestions": [
                "Do 5-min breathing every hour in the morning",
                "Schedule hardest tasks at 10:00",
                "10-min walk after lunch"
            ]
        }
        return json.dumps(mock)
    messages = [
        {"role": "system", "content": "You are a helpful data analyst for EEG/BCI metrics. Answer in strict JSON only."},
        {"role": "user", "content": prompt_text},
    ]
    return await _call_deepseek(messages)
