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
        
        from app.crud import get_or_create_user, save_metrics_bulk
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
        metric = Metric(
            user_id=1,
            metric_name="test_metric",
            metric_value=85.5
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
        
        return True
    except Exception as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестов...")
    print("=" * 50)
    
    tests = [
        ("Тест импортов", test_imports),
        ("Тест моделей", test_models),
        ("Тест конфигурации", test_config)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}:")
        if test_func():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Результаты: {passed}/{total} тестов прошли успешно")
    
    if passed == total:
        print("🎉 Все тесты прошли успешно!")
        return 0
    else:
        print("❌ Некоторые тесты не прошли")
        return 1

if __name__ == "__main__":
    exit(main())

