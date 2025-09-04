#!/usr/bin/env python3
"""
Скрипт для создания таблиц в базе данных PostgreSQL
Запускай его на сервере после настройки .env файла
"""

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from app.models import Base

# Загружаем переменные окружения
load_dotenv()

async def create_tables():
    """Создает все таблицы в базе данных"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ Ошибка: DATABASE_URL не найден в .env файле")
        return
    
    print(f"🔗 Подключаюсь к базе данных: {database_url}")
    
    try:
        # Создаем движок
        engine = create_async_engine(database_url, echo=True)
        
        # Создаем все таблицы
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Все таблицы успешно созданы!")
        
        # Показываем список созданных таблиц
        async with engine.begin() as conn:
            result = await conn.run_sync(lambda sync_conn: sync_conn.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
        
        print(f"📋 Созданные таблицы: {', '.join(tables)}")
        
    except Exception as e:
        print(f"❌ Ошибка при создании таблиц: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    print("🚀 Запускаю создание таблиц...")
    asyncio.run(create_tables())
