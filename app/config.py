"""
Читает .env и предоставляет объект settings.
Совместимо с Pydantic v2 (через pydantic-settings) и v1 (fallback).
"""

try:
    # Pydantic v2 путь
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        BOT_TOKEN: str
        DATABASE_URL: str
        DEEPSEEK_API_KEY: str = ""
        OPENROUTER_API_KEY: str = ""
        LLM_MODEL: str = "deepseek/deepseek-chat-v3.1"
        DOWNLOADS_DIR: str = "./downloads"

        model_config = SettingsConfigDict(env_file=".env")

except Exception:
    # Fallback для Pydantic v1
    from pydantic import BaseSettings  # type: ignore

    class Settings(BaseSettings):
        BOT_TOKEN: str
        DATABASE_URL: str
        DEEPSEEK_API_KEY: str = ""
        OPENROUTER_API_KEY: str = ""
        LLM_MODEL: str = "deepseek/deepseek-chat-v3.1"
        DOWNLOADS_DIR: str = "./downloads"

        class Config:
            env_file = ".env"

settings = Settings()

