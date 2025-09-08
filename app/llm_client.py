#если DEEPSEEK_API_KEY пустой — будет мок-ответ. Это удобно чтобы разворачивать и тестировать.
import httpx
import json
from .config import settings

# По умолчанию используем OpenRouter, если задан OPENROUTER_API_KEY, иначе DeepSeek API.
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek/deepseek-chat-v3.1"

async def _call_openrouter(messages: list, model: str, max_tokens: int = 800, temperature: float = 0.2) -> str:
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(OPENROUTER_ENDPOINT, headers=headers, json=payload)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]

async def _call_deepseek(messages: list, model: str, max_tokens: int = 800, temperature: float = 0.2) -> str:
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
    # Мок-ответ, если нет ни одного ключа
    if not settings.DEEPSEEK_API_KEY and not getattr(settings, "OPENROUTER_API_KEY", ""):
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
    # Если есть ключ OpenRouter — используем его, иначе DeepSeek API
    model = getattr(settings, "LLM_MODEL", DEFAULT_MODEL)
    if getattr(settings, "OPENROUTER_API_KEY", ""):
        return await _call_openrouter(messages, model=model)
    return await _call_deepseek(messages, model=model)
