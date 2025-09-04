#устанавливает асинхронное подключение к БД
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .config import settings

# engine для asyncpg
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

# фабрика асинхронных сессий
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

