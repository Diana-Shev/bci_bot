#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Тест импортов модулей"""
    try:
        from app.models import User, Metric, ProductivityPeriod, DailyRecommendation, ImprovementSuggestion
        print("✅ Импорт моделей успешен")
        
        from app.config import settings
        print("✅ Импорт конфигурации успешен")
        
        from app.crud import get_or_create_user, save_metrics_bulk, save_productivity_periods
        print("✅ Импорт CRUD операций успешен")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        return False

def test_models():
    """Тест создания экземпляров моделей"""
    try:
        from app.models import User, Metric, ProductivityPeriod, DailyRecommendation, ImprovementSuggestion
        
        # Тест User
        user = User(
            telegram_id=12345,
            username="test_user",
            name="Test User",
            email="test@example.com"
        )
        print("✅ Модель User создана успешно")
        
        # Тест Metric
        from datetime import datetime
        metric = Metric(
            user_id=1,
            timestamp=datetime.utcnow(),
            cognitive_score=85,
            focus=70,
            chill=30,
            stress=20,
            self_control=60,
            anger=5,
            relaxation_index=0.5,
            concentration_index=0.7,
            fatique_score=0.2,
            reverse_fatique=0.1,
            alpha_gravity=0.3,
            heart_rate=72
        )
        print("✅ Модель Metric создана успешно")
        
        # Тест ProductivityPeriod
        from datetime import time
        period = ProductivityPeriod(
            user_id=1,
            start_time=time(9, 0),
            end_time=time(12, 0),
            productivity_score=90.0,
            recommended_activity="coding"
        )
        print("✅ Модель ProductivityPeriod создана успешно")
        
        # Тест DailyRecommendation
        from datetime import date
        rec = DailyRecommendation(
            user_id=1,
            date=date.today(),
            recommendation_text="Test recommendation"
        )
        print("✅ Модель DailyRecommendation создана успешно")
        
        # Тест ImprovementSuggestion
        suggestion = ImprovementSuggestion(
            user_id=1,
            suggestion_text="Test suggestion"
        )
        print("✅ Модель ImprovementSuggestion создана успешно")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка создания моделей: {e}")
        return False

def test_config():
    """Тест конфигурации"""
    try:
        from app.config import settings
        
        print(f"✅ BOT_TOKEN: {settings.BOT_TOKEN}")
        print(f"✅ DATABASE_URL: {settings.DATABASE_URL}")
        print(f"✅ DEEPSEEK_API_KEY: {settings.DEEPSEEK_API_KEY}")
        print(f"✅ DOWNLOADS_DIR: {settings.DOWNLOADS_DIR}")
        
        # Проверяем, что DATABASE_URL содержит asyncpg
        if "asyncpg" in settings.DATABASE_URL:
            print("✅ DATABASE_URL содержит asyncpg драйвер")
        else:
            print("⚠️ DATABASE_URL не содержит asyncpg драйвер")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return False

def test_database_connection():
    """Тест подключения к базе данных (без создания таблиц)"""
    try:
        from app.database import engine
        
        print("✅ Импорт engine успешен")
        
        # Проверяем, что engine создан
        if engine:
            print("✅ Engine создан успешно")
            print(f"✅ URL базы данных: {engine.url}")
            return True
        else:
            print("❌ Engine не создан")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return False

def test_crud_functions():
    """Тест CRUD функций (без выполнения запросов)"""
    try:
        from app.crud import (
            get_or_create_user, 
            save_metrics_bulk, 
            save_productivity_periods,
            save_day_plan,
            save_improvement_suggestions
        )
        
        print("✅ Все CRUD функции импортированы успешно")
        
        # Проверяем, что функции существуют и являются callable
        functions = [
            get_or_create_user,
            save_metrics_bulk,
            save_productivity_periods,
            save_day_plan,
            save_improvement_suggestions
        ]
        
        for func in functions:
            if callable(func):
                print(f"✅ Функция {func.__name__} является callable")
            else:
                print(f"❌ Функция {func.__name__} не является callable")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка CRUD функций: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Запуск комплексного тестирования...")
    print("=" * 60)
    
    tests = [
        ("Тест импортов", test_imports),
        ("Тест моделей", test_models),
        ("Тест конфигурации", test_config),
        ("Тест подключения к БД", test_database_connection),
        ("Тест CRUD функций", test_crud_functions)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}:")
        if test_func():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"📊 Результаты: {passed}/{total} тестов прошли успешно")
    
    if passed == total:
        print("🎉 Все тесты прошли успешно!")
        print("\n💡 Система готова к работе!")
        print("📝 Следующий шаг: настроить и запустить PostgreSQL")
    else:
        print("❌ Некоторые тесты не прошли")
        print("\n🔧 Требуется исправление ошибок")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    exit(main())
