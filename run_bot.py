#!/usr/bin/env python3
"""
Скрипт для запуска Telegram бота
Запускай его на сервере после настройки .env файла
"""

import os
import sys
from dotenv import load_dotenv

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Загружаем переменные окружения
load_dotenv()

def main():
    """Запускает бота"""
    # Проверяем наличие необходимых переменных
    required_vars = ["BOT_TOKEN", "DATABASE_URL"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Ошибка: Отсутствуют переменные окружения: {', '.join(missing_vars)}")
        print("Создай файл .env на основе env_example.txt")
        return
    
    print("🚀 Запускаю Telegram бота...")
    print(f"🤖 Токен бота: {os.getenv('BOT_TOKEN')[:10]}...")
    print(f"🗄️ База данных: {os.getenv('DATABASE_URL').split('@')[-1] if '@' in os.getenv('DATABASE_URL') else 'локальная'}")
    
    try:
        # Импортируем и запускаем бота
        from app.bot import main as bot_main
        bot_main()
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")

if __name__ == "__main__":
    main()
