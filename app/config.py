# этот файл читает .env и даёт значение settings в коде
from pydantic import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str  # ждём async URL: postgresql+asyncpg://...
    DEEPSEEK_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    LLM_MODEL: str = "deepseek/deepseek-chat-v3.1"
    DOWNLOADS_DIR: str = "./downloads"

    class Config:
        env_file = ".env"

settings = Settings()

